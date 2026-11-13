# 最短路径与最小生成树 — 素材与校验

这个目录放这篇文章的三个校验脚本：结构门、图片门、代码门。

- 文章: [`_posts/2026-11-24-shortest-path.md`](../../../_posts/2026-11-24-shortest-path.md)
- 图片: `assets/img/shortest-path-20261124/`（7 张 SVG，脚本生成，非截图）
- 源文本归档: `assets/blog/_sources/`（12 个页面，见文末表）

## 怎么复跑

```bash
cd <repo>

# 结构门:front matter 顺序、目录锚点是否都能跳、python/cpp 围栏数量是否相等、
#        引用的图片是否真实存在、Liquid 标签是否配平
python3 assets/blog/_tools/verify_post.py _posts/2026-11-24-shortest-path.md

# 图片门:重新生成 7 张 SVG。生成时带几何校验：文字互相不重叠、不压箭头、
#        不越出画布和面板边界（problems 必须是 0）
python3 assets/blog/shortest-path-20261124/make_figures.py

# 代码门:抽出文章里的 24 个代码块 → Python 真跑 + C++ 真编真跑 → 逐例对拍
#        + 两个语言的 64 位摘要必须相同。成功时打印 CODE OK
python3 assets/blog/shortest-path-20261124/verify_code.py
```

三个脚本退出码 0 表示全部通过。

**为什么两个语言都要真跑。** 这一篇里两种语言踩的坑几乎不重叠，而且下面第一条是门抓出来的、不是我读出来的：

- **朴素 Dijkstra 少了 `done[nxt]` 判定。** 少了这一行，1.2 那个负权反例里朴素版会「侥幸」给出正确答案 `-6`，而正文和 1.2 的图都说它给 `3`（错的）——「出队即最终」这句话就没有反例可讲了。两种语言各写一遍、再逐例对拍，这个不一致才暴露出来。
- **`priority_queue` 默认是最大堆**（`greater<Item>` 不写就静默退化），Python 的 `heapq` 天生最小堆。这个坑只写 Python 永远撞不上，1.4 的「最容易写错的一行」讲的就是它。
- **`u == -1` 这个哨兵**在 Python 里是「负下标取到最后一个元素」的静默错误，在 C++ 里是越界。1.3 的「最容易写错的一行」把两边写成同一行，正是为了对齐这两种失败方式。
- **C++ 还不允许 `bits/stdc++.h`**（clang 没有这个头），所以两边的 include 清单都由 harness 统一给。

## verify_code.py 的设计

**1. 代码只从 `.md` 里抽，不留第二份。** 用 `re.findall(r"^```(python|cpp)[ \t]*\n(.*?)^```", src, re.M | re.S)` 抓围栏，然后断言：python 12 块、cpp 12 块、**每个 `##` 小节内部两种语言数量相等**、文章里不出现 `bits/stdc++.h`、C++ 块里不出现 `main`（harness 自己要提供 `main`）。

**2. 完整实现与「一行示例」分开对待。** 11 个 python / 11 个 cpp 是完整实现，直接 `exec` / 编进 harness；剩下各 1 块是「最容易写错的一行」那种片段（python 的 `if u == -1 or dist[u] == INF:`、cpp 的 `priority_queue<Item, vector<Item>, greater<Item>> pq;`），单独跑会 `SyntaxError` / 缺 `Item` 定义。门对它们做的是**语法检查**（python 包进 `while True:` + `pass` 编一遍；cpp 用一次独立的 `g++ -fsyntax-only` 判定它不属于完整实现），并在输出里明确列出来，不假装它们跑了。

**3. 两个语言共用同一个 PRNG。** 不用「生成一堆字面量再写进两个语言」的老办法，而是一个 64 位 LCG：

```text
s = (s * 6364136223846793005 + 1442695040888963407) mod 2^64
next() = s >> 33
SEED = 20261124
```

Python 和 C++ 各有一个逐位等价的 `Rng`，所以两边看到的是**同一批图**。LCG 的前 8 个输出在随机家族开始前就先喂进摘要：如果两边的生成器有任何一位不一样，摘要第一步就崩了，不会等到后面才发现。

