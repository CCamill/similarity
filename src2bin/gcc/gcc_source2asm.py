import os
import subprocess
from multiprocessing import Pool, Manager
from tqdm import tqdm
import json
import time
import logging
from contextlib import contextmanager

# 常量定义
EXCLUDED_DIRS = {
    "share", "build", "thirdparty", "testsuite","third_party",
    "third-party", "include", "lib64", "tests", 
    "test", "testsuites", "scripts", "lib-src","lib",
    "libraries", "cmake-proxies","external"
}
OPTIMIZERS = ['-O0', '-O1', '-O2', '-O3', '-Os', '-Ofast']
FILE_EXTENSIONS = ('.c', '.cpp', '.cc')
HEADER_EXTENSIONS = ('.h', '.hpp')
MAX_FILE_COUNT = 1500
TIMEOUT = 300  # 5分钟超时

# 日志配置
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@contextmanager
def change_dir(new_dir):
    """上下文管理器用于安全切换工作目录"""
    original_dir = os.getcwd()
    try:
        os.makedirs(new_dir, exist_ok=True)
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(original_dir)

def dump_json(data, path):
    """安全的JSON写入"""
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save {path}: {str(e)}")

def build_compile_command(file_path, include_paths, output_path, optimizer):
    file_name = os.path.basename(file_path)
    if file_name.endswith('.c'):
        cc = 'gcc'
    elif file_name.endswith('.cpp') or file_name.endswith('.cc'):
        cc = 'g++'
    else:
        raise ValueError(f"Unsupported file extension: {file_name}")
    """构建编译命令"""
    cmd = [
        cc,
        '-S',
        file_path,
        '-o', output_path
    ]
    
    # 添加包含路径
    for path in include_paths:
        cmd.extend(['-I', path])
    
    # 插入优化选项到正确位置（gcc选项顺序敏感）
    cmd.insert(1, optimizer)
    
    # 根据文件类型添加标准
    # if file_path.endswith('.c'):
    #     cmd.insert(2, '-std=c99')
    # elif file_path.endswith(('.cpp', '.cc')):
    #     cmd.extend(['-std=c++11', '-stdlib=libc++'])
    
    return cmd

def compile_file(args):
    """编译单个文件（供多进程调用）"""
    file_path, proj_output, include_paths = args
    errors = []
    base_name = os.path.basename(file_path)
    file_stem = os.path.splitext(base_name)[0]
    
    # 检查所有优化版本是否已存在
    all_exist = all(
        os.path.exists(os.path.join(proj_output, 'bin_files', opti, f"{file_stem}.s"))
        for opti in OPTIMIZERS
    )
    if all_exist:
        return 0, []

    # 为每个优化级别编译
    for opti in OPTIMIZERS:
        output_dir = os.path.join(proj_output, 'bin_files', opti)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{file_stem}.s")
        
        if os.path.exists(output_path):
            continue

        try:
            cmd = build_compile_command(file_path, include_paths, output_path, opti)
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                encoding='utf-8',
                errors='replace',  # 处理非UTF-8输出
                timeout=TIMEOUT
            )
            
            if result.returncode != 0:
                error_msg = (
                    f"Compilation failed [{opti}] {base_name}\n"
                    f"Error: {result.stderr[:2000]}"  # 截断长错误信息
                )
                errors.append(error_msg)
                logger.error(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout ({TIMEOUT}s) [{opti}] {base_name}"
            errors.append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error [{opti}] {base_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

    return len(errors), errors

def process_project(proj_path):
    """处理单个项目"""
    output_base = "/home/lab314/cjw/similarity/datasets/bin/gcc_asm"

    proj_name = os.path.basename(proj_path.rstrip('/'))
    output_path = os.path.join(output_base, proj_name)
    
    # 跳过已处理项目
    log_path = os.path.join(output_path, 'process.log')
    if os.path.exists(log_path):
        print(f"Skipping processed project: {proj_name}")
        return True

    with change_dir(proj_path), Manager() as manager:
        # 收集文件路径
        include_paths = set()
        source_files = []
        
        for root, dirs, files in os.walk('.', topdown=True):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            # 收集包含路径
            if os.path.basename(root) in {'include', 'lib'}:
                include_paths.add(os.path.abspath(root))
                
            # 收集源文件
            for f in files:
                full_path = os.path.abspath(os.path.join(root, f))
                if f.endswith(FILE_EXTENSIONS) and 'test' not in f.lower():
                    source_files.append(full_path)
                elif f.endswith(HEADER_EXTENSIONS):
                    include_paths.add(os.path.dirname(full_path))

        # 保存文件列表
        os.makedirs(output_path, exist_ok=True)
        dump_json(source_files, os.path.join(output_path, 'files.json'))
        
        if len(source_files) > MAX_FILE_COUNT:
            logger.warning(f"Project {proj_name} has too many files ({len(source_files)})")
            return False

        # 准备多进程任务
        task_args = [(f, output_path, list(include_paths)) for f in source_files]
        total_errors = manager.list()
        
        with Pool() as pool:
            results = list(tqdm(
                pool.imap_unordered(compile_file, task_args),
                total=len(source_files),
                desc=f"Compiling {proj_name}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [no error display]'
            ))
            
            # 收集错误信息
            for error_count, errors in results:
                if error_count > 0:
                    total_errors.extend(errors)

        # 保存日志
        if total_errors:
            with open(log_path, 'w') as f:
                f.write('\n'.join(total_errors))
            logger.warning(f"Completed {proj_name} with {len(total_errors)} errors")
            return False
        
        logger.info(f"Successfully processed {proj_name}")
        return True

def main():
    logging.disable(logging.CRITICAL)
    repos_root = "/home/lab314/cjw/ghcc/repos/repos3"
    error_log = "/home/lab314/cjw/similarity/desend2ir/error_projects.json"
    
    error_projects = []
    
    for entry in os.scandir(repos_root):
        if not entry.is_dir():
            continue
            
        try:
            success =  process_project(entry.path)
            if not success:
                error_projects.append(entry.name)
        except Exception as e:
            logger.exception(f"Failed to process {entry.name}: {str(e)}")
            error_projects.append(entry.name)
        
        # 定期保存错误列表
        if len(error_projects) % 5 == 0:
            dump_json(error_projects, error_log)

    dump_json(error_projects, error_log)

if __name__ == '__main__':
    proj_path = r'/home/lab314/cjw/ghcc/repos/repos2/MayaPosch_____NymphCast'
    process_project(proj_path)