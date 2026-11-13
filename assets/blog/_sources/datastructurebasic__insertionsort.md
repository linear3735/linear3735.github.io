# 运用逆向思维：插入排序
url: https://labuladong.online/zh/algo/data-structure-basic/insertion-sort/
folder: 十大排序算法原理及可视化

提到的力扣题号: 912

## 这节的小标题
- 反向思维
- 初始有序度越高，效率越高

## 复杂度结论
- 时间复杂度是 O(n2)O(n^2)O(n2)，具体的操作次数和选择排序类似，是一个等差数列求和，大约是 n2/2n^2/2n2/2 次
- 如果输入数组已经有序，或者仅有个别元素逆序，那么插入排序的内层 for 循环几乎不需要执行元素交换，所以时间复杂度接近 O(n)O(n)O(n)
- 的效率就会很低，内层 for 循环每次都要对 nums[0..sortedIndex-1] 的所有元素进行交换，算法的总时间复杂度就接近 O(n2)O(n^2)O(n2)
- 插入排序的空间复杂度是 O(1)O(1)O(1)，是原地排序算法

## 涉及的关键术语
- nums, sortedIndex, while, GoJavaJavaScriptPython, sort, length, Sort, Array912, minVal, comments, labuladong
