#!/usr/bin/env python3
"""Fill the `@@MEASURED_*@@` slots in the hash-and-heap post with real numbers.

The post's sections 1.5, 2.4 and 3.3 each print a block of measured data.  That
data must come from *the code printed in the post* — so this script extracts the
post's own ```python blocks with a regex, execs them, and drives them.  The only
thing written here by hand is the driver (which sizes to try, which seeds to
use) plus the two-line Floyd heapify *loop* that section 3.3 states as
pseudocode; the `sink` it calls is the post's own `MinPQ._sink`.

    python3 measure.py            # print the numbers, change nothing
    python3 measure.py --write    # also substitute them into the post

Every random choice is seeded, so the numbers are reproducible.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
POST = REPO / "_posts/2026-11-16-hash-and-heap.md"

SEED = 20261116


def extract(text: str, lang: str) -> list[str]:
    """Same extraction the code gate uses: the post is the single source."""
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def load_namespace(post: str) -> dict:
    py = extract(post, "python")
    ns: dict = {}
    exec(compile("\n".join(py), str(POST), "exec"), ns)   # noqa: S102
    return ns


def fmt_int(n: int) -> str:
    return f"{n:,}"


# --------------------------------------------------------------------------
def measure_rehash(ns) -> str:
    """1.5: total element moves during doubling, for several n."""
    rows = []
    for log_n in (14, 16, 18, 20):
        n = 1 << log_n
        m = ns["ChainingHashMap"]()
        for i in range(n):
            m.put("key%d" % i, i)
        rows.append((n, m.rehash_ops))
    lines = [f"{'n':>10}  {'扩容搬运总次数':>16}  {'搬运次数 / n':>13}"]
    for n, ops in rows:
        lines.append(f"{n:>10}  {ops:>16,}  {ops / n:>13.4f}")
    worst = max(ops / n for n, ops in rows)
    lines.append("")
    lines.append(f"比值稳定在 1.5 附近(最大 {worst:.4f});上界 1.5n 是紧的。")
    return "\n".join(lines)


# --------------------------------------------------------------------------
def measure_consistent(ns) -> str:
    """2.4: distribution and migration, ring vs modulo, two hash functions.

    FNV-1a is the hash the post's `ConsistentHash` class ships.  MD5 (first 8
    bytes) is the control: section 2.4's own code comment says real systems and
    the original tutorial use MD5/SHA1 instead.  Running both isolates how much
    of the skew is the ring's fault and how much is the hash's.
    """
    import hashlib
    import math

    keys = ["user:%d" % i for i in range(10000)]
    nodes3 = ["cache-a", "cache-b", "cache-c"]

    def ring_of(vnodes, hash_of=None):
        r = ns["ConsistentHash"](virtual_nodes=vnodes)
        if hash_of is not None:
            r.hash_of = staticmethod(hash_of)
        return r

    def assign(vnodes, nodes, hash_of=None):
        r = ring_of(vnodes, hash_of)
        for node in nodes:
            r.add_node(node)
        return r, {k: r.get_node(k) for k in keys}

    def md5_of(s):
        return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:16], 16)

    def row(name, hash_of, ideal_scale_out, ideal_scale_in, show_ideal=False):
        _, before = assign(200, nodes3, hash_of)
        dist = sorted({n: sum(1 for v in before.values() if v == n)
                       for n in nodes3}.items())
        _, after4 = assign(200, nodes3 + ["cache-d"], hash_of)
        _, after2 = assign(200, ["cache-a", "cache-b"], hash_of)
        out = sum(1 for k in keys if before[k] != after4[k])
        inn = sum(1 for k in keys if before[k] != after2[k])
        return (f"{name:16s} " + " ".join(f"{c:>5d}" for _, c in dist) +
                f"   {out / 100:>8.1f}%  {inn / 100:>8.1f}%")

    r3, mod_before = assign(200, nodes3)
    mod_after = {k: int(r3.hash_of(k) % 4) for k in keys}
    mod_moved = sum(1 for k in keys if mod_before[k] != mod_after[k])

    # ring uniformity: the top bits decide where on the ring a point lands
    def uniformity(vals, label):
        vals = sorted(vals)
        gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
        mean_gap = (vals[-1] - vals[0]) / (len(vals) - 1)
        buckets = [0] * 64
        for v in vals:
            buckets[v >> 58] += 1
        exp = len(vals) / 64
        chi = sum((b - exp) ** 2 / exp for b in buckets)
        return f"  {label:34s} maxgap/meangap={max(gaps) / mean_gap:7.2f}   chi2={chi:8.1f}"

    lines = [
        "10000 个 key,每台 200 个虚拟节点,3 台",
        "",
        "                 3 台时的分布(key 数)   3->4 迁移  3->2 迁移",
        row("FNV-1a(本文代码)", None, 25.0, 33.3),
        row("MD5 前 8 字节", md5_of, 25.0, 33.3),
        "理想均匀分布      3333  3333  3333     25.0%     33.3%",
        f"取模法(对照)      --                     {mod_moved / 100:>5.1f}%        --",
        "",
        "环铺得匀不匀(64 个桶,均匀时 chi2 应约等于 63):",
        uniformity([ns["ConsistentHash"].hash_of("cache-a#%d" % i)
                    for i in range(200)], "FNV-1a, 'cache-a#i' i=0..199"),
        uniformity([ns["ConsistentHash"].hash_of("cache-a#%d" % i)
                    for i in range(5000)], "FNV-1a, 'cache-a#i' i=0..4999"),
        uniformity([md5_of("cache-a#%d" % i) for i in range(200)],
                   "MD5,    'cache-a#i' i=0..199"),
        uniformity([ns["ConsistentHash"].hash_of("user:%d" % i)
                    for i in range(10000)], "FNV-1a, 'user:i' i=0..9999"),
        uniformity([md5_of("user:%d" % i) for i in range(10000)],
                   "MD5,    'user:i' i=0..9999"),
        "",
        "虚拟节点加到 5000 个,FNV-1a 的 chi2 仍有 3963~4864 —— 所以这不是",
        "「虚拟节点不够多」,而是 FNV-1a 的高位在「同一前缀 + 数字后缀」这类",
        "输入上会聚堆,而环上的位置恰好由高位决定。换 MD5 就摊平了。",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
def measure_buildheap(ns) -> str:
    """3.3: Floyd heapify vs one-by-one swim, on random and on worst-case input."""
    MinPQ = ns["MinPQ"]

    def heap_property_holds(pq):
        h = pq.heap
        for i in range(len(h)):
            for child in (2 * i + 1, 2 * i + 2):
                if child < len(h) and h[i] > h[child]:
                    return False
        return True

    def floyd(data):
        pq = MinPQ()
        pq.heap = list(data)
        n = len(pq.heap)
        for i in range(n // 2 - 1, -1, -1):   # section 3.3's pseudocode
            pq._sink(i)
        return pq

    def swim(data):
        pq = MinPQ()
        for v in data:
            pq.push(v)
        return pq

    def table(label, make_data, sizes):
        out = [f"{label}", f"{'n':>8}  {'逐个 swim':>12}  {'Floyd 建堆':>11}  "
               f"{'swim/n':>8}  {'floyd/n':>8}  {'swim/floyd':>10}"]
        for log_n in sizes:
            n = 1 << log_n
            data = make_data(n)
            a, b = swim(data), floyd(data)
            # the two builds do NOT give the same array -- both are valid heaps,
            # the layouts just differ, so check the heap property, not equality
            assert heap_property_holds(a) and heap_property_holds(b), label
            out.append(f"{n:>8}  {a.comparisons:>12,}  {b.comparisons:>11,}  "
                       f"{a.comparisons / n:>8.2f}  {b.comparisons / n:>8.2f}  "
                       f"{a.comparisons / b.comparisons:>10.2f}")
        return out

    sizes = (12, 14, 16, 18)
    rnd = random.Random(SEED)
    shuffled = {}
    for log_n in sizes:
        data = list(range(1 << log_n))
        rnd.shuffle(data)
        shuffled[log_n] = data

    lines = []
    lines += table("最坏输入(严格降序 n-1 .. 0):",
                   lambda n: list(range(n - 1, -1, -1)), sizes)
    lines.append("")
    lines += table("随机输入(固定种子 %d 洗牌):" % SEED,
                   lambda n: shuffled[n.bit_length() - 1], sizes)
    lines.append("")
    lines.append("Floyd 建堆任何输入都在 2n 次比较以内;逐个 swim 的最坏输入是降序,")
    lines.append("n 次 push 每次上浮到底,比较次数是 n log n 量级 —— 随 n 增大,两者")
    lines.append("的比值从 3.05 涨到 6.88。随机输入下逐个 swim 也接近 Θ(n)(新元素平均")
    lines.append("只上浮 1 层),所以「n log n 对 n」这条分界只在最坏输入上看得出来。")
    return "\n".join(lines)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="substitute the numbers into the post")
    args = ap.parse_args()

    post = POST.read_text(encoding="utf-8")
    ns = load_namespace(post)
    print(f"  loaded {len(extract(post, 'python'))} python blocks from {POST.name}")

    slots = {
        "@@MEASURED_REHASH@@": measure_rehash(ns),
        "@@MEASURED_CONSISTENT@@": measure_consistent(ns),
        "@@MEASURED_BUILDHEAP@@": measure_buildheap(ns),
    }
    for name, body in slots.items():
        print(f"\n----- {name} -----")
        print(body)

    missing = [k for k in slots if k not in post]
    if missing and args.write:
        print(f"\n  note: already substituted: {missing}")

    if args.write:
        for name, body in slots.items():
            post = post.replace(name, body)
        POST.write_text(post, encoding="utf-8")
        print(f"\n  wrote {POST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
