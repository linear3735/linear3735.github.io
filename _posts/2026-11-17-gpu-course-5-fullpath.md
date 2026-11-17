---
layout: post
title: "第 5 站: Hopper 与真实 LLM 系统"
display_title: "从算子回到模型"
subtitle: "Colfax 的 Hopper 系列按 TMA → WGMMA → 流水线 → Persistent 读；再用 CS336 把单算子放回整条执行路径"
description: "CUTLASS/CuTe 的作者讲座是「本人讲自己写的东西」最集中的部分。名字对着 CUTLASS 贡献者名单核过；一篇 2026 年的 CuTe 论文我一开始怀疑编号是编的，联网核了才写。"
excerpt: "单算子优化到极限，模型仍然可能慢 —— 因为瓶颈可能根本不在算子里。"
date: 2026-11-17 00:04:00 +0800
categories: gpu
tags: [GPU, CUTLASS, CuTe, FlashAttention, Hopper, 课程]
---

## 0 先说明材料和我的写法

这一篇是课程序列的第 5 站。入口我都抓过。其中三条我核得比较深：讲者身份对着 CUTLASS 的 `CONTRIBUTORS.md` 核，一篇 arXiv 论文核到了标题与作者，GPU MODE 的讲次目录核到了讲义目录是否真实存在。

**这一站和我已经写过的 Colfax 拆解那篇直接接上** —— 那篇是代码级拆解，这一站讲的是这条链上的材料该怎么排。

### 目录

