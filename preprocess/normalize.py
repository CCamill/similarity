import re
import os
import json
import time
from tqdm import tqdm

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))

def get_function():
    summary_dir = 'E:\Desktop\similarity\datasets\summary_files'
    summary_files = [os.path.join(summary_dir, summary_file) for summary_file in os.listdir(summary_dir)]
    for summary_file in summary_files:
        data = load_json_file(summary_file)
        for function in data:
            yield function['function_instructions']

def normalize_label(inst):
    pass

def del_debug_info(inst):
    if '!insn.addr' in inst:
        idx = inst.index('!insn.addr') - 2
        inst = inst[:idx]
    return inst

def normalize_global_variable(inst,function_globals):
    globals = set(inst.replace(',',' ').split()) & set(function_globals)
    if globals:
        for global_var in globals:
            index = function_globals.index(global_var)
            inst = re.sub(global_var, r'%global_var_' + str(index), inst)
    return inst

def replace_func(match):
    type_part = match.group(1)  # 类型部分（i8、i32等）
    number_part = match.group(2)  # 数字部分
    return f"{type_part} <const>"

def normalize_const(operand, instruction):
    patt = r'(?:i8|i16|i24|i32|i64)\s+-?\d+'
    has_const = re.search(patt, operand)
    if has_const:
        result = re.findall(patt, operand).pop()
        type_part = result.split(' ')[0]
        number_part = result.split(' ')[1]
        if number_part == '1048576':
            pass
        list_instruction = instruction.replace(',',' ,').replace(')',' )').replace('(','( ').split()
        if number_part not in ['0', '1', '8'] and number_part in list_instruction:
            indexs = [index for index, value in enumerate(list_instruction) if value == number_part]
            for index in indexs:
                index = list_instruction.index(number_part)
                list_instruction[index] = "<const>"
            instruction = ' '.join(list_instruction)
    return instruction

def nomalize_files(data):
    for function_dict in data:
        function_name, function = next(iter(function_dict.items()))
        block_labels = function['block_labels']
        label_norm_label_map = {label: r"%block_"+ str(block_labels.index(label)) for label in block_labels}
        function_globals = function['function_globals']
        global_norm_global_map = {global_var: r"%global_var_" + str(function_globals.index(global_var)) for global_var in function_globals}
        function_calls = function['function_calls']
        calls_norm_calls_map = {call: r"@function_" + str(function_calls.index(call)) for call in function_calls}
        for block in function['function_blocks']:
            blocl_name = block['block_name']
            block['block_name'] = label_norm_label_map[blocl_name]

            for inst in block['block_insts']:
                instruction = inst['instruction']
                old_inst = instruction
                labels = set(block_labels) & set(instruction.replace(',',' ').split())
                if labels:
                    for label in labels:
                        list_instruction = instruction.replace(',',' ,').replace(')',' )').replace('(','( ').split()
                        indexs = [index for index, value in enumerate(list_instruction) if value == label]
                        for index in indexs:
                            list_instruction[index] = label_norm_label_map[label]
                        instruction = ' '.join(list_instruction)
                        """ pattern = re.escape(label)
                        instruction = re.sub(pattern, label_norm_label_map[label], instruction) """
                globals = set(instruction.replace(',',' ').split()) & set(function_globals)
                if globals:
                    for global_var in globals:
                        instruction = re.sub(global_var, global_norm_global_map[global_var], instruction)

                if inst.get('operand_list'):
                    for operand in inst['operand_list']:
                        labels = set(block_labels) & set(operand.replace(',',' ').split())
                        globals = set(operand.replace(',',' ').split()) & set(function_globals)
                        functions = set(operand.replace('(',' ').split()) & set(function_calls)
                        old_operand = operand   
                        index = inst['operand_list'].index(old_operand)
                        # 如果operand是跳转标签，则将operand中的标签正则化
                        if labels:
                            for label in labels:
                                operand = re.sub(label, label_norm_label_map[label], operand)
                        # 如果operand是全局变量调用指令，则将operand替换为全局变量名
                        if globals:
                            for global_var in globals:
                                operand = global_var
                        # 如果是函数调用指令，则将operand中的函数名正则化
                        if functions:
                            for function in functions:
                                operand = re.sub(function, calls_norm_calls_map[function], operand)
                        inst['operand_list'][index] = del_debug_info(operand)
                        instruction = normalize_const(operand, instruction)

                if inst['opcode'] in ['br', 'switch']:
                    instruction = re.sub(r'(i8|i32|i24|i64|i16)\s+(\d+)', replace_func, instruction)
                if inst.get('targets'):
                    for target in inst['targets']:
                        index = inst['targets'].index(target)
                        inst['targets'][index] = label_norm_label_map[target]
                if inst.get('condition'):
                    condition = del_debug_info(inst['condition'])
                    labels = set(block_labels) & set(condition.replace(',',' ').split())
                    if labels:
                        for label in labels:
                            condition = re.sub(label, label_norm_label_map[label], inst['condition'])
                    inst['condition'] = condition
                
                if inst.get('called_function_name'):
                    called_function_name = inst['called_function_name']
                    index = function['function_calls'].index(called_function_name)
                    instruction = re.sub(called_function_name, calls_norm_calls_map[called_function_name], instruction)

                block_index = block['block_inst_list'].index(old_inst)
                block['block_inst_list'][block_index] = instruction
                fun_index = function['function_instructions'].index(old_inst)
                function['function_instructions'][fun_index] = instruction   
                inst['instruction'] = instruction

