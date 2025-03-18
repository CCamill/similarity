import argparse
import os
import re
import subprocess
import llvmlite.ir as ir
import llvmlite.binding as llvm
import json
from collections import defaultdict
import sys
from tqdm import tqdm
import time
import logging
from multiprocessing import Pool
from functools import partial

def setup_logger(log_file):
    """设置日志记录器"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 移除所有现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # 将文件处理器添加到日志记录器
    logger.addHandler(file_handler)

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def get_funtion_name_by_re(instruction):
    pattern = r'@(\w+)'  # 匹配以 @ 开头的函数名
    match = re.search(pattern, instruction)
    return match.group(1) if match else 'unknown'

def dump_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_llvm_ir(input_file):
    with open(input_file, 'r') as f:
        return f.read()

def parse_llvm_IR(llvm_ir):
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        return llvm_mod
    except RuntimeError as e:
        raise RuntimeError(f"Error parsing LLVM IR: {e}")

def del_debug_info(inst):
    if '!insn.addr' in inst:
        idx = inst.index('!insn.addr') - 2
        return inst[:idx]
    return inst

def get_global_var_name(operand):
    return [var.replace(',', '') for var in operand.split() if var.startswith('@')]

def get_global_var_re(input_string):
    match = re.search(r'@global_var_[\w]+', input_string)
    return match.group() if match else None

def get_varname(instruction):
    return instruction[:instruction.index('=')].strip().replace(" ", "")

def get_function_name(operand):
    try:
        start = operand.index('@')
        end = operand.index('(')
        return operand[start:end].strip()
    except ValueError:
        return 'unknown'

def get_called_function_info(operands, instruction):
    try:
        func_attrs = next(op for op in operands if 'Function Attrs' in op or ('declare' in op and '@' in op))
        return_type_start = func_attrs.index('declare')+7 if 'declare' in func_attrs else func_attrs.index('define')+6
        return_type_end = func_attrs.index('@')
        func_name_start = func_attrs.index('@')
        func_name_end = func_attrs.index('(')
        return (
            func_attrs[func_name_start:func_name_end].strip(),
            func_attrs[return_type_start:return_type_end].strip()
        )
    except (StopIteration, ValueError):
        func_attrs = instruction[instruction.index('call')+4:instruction.index('(')].strip()
        parts = func_attrs.split()
        return (
            parts[1] if len(parts) > 1 else get_funtion_name_by_re(instruction),
            parts[0] if parts else 'void'
        )

def get_block_label(block):
    colon_index = str(block).find(':')
    return str(block)[1:colon_index] if colon_index != -1 else "0"

def process_ir_file(ll_file, output_file, global_info_path, struct_info_path):
    if os.path.exists(output_file):
        return 1, None

    bc_path = ll_file.replace('.ll', '.bc')
    result = subprocess.run(
            ["llvm-dis", str(bc_path), "-o", ll_file],
            capture_output=True,
            text=True
        )
    if result.returncode != 0:
        raise RuntimeError(f"llvm-dis failed: {result.stderr}")

    try:
        # 初始化LLVM环境
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        llvm.initialize_native_asmparser()

        llvm_ir = generate_llvm_ir(ll_file)
        llvm_mod = parse_llvm_IR(llvm_ir)
        global_infos = load_json_file(global_info_path)
        struct_infos = load_json_file(struct_info_path)
        try:
            global_var_list = list(global_infos.keys())
        except Exception as e:
            logging.error(f"{e}")
            global_var_list = []
        try:
            struct_var_list = list(struct_infos.keys())
        except Exception as e:
            logging.error(f"{e}")
            struct_var_list = []
        
        file_info = []
        inst_id = 0

        for function in llvm_mod.functions:
            function_data = process_function(function, global_var_list, struct_var_list, inst_id)
            if function_data:
                file_info.append(function_data)
                inst_id = function_data[function.name]["last_inst_id"] + 1

        dump_json_file(file_info, output_file)
        return 1, None
    except Exception as e:
        return 0, str(e)

def process_function(function, global_var_list, struct_var_list, inst_id):
    function_blocks = []
    function_calls = set()
    function_vars = set()
    function_globals = set()
    function_structs = set()
    instructions = []
    block_labels = []
    function_param_list = [str(param) for param in function.arguments]

    for block in function.blocks:
        block_data, inst_id = process_block(
            block, 
            global_var_list,
            struct_var_list,
            inst_id,
            function_calls,
            function_vars,
            function_globals,
            function_structs,
            instructions
        )
        if block_data:
            function_blocks.append(block_data)
            block_labels.append(f"%{get_block_label(block)}")

    if not function_blocks:
        return None

    return {
        function.name: {
            "base_info": {
                "function_name": function.name,
                "function_inst_num": len(instructions),
                "function_globals_num": len(function_globals),
                "function_structs_num": len(function_structs),
                "function_blocks_num": len(function_blocks)
            },
            "function_calls": sorted(list(function_calls)),
            "function_vars": sorted(list(function_vars)),
            "block_labels": block_labels,
            "function_instructions": instructions,
            "function_param_list": function_param_list,
            "function_structs": sorted(list(function_structs)),
            "function_globals": sorted(list(function_globals)),
            "function_blocks": function_blocks,
            "last_inst_id": inst_id - 1
        }
    }

def process_block(block, global_var_list, struct_var_list, inst_id, function_calls, function_vars, function_globals,function_structs, instructions):
    block_insts = []
    block_label = get_block_label(block)
    block_var_list = []

    for instruction in block.instructions:
        inst_data = process_instruction(
            instruction, 
            inst_id,
            global_var_list,
            struct_var_list,
            function_calls,
            function_vars,
            function_globals,
            function_structs
        )
        if inst_data:
            block_insts.append(inst_data)
            instructions.append(inst_data["instruction"])
            if "var_name" in inst_data:
                block_var_list.append(inst_data["var_name"])
            inst_id += 1

    if not block_insts:
        return None, inst_id

    return {
        "block_name": f"%{block_label}",
        "block_var_list": block_var_list,
        "inst_num": len(block_insts),
        "block_inst_list": [inst["instruction"] for inst in block_insts],
        "block_insts": block_insts
    }, inst_id

def process_instruction(instruction, inst_id, global_var_list, struct_var_list, function_calls, function_vars, function_globals, function_structs):
    instruction_str = del_debug_info(str(instruction).strip())
    old_instruction_str = instruction_str
    opcode = str(instruction.opcode).strip()
    operands = [str(op).strip() for op in instruction.operands]
    
    # 新增：规范化结构体名称（移除 .数字 后缀）
    normalized_instruction = re.sub(r'%([\w.]+)\.\d+', r'%\1', instruction_str)  # 处理类型名称
    
    # 检测全局变量
    # 去除*号是为了做集合&运算时能匹配到结构体指针
    inst_no_syb = normalized_instruction.replace(',', ' ').replace('*',' ').split()

    vars = re.findall(r'@(?:[\w.]+)', instruction_str)
    # found_globals = {var for var in vars if var in global_var_list}
    set_inst_no_syb = set(inst_no_syb)
    if len(global_var_list) > 0:
        found_globals = set_inst_no_syb & set(global_var_list)
    if len(struct_var_list) > 0:
        found_structs = set_inst_no_syb & set(struct_var_list)

    function_globals.update(found_globals)
    function_structs.update(found_structs)
    
    # 构建指令信息
    inst_info = {
        "inst_id": str(inst_id),
        "instruction": instruction_str,
        "opcode": opcode,
        "operand_list": process_operands(operands, opcode)
    }

    # 变量提取
    if '=' in instruction_str:
        var_name = get_varname(instruction_str)
        inst_info["var_name"] = var_name
        function_vars.add(var_name)

    # 特殊指令处理
    if opcode == "call":
        func_name, return_type = get_called_function_info(operands, instruction_str)
        function_calls.add(func_name)
        inst_info.update({
            "called_function_name": func_name,
            "called_function_return_type": return_type
        })

    elif opcode in ["br", "switch"]:
        labels = re.findall(r'label (%[\w.-]+)', instruction_str)
        condition = operands[0] if len(operands) > 1 else None
        inst_info.update({
            "condition": condition,
            "targets": labels
        })

    elif opcode == "ret":
        inst_info["return_value"] = operands[0] if operands else 'void'

    return inst_info

def process_operands(operands, opcode):
    if opcode in ["ret", "br", "switch"]:
        return []
    return [op for op in operands if not any(kw in op for kw in ['Function Attrs', 'declare', 'define'])]

def process_ir_file_wrapper(args):
    """多进程包装函数"""
    ll_file, output_file, global_info_path, struct_info_path, log_file = args
    try:
        status, error_msg = process_ir_file(ll_file, output_file, global_info_path, struct_info_path)
        return status, error_msg, ll_file
    except Exception as e:
        return 0, str(e), ll_file


def collect_ll_files(proj_root):
    ll_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if file.endswith('.ll'):
                ll_paths.append(full_path)
    
    return ll_paths

def processing_single_proj(proj_path):
    proj_summaries_dir = r'/home/lab314/cjw/similarity/datasets/bin/clang/summary'
    proj_name = os.path.basename(proj_path)
    proj_summaries_path = os.path.join(proj_summaries_dir, proj_name)

    if not os.path.exists(proj_summaries_path):
        os.makedirs(proj_summaries_path)

    # 设置主进程日志
    log_file = os.path.join(proj_summaries_path, 'log.txt')
    # if os.path.exists(log_file):
    #     print(f"Log file {log_file} already exists, skipping project {proj_name}")
    #     return
    
    setup_logger(log_file)
    logging.info(f"Start processing project: {proj_name}")

    # 准备任务参数
    task_args = []
    ll_paths = collect_ll_files(proj_path)
    for ll_path in ll_paths:
        dir_path, file_name = os.path.split(ll_path)

        output_dir, _ = os.path.split(dir_path.replace(r'/clang_ll/', r'/summary/'))

        output_path = os.path.join(output_dir,file_name.replace(".ll", "_info_summary.json"))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        global_dir, _ = os.path.split(dir_path.replace(r'/clang_ll/', r'/global_info/'))
        global_path = os.path.join(global_dir, file_name.replace(".ll", "_globals.json"))

        struct_dir, _ =  os.path.split(dir_path.replace(r'/clang_ll/', r'/struct_info/'))
        struct_path = os.path.join(struct_dir, file_name.replace(".ll", "_structs.json"))

        if all([
                os.path.exists(ll_path),
                os.path.exists(global_path),
                os.path.exists(struct_path),
                not os.path.exists(output_path)
            ]):
                task_args.append((ll_path, output_path, global_path, struct_path, log_file))

    # 跳过超大项目
    # if len(task_args) > 3000:
    #     logging.warning(f"Project {proj_name} has {len(task_args)} tasks, skipping")
    #     continue

    # 使用进程池处理
    with Pool(processes=2) as pool:
        results = pool.imap_unordered(process_ir_file_wrapper, task_args)
        success_count = 0
        with tqdm(total=len(task_args), 
                    desc=f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]Processing {proj_name}",
                    leave=False) as pbar:
            for status, error_msg, ll_file in results:
                if status == 1:
                    success_count += 1
                    logging.info(f"Processed {ll_file} successfully.")
                else:
                    logging.error(f"Error processing {ll_file}: {error_msg}")
                pbar.update(1)

        logging.info(f"Finished project: {proj_name}, Success: {success_count}/{len(task_args)}")
        logging.info("-" * 60)

def summary_bin_ir():
    ll_path = r"/home/lab314/cjw/similarity/datasets/bin/gcc/bin_lls"
    for proj_name in os.listdir(ll_path):
        proj_path = os.path.join(ll_path, proj_name)
        processing_single_proj(proj_path)

if __name__ == "__main__":
    # summary_bin_ir()
    proj_path = r'/home/lab314/cjw/similarity/datasets/bin/clang/clang_ll/MayaPosch_____NymphCast'
    processing_single_proj(proj_path)