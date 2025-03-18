import json
import time 

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

path = r"E:\Desktop\similarity\global_info\arm32-clang-5.0-O0_curl_global_info.json"
global_infos = load_json_file(path)
operand = "%19 = call i32 @curl_getenv(i8* getelementptr inbounds ([8 x i8], [8 x i8]* @global_var_44f4e, i32 0, i32 0)), !insn.addr !9"


if '@' in operand:
    t0 = time.time()
    global_var_list = [key for key, _ in global_infos.items()]
    list_operand= operand.split(" ")
    global_var = [var.replace(',', '') for var in list_operand if '@' in var]
    print(list(set(global_var) & set(global_var_list)))
    print(time.time() - t0)

if '@' in operand:
    t1 = time.time()
    list_operand= operand.replace(',', '').split(" ")
    global_var = [var for var in list_operand if '@' in var]
    print(set(global_var) & set(global_var_list))
    print(time.time() - t1)