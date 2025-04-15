#定位操作数在指令中的位置,以便在预训练是做跟操作数预测使用

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
    return instruction[:instruction.index('=')].strip()

def nomalize_operands(data):
    for function_dict in data:
        _, function = next(iter(function_dict.items()))
        function_instructions = function['function_instructions']
        for block in function['function_blocks']:
            for inst in block['block_insts']:
                operand_list = inst['operand_list']
                if inst.get('targets'):
                    operand_list += inst['targets']
                if inst.get('condition'):
                    operand_list += inst['condition']
                if inst.get('return_value'):
                    operand_list += inst['return_value']
                operands = []
                for operand in function_instructions:
                    if operand in function_instructions:
                        operand = get_varname(operand)
                    operands.append(operand)
                inst.update({'operands': operands})
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
        
        task_args.append((json_path,json_path))
    pbar = tqdm(total=len(task_args))
    for json_path, out_path in task_args:
        out_dir,out_name = os.path.split(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        data = load_json_file(json_path)
        code = nomalize_operands(data)
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
    processing_single_proj(r'/home/lab314/cjw/similarity/datasets/source/norm_summary/MayaPosch_____NymphCast')