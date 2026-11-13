# 动态规划设计：最长递增子序列
url: https://labuladong.online/zh/algo/dynamic-programming/longest-increasing-subsequence/
folder: 动态规划基本技巧

提到的力扣题号: 300, 354

## 这节的小标题
- 一、动态规划解法
- 二、二分查找解法
- 三、拓展到二维

## 复杂度结论
- t Increasing Subsequence，简写 LIS）是非常经典的一个算法问题，比较容易想到的是动态规划解法，时间复杂度 O(N2)O(N^2)O(N2)，我们借这个问题来由浅入深讲解如何找状态转移方程，如何写出动态规划解法
- 比较难想到的是利用二分查找，时间复杂度是 O(NlogN)O(NlogN)O(NlogN)，我们通过一种简单的纸牌游戏来辅助理解这种巧妙的解法
- - 你能将算法的时间复杂度降低到 O(n log(n)) 吗?
- 至此，这道题就解决了，时间复杂度 O(N2)O(N^2)O(N2)
- 这个解法的时间复杂度为 O(NlogN)O(NlogN)O(NlogN)，但是说实话，正常人基本想不到这种解法（也许玩过某些纸牌游戏的人可以想出来）
- 这样的话算法的时间复杂度为 O(NlogN)O(NlogN)O(NlogN)，因为排序和计算 LIS 各需要 O(NlogN)O(NlogN)O(NlogN) 的时间，加到一起还是 O(NlogN)O(N
- gN) 的时间，加到一起还是 O(NlogN)O(NlogN)O(NlogN)；空间复杂度为 O(N)O(N)O(N)，因为计算 LIS 的函数中需要一个 top 数组

## 涉及的关键术语
- nums, NlogN, LIS, envelopes, length, case, base, GoJavaJavaScriptPython, lengthOfLIS, top, piles, mid, Solution, poker, left, Longest
