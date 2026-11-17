#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把这篇的两个数字来源都钉死,然后独立重算所有派生量。

这篇和同系列的上一篇(`nsight-bogus-copies`)在数字纪律上有一处根本区别:

  上一篇的每个数字都来自我自己跑出来的日志,所以门可以「从原始数据重算」,
  重算结果和正文对不上就是错。

  这一篇我没有跑任何实验。所有性能数字都是**引用**别人的,所以「重算」
  这条路走不通 —— 我能验的只有两件事:

    1. 引文是不是**逐字**存在(不是我记得的样子,是材料里真有的样子)
    2. 材料自己给的算术是不是**自洽**(幻灯片 p13 那串 cycle 推导,
       以及 p20 的 tile 数),这个可以脱离硬件独立算

第 2 条不是走过场:第一遍读材料时我把幻灯片 p13 的 3072 cycles 当成
「大概是凑的」,重算之后发现四个数连比值都精确吻合 —— 这类推导是整场
演讲唯一可以不带硬件就站住的部分,值得单独讲一节。

跑法:
    /opt/miniconda3/bin/python3 assets/blog/fa3-cutlass-mainloop-20261115/fa3_facts.py
"""

from __future__ import annotations

import hashlib
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLIDES = HERE / "data" / "slides-text.txt"
PAPER = HERE / "data" / "paper-abstract.txt"
UPSTREAM = HERE / "upstream"

# 每条 = (出现在正文哪一节, 引文, 必须在哪个材料里逐字找到)
#
# 引文一律用**材料里的原话**,包括它的措辞习惯。改写过的句子不放这里 ——
# 那样只是拿门去验我自己写的东西,验不出材料。
CITATIONS: list[tuple[str, str, str]] = [
    # ---- 幻灯片:性能数字 ----
    ("§1", "Upshot: 1.6-3x speedup", "slides"),
    ("§1", "BF16 Benchmark: 1.6-2.0x speedup", "slides"),
    ("§4", "BF16 Benchmark: reach up to 850 TFLOPS", "slides"),
    ("§4", "FP8 Benchmark: up to 1.3 PFLOPS", "slides"),
    ("§2", "Pingpong scheduling using synchronization barriers (with bar.sync):", "slides"),
    ("§2", "580 TFLOPS -> 640 TFLOPS", "slides"),
    ("§2", "2-stage pipelining: 640 TFLOPS -> 670 TFLOPS (but higher register pressure)", "slides"),

    # ---- 幻灯片:算术与约束 ----
    ("§2", "MUFU.EX2 takes 50% the cycles of WGMMA!", "slides"),
    ("§2", "FP8 is even worse: WGMMA and EX2 both take 1536 cycles.", "slides"),
    ("§1", "FP8 doubles WGMMA throughput, but trade off accuracy", "slides"),
    # p11 是左右两栏。pdftotext 按行拼,左栏这句话被右栏文字从中间劈开:
    #     wgmma necessary, mma.sync can   TMA: accelerate gmem ->   only reach 2/3 peak throughput
    #                                                   smem, saves registers
    # 所以整句在文字层里**不连续**,任何「去掉空格再比」的做法都救不回来
    # (试过,不行:空格没了之后右栏文字会插进句子中间)。拆成两段各自核对,
    # 正文里也用省略号标明中间被别的文字隔开了 —— 不假装它是一整行。
    ("§1", "wgmma necessary", "slides"),
    ("§1", "only reach 2/3 peak throughput", "slides"),
    ("§1", "FA2 only gets to 35-40% utilization (no WGMMA, no TMA)", "slides"),

    # ---- 幻灯片:FP8 layout ----
    ("§4", "requires operand SMEM tensors to be memory-contiguous in the inner dimension (k-major)", "slides"),
    ("§4", "It is standard for QKV to be memory-contiguous in the head dimension (BSHD).", "slides"),
    # 材料用的是弯引号 U+2019,不是直角撇号。引文以材料为准,包括标点。
    ("§4", "Note: TMA can\u2019t change the contiguous mode.", "slides"),
    ("§4", "FP32 accumulator layout differs from FP8 operand A layout.", "slides"),
    ("§4", "Uses LDSM/STSM instructions with custom layouts and byte permute in-between.", "slides"),

    # ---- 幻灯片:持久化 ----
    ("§4", "Decouple physical CTAs from logical work tiles, launching fixed number of CTAs.", "slides"),
    ("§4", "With persistent kernel on H100 SXM5 GPU, launch 132 CTAs = num SMs.", "slides"),

    # ---- 幻灯片:CUTLASS 结构 ----
    ("§4", "CollectiveMainloop for load and mma.", "slides"),
    ("§4", "CollectiveEpilogue for store.", "slides"),
    ("§4", "TileScheduler to manage work loop for persistent kernel.", "slides"),

    # ---- 幻灯片:作者与出处 ----
    ("§2", "Jay Shah*, Ganesh Bikshandi*, Ying Zhang, Vijay Thakkar, Pradeep Ramani, Tri Dao", "slides"),

    # ---- 论文摘要:与幻灯片**不同**的那一组数 ----
    # 这一组是全文的重点之一:同一个工作,论文(v2, 2024-07)和幻灯片(2024-11)
    # 报的数字不一样。两条都必须能逐字找到,否则「数字变了」这个说法就站不住。
    ("§5", "with FlashAttention-2 achieving only 35% utilization on the H100 GPU", "paper"),
    ("§5", "achieves speedup on H100 GPUs by 1.5-2.0x with FP16 reaching up to 740 TFLOPs/s (75% utilization)", "paper"),
    ("§5", "and with FP8 reaching close to 1.2 PFLOPs/s", "paper"),
    ("§5", "achieves 2.6x lower numerical error than a baseline FP8 attention", "paper"),
]

# 四张基准图页(p21-p24)的说明文字。这几个数字是文章**唯一**能引用的
# 性能数字,而它们对应的曲线一张都看不到 —— 所以说明文字本身必须钉住。
# 负对照里试过把 p24 的说明删掉:「这页没有正文」那个判据依然是成立的
# (只剩页码,照样算短页),门就没红。补上这一条才关得住。
BENCHMARK_CAPTIONS = {
    21: "BF16 Benchmark: 1.6-2.0x speedup",
    22: "BF16 Benchmark: reach up to 850 TFLOPS",
    23: "FP8 Benchmark: up to 1.3 PFLOPS",
    24: "BF16 Decode Benchmark for MQA. Lower is better!",
}

# upstream/ 里钉住的文件与它们的 SHA-256。这些是我下载的**上游只读副本**,
# 文章里引的每一段代码都必须能在这几个文件里按行号找到。
EXPECTED_SHA256 = {
    "mainloop_fwd_sm90_tma_gmma_ws.hpp":
        "d8f7bef971566efeda21dc8feadc2c56d3db258def2dbc6a0d3e8a3ab26b5f0e",
    "named_barrier.hpp":
        "35206d7ff0375bd5fcde0a7af9a9fd86f6c673e5fc7d8dcde21ef32cea65072e",
    "tile_scheduler.hpp":
        "2e01e49b3b89014884e12842a96f1c9c021483197fbe49fea0d2dbd884778b6d",
    "softmax.h":
        "4eef1079d07c9620eef8cadd55527e6d58b15400f83cacafabe9413936800da7",
}

BAD: list[int] = []


def norm(s: str) -> str:
    """把空白压成单空格。

    pdftotext 会在字符之间插空格(幻灯片里那行作者名单抽出来是
    `Jay  Shah*,  Ganesh  Bikshandi*, ...`),所以逐字比对前必须归一化空白。
    归一化的是**空白**,不是标点也不是大小写 —— 那两样变了就是真变了。
    """
    return re.sub(r"\s+", " ", s).strip()


def squash(s: str) -> str:
    """归一化空白并**去掉空格**。

    写这个函数本来是想核对 p11 那句被拆开的引文,结果发现救不回来:
    pdftotext 是按行拼的,右栏文字会插进左栏句子的中间,去掉空格之后
    插进来的字反而粘得更紧。留着它是因为下面 check_citations 的失败信息
    会用到,顺便记下这条走不通的路。
    """
    return norm(s).replace(" ", "")


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok   {label}")
        BAD.append(0)
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        BAD.append(1)


def check_citations(slides: str, paper: str) -> None:
    print("引文是否逐字存在")
    n_s, n_p = norm(slides), norm(paper)
    for where, quote, src in CITATIONS:
        hay = n_s if src == "slides" else n_p
        # 只做「归一化空白后逐字」一种比对。试过放宽(去掉空格),结果是
        # 把右栏文字插进左栏句子的情况也放过了,反而更不可靠。
        check(f"{where} [{src}] {quote[:58]}", norm(quote) in hay,
              "材料里找不到这句话")


def check_sha256() -> None:
    print("上游文件是否与记录一致")
    for name, want in sorted(EXPECTED_SHA256.items()):
        p = UPSTREAM / name
        if not p.exists():
            check(f"sha256 {name}", False, "文件不存在")
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        check(f"sha256 {name}", got == want, f"期望 {want[:16]}… 实际 {got[:16]}…")


def check_arithmetic() -> None:
    """幻灯片 p13 的推导,和 p20 的 tile 数,全部独立重算。

    这四条是整场演讲里唯一不用 H100 也能判对错的数字。
    """
    print("材料自给的算术是否自洽")

    # p13: FP16 WGMMA 的 cycle 数
    # 原文 "2 x 2 x 128 x 192 x 128 = 12.6 MFLOPS, 4096 FLOPS/cycle -> 3072 cycles"
    wgmma_flop = 2 * 2 * 128 * 192 * 128
    peak_fp16 = 4096
    cyc_wgmma = wgmma_flop / peak_fp16
    check("p13 2x2x128x192x128 = 12.6 M(FLOP)", abs(wgmma_flop / 1e6 - 12.6) < 0.05,
          f"实算 {wgmma_flop / 1e6:.2f}")
    check("p13 12582912 / 4096 = 3072 cycles", cyc_wgmma == 3072,
          f"实算 {cyc_wgmma}")

    # p13: MUFU.EX2 的 cycle 数
    ex2_ops = 128 * 192
    mufu_rate = 16
    cyc_ex2 = ex2_ops / mufu_rate
    check("p13 128x192 = 24.6k OPS", abs(ex2_ops / 1e3 - 24.6) < 0.05,
          f"实算 {ex2_ops / 1e3:.1f}k")
    check("p13 24576 / 16 = 1536 cycles", cyc_ex2 == 1536, f"实算 {cyc_ex2}")

    # p13: 「EX2 占 WGMMA 的 50%」和「FP8 时两者相等」
    ratio = cyc_ex2 / cyc_wgmma
    check("p13 EX2/WGMMA = 50%", abs(ratio - 0.5) < 1e-9, f"实算 {ratio:.4f}")
    cyc_wgmma_fp8 = cyc_wgmma / 2      # FP8 让 WGMMA 吞吐翻倍
    check("p13 FP8 时 WGMMA 与 EX2 都是 1536 cycles",
          cyc_wgmma_fp8 == 1536 and cyc_ex2 == 1536,
          f"FP8 WGMMA {cyc_wgmma_fp8}, EX2 {cyc_ex2}")

    # p20: 持久化 kernel 的 work tile 数
    seqlen, heads, batch, block_m = 4096, 8, 4, 128
    mblocks = seqlen // block_m
    tiles = mblocks * heads * batch
    check("p20 mblocks = 4096/128 = 32", mblocks == 32, f"实算 {mblocks}")
    check("p20 32*8*4 = 1024 work tiles", tiles == 1024, f"实算 {tiles}")
    # 132 个 CTA 分摊 1024 个 tile
    check("p20 1024 tiles / 132 CTA > 1", tiles / 132 > 1,
          f"实算 {tiles / 132:.2f} tile/CTA")

    # FP8 吞吐翻倍这个前提本身
    check("FP8 相对 FP16 的 WGMMA 吞吐翻倍(前提)", peak_fp16 * 2 == 8192,
          "只是复述材料的前提,不是我对硬件的断言")


def check_slide_coverage() -> None:
    """确认 27 页都读到了,并且**承认**有九页读不到内容。

    这不是解析失败,是材料本身的性质。九页分两类:

      - p1 标题页、p4/p8/p12/p16 四张算法图(循环结构、tile 走位全在图里)
      - p21-p24 四张基准图。这四页最值得说:它们的**标题**恰好含一个数字
        (1.6-2.0x、850 TFLOPS、1.3 PFLOPS),所以文字层里「有一个数字」,
        但坐标轴、曲线、测试配置全在图里。结果是这几个数字**能引用、
        不能核对** —— 文章里必须这么写,不能因为看得见就当成验过。

    这一条把上面的判断变成可检查的:哪天 pdftotext 换了版本、把图里的
    文字读出来了,或者反过来连标题都读不到了,它都会响。
    """
    print("幻灯片逐页覆盖")
    pages = [p for p in SLIDES.read_text(encoding="utf-8").split("\f") if p.strip()]
    check("幻灯片解析出 27 页正文", len(pages) == 27, f"实得 {len(pages)}")

    # 一页去掉页码之后,如果剩下的行都是短行,就算「文字层里没有正文」。
    # 上界取 50 字符,是因为 p21-p24 那四张基准图的说明文字最长到 47 字符
    # (`BF16 Decode Benchmark for MQA. Lower is better!`);再放宽就会把真有
    # 正文的页卷进来(p20 有 598 字符)。
    title_only: list[int] = []
    for i, page in enumerate(pages, 1):
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        while lines and lines[-1].isdigit():      # 去掉页码
            lines.pop()
        if lines and all(len(ln) < 50 for ln in lines) and len(lines) <= 4:
            title_only.append(i)

    check("文字层里没有正文的页 = 标题页 + 4 张算法图 + 4 张基准图",
          title_only == [1, 4, 8, 12, 16, 21, 22, 23, 24],
          f"实得 {title_only}")
    check("即 27 页里 9 页的正文读不到(三分之一)",
          len(title_only) == 9, f"实得 {len(title_only)}")

    # 基准图页的说明文字必须逐页对上。这几行是文章引用性能数字的唯一依据,
    # 而它们指向的曲线在图里、读不到 —— 所以说明文字丢了必须响。
    for pg, want in sorted(BENCHMARK_CAPTIONS.items()):
        got = norm(pages[pg - 1])
        check(f"p{pg} 的说明文字还在", want in got,
              f"该页文字层里找不到: {want}")


def main() -> int:
    if not SLIDES.exists() or not PAPER.exists():
        print(f"缺材料: {SLIDES} 或 {PAPER}")
        return 1
    slides = SLIDES.read_text(encoding="utf-8")
    paper = PAPER.read_text(encoding="utf-8")

    check_citations(slides, paper)
    check_sha256()
    check_arithmetic()
    check_slide_coverage()

    total = sum(BAD)
    if total:
        print(f"\nfacts problem(s): {total}")
        return 1
    print(f"\nfacts problem(s): 0   ({len(CITATIONS)} 条引文 / "
          f"{len(EXPECTED_SHA256)} 个上游文件 / 13 项重算)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
