# 面试算法系列 · 写作规范

这份文件是这一系列所有文章的**唯一体例来源**。写任何一篇之前先读它；
写完必须跑通三道门。规范之外的自由度在于内容，不在于格式。

---

## 1. 定位与出处(最重要)

这批文章是**我自己的学习笔记**，不是 labuladong 教程的转载、翻译或复刻。

**必须做到的:**

- 可以引用、讨论、对照 labuladong 的教程，并给出链接
- 每条思路的**表述必须是自己的话**：先讲清"这个套路为什么成立"，
  再给出实现。这也是这个系列和原教程的区别所在
- 原文的可视化面板和动图**不可复制**，我们要自绘 SVG
- 不要成段照搬原文表述；算法结论(复杂度、边界条件)属于事实，可以写

**绝对不可以:**

- 声称读过没读过的材料。**只写你实际验证过的东西**
- 把不确定的说成确定的。取不到原文就明说"这一节是我自己的推导"
- 编造性能数字、编造"实测"

**关于代码语言:** 教程原文是 **Java**。本系列一律 **Python 3 + C++**，
且代码是我们自己写的实现，不是从原文抄的。文章里要有一句话说清楚这一点。

---

## 2. 文件与命名

| 项目 | 约定 |
|---|---|
| 文章 | `_posts/YYYY-MM-DD-<slug>.md` |
| 图片 | `assets/img/<slug>-<YYYYMMDD>/NN-<name>.svg` |
| 图脚本 | `assets/blog/<slug>-<YYYYMMDD>/` 下放生成图的 py 脚本 |
| 验证脚本 | 复用 `assets/blog/_tools/`，不要每篇重写 |

发布日期用**未来日期**，彼此错开，保证归档顺序稳定。

---

## 3. Front matter(顺序固定，不要改)

```yaml
---
layout: post
title: "ASCII 冒号:这里用半角标点"
display_title: "列表页显示的短标题"
subtitle: "副标题用中文全角标点，可以有逗号。"
description: "一句话摘要，给 SEO 和分享卡片用。"
excerpt: "列表页摘要，比 description 略长，讲清这篇解决什么问题。"
date: YYYY-MM-DD 00:00:00 +0800
categories: algorithms
tags: [算法, 数据结构, 链表, 双指针]
---
```

**注意:** `title` 里只能用半角 `:` 和 `,`；`subtitle` / `description` /
`excerpt` 用中文全角标点。混了会破坏 feed 和 og:title。

`tags` 从这几个里挑，别自创太多:
`算法` `数据结构` `链表` `数组` `字符串` `双指针` `滑动窗口` `二分搜索`
`栈` `队列` `单调栈` `单调队列` `哈希表` `二叉树` `BST` `图论` `并查集`
`拓扑排序` `最短路` `回溯` `BFS` `DFS` `动态规划` `背包` `贪心`
`排序` `前缀和` `差分` `设计题` `面试`

---

## 4. 正文结构

```markdown
## 0 先说明材料和我的写法

(一段:这篇讲什么、材料来自哪里、代码是 Python/C++ 不是原文的 Java)

### 目录

- [1 标题](#kramdown-生成的锚点)
- [2 标题](#...)

## 1 主标题:副题

正文…

### 1.1 小节

## 2 …

## N 把这 N 个套路收成一张表

(一张总结表，这是系列特色)

## N+1 材料与出处

(列出引用的教程链接、说明哪些部分是自己的推导)
```

**硬性要求:**

- `## N 标题` 编号从 0 开始，`0` 是说明，最后两节是总结表和出处
- 每个 `##` 标题都要在 `### 目录` 里有一条 `- [文字](#锚点)` 链接。
  锚点 = kramdown 算法:NFKC + 转小写 → 只保留字母数字/空格/`-`/`_`/`.` →
  去掉 `.` → 空白折叠成一个 `-`。**中文数字和汉字都保留**。
  例:`## 1 队列与栈:受限,恰恰是它们存在的理由` → `#1-队列与栈受限恰恰是它们存在的理由`
- 标题里的 `:` 用**半角**(kramdown 会把它删掉，锚点里没有它)

**这个系列的特色(每篇都要有):**

1. **先讲为什么成立**，再给代码。不要只贴模板
2. **标出最容易写错的那一行**，用 `**最容易写错的一行:**` 起头
3. **复杂度要给推导**，不要只丢一个结论
4. 结尾一张**归纳表**，把这几个套路压成可查阅的形式

---

## 5. 代码块

**每一道题都给 Python 3 和 C++ 两版，数量必须相等。**

- 围栏只用 `python`、`cpp`、`text`、`bash`、`json`、`yaml`
- 这个站点**没有语法高亮配色**(只用 kramdown，没有 token CSS)。
  所以代码要靠**排版和注释**自己讲清楚，不要依赖颜色区分
- 注释用中文，讲"为什么"而不是复述代码
- Python 用类型提示可选，但**不要**用 3.10+ 独有语法(站点读者环境未知)
- C++ 用 C++17，头文件写全(`<vector>` `<queue>` `<algorithm>` 等)，
  **不要用 `bits/stdc++.h`**(macOS/clang 没有这个头)
- 代码必须能编译/运行。每篇都要附一个跑得起来的测试 harness

**两版都要写的原因:** 它们错的点不一样。比如 Python 的 `heapq`
在元素相等时会比较元组第二个元素(塞节点会 `TypeError`)，
而 C++ 的 `priority_queue` 比较器只读指定字段，不会碰到这个问题。
文章里要把这种差异写出来。

