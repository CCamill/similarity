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

def get_function():
    summary_dir = 'E:\Desktop\similarity\datasets\summary_files'
    summary_files = [os.path.join(summary_dir, summary_file) for summary_file in os.listdir(summary_dir)]
    for summary_file in summary_files:
        data = load_json_file(summary_file)
        for function in data:
            yield function['function_instructions']

def normalize_label(inst):
    pass

def normal_struct(input):
    return re.sub(r'%([\w.]+)\.\d+', r'%\1', input)

def del_debug_info(inst):
    if '!insn.addr' in inst:
        idx = inst.index('!insn.addr') - 2
        inst = inst[:idx]
    if '!tbaa'  in inst:
        idx = inst.index('!tbaa') - 2
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

def nomalize_instruction(inst:dict,
                        instruction: str,
                        function_globals: list, 
                        function_structs: list, 
                        block_labels: list, 
                        label_norm_label_map: dict,
                        global_norm_global_map: dict,
                        struct_norm_struct_map:  dict,
                        calls_norm_calls_map: dict
                        ):
    labels = set(block_labels) & set(instruction.replace(',',' ').split())
    if labels:
        for label in labels:
            list_instruction = instruction.replace(',',' ,').replace(')',' )').replace('(','( ').split()
            indexs = [index for index, value in enumerate(list_instruction) if value == label]
            for index in indexs:
                list_instruction[index] = label_norm_label_map[label]
            instruction = ' '.join(list_instruction)
    
    globals = set(instruction.replace(',',' ').split()) & set(function_globals)
    if globals:
        for global_var in globals:
            instruction = re.sub(global_var, global_norm_global_map[global_var], instruction)

    structs = set(instruction.replace(',', ' ').replace('*',' ').replace(']',' ').split()) & set(function_structs)
    if structs:
        for struct in structs:
            instruction = re.sub(struct, struct_norm_struct_map[struct], instruction)
    
    # 如果是函数调用指令，则将指令中的函数名标准化
    if inst.get('called_function_name'):
        called_function_name = inst['called_function_name']
        if not called_function_name.startswith('@llvm.'):
            instruction = re.sub(called_function_name, calls_norm_calls_map[called_function_name], instruction)

    if inst['opcode'] in ['br', 'switch']:
        # 将跳转指令中类似于i32 123的常量替换为 i32 <const>
        instruction = re.sub(r'(i8|i32|i24|i64|i16)\s+(\d+)', replace_func, instruction)
    
    return normal_struct(del_debug_info(instruction))

def find_dict_with_key_value(data, target_key, target_value):
    """
    在多级字典中查找包含目标键值对的字典
    :param data: 多级字典
    :param target_key: 目标键
    :param target_value: 目标值
    :return: 包含目标键值对的字典，如果未找到则返回 None
    """
    # 如果当前字典包含目标键值对，返回当前字典
    if isinstance(data, dict):
        if target_key in data and data[target_key] == target_value:
            return data

        # 遍历字典的值，递归查找
        for key, value in data.items():
            if isinstance(value, dict):  # 如果值是字典，递归查找
                result = find_dict_with_key_value(value, target_key, target_value)
                if result is not None:
                    return result
            elif isinstance(value, list):  # 如果值是列表，遍历列表中的字典
                for item in value:
                    if isinstance(item, dict):
                        result = find_dict_with_key_value(item, target_key, target_value)
                        if result is not None:
                            return result

    return None  # 未找到目标键值对

