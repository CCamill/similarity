from collections import defaultdict
import os
import llvmlite.ir as ir
import llvmlite.binding as llvm
import re
import json
import argparse


def generate_llvm_ir(input_file):
    # 从输入文件读取 LLVM IR
    with open(input_file, 'r') as f:
        llvm_ir = f.read()

    # 打印读取的 LLVM IR
    # print("Read LLVM IR from file:")

    return llvm_ir

def get_global_var_info(global_var):
    linkages = ['external', 'internal', 'available_externally', 'private','linkonce', 'weak', 'weak_odr', 'linkonce_odr']
    visibilities = ['default', 'hidden', 'protected']
    addressing_modes = ['local_unnamed_addr','unnamed_addr']
    # 获取全局变量的信息
    info = {}
    info.setdefault('define',global_var)
    linkage_flag = False
    for linkage in linkages:
        if linkage in global_var:
            info.setdefault('linkage', linkage)
            linkage_flag = True
    if not linkage_flag:
        info.setdefault('linkage', None)
    
    visibility_flag = False
    for visibility in visibilities:
        if visibility in global_var:
            info.setdefault('visibility', visibility)
            visibility_flag = True
    if not visibility_flag:
        info.setdefault('visibility', None)
    
    addressing_mode_flag = False
    for addressing_mode in addressing_modes:
        if addressing_mode in global_var:
            info.setdefault('addressing_mode', addressing_mode)
            addressing_mode_flag = True
    if not addressing_mode_flag:
        info.setdefault('addressing_mode', None)
    

    var_start_idx = global_var.index('@')
    var_end_idx = global_var.index('=')
    var_name = global_var[var_start_idx:var_end_idx].strip()
    info.setdefault('var_name', var_name)
    var_list.append(var_name)

    # 字符串
    string_matcher = r'((constant|global|internal) \[[\d]+ x i[\d]+\] c)'          #[25 x i8]
    string_match = re.search(string_matcher, global_var)
    if string_match:
        info.setdefault('type_field', 'string')
        string_len = string_match.group(0)
        info.setdefault('value_size', string_len)
        string_start_idx = global_var.index('c"')+2
        string_end_idx = global_var.find('00"')+2
        global_value = global_var[string_start_idx:string_end_idx]
        info.setdefault('global_value', global_value)

        return info

    # 整型
    int_matcher = r'(constant|global|internal) i(1|8|16|32|64|128)\s+(\d*|-\d*)'
    int_match = re.search(int_matcher, global_var)
    if int_match:
        info.setdefault('type_field', 'int')
        int_size = int_match.group(2)
        info.setdefault('value_size', int_size)
        if info['linkage'] == 'external':
            info.setdefault('global_value', None)
        else:
            global_value = int_match.group(3)
            info.setdefault('global_value', global_value)
    
    # float
    float_matcher = r'float\s+((0x[0-9a-fA-F]+(\.[0-9a-fA-F]+)?([pP][+-]?\d+)?)|([-+]?\d*\.\d+|\d+)([eE][-+]?\d+)?)'
    float_match = re.search(float_matcher, global_var)
    if float_match:
        info.setdefault('type_field', 'float')
        float_value = float_match.group(1)
        info.setdefault('global_value', float_value)
        info.setdefault('value_size', "32")
    
    # double
    double_matcher = r'double\s+((0x[0-9a-fA-F]+(\.[0-9a-fA-F]+)?([pP][+-]?\d+)?)|([-+]?\d*\.\d+|\d+)([eE][-+]?\d+)?)'
    double_match = re.search(double_matcher, global_var)
    if double_match:
        info.setdefault('type_field', 'double')
        double_value = double_match.group(1)
        info.setdefault('global_value', double_value)
        info.setdefault('value_size', "64")
    
    # 指针数组
    string_ptr_matcher = r'(((constant|global|internal) \[[\d]+ x i[\d]+\*\] ))'    #[25 x i8*]
    string_ptr_match = re.search(string_ptr_matcher, global_var)
    if string_ptr_match:
        ptr_array = []
        info.setdefault('type_field', 'ptr_array')
        for var in var_list:
            if var in global_var:
                ptr_array.append(var)
        info.setdefault('ptr_array', ptr_array)
        info.setdefault('global_value', None)
    
    # 数组指针
    array_ptr = r"((constant|global|internal) \[[\d]+ x i[\d]+\]\* \@)"
    array_ptr_match = re.search(array_ptr, global_var)
    if array_ptr_match:
        info.setdefault('type_field', 'array_ptr')
        for var in var_list:
            if var in global_var:
                info.setdefault('array_ptr', var)
        info.setdefault('global_value', None)
    
    if 'type_field' not in info.keys():
        info.setdefault('type_field', 'unknown')
    
    return info

def extract_global_info(input_file, output_file):
    llvm_name = os.path.basename(input_file)
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    llvm_ir = generate_llvm_ir(input_file)

    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        print(f"{llvm_name} parsed successfully.\n")
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {e}")
        exit(1)
    global_vars = [str(global_var) for global_var in llvm_mod.global_variables]
    global_var_info_list = defaultdict(list)
    id = 0
    for global_var in global_vars:
        global_info = get_global_var_info(global_var+" ")
        global_info.setdefault('id', id)
        id += 1
        global_var_info_list.setdefault(global_info['var_name'],global_info)
    with open(output_file, 'wb+') as f:
            json_data = json.dumps(global_var_info_list)  # 转换为 JSON 字符串
            f.write(json_data.encode('utf-8'))  # 将字符串编码为字节并写入文件

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', help='Input LLVM IR dir', default=r'E:\\Desktop\similarity\\ll_files')
    parser.add_argument('--output_dir', help='Output JSON dir', default=r'E:\\Desktop\similarity\\global_info')
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for file in os.listdir(input_dir):
        if file.endswith('.ll'):
            input_file = os.path.join(input_dir, file)
            output_file = os.path.join(output_dir, file.replace('.ll', '_global_info.json'))
            extract_global_info(input_file,output_file)

var_list = []
if __name__ == '__main__':
    main()