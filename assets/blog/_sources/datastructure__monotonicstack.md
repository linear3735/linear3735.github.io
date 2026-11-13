# 单调栈算法模板解决三道例题
url: https://labuladong.online/zh/algo/data-structure/monotonic-stack/
folder: 经典队列/栈算法

提到的力扣题号: 496, 503, 739

## 这节的小标题
- 单调栈模板
- 问题变形
- 496. 下一个更大元素 I
- 739. 每日温度
- 如何处理环形数组

## 复杂度结论
- 但是暴力解法的时间复杂度是 O(n2)O(n^2)O(n2)
- 这个算法的时间复杂度不是那么直观，如果你看到 for 循环嵌套 while 循环，可能认为这个算法的复杂度也是 O(n2)O(n^2)O(n2)，但是实际上这个算法的复杂度只有 O(n)O(n)O(n
- 分析它的时间复杂度，要从整体来看：总共有 n 个元素，每个元素都被 push 入栈了一次，而最多会被 pop 一次，没有任何冗余操作
- 进阶：你可以设计一个时间复杂度为 O(nums1.length + nums2.length) 的解决方案吗？
- 这样，就可以巧妙解决环形数组的问题，时间复杂度 O(N)O(N)O(N)

## 涉及的关键术语
- nums2, nums1, length, GoJavaJavaScriptPython, nums, Stack, while, temperatures, isEmpty, peek, res, nextGreaterElement, Solution, arr, index, Next
