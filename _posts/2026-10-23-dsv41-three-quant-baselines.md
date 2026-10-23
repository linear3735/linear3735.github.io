---
layout: post
title: "实战解剖:DSV4.1-Flash 三条已跑通的 2-bit 量化基线(Q2_XXS / EXL3 / Xolotl XQ)"
date: 2026-10-23 00:00:00 +0800
categories: llm quantization deepseek
---

> 上一篇[《LLM 量化五年血统图》](/llm-quantization-five-lineages/)画了五条学术线。这一篇是实战篇:把一个 552B 混合专家模型(DeepSeek-V4.1-Flash)真正跑在硬件上的**三条已验证 2-bit 级量化方案**拆开——它们各自用了哪些方法、量化过程到底怎么做、产物长什么样、跑起来多快。
>
> 三个方案分别是:ELVEZ 的 **IQ2_XXS+Q2_K GGUF**、LibertAI/Infatoshi 的 **EXL3 2.875bpw**、以及独立引擎 Xolotl 的 **XQ 混合格式**。它们恰好是我手里三个跑通过全链路的验收基线。

## 目录

- [0 三个方案一眼览](#0-三个方案一眼览)
- [1 共同地基:被量化的模型本身](#1-共同地基被量化的模型本身)
- [2 基线 A:ELVEZ Q2(IQ2_XXS+Q2_K+imatrix,GGUF)](#2-基线-aelvez-q2iq2_xxsq2_kimatrixgguf)
- [3 基线 B:EXL3(LibertAI/Infatoshi,trellis 3bit)](#3-基线-bexl3libertaiinfatoshitrellis-3bit)
- [4 基线 C:Xolotl XQ(GPTQ+按需分配位宽)](#4-基线-cxolotl-xqgptq按需分配位宽)
- [5 横评与选型](#5-横评与选型)
- [6 对后续工作流的意义](#6-对后续工作流的意义)
- [7 参考与来源](#7-参考与来源)

## 0 三个方案一眼览

| | A. ELVEZ Q2 | B. EXL3 | C. Xolotl XQ |
|---|---|---|---|
| 作者/出处 | ELVEZ(IXV 日本) | LibertAI 原量化,Infatoshi 再制+对照 | Xolotl 独立项目 |
| 学术血统 | QuIP# E8 + SpQR 双量化 + imatrix | QTIP trellis 直系 | GPTQ 系 + 自研位宽分配(RCO-lite) |
| 专家平均精度 | 2-bit 家族(IQ2_XXS≈2.06bpw) | 2.875 bpw(逐层 2/3 bit 混合) | 2.093 bpw(V2,62.4% 三值) |
| 主包体积 | GGUF 单文件(含自排 Engram) | 分片 safetensors | 主 GGUF ~142-152GiB + Engram 双表 ~189GiB |
| 服务运行时 | IXV 引擎(Metal,M3 Ultra) | vLLM(EXL3 backend) | Xolotl 原生 CUDA 引擎(sm_90) |
| 我们这边的验收 | 格式同族已跑通(H800+SSD streaming 路线) | CPU 装配链今天全段通过 | 单 H800 全载荷:prefill 533-567 / decode 47-61 tok/s |

**三个共同特征值得先记下**:

1. 三者都不是从 BF16 出发,而是从**官方已量化的 checkpoint**(专家 MXFP4 + 稠密 FP8 e4m3/ue8m0 块浮点)**二次量化**——"teacher" 是源 checkpoint 的参考执行,不是无损原模型
2. 三者都只压 **routed experts**。注意力/共享专家/embedding/router 等"小钱"都保留 FP8/Q8 甚至更高——MoE 的账本来就是:1540 亿路由专家参数 vs 其余 ~10 亿稠密参数
3. 三者都承认一个现实:这个量级想落到消费级/单卡,**存储体系(SSD→RAM→VRAM 分层+投机解码)和量化同等重要**

## 1 共同地基:被量化的模型本身

DeepSeek-V4.1-Flash(0909 与 1017 两个 checkpoint;1017 是 2026-10-17 的小更新,语言+视觉权重都变了,旧量化文件不可复用):

- 40 层 × 384 个 routed experts,top-6 路由,hidden 5120,expert inter 2304;MoE 合计 ~552B
- **Engram**:第 2、15 层(0 计 id 1/14)的内嵌 n-gram 哈希大表,两层共 ~203GB(188.8GiB)FP8(E4M3 每行 256 值 + 每 32 值一个 E8M0 scale);每 token 只取 2×24=48 行
- **DSpark**:官方投机解码草稿头,各量化方都配套(ELVEZ 另发 DSpark.gguf,Xolotl 用 Q2_K sidecar 5.66GB,官方 1017 包自带)
- 官方发布形态:专家 MXFP4(e2m1 + ue8m0 块 scale)+ 稠密 FP8 e4m3 块浮点(32×32 块,ue8m0 scale)——也就是说**官方出厂就已经是 D 线块浮点**,三个社区方案都在"已低比特"的底子上再压

## 2 基线 A:ELVEZ Q2(IQ2_XXS+Q2_K+imatrix,GGUF)

### 2.1 方法血统

文件本名 `DeepSeek-V4.1-Flash-1017-IQ2_XXS-Q2_K-imatrix.gguf`——名字即配方:

- **IQ2_XXS**:E8 lattice 码本(256 码字,8 维联合编码,E8 是 8 维最密球堆积)离线展开成查表格式,2.0625 bpw。血统 = QuIP# 的格子被 llama.cpp 工程化(见[上一篇](../llm-quantization-five-lineages/)§3.2)
- **Q2_K**:superblock 分组标量量化(scale-of-scale 双重量化),2.625 bpw 级。血统 = SpQR 的 bi-level 思想
- **imatrix**:用 **8192 token 激活校准**统计各层激活二阶矩,量化误差按重要性加权——AWQ 思想的通用工程化

### 2.2 量化过程(llama.cpp 路线标准三步)

```
第 1 步 校准: 用 8192-token 语料过一遍模型,统计每层 imatrix(激活协方差对角)
第 2 步 量化: llama.cpp quantize 按张量类型套格式
        - 专家 gate/up → IQ2_XXS(E8 查表)
        - 专家 down   → Q2_K(superblock)
        - 稠密小件    → Q4_K/Q6_K/Q8_0 各就其位
第 3 步 打包: Engram 双表按 ELVEZ 自排布局装进同一份 GGUF(注意:不是通用 GGUF!)
```

elvez 卡明确警告:这份 GGUF 的 Engram 布局是自家的,**llama.cpp/Ollama 跑不起来**,只在 IXV 自家引擎(ixv-server,Metal,M3 Ultra)验证过。另发配套 DSpark.gguf(投机头)与 Vision.gguf 编码器。

### 2.3 这条线的意义

- **制作成本最低**:llama.cpp quantize 是纯 PTQ 查表+打包,没有训练式校准,一套流水线 CPU 就能跑
- **部署面最宽**:GGUF 是社区 lingua franca;ds4 式 SSD streaming 让 128GB Mac 成为可能目标
- 与我们自研 Q2 同族:内部 Q2 的专家同样是 **IQ2_XXS gate/up + Q2_K down** 配比——ELVEZ 是这条线的公开参照,我们的 H800 MMQ kernel 是它的 SM90 执行面

## 3 基线 B:EXL3(LibertAI/Infatoshi,trellis 3bit)

### 3.1 方法血统

EXL3 = QTIP 的直系工程产物:[上一篇](../llm-quantization-five-lineages/)已鉴定——bitshift trellis 状态机(每权重几个 bit 是"状态转移指令",Viterbi 找最优路径)+ 前后 Hadamard 打散权重。信息利用是好格子压出来的,不是靠查表。

### 3.2 产物解剖(读真实的 quantization_config)

```
quant_method : exl3,  bits: 3,  codebook: "mul1"
layer_bits   : 0-17=3, 18-22=2, 23-39=3      ← 逐层比特分配!
mtp_experts  : "source", 起始层 40            ← MTP 模块专家不量,沿用源
non_routed   : deepseek_v4_fp8
    fmt=e4m3, activation_scheme=dynamic,
    scale_fmt=ue8m0, weight_block=[32,32]     ← 稠密件保持官方 FP8 块浮点
```

三个值得抄的设计:

1. **逐层比特混合**:`layer_bits` 里 18-22 层用 2-bit、其余 3-bit——ExLlamaV3 的量化脚本按校准测量决定每层给多少 bit,平均 2.875 bpw。这就是上一篇说的 **EXL2 遗传的"总比特预算下贪心分配"**
2. **稠密件不折腾**:attention/embedding 等直接保留官方 deepseek_v4_fp8(e4m3,ue8m0,32×32 块)——官方 FP8 已足够好,重写它只亏不赚
3. **`codebook: "mul1"`**:EXL3 的乘性交融变体,在质量/速度谱系上的一个具体选型

### 3.3 量化过程(ExLlamaV3 标准链)

```
第 1 步 校准捕获: HF 原 ckpt 跑一批校准语料, 逐层抓 Hessian 侧量(measurement)
第 2 步 trellis 编码: 每个权重张量先 Hadamard 旋转,
        再 Viterbi 在 bitshift trellis 上找累计误差最小路径, 编码为每权重 2/3 bit
        (逐层 bit 数按 measurement 的敏感度分配, 总预算 "=" 2.875 bpw)
第 3 步 序列化: trellis 码 + 逐层 scales + chameleon 式 packed 权重 → safetensors 分片
第 4 步 加载时 kernel 内联解码: GEMV 里跑状态机就地复原权重, 不落地 fp16 大矩阵
```

Infatoshi 还做了**社区罕见的四件套实证对照**:同 checkpoint 的 MXFP4(官方)/NVFP4/EXL3-2.875/EXL3-3.5 四份,图比 coding、speed、latency、context。library_name=vllm——**EXL3 在 vLLM 里有原生执行面**,这是三条线里与"今晚就能用 vLLM 服务"距离最短的一条。

### 3.4 我们这条线的现状

另一条我们自己搭的 EXL3 装配链(量化→扩展构建→审计)今天在 CPU 段两半全过:packed 产物 17.46GiB/3921 张量过审计,SM90 扩展编译出 284MiB/112 个 cubin(row_store 复用);下一步是混合装配包,GPU 段等重新授权。教训已记:CPU 链五类坑(无 venv / TMPDIR / Lustre 坏 inode / tar 补丁 / 残留 build 目录)逐个 fail-fast 卡住再修。

## 4 基线 C:Xolotl XQ(GPTQ+按需分配位宽)

> 先勘名:作者已经承认旧名 GSQ 不准确——**发布版是 XQ-A = GPTQ + 混合格式分配**,真正用 Gumbel-softmax 学码本的 XQ-R 还在开发,不要把它的预期收益记到现成产物头上。

### 4.1 三种可选格式(按 projection 组任意组合)

| 格式 | 权重可取值 | 块存储 | 含元数据 bpw |
|---|---|---|---|
| PTQ1_0 | ternary {-1,0,+1}·s(base-3 打包,5 个三值数/byte) | 128 权重 28 bytes | 1.75 |
| Q2_0 | quaternary {-1,0,+1,+2}·s | 64 权重 18 bytes | 2.25 |
| Q3_K | 3-bit 编码 + 分组 scale(K-quant 直系) | 256 权重 110 bytes | 3.4375 |

### 4.2 量化过程的七步(源码锚点级)

```
1. 起点: 官方 MXFP4 专家解包成 FP32(不找回发布前已损失的信息,teacher=源 ckpt 参考执行)
2. 逐专家收激活与 Hessian:
   - gate/up: 用专家输入
   - down:    用 clamp+SwiGLU+路由权重后的中间激活   ← 按专家真实用法加权
3. scale 搜索: 多个裁剪率(必要时两种符号)×H 对角加权误差评估;
   再把理想 scale 吸附到格式能真存的网格(FP16 或 Q3_K 子 scale)——避免"导出掉一次价"
4. GPTQ 逐列补偿: 量化一列,把误差按 Hessian 逆摊分到右侧未量化列(传统艺能)
5. 三格式实测: 每个 (专家 × gate/up|down) 组合各试 PTQ1_0/Q2_0/Q3_K,量真实专家输出误差
6. RCO-lite 分配: 总存储预算下,用拉格朗日 c + λ·B 二分搜索 + 贪心找边沿,
   带护栏(每层 ternary 比例上限、低覆盖专家不降 ternary、gate/up 与 down 可不同格式)
7. 逐层 sequential: 量化完第 L 层,把它的扰动输出喂给第 L+1 层继续拟合
   ——手法等价 GPTAQ 的非对称校准,每层看到的是"已量化前序"的真实输入
最后打包: 主 GGUF 一份(专家用分配出的混合格式,稠密件 Q8_0,加载时再把 321 个 Q8_0 requant 成 Q6_K)
```

1017 V2 实测分配:三值占 62.4%,平均 2.093 bpw,专家预算 132.4GiB,主包约 142GiB;V3 改了校准与分配,专家 142.38GiB、主包 ~152GiB。**没有 Hadamard、没有 outlier 残差分支、没有 adapter,不是 QAT/蒸馏**——质量来自激活感知 + 列补偿 + 按需位宽 + 逐层拟合,旧 refinement 原型甚至让误差变大而被作者关掉。

### 4.3 服务链(这是它能跑起来的另一半)

- 三级存储:GPU 显存(热专家)→ 锁页 RAM arena(温专家)→ NVMe SSD(全量 + Engram);miss 逐级搬,DMA 上传 GPU
- Engram 两表 ~189GiB 常驻 SSD,每 token 48 行 <13KiB 按需取,行去重+排序+4KiB 页合并,~200 万行 RAM cache
- DSpark 投机:草稿侧可更狠量化甚至部分加载,主模型一次验证多 token,摊薄专家搬运
- 默认 route-bias 0.5/0.3(**有损**):偏向显存/RAM 专家,为 ~64GB RAM 台式机兜底

### 4.4 我们的单 H800 验收(2026-10-21)

单张 80GB H800 + 512GB RAM 节点,552B 全 40 层 + Engram + DSpark 全载荷:

- **速度:fresh prefill 533-567 tok/s,decode 47-61 tok/s**(DSpark tokens/pass 2.87-3.66)
- **精确路由(route-bias 0/0)不掉速**,expert 文件层 miss=0;bias 与精确臂在噪声内平手,大 prefill 精确臂反 +6.3%
- arena 320GiB 后专家全驻 RAM+VRAM;分 VRAM 7453 / RAM 15360(142.4GiB)/ SSD 0
- 结论:**bias 是 64GB 小内存的补救,在 H800+大 RAM 上可整段关掉,不必继承消费级有损配置**

### 4.5 诚实的质量口径

- 1017 V2 量化链 PPL 6.934 vs 同链 teacher 6.572;next-token top-1 = 0.670(是"猜中真实下一 token 的准确率",不是与 teacher 的一致率,更不是"保留 97.5% 能力")
- 作者的困难任务对照有退化(短 Gauntlet 1017 V2 首轮 2/5),公开承认 1017 部分任务退化
- Uncensored 版还叠加了 rank-2 refusal-direction edit——不是纯量化差异
- 定位:**把 552B 压到消费机可跑并保住相当一部分任务能力的容量与推理工程;"量化无损"未被证明**

## 5 横评与选型

| 维度 | A. Q2_XXS GGUF | B. EXL3 | C. Xolotl XQ |
|---|---|---|---|
| 制作成本 | 最低(PTQ 查表,无训练) | 中(measurement+Viterbi,GPU 校准) | 最重(逐专家 Hessian+三格式实测+逐层拟合) |
| 平均 bpw | ~2.06-2.6(混)=最低 | 2.875 | 2.093 |
| 格式家族 | GGUF(但 Engram 私排) | safetensors(EXL3 标准) | GGUF 主包+私有 Engram 切片 |
| 开箱服务面 | 窄(IXV 引擎;ds4 类同思路) | **最宽(vLLM 原生)** | 独引擎(单卡/少卡最优) |
| 单卡 H800(80GB) | 需 SSD streaming | 主包更小,理论最宽松(待实测) | **已验收**:全载荷 47-61 tok/s |
| 多并发能力 | 弱 | vLLM 调度栈继承 | 弱(一次一个请求;多卡是 layer-split 非 TP/EP) |
| 质量口径 | ELVEZ 实测如实,无损未证 | 四件套对照最透明 | 如实承认退化,绝不宣无损 |
| 适配新 ckpt | 换底重跑 quantize+imatrix 即可 | 同上,加 measurement | 最重,但流程已模板化(1017 V1→V3) |

**选型一句话**:要"今晚 vLLM 起服务"→ EXL3;要"单卡 552B 完整交互"→ Xolotl;要"最便宜的可复现 2-bit 参照系"→ ELVEZ Q2。

## 6 对后续工作流的意义

- 这三条线是**验收参照系**:任何新 PTQ 工作流(比如我们基于 AutoRound 搭的那套)产出的 Q2,横评就该和这三家比——与 A 比制作成本与格式标准度,与 B 比 vLLM 服务成熟度和逐层分配,与 C 比单卡容量工程与如实口径
- C 的 RCO-lite 与 SignRoundV2 的 AutoScheme 是思想亲属(都按实测输出误差做逐层/逐组比特分配+预算约束)——证明"按需分配"在 552B 上已经赢过均匀分配
- B 的"稠密件保留官方 FP8"与 C 的"稠密件 Q8_0→Q6_K 加载时重压"是两种相反直觉,都有运行证据:值得在我们的方案里各占一臂做对照

## 7 参考与来源

- ELVEZ:[DeepSeek-V4.1-Flash-1017-ELVEZ-Q2](https://huggingface.co/Elvez)(IQ2_XXS+Q2_K,8192-token imatrix,IXV/ixv-server)
- LibertAI / Infatoshi:[EXL3-2.9bpw 原量化](https://huggingface.co/LibertAIDAI)与[Infatoshi 四件套对照](https://huggingface.co/Infatoshi)
- Xolotl:[项目仓库](https://huggingface.co/IndrasMirror)(XQ pipeline 文档与 1017 V2/V3 模型卡)
- 理论背景:[本博客上一条 → LLM 量化五年血统图](/llm-quantization-five-lineages/)
- 内部验收与源码对齐记录均为本团队只读取证产物,未公开引用细节不列入此文

> 写作口径:所有体积/bpw/配置取自公开模型卡与 quantization_config;Xolotl 过程描述锚到其仓库源码,质量段落只搬作者与实测原文数字;性能数字为可复核实测。"无损"之类未证说法一律按证据降级。
