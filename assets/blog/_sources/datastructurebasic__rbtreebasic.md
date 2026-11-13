# 红黑树的完美平衡及可视化
url: https://labuladong.online/zh/algo/data-structure-basic/rbtree-basic/
folder: 二叉树结构的种种变换

## 复杂度结论
- 索树，它的树高在任何时候都能保持在 O(log⁡N)O(\log N)O(logN)（完美平衡），这样就能保证增删查改的时间复杂度都是 O(log⁡N)O(\log N)O(logN)
- 而普通二叉搜索树最关键的问题是它不会自动对树进行平衡，特殊的情况下会退化成链表，增删查改的时间复杂度退化为 O(N)O(N)O(N)

## 涉及的关键术语
- log, logN, TreeMap, TreeSet, NlogN, comments, labuladong
