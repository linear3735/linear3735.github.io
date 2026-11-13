#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the 7 figures for _posts/2026-11-24-shortest-path.md.

Every text label and every arrowhead is registered with svgkit.Check, which
catches text/text collisions, text/arrow collisions, off-canvas text and text
that spills out of its panel.  Plain lines are invisible to Check, so the
renders are also looked at by eye (sips -> png, 1400px wide).

Run:  python3 assets/blog/shortest-path-20261124/make_figures.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "assets", "blog", "_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = os.path.join(ROOT, "assets", "img", "shortest-path-20261124")

problems = 0


# ---------------------------------------------------------------- helpers
def lab(s, c, name, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Draw a text label and register it with Check."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)


def node(s, c, name, x, y, t, r=20, fill=PAPER, stroke=INK, size=15):
    s.circle(x, y, r, fill=fill, stroke=stroke, sw=1.6)
    lab(s, c, name, x, y + size * 0.36, t, size=size, weight="600")


def edge(s, x1, y1, x2, y2, stroke=INK, sw=1.6, dash=None):
    s.line(x1, y1, x2, y2, stroke=stroke, sw=sw, dash=dash)


def wedge(s, c, name, x1, y1, x2, y2, r=24, stroke=BLUE):
    """A short arrowhead at the (x2, y2) end, trimmed to radius r.

    Registered with a deliberately *small* hitbox: Check's arrow test is a
    bounding-box test, and the bbox of a full-length diagonal arrow would
    swallow every weight label sitting next to that edge.
    """
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    bx, by = x2 - ux * r, y2 - uy * r
    ax, ay = bx - ux * 16, by - uy * 16
    s.arrow(ax, ay, bx, by, stroke=stroke, sw=1.8)
    c.arrow(name, ax, ay, bx, by)


def panel_title(s, c, name, px, py, t, size=13):
    lab(s, c, name, px + 12, py + 26, t, size=size, anchor="start",
        weight="600", fill=BLUE)


def note(s, c, name, x, y, t, size=12, fill=MUTED, anchor="start"):
    lab(s, c, name, x, y, t, size=size, fill=fill, anchor=anchor)


def panel(s, c, name, x, y, w, h, fill=CANVAS):
    s.panel(x, y, w, h, fill=fill)
    c.panel(name, x, y, w, h)


def run(name, s, c):
    global problems
    problems += c.run(name)
    s.save(os.path.join(OUT, name + ".svg"))


# ---------------------------------------------------------------- fig 01
def fig01():
    """Four decision lanes: shortest path / MST / A* / Euler."""
    W, H = 980, 452
    s = Svg(W, H)
    c = Check(s)

    lab(s, c, "t", 24, 30, "选型:先问是哪一类问题,再问图长什么样", size=15,
        anchor="start", weight="600")

    # ① shortest path
    panel(s, c, "p1", 20, 48, 460, 184)
    panel_title(s, c, "p1t", 20, 48, "① 最短路")
    note(s, c, "a1", 36, 104, "有负权边 → 任意两点: Floyd   O(V³)", size=12.5)
    note(s, c, "a2", 36, 128, "有负权边 → 单源: Bellman-Ford  O(V·E)", size=12.5)
    note(s, c, "a3", 36, 152, "想更快: SPFA（实测快, 无硬保证）", size=12.5)
    edge(s, 36, 168, 464, 168, stroke=LINE, sw=1.2)
    note(s, c, "a4", 36, 194, "无负权 → 稠密: 朴素 Dijkstra   O(V²)", size=12.5)
    note(s, c, "a5", 36, 218, "无负权 → 稀疏: 堆版 Dijkstra   O(E log V)", size=12.5)

    # ② MST
    panel(s, c, "p2", 500, 48, 460, 184)
    panel_title(s, c, "p2t", 500, 48, "② 最小生成树:连通所有点、总代价最小")
    note(s, c, "b1", 516, 104, "Kruskal: 排序 + 并查集判环  O(E log E)", size=12.5)
    note(s, c, "b2", 516, 128, "Prim 朴素（稠密）        O(V²)", size=12.5)
    note(s, c, "b3", 516, 152, "Prim 堆版（稀疏）        O(E log V)", size=12.5)
    edge(s, 516, 168, 944, 168, stroke=LINE, sw=1.2)
    note(s, c, "b4", 516, 194, "负权边不影响: MST 只看权重的大小关系", size=12.5)
    note(s, c, "b5", 516, 218, "图不连通 → 最小生成森林（Kruskal 天然给）", size=12.5)

    # ③ A*
    panel(s, c, "p3", 20, 248, 460, 152)
    panel_title(s, c, "p3t", 20, 248, "③ A*:点对点, 能设计出可采纳的 h")
    note(s, c, "c1", 36, 304, "排序键从 g 换成 f = g + h", size=12.5)
    note(s, c, "c2", 36, 328, "h ≡ 0 → 退化成 Dijkstra（5.4 实测）", size=12.5)
    note(s, c, "c3", 36, 352, "h 高估 → 更快, 但答案会错（5.4 实测）", size=12.5)
    note(s, c, "c4", 36, 376, "无权网格上不如直接 BFS: O(E)", size=12.5)

    # ④ Euler
    panel(s, c, "p4", 500, 248, 460, 152)
    panel_title(s, c, "p4t", 500, 248, "④ 欧拉路径:每条边恰好走一次")
    note(s, c, "d1", 516, 304, "先判: 度数条件 + 连通性（两个都要）", size=12.5)
    note(s, c, "d2", 516, 328, "再跑 Hierholzer   O(E + V)", size=12.5)
    note(s, c, "d3", 516, 352, "输出 = 遍历所有边的 DFS 逆后序", size=12.5)
    note(s, c, "d4", 516, 376, "无向: 全偶 ⇒ 回路 / 恰两奇 ⇒ 路径", size=12.5)

    note(s, c, "f", 24, 434, "选错不会报错, 只会给你一个偏大（或偏小）的答案;"
         " 各条线的依据在 1.2 / 4.2 / 5.2 / 6.2。", size=12)

    run("01-algorithm-choice", s, c)


# ---------------------------------------------------------------- fig 02
def fig02():
    """Heap Dijkstra: the pop order and how dist moves."""
    W, H = 940, 404
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 20, 40, 420, 340)
    panel_title(s, c, "gt", 20, 40, "从 s 出发, 每次弹出 dist 最小的点")
    pos = {"s": (100, 160), "a": (250, 110), "b": (250, 250), "t": (390, 180)}
    weighted = [("s", "a", 1), ("s", "b", 4), ("a", "b", 1),
                ("a", "t", 5), ("b", "t", 1)]
    offs = {("s", "a"): (-16, -10), ("s", "b"): (-14, 12),
            ("a", "b"): (-16, 4), ("a", "t"): (0, -14), ("b", "t"): (0, 16)}
    for i, (u, v, w) in enumerate(weighted):
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        edge(s, x1, y1, x2, y2, stroke=LINE, sw=2.4)
        wedge(s, c, f"e{i}", x1, y1, x2, y2, r=22)
        ox, oy = offs[(u, v)]
        lab(s, c, f"w{i}", (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, str(w),
            size=12, fill=BLUE, weight="600")
    for k, (x, y) in pos.items():
        fill = FILL_TEAL if k == "s" else PAPER
        node(s, c, "n" + k, x, y, k, r=22, fill=fill)
    note(s, c, "leg1", 36, 344, "边: s→a=1  s→b=4  a→b=1", size=12)
    note(s, c, "leg2", 36, 368, "     a→t=5  b→t=1", size=12)

    panel(s, c, "tb", 460, 40, 460, 340)
    panel_title(s, c, "tbt", 460, 40, "出队顺序与 dist 的变化")
    ox, oy = 484, 92
    cols = [("出队", 92), ("s", 78), ("a", 78), ("b", 78), ("t", 78)]
    heads = ["出队", "s", "a", "b", "t"]
    cx = ox
    for i, (h, w) in enumerate(cols):
        s.cell(cx, oy, w, 32, "", fill=FILL_GREY, stroke=LINE)
        lab(s, c, f"h{i}", cx + w / 2, oy + 21, heads[i], size=12.5,
            weight="600", fill=BLUE)
        cx += w
    rows = [("s (0)", ["0", "1", "4", "∞"]),
            ("a (1)", ["0", "1", "2", "6"]),
            ("b (2)", ["0", "1", "2", "3"]),
            ("t (3)", ["0", "1", "2", "3"])]
    for r, (name, vals) in enumerate(rows):
        y = oy + 32 + r * 34
        cx = ox
        fill = FILL_TEAL if r == 3 else PAPER
        for i, (h, w) in enumerate(cols):
            s.cell(cx, y, w, 34, "", fill=fill, stroke=LINE)
            t = name if i == 0 else vals[i - 1]
            lab(s, c, f"c{r}{i}", cx + w / 2, y + 22, t, size=12.5,
                fill=TEAL_TXT if r == 3 else INK)
            cx += w
    note(s, c, "tb1", 484, 300, "出队的 dist 一定非降（1.2 的证明）", size=12)
    note(s, c, "tb2", 484, 324, "每个点第一次出队时就是最终答案", size=12)
    note(s, c, "tb3", 484, 348, "过期记录被 if d > dist[u] 丢掉", size=12)

    run("02-dijkstra-order", s, c)


# ---------------------------------------------------------------- fig 03
def fig03():
    """The negative-edge counterexample, and who returns what."""
    W, H = 960, 400
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 20, 40, 300, 340)
    panel_title(s, c, "gt", 20, 40, "原文的最小反例")
    pos = {"s": (80, 190), "a": (250, 120), "b": (250, 260)}
    edge(s, 80, 190, 250, 120, stroke=LINE, sw=2.4)
    wedge(s, c, "e0", 80, 190, 250, 120, r=22)
    lab(s, c, "w0", 152, 140, "3", size=13, fill=BLUE, weight="600")
    edge(s, 80, 190, 250, 260, stroke=LINE, sw=2.4)
    wedge(s, c, "e1", 80, 190, 250, 260, r=22)
    lab(s, c, "w1", 150, 244, "4", size=13, fill=BLUE, weight="600")
    edge(s, 250, 260, 250, 120, stroke=WARM_TXT, sw=3)
    wedge(s, c, "e2", 250, 260, 250, 120, r=22, stroke=WARM_TXT)
    lab(s, c, "w2", 236, 196, "-10", size=13, fill=WARM_TXT, weight="600",
        anchor="end")
    node(s, c, "ns", 80, 190, "s", r=22, fill=FILL_TEAL)
    node(s, c, "na", 250, 120, "a", r=22, fill=FILL_WARM)
    node(s, c, "nb", 250, 260, "b", r=22)
    note(s, c, "g1", 36, 330, "真实最短: a = -6", size=12.5, fill=WARM_TXT)
    note(s, c, "g2", 36, 354, "s → b → a = 4 + (-10)", size=12)

    panel(s, c, "r", 340, 40, 280, 340)
    panel_title(s, c, "rt", 340, 40, "四个实现, 两个答案")
    note(s, c, "r1", 356, 110, "朴素版（有 done）", size=12.5)
    lab(s, c, "r1v", 596, 110, "3  ✗", size=13, anchor="end", fill=WARM_TXT,
        weight="600")
    note(s, c, "r2", 356, 148, "堆版 + dst 提前退出", size=12.5)
    lab(s, c, "r2v", 596, 148, "3  ✗", size=13, anchor="end", fill=WARM_TXT,
        weight="600")
    edge(s, 356, 168, 604, 168, stroke=LINE, sw=1.2)
    note(s, c, "r3", 356, 200, "堆版完整跑完", size=12.5)
    lab(s, c, "r3v", 596, 200, "-6  ✓", size=13, anchor="end", fill=TEAL_TXT,
        weight="600")
    note(s, c, "r4", 356, 238, "Bellman-Ford", size=12.5)
    lab(s, c, "r4v", 596, 238, "-6  ✓", size=13, anchor="end", fill=TEAL_TXT,
        weight="600")
    edge(s, 356, 258, 604, 258, stroke=LINE, sw=1.2)
    note(s, c, "r5", 356, 296, "堆版那个 ✓ 是侥幸: 它没有", size=12)
    note(s, c, "r6", 356, 320, "done 标记, 会重新入队收敛", size=12)
    note(s, c, "r7", 356, 356, "多传一个 dst 就从对变成错", size=12,
         fill=WARM_TXT)

    panel(s, c, "bf", 640, 40, 300, 340)
    panel_title(s, c, "bft", 640, 40, "Bellman-Ford 的轮次")
    note(s, c, "b1", 656, 110, "初始        [0, ∞, ∞]", size=12.5)
    note(s, c, "b2", 656, 150, "第 1 轮后    [0, -6, 4]", size=12.5,
         fill=TEAL_TXT)
    note(s, c, "b3", 656, 190, "第 2 轮后    无改进 → 停", size=12.5)
    note(s, c, "b4", 656, 230, "第 V 轮      无改进 → 无负环", size=12.5)
    edge(s, 656, 254, 924, 254, stroke=LINE, sw=1.2)
    note(s, c, "b5", 656, 292, "原地更新让 s → b → a 在同一", size=12)
    note(s, c, "b6", 656, 316, "轮里就串起来了（2.1）", size=12)
    note(s, c, "b7", 656, 352, "[dist[s], dist[a], dist[b]]", size=12)

    run("03-negative-edge", s, c)


