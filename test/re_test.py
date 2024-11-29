import re

global_vars = """
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

# 正则表达式模式
pattern = r'@\w+ = (?:external )?(?:local_unnamed_addr )?(?:constant )?(?:global )?(\[(\d+) x (i\d+)\](?: c"([^"]*)")?|\* @\w+)?(?: (\d+))?'

matches = re.finditer(pattern, global_vars)

for match in matches:
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

        print(f"Variable: {var_name}, Type: {array_type if array_type else var_type}, Value: {var_value}")