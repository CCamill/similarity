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
import copy

LLVM_OPCODES = {
    # Terminator Instructions（终止指令）
    'ret', 'br', 'switch', 'indirectbr', 'invoke', 'resume', 
    'catchswitch', 'catchret', 'cleanupret', 'unreachable',

    # Binary Operations（二元运算）
    'add', 'fadd', 'sub', 'fsub', 'mul', 'fmul', 
    'udiv', 'sdiv', 'fdiv', 'urem', 'srem', 'frem',

    # Bitwise Binary Operations（位运算）
    'shl', 'lshr', 'ashr', 'and', 'or', 'xor',

    # Vector Operations（向量运算）
    'extractelement', 'insertelement', 'shufflevector',

    # Aggregate Operations（聚合操作）
    'extractvalue', 'insertvalue',

    # Memory Access and Addressing（内存访问与寻址）
    'alloca', 'load', 'store', 'fence', 'cmpxchg', 'atomicrmw',
    'getelementptr',  # GEP（指针计算）

    # Conversion Operations（类型转换）
    'trunc', 'zext', 'sext', 'fptrunc', 'fpext', 
    'fptoui', 'fptosi', 'uitofp', 'sitofp', 
    'ptrtoint', 'inttoptr', 'bitcast', 'addrspacecast',

    # Other Operations（其他操作）
    'icmp', 'fcmp', 'phi', 'select', 'call', 
    'va_arg', 'landingpad', 'catchpad', 'cleanuppad',

    # Special Instructions（特殊指令）
    'freeze',  # (LLVM 10+)
}

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))


paths = []

def traverse_directory(path):
    # 列出当前目录下的所有文件和目录
    items = os.listdir(path)
    
    # 遍历当前目录下的所有项
    for item in items:
        item_path = os.path.join(path, item)
        
        # 如果是目录，递归遍历
        if os.path.isdir(item_path):
            # print(f"Directory: {item_path}")
            paths.append(item_path)
            traverse_directory(item_path)
        # 如果是文件，打印文件路径
        elif os.path.isfile(item_path):
            pass



def main():
    traverse_directory('/home/lab314/cjw/similarity/datasets/binary_info/VitaSmith_____cdecrypt')
    binary_info_path = r'/home/lab314/cjw/similarity/datasets/binary_info/'
    for path in paths:
        basename = os.path.basename(path)
        new_path = os.path.join(binary_info_path, basename)
        os.rename(path, new_path)
        print(r'succeed move file: ', basename)
    
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

def test2():
    sumy = load_json_file(r'/home/lab314/cjw/similarity/datasets/source/summary/maxmind_____libmaxminddb/-Os/test_info_summary.json')
    for data in sumy:
        target_key = 'instruction'
        target_value = '%13 = tail call i8* @strchr(i8* noundef nonnull %12, i32 noundef 46) #11'
        result= find_dict_with_key_value(data, target_key, target_value)
        print(result)


def test4():
    global_dir = r'/home/lab314/cjw/similarity/datasets/source/global_info'
    for proj in os.listdir(global_dir):
        proj_root = os.path.join(global_dir, proj)
        files = []
        for root, dirs, files in os.walk(proj_root):
            for file in files:
                full_path = os.path.join(root, file)

                if file.endswith('.json'):
                    files.append(full_path)
        
        print("start processing project: ", proj)
        print("num of jsons: ",len(files))
        pbar =  tqdm(total=len(files))
        for full_path in  files:
            # dir_name, file_name =  os.path.split(full_path)
            # dir_name.replace('/global_info', '/norm_global_info')
            # out_path = os.path.join(dir_name, file_name)
            data = load_json_file(full_path)
            new_data = {"@" + key: value for key, value in data.items() if not key.startswith('@')}
            dump_json_file(new_data, full_path)
            pbar.update(1)
        pbar.close()
    
def test5():
    data = load_json_file(r"/home/lab314/cjw/similarity/preprocess/struct_info.json")
    nums = len(data.keys())
    print(nums)
def test6():
    input_path = r'/home/lab314/cjw/similarity/preprocess/afjck.ll'
    output_path = r'/home/lab314/cjw/similarity/preprocess/afjck_global_info1.json'
    cmd_list = [
        "/home/lab314/cjw/similarity/preprocess/ex_global",
        input_path,
        output_path
    ]
    cmd =  " ".join(cmd_list)
    proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=150)
    code = proc.returncode
    print(code)
def test1():
    instruction_str = "%5 = alloca %class.asCString.2199, align 8"
    normalized_instruction = re.sub(r'%([\w.]+)\.\d+', r'%\1', instruction_str)
    print(normalized_instruction)

def replace_func(match):
    type_part = match.group(1)  # 类型部分（i8、i32等）
    number_part = match.group(2)  # 数字部分
    return f"{type_part} <const>"
def test3():
    instruction = r'br i1 %18 , label %block_3 , label %block_4"'
    instruction = re.sub(r'(i8|i32|i24|i64|i16)\s+(\d+)', replace_func, instruction)
    print(instruction)

def collect_json_files(proj_root):
    json_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if file.endswith('.json'):
                json_paths.append(full_path)
    
    return json_paths

