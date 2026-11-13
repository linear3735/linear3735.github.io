# Union Find 并查集原理
url: https://labuladong.online/zh/algo/data-structure-basic/union-find-basic/
folder: 图结构基础及算法概览

## 这节的小标题
- 动态连通性及术语
- 为什么需要并查集算法

## 复杂度结论
- 我们的目标是设计一种数据结构，在尽可能小的时间复杂度下完成连接操作和查询操作
- // 初始化并查集，包含 n 个节点，时间复杂度 O(n)
- // 连接节点 p 和节点 q，时间复杂度 O(1)
- // 查询节点 p 和节点 q 是否连通（是否在同一个连通分量内），时间复杂度 O(1)
- // 查询当前的连通分量数量，时间复杂度 O(1)
- O(1)O(1)O(1) 的时间复杂度是最牛逼的，假设你没学过并查集算法，你应该如何实现上述几个方法呢？
- 构基础及通用代码实现 中已经介绍了图结构邻接表/邻接矩阵的代码实现，这个 union 方法其实就是在图中添加一条无向边，时间复杂度可以做到 O(1)O(1)O(1)
- 这样的话，connected 方法的最坏时间复杂度就是图遍历的复杂度 O(V+E)O(V+E)O(V+E)，其中 VVV 是节点数量，EEE 是边数量

## 涉及的关键术语
- Union, Find, connected, union, count, DFS, BFS, API, boolean, VVV, EEE, comments, labuladong