# ---------------------------------------------------------------- fig 04
def fig04():
    """Floyd: the k-th DP layer, and why k must be outermost."""
    W, H = 940, 410
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 20, 40, 420, 350)
    panel_title(s, c, "gt", 20, 40, "四点有向环, 只有 3 跳能到")
    pos = {0: (120, 120), 1: (330, 120), 2: (330, 280), 3: (120, 280)}
    ring = [(0, 1, 4), (1, 2, 3), (2, 3, 4), (3, 0, 2)]
    offs = {(0, 1): (0, -14), (1, 2): (16, 0), (2, 3): (0, 16),
            (3, 0): (-16, 0)}
    for i, (u, v, w) in enumerate(ring):
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        edge(s, x1, y1, x2, y2, stroke=LINE, sw=2.4)
        wedge(s, c, f"e{i}", x1, y1, x2, y2, r=22)
        ox, oy = offs[(u, v)]
        lab(s, c, f"w{i}", (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, str(w),
            size=12.5, fill=BLUE, weight="600")
    for u, (x, y) in pos.items():
        fill = FILL_TEAL if u == 1 else (FILL_WARM if u == 0 else PAPER)
        node(s, c, f"n{u}", x, y, str(u), r=22, fill=fill)
    note(s, c, "g1", 36, 344, "dist[1][0]: 1→2→3→0 = 3+4+2 = 9", size=12.5,
         fill=TEAL_TXT)
    note(s, c, "g2", 36, 368, "3 跳, 所以要转 3 圈 k 才拼得出来", size=12)

    panel(s, c, "d", 460, 40, 460, 350)
    panel_title(s, c, "dt", 460, 40, "把「允许谁当中转」写成一维阶段")
    note(s, c, "d1", 476, 104, "f_k[i][j] = 只允许前 k 个点当中转时的距离",
         size=12.5)
    note(s, c, "d2", 476, 140, "f_k[i][j] = min( f_{k-1}[i][j],", size=12.5)
    note(s, c, "d3", 476, 164, "                 f_{k-1}[i][k] + f_{k-1}[k][j] )",
         size=12.5)
    edge(s, 476, 184, 904, 184, stroke=LINE, sw=1.2)
    note(s, c, "d4", 476, 216, "k 在最外层 → 每圈多允许一个中转点", size=12.5,
         fill=TEAL_TXT)
    note(s, c, "d5", 476, 244, "答案 dist[1][0] = 9  ✓", size=12.5,
         fill=TEAL_TXT)
    note(s, c, "d6", 476, 288, "k 挪到内层 → 同一圈里 i、j 先跑完,", size=12.5)
    note(s, c, "d7", 476, 312, "3 跳路径永远拼不出来", size=12.5)
    note(s, c, "d8", 476, 340, "答案 dist[1][0] = ∞  ✗", size=12.5,
         fill=WARM_TXT)
    note(s, c, "d9", 476, 372, "两版编译都能过, 只有大图上才露馅", size=12)

    run("04-floyd-k-layer", s, c)


# ---------------------------------------------------------------- fig 05
def fig05():
    """Prim and Kruskal: same cut theorem, different way of picking."""
    W, H = 940, 410
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 20, 40, 440, 350)
    panel_title(s, c, "gt", 20, 40, "同一张图, 两法都给出总权重 16")
    pos = {0: (110, 140), 1: (280, 110), 2: (300, 250), 3: (110, 270),
           4: (400, 180)}
    mst = {(0, 1, 4), (0, 3, 3), (2, 3, 2), (2, 4, 7)}
    rest = [(0, 2, 6), (1, 2, 6), (1, 4, 8)]
    offs = {(0, 1): (0, -12), (0, 3): (-16, 0), (2, 3): (0, 16),
            (2, 4): (0, -14), (0, 2): (0, 12), (1, 2): (18, 0),
            (1, 4): (0, -14)}
    for i, (u, v, w) in enumerate(sorted(mst)):
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        edge(s, x1, y1, x2, y2, stroke=TEAL_TXT, sw=3.2)
        ox, oy = offs[(u, v)]
        lab(s, c, f"mw{i}", (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, str(w),
            size=12.5, fill=TEAL_TXT, weight="600")
    for i, (u, v, w) in enumerate(rest):
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        edge(s, x1, y1, x2, y2, stroke=LINE, sw=1.8, dash="5 5")
        ox, oy = offs[(u, v)]
        lab(s, c, f"rw{i}", (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, str(w),
            size=12, fill=MUTED)
    for u, (x, y) in pos.items():
        node(s, c, f"n{u}", x, y, str(u), r=22)
    note(s, c, "g1", 36, 344, "实线 = 选中的边（2+3+4+7=16）", size=12,
         fill=TEAL_TXT)
    note(s, c, "g2", 36, 368, "虚线 = 被判环或已连通而放弃的边", size=12)

    panel(s, c, "k", 480, 40, 210, 350)
    panel_title(s, c, "kt", 480, 40, "Kruskal: 全局排序")
    rows = [("2-3 (2)  ✓", TEAL_TXT), ("0-3 (3)  ✓", TEAL_TXT),
            ("0-1 (4)  ✓", TEAL_TXT), ("0-2 (6)  ✗ 成环", WARM_TXT),
            ("1-2 (6)  ✗ 成环", WARM_TXT), ("2-4 (7)  ✓", TEAL_TXT),
            ("1-4 (8)  ✗ 已连通", WARM_TXT)]
    for i, (t, col) in enumerate(rows):
        note(s, c, f"k{i}", 496, 104 + i * 28, t, size=12.5, fill=col)
    note(s, c, "k7", 496, 330, "排序主导 O(E log E)", size=12)
    note(s, c, "k8", 496, 356, "不连通 → 生成森林", size=12)

    panel(s, c, "p", 710, 40, 210, 350)
    panel_title(s, c, "pt", 710, 40, "Prim: 从一个点长")
    prows = [("已选 {0}", BLUE), ("0-3 (3)  ✓", TEAL_TXT),
             ("3-2 (2)  ✓", TEAL_TXT), ("0-1 (4)  ✓", TEAL_TXT),
             ("2-4 (7)  ✓", TEAL_TXT)]
    for i, (t, col) in enumerate(prows):
        note(s, c, f"p{i}", 726, 104 + i * 28, t, size=12.5, fill=col)
    note(s, c, "p5", 726, 262, "每轮挑最小的横跨边", size=12)
    note(s, c, "p6", 726, 300, "O(V²) 朴素", size=12)
    note(s, c, "p7", 726, 324, "O(E log V) 堆版", size=12)
    note(s, c, "p8", 726, 356, "结果与 Kruskal 同一棵", size=12)

    run("05-prim-vs-kruskal", s, c)


# ---------------------------------------------------------------- fig 06
def fig06():
    """A*: the three measurements, and the 5x5 grid that breaks h."""
    W, H = 960, 424
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 40, 60, 236, 300)
    panel_title(s, c, "gt", 40, 60, "反例网格 5 × 5")
    ox, oy, cs = 74, 116, 36
    walls = {(3, 1), (4, 3)}
    for r in range(5):
        for col in range(5):
            fill = PAPER
            if (r, col) in walls:
                fill = FILL_GREY
            elif (r, col) == (0, 0):
                fill = FILL_TEAL
            elif (r, col) == (4, 4):
                fill = FILL_WARM
            s.cell(ox + col * cs, oy + r * cs, cs, cs, "", fill=fill,
                   stroke=LINE)
    for i in range(5):
        lab(s, c, f"ci{i}", ox + i * cs + cs / 2, oy - 8, str(i), size=11,
            fill=MUTED)
        lab(s, c, f"ri{i}", ox - 12, oy + i * cs + cs / 2 + 4, str(i), size=11,
            fill=MUTED)
    lab(s, c, "s0", ox + 18, oy + 24, "s", size=13, fill=TEAL_TXT,
        weight="600")
    lab(s, c, "t0", ox + 4 * cs + 18, oy + 4 * cs + 24, "t", size=13,
        fill=WARM_TXT, weight="600")
    lab(s, c, "w1", ox + 1 * cs + 18, oy + 3 * cs + 24, "墙", size=11,
        fill=MUTED)
    lab(s, c, "w2", ox + 3 * cs + 18, oy + 4 * cs + 24, "墙", size=11,
        fill=MUTED)
    note(s, c, "g1", 58, 340, "s=(0,0), t=(4,4), 上下左右", size=11.5)

    panel(s, c, "r", 300, 40, 640, 350)
    panel_title(s, c, "rt", 300, 40, "三个实测（都在 verify_code.py 里复跑）")
    note(s, c, "r1", 316, 104, "① h ≡ 0 → 与 1.4 的 dijkstra() 逐格相等  ✓",
         size=12.5, fill=TEAL_TXT)
    note(s, c, "r2", 316, 136, "② h = 曼哈顿 → 答案不变, 扩展格子数变少  ✓",
         size=12.5, fill=TEAL_TXT)
    note(s, c, "r3", 316, 168, "③ h = 3 × 曼哈顿（不可采纳）→ 答案错  ✗",
         size=12.5, fill=WARM_TXT)
    edge(s, 316, 188, 924, 188, stroke=LINE, sw=1.2)
    note(s, c, "r4", 316, 220, "实测三的网格: 墙在 grid[3][1]、grid[4][3],", size=12.5)
    note(s, c, "r5", 316, 246, "起点 (0,0), 终点 (4,4)", size=12.5)
    note(s, c, "r6", 316, 282, "真实最短 = 8 步（一路向右到 (4,0), 再向下）", size=12.5)
    note(s, c, "r7", 316, 310, "h = 3 × 曼哈顿 → 10 步 ✗（扩展 23 → 11）", size=12.5,
         fill=WARM_TXT)
    note(s, c, "r8", 316, 348, "原因: h 高估 ⇒ 终点出队时 f(终点) 已经不是最优",
         size=12)
    note(s, c, "r9", 316, 372, "可采纳 = 永远不高估: h(n) ≤ 真实剩余距离",
         size=12, fill=BLUE)

    run("06-astar-grid", s, c)


# ---------------------------------------------------------------- fig 07
def fig07():
    """Hierholzer: walk, get stuck, record in postorder, reverse."""
    W, H = 960, 410
    s = Svg(W, H)
    c = Check(s)

    panel(s, c, "g", 20, 40, 430, 350)
    panel_title(s, c, "gt", 20, 40, "三角形 + 一条死胡同（6.3 的例子）")
    pos = {0: (120, 210), 1: (250, 120), 2: (250, 300), 3: (370, 210)}
    walk = [(0, 1), (1, 2), (2, 0), (0, 3)]
    for i, (u, v) in enumerate(walk):
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        if i == 3:
            edge(s, x1, y1, x2, y2, stroke=WARM_TXT, sw=3)
        else:
            edge(s, x1, y1, x2, y2, stroke=TEAL_TXT, sw=3)
    lab(s, c, "o1", 176, 146, "①", size=12, fill=TEAL_TXT, weight="600")
    lab(s, c, "o2", 266, 206, "②", size=12, fill=TEAL_TXT, weight="600")
    lab(s, c, "o3", 176, 272, "③", size=12, fill=TEAL_TXT, weight="600")
    lab(s, c, "o4", 250, 194, "④", size=12, fill=WARM_TXT, weight="600")
    for u, (x, y) in pos.items():
        fill = FILL_TEAL if u in (0, 3) else PAPER
        node(s, c, f"n{u}", x, y, str(u), r=22, fill=fill)
    note(s, c, "g1", 36, 344, "度数: 0 是 3、3 是 1（两个奇点）", size=12)
    note(s, c, "g2", 36, 368, "⇒ 必须从 0 出发, 到 3 结束", size=12,
         fill=WARM_TXT)

    panel(s, c, "w", 470, 40, 470, 350)
    panel_title(s, c, "wt", 470, 40, "栈里有路就走, 没路就收尾")
    note(s, c, "w1", 486, 104, "① 0→1  ② 1→2  ③ 2→0（边走边删）", size=12.5)
    note(s, c, "w2", 486, 132, "④ 0 还有 0→3 没走 → 走到 3", size=12.5,
         fill=WARM_TXT)
    note(s, c, "w3", 486, 160, "3 没边了 → 后序记 3", size=12.5)
    note(s, c, "w4", 486, 188, "回到 0, 边也用完 → 后序记 0", size=12.5)
    note(s, c, "w5", 486, 216, "回到 2、1、0 → 依次记 2, 1, 0", size=12.5)
    edge(s, 486, 238, 924, 238, stroke=LINE, sw=1.2)
    note(s, c, "w6", 486, 270, "后序: [3, 0, 2, 1, 0]", size=12.5, fill=INK)
    note(s, c, "w7", 486, 300, "反转: [0, 1, 2, 0, 3]  ← 欧拉路径", size=12.5,
         fill=TEAL_TXT)
    note(s, c, "w8", 486, 340, "反转后相邻两项之间都是一条真实走过的边,", size=12)
    note(s, c, "w9", 486, 364, "每条边只走一次; 走不完 ⇒ 返回 None", size=12)

    run("07-hierholzer", s, c)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (fig01, fig02, fig03, fig04, fig05, fig06, fig07):
        fn()
    print(f"\nTOTAL layout problems: {problems}")
    sys.exit(1 if problems else 0)
