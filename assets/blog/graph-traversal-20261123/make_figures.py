#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the 9 figures for _posts/2026-11-23-graph-traversal.md.

Every text label and arrow is registered with svgkit.Check, which catches
text/text collisions, text/arrow collisions, off-canvas text and text that
spills out of its panel.  Lines are not visible to Check, so the renders are
also looked at by eye (sips -> png).

Run:  python3 assets/blog/graph-traversal-20261123/make_figures.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "assets", "blog", "_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = os.path.join(ROOT, "assets", "img", "graph-traversal-20261123")

problems = 0


class Panels:
    """Panel-spill check, local because svgkit's Check.run() has an index bug.

    Check.text() stores hitboxes as (name, x0, y0, x1, y1), but run()'s
    panel-spill step computes `cx = (a[1] + a[2]) / 2`, which averages x0 with
    y0, and then tests `a[2] > p[3] - 2`, i.e. compares a text's y0 against a
    panel's x1.  Both are wrong, and the result is that it fires on text that
    is nowhere near the panel it names (it flagged a footnote at y=300 as
    "spilling out of" a panel spanning x 20..270).  svgkit is a shared file, so
    rather than edit it mid-flight we redo the check correctly here.
    """

    def __init__(self):
        self.ps = []

    def add(self, name, x, y, w, h):
        self.ps.append((name, x, y, x + w, y + h))
        return self

    def check(self, c):
        bad = []
        for name, px0, py0, px1, py1 in self.ps:
            for a in c.texts:
                x0, y0, x1, y1 = a[1], a[2], a[3], a[4]
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if px0 <= cx <= px1 and py0 <= cy <= py1:
                    if x0 < px0 + 2 or x1 > px1 - 2:
                        bad.append(f"text spills out of {name!r}: {a[0]!r} "
                                   f"x {x0:.0f}..{x1:.0f} vs panel "
                                   f"{px0:.0f}..{px1:.0f}")
        return bad


