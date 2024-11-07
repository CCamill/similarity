import os
import subprocess
from multiprocessing import Pool
from tqdm import tqdm

def extract_time(out: str):
    # 从输出中提取提取所花费的时间
    sig_s = "Time for extraction: "
    sig_e = "secs."
    out = out[out.find(sig_s) + len(sig_s) :]
    out = out[: out.find(sig_e)]
    return float(out)

def binary_lifting(input_file, out_dir):
    input_file_name = os.path.basename(input_file)
    if input_file_name.endswith('.exe'):
        binary_name = os.path.splitext(input_file_name)[0]
    else:
        binary_name = input_file_name

    out_path = os.path.join(out_dir,binary_name)
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    out_file = os.path.join(out_path, binary_name+'.c')
    dbg_info_file = os.path.join(out_path, binary_name + "_dbg")
    cmd = f'RetDec-v5\\bin\\retdec-decompiler.exe {input_file} -o {out_file} -s'
    proc = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE)
    out, _ = proc.communicate()
    code = proc.returncode  # 获取返回代码
    # 检查返回代码和输出文件是否存在
    if (code != 0) or (not os.path.exists(out_file)):
        print("[=] " + cmd)
        code = code if code is not None else -1
        return code, input_file
    
    cost = extract_time(out)  # 提取时间
    return None, cost  # 返回成功标志和耗时

def binary_lifting_wrapper(args):
    return binary_lifting(*args)



def main():
    binary_path = 'E:\\Desktop\\IR2SOG\\datasets\\binary_files'
    out_dir =  'E:\\Desktop\\IR2SOG\\datasets\\binary_info'

    binary_files = os.listdir(binary_path)
    input_files = []
    for binary_file in binary_files:
        input_file = os.path.join(binary_path, binary_file)
        input_files.append(input_file)


    pbar = tqdm(total=len(input_files))
    p = Pool(processes=4)
    failed_list = []  # 失败列表
    time_cost = []  # 耗时列表
    


    for code,info in p.imap_unordered(
        binary_lifting_wrapper, 
        [
            (
                input_file,
                out_dir
            )
            for input_file in input_files
        ]

    ):
        if code is not None:
            failed_list.append((input_file))
            print("==========================================")
            print(f"Fail to process {input_file} (code: {code}). ")
            print("==========================================")
        else:
            time_cost.append(info)
        pbar.update(1)
    p.close()
    pbar.close()
    [print(f"failed_file:{failed_file}") for failed_file in failed_list]
    print("Failed Count: ", len(failed_list))  # 打印失败数量
    print("Tot. Extraction Time: %.2f" % (sum(time_cost)))  # 打印总提取时间

if __name__ == '__main__':
    main()