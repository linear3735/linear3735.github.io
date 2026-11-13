# 二叉树系列算法核心纲领
url: https://labuladong.online/zh/algo/essential-technique/binary-tree-summary-2/
folder: 手把手刷二叉树算法

提到的力扣题号: 104, 144, 543

## 这节的小标题
- 二叉树的重要性
- 深入理解前中后序
- 两种解题思路
- 后序位置的特殊之处
- 以树的视角看动归/回溯/DFS算法的区别和联系
- 例子一：分解问题的思想体现
- 例子二：回溯算法的思想体现
- 例子三：DFS 的思想体现
- 层序遍历
- 回答评论区的问题

## 复杂度结论
- va 的话无论 ArrayList 还是 LinkedList，addAll 方法的复杂度都是 O(N)，所以总体的最坏时间复杂度会达到 O(N^2)，除非你自己实现一个复杂度为 O(1) 的 addAll 方法，底层用链表的话是可以做到的，因为多条链表只要简单的指针操作就能连接起来
- erse 遍历每个节点的时候还会调用递归函数 maxDepth，而 maxDepth 是要遍历子树的所有节点的，所以最坏时间复杂度是 O(N^2)
- 这下时间复杂度只有 maxDepth 函数的 O(N) 了

## 涉及的关键术语
- root, traverse, res, nums, TreeNode, DFS, left, right, maxDepth, GoJavaJavaScriptPython, List, depth, val, add, child, grid
