import json
from llvmlite import binding as llvm

inst_id_map = dict()

def extract_nodes_from_module(module):
    nodes = []
    id = 0
    for func in module.functions:
        for block in func.blocks:
            for inst in block.instructions:
                # print(dir(inst))
                # print(dir(llvm))
                # print(f"Instruction: {inst}, Opcode: {inst.opcode}")

                # 获取指令类型和相关属性
                node = {
                    'id':str(id),
                    'instruction': str(inst),
                    'class': inst.opcode,  # 这里假设 opcode_name 属性仍然可用
                    'attributes': {  # 可加入其他属性
                        'is_branch': inst.opcode == 'br',  # 更新条件判断
                        'operation': inst.opcode,
                        'dtype': str(inst.type),
                        # 'is_constant': inst.is_constant
                    }
                }
                inst_id_map.setdefault(node['instruction'],node['id'])
                nodes.append(node)
                id = id + 1
    return nodes


def extract_links_from_module(module):
    links = []
    for func in module.functions:
        for block in func.blocks:
            prev_inst = None
            for inst in block.instructions:
                if prev_inst:
                    # 控制流边
                    links.append({
                        'type': 'control',
                        'source': str(prev_inst),
                        'target': str(inst),
                        # 'source_id': inst_id_map[str(prev_inst)],
                        # 'target_id': inst_id_map[str(inst)]
                    })
                # 数据流边：分析操作数依赖关系
                for operand in inst.operands:
                    if isinstance(operand, llvm.ValueRef):
                        links.append({
                            'type': 'data',
                            'source': str(operand),
                            'target': str(inst),
                            # 'source_id': inst_id_map[str(operand)],
                            # 'target_id': inst_id_map[str(inst)],
                            'data_type': str(operand.type)  # 确保操作数类型可以转成字符串
                        })
                prev_inst = inst
    return links


def extract_debug_info_from_module(module):
    debug_info = []
    for func in module.functions:
        for block in func.blocks:
            for inst in block.instructions:
                # 提取与调试信息相关的元数据
                dbg_metadata = inst.debug_location  # `get_debug_location` 改为 `debug_location`
                if dbg_metadata:
                    debug_info.append({
                        'instruction': str(inst),
                        'source_file': dbg_metadata.filename,  # 更新字段名称
                        'line_number': dbg_metadata.line,
                        'column_number': dbg_metadata.column
                    })
    return debug_info


def generate_epdg(nodes, links, output_file='demo_10_generate_ePDG.json'):
    epdg = {
        'nodes': nodes,
        'links': links
    }

    with open(output_file, 'w') as f:
        json.dump(epdg, f, indent=4)


if __name__ == '__main__':
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    # 读取 LLVM IR 文件
    with open('demo_10.ll', 'r') as f:
        llvm_ir = f.read()

    # 将 LLVM IR 加载为模块
    llvm_mod = llvm.parse_assembly(llvm_ir)
    llvm_mod.verify()  # 验证 IR 是否正确

    links = extract_links_from_module(llvm_mod)
    nodes = extract_nodes_from_module(llvm_mod)
    generate_epdg(nodes, links)
