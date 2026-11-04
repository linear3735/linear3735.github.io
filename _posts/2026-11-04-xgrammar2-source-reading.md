---
layout: post
title: "XGrammar-2 精读:五个机制,两份生产代码,和一处把 bit 极性写反的内核"
display_title: XGrammar-2 精读
subtitle: 五个机制，两份生产代码，和一处把 bit 极性写反的内核
description: 以 arXiv:2601.04426 为主线精读 XGrammar-2 的五个机制，逐行对照 vLLM 与 DeepSeek DeepInfer 的真实源码，并定位到一处掩码内核的 bit 极性矛盾。
excerpt: 从 TagDispatch 到重复状态压缩，再把 vLLM 与 DeepInfer 的 xgrammar 集成逐行拆开——最后一处 CUDA 内核把 bit=1 的含义写反了。
date: 2026-11-04 00:00:00 +0800
categories: llm inference structured-generation
tags: [XGrammar, structured-generation, vLLM, DeepInfer, 源码精读]
---

> 这篇是 [arXiv:2601.04426v4](https://arxiv.org/abs/2601.04426)《XGrammar-2: Dynamic and Efficient Structured Generation Engine for Agentic LLMs》(ACM CAIS '26) 的精读笔记:
> 主轴是论文的五个机制(§3.2–§3.6),对照物是两份真实的生产代码——**vLLM 的 xgrammar 后端**(actual-0909 树)与 **DeepSeek 的 DeepInfer**(HEAD `774ce24`)。
> 所有源码结论都落到 `文件:行号`,可以直接打开核对。
>
> 方法承诺同"量化解剖"系列:数字给出处,算术注明是算术,实测注明是实测,推断标注为推断。这次手上只有只读源码副本、没有运行环境,所以凡是需要跑一次才能定的结论,一律写成"待验证",不和已核实的事实混排。
>
> 全篇唯一一处功能性发现:DeepInfer 里给 logits 打掩码的那个 TileLang **CUDA 内核,把"bit=1 表示允许"写成了"bit=0 表示允许"**——加上它依赖的 xgrammar 库,一共 9 处都按"1=允许"写。**这是源码读出来的结论,不是实测结论;判定需要一次实跑。** 第 7 节把验证边界划清楚。

## 目录

- [0 口径声明:这一篇的每个结论是怎么来的](#0-口径声明这一篇的每个结论是怎么来的)
- [1 一句话:XGrammar-2 在解决什么](#1-一句话xgrammar-2-在解决什么)
- [2 五个机制](#2-五个机制)
- [3 论文的数字能信到什么程度](#3-论文的数字能信到什么程度)
- [4 vLLM:一条完整链路上的 14 个锚点](#4-vllm一条完整链路上的-14-个锚点)
- [5 DeepInfer:在 Python 里补上 vLLM 交给库的那一层](#5-deepinfer在-python-里补上-vllm-交给库的那一层)
- [6 两套默认值:缓存上限差 20 倍](#6-两套默认值缓存上限差-20-倍)
- [7 一处把 bit 极性写反的内核](#7-一处把-bit-极性写反的内核)
- [8 局限:我没回答的问题](#8-局限我没回答的问题)
- [9 一页总表](#9-一页总表)

## 0 口径声明:这一篇的每个结论是怎么来的

先把证据分级钉死,再谈内容(系列传统:口径比数字重要)。

- **论文数字**:全部出自 arXiv:2601.04426v4 正文、摘要与 Table 1/3/4/6。凡是引原话,保留英文原文并注明节号。
- **源码结论**:对应两台机器上的**只读副本**,没有修改过任何一行:
  - vLLM:actual-0909 源码树,仓库根就是 `vllm/` 包本身,所以本文里 `v1/structured_output/backend_xgrammar.py` 这种路径是相对该树的。
  - DeepInfer:`774ce244b87cc0eb8d4b94ab9f5de2ab22049f01`(2026-10-20),`deepinfer/` 包在仓库根下。
- **版本**:DeepInfer 的 `requirements.txt:21` 明确钉 `xgrammar==0.2.2`;vLLM 这侧用的是 xgrammar **0.2.3**(本机 uv 缓存里的 `xgrammar-0.2.3.dist-info`),它调用的 `xgr.StructuralTagItem` / `compile_structural_tag`(`backend_xgrammar.py:105`、`:112`)就是这个时期的接口。**0.2.2 与 0.2.3 不是同一个能力集合**,这是第 5 节的起点。
- **没有做的事**:没有下载模型权重,没有跑 GPU 或集群,没有对 DeepInfer 那份副本执行过任何测试。所以第 7 节的矛盾我写成"源码级矛盾",不写成"某一边有 bug"。
- **不用 LaTeX**:公式全部用大白话加数字例子。

## 1 一句话:XGrammar-2 在解决什么

结构化生成的经典假设是"结构在编译期已知、请求内部不变":文法一次编译,全程复用;工具集合在编译期冻结,新增工具就重编译。

agentic 负载把这个假设打破了。论文的原话是,这些结构"在原理上可以用纯 EBNF 编码,但编码会变得笨重且低效"。拆开看,是两种不同的动态:

| 动态类型 | 现实形态 | 论文的解法 |
|---|---|---|
| **请求内动态** | 先自由输出一段文本,命中某个工具名之后才切到该工具的 JSON Schema | TagDispatch(§3.2) |
| **请求间动态** | 一个请求可能带几十到上百个候选工具;不同请求文法不同,但大量共享子结构 | Cross-Grammar Cache(§3.3) |

这两种动态要用不同机制解决,论文的章节划分也是按这条线走的。在此基础上,为了让前面两个机制真的能跑起来,论文又把解析器和缓存重做了一遍:换 Earley 解析器(§3.4)、加 JIT 编译(§3.5)、做重复状态压缩(§3.6)。

前两个解决"动态",后三个解决"执行效率"。这个划分很重要,因为后三个的收益是**有条件的**,第 3 节会看到 JIT 甚至先把一项指标弄慢了 15.9 倍。

## 2 五个机制

### 2.1 TagDispatch(§3.2):把"结构切换"做成文法内建原语

要在一套 EBNF 里同时表达自由文本、识别多个 tag、并把每个 tag 路由到不同子文法,等价于手写一个词法分析器加一个路由器。TagDispatch 把这层从用户态搬进引擎:tag 列表随请求而变,引擎内部用一个 Aho–Corasick 自动机同时跟踪任意多个 tag。

关键细节是**两段式状态**:分派中(dispatching)与已分派(dispatched)。在此之前按自由文本走,命中 tag 之后按对应子文法走,`stop_strs` 决定什么时候退出子文法。这套结构是为"请求内动态"准备的语义原语。

### 2.2 Cross-Grammar Cache(§3.3):跨请求的子结构复用

不同请求的工具集不同,但它们引用的子文法大量重叠,所以 token mask 缓存有得可复用。难点在"怎么判断两个 FSM 的子结构等价"——因为 FSM 之间会互相引用,不能只看自己。

论文的做法是层次化哈希:每个 FSM 的结构哈希 = 自身状态转移结构 + 它引用的所有 FSM 的哈希,自底向上聚合。成环时自底向上不再成立,于是环内先用临时哈希、环外按逆拓扑序迭代求不动点(论文 Algorithm 1)。另外,缓存的 key 不只取决于 FSM 结构,还取决于它被谁引用(XGrammar 的 context expansion 就吃这一点),所以哈希要把引用关系也算进去。最终以 FSM 哈希为 key 查全局缓存池,到上限按 LRU 淘汰。

命中分两档(论文 Figure 4):

| 命中档位 | 条件 | 代价 |
|---|---|---|
| **Perfect hit** | lookahead 断言相同 | 直接复用整份 mask 缓存 |
| **Partial hit** | lookahead 不同 | 只复用大部分,需重算"不确定 token + 原 lookahead 已判定的 token" |

论文的说法是这套方法下"大部分 token mask 缓存都能被复用"。注意 Partial hit 的**重算范围**——这是论文给了定义、但没给占比和最坏情况分析的一处,第 8 节会回到它。

### 2.3 Earley 自适应掩码缓存(§3.4):缓存只建在"可扫描状态"上

XGrammar 用下推自动机(PDA)跟踪输出,把 token 分成 accepted / rejected / context-dependent 三类并缓存。agentic 文法的不确定性更高,同一状态下可能展开的规则数量大得多,后果是 PDA 状态数指数级膨胀,枚举"哪些 token 一定合法"变得不可行。

所以换成 Earley 解析器——它可以在不确定展开下继续推进,代价是不能再假设"状态 = 一小段规则"。但缓存本身没废:**只建在 scannable state 上**,也就是下一个符号是终结符的状态,因为只有这些状态才可能立刻判定 token 是否合法。其余状态留到运行期解析。

这是明确的"用时间换空间",而那部分时间,就由 §3.5 的 JIT 来摊。

### 2.4 JIT 编译(§3.5):把两类开销分别藏进 prefill 和 decode

JIT 做的事很直接:编译期不生成全部 mask 缓存,改成运行期按需生成、再回填缓存池。动机是 agentic 负载里大量文法状态永远不会到达,编译期全算纯属浪费。

论文的说法是两类开销被分别藏起来:编译与 **prefill** 重叠(影响 TTFT),运行时计算与 **decode** 重叠(影响每 token 延迟)。

这个"重叠假设"是后面要追问的点——它是收益成立的前提,而论文没给重叠失败时的退化曲线。

### 2.5 重复状态压缩(§3.6):让长重复结构上的处理时间保持常数

JSON Schema 里的 `MinLength` / `MaxLength` / `MinItems` / `MaxItems` 会展开成重复结构。朴素做法要为每个可能的重复次数建一份 mask 缓存,缓存规模与重复次数成正比。

论文观察到差异只在"还能再接受几个",于是把除尾部之外的状态折叠成一个状态,让重复结构上的处理时间保持常数。论文举的例子是 `String → [^"]{20,1024}`:朴素展开 1005 个状态,压缩后数量级下降。

但论文自己把它定位为**长尾场景**的优化:schema 里没有长重复结构,就看不到那个 99.6×。这一点在引用时经常被漏掉。

### 2.6 五个机制连起来看

§3.4 和 §3.5 必须连起来读:Earley 让状态数可行,JIT 让缓存的代价被摊到 decode 里;然后 §3.3 和 §3.6 再把 mask 生成的代价压回去。单独拿任何一个机制的收益出来说,都会走样——下一节的数据就是证据。

## 3 论文的数字能信到什么程度

### 3.1 四张表、四种硬件:先看清实验设置

论文自己的评价设置是这样的:

| 项目 | 设置 |
|---|---|
| 任务 | agentic function calling:自由文本 + 工具调用交替出现 |
| 数据集 | BFCL-v3(§4.3 端到端);语法任务另设合成集(§4.1–§4.2) |
| 对比基线 | XGrammar v0.1.19 / llguidance v1.2.0 / Outlines v0.2.11 |
| 服务引擎 | SGLang-v0.5.3.post3 |
| batch | 1 / 16 / 128 三档 |

硬件按实验分,这一点最容易被忽略:**mask 生成用 AMD EPYC 9654(单线程);端到端用 RTX 5090 + Xeon 8470Q;准确率用 B200 + Xeon 8570。**

论文里可以直接引用的原话只有这么几句,而且**分属不同的实验**:

| 指标 | 论文原话 / 数字 | 出处 | 实验硬件 |
|---|---|---|---|
| 编译速度 | "over 6× faster compilation than prior structured generation engines" | 摘要 · §4.2 | AMD EPYC 9654(单线程) |
| 端到端开销 | "incurs near-zero end-to-end overhead in modern LLM serving systems" | 摘要 · §4.3 | RTX 5090 + Xeon 8470Q |
| 端到端延迟 | "about a 7x speedup over the end-to-end latency" | §4.3 | RTX 5090 + Xeon 8470Q |
| 与无约束的差距 | "no more than 6%" | §4.3 | RTX 5090 + Xeon 8470Q |

**6× 是编译时间,7× 是端到端延迟:两次实验、两套硬件,不能混着说成一个数字。** 这一页的用处就是防止过度引用——论文自己都没把三个数字说成一个。

### 3.2 Table 3:输出吞吐(token/s)

| 模型 | XGrammar | XGrammar-2 | 加速比(batch 1 / 16 / 128) |
|---|---|---|---|
| Qwen3-0.6B | 462 / 1712 / 3021 | **599 / 4287 / 9475** | 1.30× / 2.50× / 3.14× |
| Llama-3.2-1B | 274 / 861 / 1147 | **441 / 2933 / 6640** | 1.61× / 3.41× / 5.79× |
| Llama-3.2-3B | 139 / 597 / 791 | **184 / 1655 / 3830** | 1.32× / 2.77× / 4.84× |
| Llama-3.1-8B | 83 / 525 / 738 | **96 / 920 / 1938** | 1.16× / 1.75× / 2.63× |

(数据集 BFCL-v3,引擎 SGLang-v0.5.3.post3,硬件 RTX 5090 + Xeon 8470Q。加速比是我从表里两列相除得到的**算术**,不是论文原话。)

这张表的读法:batch 越大收益越大,模型越小收益越大。0.6B 在 batch 128 上从 3021 涨到 9475,而 8B 只从 738 涨到 1938。合理的解释是小模型 decode 本身很快,结构化解码的固定开销占比高,所以优化空间大;这也意味着**把这组数字搬到大模型上会失望**。

### 3.3 Table 4:消融——一个机制先把指标弄慢 15.9 倍

| 优化 | 预处理时间(ms) | 生成 mask(µs) | 相对基线 |
|---|---|---|---|
| Baseline | 4960.04 | 45.50 | — |
| + JIT | 612.07 | 722.47 | 预处理 8.1×↓ · mask **15.9×↑** |
| + Cross-grammar Cache | 534.80 | 333.75 | 1.1×↓ · 2.2×↓ |
| + Repetition State Compression | **5.37** | 126.49 | **99.6×↓** · 2.6×↓ |

这张表是全篇信息量最大的一张。加 JIT 之后预处理时间从 4960ms 掉到 612ms(8.1×),但**生成 mask 的时间从 45.5µs 涨到 722.5µs——慢了 15.9 倍**。之后靠 Cross-grammar Cache(2.2×)和重复压缩(2.6×)才把它拉回到 126.49µs。

两个必须带上的限定:

1. **15.9× 是 JIT 的代价,不是缺陷。** JIT 把编译期的工作推到了运行期,预处理时间因此下降 8.1 倍;mask 生成变慢是同一件事的另一面。引用"8.1×"而不提"15.9×",等于只引了一半。
2. **99.6× 是预处理时间,而且论文自己归类为长尾优化。** 从 534.80ms 到 5.37ms 是预处理,不是端到端;适用面是含长重复结构的 schema。

### 3.4 Table 6:schema 合法率与 Call Rate

| 模型 | 无约束 | w/ XGrammar-2 |
|---|---|---|
| Llama-3.2-1B | 22.07% | 100.00% |
| Llama-3.2-3B | 40.70% | 100.00% |
| Llama-3.1-8B | 66.95% | 100.00% |
| Llama-3.1-70B | 51.94% | 100.00% |

Call Rate 同步上升(1B:6.07% → 32.84%)。Table 1 / Table 2 则给出动机数据:跨工具集合的 token mask 缓存复用率随工具数上升;TagDispatch 的自动机规模显著小于等价的手写 EBNF 展开。**这两张表是 §3.2 / §3.3 的动机数据,不是收益承诺。**

### 3.5 能说什么,不能说什么

| 可以直说 | 不能直说 |
|---|---|
| 设计有效;相对上一代有明显提升;在 agentic 负载上结构复用真实存在。 | "快 6–7 倍";"零开销";"本机升级就能拿到同样收益"。 |

## 4 vLLM:一条完整链路上的 14 个锚点

vLLM 的结构化输出是一条"薄集成":它自己不做文法推理,只负责把 xgrammar 给出的 bitmask 施加到 logits 上。整条链路可以按数据流读一遍。

| 环节 | 位置 | 做什么 |
|---|---|---|
| 编译文法 | `v1/structured_output/backend_xgrammar.py:79` | `compile_grammar()`,内部按 schema / regex / grammar 三分支走 |
| 正则编译保护 | `v1/structured_output/backend_xgrammar.py:96` | `compile_regex_with_timeout(...)` |
| structural tag 通路 | `v1/structured_output/backend_xgrammar.py:105`、`:112`、`:114` | 构造 `xgr.StructuralTagItem`,调 `compile_structural_tag(tags, triggers)` |
| 分配掩码 | `v1/structured_output/backend_xgrammar.py:133` | `allocate_token_bitmask(max_num_seqs)` |
| 施加掩码 | `v1/structured_output/backend_xgrammar.py:208` | `fill_bitmask(bitmask, idx)` |
| 接受 token | `v1/structured_output/backend_xgrammar.py:157` | `accept_tokens(request_id, tokens)` |
| 回滚 | `v1/structured_output/backend_xgrammar.py:203` | `rollback(num_tokens)`,投机解码失败时用 |
| 全允许常量 | `v1/structured_output/__init__.py:59` | `self._full_mask = torch.tensor(-1, dtype=torch.int32)` |
| 并行阈值 | `v1/structured_output/__init__.py:62` | `fill_bitmask_parallel_threshold = 128` |
| 并行判定 | `v1/structured_output/__init__.py:63` | batch 达到阈值才走并行填充 |
| 超时开关 | `v1/structured_output/utils.py:49`、`:66-67` | `compile_regex_with_timeout`;当 `timeout <= 0` 时**直接 `return fn(pattern)`** |
| 缓存上限 | `envs.py:221`、`:1647` | `VLLM_XGRAMMAR_CACHE_MB`,默认 **512**(MB) |
| 内核入口 | `v1/worker/gpu/structured_outputs.py:59` | `apply_grammar_bitmask(...)` |
| 内核本体 | `v1/worker/gpu/structured_outputs.py:104-105`、`:126`、`:154`、`:159-162` | `BLOCK_SIZE = 8192`;Triton kernel 里现拆 bit。 |

关于 `v1/structured_output/utils.py:66-67` 有个容易说错的点:`compile_regex_with_timeout` 在 `timeout <= 0` 时是**同步调用** `fn(pattern)`,也就是超时保护被关掉了,而不是"有超时"。这个开关的默认值决定了它是保护还是摆设。

内核那一段直接读代码最清楚:

```python
# v1/worker/gpu/structured_outputs.py:154
bitmask = ((packed_bitmask[:, None] >> (tl.arange(0, 32)[None, :])) & 1) == 0

# v1/worker/gpu/structured_outputs.py:159-162
tl.store(logits_ptr + logits_idx * logits_stride + block_offset,
    -float("inf"),
    mask=position_is_active & bitmask & (block_offset < vocab_size),)
```

把 bit 右移出来、和 1 做与、**再判 `== 0`**,然后给这些位置写 `-inf`。所以 vLLM 这边的约定是:**bit = 1 允许,bit = 0 禁止。** `_full_mask = -1`(int32 全 1)也印证这一点——"全部允许"就是"全 1"。

**结论:vLLM 自己不做文法推理——它只负责把 xgrammar 给出的 bitmask 施加到 logits。** 引擎的智能全在 xgrammar 里,而 xgrammar 侧的 mask 生成,就是第 7 节要出问题的地方。

## 5 DeepInfer:在 Python 里补上 vLLM 交给库的那一层

DeepInfer 是"厚集成"。它在 `deepinfer/structure_output/` 下自建了一层,把 vLLM 完全交给 xgrammar 的语义在 Python 里重新实现了一遍。三层结构:

| 文件 | 职责 |
|---|---|
| `structure_output/matcher.py` | 自研状态机,包住 xgrammar 的 `GrammarMatcher` |
| `structure_output/compiler.py` | 包住 `GrammarCompiler`,加缓存开关与 CVE 警告 |
| `structure_output/mask.py` | 薄壳,懒 import xgrammar,转发到 TileLang 内核 |

`mask.py` 的懒 import 有个具体理由,注释写在文件里:`mask.py` 在 sampler 的 import 闭包里,顶层 `import xgrammar` 会把 xgrammar 拖进不用结构化输出的部署。所以 `from xgrammar import ...` 被放在函数体内。

采样器里的 `so_status` 状态机在 `model_executor/layers/sampler.py:318-408`:

| 状态 | 行为 |
|---|---|
| `so_status ≤ 0` | 跳过;chunked prefill 阶段也跳过(`last_output_token == -1`) |
| `status == 1 → 2` | 首步只做状态迁移,不做 accept |
| `status == 2` | accept 本步 token + 逐个 accept draft token,失败即 break,然后 rollback |
| 异常处理 | 任何异常只把本请求判死(`so_status = -1`),不连坐整个 engine |

**DeepInfer 的实质差异:它在 Python 里做了 vLLM 完全交给库的那一层**——超时、异常隔离、缓存 kill switch,以及自研的 trigger 分派。

### 5.1 两条落差,但都不是"对错"

**① 版本:0.2.2 与 0.2.3 不是同一个能力集合。** DeepInfer 的 `requirements.txt:21` 钉 `xgrammar==0.2.2`;vLLM 这侧是 0.2.3。0.2.3 有 `StructuralTagItem` / `compile_structural_tag` / `Grammar.from_structural_tag`;DeepInfer 的 compiler 只走 `compile_json_schema` / `compile_regex` / `compile_grammar`(`deepinfer/structure_output/compiler.py:57-61`),**没有 dispatch 通路**。

**② 分派:多模式自动机 vs 单模式 KMP。** 论文 §3.2 用 Aho–Corasick 同时跟踪任意多个 tag;DeepInfer 只在 Python 里跟一条 trigger 序列(`deepinfer/structure_output/matcher.py:24-33` 的 KMP 失败函数,`:74-75` 的 `trigger_progress` / `_trigger_failure`),多 tag 同时跟踪不在当前实现里。vLLM 不自己实现,把 tags + triggers 交给 xgrammar(`backend_xgrammar.py:112`)。

**版本落差是依赖管理问题,分派落差是能力边界问题,内核落差是性能策略问题。三者混在一起谈,会把"钉住旧版"说成"实现有错"。**

内核落差本身也不是对错:vLLM 用 Triton,`BLOCK_SIZE = 8192`(`v1/worker/gpu/structured_outputs.py:104`),在 kernel 里现拆 bit 再 store `-inf`;DeepInfer 用 TileLang,`threads = 128 × 64 = 8192`(`tilelang_ops/cuda/structure_output.py:28-29`),先搬进 shared memory 再写回,还用 `T.pdl_sync()`(`:40`)与相邻 kernel 重叠。同一语义,两种性能策略。

但也就是在这个内核上,出现了第 7 节的问题。

## 6 两套默认值:缓存上限差 20 倍

同一件事(编译缓存),两份代码的默认值差 20 倍:

| 项目 | vLLM actual-0909 | DeepInfer |
|---|---|---|
| xgrammar 版本 | 0.2.3 | 0.2.2(`requirements.txt:21`) |
| 缓存上限默认 | **512 MB**(`envs.py:1647`) | **10 GB**(`environ.py:170`) |
| 上限为 0 时 | 正常路径 | `logger.warning` + 指向 CVE-2025-32381 |
| 关闭开关 | `cache_enabled=True` 默认 | `DEEPINFER_XGRAMMAR_DISABLE_CACHE` |

两侧各有一处措辞值得单独记:

- vLLM:`compile_regex_with_timeout` 在 `timeout <= 0` 时同步调用 `fn(pattern)`(`v1/structured_output/utils.py:66-67`)——超时保护被关掉,并非"有超时"。
- DeepInfer:`deepinfer/structure_output/compiler.py` 的注释写明 xgrammar ≤ 0.1.x 在缓存开启时出过生产事故,因此保留 `disable_cache` 这个 kill switch。(该注释提到的 CVE 编号是 CVE-2025-32381,**我引自代码注释,没有独立核实**。)

**差异不是对错,是风险偏好:vLLM 取小默认值,DeepInfer 取大默认值加显式告警。** 但 20 倍的差距本身值得注意——它意味着同一个负载换一个框架,缓存行为可能完全不同。

## 7 一处把 bit 极性写反的内核

这是全篇唯一一处功能性发现,也是我写这篇的主要原因。

### 7.1 先说清楚 bitmask 是什么

结构化生成里,每一步都要把词表里"这一步不允许生成的 token"的 logits 打成 `-inf`。工程上不传一个布尔数组,而是传一个 **bit 数组**:vocab 里第 `i` 个 token 对应第 `i` 个 bit。于是就有了一个必须钉死的约定:

> **bit = 1 表示允许,bit = 0 表示禁止。**

vLLM 那边是按这个写的(`v1/worker/gpu/structured_outputs.py:154` 判 `== 0` 才写 `-inf`),`_full_mask = -1`(全 1 = 全允许)也印证它。而 xgrammar 自己的输出格式就是这个约定。

### 7.2 另外 9 处都按"1=允许"写

同一个仓库和它依赖的库里,下面这些地方互相印证,这一侧没有歧义:

| # | 位置 | 证据 |
|---|---|---|
| 1 | `structure_output/matcher.py:14` | `from xgrammar.matcher import _FULL_MASK, bitmask_dtype, get_bitmask_shape` —— 沿用的就是库里的定义 |
| 1b | `xgrammar/matcher.py:24`(0.2.3) | `_FULL_MASK = torch.tensor(-1, dtype=bitmask_dtype)`,`bitmask_dtype = torch.int32`(`:15`)—— int32 全 1,即"全部允许" |
| 2 | `structure_output/matcher.py:44` | `fill_with_full_mask` 时 `mask.fill_(_FULL_MASK)` |
| 3 | `structure_output/matcher.py:105` | `mask_after_eos` 用 `fill_with_full_mask=True` 构造 |
| 4 | `structure_output/matcher.py:184-186` | `vocab_mask[idx].zero_()` 之后 `\|= np.int32(np.uint32(1 << (expected & 31)))` —— **"全禁再点亮一个"** |
| 5 | `tilelang_ops/structure_output.py:60-61` | 参考实现:`allowed = ((bitmask[req, word] >> bit) & 1).bool()`,然后 `masked_fill_(~allowed, -inf)` |
| 6 | `tilelang_ops/asc/structure_output.py:95-97` | Ascend 内核:`allowed = vcmps(vand(words, bit_flags), 0, "ne")` 再 `vsel(values, neg_inf, allowed)` —— 即 **bit=1 才允许** |
| 7 | `tilelang_ops/structure_output.py:12` | 生产入口函数名本身就是 `apply_token_bitmask_by_step_inplace` ——"施加 bitmask",语义上就是把 1 的位置放行 |
| 8 | 实际生产者 | `deepinfer/model_executor/layers/sampler.py:362` 用 `matcher.fill_vocab_mask(...)` 填 `bitmasks_cpu`,再 `.cuda()`(`:398`)送进内核 —— 填的是第 4 条那套 |

第 4 条是最硬的:它"先 `zero_()` 清空、再 `|=` 点亮一个",所以被允许的 token 那一位一定是 1;如果约定是"1=禁止",这个函数就是在做完全相反的事。

### 7.3 但 CUDA 内核的判据是反的

```python
# tilelang_ops/cuda/structure_output.py:54-56
for i in T.Parallel(block_size):
    if (bitmask_smem[i // _BITS_PER_BLOCK] & (1 << (i % _BITS_PER_BLOCK))) == 0:
        logits_smem[i] = -T.infinity(T.float32)
```

读法:`bit` 为 **0** 时写 `-inf`。也就是说,这个内核认为 **bit = 0 表示允许,bit = 1 表示禁止** —— 和上面 9 处正好相反。

把两侧并排放:

| 实现 | 判据 | 约定 |
|---|---|---|
| vLLM Triton(`v1/worker/gpu/structured_outputs.py:154`) | `((bitmask >> bit) & 1) == 0` → `-inf` | bit=0 禁止 |
| DeepInfer Ascend(`asc/structure_output.py:95`) | `vcmps(vand(words, bit_flags), 0, "ne")` → allowed | bit=0 禁止 |
| DeepInfer 参考实现(`tilelang_ops/structure_output.py:60-61`) | `~((bitmask >> bit) & 1)` → `-inf` | bit=0 禁止 |
| DeepInfer mask 构建(`deepinfer/structure_output/matcher.py:184-186`) | `zero_()` 后 `\|= (1 << expected)` | bit=1 允许 |
| **DeepInfer CUDA(`cuda/structure_output.py:55`)** | `(bitmask & (1 << bit)) == 0` → `-inf` | **bit=1 禁止** |

注意最后一行有个细节:它不是"哪边允许哪边禁止"的风格差异,而是**同一个 bit 的两侧含义完全互换**。约束越强的位置(允许集越小),被放行的禁止 token 越多、被打掉的允许 token 也越多。

### 7.4 仓库自带的测试会怎么判

`tilelang_ops/structure_output.py:81-96` 里有一个 `test_apply_token_bitmask_by_step_inplace`:用参考实现和被测内核各跑一遍,断言 `torch.equal(logits_ref, logits_tl)`。也就是说,**这个仓库自己把参考实现当作正确答案,并要求内核与它逐元素相等。**

再看测试怎么造数据(`:89`):

```python
bitmask = torch.randint(-(2**31), 2**31 - 1, (num_requests, bitmask_size), dtype=torch.int32, device="cuda")
```

整个 int32 取值范围里的随机数。这个细节决定了测试的判决力:内核和参考实现只在**某一位的两种含义恰好不产生分歧**时才会一致,也就是那个 word 恰好是 `0x00000000` 或 `0xFFFFFFFF`。随机取值几乎不会落在那里。

现在把内核选择逻辑接上。`tilelang_ops/ops.py:15` 按平台动态选后端:

```python
_pkg = importlib.import_module(f"{__package__}.{PLATFORM.tilelang_ops_backend}")
```

于是:

- 在 **Ascend** 上选到 `asc/structure_output.py`,它的极性**和参考实现一致** → 这个测试过。
- 在 **CUDA** 上选到 `cuda/structure_output.py`,它的极性**和参考实现相反** → 这个测试过不去。

**也就是说,这个测试只在极性写对的那条后端上有效;在 CUDA 上它是一张必然报警的网。** 而 CUDA 恰恰是这套代码实际跑的那条路径。

### 7.5 结论与验证边界

从源码一致性出发,可以确定的是:

1. 参考实现、Ascend 内核、vLLM Triton、以及 mask 构建逻辑,这四处各自独立地写成 `bit=1 允许`;
2. CUDA 内核与它们相反;
3. 仓库自带的等价性测试站在参考实现这一侧,所以它在 CUDA 上应该失败。

因此我判断 **CUDA 内核的极性是写错的那一侧**。

但必须把边界划清楚,以下是**没有做**的事:

- 没有在 GPU 上跑过这个内核,也没有跑过这个测试。DeepInfer 在我这里只有只读副本,没有运行环境。
- 所以上面第 3 条是**推断**,不是实测。要判定它,一次 pytest 就够:`774ce24` 上跑 `test_apply_token_bitmask_by_step_inplace`,在 CUDA 上它是红是绿,当场定论。
- 如果它真的跑出红,还有一层要查:采样器里是否在别处对 mask 做过取反补偿。我按 `grep` 走完了 `deepinfer/model_executor/layers/sampler.py:362 → :398 → :437` 这条生产路径,没有看到任何取反;但"没搜到"不等于"不存在",这条也留作待验证。
- 如果极性真的反了,后果是**功能性**的:约束越强的 schema,越可能出现"该出的 token 出不来、不该出的 token 出来",表现出来是生成结果异常,而不是简单的慢。

我把这段写成"源码读出来的矛盾",而不是"DeepInfer 有 bug"——因为**判定的那一次运行不属于我这次做过的证据**。这也是我给这份材料的核实用语:已核实的事实和需要实测的推断,不能混排。

## 8 局限:我没回答的问题

这几条是我在读论文与读源码时没找到明确答案的地方,不是论文的错,是需要实测确认的部分。

| 问题 | 具体情况 |
|---|---|
| **TagDispatch 的语义边界** | 论文用 Aho–Corasick 描述多模式分派;DeepInfer 当前是单模式 KMP。两者不是同一个能力集合。 |
| **Partial hit 的重算范围** | 论文说缺省需重算"不确定 token + 原 lookahead 判定的 token",但没有给出这部分占比与最坏情况的分析。 |
| **JIT 的代价被谁吸收** | Table 4 显示 mask 生成慢 15.9×。论文说与 prefill/decode 重叠,但没有给出重叠失败时的退化曲线。 |
| **重复压缩的适用面** | 论文自己归类为"长尾场景"优化;普通 schema 上看不到 99.6×。 |
| **"升级即获得动态能力"** | vLLM 0.2.3 已有 dispatch 相关 API;DeepInfer 钉 0.2.2 且自研分派。这句话不成立。 |

还有三条工程上必须先问、但论文没回答的:

1. **"动态程度"到收益的映射。** 如果我的负载里只有 3 个固定工具,XGrammar-2 相对 XGrammar 还有多少优势?论文没有这条曲线。
2. **重叠失败的退化。** JIT 依赖"编译与 prefill 重叠"。如果 batch 很小、prefill 很短,重叠不上时会怎样?
3. **缓存容量耗尽的行为。** 论文测了命中率,没测缓存耗尽时的退化路径;而两份生产代码都设了上限(512 MB / 10 GB),说明这件事在生产里会发生。

这三条不是论文的缺陷,是"论文的边界"——引用时要连着边界一起引。

## 9 一页总表

**三句话总结 XGrammar-2:**

1. 把"结构切换"从用户态路由提升为文法内建原语(TagDispatch),语义上覆盖请求内动态。
2. 把"跨请求复用"做进引擎(Cross-Grammar Cache),用层次化哈希在 FSM 引用图上求子结构等价。
3. 把解析与缓存重做成 Earley + JIT + 重复压缩,用"运行期按需"换"编译期全算"。

**对两个生产集成的判断:**

| | vLLM | DeepInfer |
|---|---|---|
| 集成厚度 | 薄集成,文法智能全在 xgrammar | 厚集成,在 Python 里自建状态机补上分派语义 |
| 动态能力 | 已有 structural_tag 通路,动态与否取决于调用方是否传 tags/triggers | 尚未接入这条通路,自研单模式 KMP |
| 工程护栏 | 超时保护(注意 `timeout <= 0` 时失效)、缓存上限 512 MB | 超时、异常隔离、缓存 kill switch、上限 10 GB |
| 本次发现 | — | CUDA 掩码内核的 bit 极性与另外 9 处相反(待实测判定) |

**同一个引擎语义,两种集成哲学;差别不在对错,在"谁来承担复杂度"。**

**核实纪律(三条,建议照抄):**

1. 论文数字一律标注实验设置(硬件、基线版本、单线程),不与工程数字混用。
2. 源码引用对应具体修订(DeepInfer `774ce24`、vLLM actual-0909);引自代码注释的 CVE 编号标明未独立核实。
3. 涉及"应该怎么做"的推断一律标为待验证,不与已核实事实混排。

---

**材料与出处**

- 论文:XGrammar-2: Dynamic and Efficient Structured Generation Engine for Agentic LLMs — [arXiv:2601.04426v4](https://arxiv.org/abs/2601.04426) [cs.AI], 5 Aug 2026;ACM CAIS '26, May 26–29 2026, San Jose。作者:Linzhang Li, Yixin Dong, Guanjie Wang, Ziyi Xu, Alexander Jiang, Tianqi Chen。
- 代码仓库:[mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)
- 上一代:[arXiv:2411.15100](https://arxiv.org/abs/2411.15100)
- DeepInfer 只读副本:`774ce244b87cc0eb8d4b94ab9f5de2ab22049f01`(2026-10-20)