- [0 先说明材料和我的写法](#0-先说明材料和我的写法)
- [1 这一站要解决的问题](#1-这一站要解决的问题)
- [2 Colfax 的 Hopper 系列：按依赖顺序读](#2-colfax-的-hopper-系列按依赖顺序读)
- [3 跟着写代码的人学 CUTLASS 与 CuTe](#3-跟着写代码的人学-cutlass-与-cute)
- [4 我怀疑过一个 arXiv 编号，去核了](#4-我怀疑过一个-arxiv-编号去核了)
- [5 CS336：把单算子放回模型执行](#5-cs336把单算子放回模型执行)
- [6 我核到的、和我没核的](#6-我核到的和我没核的)
- [7 材料与出处](#7-材料与出处)

## 1 这一站要解决的问题

前 4 站都在单算子或单 kernel 的尺度上。这一站解决两个问题：

1. **Hopper 这一代的算子怎么设计？** TMA、WGMMA、warp specialization、persistent kernel 这几个东西是配套出现的，顺序错了会读不懂。
2. **单算子优化完了，为什么模型还是慢？** 因为瓶颈可能根本不在算子里 —— 在并行策略、在通信、在内存核算。

第 2 个问题决定了这一站的落点：**从算子回到模型**。

## 2 Colfax 的 Hopper 系列：按依赖顺序读

四篇之间是有依赖的，按这个顺序读：

| 顺序 | 主题 | 为什么在这个位置 |
|---|---|---|
| 1 | TMA（Tensor Memory Accelerator） | 先懂数据怎么搬。后面所有设计都建立在「搬运是异步的」这个前提上 |
| 2 | WGMMA（warpgroup MMA） | 再懂计算怎么发。异步指令 + 屏障，和第 1 篇的异步搬运配对 |
| 3 | 流水线与 warp specialization | 然后才是怎么把搬运和计算叠起来，以及谁来发指令 |
| 4 | Persistent kernel 与 Stream-K | 最后是工作怎么在 SM 之间分配，以及尾部不均衡怎么处理 |

这个顺序的道理：第 3 篇讲的流水线是「异步搬运」和「异步计算」的组合，前两篇没懂，第 3 篇就只是模板参数。第 4 篇讲的是调度层，它假设你已经知道一个工作单元长什么样。

那篇 Colfax 拆解里我做过一件事：把讲座里的算术独立重算了一遍。幻灯片说某个 block 的 EX2 要占掉张量核一半的时间，我把 `2 × 2 × 128 × 192 × 128 = 12,582,912` FLOP 除以 4096 FLOPS/cycle 得 3072 cycle，另一条路 `128 × 192 = 24,576` OPS 除以 16 OPS/cycle 得 1536 cycle，比值正好 0.50。**这类算术是读 Hopper 材料时必须自己过一遍的**，因为它是后面所有设计选择的理由。

## 3 跟着写代码的人学 CUTLASS 与 CuTe

这是「本人讲自己写的东西」最集中的部分。我核了讲者身份 —— 名字对着 CUTLASS 的 `CONTRIBUTORS.md` 核：

| 讲者 | 内容 | 核到的身份 |
|---|---|---|
| Cris Cecka | CuTe 布局与代数（GPU MODE 第 57 讲）、PyCuTe（第 114 讲） | 在 CUTLASS 贡献者名单里 |
| Vijay Thakkar、Pradeep Ramani | Tensor Cores（GPU MODE 第 23 讲） | 两人都在贡献者名单里 |
| Jay Shah | CUTLASS 与 FlashAttention-3（GPU MODE 第 36 讲） | 在 CUTLASS 致谢名单里 |

选这一组而不是按频道时间刷全部，理由是这些讲的题目和讲者的实际工作**直接对应**：Cecka 讲 CuTe 是因为 CuTe 是他参与的，Thakkar 讲 Tensor Core 是因为他做 CUTLASS 3。

CUTLASS 的主流用法这两年多了一条 Python 路径：CuTe DSL。如果你更习惯 Python，它是下到 layout 层的一条捷径；官方教程入口在 7.3 节。**PyCuTe** 则提供布局可视化，配 Cecka 那篇论文一起看效果好 —— 布局代数光看公式很难建立直觉。

## 4 我怀疑过一个 arXiv 编号，去核了

序列里有一条 2026 年的论文：CuTe 的布局表示与代数。我第一眼看到 `arXiv:2603.02298` 时**怀疑这个编号是编的** —— 它长得像模板套出来的。

联网核完的结果：**论文是真的**。

| 字段 | 抓到的值 |
|---|---|
| 编号 | `arXiv:2603.02298` |
| 标题 | CuTe Layout Representation and Algebra |
| 作者 | Cecka, Cris |
| 日期 | 2026/03/02 |

之所以要单独写一节：**这条恰好说明了「核对」和「转述」的差别。** 如果我按怀疑直接删掉，就漏掉了一条真材料；如果我按转述直接写上，就没法确定它真实存在。核一遍的成本很低，值得。

（顺带说明编号的读法：`2603` 是 2026 年 3 月。在这个时间点它已经存在。）

## 5 CS336：把单算子放回模型执行

CS336 是 Stanford 的「从零构建语言模型」课，主讲 Percy Liang 和 Tatsunori Hashimoto。它对这一站的价值不是教算子，而是**把算子放回模型的执行路径里**：资源核算、GPU/TPU、kernels/Triton、并行策略、推理。

这一站放在最后，是因为它回答的是第 1 节里的第二个问题：单算子优化到极限，模型仍然可能慢。原因可能是并行策略不对、通信占比过高、或者显存核算算错了。**这些都不在任何单个 kernel 的内部。**

一个具体的落点：CS336 有一次作业专门做系统部分。要练「把机制落到真实代码」这件事，它比看视频更直接。

## 6 我核到的、和我没核的

**核到了什么。**

- Colfax 四篇教程入口、CUTLASS/CuTe 相关入口、CS336 官网与录像、GPU MODE 课程目录与频道，全部返回 200。
- **讲者身份**：`CONTRIBUTORS.md` 里 `Cris Cecka`、`Vijay Thakkar`、`Pradeep Ramani` 三人均出现，`Jay Shah` 在致谢段出现。
- **GPU MODE 讲次**：README 里 `Lecture 23: Tensor Cores`、`Lecture 36: CUTLASS and Flash ATtention 3`、`Lecture 57: CuTE`、`Lecture 114: PyCuTe` 四条标题与讲者逐字核对；并用 GitHub API 确认 `lecture_036`、`lecture_057`、`lecture_114` 等讲义目录**真实存在**。
- **arXiv 论文**：标题、作者、日期三项如上表。

**没核到什么。** 五条边界：

1. **`lecture_023` 的讲义目录不在仓库里。** 第 23 讲的 Slides 链接指向一份 Google Drive 文档，不是 `lecture_023/` 目录。我核到的是「讲次标题与讲者正确」，**没有点开那份 Drive 文档**。
2. **我没有看视频，也没有跑 CuTe DSL 教程。** CuTe DSL 与 PyCuTe 的接口细节、是否适用于你手上的 CUTLASS 版本，我没有验证。
3. **Hopper 材料的算术我只重算过拆解那篇里出现的部分。** 四篇教程里其他的公式我没有逐条重算。
4. **CS336 我核的是官网与课程入口，没有核对每一次作业的当前内容。** 作业要求逐学期会变。
5. **我没核 CUTLASS 的版本兼容性。** CUTLASS 发版频繁，某一篇教程对应的版本可能与今天不同。

## 7 材料与出处

### 7.1 Hopper 算子设计（按顺序读）

- TMA — <https://research.colfax-intl.com/tutorial-hopper-tma/>
- WGMMA — <https://research.colfax-intl.com/cutlass-tutorial-wgmma-hopper/>
- 流水线与 warp specialization — <https://research.colfax-intl.com/cutlass-tutorial-design-of-a-gemm-kernel/>
- Persistent kernel 与 Stream-K — <https://research.colfax-intl.com/cutlass-tutorial-persistent-kernels-and-stream-k/>

### 7.2 作者讲座与最新材料

- GPU MODE 课程与材料目录 — <https://github.com/gpu-mode/lectures>
- GPU MODE 频道 — <https://www.youtube.com/@GPUMODE>
- Cris Cecka：CuTe（第 57 讲）— <https://www.youtube.com/watch?v=vzUhbDO_0qk>
- Cris Cecka：PyCuTe（第 114 讲）— <https://www.youtube.com/watch?v=_LmOPM5HnZ0>
- CuTe 布局代数论文（Cecka，2026-03-02）— <https://arxiv.org/abs/2603.02298>
- PyCuTe 代码与布局可视化 — <https://github.com/NVlabs/CuTe>
- CuTe DSL 官方教程 — <https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/dsl_introduction.html>
- CUTLASS 贡献者名单（用于核对讲者身份）— <https://github.com/NVIDIA/cutlass/blob/main/CONTRIBUTORS.md>

### 7.3 模型全路径

- CS336 官网与讲义 — <https://cs336.stanford.edu/>
- CS336 官方录像（2026）— <https://www.youtube.com/playlist?list=PLoROMvodv4rMqXOcazWaTUHhq-yembLCV>
- 系统方向作业 — <https://github.com/stanford-cs336/assignment2-systems/tree/main>

### 7.4 已经写过的代码级拆解

- [把 FlashAttention-3 的算法读成 CUTLASS 代码](/fa3-cutlass-mainloop/)

### 7.5 核验口径

核验日期 2026-11-17。方法：`curl -sIL` 取状态码；讲者身份从 `raw.githubusercontent.com` 抓 `CONTRIBUTORS.md` 检索姓名；GPU MODE 讲次从 README 正则提取并用 GitHub API 校验讲义目录；arXiv 从页面解析 `citation_title` / `citation_author` / `citation_date`。
