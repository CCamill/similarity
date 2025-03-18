import os
import subprocess
import time
from tqdm import tqdm
from multiprocessing import Pool

CLANG_O = r'/home/lab314/cjw/similarity/datasets/bin/clang_o'
CLANG_LL = r'/home/lab314/cjw/similarity/datasets/bin/clang_ll'

def o2ll(o_path, ll_path):
    cmd = f"/home/lab314/cjw/similarity/RetDec/bin/retdec-decompiler {o_path} -o {ll_path}"
    error_msg = ""
    code = 0
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(timeout=200)
        code = proc.returncode
        if code != 0:
            error_msg = stderr.strip() or stdout.strip() or "Unknown error"
    except subprocess.TimeoutExpired as e:
        code = 1
        error_msg = f"TimeoutExpired: {str(e)}"
    except Exception as e:
        code = 1
        error_msg = f"Unexpected error: {str(e)}"
    return code, error_msg

def process_task(args):
    o_path, ll_path, log_path = args
    lldir = os.path.dirname(ll_path)
    os.makedirs(lldir, exist_ok=True)
    code, error_msg = o2ll(o_path, ll_path)
    if code != 0:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        error_line = f"{timestamp} - Error processing {o_path} [Code {code}]: {error_msg}\n"
        try:
            with open(log_path, 'a') as f:
                f.write(error_line)
        except Exception as e:
            print(f"Failed to write to log {log_path}: {e}")
    return code

def process_single_proj(proj_o_dir):
    num_processes = 2
    pool = Pool(processes=num_processes)

    proj = os.path.basename(proj_o_dir)
    log_path = os.path.join(CLANG_LL, proj, 'log.txt')
    if os.path.exists(log_path):
        print(f"Skipping project {proj} (log exists)")
        return
    
    print(f"\n[+] Processing project: {proj}")
    tasks = []
    
    for opti in os.listdir(proj_o_dir):
        opti_dir = os.path.join(proj_o_dir, opti)
        if not os.path.isdir(opti_dir):
            continue
        
        for o_file in os.listdir(opti_dir):
            if o_file.endswith('.o'):
                o_path = os.path.join(opti_dir, o_file)
                file_name = o_file.rsplit('.', 1)[0]
                ll_dir = os.path.join(CLANG_LL, proj, opti, file_name)
                ll_file = o_file.replace('.o', '.c')
                ll_path = os.path.join(ll_dir, ll_file)
                
                if not os.path.exists(ll_path):
                    tasks.append((o_path, ll_path, log_path))
    
    
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if not tasks:
        print(f"[!] No tasks for project {proj}")
        open(log_path, 'a').close()
        return
    
    
    
    pbar = tqdm(total=len(tasks), desc=f"{proj} Progress")
    results = []
    
    for task in tasks:
        res = pool.apply_async(
            process_task,
            args=(task,),
            callback=lambda _: pbar.update(1)
        )
        results.append(res)
    
    for res in results:
        res.wait()
    
    pbar.close()
    open(log_path, 'a').close()
    print(f"[+] Completed {len(tasks)} tasks for {proj}")
    pool.close()
    pool.join()

def main():
    for proj in os.listdir(CLANG_O):
        proj_o_dir = os.path.join(CLANG_O, proj)
        if not os.path.isdir(proj_o_dir):
            continue
        process_single_proj(proj_o_dir)
        
if __name__ == '__main__':
    # main()
    proj_o_dir = r'/home/lab314/cjw/similarity/datasets/bin/clang_o/MayaPosch_____NymphCast'
    process_single_proj(proj_o_dir)