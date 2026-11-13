# 分治算法解题套路框架
url: https://labuladong.online/zh/algo/essential-technique/divide-and-conquer/
folder: 第零章、核心刷题框架汇总

## 这节的小标题
- 分治思想
- 分治算法

## 复杂度结论
- 假设你的原问题规模是 N=a+bN=a+bN=a+b，如果用一个 O(N2)O(N^2)O(N2) 的算法求解，总的时间复杂度就是 O((a+b)2)O((a+b)^2)O((a+b)2)
- 把问题分解后进行求解，相比于不分解直接求解，时间复杂度更低
- 比如 桶排序算法，桶排序的思路是把待排序数组分成若干个桶，然后对每个桶分别进行插入排序，最后把所有有序桶合并，这样时间复杂度能降到 O(n)O(n)O(n)
- 直接用 插入排序 的复杂度是 O(n2)O(n^2)O(n2)，而分解后再用插入排序，总的时间复杂度就能降到 O(n)O(n)O(n)，这种才算分治算法

## 涉及的关键术语
- fib, root, count, Merge, Sorted, base, case, leftCount, rightCount, Lists23, Two, Lists21, aaa, bbb, TreeNode, left