---

## 6. 自绘图(SVG)

所有示意图自己写脚本生成，放在博客仓库里，**不要手改 SVG**。

```python
import sys; sys.path.insert(0, "<repo>/assets/blog/_tools")
from svgkit import Svg, Check
```

`Svg` 的方法:`rect` `circle` `text` `line` `arrow` `box` `cell` `panel`
`label` `raw` `save`。

**硬性要求:**

- **不要写 `font-family`**，让 SVG 继承页面字体
- **不要产生空的 `<text></text>`**(`svgkit` 已经挡掉了)
- 每放一个文字标签，就在 `Check` 里登记一次，然后 `Check.run()` 检查
  越界和碰撞
- `Check` 只能查文字/文字、文字/箭头、越界。**它查不到"文字压在没登记的
  线上"**，所以生成后必须自己看一眼渲染结果:

```bash
sips -s format png -Z 1400 x.svg --out /tmp/x.png   # 保持真实宽高比
```

**不要用 `qlmanage -t`**，它会补成正方形，看不出真实比例。

**图的生成脚本必须用退出码表态(2026-11-09 补)。** `Check.run()` 返回问题条数，
只打印不处理等于没查——脚本照样 `exit 0`，`for d in ...; do ...; done` 这种
批量重生成看起来全绿，实际上有重叠也不会红。真实反例:`chain-reversal-20261110`
的 `01-iterative-reverse` 就这么带着一个真重叠活到了最后(null 标签框 246..268
压在虚线箭头框 240..295 上)。

```python
# 模块级累计器。用 list 不用 int:函数里对 int 做 += 会被当成局部变量，
# 每处都得补 global，很容易漏。
BAD: list[int] = []

def fig_x():
    ...
    BAD.append(c.run("01-xxx"))      # 收走返回值，别丢

if __name__ == "__main__":
    fig_x()
    total = sum(BAD)
    print(f"  layout problem(s): {total}")
    sys.exit(1 if total else 0)
```

**`sys.exit(1 if BAD else 0)` 是错的**:`[0, 0, 0, 0, 0]` 是真值，列表非空
就 exit 1。必须 `sum(...)`。

改完请用注入一个重叠标签的办法验证它**真的会红**(加两条坐标相同的已登记
标签 → 应当 exit 1)，再还原、确认回收成 exit 0。「看起来像 0」不算验证。

配色跟着站点走:墨色 `#252b33`、蓝 `#3568a3`、灰线 `#e7eaf0`、
纸张 `#fff`、画布 `#f3f5f7`。强调色可以用 `#2f7d6d`(绿)。

---

## 7. 四道门(写完必须全绿)

```bash
REPO=~/projects/linear3735.github.io

# 结构门:front matter、标题、目录锚点、围栏语言、图片是否存在
python3 $REPO/assets/blog/_tools/verify_post.py _posts/<slug>.md

# 代码门:把你文章里的代码抽出来真跑
python3 $REPO/assets/blog/<slug>-<YYYYMMDD>/verify_code.py

# 图门:每张 SVG 能解析、有文字、继承页面字体
python3 $REPO/assets/blog/_tools/verify_svg.py assets/img/<slug>-<YYYYMMDD>/*.svg

# 路线图门:合集页的链接不能指向不存在的文章
python3 $REPO/assets/blog/_roadmap/verify_roadmap.py
```

一次把所有篇都过一遍(含图门与合集页一致性):

```bash
python3 $REPO/assets/blog/_tools/verify_series.py
```

**代码门的写法**:从文章里正则抽出 ```python 和 ```cpp 块，
exec/编译后跑真实用例。不要手抄一份代码去测——那样测的不是文章里的代码。

Python 侧写法参考 `assets/blog/interview-algo-speedrun-20261108/verify_code.py`。
C++ 侧参考同目录 `cpp_solutions_test.cpp`(用
`g++ -std=c++17 -Wall -Wextra -O1`，必须零警告)。

**测试用例要覆盖边界**:空输入、单元素、全相等、长度为偶数/奇数、
目标不存在。不要只跑题面给的例子。

---

## 8. 写完之后

1. 四道门全绿（单篇:`verify_post` + `verify_code` + `verify_svg`；跨篇:`verify_series`）
2. 每一张图都渲染成 PNG 看过一眼
3. `_data/roadmap.json` 由 **Lead 统一 flip**，写手不要动。这条原来是
   「写手自己把 `status` 改成 `done` 并填 `post`」，两处都不对：
   - 键名是 **`post_slug`**，不是 `post`（`roadmap.md` 第 42 行读的是 `post_slug`）
   - `assets/blog/_roadmap/roadmap.json` 是 `_data/roadmap.json` 的逐字节副本，
     两边必须 `cmp` 一致；多人同时改会互相覆盖，所以由一个人改
4. **不要 `git add` / `git commit` / `git push`。** 攒着等用户确认
5. 交付时报告:改了什么、验证结果、**哪些还没验证**

---

## 9. 交付报告的格式

```
## <篇名>

文件:
  _posts/<file>.md            <N> 字
  assets/img/<dir>/           <N> 张 SVG
  assets/blog/<dir>/          <N> 个脚本

验证:
  结构门  exit 0
  代码门  exit 0  (<N> 个 Python 用例 + <N> 个 C++ 用例全过)
  编译    g++ -Wall -Wextra 零警告
  图片    <N>/<N> 张已渲染检查

未验证 / 已知限制:
  - <如实写>
```
