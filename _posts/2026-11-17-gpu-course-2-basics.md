---
layout: post
title: "第 2 站: 把 CUDA 基础连成体系, 再补并行系统的视角"
display_title: "基础与系统视角"
subtitle: "PMPP 作者的连续课程打底，CS149 补机制；顺便纠正一处流传较广的讲次编号"
description: "数据并行、线程索引、内存分块怎么连成体系，SIMD/SIMT、局部性、带宽、同步怎样共同决定性能。附一份按 Fall 2025 官方课表核对过的讲次对照。"
excerpt: "网上流传的「CS149 第 2 讲 SIMD、第 6 讲 Roofline」对不上 Fall 2025 的实际课表。我把官方课表抓下来逐条排了一遍。"
date: 2026-11-17 00:01:00 +0800
categories: gpu
tags: [GPU, CUDA, 并行计算, 性能优化, 课程]
---

## 0 先说明材料和我的写法

这一篇是课程序列的第 2 站。入口我都抓过，核对到「链接可达 + 标题与讲者一致」；我没有逐段播放课程。

这一站我**纠正了一处讲次编号**，在第 4 节。那处错误流传较广，值得单独写清楚，因为按错编号去找讲义会白找。

### 目录

- [0 先说明材料和我的写法](#0-先说明材料和我的写法)
- [1 这一站要解决的问题](#1-这一站要解决的问题)
- [2 PMPP 作者的课程：把 CUDA 基础连起来](#2-pmpp-作者的课程把-cuda-基础连起来)
- [3 CS149：补的是并行系统，不是 CUDA 语法](#3-cs149补的是并行系统不是-cuda-语法)
- [4 我把 Fall 2025 的课表逐条排了一遍](#4-我把-fall-2025-的课表逐条排了一遍)
- [5 两套材料怎么配合](#5-两套材料怎么配合)
- [6 我核到的、和我没核的](#6-我核到的和我没核的)
- [7 材料与出处](#7-材料与出处)

## 1 这一站要解决的问题

第 1 站建立了执行模型，但那是概念层。这一站要把它变成能写代码、能推导的东西：

- 能从数据形状**推导**线程索引，而不是背 `blockIdx * blockDim + threadIdx`；
- 能说清 global / shared / register 三级的分工，以及每一级为什么存在；
- 能解释同步为什么必须放在正确的位置 —— 放错了不是慢，是错。

再加一层系统视角：SIMD/SIMT 的区别、局部性、带宽上限、同步代价、负载均衡。这一层决定你**能不能解释**一个程序的性能，而不只是描述它。

## 2 PMPP 作者的课程：把 CUDA 基础连起来

入口是 AUB 的课程播放列表，主讲 Izzat El Hajj —— 他是《Programming Massively Parallel Processors》的合著者。

有一条要写清楚：**这套课由 El Hajj 主讲，不是 Hwu/Kirk 主讲。** 推荐它是因为讲者是教材作者之一，不等于教材作者本人在讲。

课程推进的顺序我建议按这个来：数据并行 → 线程索引 → 多维 grid → GPU 架构 → 内存 tiling → 性能考虑，然后再进归约、scan 这类并行模式。

**这一站的边界：** 课程年份较早，基础机制仍然有效，但**工具命令和硬件参数要以当前官方文档为准**。课程里出现的具体型号、具体 flag、具体 profiling 工具名，可能已经不是今天的写法了。公开视频免费；教材本身付费。

## 3 CS149：补的是并行系统，不是 CUDA 语法

CS149 是 Stanford 的并行计算系统课，主讲 Kayvon Fatahalian 和 Kunle Olukotun。它和 PMPP 的分工很不一样：

| | PMPP 作者课程 | CS149 |
|---|---|---|
| 重心 | CUDA 编程基础连成体系 | 并行执行的系统机制 |
| 视角 | 怎么写对、写快一个 kernel | 硬件和系统为什么这样设计 |
| 适合 | 打底 | 补短板、建立判断力 |

所以两套不必都从头刷完：**选一套主修，用另一套补短板**。

**关于录像，这里有一条必须说清的事实。** CS149 Fall 2025 的讲义目录是公开的，但**2025 年的录像不向公众开放**。官方页面原话是：

> We cannot distribute lecture videos to the public this year, but videos from a prior version of the course (2023) are available on Stanford's Youtube Channel.

所以**不能把 2023 年的录像称作「2025 课程视频」**。正确的用法是：讲义用 2025 的，录像用 2023 的，两边按主题匹配，不机械对应讲次。

## 4 我把 Fall 2025 的课表逐条排了一遍

网上（包括我最初看到的资料里）流传着一句「CS149 第 2 讲是 SIMD、第 6 讲是 Roofline」。我把 Fall 2025 的讲义目录抓下来逐条排了一遍，**这句对不上**：

| 官方 Fall 2025 课表 | 讲次 |
|---|---|
| A Modern Multi-Core Processor (Part I)（含 multi-core / SIMD / multi-threading 三种并行形式） | 第 2 讲 |
| Modern Multi-Core Architecture (Part II) + ISPC Programming Abstractions | 第 3 讲 |
| Program Optimization 2: Locality and Communication | 第 6 讲 |
| GPU Architecture and CUDA Programming | 第 7 讲 |
| Data-Parallel Thinking（map / reduce / scan） | 第 8 讲 |
| Efficiently Evaluating DNNs on GPUs: Transformers and ConvNets | 第 9 讲 |

差别在哪：**SIMD 在第 2 讲是以「三种并行形式之一」出现的，不是那一讲的主题**；而**第 6 讲讲的是局部性与通信，不是 Roofline**。按错的编号去找，会在第 6 讲里找不到 Roofline。

```text
按主题找,不按编号找:
  SIMD / SIMT          -> 第 2、3 讲(并行形式与多核架构)
  局部性 / 通信        -> 第 6 讲
  GPU / CUDA / SIMT    -> 第 7 讲
  reduce / scan        -> 第 8 讲
  Transformer / ConvNet-> 第 9 讲
  Roofline             -> Fall 2025 课表标题里没有独立讲次
```

课表是会变的。**用之前先抓一遍当年的目录**，别照抄任何一年（包括我这张表）的编号。

Roofline 本身仍然是要学的概念，只是它不在 Fall 2025 标题明写的位置上。它的作用是把「这个 kernel 是算力受限还是带宽受限」变成一个可以先算再测的判断 —— 正好是第 3 站「先学会判断瓶颈」的前置。

## 5 两套材料怎么配合

我把顺序理成这样：

1. **先用 PMPP 把基础连起来。** 目标是能从数据形状推导线程索引，能说清三级内存的分工。
2. **再用 CS149 补机制。** 目标是能解释「为什么这样写更快」，而不只是知道「这样写更快」。
3. **然后进第 3 站学测量。** 有了机制概念，才知道该在时间线上找什么。

一个具体的判断：如果读完 PMPP 你只是记住了几种优化手法，但说不清它们各自在省什么，那 CS149 那部分不能跳。反过来，如果机制你已经清楚，PMPP 可以只当查阅材料。

## 6 我核到的、和我没核的

**核到了什么。** CS149 讲义目录、2023 录像播放列表、PMPP 播放列表与频道、El Hajj 作者页，全部返回 200。其中两条是**抓页面正文逐字确认**的：一是 2025 录像不公开那句原话，二是 Fall 2025 的 18 讲标题列表。

**没核到什么。** 四条边界：

1. **我没看视频。** 播放列表可访问，但我没有逐段播放，所以不能确认每一讲的录制质量、字幕或实际覆盖范围。
2. **2023 录像与 2025 讲义的一一对应关系我没核。** 我只确认了「2023 录像存在」和「2025 讲义讲次标题」，没有逐讲核对两边内容是否一致。
3. **Roofline 是否在某一年出现过独立讲次，我没往下追。** 我只核了 Fall 2025 这一年的课表。
4. **PMPP 教材内容我没读。** 我核的是课程入口与讲者身份，教材本身是付费的，我没有获取。

## 7 材料与出处

### 7.1 基础体系

- PMPP 作者课程播放列表（AUB，主讲 Izzat El Hajj）— <https://www.youtube.com/playlist?list=PLRRuQYjFhpmubuwx-w8X964ofVkW1T8O4>
- PMPP 官方频道 — <https://www.youtube.com/@pmpp-book>
- 作者主页与教材补充资料入口 — <https://ielhajj.github.io/publications.html>

### 7.2 并行系统

- CS149 Fall 2025 讲义目录 — <https://gfxcourses.stanford.edu/cs149/fall25/lecture/>
- CS149 官方 2023 录像播放列表 — <https://www.youtube.com/playlist?list=PLoROMvodv4rMp7MTFr4hQsDEcX7Bx6Odp>

### 7.3 核验口径

核验日期 2026-11-17。方法：`curl -sIL` 取状态码；对 CS149 讲义目录另取页面正文，逐字提取「录像不公开」那段与 18 条讲次标题。第 4 节的对照表来自这次抓取，不是转述。
