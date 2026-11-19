---
layout: post
title: "96 张 H100 上复刻 DeepSeek 推理: 大 EP 拆开看"
display_title: "96 卡复刻 DeepSeek：大 EP 拆开看"
subtitle: "PD 分离、two-batch overlap、EPLB —— 每块解决什么问题，代价是多少"
description: "LMSYS 用 12 节点 96 张 H100 复刻 DeepSeek-V3 推理的机制拆解。重点是 two-batch overlap 和 EPLB 两个消融实验的真实数字，以及一个反直觉的负结果。"
excerpt: "把 batch 切成两份让计算和通信重叠，为什么在 32 token 的时候反而慢 27%？"
date: 2026-11-19 00:02:00 +0800
categories: gpu
tags: [GPU, 多GPU, 通信, 性能优化, 基准测试, 工具链]
---

## 0 先说明材料和我的写法

材料是 LMSYS 2025 年 5 月 5 日发的 [Deploying DeepSeek with PD Disaggregation and Large-Scale Expert Parallelism on 96 H100 GPUs](https://www.lmsys.org/blog/2025-05-05-large-scale-ep/)。

**这篇我一次实验都没做，也没有集群。** 所以这一篇里**没有任何我自己跑出来的数字** —— 凡是数字都标了出处。原文有 27 个小节、3 个代码块、表里的数字很密，我按「这块解决什么问题、代价是什么」把它拆了一遍，并且把原文**自己承认的限制**单独列了一节（第 8 节），因为那些话比结论更有用。

我做的是纯粹的阅读和核对：把 27 个小节的正文抓下来，把里面所有带数字的句子挑出来对照，确认没有把「我推断的」写成「原文说的」。凡是我自己的判断，第 10 节逐条列了。

顺便说一件和本系列别处不重复的事：DeepEP 的单机 IPC 细节、以及另一个项目的 EPLB 实现，我已经在别的地方写过了。这一篇只讲 **LMSYS 这一套在 96 卡规模上怎么组装起来**，以及**两个消融实验到底量出了什么**。

### 目录

- [0 先说明材料和我的写法](#0-先说明材料和我的写法)
- [1 规模与结论先落地](#1-规模与结论先落地)
- [2 四个部分各走什么并行](#2-四个部分各走什么并行)
- [3 为什么必须把 prefill 和 decode 拆开](#3-为什么必须把-prefill-和-decode-拆开)
- [4 DeepEP 的两种 dispatch 模式](#4-deepep-的两种-dispatch-模式)
- [5 Two-batch overlap: 机制与它真正的难点](#5-two-batch-overlap-机制与它真正的难点)
- [6 EPLB: 为什么是 288 而不是 256](#6-eplb-为什么是-288-而不是-256)
- [7 两个消融实验量出了什么](#7-两个消融实验量出了什么)
- [8 原文自己承认的限制](#8-原文自己承认的限制)
- [9 把结论收成一张表](#9-把结论收成一张表)
- [10 2025 到今天](#10-2025-到今天)
- [11 材料与出处](#11-材料与出处)

## 1 规模与结论先落地

先把硬件和数字摆出来，后面所有机制都挂在这上面。

- **12 个节点，每节点 8 张 H100，合计 96 张**，跑在 Atlas Cloud 上，节点间 InfiniBand。
- 每节点吞吐：**52.3k 输入 token/s**，**22.3k 输出 token/s**（2000 token 输入序列）。
- 按原文自己的折算，本地部署对应 **$0.20 / 1M 输出 token**，约为官方 DeepSeek Chat API 的 **五分之一**。
- 相比同样资源下的朴素张量并行，输出吞吐**最高提升 5 倍**。

**这些数都是在特定输入长度下的** —— 2000 token。原文后面分开测 prefill 和 decode 时用的是别的长度，数字不一样，别混。

## 2 四个部分各走什么并行

这是全文的地基。DeepSeek-V3 的四类层，瓶颈完全不同，所以并行策略也不同：

| 部分 | 瓶颈 | 策略 |
|---|---|---|
| Attention | KV cache 显存 | DP attention（数据并行） |
| Dense FFN | 只有 3 层，但峰值显存高 | 张量并行，但 TP 要调小 |
| Sparse FFN | 专家权重占显存 | EP（专家并行） |
| LM Head | 词表大 | 单独处理 |

**Dense FFN 那一段有个值得学的推导。** 原文给了一个显存占用函数，在假设 DP = TP 的前提下，它在 TP = √(N_param / ((1+k)·N_hidden_state)) 处取最小。DeepSeek-V3 的 intermediate size 是 **18,432**。代入两种情形：

- **prefill 阶段**：CUDA Graph 通常关掉，k = 0。此时每设备 token 数很容易超过 2048 —— 算出来的最优 TP **只有 3 或更小**。
- **decode 阶段**：实用配置可能是每设备 128 token、k = 3。这时最优 TP 是 **6**。

**「最优 TP 是 3」这种数在工程上很尴尬** —— 它意味着密集层几乎不该切。原文的做法是走 DP：把通信压成「上一层注意力之后一次 reduce-scatter + 下一层之前一次 all-gather」，通信量**减半**。这个开关就是 `--moe-dense-tp-size=1`。

Sparse FFN 那边，专家权重是显存瓶颈，所以走 EP。这也直接引出了后面 EPLB 的全部问题。

## 3 为什么必须把 prefill 和 decode 拆开

原文列了统一调度（prefill 和 decode 混在一批里）的三个问题，这三条是 PD 分离存在的全部理由：

1. **Prefill 打断 decode。** 新来的 prefill 批会打断正在跑的 decode 批，token 生成的延迟被拉长。
2. **DP attention 失衡。** 一个 DP worker 在处理 prefill 批，另一个同时在处理 decode 批，后者的延迟被拖高。
3. **和 DeepEP 不兼容。** DeepEP 对 prefill 和 decode 走的是**不同的 dispatch 模式**（下一节），统一调度根本没法同时满足两边。

**第三条是最硬的**：前两条是性能问题、可以调，第三条是结构性的 —— 只要 DeepEP 的两种模式不能在同一个通信组里共存，统一调度就成立不了。原文说得很直白：不做 PD 分离时，auto 模式**无法在同一个通信组里同时支持 normal dispatch（给 prefill）和 low-latency dispatch（给 decode）**，而这会挡住 DP attention 的兼容性。

## 4 DeepEP 的两种 dispatch 模式

DeepEP 提供两种 dispatch，分工是按序列长度切的：

| 模式 | 面向 | 优点 | 代价 |
|---|---|---|---|
| Normal Dispatch | 长输入序列（prefill） | 吞吐最大化 | 产生**符号化 shape**，**不兼容 CUDA Graph** |
| Low-Latency Dispatch | decode 出 token | 延迟最小，**支持 CUDA Graph** | 必须**预分配固定显存**，超了就 runtime error |

**这两个模式的取舍是互斥的，不是可以调的参数。** Normal 为了吞吐放弃了 CUDA Graph 兼容；Low-Latency 为了延迟和 CUDA Graph 换来了固定显存预分配，代价是「显存需求超过预分配就报错」。

SGLang 在集成时提供了 auto 模式，按负载动态选。但 auto 模式有前面说的那个限制：不做 PD 分离就没法同时支持两边。**所以 PD 分离不只是「性能优化」，它是让 auto 模式能成立的前提。**

原文还有一张模式 × 能力的表（长输入 / 长输出 / DP Attention / CUDA Graph），是用来给这个限制做证据的。

## 5 Two-batch overlap: 机制与它真正的难点

TBO 的思路一句话说完：**把一个 batch 切成两个 micro-batch，让计算和通信重叠**，顺带因为有效 batch 减半而降低峰值显存。这是照 DeepSeek 的系统设计做的。

但原文明确说「把 TBO 落地有两个实现上的难点」，这两条比机制本身有意思：

**难点一：代码会重复。** 直接写 TBO 会导致「管理多个 micro-batch」的逻辑被复制一遍。micro-batch 数量或者重叠方案一变，代码就更难维护、更容易错。

**难点二：prefill 阶段 DeepEP 的 normal dispatch 会阻塞 CPU。** 原文说即使开了异步模式也是这样。CPU 被卡住，流水线就停了，GPU 空转，TBO 的收益直接抵消掉。

**TBO 的解法是一个抽象层：operations + yield points。** 代码照「只处理一个 micro-batch」写，在需要的地方插一个 `YieldOperation()` 让别的 micro-batch 继续：

```python
operations = [
    self._forward_attn,
    YieldOperation(),   # 让出执行权给其它 micro-batch
    self._forward_dispatch,
    self._forward_mlp,
    YieldOperation(),   # 另一个让出点
    self._forward_combine,
]
```

**这个抽象的好处是它把「重叠区域在哪」变成了一个可改的列表**，而不是散在代码里的 if。原文说这样能支持不同的重叠区域选择，甚至以后做 three-batch overlap 也只需要很小的改动。`_forward_attn` 那种单 micro-batch 的处理函数**一行都不用改**。

prefill 那边还要额外做一件事：**调整发射顺序**，来绕开 DeepEP dispatch 阻塞 CPU 的问题。原文的说法是「refine the launch order during the prefill phase to avoid CPU-blocking via the dispatch operation in DeepEP」。

## 6 EPLB: 为什么是 288 而不是 256

MoE 里 EP 的固有问题是**负载不均**：GPU 之间任务分不匀，系统就得等最慢的那个（计算或者通信），算力和显存都浪费。而且**EP 规模越大越严重**。

EPLB 的输入是专家分布统计，输出是最小化不均衡的专家排布。这里有个数字值得注意：

**用户可以分配冗余专家，比如额外 32 个。加上原来的 256 个，得到一个 288 个专家的池子。**

288 这个数不只是「多 32 个」那么简单，它换来两件事：

- **可以复制热点专家。** 最常用的专家复制多份；中等使用率的专家和极少用的专家打包到同一张卡上。
- **并行度不再被限制在 2 的幂。** 原来的 256 个专家，并行度只能是 2 的幂；**288 个专家让 12 或者 72 这样的并行度成为可能**。

**第二条是纯工程收益。** 96 卡的集群上，EP72 这种配置在 256 专家的约束下根本表达不出来 —— 96 张卡要做 72 路专家并行，256 除以 72 不是整数。这就是为什么原文的 decode 实验能跑在 9 节点（EP72）上。原文明确说这带来了「更大的并行设计灵活性」。

**balancedness 的定义要说清楚**，否则后面 1.49x / 2.54x 那两个数没有意义：

- 在模拟里，GPU balancedness = **一个 MoE 层在 GPU 之间的「平均计算时间 / 最大计算时间」之比**，其中计算时间用该 GPU 的 token 数来估计。
- 在案例研究里，balancedness = **token 数的平均值 / 最大值**（跨专家）。

原文的结论是：**利用率随着节点数增加而下降，开了 EPLB 之后显著改善**；而且 balancedness 和吞吐之间有强相关。**这两句话是这篇里最有价值的因果链** —— 它把「负载均衡」从一句口号变成了一个可以画在横轴上的量。

EPLB 要在真实服务里有效，需要输入分布贴近实际负载，原文给了两个办法：**加大 batch**（大 batch 减少专家使用的随机波动，可以通过扩集群或者 MTP 实现）、**定期重平衡**（利用时间局部性，但要求专家重载足够快）。

## 7 两个消融实验量出了什么

这一节是全文最硬的部分。**两个消融都有具体的数和明确的适用条件。**

### 7.1 Two-batch overlap

**Prefill 阶段，两个收益，性质不同：**

- **支持更大的 batch。** 原版每设备最多 8192 token，到 16384 就 OOM。TBO 靠优化输入 token 的显存把这些撑住了，让每设备 batch 能到 16384。**在所有其它配置都调到最优的前提下，相比开 TBO 提升了 40.5%。**
- **吞吐提升。** 在**每设备 token 数相同**的情况下，把计算（attention、MLP）和通信（DeepEP 的 combine、dispatch）重叠，吞吐比原版高 **27% 到 35%**。

注意这两个收益要分开看：**40.5% 那一档包含了「batch 变大」带来的好处，27%–35% 那一档是纯重叠的收益**（同样 token 数）。原文把这句写得挺清楚 ——「even when processing the same token count per device」。

**Decode 阶段就复杂了，而且有一个负结果：**

- 加速**取决于 batch size 是否超过一个阈值，这个阈值在 64 到 128 token 之间**。低于它 TBO 收益极小**甚至是负的** —— 原文给的例子是 **每设备 32 token 时 −27%**。
- **256 token 时加速 25.5%**，吞吐 22310 token/s。
- **模拟 MTP 场景下收益最大**：每设备 128 个请求、每 decode step 生成 256 token 时，**加速 35%**，吞吐 17552 token/s（不开 TBO 是 12929）。原文给的原因是 attention 处理时间被拉长，正好和 DeepEP 的通信开销对齐。

**为什么小 batch 会变慢？** 原文说小 decode batch 下 kernel 效率本来就低。**这句话背后是一个通用规律：重叠的收益要能盖过切分 batch 带来的效率损失,才有得赚。** batch 小到一定程度，两个 micro-batch 都喂不饱 GPU，重叠省下的通信时间还不够赔 kernel 效率的下降。

**细节拆解里还有一个反直觉的观察。** 原文比较了三个 prefill 场景（TBO+16k、TBO+8k、no-TBO+8k），发现：

> **no-TBO 的 8k 场景，单 kernel 速度比 TBO 的 16k 场景更快** —— 尽管两者的 kernel 有效 batch size 都是 8k。

原文给的可能原因有三个，而且**没有下结论**：TBO 下可用的 SM 变少了、重叠时可能有 noisy neighbor 干扰、计算和通信 kernel 不兼容。原文把这条列为 SGLang 未来的优化方向。

**这条负结果比任何加速数字都有价值** —— 它说明「有效 batch size 相同」并不等于「kernel 表现相同」，重叠本身有代价。

decode 的细节拆解里还有一条对比：TBO+256 vs no-TBO+128，**两者 kernel 的 batch size 相同**，此时只有「没被重叠的通信」在 no-TBO 下变慢了，计算部分一致。原文解释说和 prefill 不同，**decode 的通信 kernel 要么占满 SM（send/receive 时）、要么一个都不用（inflight 等待时）**，所以不会和计算 kernel 抢资源。

### 7.2 EPLB

**总体：prefill 加速 1.49x，decode 加速 2.54x。** 原文说随着 rank 数增加不均衡会加剧，EPLB 在大规模实验里有效地解决了这个问题。

**这里必须把原文的免责声明一起写上**，否则这两个倍数会被误用：原文说考虑到 EPLB 对负载分布和分布漂移很敏感，他们**专注于定性、可推广的结论，而不是真实世界的性能 —— 后者需要生产数据**。也就是说这两个倍数是在**分布内数据**上测的。

两个案例研究：

- **不均衡 vs 吞吐**（decode，1800 输入 token / 100 输出 token / batch 256）：把 balancedness 和吞吐一起画在 decode step 上，结果是**强相关**。
- **专家分布统计**：大多数专家很少被用到，少部分被重度使用 —— 这是 MoE 模型的固有特性。prefill 和 decode 的分布**相似但有明显差异**，而**这正好支持 PD 分离**：分开之后两个阶段可以各自用不同的专家排布。

## 8 原文自己承认的限制

这一节我单独列出来，因为原文写得比结论部分更诚实，而且这些限制决定了上面所有数字的适用范围。

| 限制 | 原文的具体说法 |
|---|---|
| **延迟** | 当前优化聚焦吞吐，**TTFT 是 2–5 秒**，**ITL 约 100ms** —— 离实时场景还差得远 |
| **序列长度** | 受 96 卡限制，只能做较短序列；要更长序列得扩资源 |
| **MTP 集成** | SGLang 支持 MTP，但**和 DP attention 没有完整集成**，混合并行配置下效率下降 |
| **EPLB 分布** | 实验用的是**分布内数据**，不能反映真实世界的变异性；后续该做分布漂移下的实验 |
| **灵活 TP** | DeepSeek-V3 密集 FFN 的最优 TP 很小但大于 1，而 SGLang 只支持纯 TP 或纯 DP，显存用得不是最优 |
| **Blackwell** | 当前只支持 Hopper，正在做 Blackwell 兼容（还留了赞助联系方式） |

**TTFT 2–5 秒这条要单独说。** 它意味着这篇文章的成果是「吞吐向」的：60 倍吞吐的意义在于批量离线推理的成本（$0.20/1M token），不在于交互式聊天。看吞吐提升的时候要记得这个前提。

## 9 把结论收成一张表

| 反模式 | 材料里的说法 | 代价 / 收益 | 适用条件 |
|---|---|---|---|
| prefill 和 decode 混在一批调度 | 「Prefill 批会打断 decode 批」 | 无直接数字 | 最硬的理由是和 DeepEP 双模式不兼容 —— 结构性的，不是调参能解决 |
| 不用 PD 分离就想同时要两种 dispatch | 「auto 模式无法在同一通信组里同时支持」 | 挡住 DP attention | 两种模式互斥：normal 丢 CUDA Graph，low-latency 要预分配显存 |
| 大 EP 不做负载均衡 | 「利用率随节点数增加而下降」 | prefill 1.49x / decode 2.54x | **分布内数据**；原文自承需生产数据才能谈真实性能 |
| 只有 256 个专家 | 「并行度被限制在 2 的幂」 | 无法表达 EP72 | 加 32 个冗余专家成 288，换来 12 / 72 这类并行度 |
| 计算和通信串行 | 「通信带宽限制增加整体延迟」 | prefill 27%–35%，decode MTP 35% | **decode 下 batch 低于 64–128 token 时收益为负**（32 token 时 −27%） |
| 直接写 TBO | 「导致 micro-batch 管理逻辑重复」 | 维护成本 | 用 operations + yield points 抽象；且 prefill 必须调发射顺序避开 CPU 阻塞 |
| 假设「有效 batch 相同 = kernel 表现相同」 | 「no-TBO 8k 的单 kernel 比 TBO 16k 更快」 | 负结果，原文未定论 | 三个猜测：SM 变少、noisy neighbor、kernel 不兼容 |

**「适用条件」这一列不是凑数的**：decode 的 27%–35% 和 −27% 是同一个机制的两种结果，差的就是 batch size 有没有过 64–128 这个门槛；而 1.49x / 2.54x 明确只在分布内数据上成立。

## 10 2025 到今天

材料是 2025 年 5 月发的。有几条现状值得追，逐条给主源：

- **SGLang 是活的。** 仓库在 [sgl-project/sglang](https://github.com/sgl-project/sglang)，PD 分离和大 EP 这些功能都已经进去了。原文说 `--moe-dense-tp-size=1` 是那个开关。
- **Blackwell 支持是当时明确列出的待办。** 原文写「currently only supports Hopper」，并说在做下一代兼容。**本文不判断这件事今天做完了没有** —— 我没有核实，所以标为**没确认**。
- **DeepEP / DeepGEMM 也是活的**，在 DeepSeek 自己的组织下开源。这一篇引用的两种 dispatch 模式是 2025 年 5 月的状态。
- **这篇文章只覆盖 Hopper。** 后面几代硬件上 SM 数、共享内存、异步拷贝能力都变了，TBO 那些「SM 变少」的猜测在别代卡上未必成立。

**已消失/已改变的**：材料里没有提具体的 CLI 子命令名（除了 `--moe-dense-tp-size=1`），所以我也不写 —— 没真跑过的命令名不写。

## 11 材料与出处

材料：

- [Deploying DeepSeek with PD Disaggregation and Large-Scale Expert Parallelism on 96 H100 GPUs](https://www.lmsys.org/blog/2025-05-05-large-scale-ep/)（LMSYS，2025-05-05）

本文引用的数字全部来自这一篇，逐条对应关系如下（**没有一个是实测的**）：

| 数字 | 出处 |
|---|---|
| 12 节点 / 96×H100 / InfiniBand | Highlight、Experimental Setup |
| 52.3k 输入、22.3k 输出 token/s | Highlight |
| $0.20/1M 输出 token、官方 API 的五分之一 | Highlight 后的成本折算段 |
| 输出吞吐最高 5 倍 | 同段（对比朴素 TP） |
| 18,432 intermediate size、最优 TP 公式 | Dense FFNs 节 |
| prefill k=0 / decode k=3、最优 TP 3 或 6 | 同节 |
| 通信成本减半 | 同节（DP 的 reduce-scatter + all-gather） |
| 256 + 32 = 288 专家、并行度 12 或 72 | Expert Parallelism Load Balancer 节 |
| prefill 40.5% / 27%–35% | Ablation: Two-batch Overlap |
| decode −27% @32 token、25.5% @256 token、22310 token/s | 同节 |
| MTP 35%、17552 vs 12929 token/s | 同节 |
| EPLB 1.49x (prefill) / 2.54x (decode) | Ablation: EPLB |
| 强相关（balancedness vs 吞吐） | 同节案例研究 |
| TTFT 2–5 秒、ITL ~100ms | Limitations and Future Work |

**哪些是我自己的判断**（逐条列）：

1. **「40.5% 那一档包含 batch 变大的收益，27%–35% 是纯重叠收益」** —— 这是我对原文两句话的对照结论。原文分别写了「comparing the TBO flag with all other configurations made optimal」和「even when processing the same token count per device」，我的解读是这两档的性质不同。**原文没有明确这么对比着说。**
2. **「288 专家换来 EP72 是纯工程收益」** —— 我的归纳。原文只说 288 让 12 或 72 这样的并行度成为可能，没有把它和 96 卡的实验规模直接连起来。
3. **「小 batch 变慢背后是重叠收益盖不过切分损失」** —— 这是我的解释。原文只说小 decode batch 下 kernel 效率低。
4. **「TTFT 2–5 秒决定了这篇文章是吞吐向的」** —— 我的推断，原文没有做这个定位。

**没核到的**：

- **所有性能数字都不是我测的。** 我没有 96 卡集群，也没有复现任何一项。
- **图中数据我没有逐点读取。** 原文有多张图（吞吐对比、profile、balancedness 曲线、专家分布），我引用的是**正文里写出来的数字**，不是从图里估的。正文没给数的图（比如 balancedness 曲线的具体点），我一个字都没写。
- **1.49x / 2.54x 的实验设置细节** —— 原文没有给出这两个倍数的完整配置表（规模、batch、序列长度），只说「in our large-scale experiments」。**所以这两个倍数我不能给出适用范围，只能照抄。**
- **Blackwell 支持今天的状态** —— 没确认。
- **`--moe-dense-tp-size=1` 这个开关今天是否还存在、行为是否一样** —— 我只核到原文写了它，**没有在代码里核实**。
