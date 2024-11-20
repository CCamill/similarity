import argparse
import os
import re
import llvmlite.ir as ir
import llvmlite.binding as llvm
import json
from collections import defaultdict
import sys
from tqdm import tqdm

def generate_llvm_ir(input_file):
    # 从输入文件读取 LLVM IR
    with open(input_file, 'r') as f:
        llvm_ir = f.read()

    # 打印读取的 LLVM IR
    # print("Read LLVM IR from file:")

    return llvm_ir

def get_varname(instruction):
    instruction = str(instruction)
    return instruction[:instruction.index('=')].replace(" ", "")

def get_function_name(operand):
    function_name_start_index = operand.index('@') + 1
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
        function_name_start_index = function_attrs.index('@') + 1
        function_name_end_index = function_attrs.index('(')
        return_type = function_attrs[return_rype_start_index:return_type_end_index].strip()
        function_name = function_attrs[function_name_start_index:function_name_end_index].strip()
    except:
        function_attrs = instruction[instruction.index('call') + 4:instruction.index('(')].strip()
        return_type = function_attrs.split(' ')[0]
        function_name = function_attrs.split(' ')[1]

    parameters = [operand.strip() for operand in operand_list if  not function_name in operand]

    return function_name, return_type, parameters


def main(ll_file,output_dir):
    ll_file_name_with_extention = os.path.basename(ll_file)
    ll_file_name_without_extention = os.path.splitext(ll_file_name_with_extention)[0]
    out_file_name = ll_file_name_without_extention + "_info_summary.json"
    output_file = os.path.join(output_dir, out_file_name)

    # if os.path.exists(output_file):
        # return 0
    
    # 初始化 LLVM
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    # 生成 LLVM IR
    llvm_ir = generate_llvm_ir(ll_file)

    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        print(f"{ll_file_name_with_extention} parsed successfully.\n")
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {e}")
        exit(1)
    
    
    # 变量名到指令列表的映射
    file_var_inst_map = []

    inst_id = 0
    
    functions = [function.name for function in llvm_mod.functions]
    pbar = tqdm(total=len(functions))
    for function in llvm_mod.functions:
        # 函数参数列表
        function_param_list = [str(param) for param in function.arguments]

        inst_operand_map = defaultdict(list)

        function_blocks = []

        bb_num = 0
        
        for block in function.blocks:
            try:
                block_label = str(block)[1:str(block).index(':')]
            except:
                if bb_num == 0:
                    block_label = str(0)
                else:
                    block_label = str(block)[1:str(block).index(':')]
            block_info = {}
            block_var_list = []
            inst_num = 0
            block_insts = []
            insts_opcode = {str(inst):str(inst.opcode) for inst in block.instructions}
            for instruction in block.instructions:

                isnt_info = {}
                isnt_info.setdefault("inst_id", str(inst_id))
                isnt_info.setdefault("instruction", str(instruction).strip())
                operands = [str(operand).strip() for operand in instruction.operands]
                
                # get variable name
                if "=" in str(instruction):
                    var_name = get_varname(instruction)
                    block_var_list.append(var_name)
                else:
                    var_name = None
                isnt_info.setdefault("var_name", var_name)

                for operand in instruction.operands:
                    operand = str(operand).strip()
                    if 'Function Attrs' in operand or 'define' in operand:
                        # print("function_attrs:",operand)
                        operand = get_function_name(operand)
                    inst_operand_map.setdefault(str(instruction), []).append(operand) if instruction.opcode not in ["br"] else None
                    isnt_info.setdefault("operand_list", inst_operand_map[str(instruction)])
                
                if str(instruction.opcode) == "call":
                    called_function_name, callde_function_return_type, called_function_arguments  = get_called_function_info(instruction.operands, str(instruction))
                    isnt_info.update({"called_function_name": called_function_name, "called_function_return_type": callde_function_return_type, "called_function_arguments": called_function_arguments})
                
                if str(instruction.opcode) == "br":
                    del isnt_info["operand_list"]
                    for operand in instruction.operands:
                        if str(operand) in insts_opcode.keys() and insts_opcode[str(operand)] in ['icmp', 'fcmp']:
                            isnt_info.update({"branch_condition": str(operand).strip()})
                            labels = re.findall(r'label (%[\w.]+)', str(instruction))
                            isnt_info.update({"true_target": labels[0]})
                            isnt_info.update({"false_target": labels[1]})
                        else:
                            labels = re.findall(r'label (%[\w.]+)', str(instruction))
                            isnt_info.update({"branch_condition": 'False'})
                            isnt_info.update({"br_target": labels[0]})
                    
            
                if str(instruction.opcode) == "switch":
                    del isnt_info["operand_list"]
                    labels = re.findall(r'label (%[\w.]+)', str(instruction))
                    contition = operands[0]
                    isnt_info.update({"switch_condition": contition})
                    isnt_info.update({"case_targets": labels})
                if str(instruction.opcode) == "ret":
                    pass 
                
                isnt_info.setdefault("opcode", str(instruction.opcode))

                block_insts.append(isnt_info)
                inst_id += 1
                inst_num += 1
            bb_num += 1
            
            [block_info.update({"block_name":'block-' + block_label,"inst_num": inst_num, "block_var_list": block_var_list, "block_insts": block_insts}) if block_insts else None]

            function_blocks.append(block_info)
        
        [file_var_inst_map.append({"function_name":function.name,"bb_num":bb_num,"function_param_list":function_param_list,"function_blocks":function_blocks}) if bb_num > 0 else None]

        with open(output_file, 'wb+') as f:
            json_data = json.dumps(file_var_inst_map)  # 转换为 JSON 字符串
            f.write(json_data.encode('utf-8'))  # 将字符串编码为字节并写入文件
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