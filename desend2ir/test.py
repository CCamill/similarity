
import subprocess
import os
import time
from parse_makefile_ir import process_project
from desend2IR import generate_ir
import shutil
from tqdm import tqdm
def test1():
    file_path = "/home/chang/Desktop/sources/openssl-3.4.0/apps/ca.c"
    out_path = "ca.ll"
    cmd = f"clang -emit-llvm -o {out_path} -S {file_path} -I/home/chang/Desktop/sources/openssl-3.4.0/include -I/home/chang/Desktop/sources/openssl-3.4.0/apps/include"

    cmd = r'clang -emit-llvm -o openssl-3.4.0/ir_files/e_ossltest.ll -S /home/chang/Desktop/sources/openssl-3.4.0/engines/e_ossltest.c -I /home/chang/Desktop/sources/openssl-3.4.0/providers/common/include -I /home/chang/Desktop/sources/openssl-3.4.0/providers/implementations/include -I /home/chang/Desktop/sources/openssl-3.4.0/providers/fips/include -I /home/chang/Desktop/sources/openssl-3.4.0/include -I /home/chang/Desktop/sources/openssl-3.4.0/apps/include'
    proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 获取标准输出和标准错误
    stdout, stderr = proc.communicate()

    # 获取返回码
    return_code = proc.returncode
    print(stderr)
    print(return_code)

def test2():
    proj_path = r"/home/chang/Desktop/sources/openssl-3.4.0"
    paths = os.walk(proj_path)
    for path, dir_list, file_list in paths:
        has_h_file = any(file.endswith('.h') for file in file_list)
        if has_h_file:
            print(path)
            #print(file_list)
        # if os.path.basename(path) =="include":
            # print(path)

def test3():
    bin_ll_path = r"/home/lab314/cjw/similarity/datasets/binary_lls"
    bin_path = r'/home/lab314/cjw/ghcc/binaries'
    print(len(os.listdir(bin_path)))

def test4():
    current_path = os.getcwd()
    # 改变当前工作目录
    if current_path:
        # 输出当前工作目录
        print("Current working directory:", current_path)

def test5():
    paths = r'/home/lab314/cjw/ghcc/repos/repos1/curl_____curl'
    include_paths = []
    file_paths = []
    other_files = ["/include", "/lib", "/CMake"]
    cmd = []
    for path, dir_lst, file_lst in os.walk(paths):
        if os.path.basename(path) in ["include", "lib"]:
            include_paths.append(path)
        if "/lib/" in path or "/include/" in path:
            continue
        if os.path.basename(path) == "CMake":
            continue
        for other in other_files:
            if other in path:
                continue
        for file_name in file_lst:
            if file_name.endswith((".c", ".cpp",".cc")) and 'test' not in file_name:
                file_path = os.path.join(path, file_name)
                file_paths.append(file_path)
            if file_name.endswith((".h", ".hpp")):
                include_paths.append(path)  # 添加头文件路径到 include_paths 中
    include_paths = set(include_paths)
    for include_path in include_paths:
        cmd.append(f'-I{include_path}')
    print(' '.join(cmd))

def generate_llvm_ir(input_file):
    # 从输入文件读取 LLVM IR
    with open(input_file, 'r') as f:
        llvm_ir = f.read()

    # 打印读取的 LLVM IR
    # print("Read LLVM IR from file:")

    return llvm_ir



def test6():
    proj_path = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls/gpac_____gpac'
    proj_global_info_dir = r'/home/lab314/cjw/similarity/datasets/bin/global_info/gpac_____gpac'
    for bin_name in os.listdir(proj_path):
        ll_path = os.path.join(proj_path, bin_name, bin_name + ".ll")
        if not os.path.exists(ll_path):
            continue
        bc_path = os.path.join(proj_path, bin_name, bin_name + ".bc")
        os.system(f"llvm-dis {bc_path} -o {ll_path}")
        test7(ll_path)

