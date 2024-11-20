def longest_common_substring(strs):
    # 如果字符串列表为空，返回空字符串
    if not strs:
        return ""

    # 初始化最长公共子串为第一个字符串
    lcs = strs[0]

    # 遍历字符串列表，更新最长公共子串
    for i in range(1, len(strs)):
        # 初始化当前字符串的最长公共子串为一个空字符串
        current_lcs = ""
        # 动态规划找出lcs和strs[i]的最长公共子串
        m, n = len(lcs), len(strs[i])
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i1 in range(1, m + 1):
            for j1 in range(1, n + 1):
                if lcs[i1 - 1] == strs[i][j1 - 1]:
                    dp[i1][j1] = dp[i1 - 1][j1 - 1] + 1
                    if dp[i1][j1] > len(current_lcs):
                        current_lcs = lcs[i1 - dp[i1][j1]:i1 - 1]
                else:
                    dp[i1][j1] = 0
        # 更新最长公共子串
        lcs = current_lcs

    # 返回所有字符串的公共最长子串
    return lcs

# 示例
strs = ["@global_var_2bec7", "@global_var_2f913", "@global_var_4c05c"]
print(longest_common_substring(strs))


operand = "%17 = call i32 @create_hostcache_id(i32 ptrtoint (i8** @global_var_1e8c9 to i32), i32 %arg3, i32* nonnull %stack_var_-302, i32 262), !insn.addr !19265"
globals = [g for g in operand.split(' ') if g.startswith('@')]
print(operand.split(' '))
print(globals)