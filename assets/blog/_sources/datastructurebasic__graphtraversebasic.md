# 图结构的 DFS/BFS 遍历
url: https://labuladong.online/zh/algo/data-structure-basic/graph-traverse-basic/
folder: 图结构基础及算法概览

## 这节的小标题
- 深度优先搜索（DFS）
- 遍历所有节点（visited 数组）
- 遍历所有边（二维 visited 数组）
- 遍历所有路径（onPath 数组）

## 复杂度结论
- 由于 visited 数组的剪枝作用，这个遍历函数会遍历一次图中的所有节点，并尝试遍历一次所有边，所以算法的时间复杂度是 O(E+V)O(E + V)O(E+V)，其中 E 是边的总数，V 是节点的总数
- 时间复杂度为什么是 `O(E + V)`？我们之前讲解 二叉树的遍历 时说，二叉树的遍历函数时间复杂度是 O(N)O(N)O(N)，其中 NNN 是节点的总数
- 这里图结构既然是树结构的延伸，为什么图的遍历函数时间复杂度是 O(E+V)O(E + V)O(E+V)，要把边的数量 EEE 也算进去呢？为什么不是 O(V)O(V)O(V) 呢？
- 点击查看答案其实二叉树/多叉树的遍历函数，也要算上边的数量，只不过对于树结构来说，边的数量和节点的数量是近似相等的，所以时间复杂度还是 O(N+N)=O(N)O(N + N) = O(N)O(N+N)=O(N)
- 而对于图结构来说，任意两个节点之间都可以连接一条边，边的数量和节点的数量不再有特定的关系，所以我们要说图的遍历函数时间复杂度是 O(E+V)O(E + V)O(E+V)
- 显然，使用二维 visited 数组并不是一个很高效的实现方式，因为需要创建二维 visited 数组，这个算法的时间复杂度是 O(E+V2)O(E + V^2)O(E+V2)，空间复杂度是 O(V2)O(V^2)O(V2)，其中 EEE 是边的数量，VVV 是节点的数量
- 数组，这个算法的时间复杂度是 O(E+V2)O(E + V^2)O(E+V2)，空间复杂度是 O(V2)O(V^2)O(V2)，其中 EEE 是边的数量，VVV 是节点的数量

## 涉及的关键术语
- visited, root, Vertex, DFS, graph, traverse, neighbor, BFS, Node, base, case, System, out, println, visit, neighbors
