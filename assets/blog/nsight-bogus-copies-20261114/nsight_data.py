"""这组实验的**唯一数据来源**。

正文里的每个数字、每张图,都必须经过这里。规则只有一条:
**不在这里出现的数字,不准写进正文。**

为什么费这个劲:这类文章最容易出的错不是结论错,而是「跑完之后
手抄数字时抄错一位」或者「改了实验忘了改正文」。让它自动重算,
这两类错就没法发生了。

数据文件:
  data/run_434338.log        集群作业 434338 的完整 stdout
  data/trace_{good,sync,errsync}.csv
                             nsys stats --report cuda_gpu_trace 的导出

用法:
    from nsight_data import DATA, gaps, wallclock
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RUN_LOG = DATA / "run_434338.log"

MODES = ("good", "sync", "alloc", "errsync", "all")

# nsys 的特性:导出的 CSV 前面有几行进度噪声,真正的表头在 "Start (ns),"
# 那一行。不按这个切,第一行会被当成数据解析炸掉。
DATA_START = "Start (ns),"

# 小于这个宽度的间隔不算「空隙」——kernel 之间本来就有微秒级的气泡,
# 那些不是优化目标。
GAP_FLOOR_US = 1.0


# --------------------------------------------------------------- 墙钟

@dataclass
class Wall:
    mode: str
    iters: int
    n: int
    elapsed_ms: float
    per_iter_us: float
    checksum: float


def wallclock() -> dict[str, Wall]:
    """从日志第 1 节解析五种模式的墙钟时间。

    逐行解析,不用跨行正则:上面那行是
        mode=good iters=200 n=1048576 grid=4096 block=256
    —— 参数不止 n 一个,第一版把正则写成 `n=(\\d+)\\n`,后面的
    ` grid=...` 直接让整行匹配不上,报「日志里缺少这些模式」。
    """
    out: dict[str, Wall] = {}
    pending: dict[str, int] | None = None
    pat_head = re.compile(r"mode=(\w+) iters=(\d+) n=(\d+)")
    pat_body = re.compile(
        r"elapsed_ms=([\d.]+)\s+per_iter_us=([\d.]+)\s+checksum=(-?[\d.]+)")

    for line in RUN_LOG.read_text(encoding="utf-8").splitlines():
        m = pat_head.search(line)
        if m:
            pending = {"iters": int(m.group(2)), "n": int(m.group(3))}
            pending["_mode"] = m.group(1)          # type: ignore[assignment]
            continue
        b = pat_body.search(line)
        if b and pending is not None:
            mode = pending["_mode"]                # type: ignore[assignment]
            out[mode] = Wall(
                mode=mode,
                iters=pending["iters"],
                n=pending["n"],
                elapsed_ms=float(b.group(1)),
                per_iter_us=float(b.group(2)),
                checksum=float(b.group(3)),
            )
            pending = None

    missing = [m for m in MODES if m not in out]
    if missing:
        raise SystemExit(f"日志里缺少这些模式: {missing}")
    return out


# --------------------------------------------------------------- 空隙

@dataclass
class Trace:
    """一条 nsys 逐 kernel 时间线的统计结果。

    三个时间量必须分清,混起来会得出错的结论:

      busy_ms  GPU 真正在跑 kernel 的时间之和
      gap_ms   **kernel 之间**的空隙之和(>GAP_FLOOR_US 的才算)
      tail_ms  最后一个 kernel 跑完之后,到进程结束前的那段等待

    span_ms - busy_ms = gap_ms + tail_ms,这是个恒等式。
    只报 gap_ms 会漏掉尾:good 那条轨道的尾就占了大头,漏掉它
    会让人以为「good 几乎没有等待」。
    """

    mode: str
    kernels: int
    busy_ms: float          # GPU 真正在跑 kernel 的时间之和
    span_ms: float          # 首尾 kernel 之间的跨度
    gap_count: int
    gap_ms: float
    tail_ms: float = 0.0
    stream: int = -1
    starts_ms: list[float] = field(default_factory=list)
    durs_ms: list[float] = field(default_factory=list)

    @property
    def idle_ms(self) -> float:
        """GPU 什么都没干的时间 = 空隙 + 尾。"""
        return self.span_ms - self.busy_ms

    @property
    def gap_duty(self) -> float:
        """空闲占跨度的比例。这是全文最该盯的一个数。"""
        return self.idle_ms / self.span_ms if self.span_ms else 0.0

    @property
    def gap_median_us(self) -> float:
        return self._median(self._gap_list) * 1000.0

    @property
    def gap_max_us(self) -> float:
        return (max(self._gap_list) * 1000.0) if self._gap_list else 0.0

    _gap_list: list[float] = field(default_factory=list)

    @staticmethod
    def _median(xs: list[float]) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        return s[len(s) // 2]


def _load_trace(mode: str) -> Trace:
    path = DATA / f"trace_{mode}.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        i = next(k for k, l in enumerate(lines) if l.startswith(DATA_START))
    except StopIteration:
        raise SystemExit(f"{path} 里找不到表头 {DATA_START!r}")

    # 必须用 csv 模块,不能按逗号 split:kernel 名字本身带逗号,
    # 比如 `diffuse(float*, float*, int)` —— 按逗号切会把名字截成
    # `int)`,于是 "[CUDA kernel]" 一个都匹配不上。
    reader = csv.DictReader(lines[i:])
    rows = []
    for r in reader:
        try:
            start = int(r["Start (ns)"]) / 1e9
            dur = int(r["Duration (ns)"]) / 1e9
        except (TypeError, ValueError):
            continue
        rows.append((start, dur, r["Strm"], r["Name"]))
    if not rows:
        raise SystemExit(f"{path} 没有解析出任何事件")

    # 只统计 kernel。nsys 的 cuda_gpu_trace 里,**真 kernel 直接写名字**
    # (`diffuse(const float *, float *, int, int)`),方括号只留给
    # `[CUDA memset]` / `[CUDA memcpy ...]` 这类非 kernel 条目 ——
    # 并不存在 `[CUDA kernel]` 这个前缀(第一版就是照那个不存在的
    # 前缀去匹配,一个都没匹配上)。判据取「不以 [ 开头」。
    kern = [r for r in rows if not r[3].startswith("[")]
    if not kern:
        raise SystemExit(f"{path} 里没有解析出任何 kernel 条目")

    # 按流分组。跨流的间隔没有意义 —— 不同流的 kernel 本来就可以重叠,
    # 拿全局时间轴去减会凭空造出一堆「空隙」。
    by_stream: dict[str, list[tuple[float, float]]] = {}
    for s, d, strm, _ in kern:
        by_stream.setdefault(strm, []).append((s, d))

    # 取 kernel 最多的那条流
    strm, evs = max(by_stream.items(), key=lambda kv: len(kv[1]))
    evs.sort()

    t0 = evs[0][0]
    starts = [(s - t0) * 1000.0 for s, _ in evs]         # ms
    durs = [d * 1000.0 for _, d in evs]                  # ms
    span = (evs[-1][0] + evs[-1][1] - t0) * 1000.0

    gaps = []
    for k in range(len(evs) - 1):
        end = evs[k][0] + evs[k][1]
        nxt = evs[k + 1][0]
        g = (nxt - end) * 1000.0                          # ms
        if g * 1000.0 > GAP_FLOOR_US:
            gaps.append(g)

    busy = sum(durs)
    gap_sum = sum(gaps)
    # tail 直接取**残差** span - busy - gap_sum,这样
    #     span = busy + gap + tail
    # 是恒等式,不用再讨论舍入。
    #
    # 残差里装的是两样东西:最后一个 kernel 跑完之后到进程结束的等待,
    # 以及每条都不到 GAP_FLOOR_US 的碎缝之和(good 的那部分约
    # 0.037 ms,分在 61 条上,平均每条不到 1us —— 本来也不该算成
    # 「空隙」)。所以它读作「除了可测的空隙之外,还没在算的时间」。
    tail = max(0.0, span - busy - gap_sum)

    return Trace(
        mode=mode,
        kernels=len(evs),
        busy_ms=busy,
        span_ms=span,
        gap_count=len(gaps),
        gap_ms=gap_sum,
        tail_ms=tail,
        stream=int(strm) if strm.isdigit() else -1,
        starts_ms=starts,
        durs_ms=durs,
        _gap_list=gaps,
    )


def gaps() -> dict[str, Trace]:
    return {m: _load_trace(m) for m in ("good", "sync", "errsync")}


def busy_segments(mode: str) -> list[tuple[float, float]]:
    """返回 [(start_ms, end_ms), ...] —— 用来画时间线。"""
    t = _load_trace(mode)
    return [(s, s + d) for s, d in zip(t.starts_ms, t.durs_ms)]


def idle_profile(mode: str, buckets: int = 320) -> list[float]:
    """把跨度切成 buckets 段,返回每段的「GPU 空闲比例」(0..1)。

    trace 里记的是 kernel 区间;没有 kernel 覆盖的时间就是 GPU 在等。
    这张图是把「等」画出来,所以这个函数是核心。
    """
    t = _load_trace(mode)
    segs = [(s, s + d) for s, d in zip(t.starts_ms, t.durs_ms)]
    idle = []
    for b in range(buckets):
        x0 = t.span_ms * b / buckets
        x1 = t.span_ms * (b + 1) / buckets
        busy = 0.0
        for s, e in segs:
            lo, hi = max(s, x0), min(e, x1)
            if hi > lo:
                busy += hi - lo
        idle.append(max(0.0, 1.0 - busy / (x1 - x0)))
    return idle


# --------------------------------------------------------------- 其它实验

@dataclass
class Kernels:
    n: int
    ngroups: int
    global_ms: float
    shared_ms: float
    face_len: int
    nfaces: int
    separate_ms: float
    packed_ms: float

    @property
    def shared_speedup(self) -> float:
        return self.global_ms / self.shared_ms

    @property
    def packed_speedup(self) -> float:
        return self.separate_ms / self.packed_ms


def kernels() -> Kernels:
    t = RUN_LOG.read_text(encoding="utf-8")

    def num(pat: str, cast=float):
        m = re.search(pat, t)
        if not m:
            raise SystemExit(f"日志里找不到: {pat}")
        return cast(m.group(1))

    return Kernels(
        n=num(r"\[X\] merge\s+ngroups=\d+ n=(\d+)", int),
        ngroups=num(r"\[X\] merge\s+ngroups=(\d+)", int),
        global_ms=num(r"global atomics :\s+([\d.]+) ms"),
        shared_ms=num(r"shared atomics :\s+([\d.]+) ms"),
        face_len=num(r"face_len=(\d+)", int),
        nfaces=num(r"nfaces=(\d+)", int),
        separate_ms=num(r"6 separate copies :\s+([\d.]+) ms"),
        packed_ms=num(r"packed, 1 copy\s+:\s+([\d.]+) ms"),
    )


def main() -> int:
    """命令行自查:把重算出来的数打出来,方便和正文对照。"""
    print("=== 墙钟(bench_bogus, iters=200 n=1048576)===")
    w = wallclock()
    base = w["good"].elapsed_ms
    for m in MODES:
        x = w[m]
        print(f"  {m:8s} {x.elapsed_ms:9.3f} ms   "
              f"{x.per_iter_us:8.3f} us/iter   "
              f"相对 good {x.elapsed_ms / base:6.2f}x   "
              f"checksum={x.checksum}")
    if len({round(x.checksum, 3) for x in w.values()}) != 1:
        print("  !! 五种模式的 checksum 不一致 —— 它们算的不是同一件事")

    print("\n=== 空隙(nsys, iters=50 n=262144)===")
    g = gaps()
    print(f"  {'mode':8s} {'kernels':>8s} {'busy_ms':>9s} {'gap_ms':>8s} "
          f"{'tail_ms':>9s} {'idle_ms':>9s} {'span_ms':>9s} {'idle%':>7s}")
    for m in ("good", "sync", "errsync"):
        t = g[m]
        print(f"  {m:8s} {t.kernels:8d} {t.busy_ms:9.3f} {t.gap_ms:8.3f} "
              f"{t.tail_ms:9.3f} {t.idle_ms:9.3f} {t.span_ms:9.3f} "
              f"{t.gap_duty * 100:6.1f}%")
        # 恒等式自查:span = busy + gap + tail,误差应该在浮点噪声级别
        err = abs(t.span_ms - (t.busy_ms + t.gap_ms + t.tail_ms))
        if err > 1e-6:
            print(f"    !! 恒等式不成立,差 {err:.9f} ms")

    print("\n  以 good 为基准:")
    for m in ("sync", "errsync"):
        t, b = g[m], g["good"]
        print(f"    {m:8s} 总跨度 {(t.span_ms - b.span_ms):+7.3f} ms   "
              f"在算 {(t.busy_ms - b.busy_ms):+7.3f} ms   "
              f"在等 {(t.idle_ms - b.idle_ms):+7.3f} ms   "
              f"(空隙 {t.gap_ms - b.gap_ms:+.3f} + 尾 {t.tail_ms - b.tail_ms:+.3f})")

    print("\n=== kernels.cu ===")
    k = kernels()
    print(f"  [X] n={k.n} ngroups={k.ngroups}  "
          f"global {k.global_ms:.4f} ms  shared {k.shared_ms:.4f} ms  "
          f"{k.shared_speedup:.2f}x")
    print(f"  [Y] face_len={k.face_len} nfaces={k.nfaces}  "
          f"分开发 {k.separate_ms:.4f} ms  打包 {k.packed_ms:.4f} ms  "
          f"{k.packed_speedup:.2f}x")

    print("\n=== cpu_side.cu ===")
    t = RUN_LOG.read_text(encoding="utf-8")
    for line in t.splitlines():
        if re.search(r"cond_broadcast :|spinlock  |batch=|A 同步|C pinned|B 零拷贝|"
                     r"A -> C|C -> B|A -> B", line):
            print("  " + line.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
