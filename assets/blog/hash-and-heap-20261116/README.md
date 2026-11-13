# 哈希表、堆与树形索引 — 素材与校验

这个目录放这篇文章的校验脚本、C++ harness 和插图生成脚本。

- 文章: [`_posts/2026-11-16-hash-and-heap.md`](../../../_posts/2026-11-16-hash-and-heap.md)
- 图片: `assets/img/hash-and-heap-20261116/`（3 张 SVG，`make_figures.py` 手写生成，非截图）

## 怎么复跑

```bash
cd <repo>

# 结构门:front matter 顺序、代码围栏配对与语言标注、目录锚点可达、图片存在且是真 SVG
python3 assets/blog/_tools/verify_post.py _posts/2026-11-16-hash-and-heap.md

# 插图门:XML 可解析、<svg> 有 viewBox、<text> 非空、不设 font-family、文字不重叠
python3 assets/blog/_tools/verify_svg.py assets/img/hash-and-heap-20261116/*.svg

# 代码门:把文章里的代码块抽出来真跑，Python 3 与 C++17 两版
python3 assets/blog/hash-and-heap-20261116/verify_code.py
```

三个脚本退出码 0 表示全部通过。

重画插图（需要 `sips`，只在 macOS 上用来目视检查，不影响门禁）:

```bash
python3 assets/blog/hash-and-heap-20261116/make_figures.py
```

## verify_code.py 的设计

**它不存任何代码副本，每次运行都从文章正文里重新抽。** 抽法是

```python
re.findall(r"```" + lang + r"\n(.*?)```", post_text, re.S)
```

然后

- 每个 ```` ```python ```` 块 `exec` 进同一个命名空间，再拿文章里定义的类去跑断言；
- 所有 ```` ```cpp ```` 块按顺序拼在 `cpp_structures_test.cpp` 前面，用
  `g++ -std=c++17 -Wall -Wextra -Werror -O1` 编译。**一个 warning 就算失败**，编译产物跑完
  退出码必须是 0，stdout/stderr 里不允许出现任何诊断。
- 最后核对围栏账目:`len(opens) == len(py)+len(cpp)+len(text)+len(bash)`，且
  `sorted(set(opens)) == ["bash", "cpp", "python", "text"]`。文章改了代码却忘了改这里，
  块数就会对不上。

所以文章和门禁不可能各自漂移：**改文章就是改被测代码**。

### 对拍对象（全部与独立参照实现逐次比对，不是自己跟自己比）

| 结构 | 参照实现 | 覆盖的边界 |
| --- | --- | --- |
| 拉链法哈希表 1.3 | Python `dict` | 空表、单元素、重复 key、删两次、全同值、4000 个 key |
| 线性探查 1.4 | Python `dict` | 墓碑链上的 key 仍可达、删一半再插回、空表、单元素 |
| `ArrayHashMap` 2.3 | `dict` + 值域检查 | `random_key` 4 万次不返回不存在的 key、swap-fill 后索引仍对、单元素删除（pos == 最后一个，不触发交换） |
| 一致性哈希 2.4 | 取模法对照 | 空环返回 `None`、加节点迁移比例 < 取模法的一半、摘掉节点后 10000 个 key 全部回到原位 |
| `MinPQ` 3.2 | `bisect.insort` 维护的有序表 | 5000 次随机 push 后逐个 pop 必须升序、单元素、200 个同值、完全升序/降序插入 |
| 原地建堆 / 堆排序 3.4 | `sorted()` / 堆性质检查 | 空、单元素、两个逆序、全同值、全负、已升序、已降序、60 组随机 |
| `TrieMap` 4.2 | `set` + `any(k.startswith(...))` | 5 个原文 API、空串是合法 key、单字符 key、前缀存在但不是 key、5000 次随机探查 |
| 线段树 5.1 | O(n) 暴力（**区间求和 + 区间最值**） | 空数组、单元素、全同值、全负、40 组随机数组上**每一个** (l, r)，再做点更新后重查 |
| 懒标记线段树 5.2 | O(n) 暴力 | 单元素、全同值、300 次交错 `range_add` / `range_sum`、结束后每一个 (l, r) |
| 树状数组 5.3 | O(n) 暴力前缀和 | n = 1..40 每一个 n、每一步之后的所有 `prefix_sum` 与所有 (l, r)、`lowbit` 与 `i & -i` 比到 4096 |
| 跳表 6.1 | `dict` + `bisect` 维护的有序表 | 空表、单元素、200 个同值必须只留 1 个、2 万次随机 insert/contains/erase 逐次对拍、清空后层数回落到 1 |

