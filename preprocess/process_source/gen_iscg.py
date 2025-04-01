import json
import logging
from multiprocessing import Pool
import os
import time
import networkx as nx
from tqdm import tqdm
from py2neo import Node, Graph
from collections import defaultdict
import re
# from settings import *

test_graph = Graph('neo4j://localhost:7687',auth=('neo4j','chang8677'),name='neo4j')
summary_root = r'/home/lab314/cjw/similarity/datasets/source/summary'    

def setup_logger(log_file):
    """设置日志记录器"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 移除所有现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # 将文件处理器添加到日志记录器
    logger.addHandler(file_handler)

def creat_neo4j_graph(G,remove_redundant_edges,function_name):
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
            print(e)

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

def get_all_leaves(G, block_info):
    root = block_info['block_name']
    if block_info['inst_num'] == 1:
        return [(root, 0)]  # 如果只有一个实例，返回根节点
    
    # 获取所有叶子节点（出度为0的节点）
    leaves = [node for node in G.nodes() if G.out_degree(node) == 0]
    
    # 计算每个叶子节点到根节点的最短路径长度作为深度
    leaves_with_depth = []
    for leaf in leaves:
        try:
            depth = nx.shortest_path_length(G, root, leaf)
            leaves_with_depth.append((leaf, depth))
        except nx.NetworkXNoPath:
            # 如果节点不可达，跳过
            continue
    
    return leaves_with_depth

def collect_json_files(proj_root):
    json_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            full_path = os.path.join(root, file)

            if file.endswith('.json'):
                json_paths.append(full_path)
    
    return json_paths

def process_summary_file(summary_path, global_path, struct_path, iscg_path):
    summary_data = load_json_file(summary_path)
    global_infos = load_json_file(global_path)
    struct_infos = load_json_file(struct_path)

    if global_infos:
        global_list = global_infos.keys()
    else:
        global_list = []
    
    if struct_infos:
        struct_list = struct_infos.keys()
    else:
        struct_list = []

    iscg_dir, _ = os.path.split(iscg_path)
    if not os.path.exists(iscg_dir):
        os.mkdir(iscg_dir)
    iscg_json = dict()
    try:
        for function_dict in summary_data:
            function_name, function = next(iter(function_dict.items()))
            G = nx.MultiDiGraph()
            instructions = function['function_instructions']

            inst_instID_dict = inst_map_to_instID(function)

            function_params = function['function_param_list']
            for param in function_params:
                G.add_node(param, type = 'function_param')

            function_base_info = function['base_info']
            G.add_node(function_name,function_params=function_params, bb_num = function_base_info['function_blocks_num'])

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
                    attr_dict = {'instruction':instruction, 'opcode':inst_info['opcode'] }
                    
                    # if inst_info['opcode'] not in ["ret", "br", "switch"]:
                    #     if set(inst_info['operand_list']) & set(function_params):
                    #         attr_dict['call_fun_param'] = "True"
                    
                    # nx 图数据库中创建指令节点
                    G.add_node(inst_info['inst_id'], **attr_dict)
                    
                    # 如果该指令是基本块的入口指令，则将该指令与起始节点之间建立顺序流关系
                    if inst_info['opcode'] not in ['ret', 'br','switch','unreachable']:
                        if not set(inst_info['operand_list']) & set(block_instructions):
                            G.add_edge(block_info['block_name'], inst_id, edge_type='Sequential')
                    
                    if inst_info['opcode'] == 'br':
                        # 如果该跳转指令是无条件跳转指令，将其与该基本快中的最长路径上的指令节点相连接
                        # if not inst_info['condition']:
                        leaves_with_depth = get_all_leaves(G, block_info)
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                        # 如果该跳转指令是条件跳转指令，将其与条件表达式相连接
                        if inst_info['condition']:
                            if inst_info['condition'] in instructions:
                                G.add_edge(inst_instID_dict[inst_info['condition']], inst_id, edge_type='Data')
                            if inst_info['condition'] in function_params:
                                G.add_edge(inst_info['condition'], inst_id, edge_type='Parameter')
                        
                        # 如果该跳转指令是无条件跳转指令
                        if len(inst_info['targets']) == 1:
                            br_target = inst_info['targets'][0]
                            G.add_edge(inst_id, br_target, edge_type='Control')
                        # 如果该跳转指令是条件跳转指令
                        if len(inst_info['targets']) == 2:
                            true_target = inst_info['targets'][0]
                            false_target = inst_info['targets'][1]
                            G.add_edge(inst_id, true_target, edge_type='Control')
                            G.add_edge(inst_id, false_target, edge_type='Control')

                    elif inst_info['opcode'] =='switch':
                        switch_condition = inst_info['condition']
                        # 建立switch指令与switch条件表达式的关系
                        if switch_condition in instructions:
                            G.add_edge(inst_instID_dict[switch_condition], inst_id, edge_type='Data')
                        if switch_condition in function_params:
                            G.add_edge(switch_condition, inst_id, edge_type='Parameter')
                        # 建立switch指令与case目标基本块的关系
                        for index,target in enumerate(inst_info['targets']):
                            case_target = 'block-' + target.replace('%', '')
                            G.add_edge(inst_id, case_target, edge_type='Control')

                    elif inst_info['opcode'] == 'unreachable':
                        leaves_with_depth = get_all_leaves(G, block_info)
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                    
                    elif inst_info['opcode'] == 'ret':
                        if inst_info['return_value'] in instructions:
                            G.add_edge(inst_instID_dict[inst_info['return_value']], inst_id, edge_type='Data')
                        elif inst_info['return_value'] in function_params:
                            G.add_edge(inst_info['return_value'], inst_id, edge_type='Parameter')

                        leaves_with_depth = get_all_leaves(G, block_info)
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                    
                    elif inst_info['opcode'] == 'invoke':
                        leaves_with_depth = get_all_leaves(G, block_info)
                        for leaf in leaves_with_depth:
                            G.add_edge(leaf[0], inst_id, edge_type='Sequential')
                        
                        for target in inst_info['targets']:
                            G.add_edge(inst_id, target, edge_type='Control')

                    # 建立指令节点与其他节点之间的关系
                    for operand in inst_info['operand_list']:
                        # operand_pos = 1
                        if is_constant(operand):
                            pass
                        if operand in global_list:
                            global_info = global_infos[operand]
                            type = global_info['type']
                            # 字符串类型的全局变量单独处理，不需要创建节点
                            if type != 'string' and type != 'struct':
                                define = global_info['raw_definition']
                                var_name = global_info['var_name']
                                linkage = global_info['linkage']
                                value = global_info['value']
                                value_lens = global_info['value_lens']
                                G.add_node(operand, define=define, var_name=var_name, value=value, linkage=linkage, type=type, value_lens=value_lens, is_global='true')
                                G.add_edge(operand, inst_id, edge_type='Global')
                        if operand in function_params:
                            G.add_edge(operand, inst_id, edge_type='Parameter')
                        if operand in instructions:
                            G.add_edge(inst_instID_dict[operand], inst_id, edge_type=f'operand')
                            # operand_pos += 1
                        
                    # if len(inst_info['structs'])>0:
                    #     for struct in inst_info['structs']:
                    #         G.add_node(struct, struct_name = struct, fileds = struct_infos[struct])
                    #         G.add_edge(struct, inst_id, edge_type='Struct')
                            
            list_edges = [(edge[0], edge[1], edge[2]['edge_type']) for edge in G.edges(data=True)]
            remove_redundant_edges = list(dict.fromkeys(list_edges))
            
            nodes_info = {node[0]:node[1] for node in G.nodes(data=True)}
            nodes = [key for key in nodes_info]

            function_iscg = {
                "nodes":nodes,
                "links":remove_redundant_edges,
                "nodes_info":nodes_info
            }
            iscg_json.setdefault(function_name, function_iscg)
            dump_json_file(iscg_json, iscg_path)
            creat_neo4j_graph(G,remove_redundant_edges,function_name)
        return 1,None
    except Exception as e:
        return -1, inst_info['instruction'] + ' ' + str(e)

def process_summary_file_wrapper(args):
    summary_path, global_path, struct_path, iscg_path = args
    try:
        status, error_msg = process_summary_file(summary_path, global_path, struct_path, iscg_path)
        return status, error_msg, summary_path
    except Exception as e:
        return 0, str(e), summary_path

def process_proj(proj_root):
    '''
    先为每个基本快生成一个子图，然后遍历每个基本块中的指令，建立基本块之间的指令流关系和控制流关系
    每一个基本快都有一个起始节点和一个终止节点，起始节点的属性包括基本块名称、基本块所包含的指令数量等，终止节点为该基本块的br指令或者ret指令。
    指令节点的属性包括指令ID、指令内容、指令操作码、基本快名称、指令定义的变量、指令中的常量或者符号等
    若该指令为基本块的入口指令，则将该指令与起始节点之间建立顺序流关系
    指令流关系的属性包括数据流方向、数据流类型、数据流大小等
    控制流关系的属性包括控制流方向、控制流类型等
    若该指令与该基本块中的任何指令之间都不存在数据流关系，则将该指令与起始节点之间建立顺序流关系
    br分支指令与其他基本块的起始节点相连接
    '''
    proj_name = os.path.basename(proj_root)
    summary_paths = collect_json_files(proj_root)
    iscg_proj_root = os.path.join(r'/home/lab314/cjw/similarity/datasets/source/iscg',proj_name)
    os.makedirs(iscg_proj_root,exist_ok=True)
    log_path = os.path.join(iscg_proj_root, 'log.txt')
    setup_logger(log_path)
    logging.info(f"Start processing project: {proj_name}")

    task_args = []
    for summary_path in summary_paths:
        global_path = summary_path.replace('/norm_summary/','/global_info/').replace('_info_summary.json','_globals.json')
        struct_path = summary_path.replace('/norm_summary/','/struct_info/').replace('_info_summary.json','_structs.json')
        iscg_path   = summary_path.replace('/norm_summary/','/iscg/').replace('_info_summary.json','_iscg.json')

        if all([
                os.path.exists(summary_path),
                os.path.exists(global_path),
                os.path.exists(struct_path),
                not os.path.exists(iscg_path)
            ]):
            task_args.append((summary_path, global_path, struct_path, iscg_path))
    

    # 使用进程池处理
    with Pool(processes=1) as pool:
        results = pool.imap_unordered(process_summary_file_wrapper, task_args)
        success_count = 0
        with tqdm(total=len(task_args), 
                    desc=f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]Processing {proj_name}",
                    leave=False) as pbar:
            for status, error_msg, summary_path in results:
                if status == 1:
                    success_count += 1
                else:
                    logging.error(f"Error processing {summary_path}: {error_msg}")
                pbar.update(1)

        logging.info(f"Finished project: {proj_name}, Success: {success_count}/{len(task_args)}")
        logging.info("-" * 60)

if __name__ == '__main__':
    process_proj(r'/home/lab314/cjw/similarity/datasets/source/norm_summary/MayaPosch_____NymphCast')
    # for proj in os.listdir(summary_root):
    #     proj_root = os.path.join(summary_root, proj)
    #     process_proj(proj_root)