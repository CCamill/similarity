from collections import defaultdict
import os
import llvmlite.ir as ir
import llvmlite.binding as llvm
import re
import json
import argparse
from tqdm import tqdm
import traceback
from pathlib import Path
import subprocess
import time 

# 初始化LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# 常量定义
SOURCE_PROJ_DIR = r'/home/lab314/cjw/similarity/datasets/source/source_lls'
SOURCE_GLOBAL_INFO_DIR = r'/home/lab314/cjw/similarity/datasets/source/global_info'
BIN_PROJ_DIR = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls'
BIN_GLOBAL_INFO_DIR = r'/home/lab314/cjw/similarity/datasets/bin/global_info'
OPTI_LEVELS = ['-O0', '-O1', '-O2', '-O3', '-Os', '-Oz']
var_list = []

def setup_logging(log_path: Path):
    """初始化日志文件"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path.open('w', encoding='utf-8')

def log_error(log_file, message: str, exception: Exception = None):
    """记录错误信息"""
    log_file.write(f"[{time.ctime()}ERROR] {message}\n")
    if exception:
        log_file.write(f"Exception Type: {type(exception).__name__}\n")
        log_file.write(f"Exception Message: {str(exception)}\n")
        log_file.write("Stack Trace:\n")
        traceback.print_exc(file=log_file)
    log_file.write("-"*80 + "\n")
    log_file.flush()

def generate_llvm_ir(input_file: Path) -> str:
    """生成LLVM IR"""
    try:
        with input_file.open('r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 尝试用二进制模式读取
        with input_file.open('rb') as f:
            return f.read().decode('utf-8', errors='ignore')

def get_global_var_name(global_var: str) -> str:
    """提取全局变量名称"""
    try:
        var_start = global_var.index('@')
        var_end = global_var.index('=', var_start)
        return global_var[var_start:var_end].strip()
    except ValueError:
        return "unknown"

def parse_global_var(global_var: str) -> dict:
    """解析全局变量信息"""
    info = {'raw_definition': global_var}
    
    try:
        # 变量名称解析
        var_name = get_global_var_name(global_var)
        info['var_name'] = var_name
        var_list.append(var_name)
        
        # 类型匹配逻辑
        patterns = [
            (r'(\[\d+ x i\d+\]) \[(.*)\]', 'int_array'),
            (r'((?:constant|global|internal) \[[\d]+ x i[\d]+\] c)', 'string'),
            (r'(?:constant|global|internal) i(1|8|16|32|64|128)\s+(-?\d+)', 'int'),
            (r'float\s+((?:0x[0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?(?:[pP][+-]?\d+)?|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)', 'float'),
            (r'double\s+((?:0x[0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?(?:[pP][+-]?\d+)?|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)', 'double'),
            (r'(?:constant|global|internal) \[[\d]+ x i[\d]+\*\]', 'ptr_array'),
            (r'(?:constant|global|internal) \[[\d]+ x i[\d]+\]\*', 'array_ptr')
        ]

        for pattern, var_type in patterns:
            if match := re.search(pattern, global_var):
                info['type'] = var_type
                # 根据类型提取详细信息
                if var_type == 'int_array':
                    info['dimension'] = match.group(1)
                    info['values'] = match.group(2).split(', ')
                elif var_type in ('float', 'double'):
                    info['value'] = float(match.group(1))
                elif var_type == 'int':
                    info['bits'] = int(match.group(1))
                    info['value'] = int(match.group(2))
                break
        else:
            info['type'] = 'unknown'

        return info
    except Exception as e:
        info['error'] = f"Parsing failed: {str(e)}"
        return info

def extract_global_info_from_module(module):
    global_vars = [str(gv) for gv in module.global_variables]
    results = defaultdict(dict)
    
    for idx, gv in enumerate(global_vars):
        result = parse_global_var(gv)
        result['id'] = idx
        results[result['var_name']] = result
    return results

def extract_global_info(input_path: Path, output_path: Path, log_file):
    """提取全局变量信息主函数"""
    try:
        # 生成LLVM IR
        llvm_ir = generate_llvm_ir(input_path)
        
        # 解析模块
        module = llvm.parse_assembly(llvm_ir)
        module.verify()
        
        # 提取全局变量
        results = extract_global_info_from_module(module)
        # 保存结果
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
    except Exception as e:
        log_error(log_file, f"Failed to process {input_path.name}", e)

def process_single_binary(bin_proj_path: Path, global_info_path: Path, log_file):
    """处理单个二进制文件"""
    try:
        # 生成LL文件路径
        ll_path = bin_proj_path / f"{bin_proj_path.name}.ll"
        bc_path = bin_proj_path / f"{bin_proj_path.name}.bc"
        
        # 反汇编
        if not ll_path.exists():
            raise FileNotFoundError(f"Missing both .ll and .bc files: {bin_proj_path.name}")
            
        result = subprocess.run(
            ["llvm-dis", str(bc_path), "-o", str(ll_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"llvm-dis failed: {result.stderr}")
        
        # 处理全局变量
        output_path = global_info_path / f"{bin_proj_path.name}_global_info.json"
        if not output_path.exists():
            extract_global_info(ll_path, output_path, log_file)
            
    except Exception as e:
        log_error(log_file, f"Failed to process {bin_proj_path.name}", e)

def get_bin_ll():
    """主处理函数"""
    bin_proj_root = Path(BIN_PROJ_DIR)
    global_info_root = Path(BIN_GLOBAL_INFO_DIR)
    
    # 遍历所有项目
    for project_dir in bin_proj_root.iterdir():
        if not project_dir.is_dir():
            continue
            
        # 设置日志路径
        log_path = global_info_root / project_dir.name / "log_file.txt"
        if log_path.exists():
            continue

        with setup_logging(log_path) as log_file:
            try:
                # 创建输出目录
                global_info_path = global_info_root / project_dir.name
                global_info_path.mkdir(parents=True, exist_ok=True)
                
                # 获取所有二进制目录
                binary_dirs = [d for d in project_dir.iterdir() if d.is_dir()]
                
                # 进度条
                with tqdm(binary_dirs, desc=f"Processing {project_dir.name}") as pbar:
                    for binary_dir in pbar:
                        pbar.set_postfix({"binary": binary_dir.name})
                        process_single_binary(binary_dir, global_info_path, log_file)
                        
            except Exception as e:
                log_error(log_file, f"Fatal error processing project {project_dir.name}", e)

if __name__ == '__main__':
    get_bin_ll()