**4. 结果用 64 位摘要对齐。** 每个用例的结果（`dist` 向量、`moves`、欧拉路径、扩展格子数、判定真假……）都用 FNV-1a（`h ^= v; h *= 1099511628211`）折进摘要，两边**同一顺序、同一批值**，最后要求逐位相同。这一版是 `2455964581587443995`，两边一致；失败的家族、用例号、实参都会打印出来。

**5. 七个随机家族（全部与 C++ 侧逐例对拍）：**

| 家族 | 用例 | 对拍内容 | 本次结果 |
| --- | --- | --- | --- |
| A | 60 张非负权有向图 | 堆版 / 朴素版 / Floyd / Bellman-Ford 四方互拍；`dst` 提前退出不改变答案 | 不一致 0 |
| B | 40 张带负权边的 DAG | Bellman-Ford vs Floyd | 不一致 0 |
| C | 30 张带负环的图 | Bellman-Ford 与 Floyd 都必须报出来 | 漏报 0 |
| D | 40 张连通图 | Prim vs Kruskal vs 暴力枚举所有边子集 | 不一致 0 |
| E | 40 张随机网格 | `h ≡ 0` 必须与 Dijkstra 逐格相同；曼哈顿不改变答案 | 不一致 0；扩展格子合计 704 → 642（−8.8%） |
| F | 6,000 张图 × 有向/无向 | 先决条件判定对拍暴力；产出的路径逐步合法性；字典序 vs 暴力枚举全部欧拉路径 | 判定 12,000 例、合法 8,910 例、字典序 8,910 例，全部 0 不一致 |
| G | 2,000 张无负环图 × 每个起点 | SPFA 不许误报（真值用 Bellman-Ford 第 `V` 轮单独算） | 9,062 个组合误报 0 次 |

另外还有一批**手写用例**，就是正文里印出来的那些数字：1.2 的四个数（朴素 3 / `dst` 版 3 / 完整堆版 −6 / Bellman-Ford −6）、不可达与空图/单点/无边/自环/重边的边界、3.3 的 `dist[1][0] = 9` 与错误循环顺序给 `∞`、4.1 的「最短路那条边不在 MST 里」（8 vs 5）、5.4 的 `8 / 8 / 10` 与扩展 `23 → 11`、6.5 的力扣 332 两个官方样例。

**6. C++ 侧怎么编。** 文章的 cpp 块没有 `#include`、没有 `main`，harness 补上 include 清单和 `main`，然后：

```bash
g++ -std=c++17 -Wall -Wextra -Werror -O1 assets/blog/shortest-path-20261124/_generated_shortest_path_test.cpp
```

`-Werror` + 要求 stderr 为空 ⇒ **零警告**（本次 1.2 s 编完）。生成的文件 `_generated_shortest_path_test.cpp` 留在目录里，方便直接看「文章代码 + harness」拼出来的完整程序。

## 门抓出来的三个「文档与实现不一致」

三个都是先被门报出来、再改的文章，记在这里因为它们正好是三类典型：

1. **实现和正文说的不一样。** §1.3 朴素版漏了 `done[nxt]` 判定 ⇒ §1.2 的四组数字里「朴素版给 3（错的）」实际是 `-6`。补上判定后四个数才自洽，两种语言也一致了。
2. **docstring 和实现说的不一样。** §4.3 的 `prim` 写着「不连通时给的是最小生成森林的权重」，实现却在长不动时直接 `break`，只算了起点那一棵。改成「长不动就换个还没进树的点重新开始」（`trees` 计数顺便就是连通性判定），和 Kruskal、暴力枚举三方对齐。
3. **图和数据说的不一样。** 图 06 的两堵墙画在了**转置**的位置。5×5 里放两堵墙的 253 种布局（`C(23,2)`）中，只有 `grid[3][1] + grid[4][3]` 这一种能让「`h = 3 × 曼哈顿`」给出 10 步（真实 8 步）；墙一转置，可采纳和不采纳两种启发函数都是 8 步，反例就不成立了。正文的 ASCII 图本来是对的，图和门都按它改。

