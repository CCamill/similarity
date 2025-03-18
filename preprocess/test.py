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
# from normalize import process_single_proj
# from source_inst_info_summary import processing_single_proj

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

def test1():
    path = r'/home/lab314/cjw/similarity/datasets/source/summary/maxmind_____libmaxminddb'
    out_path = r'/home/lab314/cjw/similarity/datasets/source/norm_summary/maxmind_____libmaxminddb'    
    process_single_proj(path, out_path)

def test2():
    sumy = load_json_file(r'/home/lab314/cjw/similarity/datasets/source/summary/maxmind_____libmaxminddb/-Os/test_info_summary.json')
    for data in sumy:
        target_key = 'instruction'
        target_value = '%13 = tail call i8* @strchr(i8* noundef nonnull %12, i32 noundef 46) #11'
        result= find_dict_with_key_value(data, target_key, target_value)
        print(result)

def test3():
    proj_path = r'/home/lab314/cjw/similarity/datasets/source/source_lls/maxmind_____libmaxminddb'
    processing_single_proj(proj_path)


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

if __name__ == '__main__':
    test6()
    