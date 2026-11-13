# 小而美的算法技巧：前缀和数组
url: https://labuladong.online/zh/algo/data-structure/prefix-sum/
folder: 手把手刷数组算法

提到的力扣题号: 303, 304

## 这节的小标题
- 一维数组中的前缀和
- 二维矩阵中的前缀和
- 拓展延伸

## 复杂度结论
- 这个解法每次调用 sumRange 函数时，都要进行一次 for 循环遍历，时间复杂度为 O(N)O(N)O(N)，而 sumRange 的调用频率可能非常高，所以这个算法的效率很低
- 正确的解法是使用前缀和技巧进行优化，使得 sumRange 函数的时间复杂度为 O(1)O(1)O(1)：
- 这样，sumRange 函数仅仅需要做一次减法运算，避免了每次进行 for 循环调用，最坏时间复杂度为常数 O(1)O(1)O(1)
- 当然，你可以用一个嵌套 for 循环去遍历这个矩阵，但这样的话 sumRegion 函数的时间复杂度就高了，你算法的格局就低了
- 这样，sumRegion 函数的时间复杂度也用前缀和技巧优化到了 O(1)O(1)O(1)，这是典型的「空间换时间」思路

## 涉及的关键术语
- nums, preSum, sumRange, left, NumArray, sumRegion, right, matrix, length, NumMatrix, numArray, row1, col1, row2, col2, numMatrix
