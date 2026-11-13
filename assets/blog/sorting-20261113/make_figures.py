#!/usr/bin/env python3
"""Regenerate the five SVG figures for the sorting post.

Run:  /opt/miniconda3/bin/python3 make_figures.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent
OUT = BLOG.parent / "img" / "sorting-20261113"
sys.path.insert(0, str(BLOG / "_tools"))

from svgkit import (Svg, Check, PAPER, CANVAS, INK, MUTED, LINE, BLUE,       # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT.mkdir(parents=True, exist_ok=True)


def title(s, c, t, sub=None):
    s.text(34, 40, t, size=18, anchor="start", weight="600")
    c.text("title", 34, 40, t, size=18, anchor="start")
    if sub:
        s.text(34, 63, sub, size=12, fill=MUTED, anchor="start")
        c.text("subtitle", 34, 63, sub, size=12, anchor="start")


def note(s, c, name, x, y, t, size=12, fill=MUTED, anchor="start"):
    s.text(x, y, t, size=size, fill=fill, anchor=anchor)
    c.text(name, x, y, t, size=size, anchor=anchor)


def box(s, c, name, x, y, w, h, label, fill=PAPER, stroke=INK, size=13, sub=None):
    s.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, rx=7)
    c.panel(name, x, y, w, h)
    if sub:
        s.text(x + w / 2, y + h / 2 - 2, label, size=size, anchor="middle")
        c.text(name + ":l", x + w / 2, y + h / 2 - 2, label, size=size)
        s.text(x + w / 2, y + h / 2 + 15, sub, size=10.5, fill=MUTED)
        c.text(name + ":s", x + w / 2, y + h / 2 + 15, sub, size=10.5)
    else:
        s.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size)
        c.text(name + ":l", x + w / 2, y + h / 2 + size * 0.36, label, size=size)


def tbl(x, y, w, h, label, sub, fill):
    return dict(x=x, y=y, w=w, h=h, label=label, sub=sub, fill=fill)


# --------------------------------------------------------------- figure 1
def fig_three_families():
    s = Svg(1000, 470); c = Check(s)
    title(s, c, "十大排序算法的三个族",
          "分族的依据不是代码长短，而是「比较的下界」和「是否依赖比较」")

    fam = [
        (30, "平方级 O(n²)", "靠反复比较与交换，实现最直白", FILL_WARM, WARM_TXT,
         ["冒泡排序", "选择排序", "插入排序", "希尔排序*"]),
        (345, "O(n log n) 比较排序", "靠分治或堆结构把比较次数压到下界", FILL_BLUE, BLUE,
         ["归并排序", "快速排序", "堆排序"]),
        (660, "非比较排序 O(n+k)", "不比较元素大小，靠值域直接定位", FILL_TEAL, TEAL_TXT,
         ["计数排序", "桶排序", "基数排序"]),
    ]
    for x, name, desc, fill, stroke, items in fam:
        box(s, c, f"f{x}", x, 88, 310, 54, name, fill=fill, stroke=stroke, size=15)
        note(s, c, f"fd{x}", x + 12, 162, desc, size=11)
        for i, it in enumerate(items):
            box(s, c, f"i{x}-{i}", x, 178 + i * 46, 310, 38, it, size=13)

    s.rect(30, 372, 940, 74, fill=CANVAS, stroke=LINE, sw=1, rx=9)
    c.panel("stability", 30, 372, 940, 74)
    note(s, c, "stab1", 46, 400,
         "* 稳定性没有统一的族规律：只有「相等元素不跨越彼此」的实现才稳定。", size=12)
    note(s, c, "stab2", 46, 424,
         "稳定的：冒泡、插入、归并、计数、桶、基数；希尔、选择、快排、堆排都不稳定。",
         size=12, fill=TEAL_TXT)
    BAD.append(c.run("01-three-families"))
    s.save(OUT / "01-three-families.svg")


# --------------------------------------------------------------- figure 2
def fig_scan_compare():
    s = Svg(1000, 430); c = Check(s)
    title(s, c, "冒泡每趟扫到底,插入一遇到更小就停",
          "两者的扫描区间宽度不同，这是 O(n²) 常数项差异的来源")

    n = 8
    # real state after one bubble pass over [7,2,9,1,5,3,4,8]: 8 and 9 are home
    val = [2, 7, 1, 5, 3, 4, 8, 9]
    W0, CW, GAP = 150, 78, 12
    y = 150

    def cells(y, lbl, lbl2, hl_from=None, hl_to=None, hl_fill=FILL_WARM):
        for i, v in enumerate(val):
            x = W0 + i * (CW + GAP)
            on = hl_from is not None and hl_from <= i <= hl_to
            box(s, c, f"{lbl}-{i}", x, y, CW, 46, str(v),
                fill=hl_fill if on else PAPER, size=16)
        note(s, c, lbl + "-cap", W0 - 16, y + 30, lbl2, size=12.5, anchor="end")

    # pass 2 of bubble: fixed prefix, scans the rest
    cells(96, "bubble", "冒泡 第2趟", hl_from=0, hl_to=5)
    note(s, c, "b-note", W0 + 6.5 * (CW + GAP), 84,
         "8、9 已就位(第1趟的成果)", size=11, fill=TEAL_TXT, anchor="middle")
    note(s, c, "b-note2", W0 + 3 * (CW + GAP), 172,
         "本趟仍要把 [0, 5] 整段扫完：6 个格子，一个都不能跳",
         size=11.5, fill=WARM_TXT, anchor="middle")

    # insertion: element 5 goes left until it meets something smaller
    cells(258, "insert", "插入 处理第6个", hl_from=0, hl_to=5)
    box(s, c, "ins-key", W0 + 5 * (CW + GAP), 336, CW, 40, "key=4",
        fill=FILL_TEAL, stroke=TEAL_TXT, size=13)
    note(s, c, "i-note", W0 + 5 * (CW + GAP) + CW / 2, 396,
         "向左只看一格：3 < 4，立刻停", size=11.5, fill=TEAL_TXT, anchor="middle")
    s.arrow(W0 + 5 * (CW + GAP) + CW / 2, 332, W0 + 4.2 * (CW + GAP), 318,
            stroke=TEAL_TXT, sw=1.6, dash="5 4")
    c.arrow("ins-arrow", W0 + 5 * (CW + GAP) + CW / 2, 332,
            W0 + 4.2 * (CW + GAP), 318)

    BAD.append(c.run("02-scan-compare"))
    s.save(OUT / "02-scan-compare.svg")


# --------------------------------------------------------------- figure 3
def fig_merge_stability():
    s = Svg(1000, 400); c = Check(s)
    title(s, c, "归并时相等取左边,稳定性就是这么保住的",
          "两个已排好序的半区合并，比较只看「谁更小」，相等时必须优先取左")

    def half(y, lbl, items, x0, fill):
        note(s, c, lbl + "-cap", x0 - 14, y + 30, lbl, size=12.5, anchor="end")
        for i, (v, tag) in enumerate(items):
            x = x0 + i * 118
            s.rect(x, y, 106, 46, fill=fill, stroke=INK, sw=1.3, rx=6)
            c.panel(f"{lbl}-{i}", x, y, 106, 46)
            s.text(x + 53, y + 24, str(v), size=15)
            c.text(f"{lbl}-{i}:v", x + 53, y + 24, str(v), size=15)
            s.text(x + 53, y + 39, tag, size=10, fill=MUTED)
            c.text(f"{lbl}-{i}:t", x + 53, y + 39, tag, size=10)

    x0 = 172
    half(96, "左半区", [(3, "原下标 0"), (5, "原下标 2")], x0, FILL_BLUE)
    half(196, "右半区", [(5, "原下标 4"), (7, "原下标 6")], x0, FILL_TEAL)

    note(s, c, "rule", x0 + 280, 250,
         "两个 5 相等：必须取左半区那个（原下标 2），", size=12.5, fill=WARM_TXT)
    note(s, c, "rule2", x0 + 280, 272,
         "取右边就会让原下标 4 排到 2 前面，稳定性立刻丢失。",
         size=12.5, fill=WARM_TXT)

    for i, (v, tag, fill) in enumerate([(3, "", FILL_BLUE), (5, "← 左", FILL_BLUE),
                                        (5, "右", FILL_TEAL), (7, "", FILL_TEAL)]):
        x = x0 + i * 118
        s.rect(x, 300, 106, 46, fill=fill, stroke=INK, sw=1.3, rx=6)
        c.panel(f"out-{i}", x, 300, 106, 46)
        s.text(x + 53, 328, str(v), size=15)
        c.text(f"out-{i}:v", x + 53, 328, str(v), size=15)
        if tag:
            s.text(x + 53, 343, tag, size=10, fill=MUTED)
            c.text(f"out-{i}:t", x + 53, 343, tag, size=10)
    note(s, c, "out-cap", x0 - 14, 330, "合并结果", size=12.5, anchor="end")

    BAD.append(c.run("03-merge-stability"))
    s.save(OUT / "03-merge-stability.svg")


# --------------------------------------------------------------- figure 4
def fig_quick_pivot():
    s = Svg(1000, 420); c = Check(s)
    title(s, c, "枢轴选得好不好,决定快排退化成什么",
          "三种划分策略在「已经有序」的输入上表现完全不同")

    rows = [
        (96, "固定取首元素", "1 | 2 3 4 5 6 7 8",
         "每次只切掉 1 个 → 递归 n 层 → O(n²)", FILL_WARM, WARM_TXT),
        (200, "随机选枢轴", "1 2 3 | 4 | 5 6 7 8",
         "期望对半分 → 期望 O(n log n)，与输入顺序无关", FILL_BLUE, BLUE),
        (304, "三路划分", "[1 1 1] | 2 2 | [3 3 3]",
         "相等元素一次清空，重复多的输入反而更快", FILL_TEAL, TEAL_TXT),
    ]
    for y, name, shape, verdict, fill, stroke in rows:
        box(s, c, f"p{y}", 30, y, 190, 84, name, fill=fill, stroke=stroke, size=14)
        note(s, c, f"p{y}-shape", 246, y + 30, shape, size=13.5, fill=stroke)
        note(s, c, f"p{y}-verdict", 246, y + 60, verdict, size=11.5)

    note(s, c, "warn", 30, 410,
         "注意：「随机枢轴」是期望 O(n log n)，不是最坏——理论上仍然存在 O(n²) 的输入，只是概率极低。",
         size=11.5, fill=MUTED)
    BAD.append(c.run("04-quick-pivot"))
    s.save(OUT / "04-quick-pivot.svg")


# --------------------------------------------------------------- figure 5
def fig_heapify_cost():
    s = Svg(1000, 440); c = Check(s)
    title(s, c, "建堆为什么是 O(n) 而不是 O(n log n)",
          "自底向上建堆的总代价是「每层节点数 × 该层高度」，再被几何级数压成常数")

    h = 4
    # level d (0 = root) has 2^d nodes, each sinks at most h-d levels
    rows = []
    for d in range(h + 1):
        n = 2 ** d
        rows.append((d, n, h - d, n * (h - d)))

    x0, y0, RH = 130, 92, 48
    cols = [("层 d", 90, "middle"), ("该层节点数 2^d", 300, "middle"),
            ("每个节点最多下沉 h−d", 560, "middle"), ("该层总代价", 810, "middle")]
    for name, x, anc in cols:
        note(s, c, "h-" + name, x, y0 - 10, name, size=12, fill=MUTED, anchor=anc)

    for i, (d, n, sink, cost) in enumerate(rows):
        y = y0 + i * RH
        fill = FILL_BLUE if i % 2 == 0 else PAPER
        s.rect(x0, y, 740, RH - 6, fill=fill, stroke=LINE, sw=1, rx=5)
        c.panel(f"row{i}", x0, y, 740, RH - 6)
        for v, xc in ((str(d), 90), (str(n), 300), (str(sink), 560), (str(cost), 810)):
            s.text(xc, y + 28, v, size=14)
            c.text(f"r{i}c{xc}", xc, y + 28, v, size=14)

    yt = y0 + (h + 1) * RH + 8
    s.rect(x0, yt, 740, 46, fill=CANVAS, stroke=LINE, sw=1, rx=6)
    c.panel("total", x0, yt, 740, 46)
    s.text(x0 + 340, yt + 30, "合计 = 2^(h+1) − h − 2  <  2n", size=15, fill=TEAL_TXT)
    c.text("total-val", x0 + 340, yt + 30, "合计 = 2^(h+1) − h − 2  <  2n", size=15)

    note(s, c, "fm", 30, 432,
         "关键：下沉代价大的层节点少，节点多的层下沉代价小 —— 上重下轻，求和收敛到常数倍 n。",
         size=11.5, fill=MUTED)
    BAD.append(c.run("05-heapify-cost"))
    s.save(OUT / "05-heapify-cost.svg")


# 各图 Check.run() 返回的问题数累计在这里。用 list 而不是 int：
# 函数内部对 int 做 += 会被当成局部变量，得每处写 global，容易漏。
BAD: list[int] = []


if __name__ == "__main__":
    fig_three_families()
    fig_scan_compare()
    fig_merge_stability()
    fig_quick_pivot()
    fig_heapify_cost()
    total = sum(BAD)
    print(f"  layout problem(s): {total}")
    sys.exit(1 if total else 0)
