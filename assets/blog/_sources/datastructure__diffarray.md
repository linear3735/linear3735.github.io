# 小而美的算法技巧：差分数组
url: https://labuladong.online/zh/algo/data-structure/diff-array/
folder: 手把手刷数组算法

提到的力扣题号: 370, 1094, 1109

## 这节的小标题
- 算法实践
- 拓展延伸

## 复杂度结论
- 路很容易，你让我给区间 nums[i..j] 加上 val，那我就一个 for 循环给它们都加上呗，还能咋样？这种思路的时间复杂度是 O(N)O(N)O(N)，由于这个场景下对 nums 的修改非常频繁，所以效率会很低下
- 处理区间问题的常见问题，终极答案是 线段树 这种数据结构，它可以在 O(log⁡N)O(\log N)O(logN) 的时间复杂度内完成任意长度的区间增减和区间查询操作

## 涉及的关键术语
- nums, diff, length, Difference, val, trips, GoJavaJavaScriptPython, bookings, capacity, trip, preSum, increment, result, update, firsti, lasti
