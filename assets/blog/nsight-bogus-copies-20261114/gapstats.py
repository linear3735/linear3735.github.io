#!/usr/bin/env python3
"""从 nsys 导出的逐 kernel 时间线里算「GPU 空隙」。

talk 第 20 页那张图的论点是:Bogus memory copies! Create gaps in GPU
execution。这句话是可以量化的 —— kernel 与 kernel 之间 GPU 什么都不干的
时间,就是「空隙」。把同一个程序在几种模式下的空隙分布摆在一起,
不需要看截图也能说明问题。

输入:trace_<mode>.csv(nsys stats --report cuda_gpu_trace --format csv)
输出:每种模式的空隙条数、总空隙、总 kernel 时间、空隙占比
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

# nsys stats 会在 CSV 前面打印几行进度的噪音,先跳过
DATA_START = "Start (ns),"


def load(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    idx = text.find(DATA_START)
    if idx < 0:
        raise SystemExit(f"{path}: 找不到 CSV 表头")
    rows = list(csv.DictReader(io.StringIO(text[idx:])))
    out = []
    for r in rows:
        try:
            out.append({
                "start": int(r["Start (ns)"]),
                "dur": int(r["Duration (ns)"]),
                "name": r["Name"],
                "strm": r["Strm"],
            })
        except (KeyError, ValueError):
            continue
    out.sort(key=lambda x: x["start"])
    return out


def analyze(path: Path, gap_floor_us: float = 1.0):
    ev = load(path)
    if not ev:
        raise SystemExit(f"{path}: 没有事件")

    # 同一 stream 上的 kernel 才是「排队关系」;跨 stream 的空隙不代表
    # GPU 闲着(可能另一个 stream 在跑),所以必须分开算。
    streams: dict[str, list[dict]] = {}
    for e in ev:
        streams.setdefault(e["strm"], []).append(e)

    # 取 kernel 数最多的那个 stream —— 那是主工作流
    main = max(streams.values(), key=len)
    main.sort(key=lambda x: x["start"])

    kernel_busy = sum(e["dur"] for e in main)
    span = main[-1]["start"] + main[-1]["dur"] - main[0]["start"]

    gaps = []
    for a, b in zip(main, main[1:]):
        g = b["start"] - (a["start"] + a["dur"])
        if g > gap_floor_us * 1000:      # 只看 > 1us 的,噪声不计
            gaps.append(g)

    return {
        "file": path.name,
        "kernels": len(main),
        "busy_ms": kernel_busy / 1e6,
        "span_ms": span / 1e6,
        "gap_count": len(gaps),
        "gap_total_ms": sum(gaps) / 1e6,
        "gap_median_us": (sorted(gaps)[len(gaps) // 2] / 1e3) if gaps else 0.0,
        "gap_max_us": (max(gaps) / 1e3) if gaps else 0.0,
        "gap_duty": (sum(gaps) / span * 100.0) if span else 0.0,
    }


def main() -> int:
    files = [Path(p) for p in sys.argv[1:]]
    if not files:
        files = sorted(Path(".").glob("trace_*.csv"))

    res = [analyze(f) for f in files]

    print(f"{'mode':<10}{'kernels':>9}{'busy_ms':>10}{'span_ms':>10}"
          f"{'gaps':>7}{'gap_ms':>9}{'gap%':>8}{'med_us':>9}{'max_us':>9}")
    print("-" * 81)
    for r in res:
        mode = r["file"].replace("trace_", "").replace(".csv", "")
        print(f"{mode:<10}{r['kernels']:>9}{r['busy_ms']:>10.3f}"
              f"{r['span_ms']:>10.3f}{r['gap_count']:>7}{r['gap_total_ms']:>9.3f}"
              f"{r['gap_duty']:>8.1f}{r['gap_median_us']:>9.1f}"
              f"{r['gap_max_us']:>9.1f}")

    base = next((r for r in res
                 if r["file"].endswith("good.csv")), None)
    if base:
        print()
        print("以 good 为基准:")
        for r in res:
            if r is base:
                continue
            mode = r["file"].replace("trace_", "").replace(".csv", "")
            extra = r["gap_total_ms"] - base["gap_total_ms"]
            rd = (r["span_ms"] / base["span_ms"] - 1.0) * 100.0
            print(f"  {mode:<10} 多出的空隙 {extra:+7.3f} ms   "
                  f"总跨度 {rd:+6.1f}%   空隙条数 "
                  f"{base['gap_count']} → {r['gap_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
