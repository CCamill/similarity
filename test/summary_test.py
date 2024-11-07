import os
import llvmlite.ir as ir
import llvmlite.binding as llvm

def generate_llvm_ir(input_file):
    # 从输入文件读取 LLVM IR
    with open(input_file, 'r') as f:
        llvm_ir = f.read()

    # 打印读取的 LLVM IR
    # print("Read LLVM IR from file:")

    return llvm_ir

def main():
    ll_file = 'E:\\Desktop\\IR2SOG\\ll_files\\demo_10_o2.ll'
    llvm_name = os.path.basename(ll_file)
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    llvm_ir = generate_llvm_ir(ll_file)

    # 解析 LLVM IR
    try:
        llvm_mod = llvm.parse_assembly(llvm_ir)
        llvm_mod.verify()
        print(f"{llvm_name} parsed successfully.\n")
    except RuntimeError as e:
        print(f"Error parsing LLVM IR: {e}")
        exit(1)
    functions = [function.name for function in llvm_mod.functions]
    for function in llvm_mod.functions:
        function_param_list = [str(param) for param in function.arguments]
        prev_instruction = None
        for block in function.blocks:
            print(dir(block))
            for instruction in block.instructions:
                if str(instruction.opcode) == "icmp":
                    prev_instruction = instruction
                if str(instruction.opcode) == "br" and prev_instruction is not None:
                    print('icmp instruction:', prev_instruction)
                    print('br instruction:', instruction)
                    print("\n")

if __name__ == '__main__':
    main()