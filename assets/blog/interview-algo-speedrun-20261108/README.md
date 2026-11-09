# 面试算法题速刷 — 素材与校验

这个目录放这篇文章的校验脚本和它引用的源文本。

- 文章: [`_posts/2026-11-08-interview-algo-speedrun.md`](../../../_posts/2026-11-08-interview-algo-speedrun.md)
- 图片: `assets/img/interview-algo-speedrun-20261108/`（8 张 SVG，手写，非截图）

## 怎么复跑

```bash
cd <repo>

# 结构门:front matter 顺序、表格列数、代码围栏、目录锚点、链接与图片是否存在
python3 assets/blog/interview-algo-speedrun-20261108/verify_markdown.py \
        _posts/2026-11-08-interview-algo-speedrun.md --repo .

# 事实门:文章里每一条来自教程的说法，逐条核对到归档源文本的具体行
python3 assets/blog/interview-algo-speedrun-20261108/verify_citations.py \
        _posts/2026-11-08-interview-algo-speedrun.md
```

两个脚本退出码 0 表示全部通过。

## verify_citations.py 的设计

每条断言写成 `(标签, 文件, 行号, 必须出现的子串)`。**要求子串出现在指定的那一行**，而不只是"文件里某处出现过"。这样同时能抓住两类错误:

- 说法本身是错的;
- 说法是对的，但归错了位置（例如把作者的推导归给原文）。

目前 **42/42 条源断言通过**，另有 3 条 `OWN_CLAIMS` 反向断言，用来确保文章里始终保留三处必要的自我声明（第一节无原文、x/y/z 记法是我自己的、8 张图是我自己画的）。如果这些声明被删掉，门会失败。

## 归档的源文本

`t2-linked-list-skills-summary.txt` 是《双指针技巧秒杀七道链表题目》的正文文本（23 KB），作为引用核对的依据归档在此，便于读者复跑上面的校验。

**没有归档**《队列/栈基本原理》的页面内容。那个页面是客户端渲染的，取下来的 127 KB 是 Next.js 的 RSC 数据载荷（侧边栏目录 + 元信息），并不包含正文；而且把一个第三方站点的整页载荷放进公开仓库属于不必要的再分发，所以没有提交。文章第 1 节因此明确声明为"从标题和摘要出发的第一性原理推导，未逐字对照原文"。

## 图片

8 张图都是按本站主题色手写的 SVG（不是截图，也不是原教程的可视化面板）：

| 文件 | 内容 |
|---|---|
| `01-queue-vs-stack.svg` | 队列 FIFO 与栈 LIFO 的取出顺序对比 |
| `02-two-implementations.svg` | 队列的两种底层实现：环形缓冲 vs 链表 |
| `03-deque.svg` | 双端队列的四类操作 |
| `04-where-they-appear.svg` | 栈/队列/优先队列在算法题中的出现位置 |
| `05-dummy-node.svg` | 虚拟头结点在合并两个有序链表中的作用 |
| `06-kth-from-end.svg` | 倒数第 k 个节点：p1 先走 k 步 |
| `07-cycle-start.svg` | 找环起点：x / y / z 三个距离 |
| `08-intersection.svg` | 相交链表：两条路各走一遍对方的路 |

SVG 里**没有硬编码 `font-family`**，以便文字继承页面正文字体；颜色对齐 `assets/css/site.css` 中的 `--ink` / `--muted` / `--blue` / `--line` / `--paper` / `--canvas`。本站没有深色模式，所以图不需要做主题切换。

生成脚本不在本仓库，位于工作目录
`reports/interview-algo-speedrun-20261108/img/`（`svgkit.py` + `d01.py` / `d02.py` / `d03_04.py` / `d05_08.py`）。`svgkit.py` 带一个几何布局校验器，会在生成时断言文字互相不重叠、不压到箭头、不越出画布和面板边界——上面 8 张图都是 0 problem 生成的。
