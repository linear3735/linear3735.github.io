---
layout: post
title: "量化解剖 ④:三基线的 H800 真实 benchmark 对照——吞吐、显存、内存、KV 全账"
date: 2026-10-24 00:00:00 +0800
categories: llm quantization deepseek
---

> "量化解剖"系列终篇。前 ③ 篇把三个 2-bit 基线的量化过程拆到字节;这一篇回答剩下那个问题:**它们真在 H800 上跑起来,快多少、占多少**。
>
> 这篇最重要的部分不是数字,是**口径**:三个"模型"其实是三个不同执行器、三种不同硬件环境、两类不同来源的数字——混在一起谈"谁快"是错的。所以第 0 节先把口径钉死,后面所有表都按这口径来。

## 目录

- [0 口径声明:哪条数字是哪家的、在什么硬件上](#0-口径声明哪条数字是哪家的在什么硬件上)
- [1 吞吐对照(单请求与聚合分开读)](#1-吞吐对照单请求与聚合分开读)
- [2 存储账:文件、VRAM、DRAM、SSD](#2-存储账文件vramdramssd)
- [3 KV cache 账:量化让长上下文变成可用品](#3-kv-cache-账量化让长上下文变成可用品)
- [4 延迟解剖:时间花在哪儿](#4-延迟解剖时间花在哪儿)
- [5 缺口清单与 Root 采集包](#5-缺口清单与-root-采集包)
- [6 一页口径总表](#6-一页口径总表)

## 0 口径声明:哪条数字是哪家的、在什么硬件上

| 行 | 执行器 | 硬件 | 数字来源 | 定性 |
|---|---|---|---|---|
| A. Xolotl XQ | Xolotl 原生引擎(单会话) | **1×H800 80GB + 32C + 512GB RAM** | **我方第一手实测**(2026-10-21 单卡验收 + 7 天长服务) | H800 真数 |
| B. 原生 Q2 vLLM 栈(ELVEZ 同配方) | vLLM(TP4EP4 DSpark5) | **4×H800** | **我方第一手实测** | H800 真数,但注意:不是 ELVEZ 文件 |
| C. EXL3 2.875 | vLLM (EXL3 backend) | 4×**RTX PRO 6000 Blackwell 96GB**(作者共享多租户) | 作者卡第一手 | **非 H800**;我方 H800 数已补,见[第 ⑤ 篇](/quant-anatomy-5-exl3-h800-live/) |

必须大声说清的两点:

1. **ELVEZ 的 GGUF 文件本身从未在 H800 上跑过**(Engram 私排 + 引擎不兼容,见系列 ①)。行 B 是"同配方(gate/up IQ2_XXS + down Q2_K)的原生 vLLM 移植栈",硬件上等于告诉你在 H800 上"这条配方族跑得什么样",但它和 ELVEZ 那份 .gguf 是两个容器。
2. **EXL3 的行 C 是作者 Blackwell 实测,不是 H800**。我方 H800 EXL3 服务 benchmark 目前 = 冻结完成、GPU 排队中。凡是"EXL3 on H800"的数字本文给不出,给出的是 per-card 算术,并标注。

## 1 吞吐对照(单请求与聚合分开读)

**行 A · Xolotl XQ(我方 1×H800)**:

```
加载            冷 156.7s / 热 55.9s(arena 320GiB pin,seed 82.8s)
fresh prefill   532.8 → 566.6 tok/s(6,649 token prompt)
server decode   47.0 – 60.7 tok/s(单请求)
DSpark          2.87 – 4.07 tok/pass
7 天长服务      sustained 39.5 tok/s 级,expert-cache 命中 94.3–97.8%,restarts=0
协议            kv-fp4,ctx 524,288,prompt-batch 12,288,单会话
```

**行 B · 原生 Q2 vLLM(我方 4×H800 TP4EP4 DSpark5)**,协议:MATH 前 64 题、固定 128 输出、实际输入 52–383 token、server 上限 64:

| 并发 | 聚合 tok/s | TTFT | TPOT |
|---|---|---|---|
| C1 | 39.01 | 0.176s | 24.45ms |
| C8 | 265.72 | — | — |
| C16 | 482.43 | — | — |
| C32 | 825.89 | — | 48.49ms |
| C256(压测) | — | 16.7s | — |

另有 M512 短 A/B window 吞吐候选(baseline ≈445 → 候选 ≈666/676)已封存,待复核定案后另文。

**行 C · EXL3 2.875(作者 4×Blackwell 96GB,共享)**,聊天聚合 tok/s:

| 并发 | 聚合 tok/s | 首内容 p50 |
|---|---|---|
| C1 | 125.861(124.48–126.66) | 0.408s |
| 中档 | 205.51 / 308.74 / 338.38 | — |
| C16 | 423.110(420.78–425.61) | — |
| C32 | 452.16 | 2.499s |

**怎么读**:

- 单请求对照,A 47–61 tok/s vs C 的 C1 125.86:A 是**单会话引擎**,一个请求独占一台 C 侧 hardware 的 1/4;A 的目标是"一张卡全载荷不破 47 tok/s",C 的目标是"四卡高聚合"。这不是一个赛道的快慢,是两种产品形态。
- **聚合 vs 单请求**必须分开:行 B 的 C32 825.89 是 32 路聚合,除回去 ≈26 tok/s/请求;行 C 的 C32 452.16 除回去 ≈14 tok/s/请求。Blackwell vs H800 + 堆栈不同,别横向绝对比,要的是**量级与形状**(怎么随并发增长、TTFT 怎么抬)。
- A 的 prefill 533–567 tok/s 在 1 卡口径下是独一档——因为它把投递拆到"直接传 552B 的 quant 化专家"而不是重构 dense(对照第 ③ 篇 §6 的延迟解剖:dense 36.36ms vs tier 23.56ms)。

## 2 存储账:文件、VRAM、DRAM、SSD

| 项 | A. Xolotl XQ | B. 原生 Q2 vLLM | C. EXL3 2.875(作者件) |
|---|---|---|---|
| 主件体积 | 151.8 GiB(162,957,934,592 B,September 解剖) | ~142.4 GiB experts + 堆栈元数据 | **417.56 GB** 全件 |
| DSpark | 5.66 GB(2.91GB 上卡) | 同栈 DSpark5 | 同栈 DSpark5 |
| Engram | 2×101.4 GB(NVMe 按需行取,extract 132+148s) | 依部署 | 作者:**Engram 常驻 disk** |
| VRAM 实测 | **81,079 MiB**(81 GB 级,Q6_K 5.86 + DSpark 2.91 + KV NVFP4 + prestage 1.5 + 热专家 + 工作区) | 快照缺(GAP) | —(非 H800) |
| VRAM 算术 | — | experts 142.38 GiB ÷ EP4 = **35.60 GiB/卡** | experts ≈195.3 GB ÷ EP4 = **48.8 GB/卡** |
| DRAM | arena 320 GiB pin(15360 专家件全驻) | —(堆栈沿用标准 vLLM) | (作者未给) |
| SSD | Engram + 冷备份 | — | 作者 Engram 磁盘方案 |

一点直观:三条线对"专家放哪"的答案是三种:

- A:RAM 锁页 arena(320GiB)+ 热件 VRAM —— 单卡方案
- B:每卡 35.6 GiB 摊开 —— 4 卡方案
- C:作者选择上卡 portions + Engram 盘 —— 4 卡大显存方案(96GB/卡)

## 3 KV cache 账:量化让长上下文变成可用品

行 C 作者同套件一手对照(强调:**同一套硬件**下,bpw 差 0.625,KV 容量差近一倍):

| 件 | 总大小 | KV 容量 |
|---|---|---|
| Native(官方 FP8/MXFP4) | 510.30 GB | 4.53M tok |
| NVFP4 | 527.29 GB | 1.57M tok |
| **EXL3 2.875** | **417.56 GB** | **12.78M tok** |
| EXL3 3.5bpw | 460.03 GB | 7.41M tok |

EXL3 3.5 bpw 比 2.875 bpw 宽,但同硬件 context 反而窄——因为显存直接限 KV 池。**这就是这代模型量化的第二账:不只剩参数小,是把显存还给 KV**。

我方行 A 的 KV 池:NVFP4(indexer MXFP4),ctx 524,288,落在 81 GB VRAM 的一块;字节拆分未单独测量 → GAP。

这条账给我们的后续工作流(AutoRound 路线)一个明确验收指标:**不要只报 bpw 和 PPL,KV 池体积上限和 TTFT 也要报**——这对产品管线的意义大于 0.1 bpw 的差。

## 4 延迟解剖:时间花在哪儿

行 A 的 3-pass 实采(66.12ms/pass,这是逐字解剖,不是抽样估计):

```
verify 60.89ms  = dense 36.36 + expert tier 23.56 + logits 0.64
draft   4.84ms  + sample 0.31ms
```

——expert tier 23.56ms(35%)就是在§2 说的"VRAM↔RAM 搬运"开销;dense 36.36ms(55%)是稠密件 GEMM。对照第 ② 篇讲的事实(EXL3 ≥144 行要 dense 重构再 GEMM),两条线大头在完全相反的位置——这决定了你接下来 move 先动哪头:A 类优化专家搬运(命中率 94.3–97.8% 已够了,这是 CMS 该干的事),B/C 类优化 GEMM/trellis 解码。

行 B 的 TTFT 随队深(C1 0.176s → C256 16.7s)是 prefill 排队资源面压到极限的曲线;行 C 的首内容 p50 0.408s——量级资源面松。两行的推断原则是:看TTFT不如看每路 prefill/decode 的各自 tok/s。

## 5 缺口清单与 Root 采集包

这条列表如数奉行者交给 GPU 负责方(Root 是唯一 GPU 作业提交人,原则同上):

| 缺 | 补法 | 优先级 |
|---|---|---|
| EXL3 我方 H800 C1/C8/C16 服务 benchmark | ~~冻结包已备,等 4×H800 时值~~(已补:C1/C4/C16/C32/C64 五档实测,见[第 ⑤ 篇](/quant-anatomy-5-exl3-h800-live/)) | ✅ |
| vLLM 原生 Q2 栈 per-card 运行时 VRAM 快照 | 1 次 nvidia-smi + KV pool dump | 高 |
| Xolotl H800 自跑 PPL/任务子集 | 1 次 ppl_eval + 短任务可复链 | 高 |
| Xolotl 与 vLLM TP8 长 A/B | 同 stage 2× 4 卡对开 | 中 |
| ELVEZ GGUF 文件在 H800 的可跑态 | 结构性问题(GGUF 私排),**非采集可解**——文内只提供同配方原生栈锚 | 不行动 |
| 多并发 Xolotl | 引擎设计单会话,**不当并发引擎测** | 不行动 |
| 功耗/kW·tok | 与上面各包并采 | 低 |

## 6 一页口径总表

> 下次只要引用一张,请挑这张:

| 模型 | 平均 bpw(专家口径) | 执行器 | 硬件 | 单请求 tok/s | 聚合 tok/s | 显存 | 备注 |
|---|---|---|---|---|---|---|---|
| ELVEZ GGUF | 2.06(g/u)+2.625(down) | ixv-server(Metal) | M3 Ultra(卡面) | 47.14(M3 实测) | — | — | **H800 无态**;同配方等价 = 下一行 |
| 原生 Q2 vLLM | 2.06/2.625 同配方 | vLLM TP4EP4 DSpark5 | **4×H800** | 39.0 (C1,聚合=单请求) | 825.9 (C32) | 快照 GAP;payload/卡 35.6 GiB 算术 | 我方实测 |
| EXL3 2.875 | 2.875(expert mean) | vLLM EXL3 backend | 4×Blackwell 96GB(作者) | 125.86 (C1) | 452.16 (C32) | —(非 H800);experts/卡 48.8 GB 算术 | 作者数;我方 H800 实测见[第 ⑤ 篇](/quant-anatomy-5-exl3-h800-live/)(C1 156.81 / C32 695.27) |
| Xolotl XQ | 2.25(September 包测);2.093(1017 V2 卡) | Xolotl 原生引擎(单会话) | **1×H800 + 512GB RAM** | 47.0–60.7 decode;533–567 prefill | N/A(单会话设计) | **81,079 MiB 实测** | 我方实测;7 天长服务 run 过 |

## 参考与来源

- 作者侧第一手:[ELVEZ Q2 卡](https://huggingface.co/Elvez)、[LibertAI/Infatoshi EXL3 2.875 件+benchmark](https://huggingface.co/Infatoshi)、[Xolotl XQ pipeline](https://huggingface.co/IndrasMirror)
- 我方第一手:Xolotl 单 H800 全载荷验收/七天服务、原生 Q2 栈 4×H800 并发压测、EXL3 CPU 装配链双段验收 + kernel 级一层抽样——均为本团队只读取证产物,集群标识不写入此文
- 前文:[第 ① 篇 ELVEZ GGUF](/quant-anatomy-1-elvez-gguf/)、[第 ② 篇 EXL3](/quant-anatomy-2-exl3/)、[第 ③ 篇 Xolotl XQ](/quant-anatomy-3-xolotl-xq/);后续:[第 ⑤ 篇 EXL3 的 4×H800 五档实测](/quant-anatomy-5-exl3-h800-live/)
