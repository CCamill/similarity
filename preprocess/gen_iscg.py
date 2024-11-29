import json
import os
import networkx as nx
from tqdm import tqdm
from py2neo import Node, Graph
from collections import defaultdict
import re
iscg_dir = r'E:\\Desktop\\similarity\\iscg'
# test_graph = Graph('bolt://localhost:7687',auth=('neo4j','chang8677'),name='neo4j')
summary_path = r'E:\Desktop\similarity\summary_files'    
global_infos_dir = r"E:\\Desktop\\similarity\\global_info"

""" def creat_neo4j_graph(G,remove_redundant_edges,function_name):
    nodes_infos = [node for node in G.nodes(data=True)]
    for node in nodes_infos:
        node = Node(function_name, node_id=node[0], **node[1])
        test_graph.create(node)   
    for edge in remove_redundant_edges:
        label = function_name
        source_node = edge[0]
        target_node = edge[1]
        edge_type = edge[2]
        try:
            rel_str = f'MATCH (source:{label}{{node_id:"{source_node}"}}) MATCH (target:{label}{{node_id:"{target_node}"}}) CREATE (source)-[r:{edge_type}]->(target)'
            test_graph.run(rel_str)
        except Exception as e:
            print(e) """

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))

def is_constant(operand):
    match_str = r'\bi(32|8|16)\s+(-?\d+)'
    if re.match(match_str, operand):
        return True
    else:
        return False
def inst_map_to_instID(function):
    inst_instID_dict = dict()
    for block in function['function_blocks']:
        for inst in block['block_insts']:
            inst_instID_dict[inst['instruction']] = inst['inst_id']
    return inst_instID_dict
        
