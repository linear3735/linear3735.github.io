---
layout: post
title: "量化解剖 ③:Xolotl XQ — 三次投影组格式的字节账、RCO-lite 分配、与单卡 H800 全载荷实测"
date: 2026-10-24 00:00:00 +0800
categories: llm quantization deepseek
---

> "量化解剖"系列第 3 篇,拆三个基线里制作最重、单卡表现最独特的一条:Xolotl XQ。本篇三个承诺不变:数字给出处,算术注明算术,实测注明实测,集群标识不出现,不用 LaTeX。

## 目录

- [1 先勘名:XQ-A 是什么和 XQ-R 还没发布](#1-先勘名xq-a-是什么和-xq-r-还没发布)
- [2 三种投影组格式:张量级的字节账](#2-三种投影组格式张量级的字节账)
- [3 量化过程七步(源码锚点级)](#3-量化过程七步源码锚点级)
- [4 实测分配地图:September 主包的张量字典](#4-实测分配地图september-主包的张量字典)
- [5 服务链:三级存储与精确路由](#5-服务链三级存储与精确路由)
- [6 单张 H800 的全载荷实测](#6-单张-h800-的全载荷实测)
- [7 质量口径与缺口](#7-质量口径与缺口)

## 1 先勘名:XQ-A 是什么和 XQ-R 还没发布

这是第 ①② 篇也不同的一处纪律:**发布版 = XQ-A = GPTQ + 混合位宽分配(RCO-lite)**,不是 Gumbel-softmax 学码本的 XQ-R。XQ-R 还在开发,作者自己勘正过旧名 GSQ 不准确——本系列只写 XQ-A。

## 2 三种投影组格式:张量级的字节账

XQ-A 给每个 (expert × gate/up|down) 投影组**独立选**三种格式之一(源码锚点 `v41_formats.py:4`):

| 格式 | 权重集合 | 块布局 | bpw(含元数据) | 直觉定位 |
|---|---|---|---|---|
| **PTQ1_0** | {-1, 0, +1}·s(三值) | 128 权重 → 28 bytes(base-3 打包:5 个三值数/byte) | **1.75** | 打到底:大量专家 gate/up 都靠它 |
| **Q2_0** | {-1, 0, +1, +2}·s(四值) | 64 权重 → 18 bytes | **2.25** | 中间:2-bit 级带 4 电平 |
| **Q3_K** | 3-bit 值 + 分组 scale(K-quant 思想直系) | 256 权重 → 110 bytes | **3.4375** | 最高保障:敏感 down 端 |

字节账自己核一遍(base-3:3^5 = 243 ≤ 256,所以 5 个三值数正好塞 1 字节):

```
PTQ1_0:  128/5×8 + 2×fp16(scale) = 204.8+32 ≈ 标称 28 B → 28/128×8 = 1.75 bpw ✓
Q2_0:    64 × 2bit = 16 B + 2 B scale = 18 B → 18/64×8 = 2.25 bpw ✓
Q3_K:    256 × 3bit = 96 B + 14 B 分组 scale/元数据 = 110 B → 110/256×8 = 3.4375 bpw ✓
```

跟前两篇对照一句:三值/四值**对称中心都是 0**——MoE 专家相当多大权重只是"显著非零的小数",0 电平能精确命中(这一点是 MoE 特有的;另两篇把 0 交给 E8 格或 trellis 规则处理,这里是显式留出)。

## 3 量化过程七步(源码锚点级)

```
1. 起点: 官方 MXFP4 专家解包成 FP32
        (不找回发布前已损失信息,teacher = 源 checkpoint 的参考执行)
2. 按专家真实用途收激活与 Hessian:
        gate/up 用专家输入;
        down 用 clamp+SwiGLU+路由权重后的中间激活   ← v41_calib.py:374
3. scale 多裁剪率搜索,并把理想 scale 吸附到格式能真存的网格
        (FP16 或 Q3_K 子 scale)               ← v41_gptq.py:30
4. GPTQ 逐列补偿: 量化一列,把误差按 Hessian 逆摊到右列  ← v41_gptq.py:83
5. 三格式全试: 每个 (专家 × gate/up|down) 组合量三份,真实比专家输出误差
6. RCO-lite 分配: 拉格朗日 c + λ·B 在总存储预算内二分 + 贪心找边沿,
        护栏: 每层三值比例上限、低覆盖专家不降三值、gu/down 可不同格式  ← v41_alloc.py:30
7. 逐层 sequential: 量化完 L 层,把它的扰动输出喂给 L+1 层继续
        (= GPTAQ 的非对称校准思想)
```

**没有**:Hadamard(走 EXL3 那条路的东西)、outlier 残差分支、adapter、QAT/蒸馏。还有一个负结果:旧 refinement 原型让误差变大,被作者关掉——这是好的工程动作。

## 4 实测分配地图:September 主包的张量字典

**这段很重要**:作者文档里常说"2.093 bpw 与 62.4% 三值占比"是 **1017 V2 版**的卡面数;**实测出张量分配地图的是 September 主包**(GGUF,解剖记录具 anatomy-L14 + allocmap 交叉核对 PASS)。两者必须分清:

September 主包实测解剖(1,337 tensor 全数点过):

| 格式 | 张量字节 | 含件 |
|---|---|---|
| PTQ1_0 | 47.42 GiB | gate/up 三值 + down 三值 |
| Q2_0 | 55.75 GiB | 中等敏感性件 |
| Q3_K | 39.21 GiB | 敏感 down(占大头) + 高赌注件 |
| Q8_0 | 7.07 GiB | 321 个稠密件(加载时再 requant 成 Q6_K 5.86GiB) |
| F16 | 2.01 GiB | 小件 |
| F32 | 0.30 GiB | router 等 |
| **合计** | **151.76 ≈ 151.8 GiB** | 主文件 162,957,934,592 B 闭合 |

实测分配真貌:

- **全局均值 2.25 bpw**(九月件)
- gate/up 三值占比 **46.6%**,down 三值占比 **35.3%**(gu 更接近 ternary 友好形状、down 用 Q3_K 多,符合误差敏感性直觉)
- 1017 V2 卡的口径数字:三值占 **62.4%**、专家均值 **2.093 bpw**、专家预算 132.4GiB;V2 → V3 改了校准/分配,V3 专家区 142.38GiB、主包 ~152GiB

也就是说"Xolotl XQ"不是某个固定 bpw 的格式,**是一个"总预算 + 逐投影组三种可选项的选择器"**——bpw 随分配结果浮。这也是它跟第 ① 篇 ELVEZ"格式固定"与第 ② 篇 EXL3"逐层固定位数"本质区别。

## 5 服务链:三级存储与精确路由

第 ③ 个"一半工程"问题:552B 的一张 expert 卡分三层驻:

```
GPU VRAM     ← 热专家(game:7453 张专家件 + Q6_K 5.86GiB + DSpark 2.91GiB + KV/工作区)
锁页 RAM arena ← 温专家(320GiB pin 后,40×384 全部专家件共 142.4GiB 全驻 RAM)
NVMe SSD      ← 全量备份 + Engram 2×101.4GB(原地提取 132s+148s)
```

路由诚实记录:**精确路由(route-bias 0/0)在 H800+大 RAM 上整段可行**:40×384 全专家 RAM 驻留后,file-level miss=0;bias 与精确臂在噪声内平手,大 prefill 时精确臂反而 **+6.3%**。消费级"64GB RAM 台式机"兜底用 bias 0.5/0.3,对小内存合理,对 H800+512GB 不必继承。

KV 是 fp8/NVFP4:**KV 主体 NVFP4,indexer 持 MXFP4**,落在 81,079MiB 总 VRAM 的池子里(具体 KV 字节拆分未单独记录,是采集包待补项之一),验收时 Engram 始终按需行取。

## 6 单张 H800 的全载荷实测

协议第一手:1×H800 SXM(80GB)+ 32C CPU + 512GB RAM、kv-fp4、ctx 524,288、prompt-batch 12,288、单会话引擎、Engram 按需行取、DSpark 草稿头一并加载。

**加载与驻面**:

```
冷加载         156.7s     (热加载 55.9s)
arena         320 GiB pin(15360 个专家件=40×384 全件 142.4GiB 全驻)
VRAM 81,079 MiB 拆分:
  Q6_K 稠密件   5.86 GiB
  DSpark       2.91 GiB
  KV(pool+运行时) NVFP4(indexer MXFP4),字节拆分未单独记录
  prestage     1.5 GiB
  热专家        7,453 件(字节量见 §5)
  工作区         剩余
seed 专家搬移    82.8s
```

**速度(第一手)**:

```
fresh prefill  532.8 → 566.6 tok/s(单次 6,649 token prompt)
server decode   47.0 – 60.7 tok/s(单请求,随活跃度改)
DSpark         2.87 – 4.07 tok/pass(一次主模验证通过多 token)
```

**延迟解剖(3-pass 实采,66.12ms/pass)**:

```
verify 60.89ms  = dense 36.36 + expert tier 23.56 + logits 0.64
draft  4.84ms   + sample 0.31ms
```

——专家搬运 23.56ms 占总开销 35%,告诉你这个引擎最大的时间花在哪。

**七天服务**:7 天时窗连续服务实测 sustained **≈39.5 tok/s**(单请求、34K-token 级长生成),expert-cache 命中率 **94.3%-97.8%**,restarts=0。这张表的意义不在快,在"40×384 全件 RAM 驻 + 按需行取"的方案**连续七天不重启不 miss 地跑** —— 单卡长服务的可行性证据。

## 7 质量口径与缺口

质量数与极诚实的自标(作者的卡 + 我方验收对开):

- 1017 V2 链 PPL 6.934 vs 同链 teacher 6.572;next-token top-1 = **0.670**(猜中真实下一 token 的准确率,不是与 teacher 的一致率,更不是"保 97.5% 能力")
- 作者承认 1017 V2 首较某些困难任务对照退化(如短 Gauntlet 首轮 2/5);Uncensored 版还叠了 rank-2 refusal-direction 编辑,非纯量化差异
- 我方 H800 这条链**没有自己再跑 PPL/任务分**:H800 我们只验收了"链可行 + 引擎体况"

Root GPU 采集包缺的(终篇对照组用):H800 上的 PPL/任务子集、与 vLLM TP8 配对 A/B、kernel 级 nsys 特写、多并发(此引擎设计单会话,不要当并发引擎测)、功耗。

## 参考与来源

- Xolotl 项目:[huggingface.co/IndrasMirror](https://huggingface.co/IndrasMirror)(XQ pipeline 文档、1017 V2/V3 卡、作者勘名)
- 源码锚点:`v41_formats.py:4`、`v41_calib.py:374`、`v41_gptq.py:30, 83`、`v41_alloc.py:30`
- 加载/benchmark:1017 V2 主包实测解剖(anatomy-L14 + allocmap 交叉核对)
- 单 H800 全载荷:本团队 2026-10-21 单卡验收第一手记录(加载/VRAM/prefill/decode/延迟解剖/7 天服务),集群标识不写入此文
- 综合横评:[本博客 → DSV4.1 三基线](/dsv41-three-quant-baselines/)
