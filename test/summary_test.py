from collections import defaultdict
import os
import llvmlite.ir as ir
import llvmlite.binding as llvm
import re
import json




def generate_llvm_ir(input_file):
    # 从输入文件读取 LLVM IR
    with open(input_file, 'r') as f:
        llvm_ir = f.read()

    # 打印读取的 LLVM IR
    # print("Read LLVM IR from file:")

    return llvm_ir

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def get_global_var_name(operand):
    list_operand= operand.split(" ")
    global_vars = [var for var in list_operand if var.startswith('@')]
    if len(global_vars) == 2:
        pass
    for var in global_vars:
        if var.endswith(','):
            global_vars.remove(var)
            global_vars.append(var.replace(',', ''))
    """  global_vars = []
    for var in global_var:
        if var in global_var_list:
            global_vars.append(var) """
    return global_vars

def get_varname(instruction):
    instruction = str(instruction)
    return instruction[:instruction.index('=')].replace(" ", "")

def get_function_name(operand):
    function_name_start_index = operand.index('@') + 1
    function_name_end_index = operand.index('(')
    function_name = operand[function_name_start_index:function_name_end_index].strip()
    return function_name

def main():
    ll_file = 'E:\\Desktop\\similarity\\ll_files\\demo_10_o1_dbg.ll'
    output_file = 'E:\\Desktop\\similarity\\ll_files\\1.json'
    llvm_name = os.path.basename(ll_file)
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    llvm_ir = generate_llvm_ir(ll_file)
    global_info_path = "E:\\Desktop\\similarity\\global_info\\1_global_info.json"
    global_infos = load_json_file(global_info_path) if os.path.exists(global_info_path) else {}
    global_var_list = [key for key, _ in global_infos.items()]

    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        print(f"{llvm_name} parsed successfully.\n")
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {e}")
        exit(1)
    functions = ['@' + function.name for function in llvm_mod.functions]
    for function in llvm_mod.functions:
        instructions = []
        for block in function.blocks:
            op_inst_map = {}
            block_insts = []
            cmp_insts = []
            for inst in block.instructions:
                instruction = str(inst).strip()
                instructions.append(instruction)
                opcode = str(inst.opcode).strip()
                op_inst_map[opcode] = instruction
                block_insts.append(instruction)
                operand_list = [str(operand).strip() for operand in inst.operands]
                norm_operands = []
                if '%7 = getelementptr inbounds [3 x i8*], [3 x i8*]* @switch.table.displayPerson' in instruction:
                    for operand in operand_list:
                        is_fun = {"Function","Attrs", "define", "declare"} & set(operand.split(" "))
                        #if not is_fun:
                        
                        operand_split = operand.split(" ")
                        global_vars = [var for var in operand_split if var.startswith('@')]
                        norm_global_vars = []
                        for var in global_vars:
                            if var.endswith(','):
                                norm_global_vars.append(var.replace(',', ''))
                        print(operand_split)
                        print(set(operand_split) & set(global_var_list))
                        """ if '@' in operand:
                            is_fun = {"Function","Attrs", "define", "declare"} & set(operand.split(" "))
                            if is_fun:
                                operand = get_function_name(operand)
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
                        norm_operands.append(operand)   """      
                

if __name__ == '__main__':
    main()