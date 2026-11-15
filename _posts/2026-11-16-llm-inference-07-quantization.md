---
layout: "post"
title: "从一个 token 读懂 LLM 推理 07 · FP8、NVFP4 与后端"
display_title: "FP8、NVFP4 与后端"
subtitle: "16 个权重的存储账怎样走到 GEMM"
description: "手算低精度权重与 scale 的字节数，沿导出、加载和执行核对量化路径。"
excerpt: "手算低精度权重与 scale 的字节数，沿导出、加载和执行核对量化路径。"
date: "2026-11-16 00:07:00 +0800"
permalink: "/llm-inference-07-quantization/"
categories: ["llm", "inference"]
tags: ["LLM 推理", "从一个 token 读懂 LLM 推理"]
---

A 在 decode 时只送入一个新 token。对某个 Linear 来说，这一轮可能只收到一行激活，却仍需要用上大量权重。一种可行的思路是把权重用更低位宽存起来，再让支持该格式的 GEMM 直接消费。这条路径要从一个块的字节账开始看。

## 先给 16 个权重算账

假设权重沿输入通道排成连续的一维块，每块 16 个元素。BF16 每个占 2 字节，16 个共 32 字节。FP8 的数值区共 16 字节，所用缩放粒度决定额外开销。NVFP4 的数值是 E2M1，两个值能打包成 1 字节。16 个值占 8 字节，加一个 1 字节的 E4M3 块 scale，共 9 字节。NVFP4 还有张量级 FP32 scale，图里单列，实际文件还应检查对齐与元数据。 [NVIDIA cuDNN Block Scaling](https://docs.nvidia.com/cudnn/operations/BlockScaling/)、[Transformer Engine NVFP4](https://docs.nvidia.com/deeplearning/transformer-engine/features/low_precision_training/nvfp4/nvfp4.html)

![每 16 个数值，BF16 32 字节，FP8 数值区 16 字节，NVFP4 数值加块 scale 9 字节](/assets/img/llm-inference-from-one-token/07-weight-bytes.svg)

如果张量有 1,024 个元素，刚好分成 64 块，这个存储模型下 BF16 占 2,048 字节，NVFP4 占 64 × 9 + 4 = 580 字节。这个算式可以在实际 checkpoint 的权重、块 scale 和全局 scale 三项上逐一核对。FP8 每元素 8 位，常见编码有 E4M3 和 E5M2，两者用不同的指数位数交换动态范围和精度。 [FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433)

## 让 scale 参与乘加

把 scale 定义成恢复数值时使用的乘数。假设一个权重的 FP4 编码值是 2，块 scale 是 0.5，张量 scale 是 1.25，恢复后的权重约为 2 × 0.5 × 1.25 = 1.25。同一块里的其他权重共享后两个乘数。用这个过程理解 Linear 时，先看权重和激活从哪儿取，再看 scale 如何与 K 维分块对应。块在内存里排错了，即便反量化公式正确，kernel 也会用错 scale。

FP8 也有多种 scale 粒度。一种实现是每个输出通道给权重一份 scale，每个 token 给输入激活一份 scale。前者随权重保存，后者可以在 forward 时根据当前激活计算。A 的 decode 如果每次只进一个 token，动态缩放和打包仍然有开销，收益需要结合实际 kernel 路径测量。 [Transformer Engine FP8 与 FP4 入门](https://docs.nvidia.com/deeplearning/transformer-engine/examples/fp8_primer.html)

## 把导出和运行接起来

做 PTQ 时，先在配置里确定量化哪些层和张量，再用代表性输入校准需要校准的量，随后导出 packed 权重和 scale。服务端加载后，逐项检查权重格式、激活格式、块大小、布局和设备能力，确认命中的 GEMM。以 ModelOpt 为例，配置和导出工具解决的是产物怎么生成，运行时还要有相应的 loader 和 kernel。 [ModelOpt 量化指南](https://nvidia.github.io/Model-Optimizer/guides/_pytorch_quantization.html)

验收时先核对实际文件和加载峰值，再用固定输入比较数值，最后做同请求的延迟和吞吐对照。单卡 dense Linear 的通过记录覆盖的是那条输入和后端路径。涉及 MoE 时还要追到每张卡的专家布局和 grouped GEMM，服务指标要重新在真实请求路径上测。

## 沿着 Quantized Linear 读三段代码

A 的 decode 输入在这个例子里是一行。假设隐藏维度 K 为 1,024，Linear 输出维度 N 也为 1,024，原始权重形状就是 `[N, K]`。读量化实现时，先记下每个张量对应的轴，再顺着导出、加载和前向走一遍。下面是用来读代码的原创伪代码。这里用动态输入缩放表示其中一种实现。

```python
# 导出端
packed_weight, weight_scales = encode_weight(weight, recipe)
save_checkpoint(packed_weight, weight_scales, recipe.metadata)

# 加载后做一次
kernel = pick_backend(device, recipe.metadata, local_shape)
weight_state = kernel.prepare(packed_weight, weight_scales)

# 每次 forward
packed_input, input_scales = encode_activation(hidden, recipe)
return kernel.matmul(packed_input, input_scales, weight_state, bias)
```

**导出端决定保存什么。** 配方规定目标 Linear、排除项、权重与激活格式，以及 scale 粒度。需要校准时，校准代码先收集代表性输入的统计量，导出代码再写入 packed 权重、scale 和配置。拿 NVFP4 一维块举例，1,024 个输入通道每 16 个为一组，每个输出通道有 64 份块 scale。权重区理想形状是 `[1024, 512]` 个字节元素，未重排的块 scale 有 `[1024, 64]` 个元素。再查张量级 scale、对齐和剩余高精度层，才能从文件核对容量。 [ModelOpt 配方文档](https://nvidia.github.io/Model-Optimizer/guides/10_recipes.html) · [cuDNN 逐块缩放](https://docs.nvidia.com/cudnn/operations/BlockScaling/)

**加载端把格式交给具体后端。** 以公开 vLLM v0.11.0 的 ModelOpt NVFP4 为例，先读 `from_config` 看元数据如何转成配置，再看 `create_weights` 给权重与 scale 分配什么张量。`process_weights_after_loading` 会按后端准备布局。这个阶段发生在加载后，可以由后续多次 decode 共用。 [配置解析](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/model_executor/layers/quantization/modelopt.py#L687-L750) · [张量注册和后端布局](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/model_executor/layers/quantization/modelopt.py#L865-L977)

**前向看实际分支。** 同一版的 `apply` 中，Marlin 路径直接把输入交给专用入口，其他列出的路径会先生成 FP4 激活及其块 scale，再调用选定的 GEMM。于是同一份 NVFP4 checkpoint 在阅读时至少要问两次。权重如何保存？激活如何进 kernel？FP8 也要看实际实现是按 token、按张量还是用其他粒度缩放。这里的 `[1, 1024]` 是教学输入，真实开销要同时计入输入量化、GEMM 和结果收尾，再用 profiler 核对实际走的分支。 [vLLM NVFP4 Linear 的 apply](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/model_executor/layers/quantization/modelopt.py#L979-L1034)

---

[系列导读](/llm-inference-00-overview/) · [上一篇 · MoE、专家并行与混合注意力](/llm-inference-06-moe-hybrid/)
