from functools import partial
import os
import subprocess
from multiprocessing import Pool
from tqdm import tqdm
import time
import gc

def collect_ll_files(proj_root):
    ll_paths = []
    for root, _, files in os.walk(proj_root):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if file.endswith('.ll'):
                ll_paths.append(full_path)
    
    return ll_paths

def process_single_proj(proj_root):
    ll_paths = collect_ll_files(proj_root)

    pbar =  tqdm(total=len(ll_paths), desc=f"{proj_root} Progress")
    for ll_path in ll_paths:
        bc_path = ll_path.replace('.ll', '.bc')
        
        dir_path, file_name = os.path.split(ll_path)
        output_dir, _ = os.path.split(dir_path.replace(r'/clang_ll/', r'/struct_info/'))
        out_path = os.path.join(output_dir,file_name.replace(".ll","_structs.json"))

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if os.path.exists(out_path):
            continue
        # os.system(f'llvm-dis {bc_path} -o {ll_path}')
        cmd = f"/home/lab314/cjw/similarity/cpp_utils/ex_struct {ll_path} {out_path}"
        try:
            proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=60)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            code = 1
            print(f"[-] Timeout when processing command: {cmd}")
        pbar.update(1)
    pbar.close()

def main():
    ll_root = r'/home/lab314/cjw/similarity/datasets/bin/clang/clang_ll'
    for proj in os.listdir(ll_root):
        proj_root = os.path.join(ll_root, proj)
        process_single_proj(proj_root)
if __name__ == '__main__':
    main()
    # process_single_proj(r'/home/lab314/cjw/similarity/datasets/bin/clang/clang_ll/OpenMathLib_____OpenBLAS')