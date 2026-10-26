---
layout: post
title: "量化解剖 ②:EXL3 2.875bpw — trellis 状态机的字节账与逐层比特分配"
date: 2026-10-24 00:00:00 +0800
categories: llm quantization deepseek
---

> "量化解剖"系列第 2 篇。第 ① 篇拆的是 GGUF 查表路线;这篇拆**完全不同的第二条路:bitshift trellis 状态机编码**。承诺不变:数字给出处,算术注明算术,实测注明实测,集群标识不出现,不用 LaTeX。

## 目录

- [1 一张算术恰好闭合的配置](#1-一张算术恰好闭合的配置)
- [2 trellis 状态机:每个权重是几个 bit 的"转移指令"](#2-trellis-状态机每个权重是几个-bit-的转移指令)
- [3 实物四件套:suh / svh / trellis / mul1](#3-实物四件套suh--svh--trellis--mul1)
- [4 装配算术:188,245 个键怎么拼出来的](#4-装配算术188245-个键怎么拼出来的)
- [5 服务时的执行路径:<144 行与 ≥144 行两个世界](#5-服务时的执行路径144-行与-144-行两个世界)
- [6 作者侧 benchmark(4×Blackwell 96GB)](#6-作者侧-benchmark4blackwell-96gb)
- [7 我们的 H800 现状与缺口](#7-我们的-h800-现状与缺口)

## 1 一张算术恰好闭合的配置

直接读 Infatoshi 再制件的 `quantization_config.json`(第一手):

```
quant_method : exl3
codebook     : mul1
layer_bits   : 0-17=3,  18-22=2,  23-39=3
mtp_experts  : "source"      ← 第 40 层起的 MTP/草稿头专家不量,沿用源 checkpoint
non_routed   : deepseek_v4_fp8
    fmt=e4m3, activation_scheme=dynamic,
    scale_fmt=ue8m0, weight_block=[32,32], expert_dtype=fp4
```

平均 bpw 的算术(ib**不是估算,是精确闭合**):

```
35 层 × 3bit  +  5 层 × 2bit(18-22)= 105 + 10 = 115
115 / 40 层 = 2.875 bpw  ← 文件名里的 2.9/2.875 就是这么来的
```

两层诚实口径,都是卡面原文,一条都不能打折:

1. **2.875 只是 routed experts 的平均**。attention / shared / embedding / MTP / Engram 都不在这个数里——非路由件全保留官方 `deepseek_v4_fp8`(e4m3 动态,ue8m0 scale,32×32 块)。全模型口径不是 2.875。
2. **mtp_experts="source"**:投机解码头(DSpark)的专家不做 2-bit,直接沿用源 checkpoint 精度。三家在 DSpark 上姿态一致(第 ① 篇 ELVEZ 单发 7.9GB 无损 repack,第 ③ 篇 Xolotl 也一样)。

为什么 18-22 层是 2bit 而其他 3bit:ExLlamaV3 量化脚本的 measurement 段按校准敏感性**逐层测量决定比特预算**——这是从 EXL2 时代继承下来的"总比特预算下贪心分配"。它跟第 ① 篇"全专家同精度"是不同的工程答案。

## 2 trellis 状态机:每个权重是几个 bit 的"转移指令"

QTIP 系(血统图 §4 详述)的核心替换:**每个权重存的 2/3 个 bit 不是"量化电平编码",而是一个状态机的状态转移指令**;权重值是状态机走过路径的函数。结构账如下(不虚构逐 bit 转移表——那张表在 exllamav3 源码里,本篇给的是可验证的结构):

```
编码(量化侧,离线,GPT 校准指导下):
  1. 权重张量先过两侧 Hadamard 旋转(把局部 outlier 的能量打散到全体)
  2. 初始化一个有限状态寄存器(宽度固定,比如 8 bit 窗)
  3. 对每个权重,在 trellis 上做 Viterbi 动态规划:
     选一条累计重建误差最小的"状态转移路径" →
     每步写出的 2/3 bit 就是这条路径的转移指令
  4. 存:转移 bit 流 + 重构所需的 scale/sign/码本参数

解码(推理侧,逐 kernel,Viterbi 是更近一步"猜"):
  1. 逐权重要走:把下一个 2/3 bit 塞进状态寄存器,窗右滑
  2. 当前窗内容 → 查重构规则 → 出当前权重值(×codebook/mul1 系数)
  3. 前后套 Hadamard 逆变换 → 得到可用于 GEMM 的权重
```

为什么这是 E8 特别不同的思路:IQ2(第 ① 篇)把"8 个权重的联合形状"整体预先压进 1 个字节,靠 E8 格子信息密度;trellis 把 8 个权重间的**序信息**算进去——我的下一个权重跟我前面几个权重"走了一条合法路径",等于每权重实际依赖前 8 个权重的状态。所以名义上 3bit/权重的 trellis 能胜过同等名义比特标量。这也是它解码需要 kernel 状态机内联跑的原因。

一个落地维度的直觉:同一批权重,标量独立编码"全图邻居都一样是 4 个电平",trellis 的"合法了下一步"选项远丰富于"4 选 1"——这就是为什么 trellis 每张量需要**一个不真实的码本名词**:`codebook: mul1`。

## 3 实物四件套:suh / svh / trellis / mul1

看实物比看名字清楚。ExLlamaV3(pin 版 `5be8865`)producer 输出每个张量分四个文件(源码锚点:pack 入口 `quantize.py:1408`,forward 分派 `exl3.py:126`):

```
<name>.suh       对角 scale(单侧变换的缩放,Hadamard 之前)
<name>.svh       对角 sign(单侧变换的符号)
<name>.trellis   trellis 状态机转移 bit 流(主数据,大计件)
<name>.mul1      乘性码本/重塑系数(2.875 这件的选择)
```

要点:

- 两侧 Hadamard 是块变换,块宽 128(`128-block Hadamard`),`suh/svh` 存的就是它对角系数——所以是"小件";真正的占大头是 `.trellis` 主件。
- `mul1` 是这件 EXL3 在"乘性交融码本"谱系上的选型之一(卡面就五字母 codebook: mul1,不吹不黑);汉化理解:重建权重时核心码流之外再乘一个对角系数。Infatoshi 的卡明确:**再制时"没有重校准 LibertAI 已经发过的码本"**——codebook 沿用。
- 全件 **417.56 GB**(作者卡),比 2.875×552B 平摊出的"纯理论比"多出来的是包装件、vision/MTP 不量件、FP8 Engram 以及各 HuggingFace safetensors 元数据。

## 4 装配算术:188,245 个键怎么拼出来的

我们自己 CPU 装配链(本团队 CPU 段已全过:3921 native 键审计 PASS + SM90 扩展 284MiB/112 cubin 构建过)怎么拼的——数字全部交叉闭合:

```
routed experts 侧:   40 × 384 × 3 投影 × 4 文件组(suh/svh/trellis/mul1)
                  = 184,320 键(trellis 系四件套)
native 件(attn/shared/embed/...):
                     96,085 - 92,160(专家键)- 4(Engram.embed)
                     = 3,921 键
mtp_experts="source": 2,401 键保持源件,不作 exl3
Engram 双表:          官方 FP8 表格 4 键

合计:184,320 + 3,921 + 4 = 188,245 键 → 对齐(交叉复核通过)
```

另一层交叉检查:专家总参数量 40 × 384 × 3 × 2304 × 5120 ≈ 5.44×10^11,合 2.875 bpw **专家区字节 ≈195.3 GB**;EP4 每卡 ≈48.8 GB——服务排布时这张单页比任何一张大表都顶用。

LibertAI → Infatoshi 的再制动作:LibertAI 原始量化 pin 版 `c178a012`,Infatoshi 再制保持码本不动、装成 safetensors/VLLM 可服件。所以"EXL3-2.875"实际是原作者+社区再制的接力产物。

## 5 服务时的执行路径:<144 行与 ≥144 行两个世界

ExLlamaV3 的 forward 分派非常具体(`exl3.py:126`),

**张量行数 < 144** → 走 packed kernel,inline 跑 trellis 状态机解码,GEMV 出分;
**张量行数 ≥ 144** → 重构 dense 矩阵再跑普通 GEMM(Hadamard 两次 + 状态机全量展开,临时 fp 矩阵不落地为文件只活在临时 alloc 里)。

这个 144 是我们在 trellis 源码适配结论里的实证分界。**它的运维含义**:2,304 gate/up 上行、5,120 维 down 下行都远超 144,所以推理时每个 expert GEMM 实际都是 temp 重构 + 常规 GEMM 那一条。prefill 阶段 dense 重构占了重头,这是 EXL3 与 IQ2 码本/GEMV 逻辑上对照的一手形迹(对照第 ① 篇:IQ2_XXS 的 decode 就是在 GEMV 内逐字节的查表)。

我们的 H800 kernel 级抽样:拿一层的真实 gate W[2304, 5120] 出来跑,本批实测 255 个 fit 样本 + 100 个 held-out(held-out 未参与 build 权重数据)全过——kernel 层算通,服务层 C1/C16 的 benchmark 是我们的下一颗 GPU 预算。

## 6 作者侧 benchmark(4×Blackwell 96GB)

Infatoshi 卡面第一手实测(**授权硬件 = 4×RTX PRO 6000 Blackwell 96GB, 注意是共享多租户**,不是 H800,不是独占):

**聊天吞吐(aggregate tok/s,三趟聚合)**:

| 并发 | 聚合 tok/s | 说明 |
|---|---|---|
| C1 | **125.861**(124.48–126.66 区间) | 单会话 |
| 中档 1 | 205.51 | |
| 中档 2 | 308.74 | |
| 中档 3 | 338.38 | |
| C16 | **423.110**(420.78–425.61) | 文章中段最常用基准 |
| C32 | 452.16 | 上限密集 |

**首内容时间(p50)**:C1 0.408s → C32 2.499s。

**文件与运行时 KV 容量(同套件对照组)**:

| 件 | 总大小 | KV 容量 |
|---|---|---|
| EXL3 2.875 | **417.56 GB** | **12.78M tok** |
| Native(官方) | 510.30 GB | 4.53M tok |
| NVFP4 | 527.29 GB | 1.57M tok |
| EXL3 3.5bpw | 460.03 GB | 7.41M tok |

**服务配置**:300K context / 32 slots / DSpark5 草稿 / KV 用 FP8 / Engram 常驻 disk / gpu_util 0.90 / EXL batch cap 2048。作者侧镜像固定:`sha256:6094b86f…`,重建验证 = 112 个内嵌 cubin 逐字节一致 + 500 个系统包版本一致(这是验收 step,不是计时)。

一件事读懂这张表:**2.875bpw 买的不只是主件小,是 KV 撑到了 12.78M**——同一硬件 3.5bpw 只剩 7.41M,2.875 反而把 context 撑得更大。量化在这级模型上"压缩比 ↔ 可用的上下文窗口"才是真账本。

## 7 我们的 H800 现状与缺口

> 更新 2026-10-26:本条第一缺口已实测补完——EXL3 4×H800 五档并发 benchmark,见[第 ⑤ 篇](/quant-anatomy-5-exl3-h800-live/)。下述"排队中"为成文当时(10-24)的状态,保留原文。

诚实栏,不藏:

- 已有的:CPU 装配链全过(3,921 键审计 PASS)、SM90 ext 构建过(284MiB/112 cubin)、kernel 级一层 255fit+100held-out 全过、混合件 EOF 关 188,245 键。
- 缺的:**我们 H800 上 EXL3 的 C1/C8/C16 服务 benchmark 尚未跑**——已到冻结包的根骨验证链,排队等 GPU 授权。
- per-card 算术可用:专家区 ≈48.8GB/卡(EP4)+ KV(2.875 的 KV 容量比上表说明);但这不是 VRAM 运行时实测。
- 所以本系列终篇 benchmark 上 EXL3 只会给"作者 Blackwell 数" + "per-card 算术" + "我方 GPU 排队中"标注,不会假装有本地数。

这正是这个系列的边界筹:能实测的本地(Xolotl)实测,作者实测如实引,我方排队中如实排。

## 参考与来源

- 原量化与再制:[LibertAI DeepSeek-V4.1-Flash-EXL3](https://huggingface.co/LibertAIDAI)(commit `c178a012`)、[Infatoshi 2.875 件 + 四件套对照](https://huggingface.co/Infatoshi)(量化 config 与 Blackwell 实测表)
- exllamav3 pin 版 `5be8865`:pack 入口 `quantize.py:1408`、forward 分派 `exl3.py:126`、128-block Hadamard 变换、144 行边界
- 后续实测:[本博客 → 第 ⑤ 篇 EXL3 的 4×H800 五档实测](/quant-anatomy-5-exl3-h800-live/)
- 血统:[本博客 → LLM 量化五年血统图 §4](/llm-quantization-five-lineages/)
- 综合横评:[本博客 → DSV4.1 三基线](/dsv41-three-quant-baselines/)
- 内部 CPU 装配验收与 kernel 级抽样:本团队只读取证产物,集群标识不写入此文
