# 图论基础与连通性 — 素材与校验

这个目录放这篇文章的三个校验脚本：结构门、图片门、代码门。

- 文章: [`_posts/2026-11-23-graph-traversal.md`](../../../_posts/2026-11-23-graph-traversal.md)
- 图片: `assets/img/graph-traversal-20261123/`（9 张 SVG，脚本生成，非截图）
- 源文本归档: `assets/blog/_sources/`（9 个页面，见文末表）

## 怎么复跑

```bash
cd <repo>

# 结构门:front matter 顺序、目录锚点是否都能跳、python/cpp 围栏数量是否相等、
#        引用的图片是否真实存在、Liquid 标签是否配平
python3 assets/blog/_tools/verify_post.py _posts/2026-11-23-graph-traversal.md

# 图片门:重新生成 9 张 SVG。生成时带几何校验：文字互相不重叠、不压箭头、
#        不越出画布和面板边界（problems 必须是 0）
python3 assets/blog/graph-traversal-20261123/make_figures.py

# 代码门:抽出文章里的 24 个代码块 → Python 真跑 + C++ 真编真跑 → 摘要必须相同
python3 assets/blog/graph-traversal-20261123/verify_code.py
```

三个脚本退出码 0 表示全部通过。

**为什么两个语言都要真跑。** 这一篇里至少有三处只写一种语言就发现不了：

- **递归深度是语言相关的现实问题。** 正文 2.2 举的是「一万个节点排成一条线」：Python 默认递归上限 1000，直接 `RecursionError`；C++ 则是爆栈——所以正文单独给了一份迭代版。**门里的随机用例 `V ≤ 8`，触发不到这个风险，这是门的已知限制**（正文举的那个例子太大，不适合塞进每次都要跑的门里）。
- **C++ 用不了 `bits/stdc++.h`。** clang 没有这个头（本机 `g++` 就是 Apple clang），所以文章的 cpp 块不带 include，由 harness 统一补一份最小 include 清单——这同时也保证了「文章里的代码块能独立看懂，不需要猜头文件」。
- **「同一个算法的两种写法」不该拿逐元素顺序去比。** 迭代 DFS 与递归 DFS 给出的是两个不同的合法 DFS 序（正文 2.2 末尾专门声明过这一点），所以门对迭代版断言的是「访问到的节点集合相同」而不是「顺序相同」；拓扑排序同理，断言的是「是个排列 + 每条边都满足先后」，不是某个特定序列。

## verify_code.py 的设计

**1. 代码只从 `.md` 里抽，不留第二份。** 12 个 python 块 + 12 个 cpp 块，并且断言两者数量相等、且在文中是交替出现的（每讲完一个套路就跟着另一语言的同一份实现）。

**2. Python 侧一次性全部 exec 进同一个命名空间。** 块与块之间互相引用（后一块用前一块定义的类/函数），所以只能一起 live；`exec` 前先对每块单独 `compile()`，语法错会指名到块号。本次命名空间里有 16 个名字。

**3. 手写用例就是正文印出来的那些数字。** 空图 / 单点 / 自环 / 不连通 / 有环 / 无环 / 二分图 / 冗余连接 / 等式方程，外加图 02 里 DFS 进入-离开序与 BFS 层序的逐点顺序。

**4. 随机部分一律跟「独立的外部参照」比，不跟自己的另一个实现比：**

| 被测 | 参照物 |
| --- | --- |
| 并查集 `connected` | 每次重新 BFS 求连通性 |
| DFS 三色判环 | 传递闭包（Floyd 式可达性矩阵） |
| 二分图染色 | 枚举全部 `2^V` 种染法看是否有一种成立 |
| 684 冗余连接 | 逐条加边 + BFS 判两端本来是否已连通 |
| 990 等式方程 | 枚举所有变量赋值，检查是否存在满足全部等式的解 |

**5. C++ 侧跑的是同一批用例，不是「同一段生成逻辑」。** 随机用例由 Python 生成后**作为字面量写进** `_generated_graph_traversal_test.cpp`（本次 2,106 行，含 40 张随机图 + 25 个冗余连接 + 30 组等式方程），再和文章的 12 个 cpp 块 + harness 拼成完整程序：

```bash
g++ -std=c++17 -Wall -Wextra -Werror -O1 -o /tmp/graph_traversal_test \
    assets/blog/graph-traversal-20261123/_generated_graph_traversal_test.cpp
```

