import os
import openai
import time 
# 加载API密钥


def get_global_var_info(global_vars):
    messages = [
        {"role": "system", "content": "你是一个LLVM IR分析助手，能够从LLVM IR代码中提取变量信息。"},
        {"role": "user", "content": f"请提取以下LLVM IR变量的信息：\n{global_vars}"}
    ]
    system_message = "你是一个LLVM IR分析助手，能够从LLVM IR代码中提取变量信息。"
    user_message = f"请提取以下LLVM IR变量的信息：\n{global_vars}"
    prompt = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n{system_message}\n\n{user_message}"

    response = openai.completions.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        temperature=0,
        max_tokens=1500
    )

    return response['choices'][0]['message']['content']

# 示例LLVM IR变量
llvm_ir = """
@8 = external local_unnamed_addr global i32
@global_var_e9074 = local_unnamed_addr global i32 0
@global_var_3c407 = constant [3 x i8] c"wb\00"
@global_var_eb1b0 = global i32 0
@global_var_490ac = external constant i32
@global_var_eb240 = local_unnamed_addr global i32 0
@global_var_631ac = local_unnamed_addr constant i32 262145
@global_var_4a65c = constant [24 x i8]* @global_var_44b4a
@global_var_4a6a4 = constant [25 x i8]* @global_var_1a323
"""

# 调用函数
info = get_global_var_info(llvm_ir)
print(info)