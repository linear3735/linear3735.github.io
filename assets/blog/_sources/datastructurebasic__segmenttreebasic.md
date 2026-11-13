# 线段树核心原理及可视化
url: https://labuladong.online/zh/algo/data-structure-basic/segment-tree-basic/
folder: 二叉树结构的种种变换

## 这节的小标题
- 使用场景

## 复杂度结论
- 线段树可以在 O(log⁡N)O(\log N)O(logN) 的时间复杂度查询任意长度的区间元素聚合值，在 O(log⁡N)O(\log N)O(logN) 的时间复杂度对任意长度的区间元素进行动态修改，其中 NNN 为数组中的元素个数
- 给线段树新增 rangeAdd/rangeUpdate 方法，可以在 O(log⁡N)O(\log N)O(logN) 时间复杂度内完成任意长度的区间更新
- 进行区间操作，比如 [0, 10^9]，那么上来就需要 10910^9109 的空间复杂度构建线段树，这是非常浪费的

## 涉及的关键术语
- log, logN, query, nums, update, suffixMin, rangeUpdate, NNN, val, rangeAdd, min, comments, API, labuladong