## 实测数字从哪来

文章里所有「实测」都是这个门跑出来的，不是抄原文的：

```
consistent hash, 10000 keys, 3 nodes x 200 vnodes: 3514 / 3245 / 3241
consistent hash, add a 4th node: 2652 keys move (26.52%)
plain modulo, 3 nodes -> 4 nodes: 7443 keys move (74.43%)
Floyd build, n = 2^20 (python): 1973017 comparisons (1.8816n)
swim build, n = 2^20 (python): 2393905 comparisons (2.2830n)
Fenwick, n = 1024: max prefix_sum hops = 10, max add hops = 11, log2(n) = 10
SkipList, 65536 random inserts: 65337 distinct values stored, level = 16 (...)
ChainingHashMap, n = 2^20 inserts: rehash_ops = 1572876 (1.50001n), capacity = 2097152
```

`measure.py` 是写文章时用来试数的草稿，**不参与门禁**，保留下来只是为了说明这些数字不是手填的。

## 两处代码改动，如实记在这里

1. **2.4 节的 `hash_of` 加了 murmur3 finalizer。** 裸 FNV-1a 对「只差最后一两个字节」的虚拟节点名
   （`node-A#0`、`node-A#1`……）不做雪崩，实测三节点分到 29.8% / 25.2% / 45.0%、环上最大空弧 30.8%。
   补上 finalizer 后是 31.7% / 33.8% / 34.5%、最大空弧 1.3%。1.3 和 1.4 节的 `hash_key` 保持裸 FNV-1a
   不变——那两节只要求同一个 key 稳定映到同一个桶。
2. **6.1 节的 Python 跳表下标统一了。** 原来 `head` 用 `head[lv]`、节点用 `node[lv+1]`，两套下标混用，
   `cur` 从 `head` 走到真实节点后 `cur[lv]` 取到的是节点的「值」而不是 next 指针，第二次插入就会
   `TypeError: 'int' object is not subscriptable`。C++ 版用 `Node{value, vector<Node*> next}`，没这个问题。

两处都是**先被代码门抓出来**才改的，不是改完再补门。

## 材料出处

材料全部来自 labuladong 的算法教程站点，逐篇链接在文章第 0 节。

- **读到完整正文**:《哈希表核心原理》《一致性哈希原理及实现》《跳表核心原理》《Trie 树原理》。
- **问题设定与原理骨架完整、但最终代码被截断**:《用拉链法实现哈希表》《线性探查法的两个难点》
  《线性探查法的两种代码实现》《哈希集合》《用链表加强哈希表》《用数组加强哈希表》《二叉堆核心原理》
  《二叉堆/优先级队列代码实现》《堆排序》《线段树核心原理》《线段树代码实现》《线段树的动态开点》
  《线段树的懒更新》《TreeMap 原理》《Trie 树代码实现》。
- **原文没有**:树状数组 / Fenwick（174 篇全文搜索 `树状数组`、`Binary Indexed`、`lowbit`、`Fenwick`
  四个关键词，零命中）。5.3 节从定义到 `lowbit` 的推导到复杂度分析都是自己写的。

原文用 Java，本文全部代码用 Python 3 和 C++17 重写，原文代码与可视化面板没有复制。
