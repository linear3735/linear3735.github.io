# BFS 算法解题套路框架
url: https://labuladong.online/zh/algo/essential-technique/bfs-framework/
folder: 第零章、核心刷题框架汇总

提到的力扣题号: 752, 773

## 这节的小标题
- 算法框架
- 滑动谜题
- 解开密码锁的最少次数
- 双向 BFS 优化

## 复杂度结论
- 当然从 Big O 表示法分析算法复杂度的话，这两种 BFS 在最坏情况下都可能遍历完所有节点，所以理论时间复杂度都是 O(N)O(N)O(N)，但实际运行中双向 BFS 确实会更快一些
- 不过话说回来，无论传统 BFS 还是双向 BFS，无论做不做优化，从 Big O 衡量标准来看，时间复杂度都是一样的，只能说双向 BFS 是一种进阶技巧，算法运行的速度会相对快一点，掌握不掌握其实都无所谓

## 涉及的关键术语
- BFS, String, target, deadends, visited, add, board, HashSet, DFS, step, GoJavaJavaScriptPython, size, Set, isEmpty, deads, while
