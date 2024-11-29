import json
import os
import networkx as nx
from py2neo import Node, Graph
from collections import defaultdict

class GraphProcessor:
    def __init__(self, iscg_dir, summary_path, global_info_path, neo4j_url, neo4j_auth):
        self.iscg_dir = iscg_dir
        self.summary_path = summary_path
        self.global_info_path = global_info_path
        self.test_graph = Graph(neo4j_url, auth=neo4j_auth)
        self.iscg_json = {}

    def dfs_tree_edges(self, G, root):
        dfs_tree = nx.dfs_tree(G, root)
        depths = {node: 0 for node in G.nodes()}
        def calculate_depth(node, current_depth):
            depths[node] = current_depth
            for neighbor in dfs_tree.successors(node):
                if neighbor not in depths or depths[neighbor] == 0:
                    calculate_depth(neighbor, current_depth + 1)
        calculate_depth(root, 0)
        leaves_with_depth = [(node, depths[node]) for node in dfs_tree.nodes() if len(list(dfs_tree.successors(node))) == 0]
        return leaves_with_depth
    
    def load_data(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data

    def process_file(self, summary_file_path, global_info_path):
        summary_data = self.load_data(summary_data)
        global_infos = self.load_data(global_infos)
        global_var_list = [key for key, _ in global_infos.items()]
        instructions = []
        inst_instID_dict = dict()
        inst_instOp_dict = dict()
        inst_instVar_dict = dict()

        for function in summary_data:
            G = nx.MultiDiGraph()
            function_params = function['function_param_list']
            G.add_node(function['function_name'], node_id=function['function_name'], instruction=function['function_name'], function_params=function_params, bb_num=function['bb_num'])
            function_node = Node(function['function_name'], node_id=function['function_name'], instruction=function['function_name'])
            self.test_graph.create(function_node)

            # Process each block in the function
            for block_info in function['function_blocks']:
                self.process_block(G, block_info, function['function_name'], function_params, inst_instID_dict, inst_instOp_dict, inst_instVar_dict)

            # Process edges between blocks
            self.process_block_edges(G, function['function_name'])

            # Save the graph to ISCG JSON
            nodes_info = {node[0]: node[1] for node in G.nodes(data=True)}
            nodes = [key for key in nodes_info]
            self.iscg_json.setdefault(function['function_name'], {
                "nodes": nodes,
                "links": [(edge[0], edge[1], edge[2]['edge_type']) for edge in G.edges(data=True)],
                "nodes_info": nodes_info
            })

    def process_block(self, G, block_info, function_name, function_params, inst_instID_dict, inst_instOp_dict, inst_instVar_dict):
        # Process each instruction in the block
        for inst_info in block_info['block_insts']:
            self.process_instruction(G, inst_info, block_info['block_name'], function_name, inst_instID_dict, inst_instOp_dict, inst_instVar_dict)

    def process_instruction(self, G, inst_info, block_name, function_name, inst_instID_dict, inst_instOp_dict, inst_instVar_dict):
        # Create nodes and edges for the instruction
        inst_id = inst_info['inst_id']
        inst_opcode = inst_info['opcode']
        inst_instruction = inst_info['instruction']
        inst_node = Node(function_name, node_id=str(inst_id), instruction=inst_instruction, opcode=inst_opcode)
        self.test_graph.create(inst_node)
        G.add_node(inst_id, instruction=inst_instruction, opcode=inst_opcode)
        
        # Add edges based on instruction type
        if inst_opcode == 'br':
            # Handle branch instruction
            pass  # Add your logic here
        elif inst_opcode == 'switch':
            # Handle switch instruction
            pass  # Add your logic here
        elif inst_opcode in ['ret', 'unreachable']:
            # Handle return and unreachable instructions
            pass  # Add your logic here
        else:
            # Handle other instructions
            pass  # Add your logic here

        # Update dictionaries
        inst_instID_dict[inst_instruction] = inst_id
        inst_instOp_dict[inst_instruction] = inst_opcode
        inst_instVar_dict[inst_instruction] = inst_info['var_name']

    def process_block_edges(self, G, function_name):
        # Process edges between blocks
        pass  # Add your logic here

    def save_iscg(self):
        # Save ISCG JSON to file
        for function_name, data in self.iscg_json.items():
            iscg_path = os.path.join(self.iscg_dir, f"{function_name}_iscg.json")
            with open(iscg_path, 'wb+') as f:
                json_data = json.dumps(data)
                f.write(json_data.encode('utf-8'))

    def run(self):
        summary_file_paths = [os.path.join(self.summary_path, file) for file in os.listdir(self.summary_path)]
        global_info_files = {os.path.basename(file).split('_info_summary.json')[0]: os.path.join(self.global_info_path, file.split('_info_summary.json')[0] + '_global_info.json') for file in summary_file_paths}

        for summary_file_path, global_info_path in zip(summary_file_paths, global_info_files.values()):
            self.process_file(summary_file_path, global_info_path)
        self.save_iscg()

if __name__ == '__main__':
    iscg_dir = r'E:\\Desktop\\similarity\\iscg'
    summary_path = r'E:\Desktop\similarity\summary_files'    
    global_info_path = r"E:\\Desktop\\similarity\\global_info"
    neo4j_url = 'bolt://localhost:7687'
    neo4j_auth = ('neo4j', 'chang8677')

    processor = GraphProcessor(iscg_dir, summary_path, global_info_path, neo4j_url, neo4j_auth)
    processor.run()