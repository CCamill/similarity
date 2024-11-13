import json
import os
import sys
import networkx as nx
import matplotlib.pyplot as plt
from py2neo import Node, Relationship, Graph, NodeMatcher, RelationshipMatcher
from py2neo.bulk import create_relationships

summary_path = r'E:\Desktop\similarity\summary_files'

def main():
    test_graph = Graph('bolt://localhost:7687',auth=('neo4j','chang8677'),name='neo4j')

    
    G = nx.MultiDiGraph()
    summary_file_paths = []
    for file in os.listdir(summary_path):
        summary_file_paths.append(os.path.join(summary_path, file))

    for summary_file_path in summary_file_paths:
        print('processing file: ', summary_file_path)
        with open(summary_file_path, 'r') as f:
            summary_data = json.load(f)
        instructions = []
        inst_instID_dict = dict()
        inst_instOp_dict = dict()
        for function in summary_data:

            for block_info in function['function_blocks']:
                for inst_info in block_info['block_insts']:
                    instructions.append(inst_info['instruction'])

                    # 指令到指令ID的映射
                    inst_instID_dict[inst_info['instruction']] = inst_info['inst_id']
                    # 指令到指令操作码的映射
                    inst_instOp_dict[inst_info['instruction']] = inst_info['opcode']

                    # neo4j 图数据库中创建指令节点
                    inst_node = Node(function['function_name'],inst_id = inst_info['inst_id'], instruction=inst_info['instruction'], opcode=inst_info['opcode'])
                    test_graph.create(inst_node)

                    # nx 图数据库中创建指令节点
                    G.add_node(inst_info['inst_id'], instruction=inst_info['instruction'], opcode=inst_info['opcode'])
        # 建立指令之间的数据流
        for function in summary_data:
            for block_info in function['function_blocks']:
                for inst_info in block_info['block_insts']:
                    if inst_info['opcode'] == 'br':
                        pass
                    try:
                        if inst_info['opcode'] not in ('ret','unreachable'):
                            operand_list = inst_info['operand_list']
                            [G.add_edge(inst_instID_dict[inst_info['instruction']], inst_instID_dict[operand]) for operand in operand_list if operand in instructions]
                    except:
                        print('Error in processing instruction: ', inst_info)
        for function in summary_data:
            for edge in G.edges(data=True):
                label = function['function_name']
                rel_str = f'MATCH (source:{label}{{inst_id:{edge[0]}}}) MATCH (target:{label}{{inst_id:{edge[1]}}}) CREATE (source)-[r:data_flow]->(target)'
                test_graph.run(rel_str)

                print(edge)
        
    #nx.draw(G, with_labels=True, font_weight='bold')
    #plt.show()
if __name__ == '__main__':
    main()