def dfs_tree_edges(G, block_info):
    root = block_info['block_name']
    if block_info['inst_num'] == 1:
        return [(root, 0)]
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
        global_info_path = os.path.join(global_infos_dir, ori_file_name + '_global_info.json')
        iscg_path = os.path.join(iscg_dir, ori_file_name + '_iscg.json')

        # 若iscg文件已存在，则跳过该文件
        if os.path.exists(iscg_path):
            continue
        print('processing file: ', summary_file_path)
        # 读取json文件
        summary_data = load_json_file(summary_file_path)
        global_infos = load_json_file(global_info_path)

        
        iscg_json = dict()
        pbar = tqdm(total=len(summary_data))
        for function in summary_data:
            G = nx.MultiDiGraph()
            instructions = function['function_instructions']
            inst_instID_dict = inst_map_to_instID(function)
            function_name = function['function_name']
            function_params = function['function_param_list']
            G.add_node(function_name,function_params=function_params, bb_num = function['bb_num'])

            # 建立同一基本块之间的指令流关系
            for index,block_info in enumerate(function['function_blocks']):
                if index == 0:
                    G.add_edge(function_name, block_info['block_name'], edge_type='Function_Entry')
                # 为每个基本块中的指令创建节点
                block_instructions = block_info['block_inst_list']

                # 为基本块创建起始节点
                G.add_node(block_info['block_name'],block_var_list=block_info['block_var_list'],block_inst_count=block_info['inst_num'])
                 
                for index,inst_info in enumerate(block_info['block_insts']):
                    leaves_with_depth = []
                    instruction = inst_info['instruction']              
                    inst_id = inst_info['inst_id']
                    attr_dict = {'instruction':instruction, 'opcode':inst_info['opcode'], }
                    if inst_info['opcode'] not in ["ret", "br", "switch"]:
                        if set(inst_info['operand_list']) & set(function_params):
                            attr_dict['call_fun_param'] = "True"
                    
                    # nx 图数据库中创建指令节点
                    G.add_node(inst_info['inst_id'], **attr_dict)
                    
                    # 如果该指令是基本块的入口指令，则将该指令与起始节点之间建立顺序流关系
                    if inst_info['opcode'] not in ['ret', 'br','switch','unreachable']:
                        if not set(inst_info['operand_list']) & set(block_instructions):
                            G.add_edge(block_info['block_name'], inst_id, edge_type='Sequential')
                    
                    # 如果该指令是'br'指令
                    if inst_info['opcode'] == 'br':
                        # 如果该跳转指令是无条件跳转指令，将其与该基本快中的最长路径上的指令节点相连接
                        if inst_info['branch_condition'] == 'False':
                            leaves_with_depth = dfs_tree_edges(G, block_info)
                            for leaf in leaves_with_depth:
                                G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                        # 如果该跳转指令是条件跳转指令，将其与条件表达式相连接
                        elif inst_info['branch_condition'] in instructions:
                            G.add_edge(inst_instID_dict[inst_info['branch_condition']], inst_id, edge_type='Data')
                        elif inst_info['branch_condition'] in function_params:
                            G.add_edge(function_name, inst_id, edge_type='Parameter')
                        
                        # 如果该跳转指令是无条件跳转指令
                        if inst_info['branch_condition'] == 'False':
                            br_target = 'block-' + inst_info['br_target'].replace('%', '')
                            G.add_edge(inst_id, br_target, edge_type='Control')
                        # 如果该跳转指令是条件跳转指令
                        else:
                            true_target = 'block-' + inst_info['true_target'].replace('%', '')
                            false_target = 'block-' + inst_info['false_target'].replace('%', '')
                            G.add_edge(inst_id, true_target, edge_type='Control')
                            G.add_edge(inst_id, false_target, edge_type='Control')
                        continue
                    elif inst_info['opcode'] =='switch':
                        switch_condition = inst_info['switch_condition']
                        # 建立switch指令与switch条件表达式的关系
                        if switch_condition in instructions:
                            G.add_edge(inst_instID_dict[switch_condition], inst_id, edge_type='Data')
                        if switch_condition in function_params:
                            G.add_edge(function_name, inst_id, edge_type='Parameter')
                        # 建立switch指令与case目标基本块的关系
                        for index,target in enumerate(inst_info['case_targets']):
                            case_target = 'block-' + target.replace('%', '')
                            G.add_edge(inst_id, case_target, edge_type='Control')
                        continue
                    elif inst_info['opcode'] == 'unreachable':
                        leaves_with_depth = dfs_tree_edges(G, block_info)
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                        continue
                    elif inst_info['opcode'] == 'ret':
                        if inst_info['return_value'] in instructions:
                            G.add_edge(inst_instID_dict[inst_info['return_value']], inst_id, edge_type='Data')
                        elif inst_info['return_value'] in function_params:
                            G.add_edge(function_name, inst_id, edge_type='Parameter')
                        else:
                            leaves_with_depth = dfs_tree_edges(G, block_info)
                            for leaf in leaves_with_depth:
                                G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                        continue
                    # 建立指令节点与其他节点之间的关系
                    else:
                        for operand in inst_info['operand_list']:
                            if is_constant(operand):
                                pass
                            if '@' in operand and operand not in instructions:
                                global_info = global_infos[operand]
                                define = global_info['define']
                                G.add_node(operand, define=define, is_global='true')
                                G.add_edge(operand, inst_id, edge_type='Global')
                            # if operand in function_params:
                                # G.add_edge(function_name, inst_id, edge_type='Parameter')
                            if operand in instructions:
                                G.add_edge(inst_instID_dict[operand], inst_id, edge_type='Data')
                                
                        
            
            """ # 创建不同基本块之间的指令流关系
            for block_info in function['function_blocks']:
                for index,inst_info in enumerate(block_info['block_insts']):
                    if inst_info['opcode'] == 'br':
                        # 如果该跳转指令是无条件跳转指令
                        if inst_info['branch_condition'] == 'False':
                            br_target = 'block-' + inst_info['br_target'].replace('%', '')
                            G.add_edge(inst_id, br_target, edge_type='Control')
                        # 如果该跳转指令是条件跳转指令
                        else:
                            true_target = 'block-' + inst_info['true_target'].replace('%', '')
                            false_target = 'block-' + inst_info['false_target'].replace('%', '')
                            G.add_edge(inst_id, true_target, edge_type='Control')
                            G.add_edge(inst_id, false_target, edge_type='Control')
                    elif inst_info['opcode'] =='switch':
                        for index,target in enumerate(inst_info['case_targets']):
                            case_target = 'block-' + target.replace('%', '')
                            G.add_edge(inst_id, case_target, edge_type='Control')
                    elif inst_info['opcode'] in ['unreachable']:
                        continue
                    else:
                        for operand in inst_info['operand_list']:
                            if operand in instructions and operand not in block_instructions:
                                G.add_edge(inst_instID_dict[operand], inst_id, edge_type='Data')
                            if operand in function_params:
                                G.add_edge(function_name, inst_id, edge_type='Parameter')
                            if '@' in operand:
                                globals = [g for g in operand.split(' ') if g.startswith('@')]
                                if inst_info['opcode'] in ['call']:
                                    globals = [g for g in globals if inst_info['called_function_name'] not in g]
                                for global_var in globals:
                                    if global_var in global_var_list:
                                        if global_infos[global_var]['type_field'] not in ['array_ptr', 'ptr_array','unknown']:
                                            attr_dict = global_infos[global_var]
                                            attr_dict['is_global'] = True
                                            G.add_node(global_var, **attr_dict)
                                            # global_node = Node(function['function_name'], node_id=global_var, **attr_dict)
                                            # test_graph.create(global_node)
                                            G.add_edge(global_var, inst_id, edge_type='Global') """
            
            list_edges = [(edge[0], edge[1], edge[2]['edge_type']) for edge in G.edges(data=True)]
            remove_redundant_edges = list(dict.fromkeys(list_edges))
            # creat_neo4j_graph(G,remove_redundant_edges,function_name)
            
            
            nodes_info = {node[0]:node[1] for node in G.nodes(data=True)}
            nodes = [key for key in nodes_info]

            function_iscg = {
                "nodes":nodes,
                "links":remove_redundant_edges,
                "nodes_info":nodes_info
            }
            iscg_json.setdefault(function['function_name'], function_iscg)
            dump_json_file(iscg_json, iscg_path)
            pbar.update(1)
        pbar.close()
if __name__ == '__main__':
    main()