# ---------------------------------------------------------------- helpers
def lab(s, c, name, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Draw a text label and register it with Check."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)


def node(s, c, name, x, y, t, r=20, fill=PAPER, stroke=INK, size=15):
    s.circle(x, y, r, fill=fill, stroke=stroke, sw=1.6)
    lab(s, c, name, x, y + size * 0.36, t, size=size, weight="600")


def edge(s, x1, y1, x2, y2, stroke=INK, sw=1.6):
    s.line(x1, y1, x2, y2, stroke=stroke, sw=sw)


def dart(s, c, name, x1, y1, x2, y2, r=22, stroke=BLUE, sw=1.8):
    """Arrow between two nodes, trimmed to the node borders so its bounding
    box does not swallow either node's label."""
    import math
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    ax, ay = x1 + ux * r, y1 + uy * r
    bx, by = x2 - ux * r, y2 - uy * r
    s.arrow(ax, ay, bx, by, stroke=stroke, sw=sw)
    c.arrow(name, ax, ay, bx, by)


def panel_title(s, c, name, px, py, t, size=13):
    lab(s, c, name, px + 12, py + 24, t, size=size, anchor="start",
        weight="600", fill=BLUE)


def note(s, c, name, x, y, t, size=12, fill=MUTED, anchor="start"):
    lab(s, c, name, x, y, t, size=size, fill=fill, anchor=anchor)


def run(name, s, c, P):
    global problems
    bad = c.run(name) + len(P.check(c))
    problems += bad
    s.save(os.path.join(OUT, name + ".svg"))


# ---------------------------------------------------------------- fig 01
def fig01():
    W, H = 900, 440
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    # A. the graph itself
    s.panel(20, 40, 250, 210)
    P.add("graph-panel", 20, 40, 250, 210)
    panel_title(s, c, "graph-title", 20, 40, "同一个无向图: V=4, E=3")
    pos = {0: (85, 120), 1: (195, 120), 2: (85, 210), 3: (195, 210)}
    for a, b in [(0, 1), (0, 2), (1, 3)]:
        edge(s, pos[a][0], pos[a][1], pos[b][0], pos[b][1])
    for u, (x, y) in pos.items():
        node(s, c, f"node{u}", x, y, str(u))

    # B. adjacency list
    s.panel(290, 40, 260, 210)
    P.add("list-panel", 290, 40, 260, 210)
    panel_title(s, c, "list-title", 290, 40, "邻接表 graph[u]")
    rows = ["0 -> [1, 2]", "1 -> [0, 3]", "2 -> [0]", "3 -> [1]"]
    for i, t in enumerate(rows):
        note(s, c, f"list-row{i}", 306, 100 + i * 30, t, size=13, fill=INK)

    # C. adjacency matrix
    s.panel(570, 40, 310, 210)
    P.add("mat-panel", 570, 40, 310, 210)
    panel_title(s, c, "mat-title", 570, 40, "邻接矩阵 m[u][v]")
    ox, oy, cs = 640, 95, 32
    for i in range(4):
        lab(s, c, f"mat-col{i}", ox + cs * i + cs / 2, oy - 8, str(i),
            size=12, fill=MUTED)
        lab(s, c, f"mat-row{i}", ox - 14, oy + cs * i + cs / 2 + 4, str(i),
            size=12, fill=MUTED)
    ones = {(0, 1), (1, 0), (0, 2), (2, 0), (1, 3), (3, 1)}
    for i in range(4):
        for j in range(4):
            hot = (i, j) in ones
            # label drawn once, by lab() below, so that Check can see it
            s.cell(ox + cs * j, oy + cs * i, cs, cs, "",
                   fill=FILL_BLUE if hot else PAPER, stroke=LINE)
            lab(s, c, f"mat{i}{j}", ox + cs * j + cs / 2,
                oy + cs * i + cs / 2 + 4, "1" if hot else "0", size=13,
                fill=BLUE if hot else MUTED)

    # D. cost band
    s.panel(20, 280, 250, 140)
    P.add("cost-a", 20, 280, 250, 140)
    panel_title(s, c, "cost-a-t", 20, 280, "邻接表的代价")
    note(s, c, "cost-a1", 34, 330, "空间 O(V+E)", size=13, fill=INK)
    note(s, c, "cost-a2", 34, 356, "查 u-v 有无边 O(deg u)", size=13, fill=INK)
    note(s, c, "cost-a3", 34, 382, "枚举邻居 O(deg u)", size=13, fill=INK)
    note(s, c, "cost-a4", 34, 408, "遍历整图 O(E+V)", size=13, fill=TEAL_TXT)

    s.panel(290, 280, 260, 140)
    P.add("cost-b", 290, 280, 260, 140)
    panel_title(s, c, "cost-b-t", 290, 280, "邻接矩阵的代价")
    note(s, c, "cost-b1", 304, 330, "空间 O(V^2)", size=13, fill=INK)
    note(s, c, "cost-b2", 304, 356, "查 u-v 有无边 O(1)", size=13, fill=INK)
    note(s, c, "cost-b3", 304, 382, "枚举邻居 O(V)", size=13, fill=INK)
    note(s, c, "cost-b4", 304, 408, "遍历整图 O(V^2)", size=13, fill=TEAL_TXT)

    s.panel(570, 280, 310, 140, fill=FILL_WARM, stroke=FILL_WARM)
    P.add("pick", 570, 280, 310, 140)
    lab(s, c, "pick-t", 582, 304, "怎么选", size=13, anchor="start",
        weight="600", fill=WARM_TXT)
    note(s, c, "pick1", 582, 334, "简单图里 0 <= E <= V(V-1)/2", size=13,
         fill=INK)
    note(s, c, "pick2", 582, 360, "E 接近 V^2 -> 稠密 -> 矩阵", size=13,
         fill=INK)
    note(s, c, "pick3", 582, 386, "E 远小于 V^2 -> 稀疏 -> 邻接表", size=13,
         fill=INK)
    note(s, c, "pick4", 582, 410, "要三层循环的算法(Floyd)偏爱矩阵", size=12,
         fill=WARM_TXT)

    run("01-adjacency-list-vs-matrix", s, c, P)


# ---------------------------------------------------------------- fig 02
def fig02():
    W, H = 900, 400
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    s.panel(20, 30, 300, 340)
    P.add("g", 20, 30, 300, 340)
    panel_title(s, c, "g-t", 20, 30, "同一个图, 从节点 0 出发")
    pos = {0: (170, 90), 1: (95, 200), 2: (245, 200),
           3: (60, 300), 4: (140, 300)}
    for a, b in [(0, 1), (0, 2), (1, 3), (1, 4)]:
        edge(s, pos[a][0], pos[a][1], pos[b][0], pos[b][1])
    for u, (x, y) in pos.items():
        node(s, c, f"n{u}", x, y, str(u), r=19)
    note(s, c, "g-note", 36, 356, "邻接表插入顺序: 0:[1,2] 1:[0,3,4]",
         size=11)

    # DFS column
    s.panel(350, 30, 250, 340)
    P.add("dfs", 350, 30, 250, 340)
    panel_title(s, c, "dfs-t", 350, 30, "DFS: 栈顶取")
    lab(s, c, "dfs-sub", 475, 82, "访问序 = 前序位置", size=12, fill=MUTED)
    dfs_rows = ["栈: [0]", "弹 0 -> 逆序压 2,1", "弹 1 -> 逆序压 4,3",
                "弹 3", "弹 4", "弹 2"]
    for i, t in enumerate(dfs_rows):
        note(s, c, f"dfs{i}", 368, 118 + i * 32, t, size=13, fill=INK)
    s.rect(360, 312, 230, 46, fill=FILL_WARM, stroke=FILL_WARM, rx=6)
    lab(s, c, "dfs-res", 475, 341, "0 1 3 4 2", size=15, weight="600",
        fill=WARM_TXT)

    # BFS column
    s.panel(630, 30, 250, 340)
    P.add("bfs", 630, 30, 250, 340)
    panel_title(s, c, "bfs-t", 630, 30, "BFS: 队头取")
    lab(s, c, "bfs-sub", 755, 82, "dist[] 既去重又记层", size=12, fill=MUTED)
    bfs_rows = ["队: [0]  dist0=0", "出 0 -> 1,2 dist=1",
                "出 1 -> 3,4 dist=2", "出 2", "出 3", "出 4"]
    for i, t in enumerate(bfs_rows):
        note(s, c, f"bfs{i}", 648, 118 + i * 32, t, size=13, fill=INK)
    s.rect(640, 312, 230, 46, fill=FILL_TEAL, stroke=FILL_TEAL, rx=6)
    lab(s, c, "bfs-res", 755, 341, "0 1 2 3 4", size=15, weight="600",
        fill=TEAL_TXT)

    run("02-dfs-vs-bfs-order", s, c, P)


# ---------------------------------------------------------------- fig 03
def fig03():
    W, H = 900, 400
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    s.panel(20, 24, 860, 96)
    P.add("r1", 20, 24, 860, 96)
    lab(s, c, "r1-h", 40, 52, "visited[u]", size=14, anchor="start",
        weight="600", fill=BLUE)
    lab(s, c, "r1-k", 40, 78, "进入时置位, 永不撤销", size=12, anchor="start",
        fill=MUTED)
    lab(s, c, "r1-q", 40, 102, "回答: 我来过这里吗", size=12, anchor="start",
        fill=INK)
    note(s, c, "r1-u", 460, 66, "遍历所有节点 / 求连通分量 / 可达性",
         size=13, fill=INK)
    note(s, c, "r1-u2", 460, 92, "每个节点只处理一次 -> O(E+V)",
         size=12, fill=TEAL_TXT)

    s.panel(20, 136, 860, 96)
    P.add("r2", 20, 136, 860, 96)
    lab(s, c, "r2-h", 40, 164, "onPath[u]", size=14, anchor="start",
        weight="600", fill=WARM_TXT)
    lab(s, c, "r2-k", 40, 190, "进入时置位, 离开时清除", size=12,
        anchor="start", fill=MUTED)
    lab(s, c, "r2-q", 40, 214, "回答: 我现在站在这里吗", size=12,
        anchor="start", fill=INK)
    note(s, c, "r2-u", 460, 178, "有向图判环 / 枚举所有路径",
         size=13, fill=INK)
    note(s, c, "r2-u2", 460, 204, "配合 visited 才能剪枝到 O(E+V)",
         size=12, fill=WARM_TXT)

    s.panel(20, 248, 860, 96)
    P.add("r3", 20, 248, 860, 96)
    lab(s, c, "r3-h", 40, 276, "visited[u][v]", size=14, anchor="start",
        weight="600", fill=TEAL_TXT)
    lab(s, c, "r3-k", 40, 302, "走过这条边时置位", size=12, anchor="start",
        fill=MUTED)
    lab(s, c, "r3-q", 40, 326, "回答: 这条边走过吗", size=12, anchor="start",
        fill=INK)
    note(s, c, "r3-u", 460, 290, "欧拉路径 / 无向图枚举路径",
         size=13, fill=INK)
    note(s, c, "r3-u2", 460, 316, "标记要放进 for 内部, 因为边有两个端点",
         size=12, fill=INK)
    note(s, c, "r3-u3", 460, 338, "代价: 时间 O(E+V^2), 空间 O(V^2)",
         size=12, fill=MUTED)

    run("03-three-marks", s, c, P)


# ---------------------------------------------------------------- fig 04
def fig04():
    W, H = 900, 420
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    # Left: a DAG, all black
    s.panel(20, 30, 400, 360)
    P.add("dag", 20, 30, 400, 360)
    panel_title(s, c, "dag-t", 20, 30, "无环: 走到黑节点不算环")
    dpos = {0: (110, 130), 1: (250, 130), 2: (110, 250), 3: (250, 250)}
    for a, b in [(0, 1), (0, 2), (1, 3), (2, 3)]:
        dart(s, c, f"dag-a{a}{b}", dpos[a][0], dpos[a][1],
             dpos[b][0], dpos[b][1])
    # 0 and 2 are still on the path (grey); 1 and 3 are already finished
    # (black) by the time 2 -> 3 is examined.
    for u, (x, y) in dpos.items():
        done = u in (1, 3)
        node(s, c, f"dag-n{u}", x, y, str(u),
             fill=FILL_GREY if done else FILL_WARM,
             stroke=MUTED if done else WARM_TXT)
    note(s, c, "dag-1", 40, 316, "灰 = 还在当前路径上; 深灰 = 已完成",
         size=12, fill=INK)
    note(s, c, "dag-2", 40, 342, "查 2 -> 3 时 3 已是深灰", size=13,
         fill=INK)
    note(s, c, "dag-3", 40, 368, "-> 回不到当前路径, 不构成环", size=12,
         fill=TEAL_TXT)

    # Right: a cycle, gray hit
    s.panel(450, 30, 430, 360)
    P.add("cyc", 450, 30, 430, 360)
    panel_title(s, c, "cyc-t", 450, 30, "有环: 撞到灰节点即有环")
    cpos = {0: (530, 120), 1: (730, 120), 2: (730, 260), 3: (560, 274)}
    for a, b in [(0, 1), (1, 2), (2, 3)]:
        dart(s, c, f"cyc-a{a}{b}", cpos[a][0], cpos[a][1],
             cpos[b][0], cpos[b][1], stroke=WARM_TXT)
    # the closing edge 3 -> 0 is the one that hits a grey node
    dart(s, c, "cyc-a30", cpos[3][0], cpos[3][1],
         cpos[0][0], cpos[0][1], stroke=INK, sw=2.6)
    for u in range(4):
        node(s, c, f"cyc-n{u}", cpos[u][0], cpos[u][1], str(u),
             fill=FILL_WARM, stroke=WARM_TXT)
    note(s, c, "cyc-l", 470, 316, "走的路径是 0-1-2-3, 四个点都还在路上",
         size=12, fill=INK)
    note(s, c, "cyc-l2", 470, 342, "查 3 -> 0 时 0 还在路上 (粗箭头)",
         size=12, fill=INK)
    note(s, c, "cyc-l3", 470, 368, "-> 拼成一个环 0-1-2-3-0", size=12,
         fill=WARM_TXT)

    run("04-cycle-three-colors", s, c, P)


# ---------------------------------------------------------------- fig 05
def fig05():
    W, H = 900, 430
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    # shared DAG
    s.panel(20, 30, 300, 370)
    P.add("g", 20, 30, 300, 370)
    panel_title(s, c, "g-t", 20, 30, "要排序的 DAG")
    pos = {0: (110, 110), 1: (230, 110), 2: (110, 230), 3: (230, 230)}
    for a, b in [(0, 1), (0, 2), (1, 3), (2, 3)]:
        dart(s, c, f"g-a{a}{b}", pos[a][0], pos[a][1], pos[b][0], pos[b][1])
    for u, (x, y) in pos.items():
        node(s, c, f"g-n{u}", x, y, str(u))
    note(s, c, "g-e", 40, 320, "边 = 被依赖: 0 -> 1 表示", size=12, fill=INK)
    note(s, c, "g-e2", 40, 344, "做完 0 才能做 1", size=12, fill=INK)
    note(s, c, "g-e3", 40, 372, "入度: 0:0  1:1  2:1  3:2", size=12,
         fill=MUTED)

    # DFS side
    s.panel(340, 30, 270, 370)
    P.add("d", 340, 30, 270, 370)
    panel_title(s, c, "d-t", 340, 30, "DFS: 后序 + 反转")
    rows = ["离开 3 -> post=[3]",
            "离开 1 -> post=[3,1]",
            "离开 2 -> post=[3,1,2]",
            "离开 0 -> post=[3,1,2,0]"]
    for i, t in enumerate(rows):
        note(s, c, f"d{i}", 358, 92 + i * 30, t, size=13, fill=INK)
    note(s, c, "d-x", 358, 224, "post 的性质: 每条边 u->v", size=12,
         fill=MUTED)
    note(s, c, "d-x2", 358, 246, "都有 v 排在 u 前面", size=12, fill=MUTED)
    s.rect(352, 276, 246, 50, fill=FILL_WARM, stroke=FILL_WARM, rx=6)
    lab(s, c, "d-r", 475, 292, "反转 post", size=11, fill=WARM_TXT)
    lab(s, c, "d-r2", 475, 314, "0 2 1 3", size=16, weight="600",
        fill=WARM_TXT)
    note(s, c, "d-y", 358, 356, "撞到灰 -> 直接返回空", size=12,
         fill=WARM_TXT)

    # Kahn side
    s.panel(630, 30, 250, 370)
    P.add("k", 630, 30, 250, 370)
    panel_title(s, c, "k-t", 630, 30, "Kahn: 入度归零")
    krows = ["入度 0 的入队: [0]",
             "出 0 -> 1,2 入度 0", "入队 [1,2]",
             "出 1 -> 3 入度 1", "出 2 -> 3 入度 0",
             "出 3"]
    for i, t in enumerate(krows):
        note(s, c, f"k{i}", 648, 92 + i * 30, t, size=13, fill=INK)
    s.rect(642, 276, 226, 50, fill=FILL_TEAL, stroke=FILL_TEAL, rx=6)
    lab(s, c, "k-r", 755, 292, "出队顺序", size=11, fill=TEAL_TXT)
    lab(s, c, "k-r2", 755, 314, "0 1 2 3", size=16, weight="600",
        fill=TEAL_TXT)
    note(s, c, "k-y", 648, 356, "出队数 < V -> 有环", size=12, fill=TEAL_TXT)

    run("05-topo-dfs-vs-kahn", s, c, P)


# ---------------------------------------------------------------- fig 06
def fig06():
    """Kahn, step by step: 4 rounds with the live in-degree table."""
    W, H = 900, 450
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    steps = [
        ("初始", [0, 1, 1, 2], "队: [0]", "入度 0 的只有 0"),
        ("第 1 轮", [-1, 0, 0, 2], "队: [1, 2]", "出 0, 1 和 2 归零"),
        ("第 2 轮", [-1, -1, -1, 1], "队: [2]", "出 1, 3 减到 1"),
        ("第 3 轮", [-1, -1, -1, 0], "队: [3]", "出 2, 3 归零"),
    ]
    bw, gap = 205, 15
    for i, (title, deg, q, desc) in enumerate(steps):
        x = 25 + i * (bw + gap)
        s.panel(x, 40, bw, 300)
        P.add(f"s{i}", x, 40, bw, 300)
        lab(s, c, f"s{i}-t", x + bw / 2, 68, title, size=14, weight="600",
            fill=BLUE)
        # in-degree row for nodes 0..3
        cx = x + 32
        for j in range(4):
            v = deg[j]
            hot = v == 0
            fill = FILL_WARM if hot else (FILL_GREY if v < 0 else PAPER)
            stroke = WARM_TXT if hot else (LINE if v < 0 else INK)
            s.cell(cx + j * 36, 96, 36, 40, "",
                   fill=fill, stroke=stroke)
            lab(s, c, f"s{i}-c{j}", cx + j * 36 + 18, 122,
                str(v) if v >= 0 else "-", size=13,
                fill=WARM_TXT if hot else (MUTED if v < 0 else INK))
        lab(s, c, f"s{i}-hdr", x + bw / 2, 158, "节点 0 1 2 3 的入度",
            size=11, fill=MUTED)
        s.rect(x + 14, 180, bw - 28, 44, fill=FILL_BLUE, stroke=FILL_BLUE,
               rx=6)
        lab(s, c, f"s{i}-q", x + bw / 2, 207, q, size=13, weight="600",
            fill=BLUE)
        lab(s, c, f"s{i}-d", x + bw / 2, 258, desc, size=12, fill=INK)
        lab(s, c, f"s{i}-o", x + bw / 2, 300, f"order = {i} 个",
            size=12, fill=TEAL_TXT)

    note(s, c, "f6-foot", 25, 380,
         "每轮把入度归零的节点入队; 出队时把它的后继入度减 1。"
         "出队总数 == V 才存在拓扑序。", size=13, fill=INK)
    note(s, c, "f6-foot2", 25, 408,
         "如果有环 (例如 1 -> 2 -> 1), 这两个节点的入度永远减不到 0, "
         "出队总数就会小于 V。", size=13, fill=WARM_TXT)

    run("06-kahn-steps", s, c, P)


# ---------------------------------------------------------------- fig 07
def fig07():
    W, H = 900, 420
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    # even cycle -> bipartite
    s.panel(20, 30, 420, 360)
    P.add("bi", 20, 30, 420, 360)
    panel_title(s, c, "bi-t", 20, 30, "偶环: 可以二染色")
    bpos = {0: (110, 120), 1: (250, 120), 2: (250, 260), 3: (110, 260)}
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
        edge(s, bpos[a][0], bpos[a][1], bpos[b][0], bpos[b][1], stroke=BLUE)
    fills = {0: FILL_BLUE, 1: FILL_WARM, 2: FILL_BLUE, 3: FILL_WARM}
    strokes = {0: BLUE, 1: WARM_TXT, 2: BLUE, 3: WARM_TXT}
    for u, (x, y) in bpos.items():
        node(s, c, f"bi-n{u}", x, y, str(u), fill=fills[u], stroke=strokes[u])
    note(s, c, "bi-l", 40, 316, "走 4 条边回到起点, 颜色翻转 4 次",
         size=13, fill=INK)
    note(s, c, "bi-l2", 40, 342, "偶数次翻转 -> 回到原色, 自洽", size=13,
         fill=TEAL_TXT)
    note(s, c, "bi-l3", 40, 370, "所以是二分图 (785 例 2)", size=12,
         fill=MUTED)

    # odd cycle -> not bipartite
    s.panel(470, 30, 410, 360)
    P.add("tri", 470, 30, 410, 360)
    panel_title(s, c, "tri-t", 470, 30, "奇环: 一定不是二分图")
    tpos = {0: (600, 140), 1: (760, 140), 2: (680, 280)}
    for a, b in [(0, 1), (1, 2), (2, 0)]:
        edge(s, tpos[a][0], tpos[a][1], tpos[b][0], tpos[b][1], stroke=WARM_TXT)
    node(s, c, "tri-n0", tpos[0][0], tpos[0][1], "0", fill=FILL_WARM,
         stroke=WARM_TXT)
    node(s, c, "tri-n1", tpos[1][0], tpos[1][1], "1", fill=FILL_BLUE,
         stroke=BLUE)
    node(s, c, "tri-n2", tpos[2][0], tpos[2][1], "2", fill=FILL_WARM,
         stroke=WARM_TXT)
    note(s, c, "tri-l", 490, 316, "0 和 2 都染成 A 色, 但它们相邻",
         size=13, fill=INK)
    note(s, c, "tri-l2", 490, 342, "染色法在这里报冲突 -> 返回 false",
         size=13, fill=WARM_TXT)
    note(s, c, "tri-l3", 490, 370, "等价说法: 有奇环 (785 例 1)", size=12,
         fill=MUTED)

    run("07-bipartite-coloring", s, c, P)


# ---------------------------------------------------------------- fig 08
def fig08():
    W, H = 900, 440
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    # naive: a chain
    s.panel(20, 30, 420, 380)
    P.add("chain", 20, 30, 420, 380)
    panel_title(s, c, "chain-t", 20, 30, "朴素: 退化成一条链")
    xs = [80, 160, 240, 320, 400]
    for i, x in enumerate(xs):
        node(s, c, f"ch{i}", x, 130, str(i), r=19,
             fill=FILL_GREY if i else FILL_BLUE,
             stroke=MUTED if i else BLUE)
    for i in range(4):
        dart(s, c, f"ch-a{i}", xs[i], 130, xs[i + 1], 130,
             r=20, stroke=MUTED, sw=1.5)
    lab(s, c, "ch-hdr", 240, 90, "parent 指针", size=12, fill=MUTED)
    note(s, c, "ch-1", 40, 200, "union(0,1) union(1,2) union(2,3) ...",
         size=12, fill=INK)
    note(s, c, "ch-2", 40, 228, "每次都把 p 的根挂到 q 的根下面", size=12,
         fill=INK)
    note(s, c, "ch-3", 40, 274, "find(0) 要爬 4 层", size=13, fill=WARM_TXT)
    note(s, c, "ch-4", 40, 300, "n 个节点最坏 O(n)", size=12, fill=MUTED)
    note(s, c, "ch-5", 40, 344, "只做路径压缩也不够: union 还能", size=12,
         fill=INK)
    note(s, c, "ch-6", 40, 368, "把大树挂到小树下, 重新造深树", size=12,
         fill=INK)

    # optimized: flat forest
    s.panel(470, 30, 410, 380)
    P.add("flat", 470, 30, 410, 380)
    panel_title(s, c, "flat-t", 470, 30, "两个优化都加上")
    root = (600, 130)
    node(s, c, "fl-r", root[0], root[1], "0", r=21, fill=FILL_TEAL,
         stroke=TEAL_TXT)
    kids = [(520, 240), (600, 250), (680, 240)]
    for i, (x, y) in enumerate(kids):
        dart(s, c, f"fl-a{i}", x, y, root[0], root[1], r=22,
             stroke=TEAL_TXT, sw=1.5)
        node(s, c, f"fl-k{i}", x, y, str(i + 1), r=19, fill=FILL_TEAL,
             stroke=TEAL_TXT)
    lab(s, c, "fl-hdr", 600, 320, "路径压缩后: 全部直接挂在根上",
        size=12, fill=TEAL_TXT)
    note(s, c, "fl-1", 490, 356, "按秩合并保证树高 O(log n)", size=12,
         fill=INK)
    note(s, c, "fl-2", 490, 380, "路径压缩保证爬过的路只爬一次", size=12,
         fill=INK)
    note(s, c, "fl-3", 490, 404, "合起来摊还 O(alpha(n)) <= O(1)",
         size=12, fill=TEAL_TXT)

    run("08-unionfind-optimizations", s, c, P)


# ---------------------------------------------------------------- fig 09
def fig09():
    W, H = 900, 400
    s = Svg(W, H)
    c = Check(s)
    P = Panels()

    s.panel(20, 30, 500, 340)
    P.add("rc", 20, 30, 500, 340)
    panel_title(s, c, "rc-t", 20, 30, "edges = [[1,2],[1,3],[2,3]]")
    pos = {1: (170, 140), 2: (330, 140), 3: (250, 280)}
    edge(s, pos[1][0], pos[1][1], pos[2][0], pos[2][1], stroke=INK)
    edge(s, pos[1][0], pos[1][1], pos[3][0], pos[3][1], stroke=INK)
    edge(s, pos[2][0], pos[2][1], pos[3][0], pos[3][1], stroke=WARM_TXT,
         sw=2.6)
    for u, (x, y) in pos.items():
        fill = FILL_WARM if u == 3 else PAPER
        node(s, c, f"rc-n{u}", x, y, str(u), fill=fill)
    lab(s, c, "rc-hi", 250, 210, "这条边多余", size=12, fill=WARM_TXT)
    note(s, c, "rc-1", 40, 320, "加入 (1,2): 合并成功", size=12, fill=INK)
    note(s, c, "rc-2", 40, 344, "加入 (1,3): 合并成功", size=12, fill=INK)

    s.panel(550, 30, 330, 340)
    P.add("uf", 550, 30, 330, 340)
    panel_title(s, c, "uf-t", 550, 30, "并查集判环")
    note(s, c, "uf-1", 568, 82, "加入 (1,2) -> union 返回 true", size=12,
         fill=INK)
    note(s, c, "uf-2", 568, 110, "加入 (1,3) -> union 返回 true", size=12,
         fill=INK)
    note(s, c, "uf-3", 568, 138, "加入 (2,3) -> 2 和 3 已连通", size=12,
         fill=INK)
    note(s, c, "uf-4", 568, 166, "union 返回 false", size=13, fill=WARM_TXT)
    s.rect(562, 194, 306, 52, fill=FILL_WARM, stroke=FILL_WARM, rx=6)
    lab(s, c, "uf-5", 715, 214, "返回 false 的那一刻", size=11,
        fill=WARM_TXT)
    lab(s, c, "uf-6", 715, 236, "就是多余的边 [2,3]", size=14, weight="600",
        fill=WARM_TXT)
    note(s, c, "uf-7", 568, 286, "不需要额外判环: 树上两点", size=12,
         fill=INK)
    note(s, c, "uf-8", 568, 310, "之间本来就只有一条路径", size=12,
         fill=INK)
    note(s, c, "uf-9", 568, 346, "同一个判断也是 Kruskal 的零件", size=12,
         fill=TEAL_TXT)

    run("09-redundant-connection", s, c, P)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09):
        fn()
    print(f"\nTOTAL layout problems: {problems}")
    sys.exit(1 if problems else 0)
