---
layout: post
title: "量化解剖 ①:ELVEZ IQ2_XXS+Q2_K GGUF — 把一个 340GiB 的文件拆到字节"
date: 2026-10-24 00:00:00 +0800
categories: llm quantization deepseek
---

> 这是"量化解剖"系列第 1 篇。上一篇[横评](/dsv41-three-quant-baselines/)回答了"三个基线各是什么、怎么选";本系列回答更细的问题:**量化过程到底一步步做了什么、产物文件里每个字节是什么**。三个模型各一篇,最后一篇是同口径 H800 benchmark。
>
> 方法承诺:写到数字就给出处(公开模型卡/公开源码/我们本地实证),算术注明是算术,实测注明是实测;集群内部标识一律不出现;公式全部用大白话和数字例子,不用 LaTeX。

## 目录

- [1 这个文件本身:一张 340.6GiB 的账单](#1-这个文件本身一张-3406gib-的账单)
- [2 张量级精度分配:1,046 个张量各拿什么格式](#2-张量级精度分配1046-个张量各拿什么格式)
- [3 两种 2-bit 块的字节解剖:IQ2_XXS 与 Q2_K](#3-两种-2-bit-块的字节解剖iq2_xxs-与-q2_k)
- [4 imatrix 校准:8192 token 花在哪了](#4-imatrix-校准8192-token-花在哪了)
- [5 制作与验证:69 分钟、97.21% 覆盖、byte-identical](#5-制作与验证69-分钟9721-覆盖byte-identical)
- [6 配套件与运行面:DSpark、Engram、以及"为什么通用 llama.cpp 跑不了"](#6-配套件与运行面dsparkengram以及为什么通用-llamacpp-跑不了)
- [7 它在我们 H800 语境下对应什么](#7-它在我们-h800-语境下对应什么)

## 1 这个文件本身:一张 340.6GiB 的账单

产物全名 `DeepSeek-V4.1-Flash-1017-IQ2_XXS-Q2_K-imatrix.gguf`(基座 rev `1bae0e10`)。ELVEZ 模型卡给的第一手数字:

| 项 | 值 |
|---|---|
| 文件总大小 | 365,713,686,528 B(**340.6 GiB**) |
| 主 SHA256 | `e78230…`(全文校验) |
| 张量总数 | **1,046** |
| 常驻内存区(权重等) | ~151.8 GiB |
| 文件尾部 Engram(FP8 原值) | ~188.8 GiB |
| 151.8 + 188.8 | = 340.6 GiB,账正好闭合 |

关键点先说破:**这不是"一份 2-bit 模型"**,而是"151.8GiB 权重区 + 188.8GiB Engram 哈希大三表同箱打包"。Engram 部分保持官方 FP8(E4M3 值 + 每 32 值一个 E8M0 scale)原封放在文件尾,引擎按需从盘按行取——量化只发生在权重区,Engram 连碰都没碰。这一拆对后文理解"bpw 真实成本"很重要:把 340.6GiB 平摊到 552B 参数没有意义,因为其中 189GiB 是 FP8 的查询表,1017 个 checkpoint 里就有它。

## 2 张量级精度分配:1,046 个张量各拿什么格式

按模型卡给出的分配规则(DSV4.1-Flash = 40 层 × 384 routed experts + 稠密件):

| 张量类别 | 格式 | 精度含义 |
|---|---|---|
| routed 专家 gate/up | **IQ2_XXS**(imatrix 加权) | E8 系码本查表,2.0625 bpw(下面 §3.1 拆字节) |
| routed 专家 down | **Q2_K**(imatrix 加权) | superblock + scale-of-scale,2.625 bpw(§3.2 拆字节) |
| attention / shared experts / lm_head | Q8_0 | 8.5 bpw,占参数不到 2% 的"保险件" |
| norms / router(小件) | F16 / F32 | 保 router 分布误差 |
| Engram 双表 | FP8 原值(尾部) | 不量化,按需按行从盘取 |

这个分配本身就是 R1-int2 时代传下来的公开配方形状:**路由专家压到底,其余件留高位**。注意 asymmetry:gate/up 用 IQ2_XXS(质量略优的"雕出来"码本),down 用 Q2_K(结构更规整、解码更便宜)——in/out 维度不同,down 是收敛端,imatrix 对它的加权更重要。

另一个非常少见的诚实记录:**1,288 个专家槽没有进 imatrix 层,用非 imatrix 量化**(下面 §4 讲为什么)。模型卡直接写了,没有藏。

## 3 两种 2-bit 块的字节解剖:IQ2_XXS 与 Q2_K

这一节是本篇与上一篇横评最大的"深入度差"——把两种格式拆到"一个 256 权重块 = 几个字节,每个字节拆了什么"。

### 3.1 IQ2_XXS:E8 码本查表,528 bit/256 权重 = **2.0625 bpw**

IQ2_XXS 的核心思想:**不把每个权重单独量化,而是把 8 个连续权重当一个"8 维向量形状",从 256 个预设码字(codeword)里找最近的那个**。llama.cpp 源码 `ggml-quants.c:2860` 里就是那张预设表 `kgrid_2bit_256[256]`:

- 每行 = 1 个码字 = 8 个坐标,坐标 ∪ {±1,±3,±5,±7}(奇整数 × 块 scale)
- 打包规则(与 `ggml_quantize_init` 一致):`l = (packed >> 2i) & 3`,`coord = 2l+1 ∈ {1,3,5,7}`,符号独立存

为什么敢这么干:E8 是 8 维空间最密的球堆积格——同样数量的候选点,格点比"每维独立 4 电平"的方形网格近邻覆盖误差更小。2D 平面类比:方形格 vs 三角格(六边形最密堆积),等密度下最坏覆盖半径 0.707 vs 0.620(-12.3%);这个数字随维度放大越来越悬殊。

一个 **256 权重的块**实际存这些(按 `block_iq2_xxs` 源码推):

```
16 bit                块 scale d(fp16)
8 个 × [4×8bit 码字号 + 4×7bit 符号 + 4bit 子块 scale] = 8×64 bit = 512 bit
合计 16 + 512 = 528 bit / 256 权重 = 2.0625 bpw
```

对照一个理想端到端"每权重 2.0 整"还差 0.0625 bpw——就是那一个 fp16 块 scale 的摊销。

反量化照样从源码(`ggml-quants.c:2489`)读出来:

```
y[j] = db × grid[j] × sign[j]
其中 db = d × (0.5 + subscale) × 0.25
grid[j] 来自那个 1 字节码字号查 256 码字表,sign[j] 来自 7bit 符号查表
```

最近邻搜索用 `iq2_find_best_neighbour`(`ggml-quants.c:3271`):把 8 个实数按"scale × 权重"逐维加权,在 256 个码字里找加权误差最小的一套坐标。**LLM 里"查表量化"的真身就是函数这一层**:不是 `round(x/3)`,是对 8 维形状做最近邻。

### 3.2 Q2_K:superblock + scale-of-scale,672 bit/256 权重 = 2.625 bpw

Q2_K 是 K-quant 家族里的"朴素但够格"形态,`block_q2_K` 源码布局(`ggml-common.h:560` 附近附件):

```
block_q2_K:
  scales[16]      16 B  → 8 个子块 × (scale 4bit + min 4bit)
  qs[64]          64 B  → 256 个 2-bit 值打包
  d, dmin          2×fp16 = 4 B → 块级 scale 与 shift
合计 128 bit(scales)+ 512 bit(qs)+ 32 bit(d/dmin)= 672 bit / 256 = 2.625 bpw
```

它不像 IQ2_XXS 那样"8 维查 E8 码字",而是回到标量路线:每 32 权重一子块,子块有 4bit scale + 4bit min,再由块级 fp16 d/dmin 双重量化(scale-of-scale)——这是 SpQR 论文"double quantization"思路的直系工程实现。与 IQ2_XXS 比好处在解码 kernel 极简单、适配面广,代价是质量略逊;所以 gate/up(质量敏感支)投了 IQ2_XXS,down(量大多用支)给 Q2_K。

### 3.3 一块 E8 码本长什么样

我们在本地有一个配套演示页(AutoQ 平台,#anat 页签,本地起服务即可交互)能看到:

- L2 卡 = 2D 方形格 vs 三角格的对照示意图
- L2+ 卡 = `kgrid_2bit_256[256]` 全部 256 个码字可点选,联动"亲手查最近码字"工具
- E8 的 240 根 Coxeter 面投影(自检 8 同心环 × 30 点)

不装东西也能在脑子里跑:8 个连续权重 → 归一化 → 找最近码字 → 存 1 字节码字号 + 符号位 + scale。量化到 2-bit 在 IQ 系里就是这么一个"8 维形状检索"动作。

## 4 imatrix 校准:8192 token 花在哪了

这个项目**没有训练**,但 imatrix 校准非常讲质量。模型卡第一手数据:

- 校准 token 数:**8,192**(短到离谱,但这符合 AWQ 系校准直觉)
- 校准样本三轮轮转选样,routed expert 激活覆盖从 **89.40% → 97.21%**
- 绝对口径:15,360 个专家槽(40 层 × 384)覆盖到 14,931 个
- **没覆盖的 1,288 个专家槽用非 imatrix 量化降级处理,记录在卡面里**

imatrix 干的事一句话重申:在校准语料跑一遍,统计每层激活二阶矩(每维活性权),量化时"重要维误差罚重、非重要维放飞"。8192 token 够把专家浓度分布拉出来,拉不到的是尾部冷门 expert——所以 triage 这 1,288 个槽的做法是**显式降级并记录**,比"imatrix 全覆盖但事实上零样本"诚实得多。

## 5 制作与验证:69 分钟、97.21% 覆盖、byte-identical

卡面第一手:

- 主 GGUF 转换 **69 min @ Apple M3 Ultra / 24 线程**(制作成本极低——PTQ 离线查表 + 打包,无 GPU)
- 与 antirez/ds4 家的 `gguf-tools` @ `9139e2ae` **当日 byte-identical**(用 `gguf-tools --payload` 全 1,046 张量过验证)
- DSpark.gguf 单独 7.9GB / 81 张量:MXFP4 无损失 repack 官方 shards 44-46 + Q8_0/F16/F32 小件

这比 GPTQ 系家家 GPU 因子的"校准-补偿"链的制作侧成本低一个量级,是这条线的天然优势之一。

## 6 配套件与运行面:DSpark、Engram、以及"为什么通用 llama.cpp 跑不了"

三件要分清:

1. **DSpark.gguf(7.9GB)**:官方投机解码草稿头的无损 MXFP4 repack + 必要小件。卡面给了 M3 Ultra 实测:短 prompt 35.96 → **47.14 tok/s(1.31×)**,38.8k context 34.06 → 36.94(1.08×),draft 接受率 68% → 61%(上下文长接受的 token 数自然少一点)。注意它是配在主件旁边的,不是可选可选不要。
2. **Engram 188.8GiB**:FP8 原值放在文件尾部,服务时按行按需从盘取(12 byte × 2-scale 粒度行),不是全部搬内存。
3. **Engram 布局是 ELVEZ 自排**:模型卡**明确警告**:这份 GGUF 在通用 llama.cpp/Ollama **跑不起来**,只在 IXV 自家引擎(ixv-server,Metal,M3 Ultra)验证过。换句话说,它是"GGUF 容器 + 私有布局"——文件读得懂,引擎接不上。

最后一项是后面终篇 benchmark 时**最重要的诚实点**(下面 §7)。

## 7 它在我们 H800 语境下对应什么

实事:**ELVEZ 的 GGUF 文件本身从未在 H800 上跑过**(结构性缺口:引擎不兼容 + Engram 私排)。这一点在后续终篇 benchmark 里要特别说明。

但它在 H800 语境下的"同配方锚"是我们自己的一条线:内部自研 Q2 栈的**专家精度配比与 ELVEZ 同族**(gate/up = IQ2_XXS 类,down = Q2_K 类),在 4×H800 TP4EP4 DSpark5 FULL_DECODE 配对下的真实实测数列(MATH 前 64 题、固定 128 输出、并发 C1/C8/C16/C32):

```
C1  :    39.01 tok/s 聚合
C8  :   265.72 tok/s
C16 :   482.43 tok/s
C32 :   825.89 tok/s  ← 聚合,单请求约 27 tok/s
TTFT: 0.176s(C1)→ 16.7s(C256)
TPOT: 24.45 → 48.49 ms
专家 payload/卡: 全局 142.38 GiB ÷ EP4 = ≈35.60 GiB/卡
```

这些数字全部出自我方 H800 实测记录(内部参考,细节对博文而言终点是"同配方的 H800 真实量级"已经有了)。另一条 M512 短 A/B(window 吞吐 baseline → 候选 445 → 676 量级)已封存待 Root 复算定案,不在此文预告收益。

所以这一篇的 H800 借鞋是:**IQ2_XXS gate/up + Q2_K down 这条配方族,在 H800 上有真实落点**,ELVEZ 是它在 GGUF 容器里的公开代表,内部栈是它在 vLLM 容器里的私有对应。下一篇(②)讲 EXL3:同样 2 字头,走的是 trellis 状态机那条完全不同的路。

## 参考与来源

- ELVEZ 模型卡:`DeepSeek-V4.1-Flash-1017-IQ2_XXS-Q2_K-imatrix.gguf`(文件大小、SHA、张量分配、imatrix 覆盖、制作时长、IXV 警告均出此)[huggingface.co/Elvez](https://huggingface.co/Elvez)
- llama.cpp 公开源:`ggml/src/ggml-quants.c`(IQ2_XXS 表/解码/最近邻),`ggml/src/ggml-common.h`(block_q2_K 结构)
- 血统:[本博客 → LLM 量化五年血统图](/llm-quantization-five-lineages/)§3.2
- 综合横评:[本博客 → DSV4.1 三基线](/dsv41-three-quant-baselines/)
- 内部 H800 数:本团队只读实测记录,集群标识不写入此文
