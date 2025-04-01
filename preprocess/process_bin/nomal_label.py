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

def normal_struct(input):
    if '"' in input:
        input = input.replace('"','')
    return re.sub(r'%([\w:<>.]+)\.\d+', r'%\1', input)

def advanced_replace(s, pattern=r'[(),*\]\[\]<>]', replacement=' '):
    """使用正则表达式处理替换"""
    return re.sub(pattern, replacement, s).split()

def nomal_label(instruction,block_labels,label_norm_label_map):
    labels = set(block_labels) & set(advanced_replace(instruction))
    if labels:
        for label in labels:
            instruction = re.sub(label, label_norm_label_map[label], instruction)
    return instruction


def nomalize_label(data):
    for function_dict in data:
        _, function = next(iter(function_dict.items()))
        raw_function_info = copy.deepcopy(function)

        block_labels = function['block_labels']
        label_norm_label_map = {label: r"%label_" + str(block_labels.index(label)) for label in block_labels}
        normal_block_labels = list(label_norm_label_map.values())

        for block in function['function_blocks']:
            block['block_name'] = label_norm_label_map[block['block_name']]
            for inst in block['block_insts']:
                instruction = inst['instruction']
                old_inst = instruction
                instruction = nomal_label(instruction = instruction, block_labels=block_labels, label_norm_label_map=label_norm_label_map,)
                
                block_index = block['block_inst_list'].index(old_inst)
                block['block_inst_list'][block_index] = instruction

                fun_index = function['function_instructions'].index(old_inst)
                function['function_instructions'][fun_index] = instruction   

                inst['instruction'] = instruction

                if inst.get('condition'):
                    condition = inst['condition']
                    inst['condition'] = nomal_label(condition, block_labels, label_norm_label_map)
                
                if inst.get('return_value'):
                    return_value = inst['return_value']
                    inst['return_value'] = nomal_label(return_value, block_labels, label_norm_label_map)
                
                if inst.get('targets'):
                    targets = inst['targets']
                    for target in targets:
                        idx = targets.index(target)
                        inst['targets'][idx] = label_norm_label_map[target]

                # 处理参数列表
                if inst.get('operand_list'):
                    for operand in inst['operand_list']:
                        index = inst['operand_list'].index(operand)
                        operand = normal_struct(operand)  # 去除结构体变量的数字后缀(如果参数中有结构体变量的话)
                        #如果该参数是一条指令，则按照指令的方式处理
                        operand = nomal_label(instruction= operand, block_labels=block_labels, label_norm_label_map=label_norm_label_map,)

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
        
        task_args.append((json_path,out_path))
    pbar = tqdm(total=len(task_args))
    for json_path, out_path in task_args:
        out_dir,out_name = os.path.split(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        data = load_json_file(json_path)
        code = nomalize_label(data)
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