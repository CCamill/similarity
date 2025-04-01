import re
import os
import json
import time
import copy
from tqdm import tqdm

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))

def advanced_replace(s, pattern=r'[(),*\]\[\]<>]', replacement=' '):
    """使用正则表达式处理替换"""
    return re.sub(pattern, replacement, s).split()

def nomal_var(instruction,function_vars,var_norm_var_map, function_param_list, param_norm_param_map):
    vars = set(function_vars) & set(advanced_replace(instruction))
    if vars:
        for var in vars:
            instruction = re.sub(var, var_norm_var_map[var], instruction)
    params = set(function_param_list) & set(advanced_replace(instruction))
    if params:
        for param in params:
            instruction = re.sub(param, param_norm_param_map[param], instruction)
    return instruction



def nomalize_var(data):
    for function_dict in data:
        _, function = next(iter(function_dict.items()))
        raw_function_info = copy.deepcopy(function)

        function_vars = function['function_vars']
        var_norm_var_map = {var: r"%var" + str(function_vars.index(var)) for var in function_vars}
        function_param_list = function['function_param_list']
        param_norm_param_map = {param: r"%arg" + str(function_param_list.index(param) + 1) for param in function_param_list}
        function['function_param_list'] = list(param_norm_param_map.values())
        for block in function['function_blocks']:
            for inst in block['block_insts']:
                instruction = inst['instruction']
                old_inst = instruction
                instruction = nomal_var(instruction = instruction, function_vars=function_vars, var_norm_var_map=var_norm_var_map, function_param_list = function_param_list, param_norm_param_map = param_norm_param_map)
                
                block_index = block['block_inst_list'].index(old_inst)
                block['block_inst_list'][block_index] = instruction

                fun_index = function['function_instructions'].index(old_inst)
                function['function_instructions'][fun_index] = instruction   

                inst['instruction'] = instruction

                if inst.get('condition'):
                    condition = inst['condition']
                    inst['condition'] = nomal_var(condition, function_vars=function_vars, var_norm_var_map=var_norm_var_map, function_param_list = function_param_list, param_norm_param_map = param_norm_param_map)
                
                if inst.get('return_value'):
                    return_value = inst['return_value']
                    inst['return_value'] = nomal_var(return_value, function_vars=function_vars, var_norm_var_map=var_norm_var_map, function_param_list = function_param_list, param_norm_param_map = param_norm_param_map)

                # 处理参数列表
                if inst.get('operand_list'):
                    for operand in inst['operand_list']:
                        if operand == r"%rdi.reg2mem = alloca i64, align 8":
                            pass
                        index = inst['operand_list'].index(operand)
                        #如果该参数是一条指令，则按照指令的方式处理
                        operand = nomal_var(instruction= operand, function_vars=function_vars, var_norm_var_map=var_norm_var_map, function_param_list = function_param_list, param_norm_param_map = param_norm_param_map)
                        inst['operand_list'][index] = operand
    return 1

def collect_json_files(proj_root):
    json_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if file.endswith('.json'):
                json_paths.append(full_path)
    
    return json_paths

def processing_single_proj(proj_path):
    task_args = []
    json_paths = collect_json_files(proj_path)
    for json_path in json_paths:
        out_path = json_path.replace('/summary/','/norm_summary/')
        
        # if os.path.exists(out_path):
        #     continue
        task_args.append((json_path,out_path))
    pbar = tqdm(total=len(task_args))
    for json_path, out_path in task_args:
        out_dir,out_name = os.path.split(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        data = load_json_file(json_path)
        code = nomalize_var(data)
        if code == 0:
            print("error",json_path)
        if code:
            dump_json_file(data, out_path)
        pbar.update(1)
    pbar.close()

def main():
    proj_summaries_dir = r'/home/lab314/cjw/similarity/datasets/source/summary'
    for proj in os.listdir(proj_summaries_dir):
        proj_path = os.path.join(proj_summaries_dir, proj)
        processing_single_proj(proj_path)
if __name__ == '__main__':
    # main()
    processing_single_proj(r'/home/lab314/cjw/similarity/datasets/bin/clang/summary/MayaPosch_____NymphCast')