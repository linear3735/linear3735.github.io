# 经典动态规划：编辑距离
url: https://labuladong.online/zh/algo/dynamic-programming/edit-distance/
folder: 子序列类型问题

提到的力扣题号: 72

## 这节的小标题
- 一、思路
- 二、代码详解
- 三、动态规划优化
- 备忘录解法
- DP table 解法
- 四、扩展延伸

## 复杂度结论
- 还有一个细节，既然每个 dp[i][j] 只和它附近的三个状态有关，空间复杂度是可以压缩成 O(min(M,N))O(min(M, N))O(min(M,N)) 的（M，N 是两个字符串的长度）

## 涉及的关键术语
- String, case, length, min, base, val, System, out, charAt, memo, choice, GoJavaJavaScriptPython, table, println, word1, word2
