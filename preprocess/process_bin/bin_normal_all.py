import re
import os
import json
import time
import copy
from tqdm import tqdm
from utils.nomal_const import nomalize_consts
from utils.nomal_function_name import nomalize_function_name
from utils.nomal_global import nomalize_global_var
from utils.nomal_structs import nomalize_structs
from utils.nomal_var import nomalize_var
from utils.nomal_label import nomalize_label

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def dump_json_file(data, file_path):
    with open(file_path, 'wb+') as f:
        json_data = json.dumps(data)
        f.write(json_data.encode('utf-8'))

def collect_json_files(proj_root):
    json_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if file.endswith('.json'):
                json_paths.append(full_path)
    
    return json_paths

def processing_single_proj(proj_path):
    proj_name = os.path.basename(proj_path)
    task_args = []
    json_paths = collect_json_files(proj_path)
    for json_path in json_paths:
        out_path = json_path.replace('/summary/','/norm_summary/')
        if all([
            os.path.exists(json_path), 
            not os.path.exists(out_path)
        ]):
            task_args.append((json_path,out_path))
    pbar = tqdm(total=len(task_args), desc=f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]Processing {proj_name}",leave=False)
    for json_path, out_path in task_args:
        out_dir,out_name = os.path.split(out_path)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        data = load_json_file(json_path)

        nomalize_var(data)
        nomalize_structs(data)
        nomalize_consts(data)
        nomalize_function_name(data)
        nomalize_global_var(data)
        nomalize_label(data)
        
        dump_json_file(data, out_path)
        pbar.update(1)
    pbar.close()

def main():
    proj_summaries_dir = r'/home/lab314/cjw/similarity/datasets/bin/clang/summary'
    for proj in os.listdir(proj_summaries_dir):
        proj_path = os.path.join(proj_summaries_dir, proj)
        processing_single_proj(proj_path)
if __name__ == '__main__':
    main()
    # processing_single_proj(r'/home/lab314/cjw/similarity/datasets/bin/clang/summary/MayaPosch_____NymphCast')