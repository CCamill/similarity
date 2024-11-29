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

def get_global_var_name(global_var):
    var_start_idx = global_var.index('@')
    var_end_idx = global_var.index('=')
    var_name = global_var[var_start_idx:var_end_idx].strip()
    return var_name

def get_global_compile_info(global_var):
    linkages = ['external', 'internal', 'available_externally', 'private','linkonce', 'weak', 'weak_odr', 'linkonce_odr']
    visibilities = ['default', 'hidden', 'protected']
    addressing_modes = ['local_unnamed_addr','unnamed_addr']
    global_var_tokens = global_var.split(" ")

    linkage = list(set(linkages) & set(global_var_tokens))
    visibility = list(set(visibilities) & set(global_var_tokens))
    addressing_mode = list(set(addressing_modes) & set(global_var_tokens))
    is_constant = True if 'constant' in global_var_tokens else False

    return {'linkage': linkage[0] if linkage else None, 'visibility': visibility[0] if visibility else None, 'addressing_mode': addressing_mode[0] if addressing_mode else None,'is_constant':is_constant}

""" def get_global_var_info(global_var):
    # 获取全局变量的信息
    info = {}
    info.setdefault('define',global_var)

    info.update(get_global_compile_info(global_var))


    var_name = get_global_var_name(global_var)
    info.setdefault('var_name', var_name)
    var_list.append(var_name)

    # 整形数组
    int_array_matcher = r'(\[\d+ x i\d+\]) \[(.*)\]'
    int_array_match = re.search(int_array_matcher, global_var)
    if int_array_match:
        info.setdefault('type_field', 'int_array')
        int_array_len = int_array_match.group(1)
        info.setdefault('value_size', int_array_len)
        int_array_value = int_array_match.group(2)
        info.setdefault('global_value', int_array_value)
        return info

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
    
    info.update(parse_global_var(global_var, var_list))

    return info """

def set_info(info, key, value):
    info.setdefault(key, value)

def parse_int(info, match):
    set_info(info, 'type_field', 'int')
    int_size = match.group(2)
    set_info(info, 'value_size', int_size)
    global_value = match.group(3)
    set_info(info, 'global_value', global_value if info.get('linkage') != 'external' else None)

def parse_floating_point(info, match, size):
    set_info(info, 'type_field', 'float' if size == 32 else 'double')
    set_info(info, 'global_value', match.group(1))
    set_info(info, 'value_size', str(size))

def parse_global_var(global_var):
    info = {'define': global_var}
    var_name = get_global_var_name(global_var) 
    set_info(info, 'var_name', var_name)
    var_list.append(var_name) 

    patterns = {
        r'(\[\d+ x i\d+\]) \[(.*)\]': lambda match: (
            set_info(info, 'type_field', 'int_array'),
            set_info(info, 'value_size', match.group(1)),
            set_info(info, 'global_value', match.group(2))
        ),
        r'((constant|global|internal) \[[\d]+ x i[\d]+\] c)': lambda match: (
            set_info(info, 'type_field', 'string'),
            set_info(info, 'value_size', match.group(0)),
            set_info(info, 'global_value', global_var[global_var.index('c"')+2:global_var.find('00"')+2])
        ),
        r'(constant|global|internal) i(1|8|16|32|64|128)\s+(\d*|-\d*)': lambda match: parse_int(info, match),
        r'float\s+((0x[0-9a-fA-F]+(\.[0-9a-fA-F]+)?([pP][+-]?\d+)?)|([-+]?\d*\.\d+|\d+)([eE][-+]?\d+)?)': lambda match: parse_floating_point(info, match, 32),
        r'double\s+((0x[0-9a-fA-F]+(\.[0-9a-fA-F]+)?([pP][+-]?\d+)?)|([-+]?\d*\.\d+|\d+)([eE][-+]?\d+)?)': lambda match: parse_floating_point(info, match, 64),
        r'((constant|global|internal) \[[\d]+ x i[\d]+\*\] )': lambda match: (
            set_info(info, 'type_field', 'ptr_array'),
            set_info(info, 'ptr_array', [var for var in var_list if var in global_var]),
            set_info(info, 'global_value', None)
        ),
        r"((constant|global|internal) \[[\d]+ x i[\d]+\]\* \@)": lambda match: (
            set_info(info, 'type_field', 'array_ptr'),
            set_info(info, 'array_ptr', [var for var in var_list if var in global_var]),
            set_info(info, 'global_value', None)
        ),
    }

    for pattern, handler in patterns.items():
        match = re.search(pattern, global_var)
        if match:
            handler(match)
            return info

    set_info(info, 'type_field', 'unknown')
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
        global_info = parse_global_var(global_var+" ")
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