def path_process(input_dir, output_dir):
    for proj_name in os.listdir(input_dir):
        proj_summaries_path = os.path.join(input_dir, proj_name)    # similarity/datasets/summary_files/32blit_____32blit-sdk
        if not os.path.exists(os.path.join(proj_summaries_path, '-O0')) or len(os.listdir(os.path.join(proj_summaries_path, '-O0'))) == 0:
            continue
        proj_nomr_smry_path = os.path.join(output_dir, proj_name)   # similarity/datasets/normalize_files/32blit_____32blit-sdk
        if os.path.exists(proj_nomr_smry_path):
            # print(f"{proj_name} has already been processed...")
            # continue
            pass
        else:
            os.makedirs(proj_nomr_smry_path)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Normalizing {proj_name}...")
        
        nums = len(os.listdir(os.path.join(proj_summaries_path, '-O0')))
        pbar = tqdm(total=nums)

        for opti in os.listdir(proj_summaries_path):
            proj_nomr_smry_opti_path = os.path.join(proj_nomr_smry_path, opti)    # similarity/datasets/normalize_files/32blit_____32blit-sdk/O1
            proj_summaries_opti_path = os.path.join(proj_summaries_path, opti)    # similarity/datasets/summary_files/32blit_____32blit-sdk/O1
            if not os.path.exists(proj_nomr_smry_opti_path):
                os.makedirs(proj_nomr_smry_opti_path)
            for _file in os.listdir(proj_summaries_opti_path):
                if _file.endswith('.json'):
                    input_file = os.path.join(proj_summaries_opti_path, _file)
                    output_file = os.path.join(proj_nomr_smry_opti_path, _file.replace('.json', '_normalized.json'))
                    if os.path.exists(output_file):
                        pbar.update(1)
                        continue
                    data = load_json_file(input_file)
                    nomalize_files(data)
                    dump_json_file(data, output_file)
                    pbar.update(1)
        pbar.close()


if __name__ == '__main__':
    proj_summaries_dir = r'/home/lab314/cjw/similarity/datasets/source/summary'
    proj_nomr_smry_dir = r'/home/lab314/cjw/similarity/datasets/source/norm_summary'
    path_process(proj_summaries_dir, proj_nomr_smry_dir)