from collections import Counter
def fun_call_num():
    # 统计函数的调用次数

    summary_root = r'/home/lab314/cjw/similarity/datasets/source/summary_no_global'
    pbar =  tqdm(total=len(os.listdir(summary_root)))
    all_function = []
    for proj in os.listdir(summary_root):
        proj_root = os.path.join(summary_root, proj)
        json_paths = collect_json_files(proj_root)
        for json_path in json_paths:
            try: 
                data = load_json_file(json_path)
            except Exception as e:
                print(f"{json_path} error {e}")
                continue
            for function_dict in data:
                function_name, function = next(iter(function_dict.items()))
                function_calls = function['function_calls']
                all_function += function_calls
        pbar.update(1)
    pbar.close()
    count = Counter(all_function)
    count_dict = dict(count)
    sorted_count_dict = dict(sorted(count_dict.items(), key=lambda item: item[1], reverse=True))
    with open('/home/lab314/cjw/similarity/datasets/function_call_count_result.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_count_dict, f, ensure_ascii=False, indent=4)
    
    print("统计结果已写入 function_call_count_result.json 文件")

def test4():
    inst = '%3 = bitcast %"class.litehtml::el_body"* %0 to %"class.litehtml::html_tag.23463"*'
    if '"' in inst:
        inst = inst.replace('"','')
    print(inst)

import re
def test5():
    consts = set()
    str = r"i32 1819239276"
    pattern = r'^(?:i8|i16|i24|i32|i64)\s+(-?\d+)$'
    match = re.search(pattern,str)
    if match:
        const = match.group(1)
        consts.add(const)
    print(consts)

def fun_const_num():
    # 统计函数的调用次数

    summary_root = r'/home/lab314/cjw/similarity/datasets/source/summary'
    pbar =  tqdm(total=len(os.listdir(summary_root)))
    all_const = []
    for proj in os.listdir(summary_root):
        proj_root = os.path.join(summary_root, proj)
        json_paths = collect_json_files(proj_root)
        for json_path in json_paths:
            try: 
                data = load_json_file(json_path)
            except Exception as e:
                print(f"{json_path} error {e}")
                continue
            for function_dict in data:
                function_name, function = next(iter(function_dict.items()))
                function_consts = function['function_consts']
                all_const += function_consts
        pbar.update(1)
    pbar.close()
    count = Counter(all_const)
    count_dict = dict(count)
    sorted_count_dict = dict(sorted(count_dict.items(), key=lambda item: item[1], reverse=True))
    with open('/home/lab314/cjw/similarity/datasets/function_const_count_result.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_count_dict, f, ensure_ascii=False, indent=4)
    
    print("统计结果已写入 function_const_count_result.json 文件")

def test6():
    struct_pattern = r'%([\w:.]+\.\d+)'
    instruction = r'%76 = getelementptr inbounds %class.std::__1::allocator.100, %class.std::__1::allocator.100* %3, i64 0, i32 0'
    matches = re.findall(struct_pattern, instruction)
    print(matches)

def normal_struct(input):
    if '"' in input:
        input = input.replace('"','')
    return re.sub(r'%([\w:.]+)\.\d+', r'%\1', input)

def test7():
    operand = r'%76 = getelementptr inbounds %class.std::__1::allocator, %class.std::__1::allocator.100* %3, i64 0, i32 0'
    deepcopy_operand = copy.deepcopy(operand)
    old_operand = operand
    operand = normal_struct(operand)
    print("operand         : ", operand)
    print("deepcopy_operand: ", deepcopy_operand)
    print("old_operand     : ",old_operand)

def test8():
    operand_list=[
                "%23 = getelementptr inbounds %struct.hb_face_t.735, %struct.hb_face_t.735* %11, i64 0, i32 8, i32 24, i32 0",
                "%struct.hb_face_t.735* %11"
              ]
    normal_operand_list = []
    for operand in operand_list:
        if set(operand.split()) & LLVM_OPCODES:
            normal_operand_list.append(normal_struct(operand))
        else:
            normal_operand_list.append(operand)
    print(normal_operand_list)

def del_debug_info(inst):
    index = inst.find('!') - 2
    inst =  inst[:index]
    return inst

def test9():
    inst = del_debug_info("%95 = load i32, i32* %94, align 8, !tbaa !65, !noalias !54")
    print(inst)

def advanced_replace(s, pattern=r'[(),*\]\[\]<>]', replacement=' '):
    """使用正则表达式处理替换"""
    return re.sub(pattern, replacement, s).split()

def test10(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    # 调试：检查嵌套集合
    def check_nested(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, (list, dict)) and any(isinstance(i, (list, dict)) for i in (v.values() if isinstance(v, dict) else v)):
                    raise ValueError(f"Nested collection in {obj}")
                check_nested(v)
        elif isinstance(obj, list):
            for i in obj:
                check_nested(i)
    check_nested(data)  # 触发异常
    return data

if __name__ == '__main__':
    test10(r'/home/lab314/cjw/similarity/datasets/source/norm_summary/MayaPosch_____NymphCast/-Os/box_info_summary.json')
    