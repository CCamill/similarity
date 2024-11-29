import argparse
import os
import re
import llvmlite.ir as ir
import llvmlite.binding as llvm
import json
from collections import defaultdict
import sys
from tqdm import tqdm


def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))

def generate_llvm_ir(input_file):
    with open(input_file, 'r') as f:
        llvm_ir = f.read()
    return llvm_ir

def parse_llvm_IR(llvm_ir):
    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {e}")
        exit(1)
    return llvm_mod

def get_global_var_name(operand):
    list_operand= operand.split(" ")
    global_vars = [var for var in list_operand if var.startswith('@')]
    norm_global_vars = []
    for var in global_vars:
        if var.endswith(','):
            norm_global_vars.append(var.replace(',', ''))
    """  global_vars = []
    for var in global_var:
        if var in global_var_list:
            global_vars.append(var) """
    return norm_global_vars

def get_varname(instruction):
    instruction = str(instruction)
    return instruction[:instruction.index('=')].replace(" ", "")

def get_function_name(operand):
    function_name_start_index = operand.index('@')
    function_name_end_index = operand.index('(')
    function_name = operand[function_name_start_index:function_name_end_index].strip()
    return function_name

def get_called_function_info(operands,instruction):
    operand_list = list(map(str, operands))
    try:
        function_attrs = [operand for operand in operand_list if 'Function Attrs' in operand or ('declare' and '@') in operand].pop()
        if 'declare' in function_attrs:
            return_rype_start_index = function_attrs.index('declare')+7
        if 'define' in function_attrs:
            return_rype_start_index = function_attrs.index('define')+6
        return_type_end_index = function_attrs.index('@') 
        function_name_start_index = function_attrs.index('@')
        function_name_end_index = function_attrs.index('(')
        return_type = function_attrs[return_rype_start_index:return_type_end_index].strip()
        function_name = function_attrs[function_name_start_index:function_name_end_index].strip()
    except:
        function_attrs = instruction[instruction.index('call') + 4:instruction.index('(')].strip()
        return_type = function_attrs.split(' ')[0]
        function_name = function_attrs.split(' ')[1]

    # parameters = [operand.strip() for operand in operand_list if not function_name in operand]  

    return function_name, return_type


def get_block_label(block):
    colon_index = str(block).find(':')
    if colon_index != -1:
        block_label = str(block)[1:colon_index]
    else:
        block_label = "0"
    return block_label
