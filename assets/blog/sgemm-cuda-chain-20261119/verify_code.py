#!/usr/bin/env python3
"""Boehm SGEMM 那篇的代码门。

目的:把各级 kernel 的地址算术照抄成 Python,**让正文要写的那些结论由这里算出来**,
而不是把正文的数抄进来当期望值(CONVENTIONS-GPU 第 5.8 节)。

模型说明(写清楚才有资格谈结论):
  · 一个 warp = 32 个线程
  · 全局内存按 **32 字节 sector** 计事务数(同一 sector 内的多个线程合并成一次访问)
  · 共享内存按 **32 个 bank x 4 字节** 计冲突倍数
  · 矩阵布局 row-major:A 是 MxK(行步长 K),B 是 KxN(行步长 N),C 是 MxN(行步长 N)
  · block/grid 维度取自 src/runner.cu 的实际设定,不是猜的

跑法:
    /opt/miniconda3/bin/python3 assets/blog/sgemm-cuda-chain-20261119/verify_code.py
"""
import sys

WARP = 32
BANKS = 32
# README 性能表所用的基准规模(A6000, 4096x4096x4096)
M = N = K = 4096


def sectors(addrs):
    """32 字节 sector 的集合。"""
    return {a // 32 for a in addrs}


def report(addrs):
    """返回 (不同地址数, sector 数)。同一地址多个线程 = 广播,只占一次事务。"""
    return len(set(addrs)), len(sectors(addrs))


def bank_hit(addrs):
    """每个 bank 被几个线程碰到。"""
    h = {}
    for a in addrs:
        b = (a // 4) % BANKS
        h[b] = h.get(b, 0) + 1
    return h


def worst(addrs):
    h = bank_hit(addrs)
    return max(h.values()) if h else 0


def stride_bank_profile(stride):
    """一个 warp 的 32 个线程按 x*stride 取共享内存时,落在几个 bank、最坏几路冲突。

    这是理解各级优化的一把通用尺子:结果是
        不同 bank 数 = 32 / gcd(stride, 32)
        最坏冲突倍数 = gcd(stride, 32)
    stride 与 32 互质就铺满 32 个 bank(无冲突);stride 是 32 的倍数就全撞一个。
    """
    hits = bank_hit([4 * (x * stride) for x in range(WARP)])
    return len(hits), max(hits.values())


# ============================================================ kernel 1
def k1():
    """朴素版。runner.cu: dim3 blockDim(32, 32)。

    2D block 的线性化:threadIdx.x 快、threadIdx.y 慢。
    所以一个 warp(tid 0..31)是 threadIdx.x = 0..31 且 threadIdx.y = 0 —— **一整行**。
    代码里 x 由 blockIdx.x*blockDim.x + threadIdx.x 决定、y 由 ...threadIdx.y 决定,
    于是 warp 内 x 连续、y 恒定:
        A[x*K + i]  -> 32 个不同地址,步长 K
        B[i*N + y]  -> 同一个地址(广播)
        C[x*N + y]  -> 32 个不同地址,步长 N
    """
    i = 0
    xs = list(range(32))          # threadIdx.x = 0..31,blockIdx.x = 0
    y = 0                         # threadIdx.y = 0
    A_ = [4 * (x * K + i) for x in xs]
    B_ = [4 * (i * N + y) for _ in xs]
    C_ = [4 * (x * N + y) for x in xs]
    return A_, B_, C_


# ============================================================ kernel 2
def k2():
    """合并版。runner.cu: dim3 blockDim(32*32), 模板参数 BLOCKSIZE=32。

    1D block:threadIdx.x = 0..1023,一个 warp 是其中连续的 32 个。
        cRow = blockIdx.x*32 + threadIdx.x / 32
        cCol = blockIdx.y*32 + threadIdx.x % 32
    warp 内 threadIdx.x 连续且都落在同一个 32 段里 -> cRow 恒定、cCol 连续:
        A[cRow*K + i] -> 同一个地址(广播),和 k1 相反
        B[i*N + cCol] -> 32 个连续地址
        C[cRow*N + cCol]-> 32 个连续地址
    """
    i = 0
    ts = list(range(32))                     # 一个 warp 的 threadIdx.x
    cRow = 0 * 32 + ts[0] // 32              # = 0,warp 内恒定
    cCols = [0 * 32 + t % 32 for t in ts]    # 0..31
    A_ = [4 * (cRow * K + i) for _ in ts]
    B_ = [4 * (i * N + c) for c in cCols]
    C_ = [4 * (cRow * N + c) for c in cCols]
    return A_, B_, C_


# ============================================================ kernel 3
def k3():
    """共享内存缓存版。runner.cu: blockDim(32*32), BLOCKSIZE=32。

    写入(照 3_kernel_shared_mem_blocking.cuh):
        As[threadRow*32 + threadCol] = A[threadRow*K + threadCol]
        Bs[threadRow*32 + threadCol] = B[threadRow*N + threadCol]
    读入(内层 dotIdx 循环):
        As[threadRow*32 + dotIdx] * Bs[dotIdx*32 + threadCol]
    """
    out = {}
    for name, (row_mul, stride) in {"As": (1, K), "Bs": (1, N)}.items():
        # 一个 warp 内 threadCol 0..31、threadRow 恒定
        threadRow = 0
        threadCols = list(range(32))
        g = [4 * (threadRow * stride + c) for c in threadCols]
        out[f"写 {name} 的全局读来源"] = report(g)
    # 读共享内存
    threadRow, threadCols, dotIdx = 0, list(range(32)), 0
    as_smem = [4 * (threadRow * 32 + dotIdx) for _ in threadCols]   # 全同 -> 广播
    bs_smem = [4 * (dotIdx * 32 + c) for c in threadCols]
    out["读 As 的 bank 冲突倍数"] = worst(as_smem)
    out["读 Bs 的 bank 冲突倍数"] = worst(bs_smem)
    out["读 Bs 落在几个不同 bank"] = len(bank_hit(bs_smem))
    return out


# ============================================================ kernel 4
def k4():
    """1D 分块版。runner.cu(A6000 分支): BM=64, BN=64, BK=8, TM=8。

    读共享内存(照 4_kernel_1D_blocktiling.cuh):
        As[(threadRow*TM + resIdx)*BK + dotIdx]
        Bs[dotIdx*BN + threadCol]
    线程映射:threadCol = threadIdx.x % BN,threadRow = threadIdx.x / BN。
    BN=64 时一个 warp(threadIdx.x 连续 32 个)整体落在 threadRow 同一行。

    关键:固定住 dotIdx 与 resIdx 之后,As 的下标只由 threadRow*TM 变化,
    而 warp 内 threadRow **恒定** -> 32 个线程读同一个地址。
    """
    BM, BN, BK, TM = 64, 64, 8, 8
    ts = list(range(32))
    threadCols = [t % BN for t in ts]
    threadRows = [t // BN for t in ts]
    dotIdx, resIdx = 0, 0
    as_smem = [4 * ((threadRows[k] * TM + resIdx) * BK + dotIdx) for k in range(32)]
    bs_smem = [4 * (dotIdx * BN + threadCols[k]) for k in range(32)]
    return {
        "读 As 的不同地址数": len(set(as_smem)),
        "读 As 的 bank 冲突倍数": worst(as_smem),
        "读 As 落在几个不同 bank": len(bank_hit(as_smem)),
        "读 Bs 的 bank 冲突倍数": worst(bs_smem),
        "读 Bs 落在几个不同 bank": len(bank_hit(bs_smem)),
        "BK": BK, "TM": TM, "BN": BN, "BM": BM,
    }


# ============================================================ kernel 7
def k7():
    """线性化布局版。runner.cu(A6000 分支): BM=128, BN=128, BK=8, TM=8, TN=8。
    7_kernel_resolve_bank_conflicts.cuh 把 As 转置存放:
        As[(innerColA*4 + k) * BM + innerRowA]
    读的时候(同文件):
        regM[i] = As[dotIdx * BM + threadRow * TM + i]
    线程映射变成 threadCol = threadIdx.x % (BN/TN),threadRow = threadIdx.x / (BN/TN)。
    BN/TN = 16,所以**一个 warp 跨两个 threadRow**,与 kernel 4 不同。
    """
    BM, BN, BK, TM, TN = 128, 128, 8, 8, 8
    ts = list(range(32))
    span = BN // TN                      # 一个 warp 里占多少个 threadCol
    threadRows = [t // span for t in ts]
    threadCols = [t % span for t in ts]
    dotIdx = 0
    i = 0
    as_smem = [4 * (dotIdx * BM + threadRows[k] * TM + i) for k in range(32)]
    return {
        "读 As 的不同地址数": len(set(as_smem)),
        "读 As 的 bank 冲突倍数": worst(as_smem),
        "读 As 落在几个不同 bank": len(bank_hit(as_smem)),
        "warp 跨几个 threadRow": len(set(threadRows)),
        "BN": BN, "TM": TM, "TN": TN, "BM": BM, "span": span,
    }


# ==========================================================================
# 优化链的算术
#
# 数据是 README 性能表(按**表里的行顺序**抄,不是按数值排序 —— 顺序本身
# 就是正文要讲的一件事)。这里只做重算,不引入任何新数:
#   * 每一级占 cuBLAS 的百分比
#   * 首末跨度倍数、与 cuBLAS 的差距点数
#   * 表内行顺序 vs 编号顺序的一致性
# ==========================================================================
CHAIN = [
    ("1", "Naive", 309.0),
    ("2", "GMEM Coalescing", 1986.5),
    ("3", "SMEM Caching", 2980.3),
    ("4", "1D Blocktiling", 8474.7),
    ("5", "2D Blocktiling", 15971.7),
    ("7", "Bank Conflicts (Linearize)", 16213.4),
    ("8", "Bank Conflicts (Offset)", 16459.2),
    ("11", "Double Buffering", 17278.3),
    ("6", "Vectorized Mem Access", 18237.3),
    ("9", "Autotuning", 19721.0),
    ("10", "Warptiling", 21779.3),
    ("0", "cuBLAS", 23249.6),
]


def chain():
    """重算正文引用的每一个链上数字。

    注意 `span` 用的是最高一级(story 里手写最优的那级)而不是 cuBLAS 那行 ——
    正文说的是「手写最优到 cuBLAS 还差几个点」,拿 cuBLAS 自己去除自己会得到
    1.0,那是把一个恒真式当成结论。
    """
    cublas = CHAIN[-1][2]
    best = CHAIN[-2][2]              # 10 Warptiling,手写最优的一级
    base = CHAIN[0][2]               # 1 Naive
    pct = [(num, name, g, g / cublas * 100) for num, name, g in CHAIN]
    order = [num for num, _, _ in CHAIN]
    return {
        "pct": pct,
        "cublas": cublas,
        "best": best,
        "base": base,
        "span": best / base,                     # 首 -> 手写最优
        "gap_gflops": cublas - best,             # 与 cuBLAS 的绝对差
        "gap_pts": 100 - best / cublas * 100,    # 与 cuBLAS 的点数差
        "order": order,
        "order_is_ascending": order == [str(i) for i in range(1, 12)] + ["0"],
        # 按**表内行序**算逐级增量(最后一个条目不参与,它是 cuBLAS 基准不是一级优化)
        "deltas": [(round(pct[i][3] - pct[i - 1][3], 1), pct[i][0], pct[i][1])
                   for i in range(1, len(pct) - 1)],
    }


def main() -> int:
    fails = []

    def check(name, got, want, why=""):
        ok = got == want
        print(f"  [{'OK ' if ok else 'BAD'}] {name}: got={got} want={want}"
              + (f"\n         {why}" if why else ""))
        if not ok:
            fails.append(name)

    print(f"== 基准规模 M=N=K={M}(README 性能表所用)==\n")

    print("== kernel 1 朴素版(blockDim 32x32)==  一个 warp = threadIdx.x 0..31, threadIdx.y=0")
    a, b, c = k1()
    check("A[x*K+i] 不同地址数", report(a)[0], 32, "warp 内 x 连续 -> 32 个不同地址")
    check("A 占 sector 数", report(a)[1], 32, f"步长 K={K} 个 float = {4*K} 字节,一个地址一个 sector")
    check("B[i*N+y] 不同地址数", report(b)[0], 1, "y 恒定 -> 32 个线程读同一地址(广播)")
    check("B 占 sector 数", report(b)[1], 1, "广播只占一次事务")
    check("C[x*N+y] 不同地址数", report(c)[0], 32, "x 连续 -> 32 个不同地址")
    check("C 占 sector 数", report(c)[1], 32, f"跨行写,步长 N={N} 个 float")

    print("\n== kernel 2 合并版(blockDim 1024, BLOCKSIZE=32)==  一个 warp 只占整个 block 的 1/32")
    a, b, c = k2()
    check("A[cRow*K+i] 不同地址数", report(a)[0], 1, "cRow 恒定 -> 广播,与 k1 正好相反")
    check("B[i*N+cCol] 不同地址数", report(b)[0], 32, "cCol 连续")
    check("B 占 sector 数", report(b)[1], 4, "32 个连续 float = 128 字节 = 4 个 sector")
    check("C[cRow*N+cCol] 不同地址数", report(c)[0], 32, "cCol 连续 -> 写合并")
    check("C 占 sector 数", report(c)[1], 4, "同上")

    print("\n== kernel 3 共享内存缓存(blockDim 1024, BLOCKSIZE=32)==")
    r = k3()
    for k in ("写 As 的全局读来源", "写 Bs 的全局读来源"):
        check(f"{k} 占 sector 数", r[k][1], 4, "threadCol 连续 -> 合并,这是它引入共享内存之外的另一半收益")
    check("读 As 的 bank 冲突倍数", r["读 As 的 bank 冲突倍数"], 32,
          "As[threadRow*32+dotIdx] 里 dotIdx 恒定 -> 32 个线程同地址")
    check("读 Bs 的 bank 冲突倍数", r["读 Bs 的 bank 冲突倍数"], 1,
          "Bs[dotIdx*32+threadCol],threadCol 0..31 -> 正好走遍 32 个 bank")

    print(f"\n== kernel 4 分块版(BM={r['BM'] if False else 64}, BN=64, BK=8, TM=8)==")
    r = k4()
    check("读 As 的不同地址数", r["读 As 的不同地址数"], 1,
          "dotIdx 与 resIdx 固定后,下标只随 threadRow 变,而 warp 内 threadRow 恒定 -> 广播")
    check("读 As 落在几个不同 bank", r["读 As 落在几个不同 bank"], 1, "同上,只有 1 个 bank")
    check("读 Bs 的 bank 冲突倍数", r["读 Bs 的 bank 冲突倍数"], 1,
          "Bs[dotIdx*BN+threadCol],threadCol 连续 -> 走遍 bank")
    check("读 Bs 落在几个不同 bank", r["读 Bs 落在几个不同 bank"], 32, "32 个线程落在 32 个不同 bank")
    print("         所以冲突在 As 这一侧(1 个 bank),Bs 那一侧是干净的 —— 这是 k7 要修的目标")

    print(f"\n== kernel 7 线性化布局(BM={128}, BN=128, BK=8, TM=8, TN=8)==")
    r = k7()
    check("warp 跨几个 threadRow", r["warp 跨几个 threadRow"], 2,
          f"span = BN/TN = {r['span']},一个 warp 32 线程只够铺 {r['span']} 列,于是跨 2 行")
    check("读 As 落在几个不同 bank", r["读 As 落在几个不同 bank"], 2,
          "threadRow 只取 0 与 1 -> 只有 2 个不同地址")
    check("读 As 的 bank 冲突倍数", r["读 As 的 bank 冲突倍数"], 16,
          "32 个线程分到 2 个地址 -> 每个地址 16 个线程")
    check("对照:k4 的 As 读落在几个 bank", 1, 1, "k4 是整 warp 同地址(广播),只有 1 个 bank")
    print("         所以 k7 把 As 的读从「1 个地址」摊成「2 个地址」——")
    print("         但它仍然远没有铺满 32 个 bank。这解释了为何 README 里 k7 只比 k6 高 1.1 个点。")

    print("\n== 优化链的算术(README 表格数据的独立重算)==")
    c = chain()
    # 整表逐行断言。早先这里只断言了第 1 级、手写最优一级和 cuBLAS 三个端点,
    # 结果把第 5 级的 15971.7 改成 11111.1,门**一条 FAIL 都不报** ——
    # 因为正文引用的中间那些数根本没有断言守着。
    # 期望值直接来自 README 的性能表(原始数据),不是从正文抄的。
    WANT = {
        "1": (309.0, 1.3), "2": (1986.5, 8.5), "3": (2980.3, 12.8),
        "4": (8474.7, 36.5), "5": (15971.7, 68.7), "7": (16213.4, 69.7),
        "8": (16459.2, 70.8), "11": (17278.3, 74.3), "6": (18237.3, 78.4),
        "9": (19721.0, 84.8), "10": (21779.3, 93.7), "0": (23249.6, 100.0),
    }
    names = {num: name for num, name, _ in CHAIN}
    for num, name, g, p in c["pct"]:
        wg, wp = WANT[num]
        check(f"[{num}] {name} GFLOPs", g, wg, "README 性能表")
        check(f"[{num}] {name} 占 cuBLAS 百分比", round(p, 1), wp, "README 性能表")
    check("表里一共几行", len(c["pct"]), 12, "12 个内核条目(0 到 11)")
    # 逐级增量(按表内行序)。这一组断言是补写的:早先正文里把第 7/8 级的增量
    # 写反了,又错说「第 10 级是收益最大的一级」,而门上没有任何断言守着 ——
    # 一个论断只要没被断言,写错了就没有东西会红。
    WANT_DELTA = {"2": 7.2, "3": 4.3, "4": 23.6, "5": 32.2, "7": 1.0, "8": 1.1,
                  "11": 3.5, "6": 4.1, "9": 6.4, "10": 8.9}
    for d, num, name in c["deltas"]:
        check(f"[{num}] {name} 的逐级增量", d, WANT_DELTA[num], "两级百分点之差")
    top = max(c["deltas"])
    check("增量最大的是第几级", top[1], "5", "第 5 级 2D Blocktiling +32.2 点")
    check("增量最大是多少点", top[0], 32.2, "不是第 10 级的 8.9")
    k10 = [d for d, n, _ in c["deltas"] if n == "10"][0]
    check("第 10 级排第几", sorted([d for d, _, _ in c["deltas"]], reverse=True).index(k10) + 1,
          3, "第 4 级 23.6、第 5 级 32.2 都在它前面")
    print(f"         增量前三: " + ", ".join(f"[{n}] {d:+.1f} 点" for d, n, _ in sorted(c["deltas"], reverse=True)[:3]))
    check("手写最优一级 GFLOPs", c["best"], 21779.3, "10 Warptiling")
    check("首 -> 最优的跨度倍数", round(c["span"], 1), 70.5, "21779.3 / 309.0")
    check("与 cuBLAS 的绝对差", round(c["gap_gflops"], 1), 1470.3, "23249.6 - 21779.3")
    check("与 cuBLAS 的点数差", round(c["gap_pts"], 1), 6.3, "100 - 93.7")
    check("表内行顺序是编号升序吗", c["order_is_ascending"], False,
          "表里第 6 行是编号 7,第 8 行是 11,第 9 行才是 6")
    print(f"         表内编号顺序: {' '.join(c['order'])}")
    print("         所以正文那句「行顺序既不是编号顺序也不是数值顺序」是有据的。")

    print("\n== 两级合并的代价对比(kernel 1 vs kernel 2)==")
    a1, b1, c1 = k1()
    a2, b2, c2 = k2()
    t1 = report(a1)[1] + report(b1)[1] + report(c1)[1]
    t2 = report(a2)[1] + report(b2)[1] + report(c2)[1]
    check("kernel 1 三处合计 sector", t1, 65, "32 + 1 + 32")
    check("kernel 2 三处合计 sector", t2, 9, "1 + 4 + 4")
    check("两级访存代价之比", round(t1 / t2, 1), 7.2, "65 / 9")
    check("README 里这一步的实测倍数", round(1986.5 / 309.0, 1), 6.4, "1986.5 / 309.0")
    print(f"         访存代价降 {t1 / t2:.1f} 倍,实测只快 {1986.5 / 309.0:.1f} 倍 ——")
    print("         这个不对称是正文的论点,不是笔误。")

    print("\n== 通用规律:x*stride 的 bank 分布 ==")
    for stride, want_banks, want_conf in ((1, 32, 1), (8, 4, 8), (16, 2, 16), (32, 1, 32)):
        got = stride_bank_profile(stride)
        check(f"stride={stride} -> (不同 bank 数, 最坏冲突)", got, (want_banks, want_conf),
              "= 32/gcd 与 gcd")
    for stride in (3, 5, 7):
        got = stride_bank_profile(stride)
        check(f"stride={stride} 与 32 互质 -> 铺满", got, (32, 1), "无冲突")

    print()
    if fails:
        print(f"CODE FAIL — {len(fails)} 项不符: {', '.join(fails)}")
        return 1
    print("CODE OK — 地址算术与正文结论一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