`-Werror` + 要求 stderr 为空 ⇒ **零警告**。这样「用例生成」这一环不可能两边不一致，剩下能不一致的只有实现本身，而实现不一致会被 64 位摘要抓住：Python 侧把每个用例的结果折进一个 64 位摘要，C++ 侧用同一顺序折一遍，两边必须逐位相同。本次是 `14532508442979461639`，两边一致（415 项 Python 断言 0 失败）。

生成的 `.cpp` 留在本目录里方便阅读；**编出来的二进制放系统临时目录**，因为 `assets/` 会被 Jekyll 原样发布，不该塞进构建产物。

## 图片

9 张都是按本站主题色手写的 SVG（不是截图，也不是原教程的可视化面板），编号与正文出现顺序一致：

| 文件 | 内容 |
|---|---|
| `01-adjacency-list-vs-matrix.svg` | 同一个图的邻接表与邻接矩阵表示，及两种存法的查询代价 |
| `02-dfs-vs-bfs-order.svg` | 同一个图上 DFS 的进入/离开顺序与 BFS 的层序对比 |
| `03-three-marks.svg` | `visited` / `onPath` / 二维 `visited` 三种标记各自解决的问题 |
| `04-cycle-three-colors.svg` | 三色标记判环：白色未访问、灰色在当前路径上、黑色已完成 |
| `05-topo-dfs-vs-kahn.svg` | 拓扑排序 DFS 版（后序反转）与 Kahn 版（入度归零出队） |
| `06-kahn-steps.svg` | Kahn 逐轮把入度归零的节点出队，数出队个数即可判环 |
| `07-bipartite-coloring.svg` | 二分图染色法：相邻点异色，遇到同色邻居即出现奇环 |
| `08-unionfind-optimizations.svg` | 并查集朴素挂法退化成链 vs 路径压缩 + 按大小合并 |
| `09-redundant-connection.svg` | 冗余连接：加边前两端已连通的那条边就是多余的 |

SVG 里**没有硬编码 `font-family`**，文字继承页面正文字体；颜色对齐 `assets/css/site.css` 的 `--ink` / `--muted` / `--blue` / `--line` / `--paper` / `--canvas` / 强调绿。本站没有深色模式，图不需要做主题切换。生成器在**仓库内**：`make_figures.py`（用 `assets/blog/_tools/svgkit.py`），上面 9 张都是 `TOTAL layout problems: 0` 生成的。

肉眼核对用的命令（`sips` 转 PNG，不要用 `qlmanage -t`）：

```bash
sips -s format png -Z 1400 assets/img/graph-traversal-20261123/04-cycle-three-colors.svg --out /tmp/04.png
```

## 归档的源文本

正文第 8 节列的 9 个 labuladong 页面，抽取到的正文都归档在 `assets/blog/_sources/`，文件名是把 URL 路径里的 `-` 去掉后的形式：

| 归档文件 | 对应页面 |
|---|---|
| `datastructurebasic__graphterminology.md` | 图论中的基本术语（简单图、E ≤ V(V−1)/2、稠密/稀疏） |
| `datastructurebasic__graphbasic.md` | 图结构的通用代码实现（**只抽到标题、一句话总结和目录，正文代码没抽到**） |
| `datastructurebasic__graphtraversebasic.md` | 图结构的 DFS/BFS 遍历（四种场景划分、前序标记/后序撤销、二维 `visited` 的代价） |
| `datastructure__cycledetection.md` | 环检测算法（只记 `onPath` 为何超时、`visited` 剪掉了什么） |
| `datastructure__topologicalsort.md` | 拓扑排序算法（逆后序、建图方向与要不要反转） |
| `datastructure__bipartitegraph.md` | 二分图判定算法（双色问题、`visited` 判断的位置） |
| `datastructurebasic__unionfindbasic.md` | Union Find 并查集原理（动态连通性、平衡性优化与路径压缩） |
| `datastructure__unionfind.md` | Union-Find 并查集算法（10 节点逐步连线、分节结构） |
| `problemset__unionfind.md` | 并查集经典习题（323、130、990、547、1361、947） |

**来源边界（文章里也照此声明了）**：这些抽取文本是**截断**的——每页末尾能看到完整目录，正文只有一部分（例如图遍历那页目录里的「同时使用 `visited` 和 `onPath`」「BFS 写法一/二/三」都没抽到）。所以文章与原文冲突时以原文为准。另外《图结构的通用代码实现》一篇只拿到标题和目录，§1.2 的三个存储约定是文章自己定的，不是原文的转述。
