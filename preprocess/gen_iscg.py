import json
import os
import networkx as nx
from py2neo import Node, Graph

def dfs_tree_edges(G, root):
    # 从节点'A'开始进行深度优先搜索，获取深度优先搜索树
    dfs_tree = nx.dfs_tree(G, root)

    # 初始化一个字典来存储每个节点的深度
    depths = {node: 0 for node in G.nodes()}

    # 定义一个函数来递归地计算每个节点的深度
    def calculate_depth(node, current_depth):
        depths[node] = current_depth
        for neighbor in dfs_tree.successors(node):
            if neighbor not in depths or depths[neighbor] == 0:  # 避免重复计算
                calculate_depth(neighbor, current_depth + 1)

    # 从根节点'A'开始计算深度
    calculate_depth(root, 0)

    # 找到叶子节点及其深度 [('D', 3), ('G', 3)]
    leaves_with_depth = [(node, depths[node]) for node in dfs_tree.nodes() if len(list(dfs_tree.successors(node))) == 0]

    return leaves_with_depth

def main():
    summary_path = r'E:\Desktop\similarity\summary_files'
    test_graph = Graph('bolt://localhost:7687',auth=('neo4j','chang8677'),name='neo4j')
    global_info_path = r"E:\\Desktop\\similarity\\global_info"


    # 先为每个基本快生成一个子图，然后遍历每个基本块中的指令，建立基本块之间的指令流关系和控制流关系
    # 每一个基本快都有一个起始节点和一个终止节点，起始节点的属性包括基本块名称、基本块所包含的指令数量等，终止节点为该基本块的br指令或者ret指令。
    # 指令节点的属性包括指令ID、指令内容、指令操作码、基本快名称、指令定义的变量、指令中的常量或者符号等
    # 若该指令为基本块的入口指令，则将该指令与起始节点之间建立顺序流关系
    # 指令流关系的属性包括数据流方向、数据流类型、数据流大小等
    # 控制流关系的属性包括控制流方向、控制流类型等
    # 若该指令与该基本块中的任何指令之间都不存在数据流关系，则将该指令与起始节点之间建立顺序流关系
    # br分支指令与其他基本块的起始节点相连接
    
    
    summary_file_paths = []
    for file in os.listdir(summary_path):
        summary_file_paths.append(os.path.join(summary_path, file))

    for summary_file_path in summary_file_paths:
        # 路径拼接
        ori_file_name = os.path.basename(summary_file_path)[0:os.path.basename(summary_file_path).index('_info_summary.json')]
        global_info_path = os.path.join(global_info_path, ori_file_name + '_global_info.json')

        print('processing file: ', summary_file_path)
        # 读取json文件
        with open(summary_file_path, 'r') as f:
            summary_data = json.load(f)
        with open(global_info_path, 'r') as f:
            global_infos = json.load(f)
        
        global_var_list = [key for key, _ in global_infos.items()]

        instructions = []
        inst_instID_dict = dict()
        inst_instOp_dict = dict()
        inst_instVar_dict = dict()

        for function in summary_data:
            G = nx.MultiDiGraph()
            function_params = function['function_param_list']
            G.add_node(function['function_name'], node_id=function['function_name'],instruction=function['function_name'],function_params=function_params, bb_num = function['bb_num'])
            function_node = Node(function['function_name'],node_id=function['function_name'], instruction = function['function_name'])
            test_graph.create(function_node)

            for index,block_info in enumerate(function['function_blocks']):
                if index == 0:
                    G.add_edge(function['function_name'], block_info['block_name'], edge_type='Entry')
                # 为每个基本块中的指令创建节点
                block_instructions = []

                # 为基本块创建起始节点
                G.add_node(block_info['block_name'],block_var_list=block_info['block_var_list'],block_inst_count=block_info['inst_num'])
                block_node = Node(function['function_name'],node_id=block_info['block_name'], instruction = block_info['block_name'] )
                test_graph.create(block_node)
                
                
                for index,inst_info in enumerate(block_info['block_insts']):
                    leaves_with_depth = []
                    block_instructions.append(inst_info['instruction'])
                    instructions.append(inst_info['instruction'])                   
                    
                    # 指令到指令ID的映射
                    inst_instID_dict[inst_info['instruction']] = inst_info['inst_id']
                    # 指令到指令操作码的映射
                    inst_instOp_dict[inst_info['instruction']] = inst_info['opcode']
                    # 指令到变量名称的映射
                    inst_instVar_dict[inst_info['instruction']] = inst_info['var_name']

                    # neo4j 图数据库中创建指令节点
                    inst_node = Node(function['function_name'],node_id = str(inst_info['inst_id']), instruction=inst_info['instruction'], opcode=inst_info['opcode'])
                    test_graph.create(inst_node)

                    # nx 图数据库中创建指令节点
                    G.add_node(inst_info['inst_id'], instruction=inst_info['instruction'], opcode=inst_info['opcode'])

                    # 如果该指令是基本块的入口指令，则将该指令与起始节点之间建立顺序流关系
                    if index == 0:
                        G.add_edge(block_info['block_name'], inst_instID_dict[inst_info['instruction']], edge_type='Sequential')
                        continue
                    
                    # 如果该指令是'br'指令
                    if inst_info['opcode'] == 'br':
                        # 如果该跳转指令是无条件跳转指令，将其与该基本快中的最长路径上的指令节点相连接
                        if inst_info['branch_condition'] == 'False':
                            leaves_with_depth = dfs_tree_edges(G, block_info['block_name'])
                            for leaf in leaves_with_depth:
                                G.add_edge(leaf[0], inst_instID_dict[inst_info['instruction']], edge_type='Sequential')
                            
                        # 如果该跳转指令是条件跳转指令，将其与条件表达式相连接
                        else:
                            G.add_edge(inst_instID_dict[inst_info['branch_condition']], inst_instID_dict[inst_info['instruction']], edge_type='Data')
                        continue
                    
                    if inst_info['opcode'] =='switch':
                        switch_condition = inst_info['switch_condition']
                        G.add_edge(inst_instID_dict[switch_condition], inst_instID_dict[inst_info['instruction']], edge_type='Data')
                        continue

                    if inst_info['opcode'] in ['ret','unreachable']:
                        leaves_with_depth = dfs_tree_edges(G, block_info['block_name'])
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_instID_dict[inst_info['instruction']], edge_type='Sequential')
                        continue

                    # rule 1: 指令之间存在数据流关系
                    # 指令之间存在数据流关系，则将该指令与其操作数相连接
                    if inst_info['opcode'] not in ['br', 'ret', 'unreachable','switch']:
                        flag = 0
                        for operand in inst_info['operand_list']:
                            if operand in block_instructions:
                                G.add_edge(inst_instID_dict[operand], inst_instID_dict[inst_info['instruction']], edge_type='Data')
                                flag = 1
                        if flag == 0:
                            G.add_edge(block_info['block_name'], inst_instID_dict[inst_info['instruction']], edge_type='Sequential')
                        continue
            
            # 为创建不同基本块之间的指令流关系
            for block_info in function['function_blocks']:
                for index,inst_info in enumerate(block_info['block_insts']):
                    if inst_info['opcode'] == 'br':
                        # 如果该跳转指令是无条件跳转指令
                        if inst_info['branch_condition'] == 'False':
                            br_target = 'block-' + inst_info['br_target'].replace('%', '')
                            G.add_edge(inst_instID_dict[inst_info['instruction']], br_target, edge_type='Control')
                        # 如果该跳转指令是条件跳转指令
                        else:
                            true_target = 'block-' + inst_info['true_target'].replace('%', '')
                            false_target = 'block-' + inst_info['false_target'].replace('%', '')
                            G.add_edge(inst_instID_dict[inst_info['instruction']], true_target, edge_type='Control')
                            G.add_edge(inst_instID_dict[inst_info['instruction']], false_target, edge_type='Control')
                    elif inst_info['opcode'] =='switch':
                        for index,target in enumerate(inst_info['case_targets']):
                            case_target = 'block-' + target.replace('%', '')
                            G.add_edge(inst_instID_dict[inst_info['instruction']], case_target, edge_type='Control')
                    elif inst_info['opcode'] in ['ret', 'unreachable']:
                        continue
                    else:
                        for operand in inst_info['operand_list']:
                            if operand in instructions and operand not in block_instructions:
                                G.add_edge(inst_instID_dict[operand], inst_instID_dict[inst_info['instruction']], edge_type='Data')
                            if operand in function_params:
                                G.add_edge(function['function_name'], inst_instID_dict[inst_info['instruction']], edge_type='Parameter')
                            if '@' in operand:
                                globals = [g for g in operand.split(' ') if g.startswith('@')]
                                if inst_info['opcode'] in ['call']:
                                    globals = [g for g in globals if inst_info['called_function_name'] not in g]
                                for global_var in globals:
                                    if global_var in global_var_list:
                                        if global_infos[global_var]['type_field'] not in ['array_ptr', 'ptr_array','unknown']:
                                            attr_dict = global_infos[global_var] 
                                            G.add_node(global_var, **attr_dict)
                                        if 

            
            list_edges = [(edge[0], edge[1], edge[2]['edge_type']) for edge in G.edges(data=True)]
            remove_redundant_edges = list(dict.fromkeys(list_edges))
            for edge in remove_redundant_edges:
                label = function['function_name']
                source_node = edge[0]
                target_node = edge[1]
                edge_type = edge[2]
                rel_str = f'MATCH (source:{label}{{node_id:"{source_node}"}}) MATCH (target:{label}{{node_id:"{target_node}"}}) CREATE (source)-[r:{edge_type}]->(target)'
                test_graph.run(rel_str)
                print(edge)
        
    # nx.draw(G, with_labels=True, font_weight='bold')
    # plt.show()
if __name__ == '__main__':
    main()