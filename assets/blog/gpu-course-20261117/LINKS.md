# 课程序列：入口核验记录

核验日期：2026-11-17（Asia/Hong_Kong）。核验人：作者本人。

**这份记录回答的问题**：`/courses/` 那条序列里每个外部入口，我到底核到了哪一层。

**它不回答的问题**：这些材料讲得好不好、是否完整覆盖了某个主题、视频里具体讲了什么。这些我没有逐段播放，无法判断。

## 方法

| 层 | 做法 | 能证明什么 |
|---|---|---|
| 1 可达性 | `curl -sIL` 取 HTTP 状态码 | 链接现在能打开 |
| 2 身份 | `curl -sL` 取页面，解析 `og:title` / `<title>` / 正文 | **这个入口是那一场**，不是别的内容 |
| 3 内容 | 抓正文并逐字提取关键结论或课表 | 转述与官方原文一致 |
| 4 文件 | GitHub API 取默认分支与递归文件树 | 仓库里确实有那个文件 |

第 1 层不够。**「能打开」不等于「是那一场」** —— 一个 session ID 打错一位也可能落到别的页面上，所以主入口我做到了第 2 层，凡是我在正文里写了「官方原文是……」的做到了第 3 层。

## 核到第 3 层（正文里有逐字引文或课表对照）

| 入口 | 核到的内容 |
|---|---|
| `gtc25-s72897` | 标题逐字：How To Write A CUDA Program: The Parallel Programming Edition — GTC San Jose **2025** |
| `gtc24-s62401` | 标题逐字：How To Write A CUDA Program: The Ninja Edition — GTC San Jose **2024** |
| CS149 Fall 2025 讲义目录 | 官方原文「We cannot distribute lecture videos to the public this year, but videos from a prior version of the course (2023) are available」+ 18 条讲次标题 |
| SGEMM_CUDA README | 性能表逐行抓取：11 条数据行，最高到 11 号，**没有 12 号** |
| `CONTRIBUTORS.md` | `Cris Cecka`、`Vijay Thakkar`、`Pradeep Ramani` 三人均在；`Jay Shah` 在致谢段 |
| GPU MODE lectures README | `Lecture 23: Tensor Cores`、`Lecture 36: CUTLASS and Flash ATtention 3`、`Lecture 57: CuTE`、`Lecture 114: PyCuTe` 四条标题与讲者 |
| arXiv `2603.02298` | `citation_title` = CuTe Layout Representation and Algebra；`citation_author` = Cecka, Cris；`citation_date` = 2026/03/02 |

## 核到第 2 层（标题/讲者一致，未取正文）

Colfax 四篇教程、PMPP 播放列表与频道、El Hajj 作者页、Harris 的 PDF、Kepler 更新、warp 级原语、Boehm 原文、Triton 教程目录、CS336 官网与录像、GTC 2026 Nsight Systems 场次、NVIDIA 工具视频系列、GTC 2026 Tensor Core 场次、CuTe DSL 文档、PyCuTe 仓库、CUDA 下载页、On-Demand FAQ。

全部返回 **200**。

## 核到第 4 层（文件层面）

| 目标 | 核到的 |
|---|---|
| `siboehm/SGEMM_CUDA` | 默认分支是 **`master`**（不是 `main`）；`src/kernels/` 下 `1_naive` … `12_kernel_double_buffering` **共 12 个文件齐全**；11 与 12 都是 double buffering |
| `gpu-mode/lectures` | `lecture_036`、`lecture_057`、`lecture_086`、`lecture_103`、`lecture_114` 目录**真实存在**；**`lecture_023` 不存在** |
| `NVIDIA/cutlass` | `CONTRIBUTORS.md` 可读取 |

## 没核到 / 明确不核的

| 项 | 状态 |
|---|---|
| 视频内容与讲授质量 | **没核**。没有逐段播放任何一门课 |
| 播放可用性（是否需登录） | **没核**。NVIDIA On-Demand 部分内容需要登录，页面本身公开可访问，但我没有登录测试过播放 |
| `lecture_023` 的 Slides | **没核**。它指向一份 Google Drive 文档，不是仓库目录；我核到的是讲次标题与讲者正确 |
| CS149 2023 录像与 2025 讲义的一一对应 | **没核**。只分别确认了两边存在 |
| Roofline 是否为独立讲次 | **没核**。只核了 Fall 2025 这一年的课表标题 |
| PMPP 教材内容 | **没核**。付费材料，未获取 |
| Triton 教程是否逐个可跑 | **没核**。只核了目录入口 |
| CUTLASS 版本兼容性 | **没核**。发版频繁，教程对应的版本可能与今天不同 |
| 压缩包的 SHA-256 | **不适用**。本站不下载任何上游文件，没有快照 |

## B 站入口

B 站对直接抓取返回 **HTTP 412**（反爬），所以这几条**没有做可达性核验**：

| 入口 | 我标注它是什么 |
|---|---|
| PMPP 中译课程 | 上传者引用 AUB 官方播放列表；页面列出的是部分中译，**不是全套中文课** |
| SGEMM 第三方系列 | 辅助理解的讲解；**未证明**是 Boehm 原文的逐节配套视频 |
| CS149 字幕版 | 对应 **2023** 录像，不是 2025 讲义版本的完整新录像 |
| CS336 字幕版 | 当前可见部分分段，**缺部分嘉宾课**；要完整目录请回官方课程 |

**B 站的「官方课程」「全集」字样不等于官方发布或完整收录。** 我核过的是官方目录、标题、讲者与材料入口；B 站那几条我按「民间搬运/字幕/讲解」标注，不当成已确认的完整来源。

## 免费范围

上述官方公开文章、代码和公开视频可免费访问；**PMPP 纸书/电子书本身付费**；**NVIDIA On-Demand 部分内容需要登录**，NVIDIA Developer Program 可免费注册（见 <https://www.nvidia.com/en-us/on-demand/faq/>）。

## 一处纠正记录

序列里最初流传的一句「CS149 第 2 讲是 SIMD、第 6 讲是 Roofline」与 Fall 2025 官方课表不符 —— SIMD 在第 2 讲是三种并行形式之一、不是该讲主题，第 6 讲讲的是局部性与通信。按错编号找讲义会白找。详细对照见第 2 站那篇。
