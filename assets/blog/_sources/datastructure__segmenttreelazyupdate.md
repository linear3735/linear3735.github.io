# 优化：实现懒更新线段树
url: https://labuladong.online/zh/algo/data-structure/segment-tree-lazy-update/
folder: 经典数据结构设计

## 复杂度结论
- 术，为线段树新增 rangeAdd/rangeUpdate 方法，在 O(log⁡N)O(\log N)O(logN) 时间复杂度内完成任意长度的区间更新
- // 查询闭区间 [qL, qR] 的聚合值，时间复杂度 O(logN)
- // 单点更新，设置 nums[i] = val，时间复杂度 O(logN)
- // 将闭区间 [qL, qR] 增加 delta（可以是负数），时间复杂度 O(logN)
- // 查询闭区间 [qL, qR] 的元素和，时间复杂度 O(logN)
- // 将闭区间 [qL, qR] 赋值为 val，时间复杂度 O(logN)

## 涉及的关键术语
- logN, log, val, rangeAdd, rangeUpdate, query, merge, AllInOneSegmentTree, API, SegmentTree, nums, IncrSegmentTree, start, end, defaultValue, delta
