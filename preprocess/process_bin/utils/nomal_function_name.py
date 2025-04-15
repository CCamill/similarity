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

def get_varname(instruction):
    return instruction[:instruction.index('=')].strip().replace(" ", "")

def get_common_function_list(function_call_counter_path: str):
    data = load_json_file(function_call_counter_path)
    return data.keys()

def nomal_function(instruction, function_calls, calls_norm_calls_map):
    
    for function_call in function_calls:
        if function_call in common_function_list or function_call.startswith("@llvm."):
            pass
        else:
            instruction = re.sub(function_call, calls_norm_calls_map[function_call], instruction)
    return instruction

def nomalize_function_name(data):
    for function_dict in data:
        _, function = next(iter(function_dict.items()))
        function_calls = function['function_calls']
        calls_norm_calls_map = {call: r"@function_" + str(function_calls.index(call)) for call in function_calls}


        for block in function['function_blocks']:

            for inst in block['block_insts']:
                if inst.get("called_function_name"):
                    called_function_name = inst.get("called_function_name")
                    instruction = inst['instruction']
                    block_index = block['block_inst_list'].index(instruction)
                    fun_index = function['function_instructions'].index(instruction)

                    instruction = nomal_function(instruction, function_calls, calls_norm_calls_map)

                    inst['instruction'] = instruction
                    block['block_inst_list'][block_index] = instruction
                    function['function_instructions'][fun_index] = instruction   

                if len(inst['operand_list']) > 0:
                    for operand in inst['operand_list']:
                        if 'call' in operand or "invoke" in operand:
                            operand_index = inst['operand_list'].index(operand)
                            inst['operand_list'][operand_index] = nomal_function(operand, function_calls, calls_norm_calls_map)
                if inst.get("condition"):
                    condition = inst['condition']
                    if condition:
                        if "call" in condition or "invoke" in condition:
                            inst['condition'] = nomal_function(condition, function_calls, calls_norm_calls_map)
                
                if inst.get("return_value"):
                    return_value = inst['return_value']
                    if return_value:
                        if "call" in return_value or "invoke" in return_value:
                            inst['return_value'] = nomal_function(return_value, function_calls, calls_norm_calls_map)
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
        
        task_args.append((json_path,out_path))
    pbar = tqdm(total=len(task_args))
    for json_path, out_path in task_args:
        out_dir,out_name = os.path.split(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        data = load_json_file(json_path)
        code = nomalize_function_name(data)
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

common_function_list = get_common_function_list(r'/home/lab314/cjw/similarity/datasets/function_call_count_result.json')
if __name__ == '__main__':
    # main()
    processing_single_proj(r'/home/lab314/cjw/similarity/datasets/source/summary/MayaPosch_____NymphCast')