import os
import subprocess
from tqdm import tqdm

CLANG_ASM = r'/home/lab314/cjw/similarity/datasets/bin/clang_asm'
CLANG_O = r'/home/lab314/cjw/similarity/datasets/bin/clang_o'
CLANG_LL = r'/home/lab314/cjw/similarity/datasets/bin/clang_ll'

def asm2o(asm_path, o_path):
    """
    asm_path: the path of the assembly file
    o_path: the path of the output file
    """
    cmd = f"clang -c -o {o_path} {asm_path}"
    try:
        proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=60)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        code = 1
        print(f"[-] Timeout when processing command: {cmd}")
    return code


def main():
    for proj in os.listdir(CLANG_ASM):
        log_path = os.path.join(CLANG_O, proj, 'log.txt')
        if os.path.exists(log_path):
            continue
        asm_dir = os.path.join(CLANG_ASM, proj,  'ir_files')
        
        if not os.path.exists(asm_dir):
            continue
        print(f"[+] Processing {proj}")
        for opti in os.listdir(asm_dir):
            opti_dir = os.path.join(asm_dir, opti)
            o_opti_dir = os.path.join(CLANG_O, proj, opti)
            ll_opti_dir = os.path.join(CLANG_LL, proj, opti)
            print(f"[+] Processing {opti}")
            pbar = tqdm(total=len(os.listdir(opti_dir)))
            if not os.path.exists(o_opti_dir):
                os.makedirs(o_opti_dir)
            for asm_file in os.listdir(opti_dir):
                file_name = asm_file.split('.')[0]
                if asm_file.endswith('.s'):
                    asm_path = os.path.join(opti_dir, asm_file)
                    o_path = os.path.join(o_opti_dir, asm_file.replace('.s', '.o'))
                    code = asm2o(asm_path, o_path)
                    if code != 0:
                        # print(f"[-] Error when processing {asm_path}")
                        continue
                pbar.update(1)
            pbar.close()
        os.system(f'touch {log_path}')

if __name__ == '__main__':
    main()