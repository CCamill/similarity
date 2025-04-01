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

def get_common_const_list(function_const_counter_path: str):
    data = load_json_file(function_const_counter_path)
    return data.keys()

def normal_other_const(input: str):
    if 'inttoptr' in input:
        patt = r'(?:i8|i16|i24|i32|i64)\s+-?\d+\s'
        result = re.search(patt, input)
        if result and result.group().split()[-1] not in common_const_list:
            return input.replace(result.group().strip(), result.group().split()[0] + ' <const>')
    return input

def nomal_const(instruction, function_consts, consts_norm_consts_map):
    for function_const in function_consts:
        if function_const not in common_const_list:
            if f' {function_const}' in instruction:
                instruction = re.sub(f' {function_const}', f' {consts_norm_consts_map[function_const]}', instruction)
            if f'dereferenceable({function_const})' in instruction:
                instruction = instruction.replace(f'dereferenceable({function_const})', f'dereferenceable({consts_norm_consts_map[function_const]})')

            if f'dereferenceable_or_null({function_const})' in instruction:
                instruction = instruction.replace(f'dereferenceable_or_null({function_const})', f'dereferenceable_or_null({consts_norm_consts_map[function_const]})')
    return instruction

def nomalize_consts(data):
    for function_dict in data:
        _, function = next(iter(function_dict.items()))
        function_consts = function['function_consts']
        consts_norm_consts_map = {const: f"<const_{str(function_consts.index(const))}>" for const in function_consts}
        for block in function['function_blocks']:
            for inst in block['block_insts']:
                instruction = inst['instruction']
                block_index = block['block_inst_list'].index(instruction)
                fun_index = function['function_instructions'].index(instruction)

                instruction = normal_other_const(nomal_const(instruction, function_consts, consts_norm_consts_map))

                inst['instruction'] = instruction
                block['block_inst_list'][block_index] = instruction
                function['function_instructions'][fun_index] = instruction   

                if len(inst['operand_list']) > 0:
                    for operand in inst['operand_list']:
                        if re.match(r'^(?:i8|i16|i24|i32|i64)\s+-?\d+$', operand):
                            continue
                        operand_index = inst['operand_list'].index(operand)
                        inst['operand_list'][operand_index] = normal_other_const(nomal_const(operand, function_consts, consts_norm_consts_map))

                if inst.get("condition"):
                    condition = inst['condition']
                    if condition:
                        if "call" in condition or "invoke" in condition:
                            inst['condition'] = normal_other_const(nomal_const(condition, function_consts, consts_norm_consts_map))
                
                if inst.get("return_value"):
                    return_value = inst['return_value']
                    if return_value:
                        if "call" in return_value or "invoke" in return_value:
                            inst['return_value'] = normal_other_const(nomal_const(return_value, function_consts, consts_norm_consts_map))
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
        code = nomalize_consts(data)
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

common_const_list = get_common_const_list(r'/home/lab314/cjw/similarity/datasets/function_const_count_result.json')
if __name__ == '__main__':
    # main()
    processing_single_proj(r'/home/lab314/cjw/similarity/datasets/source/summary/MayaPosch_____NymphCast')