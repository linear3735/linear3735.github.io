---
layout: post
title: "部署解剖:一条 sglang 命令看懂 AI Infra 硬件与生态 — 从五个 .so 拆到 NVLink 与 400G 网卡"
date: 2026-10-25 00:00:00 +0800
categories: llm inference gpu
---

> 这篇是对 B 站 UP 主「前滩猿神」《90 分钟讲透 AI Infra》系列第 9 集[《从一条推理命令,看懂 AI Infra 硬件与生态》(BV1Wgnp64E6e)](https://www.bilibili.com/video/BV1Wgnp64E6e)(2026-10-22 发布)的学习笔记式整理。第 9 集是系列的归纳汇总:素材是 8×H200 上跑 GLM-4.6 的一条 sglang 启动命令,一路从 Python 拆到 5 个 .so、设备文件、NVLink 拓扑、400G 网卡,再回头解释 sglang 替我们选的每个 backend 为什么是那个。本文按视频顺序重排成文字版,配图是原视频幻灯片截图(版权归原作者)。
>
> 方法承诺同「量化解剖」系列:写到数字就给出处(视频原话 / 公开规格文档 / 我们的算术),算术注明是算术,实测注明是实测;公式全部用大白话加数字例子,不用 LaTeX;集群内部标识一律为 0。

## 目录

- [1 一条命令，四张替你做的选择题](#1-一条命令四张替你做的选择题)
- [2 操作系统里的五个 .so](#2-操作系统里的五个-so)
- [3 libcuda 再往下:设备文件与内核模块](#3-libcuda-再往下设备文件与内核模块)
- [4 通信两条路:单机 NVLink 与多机 IB](#4-通信两条路单机-nvlink-与多机-ib)
- [5 硬件三大资源:算力、显存、互联](#5-硬件三大资源算力显存互联)
- [6 瓶颈算术:时间取三个除法的最大值](#6-瓶颈算术时间取三个除法的最大值)
- [7 SM 内部与精度阶梯](#7-sm-内部与精度阶梯)
- [8 GPU 代际:Hopper 缺的那块积木](#8-gpu-代际hopper-缺的那块积木)
- [9 三个 backend 的为什么](#9-三个-backend-的为什么)
- [10 这套讲法为什么好](#10-这套讲法为什么好)

## 1 一条命令，四张替你做的选择题

整集视频的起点只有两行:

```
python -m sglang.launch_server \
    --model-path zai-org/GLM-4.6 --tp 8 --ep 8 --port 30000
```

![sglang 启动命令与 8×H200 分工](/assets/img/aiinfra-20261025/command-eight-cards.png)

这行命令背后的硬件是 8 张 H200(每张 141GB)。GLM-4.6 切成八份摊上去:每卡扛约 89GB 权重——20 个专家加上稠密件;注意力是 GQA,Q 头 12 个、KV 头 1 个。`--tp 8`(张量并行)和 `--ep 8`(专家并行)是你显式写的,但**你只写了三个参数,sglang 替你做了四张选择题**:

| 参数(你没写) | 替你选的值 | 干什么 |
|---|---|---|
| `--attention-backend` | **fa3** | FlashAttention 3,只管 Hopper 代 |
| `--bf16-gemm-backend` | **torch** | 非 Blackwell 上 auto 落回 torch matmul → cuBLAS |
| `--moe-a2a-backend` | **deepep** | 跨卡专家互寄;不开它,8 卡之间 experts 不通信 |
| `--moe-runner-backend` | **deep_gemm** | 接 DeepEP 数据格式的 MoE GEMM |

![sglang 按硬件代号查表选出的四个 backend](/assets/img/aiinfra-20261025/backends-chosen.png)

选择的依据就两行硬件信息:`torch.cuda.get_device_name()` 返回 H200,capability 是 `(9, 0)` 即 sm90。整条命令表面是"启动一个服务",实质是一次**按硬件代号查表**。为什么是 fa3 不给老卡用、deep_gemm 为什么必须配 deepep、17 个 attention-backend 是怎么排出来的——后面每节回答一个。

## 2 操作系统里的五个 .so

pip 装完 sglang,dist-packages 里躺着五个关键库:

| .so | 真身 | 备注 |
|---|---|---|
| `libcublas.so.13` | cuBLAS | BF16 GEMM 的默认去处 |
| `sgl_kernel` 的 `flash_ops.abi3.so` | FlashAttention 3 | `cuobjdump --list-elf` 可见内嵌 sm_90a cubin——wheel 里已编译好 |
| `deep_gemm/_C.so` | DeepGEMM | `cuobjdump` 查:**无 device code**。它是 JIT,第一次跑现编(§9.2) |
| `libnccl.so.2` | NCCL | 集合通信 |
| `deep_ep/_C.*.so` | DeepEP | MoE 收发 |

这些库再往下走是两层 CUDA API,视频给的对照表:

```
torch.empty()      → cudaMalloc()      → cuMemAlloc()
kernel <<<>>>      → cudaLaunchKernel() → cuLaunchKernel()
```

`cuda*` 是 runtime API(`libcudart.so.13`,pip 装的,用户态);`cu*` 是 driver API(`libcuda.so.1`,**系统层,随驱动装,容器里从宿主机挂进**)。`ldd deep_ep/_C.so` 能一眼看到两个世界:一边 `torch_cuda`/`nvshmem_host`/`nccl`/`cudart` 全是 pip 目录,另一边 `libcuda.so.1` 在系统目录;`dpkg -S` 反查它属于 `libnvidia-compute-580`。

**两处版本必须咬合**:`libcuda.so.580.95.05` ↔ `/proc/driver/nvidia/version` 报的内核模块 580.95.05。推理栈起不来的经典原因之一就是这两处错位——容器挂了宿主机的驱动,任何一个环节版本漂移都会在 `cuInit` 处炸出一份难读的错。

## 3 libcuda 再往下:设备文件与内核模块

strace 跟一把,`libcuda` 干的事很朴素:对设备文件 `openat`/`ioctl`:

- `/dev/nvidiactl`(控制面)、`/dev/nvidia0` ~ `/dev/nvidia7`(每卡一个)、`/dev/nvidia-uvm`(统一虚拟地址)
- 设备文件是内核的手柄:`grep /proc/devices` 能看到 major **195 = nvidia**、**510 = nvidia-uvm**
- 手柄背后是内核模块:`lsmod` → `nvidia` / `nvidia_uvm` / `nvidia_peermem` / `nvidia_modeset`
- 模块底下是硬件:`lspci` → `GH100 [H200 SXM 141GB] × 8`

一句话:**Python 里一行 `torch.empty`,落到内核是一次对 major 195 设备文件的 ioctl**。理解了这条竖井,后面"容器为什么要挂 `/dev/nvidia*`""为什么 `nvidia-smi` 能在没 CUDA 依赖时工作"全部迎刃而解。

## 4 通信两条路:单机 NVLink 与多机 IB

### 4.1 单机:18 条 NVLink 和一把"钥匙"

`nvidia-smi topo -m` 显示卡间全部 `NV18`——18 条 bonded NVLink,走 NVSwitch;配套的 `nvidia-fabricmanager.service` 必须 active。

DeepEP 的单机收发抽象只有四步:本卡 `buf = cudaMalloc` → `handle = cudaIpcGetMemHandle(buf)` → 用 `torch.distributed` 把 handle 这把"钥匙"发给邻居卡 → 邻居 `peer = cudaIpcOpenMemHandle(handle)`。此后 dispatch kernel 直接写 `peer[i] = token`——**一条 GPU store 指令,数据就走 NVLink 到了对端显存,CPU 全程没摸数据**。它当然仍要经 `cudaIpc*` → libcuda → `/dev/nvidia*` → `nvidia.ko` 进内核拿授权,但数据面不过 CPU 内存。NCCL 的 all-reduce 是同一条用户态→内核路径。

![单机 NVLink 拓扑与 DeepEP 钥匙传递](/assets/img/aiinfra-20261025/single-nvlink-topo.png)

### 4.2 多机:IB 栈与 GPU 自己按门铃

跨机没有 NVLink 可走,换 InfiniBand。NVSHMEM 的传输插件是三个 .so:`nvshmem_transport_{ibgda, ibrc, ucx}.so.7`——其中 IBGDA 让 **GPU kernel 直接给网卡写门铃**(Doorbell),旁路掉 CPU 的 verbs 调用;sglang 的 Dockerfile 里专门修过一个 `libmlx5.so.1 → libmlx5.so` 的 symlink,就是 IBGDA 插件的依赖坑。

多机链路:`libnccl` → `libibverbs.so.1` → `libmlx5.so.1`(Mellanox 用户态驱动)→ `/dev/infiniband/uverbs0-7` → 内核 `mlx5_ib` / `ib_uverbs` / `ib_core` / `mlx5_core`,外加 `nvidia_peermem`(GPUDirect RDMA 直通显存)与 `gdrdrv`。`ibstat mlx5_0` 报:`ConnectX-7 MT4129, State: Active, Rate: 400Gb/s`——**一张 GPU 配一张网卡**,8 卡 8 口。

![多机 IB 链路与 GPUDirect RDMA](/assets/img/aiinfra-20261025/multi-machine-ib.png)

到此,从 sglang 到硅片的整条竖井齐了。视频的总图是这样两列:

![sglang 到硬件全栈图:左列计算,右列通信,中间虚线是系统调用](/assets/img/aiinfra-20261025/sglang-to-hardware.png)

左列计算:sglang → PyTorch | cuBLAS / FA3 / DeepGEMM(JIT nvcc → cubin)| `libcudart.so.13` | `libcuda.so.1` | `/dev/nvidia*` | `nvidia.ko` / `nvidia_uvm.ko` | 8×H200(sm90)。右列通信:NCCL / DeepEP | `libnvshmem_host.so.3` / `libibverbs.so.1` | `libmlx5.so.1` | `/dev/infiniband/uverbs*` | `mlx5_core` / `mlx5_ib` / `ib_uverbs` | NVLink + NVSwitch(单机)/ ConnectX-7 400G(多机)。中间那道虚线就是 `open`/`ioctl`/`mmap`——用户态与内核态的分界线。

## 5 硬件三大资源:算力、显存、互联

| 资源 | H200 数字 | 出处 |
|---|---|---|
| 算力(BF16 dense) | ≈ **989 万亿次/s** | NVIDIA 公开规格 |
| 显存 | 141GB HBM3e · **4.8TB/s**(`nvidia-smi` 报 143771 MiB) | 公开规格 + 命令实测 |
| 互联(机箱内) | NVLink **450GB/s 单向**(900 双向) | 公开规格 |
| 互联(机箱间) | IB 400Gb/s ≈ **50GB/s** | 公开规格 |

![三大资源对照一页](/assets/img/aiinfra-20261025/three-resources.png)

一句话梯度:**每往外推一级,带宽掉约一个数量级**——卡内 4.8TB/s → 机箱内卡间 0.45TB/s → 机箱间 0.05TB/s。后面所有"代码为什么长成那样"都是这三行数字逼出来的。

## 6 瓶颈算术:时间取三个除法的最大值

视频给的口算模型(算术,不是实测):

```
一步的时间 ≈ max( 计算量 ÷ 算力, 搬运量 ÷ 显存带宽, 通信量 ÷ 互联带宽 )
```

**decode(64 并发)**:每步每卡都要把 89GB 权重从 HBM 完整过一遍。

- 搬:89e9 字节 ÷ 4.8e12 字节/s ≈ **18.5ms**
- 算:64 个 token 的 GEMM ≈ 0.51 万亿次 ÷ 989 万亿次/s ≈ **0.5ms**
- max = 18.5ms → **Tensor Core 约 97% 的时间在闲着**。decode 是显存带宽瓶颈。

![decode 步的搬运 vs 计算对照](/assets/img/aiinfra-20261025/decode-memory-bound.png)

**prefill(32K token)**:搬的还是那 89GB(一遍),算的量随 token 数涨——64→32768 是 512 倍,0.5ms × 512 ≈ **260ms** 量级 → compute-bound,Tensor Core 终于吃饱。

交叉点在哪(算术):989e12 ÷ 4.8e12 ≈ **206**。意思是:平均每个从显存搬来的字节,要配上约 206 次浮点运算,算力才压得住带宽。代到三个真实场景:

| 场景 | 每个"位置"摊到的 token 数 n | 对照 206 | 瓶颈 |
|---|---|---|---|
| MoE decode(每专家) | ~3 | ≪ | 带宽 |
| 稠密 decode | 64 | < | 带宽 |
| prefill | 32768 | ≫ | 算力 |

![n≈206 交叉点:每个字节的浮点配额](/assets/img/aiinfra-20261025/n206-crossover.png)

一个数字 206 把 LLM 推理的两种 regime 一刀分开;MoE 的"每专家只摊到 3"还顺手解释了为什么专家 GEMM 是全场最难看的算术强度——§9.2 的 DeepGEMM 就是为这个 n≈3 设计的。

## 7 SM 内部与精度阶梯

"989 万亿次/s"这张嘴是怎么长出来的?H200 = **132 个 SM,每个 SM 分 4 个 partition**;每个 partition 里是 32 个 FP32 CUDA core 加 1 个 Tensor Core。

![SM 内部:每 SM 每周期 CUDA core 128 次 FP32 FMA vs Tensor Core 2048 次 BF16 FMA](/assets/img/aiinfra-20261025/sm-inside-cuda-tensor.png)

每个 SM 每个时钟周期:CUDA core 合起来能干 **128 次 FP32 FMA**;Tensor Core 能干 **2048 次 BF16 FMA**——16 倍。落到 8192³ 的 GEMM 数量级:FP32 ≈ 50 万亿次/s,BF16 ≈ 750 万亿次/s,约 15 倍的差距就是这么来的。这就是为什么全部推理栈最终都绕着 Tensor Core 转,而 CUDA core 沦为"打杂的"——但 §8、§9 会看到,这个打杂的偏偏继承了全部精度兜底工作。

精度阶梯(位宽 = 符号 + 指数 + 尾数):

- **FP32**:1+8+23
- **BF16**:1+8+7 → 65536 个可表示值
- **FP8 E4M3**:1+4+3 → 256 个值,最大 448
- **FP4 E2M1**:1+2+1 → 16 个值,最大 6;正值全体只有 0.5 / 1 / 1.5 / 2 / 3 / 4 / 6 这七个

![从 FP32 到 FP4 的精度释放图](/assets/img/aiinfra-20261025/release-precision.png)

16 个数怎么表达真实权重?给每小块配一个 **scale factor**。视频的手算例子:一小块原值 `[0.012, -0.031, 0.007, 0.024]`,绝对值最大 0.031;拿 FP4 的最大正值 6 去对位,`s = 0.031 ÷ 6 ≈ 0.0052`;每个值 ÷ s 再取最近可表示数 → 存 `[2, -6, 1.5, 4]`,另存一个 s。用时乘回来。全部量化误差就藏在"取最近"那一下里。

![scale factor 手算例子](/assets/img/aiinfra-20261025/scale-factor.png)

scale 自己也有格式,于是分成两派:

- **MXFP4**:每 32 个值配一个 E8M0 scale(纯 2 的幂,没有尾数)→ 平均 4.25 bit/值。OCP 开放标准;DeepSeek-V4 的专家、gpt-oss 走这条路数。
- **NVFP4**:每 16 个值配一个 FP8 E4M3 scale,再加一个全局 FP32 scale → 平均 4.5 bit/值。NVIDIA 自家方案,更准也更贵;Qwen3.8-27B-NVFP4 是其代表。

![MXFP4 vs NVFP4](/assets/img/aiinfra-20261025/mxfp4-vs-nvfp4.png)

第一手实证(DeepSeek-V4-Flash 的 `config.json`):`expert_dtype = "fp4"`、`fmt = "e4m3"`、`quant_method = "fp8"`、`scale_fmt = "ue8m0"`(即 E8M0)、`weight_block_size = [128, 128]`。看完本节,"模型卡里的 fp4 到底是哪种"就有读法了;与我们[量化解剖系列](/quant-anatomy-1-elvez-gguf/)拆的 IQ2_XXS/Q2_K 是同一主题的另一家族(那边按字节拆 GGUF 容器,这里按位宽拆数值格式)。

## 8 GPU 代际:Hopper 缺的那块积木

| 代 | 代号 | Tensor Core 新增精度 | 峰值(dense 口径) |
|---|---|---|---|
| Volta(2017) | sm_70 | FP16(首代 Tensor Core) | V100 125 万亿次/s |
| Ampere(2020) | sm_80 | + BF16 / TF32 / INT8 | A100 312 |
| Hopper(2022) | sm_90 | + FP8 | H100/H200 FP8 1979 |
| Blackwell(2024) | sm_100 | + FP6 / MXFP8 / MXFP4 / NVFP4 | B200 FP4 9000 |

关键不是数字翻倍,而是 **Hopper 的 Tensor Core 不认识"每块一个 scale"**——block scaling 是 Blackwell 才进 Tensor Core 的硬件特性。这条缺席引发两串后果:

**FP8 在 Hopper 上要靠 CUDA core 兜底。**Hopper 的 FP8 WGMMA 累加精度大约只有 14 位(DeepSeek-V3 技术报告第一手),长链累加会丢精度。工程解法:Tensor Core 只算原始 FP8 部分和,每算完一小段(128 个 K)由 CUDA core 把部分和乘上该段的 scale、升回 FP32 再累积——§9.2 DeepGEMM 的 kernel 就是照这个分工长的。

**FP4 在 H200 上"能存不能算"。**显存里、NVLink 上都按 FP4 走,进 Tensor Core 之前先在片上转回 BF16/FP8 再算。听着像白折腾?回到 §6:decode 是带宽瓶颈,账单按字节算。同一份 89GB 权重:

```
BF16  : 89GB   → 18.5ms
FP8   : 减半    → 9.3ms
NVFP4 : × 4.5/16 → ≈ 5.2ms   (算术)
```

精度砍到四分之一,decode 单步延迟砍掉 72%,而算力一点没变。这就是"decode 代低精度"的全部物理:不是算得更快,是搬得更少。

## 9 三个 backend 的为什么

回到 §1 的四张选择题。现在每张都能解释了。

### 9.1 `--attention-backend = fa3`

实际问题:attention 里 QKᵀ 得到的 S 矩阵、softmax 后的 P 矩阵都随序列长度平方膨胀,朴素写法要把它们落了 HBM 再读回来——在两张 n² 大小的矩阵上各走一轮最贵的操作。

FA3 的写法:把 Q/K/V 切成 128×128 的 tile(H200 的 228KB SMEM 正好塞),S/P 只在片上寄存器/SMEM 里活,**永不落 HBM**;softmax 用 online softmax 分块边算边归一,数学上与一次性 softmax 完全等价,不是近似。

![FA3 的 tile 方案](/assets/img/aiinfra-20261025/fa3-tiling.png)

为什么只给 Hopper:FA2 搬上 H100 只能吃到 35% 的算力利用率——它缺两样 Hopper 才有的硬件:TMA(硬件异步大块搬运)和 wgmma(异步 Tensor Core 指令)。FA3 用了这两样,利用率 75%。所以 `--attention-backend` 本质是一张按硬件代号查的表:sm90 → fa3,老卡 → fa2 / triton / flashinfer。

![FA3 为什么 Hopper-only](/assets/img/aiinfra-20261025/fa3-hopper-only.png)

Blackwell 上的新瓶颈又换了地方:Tensor Core 每周期能干 8192 次 FMA,而 exp 单元每周期只有约 16 个——softmax 里的 eˣ 成了短板。两种解法:fa4 用 CUDA core 上的多项式逼近去补 exp;TensorRT-LLM 的 `trtllm_mha` 把 attention 重排成对 Blackwell 友好的形状,sglang 在 B200 上默认就是后者。`--attention-backend` 一共 17 个值,分四组:通用 / NVIDIA 卡 / AMD / 其他(ascend、CPU)。

### 9.2 `--moe-runner-backend = deep_gemm`

实际问题:decode 时 512 个 token 的分配 ÷ 256 个专家 ≈ **每个专家 2 个 token**。naive 写法给每专家发一个小 GEMM:32 个小 GEMM 只点亮 132 个 SM 里的 32 个,剩下 100 个全程围观。

![naive 专家 GEMM 点亮不了全部 SM](/assets/img/aiinfra-20261025/moe-idle-sm.png)

DeepGEMM 三招:

- **招一,grouped GEMM**:dispatch 时就把 token 按目标专家排成 `x_sorted` 加每专家 `counts`,一次 kernel launch 发上千个 block,每个 block 认领"一个专家 × 一段 tile"——SM 全部点亮。
- **招三,FP8 的正确打开方式**:K 维 6144 切成 48 段 128;Tensor Core 只管吃原始 FP8 部分和,CUDA core 同时把每段部分和乘上该段的 scale、以 FP32 累加,两拨人流水线 overlap。顺手把 §8 说的 Hopper FP8 约 14 位累加精度的坑填了:误差在每 128 长度内不积累。
- **招二,JIT**:不发编译好的 cubin,发 `.cuh` 源码,首次跑用 nvcc 现编。

![grouped GEMM 的 x_sorted + counts 结构](/assets/img/aiinfra-20261025/grouped-gemm.png)

JIT 的现场长这样(视频里的启动日志):`Entering DeepGEMM JIT Pre-Compile session … typically 10-20 mins`,编译对象 `GROUPED_GEMM_NT_F8F8BF16_MASKED, N=4096, K=6144, num_groups=32`,编完落缓存,之后启动只要约 1 秒。代价是首次启动要等 10-20 分钟;好处是 tile 形状、分组数全部成了编译期常量,循环能彻底展开,kernel 为这一个模型形状量体裁衣。

![DeepGEMM JIT 预编译日志](/assets/img/aiinfra-20261025/jit-log.png)

### 9.3 `--moe-a2a-backend = deepep`

实际问题:EP 下每张卡要把 token 寄给"持有对应专家的卡",但寄给谁、寄多少,要等 router 算完才知道。naive 写法:每层一次 GPU→CPU 拷贝拿到统计,再决定怎么发——40 层,每层都在等 CPU。

![DeepEP 的四招](/assets/img/aiinfra-20261025/deepep-tricks.png)

DeepEP 四招:

1. **GPU 自己写对端显存**:单机走 NVLink(cudaIpc,§4.1),跨机走 IBGDA(§4.2),CPU 全程不摸数据。
2. **固定收件箱**:每卡给每个 peer 留好定长槽位,发送方直接写;收到多少由 GPU kernel 自己数——数出来的 counts **正好就是 grouped GEMM 要的那个 counts**。§9.2 和这一节的接口就是这么咬上的,为什么这对 backend 必须一起选。
3. **先压再寄**:token 先 FP8 压缩再上 NVLink/IB——通信量直接减半(互联是三大资源里最慢的那级,§5)。
4. **一个开关两套调度**:`--deepep-mode auto`,prefill 走 normal(大批量吞吐优先),decode 走 low_latency(小批量延迟优先)。

`--moe-a2a-backend` 有 13 个值:deepep / deep_ep_v2 / flashinfer / megamoe / pplx / mooncake / nixl / mori / ascend 系——一半是各家硬件的对应实现。视频最后用一张表把整条命令的选择题全部收拢:

![全命令 backend 汇总表](/assets/img/aiinfra-20261025/recap-table.png)

### 9.4 跨厂商:同一张表,每格重填

![NVIDIA / AMD / AWS Trainium 三列对照](/assets/img/aiinfra-20261025/cross-vendor.png)

- **AMD MI355X**:SM → CU,Tensor Core → Matrix Core,SMEM → LDS,NVLink → Infinity Fabric,IB → RoCE,CUDA → HIP,cuBLAS → hipBLASLt,NCCL → RCCL,NVSHMEM → rocSHMEM,kernel 写 ComposableKernel 或 Triton。生态上最接近 NVIDIA——但每一格都要重填。
- **AWS Trainium3**:8 个 NeuronCore(每个 = Tensor Engine + vector + scalar 三种 unit);没有硬件管理的 cache 层级,SBUF/PSUM 是软件管理的 SRAM——**tile 划分在 NVIDIA 上是优化,在 Trainium 上是必需(不划分就根本不动)**;NeuronLink + NeuronSwitch 互联,EFA 网卡,NKI 写 kernel,vLLM 有 Neuron 插件。

结论:"按硬件查 backend 表"这件事不是 NVIDIA 特产,是"算子 × 硬件"这套结构的必然产物——换任何一家厂商,表的结构不变,每一格换名字。

## 10 这套讲法为什么好

把九节摊开,会发现全视频没有一处超出三栏:

| 栏 | 问的问题 | 本文的例子 |
|---|---|---|
| **实际问题** | 系统在哪里疼? | decode 每步 18.5ms 在搬权重;2 token/专家点不亮 132 个 SM;exp 16/cycle 拖住 8192 FMA/cycle;每层等一次 CPU 拷贝 |
| **硬件条件** | 这一代硬件给了什么、没给什么 | 989 万亿次 vs 4.8TB/s vs 50GB/s 的三级带宽;TMA / wgmma 有没有;block scaling 有没有;SMEM 228KB |
| **代码写法** | 于是代码长成什么样 | tile 128×128;grouped GEMM 一次 launch;CUDA core 补 scale;JIT 固化形状;FP8 先压再寄;IBGDA |

视频自己的一句话总结:**每一个 backend = 一类算子的计算特点 × 一代硬件的瓶颈**。

这张三栏表不是事后总结,是事前推导。看到一个新算子,先问它每个输出元素要搬多少字节、做多少次运算(对照 §6 的 206 预判瓶颈),再问这一代硬件缺什么,最后才读代码——代码里每个怪形状(为什么 grouped、为什么 tile 是 128、为什么要 JIT、为什么两种 core 接力)都能反推回前两栏。反过来拿它看新论文也有效:只解决当代硬件缺席的优化(比如 Hopper 上 CUDA core 补 scale),大概率被下一代硬件吞掉;解决算子本身矛盾的(tile 不落 HBM、发送前压缩),会活过好几次换代。

套到我们自己的栈上:

- 我们的 dsv41 Q2 栈:decode 带宽瓶颈 → 把每卡专家权重压到约 35.6GiB/卡,就是"省搬运"同一招的更激进版本(2 字头 bpw);我们 decode trace 里每步毫秒级的 allreduce 开销,就是 §4.2 通信列的成本。见[量化解剖系列](/quant-anatomy-1-elvez-gguf/)四篇与[三基线横评](/dsv41-three-quant-baselines/)。
- FA3 / DeepGEMM / DeepEP 这套 Hopper 三件套在我们 H800 上同样成立:H800 与 H200 同为 sm90,瓶颈算术同构(NVLink 带宽规格有差异,但"带宽瓶颈"的定性不变)——这也是为什么这套框架对我们不是科普,是工程地图。

## 参考与来源

- 视频本体:前滩猿神《90 分钟讲透 AI Infra》第 9 集《从一条推理命令,看懂 AI Infra 硬件与生态》,B 站 [BV1Wgnp64E6e](https://www.bilibili.com/video/BV1Wgnp64E6e),2026-10-22 发布。本文全部幻灯片截图出自该视频,版权归原作者所有(视频页标注"未经作者授权,禁止转载",本文按学习笔记引用并注明出处)。
- sglang 文档与源码(`--attention-backend` / `--moe-runner-backend` / `--moe-a2a-backend` 的取值表)
- DeepSeek-V3 技术报告(Hopper FP8 累加精度);DeepSeek-V4-Flash `config.json`(fp4/e4m3/ue8m0/block size)
- FlashAttention-3 论文(FA2 35% / FA3 75% 利用率);DeepGEMM、DeepEP 开源仓库
- NVIDIA H200 / B200 公开规格;OCP MX 规范(MXFP4)
- 本博客相邻:[量化解剖 ① ELVEZ GGUF](/quant-anatomy-1-elvez-gguf/) · [② EXL3](/quant-anatomy-2-exl3/) · [③ Xolotl](/quant-anatomy-3-xolotl-xq/) · [④ H800 benchmark](/quant-anatomy-4-h800-benchmark/) · [三基线横评](/dsv41-three-quant-baselines/) · [LLM 量化五年血统图](/llm-quantization-five-lineages/)
- 内部 H800 trace:本团队实测记录,集群标识不写入此文
