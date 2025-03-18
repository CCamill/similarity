import os
import subprocess
from multiprocessing import Pool
from tqdm import tqdm
import time
import gc

def get_binary_name(binary_path):
    """Extracts the binary name from the path, removing the extension if it's .exe."""
    binary_name = os.path.basename(binary_path)
    return os.path.splitext(binary_name)[0] if binary_name.endswith('.exe') else binary_name

def extract_time(out: str):
    """Extracts the time taken for extraction from the output string."""
    sig_s = "Time for extraction: "
    sig_e = "secs."
    out = out[out.find(sig_s) + len(sig_s):]
    out = out[:out.find(sig_e)]
    return float(out)

def binary_lifting(binary_path, output_dir):
    """Performs binary lifting using retdec-decompiler."""
    binary_name = get_binary_name(binary_path)
    out_path = os.path.join(output_dir, binary_name)

    cmd = f"/home/lab314/cjw/similarity/RetDec/bin/retdec-decompiler {binary_path} -o {os.path.join(out_path, binary_name + '.c')}"

    try:
        proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=150)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        code = 1
        print(f"[-] Timeout when processing command: {cmd}")
    
    return code

def binary_lifting_wrapper(args):
    """Wrapper function for multiprocessing."""
    return binary_lifting(*args)

def process_binaries(bin_proj_path, output_dir):
    """Processes all binaries in a given project path."""
    failed_list_path = os.path.join(output_dir, 'failed_list.txt')
    if os.path.exists(failed_list_path):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] {bin_proj_path} already exists")
        return

    binary_paths = [
        os.path.join(bin_proj_path, binary)
        for binary in os.listdir(bin_proj_path)
        if not os.path.exists(os.path.join(output_dir, get_binary_name(binary)))
    ]

    for binary_path in binary_paths:
        os.makedirs(os.path.join(output_dir, get_binary_name(binary_path)), exist_ok=True)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] start to process {bin_proj_path}")
    with Pool(processes=2) as pool:
        pbar = tqdm(total=len(binary_paths), leave=True)
        failed_list = []
        success_num = 0
        for code in pool.imap_unordered(binary_lifting_wrapper, [(binary_path, output_dir) for binary_path in binary_paths]):
            if code == 0:
                success_num += 1
            else:
                failed_list.append(binary_path)
                # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Fail to process {binary_path} (code: {code}).")
            pbar.update(1)
            gc.collect()
        pbar.close()

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] success_num: {success_num}/{len(binary_paths)}")
    with open(failed_list_path, 'w') as f:
        for binary_path in failed_list:
            f.write(binary_path + '\n')

if __name__ == '__main__':
    binaries = r'/home/lab314/cjw/ghcc/binaries'
    binary_lls = r'/home/lab314/cjw/similarity/datasets/bin/bin_lls'

    for author_name in os.listdir(binaries):
        author_path = os.path.join(binaries, author_name)
        if not os.listdir(author_path):
            continue
        for proj_name in os.listdir(author_path):
            bin_proj_path = os.path.join(author_path, proj_name)
            if not os.listdir(bin_proj_path):
                continue
            output_dir = os.path.join(binary_lls, f"{author_name}_____{proj_name}")
            os.makedirs(output_dir, exist_ok=True)
            process_binaries(bin_proj_path, output_dir)