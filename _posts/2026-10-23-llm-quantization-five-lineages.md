---
layout: post
title:  "LLM 量化五年血统图:从 GPTQ 到 QTIP,再到 INT4 原生训练(2022→2026)"
date:   2026-10-23 00:00:00 +0800
categories: llm quantization
---

> 一句话总纲:五年里 LLM 量化不是在比"谁的 bit 低",而是在五条血统线的接力——
> **块标量补偿线(GPTQ 系)、向量码本线(QuIP→QTIP 系)、激活匀衡/旋转线(SmoothQuant→QuaRot 系)、硬件块浮点线(int8→NVFP4)、原生低比特训练线(BitNet→Kimi-K2)**。
> 你手上的 Q2_K / IQ2_XXS / EXL3 / vLLM-FP8,各自挂在这棵树的不同枝上。

## 目录

- [0 问题:为什么要给 LLM 降比特](#0-问题为什么要给-llm-降比特)
- [1 总览:五条血统线](#1-总览五条血统线)
- [2 第一世代 2022-2023:地基期,敌人是 outlier](#2-第一世代-2022-2023地基期敌人是-outlier)
- [3 第二世代 2024:格子战争](#3-第二世代-2024格子战争)
- [4 第三世代 2025-2026:FP4 硬件纪元与原生低比特](#4-第三世代-2025-2026fp4-硬件纪元与原生低比特)
- [5 家谱鉴定:你手上工具的亲爹是谁](#5-家谱鉴定你手上工具的亲爹是谁)
- [6 七个必须懂的思想(纯文本图解)](#6-七个必须懂的思想纯文本图解)
- [7 2026-10 主流座次](#7-2026-10-主流座次)
- [8 论文总表](#8-论文总表)
- [9 观点](#9-观点)
- [10 参考与链接](#10-参考与链接)

## 0 问题:为什么要给 LLM 降比特

LLM 推理 decode 阶段是 memory-bound:每生成一个 token,要把全部权重从显存搬进计算单元一遍。权重的 bit 数几乎线性决定 decode 速度、单卡能否装下模型、以及同卡并发 batch 上限(V800)。

五年里所有论文绕四个问题转,读懂这四个问题就不会迷路:

- **Q1 压什么**:只压权重(W4A16,省访存)还是连激活也压(W4A4,省算力),KV cache 压不压
- **Q2 格子怎么选**:标量等距格(Round-To-Nearest)、非均匀码本(kmeans 学习型)、高维格子(E8/Leech lattice)、还是状态机驱动的隐式格子(TCQ trellis)——**这是 Q2_K 与 EXL3 分家的根本点**
- **Q3 误差怎么救**:补偿法(把误差摊给未量化的列,GPTQ)、重整法(先缩放/旋转把权重变均匀,SmoothQuant→QuaRot)、训练法(QAT,让网络自己适应低比特)
- **Q4 隐藏 BOSS:kernel**。论文 lossless 不等于能部署,五年里死在没有真 kernel 上的 "SOTA" 至少一打(QuIP# 是最著名的例子)

## 1 总览:五条血统线

```
A. 块标量/补偿线     GPTQ(2023-03) → SpQR → AWQ → GPTAQ(2025-04) → GPTQ=Babai(2025-07)
                     └ 工程化:AutoGPTQ / Q2_K + imatrix / Marlin kernel / llm-compressor
B. 向量码本线        SqueezeLLM(2023-06) → QuIP(2023-08) → QuIP#(E8,2024-02)
                     → AQLM(2024-02) → QTIP(TCQ,2024-06) → VPTQ(2024-09)
                     → 2026 大爆炸:XOR-Trellis / CurveTQ / Tetra / BCJR-QAT / pingala8 进 GGUF
                     └ 工程化:IQ2_XXS(E8 离线查表) / EXL3(QTIP 直系) / VPTQ-kernel
C. 激活匀衡/旋转线   SmoothQuant(2022-11) → AWQ-scale → QuaRot(2024-04) → SpinQuant(2024-05)
                     → DuQuant / FlatQuant(2024) → WUSH / ParoQuant / OffQ(2025-11→2026)
D. 硬件块浮点线      int8(2022) → FP8 E4M3 块缩放(2023-) → OCP MX 格式 → MXFP4(2025)
                     → NVFP4(Blackwell 原生,2025) → Disaggregated Quantization(2026-09)
E. 原生低比特训练    BitNet b1.58(2024-02) → bitnet.cpp(2025) → gpt-oss MXFP4(2025-08)
                     → Kimi-K2-Thinking INT4 QAT(2025-11) → TRACE(RL FP4-QAT,2026-10)
```

## 2 第一世代 2022-2023:地基期,敌人是 outlier

### 【2022-08】LLM.int8()(arXiv 2208.07339,Dettmers 等,NeurIPS 2022)

- **发现**:大模型激活里有系统性离群维(outlier features),不到 0.1% 的通道幅度比其余通道大 20 倍;直接 int8 全量化会崩,崩的就是这几个通道
- **解法**:混合精度分解——outlier 维走 fp16 小 GEMM,其余 99.9% 走 int8 大 GEMM,相加合并
- **地位**:它不是压缩法(内存没省),但给全领域立下第一公理:**outlier 是量化的大敌**。后面五年所有人都在打这只怪
- 遗产:bitsandbytes `load_in_8bit`

### 【2022-11】SmoothQuant(arXiv 2211.10438,韩松组,ICML 2023)

- **观察**:权重分布平坦好量化、激活有 outlier 难量化——难度不对称
- **解法**:数学等价变换把激活的难度匀给权重:`Y = X·W = (X·diag(s)^-1) · (diag(s)·W)`,matmul 结果不变,两边都变得好量化
- **效果**:W8A8 首次近乎无损
- **地位**:C 线祖宗。对角缩放是"最简单的正交变换",2024 年 QuaRot 把它升级成 Hadamard 旋转就是同一个公式的一般化。今天 vLLM/SGLang 里 W8A8/FP8 的缩放哲学,八成还是它的子孙

### 【2023-03】GPTQ(arXiv 2210.17323,Frantar/Alistarh,ICLR 2023 Spotlight)★

- **谱系**:LeCun 1990 Optimal Brain Damage → Hassibi 1993 Optimal Brain Surgeon(删一个权重、用 Hessian 逆补偿其余)→ GPTQ 把"删"改成"量化",并解决效率
- **核心做法(纯文本)**:逐列处理。量化第 j 列产生误差 err_j,立刻用 `W[:,j+1:] -= err_j * Hinv[j,j+1:] / Hinv[j,j]` 把误差摊分到右侧所有未量化列;Hessian 逆用 Cholesky 一次分解,列内 lazy batch 更新。175B 模型 4 小时压完
- **地位**:A 线开宗族长。AutoGPTQ、Q2_K 的误差控制范式、Marlin kernel、llm-compressor 全部挂在它名下
- **局限**:格子仍是标量四舍五入——2 bit 标量格只有 4 个点,必死。这是第二世代的起点

### 【2023-06】SpQR(arXiv 2306.03078,Dettmers 组)

- **发现**:3-4 bit 崩不是均匀崩,是极少数敏感权重贡献绝大多数误差
- **解法**:约 0.3% 敏感权重抽出来 fp16 稀疏存;其余 3 bit 分组量化;scale/zero 本身再量化一次(**bi-level quantization**)
- **地位**:"敏感成分单独高精存"第一枪 + scale-of-scale 思想——**Q2_K 的 superblock 双重量化就是它**

### 【2023-06】AWQ(arXiv 2306.00978,韩松组,MLSys 2024 Best Paper)

- **修正直觉**:"幅度大的权重重要"是错的;**对着大激活的权重才重要**。按激活幅度挑 1% salient 通道就能保大半误差
- **解法**:不做稀疏存储,对 salient 通道做逐通道 scale(SmoothQuant 局部版)
- **地位**:C 线骤变成可部署形态。AutoAWQ、Qwen 官方 -AWQ 包、vLLM AWQ-Marlin 都是它。llama.cpp 的 **imatrix(按激活二阶矩加权误差)是它的工程兄弟**

### 【2023-06】SqueezeLLM(arXiv 2306.07629,UCLA/UCB,ICML 2024)

- 想法复古:为什么量化点要等间距?**kmeans 聚类权重出非均匀码本**,3 bit 近无损
- **地位**:B 线先声(代码本思想 GOBO 2020 / nuQmm 2022 就有,但 LLM 时代第一次好用)
- **局限**:码本按权重密度聚类,没感知激活——敏感权重被分到了烂码点。QuIP 来修

### 【2023-08】QuIP(arXiv 2307.13304,Cornell RelaxML,NeurIPS 2023)★

- **理论核心**:量化误差由权重的 Hessian 决定、Hessian 的"相干性"(incoherence,对角占优程度)决定标量量化能不能活
- **解法**:incoherence processing——用随机正交阵把权重打散 `W' = U·W·V^T`,权重近似高斯白噪声后,简单舍入(LDLQ,用 LDL 分解替代 Hessian 逆)就能逼近无损
- **地位**:一颗种子开两朵花——B 线(向量量化派)和 C 线(W4A4 旋转派)共同的爷爷。EXL3 的 Hadamard、QuaRot 的旋转,源头都是这篇

### 【2023-06 起】工程双子星:k-quants 与 EXL2(非论文,但决定你今天用什么)

- **k-quants**(ikawrakow,llama.cpp PR #1684):Q2_K..Q8_K。256 权重拆 superblock 再拆 8 个 sub-block,每层 scale/min 用 6-8 bit 再量化(SpQR 的 scale-of-scale 工程版)。Q2_K 平均 2.125-2.625 bpw
- **EXL2**(turboderp,2023-11):每个 group 可选 2-8 bit,一次 measurement pass 量各层误差后按总比特预算贪心分配——A 线 + SpQR 混合精度思想的可调容器
- 这两个格式在当时把 GPTQ 的理论压到了消费级单卡能跑的形态

## 3 第二世代 2024:格子战争

2024 年三条线同时爆发:B 线四连发(QuIP# / AQLM / QTIP / VPTQ)争夺"2 bit 用什么格子",C 线武装升级成"旋转派"打通 W4A4,E 线 BitNet 第一枪。加上 llama.cpp / ExLlama 工程吸收——你今天用的每个格式,源头都在这一年。

### 3.1 B 线四连发

#### 【2024-02】QuIP#(arXiv 2402.04396,RelaxML,ICML 2024)★

- **核心**:E8 格子码本。8 维空间最密球堆积 E8 lattice 取 256 个格点 → 8 个权重共享 8 bit = 每权重 2 bit,但"球覆盖"远好于 4 点标量格
- **配套**:Randomized Hadamard Transform(RHT)做 incoherence processing,把 QuIP 的 Kronecker 构造换成蝴蝶形 Hadamard
- **成绩**:2 bit 理论上首次接近无损
- **教训**:**论文 lossless ≠ 能部署**。E8 在线查表 decode 太慢,生态没接住,QuIP# 成了学术赢家+工程输家
- **遗产**:llama.cpp 的 **IQ2_XXS 把 E8 码本离线展开成查表格式**运行——学术成果以工程化形态活下来

#### 【2024-02】AQLM(arXiv 2401.06118,Yandex/HSE,ICML 2024)

- **另一条 VQ 路线**:加性量化(Additive Quantization)。8 维一组,不查一个 256 点格子,而是 M 个码本(各 65536 码字、16 bit 索引),向量 = M 个码字之和
- **码本是学出来的**(对校准数据最小化块输出误差,beam-search + 块级微调),不是手挑的格子
- **对局**:AQLM vs QuIP# = **学码本 vs 用固定好格子**。后续 PV-Tuning(2024-05)把"调好码本/表征"推广成通用框架

#### 【2024-06】QTIP(arXiv 2406.11235,RelaxML,NeurIPS 2024 Spotlight)★ 本文主角

- **问题**:QuIP# 质量够但 kernel 慢;8 维格的信息利用也到顶了
- **核心发明**:TCQ(Trellis Coded Quantization)——把 1992 年 Ungerboeck 的通信编码思想搬来量化权重:
  - 每个 weight 仍只占 2 bit,但 2 bit 不再是"4 个点选 1 个",**是驱动一个 256 状态状态机(trellis)往前走一步**
  - 量化解码 = 用 Viterbi 在状态机里找累计误差最小的路径;**等效码本 = 所有合法长程路径的集合**——维度 100+、隐式码本大到不存在,显存里却依旧每权重 2 bit
  - 大白话:QuIP# 是"8 个 weight 查一次共享码本",QTIP 是"上百个 weight 拼成一整句密码,用状态机倒推原值"
- **硬件设计**:bitshift trellis——状态转移就是移位+查小表(或完全无表纯计算),1 个 kernel 内嵌解量化 GEMV;论文给出"纯查表 ↔ 纯计算"的三档变体让硬件自选
- **成绩**:2 bit 质量与真实 kernel 速度同时 SOTA——量化论文史上罕见两开花
- **遗产**:**EXL3 = QTIP 直系工程后代**(ExLlamaV3 README 原话:"a streamlined variant of QTIP")

#### 【2024-09】VPTQ(arXiv 2409.17066,微软)

- AQLM"学码本"思想 + 二阶 Hessian:centroid 按块输出误差闭式迭代更新,不靠随机梯度
- 2 bit 质量追平甚至局部超过 QTIP,有 vLLM kernel——**QTIP 同期最强对手**,最终市场选了 QTIP 一脉

### 3.2 工程吸收:i-quants / imatrix(2023-12→2024-03)★ 社区线

- **i-quants**(ikawrakow):IQ2_XXS(2.06 bpw)、IQ1_S(1.56 bpw)、IQ3_XXS、IQ4_NL——**QuIP# 的 E8 格子离线展开、运行期纯查表**,代码注释明确引 QuIP#
- **imatrix**(2024-03 merge):拿语料跑一遍统计各层激活二阶矩生成 imatrix 数据文件,量化误差按它加权 —— **AWQ 思想通用化到全部 gguf 格式**
- 结论:**IQ2_XXS 的学名 = QuIP#(E8 格子)× SpQR(bi-level)× AWQ(imatrix 加权)三合一工程优化**,不是某一论文的独生子

### 3.3 C 线:旋转派打通 W4A4

#### 【2024-04】QuaRot(arXiv 2404.00456,IST-DASLab,NeurIPS 2024)

- **换敌人**:访存省了,算力也要省——激活也得 4 bit,但激活的 outlier 比权重更野
- **核心**:computational invariance。RMSNorm 前乘旋转 R、后乘 R^T 消掉,数学上网络不变;**Weights、激活、Attention、KV cache 四处全部插入 Hadamard 旋转**,QuIP 的 incoherence 在全网均匀生效;随后 GPTQ 一压,四者 4 bit 全活
- **地位**:LLM.int8() 发现的 outlier 在这里被根治(旋转移除,不再混合精度分流)。**W4A4KV4 从这篇开始算"被解决"**

#### 【2024-05】SpinQuant(arXiv 2405.16406,Meta,ICLR 2025)

- Hadamard 是手挑的固定旋转——**让它学**:Cayley 参数化保正交性,随机梯度优化 4 组旋转矩阵,比 QuaRot 再降一截 loss
- 学好的 R 离线烧进权重,运行期零代价 → 成 2025-2026 NVFP4 PTQ 的标配前置

#### 【2024-06→10】DuQuant(arXiv 2406.01721)/ FlatQuant(arXiv 2410.09426)

- DuQuant:旋转 + 通道置换双管齐下打散 outlier
- FlatQuant:每个线性层各学自己的仿射变换(旋转+逐通道 scale+shift)再折叠回前层权重——"平台化"权重再量化
- 信号:**到 2024 年底,W4A4 精度问题基本被旋转派收官,瓶颈转向 kernel 与硬件**

### 3.4 kernel 追兵与 E 线第一枪

- **Marlin**(arXiv 2408.11743,IST-DASLab):GPTQ 4-bit 的 A100 GEMM 逼近理论加速比;**Machete/Ladder**(Neural Magic,2024-10)把混合精度 GEMM 带上 Hopper——论文界的"kernel 证明义务"由此成为行规
- **BitNet b1.58**(arXiv 2402.17764,微软亚研):从零训练权重 {-1,0,+1} 的 LLM,absmean 三值化 + STE 估计梯度,3B 打平同尺寸 LLaMA——E 线开宗
- **BitNet a4.8**(2024-10):激活 4.8 bit + 3bit KV,延续原生路线
- **EfficientQAT**(arXiv 2407.11062):PTQ 初值 + 轻量 QAT 反传,打通两域的"性价比款"

## 4 第三世代 2025-2026:FP4 硬件纪元与原生低比特

重大转变:量化的主战场从"算法"迁移到"硬件格式 + 出厂训练"。

### 4.1 D 线成为主角:块浮点烧进硬件

- **【2025】NVFP4 原生进 Blackwell**(B200/GB200/GB300 第五代 Tensor Core):每个权重 4 bit(E2M1,16 个码点)+ 每 16 个元素共享一个 FP8(E4M3)块 scale + 一个 fp32 全局 scale。两阶缩放解决"4 bit 只有 16 格"的范围灾难——**这正是 SpQR bi-level 思想被烧进硅里**
- **【2025】OCP MX 格式铺开**:MXFP4/MXFP6/MXFP8(32 元素共享 e8m0 块 scale);AMD MI355X(2025-06)原生 MX FP4/FP6
- 精密化论文一串:AMXFP4(ACL 2025 Findings,非对称微缩放对付激活 outlier)、Quartet(NeurIPS 2025,原生 FP4 训练性)、ARCQuant(ACL 2026,NVFP4+残差通道)、OSFP4(2026-10,对角平滑+块 scale 联合优化)
- **【2026-09】Disaggregated Quantization**:prefill(算力密集)用 NVFP4、decode(访存密集)用 1-bit——**prefill/decode 用不同精度**成为显式范式

### 4.2 E 线兑现承诺:低比特成为出厂配置

- **【2025-08】gpt-oss-120b/20b**(OpenAI,arXiv 2508.10925):MoE 权重**原生 MXFP4 后训练**,官方评测直接在 MXFP4 下跑,单 H100 可装 120B——顶级实验室第一次把低比特当交付精度
- **【2025-11】Kimi-K2-Thinking**(月之暗面)★:1T 总参/32B 激活 MoE,**expert 权重在 post-training 阶段原生 INT4 QAT**,官方成绩全部在 INT4 下报,生成提速约 2x;走 llm-compressor 的 compressed-tensors 格式,vLLM/SGLang/KTransformers 全支持——PTQ/QAT 之争的量产级裁判
- **BitNet 战线**:bitnet.cpp(2025-04 出 2B-4T、2025-05 官方 GPU kernel、2026-01 CPU 优化、2026-07 首批 1-bit embedding 模型)——技术成立,但 1-bit 仍困在 CPU/edge/embedding 生态位
- **旗舰出厂精度普查**:Qwen3 全系官方 FP8 block-128(arXiv 2505.09388);DeepSeek-V3.2(2025-09)BF16+F8_E4M3 块wise scales;MiniMax-M2(约 2025-10)FP8 E4M3;GLM-4.6(约 2025-10)只发 BF16——**FP8 E4M3 块缩放 = 开源旗舰默认出厂位**

### 4.3 A 线理论反攻:补偿派和格理论合流

- **【2025-04】GPTAQ**:非对称校准——每层拟合**全精度模型**的输出而非被量化污染的输入;约 20 行改动成为"现代 GPTQ"基线
- **【2025-07】GPTQ = Babai 最近平面算法**(IST-DASLab,代码 github.com/IST-DASLab/GPTQ-Babai):证明 GPTQ 的列序补偿**完全等价**于在 Hessian 格子上跑 Babai CVP——**A 线和 B 线在格理论里是同一件事的两种说法**,五年血统在此打结
- **【2026】纵深**:FOEM(2026-03,一阶梯度项)、KronQ(2026-07,Kronecker Hessian,救 70B@2bit)、ReQuant(2026-08,固定格离散精化超越 GPTAQ)

### 4.4 B 线 2026 大爆炸:trellis 家族扩编并反攻 GGUF

> 以下 2026 年论文按 arXiv/发布日期汇总,个别条目未逐篇精读,以标题+方向方式列出。

- **BCJR-QAT**(05):用 BCJR 的 sum-product 松弛替代 Viterbi 硬判决,**trellis 变成可微结构,可以做 QAT**;2 bpw 压过 QTIP-PTQ
- **Tetra**(09-28):**Leech 格子(24 维,比 E8 还稠)**打包成 64 状态 trellis + Golay 码 + 单张 16KiB LUT,serving Qwen3 4B-14B
- **XOR-Trellis**(09-30):免 Hadamard 的 trellis 解量化,超低复杂度 decode
- **CurveTQ**(10-06):免旋转,Hessian 对角 curvature 直接折进 Viterbi 分支度量
- **ApexQuant**(10-06,标量/E8/trellis 三档互换、免校准)、**SAGE**(10-10,能量分层 VQ)、**GSQ**(2026-04,IST,Gumbel-Softmax 标量格逼近 QTIP @2bit)、**OA-EM**(2026-04,发现加性 VQ 的失败主因是初始化而非搜索)
- **共同方向**:去旋转、去查表、可微化、向更大格子(Leech 24D)推进
- **【2026-10-19】pingala8 "Small-State Coset Trellis"**(Zenodo + github.com/Genrius-AI/pingala8-llm)★:8 状态 coset 码 + LDLQ + Hadamard **打进 GGUF 格式本体**;IQ2_XXS 同体积下 Qwen3-4B WikiText-2 ppl **16.64 vs 28.61**——trellis 学术线与 GGUF 工程线**此刻正在合并**,i-quants 的王位第一次遇到格式级挑战

### 4.5 C 线抛光期

WUSH(2025-11,IST,闭式 Hadamard+数据相关块变换)、ParoQuant(2025-11,Givens 旋转,面向推理模型)、HARP(2026-05,双侧可学正交)、ConQuR(2026-05,Procrustes 角对齐)、OffQ(2026-06,PCA 主 outlier 子空间吸收为共享 offset)——W4A4 精度问题已被收官,继续刷 0.0x% ppl 边际收益趋零,战场转移到 NVFP4 精密化。

### 4.6 校准锚:市场为什么停在 FP8/INT4

**"Give Me BF16 or Give Me Death"(ACL 2025)**:受控大样本实验——FP8 ≈ 无损,INT8 微损,INT4 W4A16 小心可用,**sub-4 bit 仍然痛**。这解释了 2026 生产现实的形状:不是 QTIP 不够好,是整个生态(eval、KV cache、attention kernel)还没跟上 sub-4 的权重,所以旗舰停在 FP8,低位推进发生在"原生训练"而不是"事后压缩"。

### 4.7 综述入口

**《Transforms for LLM Quantization: The Great Inversion and Format Co-Design》**(2026-08-25,覆盖约 200 篇):官方承认"补偿 vs 变换"大战重开,格式-硬件协同设计成新纲。

## 5 家谱鉴定:你手上工具的亲爹是谁

| 工具/格式 | 厂家 | 血统配方 | 学术亲爹 |
|---|---|---|---|
| Q2_K / k-quants | llama.cpp | superblock + scale-of-scale + 非对称 min/max(可配 imatrix) | SpQR + GPTQ 时代范式 + AWQ(imatrix);**与 VQ 无血缘** |
| IQ2_XXS / IQ1_S | llama.cpp | E8 格子离线查表 + bi-level + imatrix 必选 | QuIP# + SpQR + AWQ;与 QTIP 是叔侄(同上源 QuIP 的 incoherence,但**无 trellis**) |
| EXL2 | ExLlamaV2 | mixed-bpw group + measurement pass | GPTQ + SpQR + AWQ 的工程合体 |
| EXL3 | ExLlamaV3 | QTIP bitshift trellis 简化变体 + Hadamard | **QTIP 直系**(README 自认 "streamlined variant of QTIP") |
| GPTQ-Int4 W4A16 + Marlin | vLLM/TRT 系 | GPTQ 系补偿 + 4-bit GEMM kernel | GPTQ(A 线) |
| FP8 W8A8(compressed-tensors) | llm-compressor/vLLM | per-tensor/block scale + 硬件 FP8 | SmoothQuant 思想 → D 线 |
| NVFP4 W4A16 | llm-compressor / TensorRT | 块浮点 + Hadamard 前置 + GPTQ 系 observer | QuaRot/SpinQuant + GPTQ 家族 + 硬件格式码 |
| Kimi-K2 INT4 | 月之暗面出厂 | expert 权重训练期 INT4 QAT | BitNet → 工业化 QAT(E 线) |
| gpt-oss MXFP4 | OpenAI 出厂 | MoE MXFP4 后训练 | MX 块浮点 + QAT(D×E) |

## 6 七个必须懂的思想(纯文本图解)

### 6.1 GPTQ:把误差摊给还没量化的列

```
输入: 权重 W, 校准激活的 Hessian H = 2·X·X^T
for j = 1..cols:
    q_j   = round(W[:,j])           # 本列量化
    err_j = (W[:,j] - q_j) / Hinv[j,j]
    W[:,j+1:] -= err_j * Hinv[j, j+1:]   # 误差摊分到右侧列
关键工程: Hinv 用 Cholesky 一次分解; 列内 lazy batch update 避免每列重算
```

直觉:某一列四舍五入亏了,让后面能补偿的列"多走一点"。这就是 Optimal Brain Surgeon 的"删一补万"换成"量一补万"。

### 6.2 incoherence processing:为什么乘个正交阵就合法

对线性层 `Y = X·W`,任取正交矩阵 R(R·R^T = I):

```
Y = X·W = (X·R) · (R^T·W)        # 输出分毫不差
RMSNorm 前后同理可插 (R, R^T)
```

随机 Hadamard/旋转把权重"打散"成近似独立高斯——Hessian 对角占优度(incoherence)下降,**没有一个大方向能带崩标量量化**。QuIP/QuIP#/QTIP 用它打权重,QuaRot/SpinQuant 用它连激活+KV 一起打。

### 6.3 E8 格子:2 bit 的"格子"可以不是 4 个点

2 bit 标量格 = 数轴上 4 个点。8 维空间的 E8 lattice 是已知最密球堆积:256 个格点拼一本码本,8 个权重共享 8 bit。类比:同样预算,**乐高拼 8 块一起买 vs 单块买 8 次**——联合编码的信息密度更高(球覆盖/形状增益)。QuIP# 的 E8 在线查表慢;IQ2_XXS 把它离线展开成整数查表,活了下来。

### 6.4 TCQ trellis:2 bit 不再是"选点",是"走状态机"

```
状态机: 256 个状态; 输入 bit序列; 每 step:
    next_state = shift(left(state, 2) XOR bits)   # bitshift trellis = 移位+异或,硬件免费
    output     = 小表/公式(state, bits)
编码: 对长程 weight 序列跑 Viterbi,找累计重建误差最小的路径
效果: 等效码本 = 所有合法路径集合(维度 100+ 的隐式超格), 存储仍 2 bit/weight
```

Ungerboeck 1992 年的通信编码,被 QTIP 搬来量化;EXL3 是它的工程化身。

### 6.5 QuaRot computational invariance:给全网"灭菌"

利用 RMSNorm 的缩放不变性与线性性,在四对位置插 (R, R^T):FNN1 权重右乘 R、FNN2 左乘 R^T;Attention 的 V/O 同理;K/Q 处在线做 Hadamard(便宜,融合进算子)。权重、激活、KV cache 全部高斯化 → 暗处消杀 outlier → GPTQ 一压 4 bit 全活。

### 6.6 NVFP4 / MXFP4:块浮点 = bi-level 的硅形态

```
NVFP4:  值 = E2M1(4bit, 16码点, ±6) · block_scale(E4M3) · global_scale(fp32)
        block = 16 个连续元素共享一个 E4M3 scale
MXFP4:  块 32 元素, scale 为 e8m0(2 的幂) —— 乘法=指数加法, 免费
```

4 bit 的致命短板是动态范围;块 scale 把"范围"外包给 8 bit,全局 scale 兜底——**SpQR 的 scale-of-scale 从软件思想变成数据通路**。

### 6.7 STE / QAT:低比特怎么参与训练

正向把权重三值化/量化(real value → 最近码点),反向把量化器当恒等映射(直通估计):梯度绕过 round 直接更新底层的 fp 影子权重。BitNet 用 absmean 归一 + STE,Kimi-K2 把 INT4 约束织进 post-training。**PTQ 是"网页发布后截稿",QAT 是"边写边改"**。

## 7 2026-10 主流座次

| 场景 | 事实标准 | 血统 |
|---|---|---|
| 开源旗舰出厂精度 | FP8 E4M3 block-128 W8A8(Qwen3/DeepSeek/MiniMax;GLM 暂 BF16) | SmoothQuant → 硬件块浮点 |
| Blackwell 低位部署 | NVFP4 W4A16(llm-compressor 出包 + Marlin/TRT);iMatrix observer 在部分路径反超 GPTQ | C 旋转派 × GPTQ 系 × 块浮点 |
| Hopper 存量(如 H800) | INT4 W4A16 Marlin(GPTQ/AWQ/GPTAQ) | A 线 |
| 消费级本地 | GGUF Q4_K_M / IQ+imatrix(易);EXL3 2-4 bpw(质)——QTIP 遗产唯一主流落地 | k-quants 工程线 / QTIP 直系 |
| 前沿研究 | trellis 家族(入侵 GGUF 中)、NVFP4 精密化、RL/推理模型时代的 native QAT/FP4 | B/E 线 |
| 已被淘汰 | 纯在线 E8 查表(QuIP#)、没把 kernel 做实的 SOTA 说明书 | 教训同上 |

## 8 论文总表

### 2022-2023 地基期

| 日期 | 论文 | arXiv | 线 | 一句话 |
|---|---|---|---|---|
| 2022-08 | LLM.int8() | 2208.07339 | - | 发现激活 outlier;混合精度分解 |
| 2022-06 | ZeroQuant | 2206.01861 | A前 | 逐层量化 + 知识蒸馏 |
| 2022-11 | SmoothQuant | 2211.10438 | C | 难度匀衡对角缩放,W8A8 可行 |
| 2023-03 | GPTQ | 2210.17323 | A | OBS→逐列补偿,A 线宗 |
| 2023-06 | SpQR | 2306.03078 | A+ | 敏感权重 fp16 稀疏 + bi-level |
| 2023-06 | AWQ | 2306.00978 | C→工程 | 激活挑 salient + scale;imatrix 学术兄弟 |
| 2023-06 | SqueezeLLM | 2306.07629 | B先 | kmeans 非均匀码本,3bit 近无损 |
| 2023-08 | QuIP | 2307.13304 | B,C祖 | incoherence processing;LDLQ |
| 2023-08 | OmniQuant | 2308.13137 | C | 可学 clip/scale |
| 2023-11 | HQQ | - | A旁 | 免校准 half-quadratic |

### 2024 格子战争

| 日期 | 论文 | arXiv | 线 | 一句话 |
|---|---|---|---|---|
| 2024-02 | QuIP# | 2402.04396 | B | E8 格子码本 + RHT;2bit 理论近无损 |
| 2024-02 | AQLM | 2401.06118 | B | 加性量化、学码本 |
| 2024-02 | BitNet b1.58 | 2402.17764 | E | {-1,0,+1} 从零训练,3B 打平 LLaMA |
| 2024-02 | KIVI | 2402.02750 | KV | KV cache 2bit:K 按channel、V 按token |
| 2024-04 | QuaRot | 2404.00456 | C | Hadamard 全网,W4A4KV4 解决 |
| 2024-05 | SpinQuant | 2405.16406 | C | Cayley 学旋转 |
| 2024-06 | QTIP | 2406.11235 | B | TCQ bitshift trellis;EXL3 亲爹 |
| 2024-06 | DuQuant | 2406.01721 | C | 旋转+置换 |
| 2024-07 | EfficientQAT | 2407.11062 | A×E | PTQ 初值 + 轻量 QAT |
| 2024-08 | Marlin | 2408.11743 | 工程 | 4-bit GEMM 近理论加速比 |
| 2024-09 | VPTQ | 2409.17066 | B | 二阶闭式更新码本 |
| 2024-10 | FlatQuant | 2410.09426 | C | 每层仿射变换可折叠 |
| 2024-10 | BitNet a4.8 | 2410.16144 | E | W1.58A4.8 + 3bit KV |

### 2025-2026 硬件纪元(个别 2026 条目未逐篇精读)

| 日期 | 论文/事件 | 线 | 一句话 |
|---|---|---|---|
| 2025-02 | NestQuant | B | Gosset 嵌套格 W/A/KV |
| 2025-04 | GPTAQ | A | 非对称校准,现代 GPTQ 基线 |
| 2025-07 | GPTQ as Babai | A×B | GPTQ ≡ Hessian 格子 Babai CVP |
| 2025-08 | gpt-oss MXFP4 (arXiv 2508.10925) | D×E | MoE 原生 MXFP4 后训练 |
| 2025-11 | Kimi-K2-Thinking INT4 QAT | E | 1T MoE expert 原生 INT4,量产裁判 |
| 2025-11 | WUSH | C | 闭式 Hadamard+数据块变换 |
| 2025-11 | ParoQuant | C | Givens 旋转,面向推理模型 |
| 2025 | AMXFP4 / Quartet / MX+ / LUT Tensor Core | D | 块浮点训练与 serving 精密化 |
| 2026-03 | FOEM | A | 一阶梯度项 |
| 2026-04 | GSQ / OA-EM | B | Gumbel 标量格逼近 QTIP;初始化主导 AQLM 失败 |
| 2026-05 | BCJR-QAT | B×E | sum-product 松弛让 trellis 可微 |
| 2026-05 | HARP / ConQuR / OffQ | C | 学习变换三连 |
| 2026-07 | KronQ | A | Kronecker Hessian 救 70B@2bit |
| 2026-08 | ReQuant | A | 固定格离散精化超 GPTAQ |
| 2026-08 | Great Inversion survey | 全 | 补偿 vs 变转换位大势 |
| 2026-09 | Disaggregated Quantization | D | prefill NVFP4 + decode 1-bit 分相精度 |
| 2026-09 | Tetra | B | Leech 24D 格走 trellis 上 serving |
| 2026-09 | XOR-Trellis | B | 免 Hadamard 解量化 |
| 2026-10 | CurveTQ | B | 免旋转,curvature 进 Viterbi 度量 |
| 2026-10 | ApexQuant / SAGE / TRACE / DuoRate | B/D/E | 免校准弹性;能量分层 VQ;RL FP4-QAT;MoE 双速率 |
| 2026-10-19 | pingala8 coset trellis → GGUF | B×工程 | IQ2_XXS 同体积 ppl 16.64 vs 28.61 |

## 9 观点

1. **两条主线正在合流**:GPTQ=Babai 证明 A/B 线在格理论上同源;trellis 进 GGUF 证明学术格与工程格式同源。未来两年胜负手不是"再压 0.1 bit",是 (a) prefill/decode 分相精度 (b) reasoning/RL 后训练链的原生低比特 (c) consumer 端能否把 trellis 做成 gguf 默认选项
2. **kernel 才是裁判**:QuIP#(无 kernel)死、QTIP(带 kernel)活、EXL3(纯实现)赢。看任何量化新论文,先翻它的 kernel 章节
3. **W4A4 已收官**是好消息:说明这个坑不用再刷;NVFP4 精密化与"出厂精度"才是新坑
4. 如果你在 H800/MI 系服役:**INT4 W4A16 Marlin 是今天的卧铺位,NVFP4 是改签下一班车**;在消费级:EXL3 是你在 QTIP 论文里读到的那个东西的可用形态

## 10 参考与链接

- [QTIP arXiv 2406.11235](https://arxiv.org/abs/2406.11235) · [QuIP# 2402.04396](https://arxiv.org/abs/2402.04396) · [GPTQ 2210.17323](https://arxiv.org/abs/2210.17323) · [QuaRot 2404.00456](https://arxiv.org/abs/2404.00456) · [BitNet 2402.17764](https://arxiv.org/abs/2402.17764) · [gpt-oss 2508.10925](https://arxiv.org/abs/2508.10925)
- [ExLlamaV3(EXL3 = "streamlined variant of QTIP")](https://github.com/turboderp-org/exllamav3) · [llama.cpp](https://github.com/ggerganov/llama.cpp) · [vllm-project/llm-compressor](https://github.com/vllm-project/llm-compressor)
- [vLLM quantization docs](https://docs.vllm.ai/en/latest/features/quantization/)
- [Kimi-K2-Thinking](https://huggingface.co/moonshotai/Kimi-K2-Thinking) · [gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) · [Qwen3-235B-A22B-FP8](https://huggingface.co/Qwen/Qwen3-235B-A22B-FP8) · [DeepSeek-V3.2-Exp](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp) · [MiniMax-M2](https://huggingface.co/MiniMaxAI/MiniMax-M2) · [GLM-4.6](https://huggingface.co/zai-org/GLM-4.6)
- [microsoft/BitNet(bitnet.cpp)](https://github.com/microsoft/BitNet) · [Genrius-AI/pingala8-llm](https://github.com/Genrius-AI/pingala8-llm) · [IST-DASLab/GPTQ-Babai](https://github.com/IST-DASLab/GPTQ-Babai)

> 写作说明:血统鉴定(EXL3/QTIP、IQ2_XXS/QuIP#)据官方 README/代码注释;2025 后生产事实(vLLM/llm-compressor/模型卡)以官方库与 HuggingFace 模型卡为准;2026 年新论文清单按 arXiv 日期汇总,个别条目未精读,已在文中标注。日期与 arXiv 号如有勘误欢迎 PR。