def test7(input_file = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls/gpac_____gpac/8d937514441dc48409bbb16fb542f19a6b7497e60b56bbe627fd23c9a638f831/8d937514441dc48409bbb16fb542f19a6b7497e60b56bbe627fd23c9a638f831.ll'):
    # input_file = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls/gpac_____gpac/1dc370c87c140ed0e40825b9b110366c73b3e2d7ab2cead937a96c840d3200da/1dc370c87c140ed0e40825b9b110366c73b3e2d7ab2cead937a96c840d3200da.ll'
    llvm_name = os.path.basename(input_file)

    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()


    llvm_ir = generate_llvm_ir(input_file)

    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        print(f"{llvm_name} parsed successfully.\n")
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {input_file} \n {e}")
        # return


def test8():
    # 删除空目录
    summary_dir = r'/home/lab314/cjw/similarity/datasets/source/summary'
    for proj_name in os.listdir(summary_dir):
        proj_path = os.path.join(summary_dir, proj_name)
        if len(os.listdir(proj_path)) == 0:
            os.rmdir(proj_path)

# def test9():
#     path = r'/home/lab314/cjw/similarity/datasets/source/source_lls'
#     for proj_name in os.listdir(path):
#         proj_path = os.path.join(path, proj_name)
#         log_path = os.path.join(proj_path, 'log.txt')
#         if os.path.exists(log_path):
#             os.remove(log_path)
        # print(log_path)

def test10():
    process_project(r'/home/lab314/cjw/ghcc/repos/repos1/libvips_____libvips', r"/home/lab314/cjw/similarity/datasets/source/source_lls/libvips_____libvips")

def test11():
    bin_proj_dir = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls'
    bin_global_info_dir = r'/home/lab314/cjw/similarity/datasets/bin/global_info'

    bin_projects = os.listdir(bin_proj_dir)
    for bin_proj_name in bin_projects:
        bin_proj_path = os.path.join(bin_proj_dir, bin_proj_name)
        bin_proj_global_info_path = os.path.join(bin_global_info_dir, bin_proj_name)

        if not os.path.exists(bin_proj_global_info_path):
            os.makedirs(bin_proj_global_info_path)

        for bin_name in os.listdir(bin_proj_path):
            bin_path = os.path.join(bin_proj_path, bin_name, bin_name + '.ll')
            if not os.path.exists(bin_path):
                continue
            bc_path = os.path.join(bin_proj_path, bin_name, bin_name + '.bc')
            os.system(f"llvm-dis {bc_path} -o {bin_path}")
            print(bin_name , ' success')
            global_info_path = os.path.join(bin_proj_global_info_path, bin_name + '_global_info.json')
        
def test12():
    bin_proj_dir = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls'
    numbers = 0
    for bin_proj_name in os.listdir(bin_proj_dir):
        proj_path = os.path.join(bin_proj_dir, bin_proj_name)
        numbers += len(os.listdir(proj_path))
    print(numbers)

def test13():
    num = 0
    source_proj_dir = r'/home/lab314/cjw/similarity/datasets/source/source_lls'
    for proj_name in os.listdir(source_proj_dir):
        proj_ir_path = os.path.join(source_proj_dir, proj_name, 'ir_files', '-O0')
        if os.path.exists(proj_ir_path):
            num += len(os.listdir(proj_ir_path)) * 6
    print(num)    

import json
def test15():
    too_large_bin_lls_path = r'/home/lab314/cjw/similarity/datasets/bin/too_large_bin_lls.json'
    too_large_bin_lls = []
    ll_path = r"/home/lab314/cjw/similarity/datasets/bin/bin_lls"
    for proj_name in os.listdir(ll_path):
        proj_path = os.path.join(ll_path, proj_name)
        bin_files = [f for f in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, f))]
        
        # 准备任务参数（包含日志文件路径）
        for bin_name in bin_files:
            bin_path = os.path.join(proj_path, bin_name, bin_name + '.ll')
            if not os.path.exists(bin_path):
                continue
            file_size = os.path.getsize(bin_path)
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > 30:
                too_large_bin_lls.append(bin_path)
                continue
    with open(too_large_bin_lls_path, 'w', encoding='utf-8') as f:
        json.dump(too_large_bin_lls, f, ensure_ascii=False, indent=2)

def opt_ir():
    ir_path = r'/home/lab314/cjw/ghcc/repos/repos1/micropython_____micropython/mpy-cross/build/py'
    out_path = r'/home/lab314/cjw/similarity/datasets/source/source_lls/micropython_____micropython/ir_files/-O0'
    for ir_file in os.listdir(ir_path):
        input = os.path.join(ir_path, ir_file)
        output = os.path.join(out_path, ir_file)
        cmd = f"opt -S -O1 {input} -o {output}"
        os.system(cmd)


def source2ir():
    projpath = r'/home/lab314/cjw/ghcc/repos/repos1/contiki-os_____contiki'
    outpath = r'/home/lab314/cjw/similarity/datasets/source/source_lls/contiki-os_____contiki'
    generate_ir(projpath, outpath)



def clear_empty_proj():
    path = r'/home/lab314/cjw/similarity/datasets/source/summary'
    for proj in os.listdir(path):
        proj_path = os.path.join(path, proj)
        opti_path = os.path.join(proj_path, '-O0')
        if not os.path.exists(opti_path) or len(os.listdir(opti_path)) == 0:
            print(proj)
            os.system(f'rm -rf {proj_path}')

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def re_json_struct():
    old = r'/home/lab314/cjw/similarity/datasets/source/norm_summary'
    new = r'/home/lab314/cjw/similarity/datasets/source/new_norm_summary'
    for proj in os.listdir(old):
        old_path = os.path.join(old, proj)
        new_path = os.path.join(new, proj)
        if os.path.exists(new_path):
            print(proj, "is exist")
            continue
        if not os.path.exists((os.path.join(old_path, '-O0'))):
            continue
        print("start processing", proj, "...")
        count = len(os.listdir(os.path.join(old_path, '-O0'))) * 6
        pbar = tqdm(total=count)
        for opti in os.listdir(old_path):
            old_opti_path = os.path.join(old_path, opti)
            
            new_opti_path = os.path.join(new_path, opti)
            if not os.path.exists(new_opti_path):
                os.makedirs(new_opti_path)
            for file in os.listdir(old_opti_path):
                old_file_path = os.path.join(old_opti_path, file)
                new_file_path = os.path.join(new_opti_path, file)
                old_data = load_json_file(old_file_path)
                new_data = []
                for function in old_data:
                    function_name = function['function_name']
                    new_data.append({f'{function_name}': function})
                dump_json_file(new_data, new_file_path)
                pbar.update(1)
        pbar.close()

def add_endprix():
    gcc_asm_dir = r'/home/lab314/cjw/similarity/datasets/bin/gcc_asm'
    for proj in os.listdir(gcc_asm_dir):
        asm_dir = os.path.join(gcc_asm_dir, proj, 'bin_files')
        if not os.path.exists(asm_dir):
            continue
        for opti in os.listdir(asm_dir):
            opti_dir = os.path.join(asm_dir, opti)
            for file in os.listdir(opti_dir):
                if not file.endswith('.s'):
                    old_name = os.path.join(opti_dir, file)
                    new_name = os.path.join(opti_dir, file + '.s')
                    os.rename(old_name, new_name)

if __name__ == "__main__":
    re_json_struct()
    pass
