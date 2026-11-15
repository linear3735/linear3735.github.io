---
layout: "post"
title: "从一个 token 读懂 LLM 推理 05 · TP、PP、DP"
display_title: "TP、PP、DP"
subtitle: "沿矩阵、层和请求理解三种切分"
description: "用两张卡做一遍可手算的矩阵乘，再区分流水线和副本分流。"
excerpt: "用两张卡做一遍可手算的矩阵乘，再区分流水线和副本分流。"
date: "2026-11-16 00:05:00 +0800"
permalink: "/llm-inference-05-parallel/"
categories: ["llm", "inference"]
tags: ["LLM 推理", "从一个 token 读懂 LLM 推理"]
---

还是请求 A，输入 6 个 token，生成 3 个。单卡上每个 token 要过完整模型。换成两张卡，可以让它们一起算每一层，也可以各算一段层，还可以把 A 全交给一张卡，另一张卡服务请求 B。每一种安排需要传输的数据都不同。

![TP 切同层矩阵，PP 切层，DP 将请求送往不同副本](/assets/img/llm-inference-from-one-token/05-parallel.svg)

## 张量并行切一层

先拿 A 某个 token 的激活做一次手算。输入行向量是 [2, 3]，权重矩阵按输出维乘输入维存放，两行分别是 [1, 4] 和 [2, 1]。整层的输出是 [14, 7]。

沿输出维切，卡 0 拿第一行权重，卡 1 拿第二行。两张卡都读完整输入，各得到 [14] 和 [7]。如果下一层需要完整向量，按维度拼接即可，通信对应 AllGather。沿输入维切，卡 0 负责输入的 2，得到 [2, 4]，卡 1 负责输入的 3，得到 [12, 3]。两张卡各得到一个完整形状的部分和，用 AllReduce 按元素相加，还原 [14, 7]。有 bias 时，可以在归约完成后加一次。[Megatron-LM 论文](https://arxiv.org/abs/1909.08053) · [NCCL 集合通信文档](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html)


一次输出切分之后，如果下一层正好只需本卡的那段激活，中间的拼接可以省下来。检查通信时要跟着相邻两层的数据走，先判断谁需要完整张量，再数 collective。

## 流水线并行切层，数据并行切请求

假设模型 4 层，流水线并行让卡 0 算前两层，卡 1 算后两层。A 的 prefill 先过卡 0，再把中间激活交给卡 1。每轮 decode 同样要跨 stage。若边界传两块 [6, 4096] 的 BF16 张量，这次逻辑传输量是 2 × 6 × 4,096 × 2 = 98,304 字节，也就是 96 KiB。单行 decode 对应 16 KiB。消息数、互联带宽和等待时间还要从时间线读。

数据并行让两个副本都保留完整模型。A 可以一直由副本 0 执行，B 走副本 1。每个副本各自排队，保存各自的 KV。假设 TP=2、PP=1、DP=2，总共要 4 张 GPU。A 由其中一个副本的两张卡共同计算，B 可以由另两张负责。比较这些安排时，记录 A 的延迟和所有请求的总输出吞吐，两项指标回答的是不同问题。本文的数字是逻辑数据量和代数验算。

---

[系列导读](/llm-inference-00-overview/) · [上一篇 · 算子融合与 CUDA Graph](/llm-inference-04-kernels-graphs/) · [下一篇 · MoE、专家并行与混合注意力](/llm-inference-06-moe-hybrid/)
