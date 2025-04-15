import os
import subprocess
import json
from multiprocessing import Pool
from tqdm import tqdm
from functools import partial
import time  

# 常量定义提升可维护性
EXCLUDED_DIRS = {
    "share", "build", "thirdparty", "testsuite","third_party",
    "third-party", "include", "lib64", "tests", 
    "test", "testsuites", "scripts", "lib-src","lib",
    "libraries", "cmake-proxies","external","harfbuzz","sqlite3"
}
OPTIMIZERS = ['-O0', '-O1', '-O2', '-O3', '-Os', '-Ofast']
COMPILE_STANDARDS = {
    '.c': '-std=c99',
    '.cpp': '-std=c++11',
    '.cc': '-std=c++11'
}

def dump_json_file(data, file_path):
    """优化后的JSON文件写入"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def is_source_excluded(root_path):
    """检查源文件是否需要被排除"""
    path_parts = os.path.normpath(root_path).split(os.path.sep)
    return any(part in EXCLUDED_DIRS for part in path_parts)

def run_clang_command(cmd_args, out_file):
    """安全执行clang命令"""
    try:
        result = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return 0, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stderr
    except Exception as e:
        return -1, str(e)

def compile_to_asm(file_path, out_root, include_dirs):
    """核心编译函数"""
    base_name = os.path.basename(file_path)
    file_stem = os.path.splitext(base_name)[0]
    ext = os.path.splitext(base_name)[1].lower()
    
    if ext in ('.cc', '.cpp'):
        cc = 'clang++'
    elif ext in ('.c'):
        cc = 'clang'
    else:
        return 1, 'Unsupported file type: {}'.format(ext)
    # 构造基础命令
    cmd_args = [
        cc,
        "-S",
        file_path
    ]
    
    # 添加编译标准
    if ext in ('.cpp', '.cc'):
        cmd_args.insert(1, "-stdlib=libc++")
        cmd_args.insert(1, "-std=c++11")
    
    # 添加包含路径
    for include in include_dirs:
        cmd_args.extend(["-I", include])
    
    # 创建输出目录
    os.makedirs(out_root, exist_ok=True)
    
    # 尝试不同优化级别
    exit_codes = []
    error_log = []
    
    for opt_level in OPTIMIZERS:
        opt_dir = os.path.join(out_root, opt_level)
        os.makedirs(opt_dir, exist_ok=True)
        output_path = os.path.join(opt_dir, f"{file_stem}.s")
        
        if os.path.exists(output_path):
            continue  # 跳过已存在文件
        
        full_cmd = cmd_args.copy()
        full_cmd.insert(1, opt_level)  # 插入优化级别
        full_cmd += ["-o", output_path]
        cmd_srt =  ' '.join(full_cmd)
        # error_log.append(f"Running command: {cmd_srt}")
        ret_code, err_msg = run_clang_command(full_cmd, output_path)
        exit_codes.append(ret_code)
        if ret_code != 0:
            error_log.append(f"Error compiling {base_name} with {opt_level}:\n{err_msg}")
    
    return sum(exit_codes), '\n'.join(error_log)

def process_single_file(args, include_dirs):
    """多进程任务包装函数"""
    file_path, out_path = args
    return compile_to_asm(file_path, os.path.join(out_path, "ir_files"), include_dirs)

def process_project(project_path):
    """主处理函数"""
    OUTPUT_ROOT = r"/home/lab314/cjw/similarity/datasets/bin/clang/clang_asm"
    repo_name =  os.path.basename(project_path)
    output_path = os.path.join(OUTPUT_ROOT, repo_name)
    # 初始化目录
    os.makedirs(output_path, exist_ok=True)
    log_path = os.path.join(output_path, "log.txt")

    if os.path.exists(log_path):
        return 1
    
    # 收集文件路径
    source_files = []
    include_dirs = set()
    include_dirs.add(project_path)
    
    for root, dirs, files in os.walk(project_path):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)
            
            # 处理头文件
            if file_ext in ('.h', '.hpp','.hh'):
                include_dirs.add(root)
                
            # 处理源文件
            elif file_ext in ('.c', '.cpp', '.cc'):
                if not is_source_excluded(root) and 'test' not in file.lower():
                    source_files.append(full_path)
    
    # 保存文件列表
    dump_json_file(source_files, os.path.join(output_path, "c_files.json"))
    dump_json_file(list(include_dirs), os.path.join(output_path, "include_files.json"))
    # 处理大型项目
    # if len(source_files) > 1500:
    #     print(f"Project {os.path.basename(project_path)} is too large, skipping")
    #     return 0
    
    # 并行处理
    failed_files = []
    success_count = 0
    error_log = []
    
    with Pool(processes=3) as pool:
        task_args = [(f, output_path) for f in source_files]
        task_func = partial(process_single_file, include_dirs=list(include_dirs))
        
        with tqdm(total=len(source_files), desc=f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]Processing {os.path.basename(project_path)}") as pbar:
            for ret_code, err_msg in pool.imap_unordered(task_func, task_args):
                if ret_code == 0:
                    success_count += 1
                else:
                    failed_files.append(task_args[len(failed_files)][0])
                    error_log.append(err_msg)
                pbar.update()
        
    # error_log.append(f"success rate: {success_count}/{len(source_files)}")
    # 保存结果
    with open(log_path, 'w') as f_log:
        f_log.write('\n'.join(error_log))

        
    dump_json_file(failed_files, os.path.join(output_path, "failed_list.json"))
    
    # print(f"success rate: {success_count}/{len(source_files)}")
    return 1 if success_count > 0 else 0


def main():
    REPOS_ROOT = r"/home/lab314/cjw/ghcc/repos/repos1"
    
    ERROR_LOG = r"/home/lab314/cjw/similarity/desend2ir/error_pros.json"
    
    error_projects = []
    
    for repo in os.listdir(REPOS_ROOT):
        repo_path = os.path.join(REPOS_ROOT, repo)
        # print(f"\n{'='*60}\n处理项目: {repo}")
        
        try:
            result = process_project(repo_path)
            if not result:
                error_projects.append(repo)
        except Exception as e:
            print(f"处理异常: {str(e)}")
            error_projects.append(repo)
        
        # 实时保存错误日志
        if error_projects:
            dump_json_file(error_projects, ERROR_LOG)
if __name__ == '__main__':
    # proj_path = r'/home/lab314/cjw/ghcc/repos/repos2/MayaPosch_____NymphCast'
    # process_project(proj_path)
    main()