def main(ll_file,output_dir):
    ll_file_name_with_extention = os.path.basename(ll_file)
    ll_file_name_without_extention = os.path.splitext(ll_file_name_with_extention)[0]
    out_file_name = ll_file_name_without_extention + "_info_summary.json"
    output_file = os.path.join(output_dir, out_file_name)
    global_info_file = ll_file_name_without_extention + "_global_info.json"
    global_info_path = os.path.join("E:\Desktop\similarity\global_info", global_info_file)

    if os.path.exists(output_file):
        return 0
    
    # 初始化 LLVM
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    llvm.initialize_native_asmparser()

    # 生成 LLVM IR
    llvm_ir = generate_llvm_ir(ll_file)

    # 解析 LLVM IR
    llvm_mod = parse_llvm_IR(llvm_ir)
    print(f"{ll_file_name_with_extention} parsed successfully.\n")
    
    # 变量名到指令列表的映射
    file_var_inst_map = []

    inst_id = 0
    
    global_infos = load_json_file(global_info_path)
    global_var_list = [key for key, _ in global_infos.items()]
    functions = ['@' + function.name for function in llvm_mod.functions]
    pbar = tqdm(total=len(functions))
    for function in llvm_mod.functions:
        # 函数参数列表
        function_param_list = [str(param) for param in function.arguments]
        # inst_operand_map = defaultdict(list)


        function_blocks = []
        bb_num = 0
        instructions = []
        for block in function.blocks:
            block_label = get_block_label(block)
            block_info = {}
            block_inst_list = []
            inst_num = 0
            block_var_list = []
            block_insts = []
            cmp_insts = []
            # 指令到操作码的映射
            for instruction in block.instructions:
                inst_info = {}

                instruction_str = str(instruction).strip()
                instructions.append(instruction_str)
                opcode = str(instruction.opcode).strip()
                operands = [str(operand).strip() for operand in instruction.operands]
                
                block_inst_list.append(instruction_str)
                inst_info.setdefault("inst_id", str(inst_id))
                inst_info.setdefault("instruction", instruction_str)
                inst_info.setdefault("opcode", opcode)
                
                norm_operands = []
                if opcode not in ["ret", "br", "switch"]:
                    for operand in operands:
                        if '@' in operand:
                            is_fun = {"Function","Attrs", "define", "declare"} & set(operand.split(" "))
                            if is_fun:
                                operand = get_function_name(operand)
                                if operand in functions:
                                    inst_info.setdefault("call_back_func", operand)
                                    continue
                                norm_operands.append(operand)
                                continue
                            if set(operand) & set(global_var_list):
                                continue
                            if not is_fun and operand not in instructions and 'call' not in operand:
                                global_var = get_global_var_name(operand)
                                if global_var:
                                    for var in global_var:
                                        norm_operands.append(var)
                                continue
                        norm_operands.append(operand)        
                    inst_info.setdefault("operand_list", norm_operands)
                    
                # get variable name
                if "=" in instruction_str:
                    var_name = get_varname(instruction)
                    block_var_list.append(var_name)
                    inst_info.setdefault("var_name", var_name)
                
                if opcode in ['icmp' ,'fcmp']:
                    cmp_insts.append(instruction_str)
                
                if opcode == "call":
                    called_function_name, callde_function_return_type  = get_called_function_info(instruction.operands, instruction_str)
                    for operand in inst_info["operand_list"]:
                        inst_info["operand_list"].remove(operand) if called_function_name in  operand else None
                    inst_info.update({"called_function_name": called_function_name, "called_function_return_type": callde_function_return_type})
                
                if opcode == "br":
                    # del inst_info["operand_list"]
                    branch_condition = set(operands) & set(cmp_insts)
                    labels = re.findall(r'label (%[\w.]+)', instruction_str)
                    if branch_condition:
                        inst_info.update({"branch_condition": branch_condition.pop()})
                        inst_info.update({"true_target": labels[0]})
                        inst_info.update({"false_target": labels[1]})
                    else:
                        inst_info.update({"branch_condition": 'False'})
                        inst_info.update({"br_target": labels[0]})
                    
            
                if opcode == "switch":
                    # del inst_info["operand_list"]
                    labels = re.findall(r'label (%[\w.]+)', instruction_str)
                    contition = operands[0]
                    inst_info.update({"switch_condition": contition})
                    inst_info.update({"case_targets": labels})
                
                if opcode == "ret":
                    if len(operands) == 0:
                        inst_info.update({"return_value": '0'})
                    else:
                        inst_info.update({"return_value": operands[0]})

                block_insts.append(inst_info)
                inst_id += 1
                inst_num += 1
            bb_num += 1
            
            [block_info.update({"block_name":'block-' + block_label,'block_var_list': block_var_list,"inst_num": inst_num, "block_inst_list": block_inst_list, "block_insts": block_insts}) if block_insts else None]

            function_blocks.append(block_info)
        
        [file_var_inst_map.append({"function_name":function.name,"function_instructions":instructions,"bb_num":bb_num,"function_param_list":function_param_list,"function_blocks":function_blocks}) if bb_num > 0 else None]

        dump_json_file(file_var_inst_map, output_file)
        pbar.update(1)
    pbar.close()
    return 1



isDebug = True if sys.gettrace() else False
if isDebug:
    print("Debugging mode")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", help="Input LLVM IR file")
    parser.add_argument("--output_file", help="Output LLVM IR file")
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_file
else:
    input_dir = "E:\Desktop\similarity\ll_files"
    output_dir = "E:\Desktop\similarity\summary_files"
    print("Running mode")

if __name__ == "__main__":
    #pbar = tqdm(total=len(input_dir))
    input_files_num = len(os.listdir(input_dir))
    for input_file in os.listdir(input_dir):
        code = main(os.path.join(input_dir, input_file),output_dir)
        input_files_num -= 1
        if code == 1:
            print(f"Processed {input_file} successfully")
        else:
            print(f"{input_file} already exists")
        print(f"Number of unprocessed files: {input_files_num}")
        #pbar.update(1)