def nomalize_files(data):
    for function_dict in data:
        function_name, function = next(iter(function_dict.items()))
        raw_function_info = copy.deepcopy(function)

        # 对参数列表中的结构体参数正则化
        function_param_list = function['function_param_list']
        for function_param in  function_param_list:
            index = function['function_param_list'].index(function_param)
            function_param = re.sub(r'%([\w.]+)\.\d+', r'%\1', function_param)
            function['function_param_list'][index] =  function_param

        block_labels = function['block_labels']
        label_norm_label_map = {label: r"%block_"+ str(block_labels.index(label)) for label in block_labels}

        function_globals = function['function_globals']
        global_norm_global_map = {global_var: r"%global_var_" + str(function_globals.index(global_var)) for global_var in function_globals}

        function_structs =  function['function_structs']
        struct_norm_struct_map = {struct: r"%struct_" + str(function_structs.index(struct)) for struct in function_structs}

        function_calls = function['function_calls']
        calls_norm_calls_map = {call: r"@function_" + str(function_calls.index(call)) for call in function_calls}

        function_instructions = function['function_instructions']

        for block in function['function_blocks']:
            raw_block_info = copy.deepcopy(block)
            blocl_name = block['block_name']
            block['block_name'] = "%block_"

            for inst in block['block_insts']:
                instruction = inst['instruction']
                old_inst = instruction
                instruction = nomalize_instruction(inst=inst,
                                                   instruction = instruction,
                                                   function_globals=function_globals,
                                                   function_structs=function_structs,
                                                   block_labels=block_labels,
                                                   label_norm_label_map=label_norm_label_map,
                                                   global_norm_global_map=global_norm_global_map,
                                                   struct_norm_struct_map=struct_norm_struct_map,
                                                   calls_norm_calls_map=calls_norm_calls_map)
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

                # 处理参数列表
                if inst.get('operand_list'):
                    for operand in inst['operand_list']:
                        index = inst['operand_list'].index(operand)
                        operand = normal_struct(operand)  # 去除结构体变量的数字后缀(如果参数中由结构体变量的话)
                        
                        #如果该参数是一条指令，则按照指令的方式处理
                        if operand in raw_function_info['function_instructions']:
                            # 新增：规范化结构体名称（移除 .数字 后缀）
                            operand = re.sub(r'%([\w.]+)\.\d+', r'%\1', operand)  # 处理类型名称
                            # 根据键值对在block字典中找出该指令的字典
                            operand_inst = find_dict_with_key_value(raw_block_info,"instruction",operand)
                            if operand_inst == None:
                                # 如果没有在block字典中找到该指令的字典，则根据键值对在function字典中中找出该指令的字典
                                operand_inst = find_dict_with_key_value(raw_function_info,"instruction",operand)
                            if operand_inst == None:
                                return 0
                            operand = nomalize_instruction( inst = operand_inst,
                                                            instruction= operand,
                                                            function_globals=function_globals,
                                                            function_structs=function_structs,
                                                            block_labels=block_labels,
                                                            label_norm_label_map=label_norm_label_map,
                                                            global_norm_global_map=global_norm_global_map,
                                                            struct_norm_struct_map=struct_norm_struct_map,
                                                            calls_norm_calls_map=calls_norm_calls_map)
                        # 如果 operand 不是一条指令
                        else:
                            # 如果operand是跳转标签，则将operand中的标签正则化
                            labels = set(block_labels) & set(operand.replace(',',' ').split())
                            if labels:
                                for label in labels:
                                    operand = re.sub(label, label_norm_label_map[label], operand)

                            # 如果operand包含结构体，则将operand中的结构体正则化
                            structs = set(operand.replace(',', ' ').replace('*',' ').replace(']',' ').split()) & set(function_structs)
                            for struct in structs:
                                operand = struct
                        
                            # 如果operand包含全局变量，则将operand替换为全局变量名
                            globals = set(operand.replace(',',' ').split()) & set(function_globals)
                            if globals:
                                for global_var in globals:
                                    operand = global_var
                            inst['operand_list'][index] = operand

                block_index = block['block_inst_list'].index(old_inst)
                block['block_inst_list'][block_index] = instruction

                fun_index = function['function_instructions'].index(old_inst)
                function['function_instructions'][fun_index] = instruction   

                inst['instruction'] = instruction
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
        dir_path, file_name = os.path.split(json_path)

        output_dir = dir_path.replace(r'/summary/', r'/norm_summary/')
        output_path = os.path.join(output_dir,file_name.replace("_info_summary.json", "_info_summary_normalized.json"))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if all([
                os.path.exists(json_path),
                not os.path.exists(output_path)
            ]):
                task_args.append((json_path, output_path))
    pbar = tqdm(total=len(task_args))
    for  json_path, output_path in task_args:
        data = load_json_file(json_path)
        code = nomalize_files(data)
        if code == 0:
            print(json_path)
        if code:
            dump_json_file(data, output_path)
        pbar.update(1)
    pbar.close()
def main():
    proj_summaries_dir = r'/home/lab314/cjw/similarity/datasets/source/summary'
    for proj in os.listdir(proj_summaries_dir):
        proj_path = os.path.join(proj_summaries_dir, proj)
        processing_single_proj(proj_path)
if __name__ == '__main__':
    # main()
    processing_single_proj(r'/home/lab314/cjw/similarity/datasets/source/summary/MayaPosch_____NymphCast')