## 图片

7 张都是按本站主题色手写的 SVG（不是截图，也不是原教程的可视化面板）：

| 文件 | 内容 |
|---|---|
| `01-algorithm-choice.svg` | 六套算法的选型总图：输入条件 → 该选哪个 |
| `02-dijkstra-order.svg` | 堆版 Dijkstra 的出队顺序与 `dist` 逐轮变化 |
| `03-negative-edge.svg` | 负权边反例：四种实现给出两个答案 |
| `04-floyd-k-layer.svg` | Floyd 的「允许经过前 k 个点」逐层扩大 |
| `05-prim-vs-kruskal.svg` | 同一张图上 Prim 与 Kruskal 的选中/放弃边 |
| `06-astar-grid.svg` | A\* 的三个实测与那张 5 × 5 反例网格 |
| `07-hierholzer.svg` | Hierholzer：走、卡住、逆后序插入 |

**编号不等于正文出现顺序。** 图按内容编号（选型图是 01），插入位置按叙事走，所以正文里的顺序是 01 → 03 → 02 → 04 → 05 → 06 → 07。1.2 里那句「第 2 张图」是按**出现顺序**说的（即 `03-negative-edge.svg`）。

SVG 里**没有硬编码 `font-family`**，文字继承页面正文字体；颜色对齐 `assets/css/site.css` 的 `--ink` / `--muted` / `--blue` / `--line` / `--paper` / `--canvas` / 强调绿。本站没有深色模式，图不需要做主题切换。生成器和几何校验器在**仓库内**：`make_figures.py`（用 `assets/blog/_tools/svgkit.py`），上面 7 张都是 `TOTAL layout problems: 0` 生成的。

肉眼核对用的命令（`sips` 转 PNG，不要用 `qlmanage -t`）：

```bash
sips -s format png -Z 1400 assets/img/shortest-path-20261124/06-astar-grid.svg --out /tmp/06.png
```

## 归档的源文本

正文第 8 节列的 12 个 labuladong 页面，抽取到的正文都归档在 `assets/blog/_sources/`，文件名是把 URL 路径里的 `-` 去掉后的形式：

| 归档文件 | 对应页面 |
|---|---|
| `datastructurebasic__graphshortestpath.md` | 图的最短路径算法（三类划分、负权边反例、负权环定性） |
| `datastructure__dijkstra.md` | Dijkstra 算法（只抽到一句话总结 + 两处差别 + 目录，**代码与证明没抽到**） |
| `datastructure__dijkstrafollowup.md` | Dijkstra 算法的拓展（`distTo` 升维、`State` 加字段） |
| `datastructure__floyd.md` | Floyd 算法（`dp[i][j]` 定义与 base case） |
| `datastructure__astar.md` | A\* 算法（用途、启发函数经验法则） |
| `datastructure__prim.md` | Prim 算法（一句话总结；切分定理/正确性/复杂度只有目录） |
| `datastructure__kruskal.md` | Kruskal 算法（一句话总结、习题清单） |
| `datastructurebasic__graphminimumspanningtree.md` | 最小生成树（定义与三个特性、修路场景） |
| `datastructurebasic__euleriangraph.md` | 欧拉图与一笔画（三条判定、七桥问题） |
| `datastructure__euleriangraphhierholzer.md` | Hierholzer 算法（判定口径、逆后序、`O(E + V)`） |
| `problemset__dijkstra.md` | 最短路习题（743、1631、1514、787） |
| `problemset__eulerianpath.md` | 欧拉路径习题（332、2097） |

**没有** Bellman-Ford / SPFA 的独立页面可归档——素材里只有 `graphshortestpath` 那一篇的一句定性，第 2 节整节（`D_k` 不变量、`V - 1` 轮证明、第 `V` 轮查负环、SPFA 判据与那 9,062 组的实测）都是本篇自己的推导和实验，文章里也照此声明了。
