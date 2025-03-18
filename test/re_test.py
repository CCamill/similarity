import re

inst = r"i8* inttoptr (i32 67108864 to i8*)"

patt = r'(?:i8|i6|i32|i64)\s+\d+'
has_const = re.search(patt, inst)
result = re.findall(patt, inst).pop()
type_part = result.split(' ')[0]
number_part = result.split(' ')[1]
print(has_const)
if has_const:
    print(type_part)
    print(number_part)

def replace_func(match):
    type_part = match.group(1)  # 类型部分（i8、i32等）
    number_part = match.group(2)  # 数字部分
    return f"{type_part} <const>"

# inst = "switch i8 %43, label %block_41 [\n    i8 32, label %block_14\n    i8 35, label %block_17\n    i8 42, label %block_35\n    i8 43, label %block_15\n    i8 45, label %block_16\n    i8 46, label %block_18\n    i8 48, label %block_32\n    i8 49, label %block_34\n    i8 50, label %block_34\n    i8 51, label %block_34\n    i8 52, label %block_34\n    i8 53, label %block_34\n    i8 54, label %block_34\n    i8 55, label %block_34\n    i8 56, label %block_34\n    i8 57, label %block_34\n    i8 76, label %block_28\n    i8 79, label %block_31\n    i8 104, label %block_26\n    i8 108, label %block_27\n    i8 113, label %block_29\n    i8 122, label %block_30\n  ]"
# print(re.sub(r'(i8|i32|i64|i16)\s+(\d+)', replace_func, inst))


""" for match in matches:
    if match:
        var_name = match.group(0).split(' = ')[0]
        var_type = match.group(1)
        var_value = match.group(3) or match.group(4)
        
        # 处理数组类型
        if var_type and 'x' in var_type:
            array_size, array_type = var_type.split(' x ')
            if array_size.isdigit():
                array_size = int(array_size)
                array_type = 'i' + array_type
                if match.group(2):  # 如果有值
                    var_value = match.group(2)
                else:
                    var_value = 'null'  # 没有初始化值
        elif var_type and var_type.startswith('i'):  # 处理整型
            array_type = var_type
            if match.group(4):  # 如果有值
                var_value = match.group(4)
            else:
                var_value = 'null'  # 没有初始化值
        else:
            array_type = None

        print(f"Variable: {var_name}, Type: {array_type if array_type else var_type}, Value: {var_value}") """