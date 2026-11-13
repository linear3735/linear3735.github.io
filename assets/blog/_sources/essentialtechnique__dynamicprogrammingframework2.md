# 动态规划解题套路框架
url: https://labuladong.online/zh/algo/essential-technique/dynamic-programming-framework-2/
folder: 动态规划基本技巧

提到的力扣题号: 322, 509

## 这节的小标题
- 一、斐波那契数列
- 暴力递归
- 带备忘录的递归解法
- 自顶向下 vs 自底向上
- dp 数组的迭代（递推）解法
- 拓展延伸
- 二、凑零钱问题
- 暴力递归
- 带备忘录的递归
- dp 数组的迭代解法
- 三、最后总结

## 复杂度结论
- 递归算法的时间复杂度怎么计算？就是用子问题个数乘以解决一个子问题需要的时间
- 所以，这个算法的时间复杂度为二者相乘，即 O(2n)O(2^n)O(2n)，指数级别，爆炸
- 所以，本算法的时间复杂度是 O(n)O(n)O(n)，比起指数级复杂度的暴力算法，已经非常高效了
- 递归算法的时间复杂度分析：子问题总数 x 解决每个子问题所需的时间
- 对于这种情况，我们一般的做法是按照最坏的情况估算一个时间复杂度的上界
- 接下来看每个子问题的复杂度，由于每次递归包含一个 for 循环，复杂度为 O(k)O(k)O(k)，相乘得到总时间复杂度为 O(kn)O(k^n)O(kn)，指数级别
- 处理一个子问题的时间不变，仍是 O(k)O(k)O(k)，所以总的时间复杂度是 O(kn)O(kn)O(kn)
- 用空间换时间的思路，是降低时间复杂度的不二法门，除此之外，试问，还能玩出啥花活？

## 涉及的关键术语
- amount, memo, base, case, coins, table, GoJavaJavaScriptPython, fib, coin, coinChange, cases, result, Arrays, fill, res, min
