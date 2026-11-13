#!/usr/bin/env python3
"""Regenerate the four SVG figures for the DP-advanced post.

Run:  /opt/miniconda3/bin/python3 make_figures.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent
OUT = BLOG.parent / "img" / "dp-advanced-20261129"
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


# --------------------------------------------------------------- figure 1
def fig_dependency_shapes():
    s = Svg(1000, 500); c = Check(s)
    title(s, c, "三种依赖形态,对应三种压缩手法",
          "能不能压、压成几维，只看 dp[i][j] 到底依赖哪些格子")

    CW, GAP = 58, 10
    rows = [
        (88, "只依赖本行更小下标", ["dp[j-1]", "dp[j]"], "→ 一维就够，正序遍历", FILL_BLUE),
        (216, "只依赖上一行", ["dp[i-1][j]", "dp[i][j]"], "→ 一维就够，但要留住旧值", FILL_WARM),
        (344, "同时依赖上一行和本行", ["dp[i-1][j]", "dp[i][j-1]", "dp[i][j]"],
         "→ 一维不够，必须保留两行", FILL_TEAL),
    ]
    for y, name, cells, verdict, fill in rows:
        s.rect(30, y, 300, 106, fill=fill, stroke=INK, sw=1.3, rx=8)
        c.panel(f"p{y}", 30, y, 300, 106)
        s.text(180, y + 40, name, size=14)
        c.text(f"p{y}:n", 180, y + 40, name, size=14)
        s.text(180, y + 68, verdict, size=11.5, fill=MUTED)
        c.text(f"p{y}:v", 180, y + 68, verdict, size=11.5)
        s.text(180, y + 90, "  ".join(cells), size=10.5, fill=MUTED)
        c.text(f"p{y}:c", 180, y + 90, "  ".join(cells), size=10.5)

    # little 2x3 grid showing read-before-write for the "keep the old value" case
    gx, gy = 430, 216
    note(s, c, "grid-cap", gx, gy - 14,
         "「留住旧值」在代码里长这样：", size=12)
    s.rect(gx, gy, CW * 3 + GAP * 2, CW * 2 + GAP, fill=PAPER, stroke=LINE,
           sw=1, rx=6)
    c.panel("grid", gx, gy, CW * 3 + GAP * 2, CW * 2 + GAP)
    labels = [["i-1, j-1", "", ""], ["i-1, j", "i, j", ""]]
    for r in range(2):
        for col in range(3):
            x = gx + col * (CW + GAP)
            y = gy + r * (CW + GAP)
            s.rect(x, y, CW, CW, fill=FILL_GREY if labels[r][col] else PAPER,
                   stroke=LINE, sw=1.2, rx=5)
            if labels[r][col]:
                s.text(x + CW / 2, y + CW / 2 + 4, labels[r][col], size=9.5)
                c.text(f"g{r}{col}", x + CW / 2, y + CW / 2 + 4, labels[r][col], size=9.5)

    note(s, c, "keep", gx, gy + 150,
         "先存 pre = dp[j] 再覆写 dp[j]，", size=12, fill=WARM_TXT)
    note(s, c, "keep2", gx, gy + 174,
         "否则 dp[i-1][j] 会被本行新值顶掉。", size=12, fill=WARM_TXT)

    note(s, c, "foot", 30, 480,
         "判断顺序永远是：先写清 dp 的递推依赖哪几个格子，再决定维度怎么省——反过来一定出错。",
         size=11.5)
    BAD.append(c.run("01-dependency-shapes"))
    s.save(OUT / "01-dependency-shapes.svg")


# --------------------------------------------------------------- figure 3
def fig_interval_order():
    s = Svg(1000, 700); c = Check(s)
    title(s, c, "区间 DP 的填表顺序:沿长度一层层往外",
          "base case 在主对角线（长度 1），之后按区间长度 2、3、4 依次外推")

    N = 6
    CW, GAP = 62, 10
    x0, y0 = 168, 96
    lens = {1: FILL_BLUE, 2: FILL_TEAL, 3: FILL_WARM, 4: "#efe6f5", 5: FILL_GREY, 6: PAPER}

    # outer loop order: increasing interval length
    order = []
    for L in range(1, N + 1):
        for i in range(0, N - L + 1):
            order.append((i, i + L - 1, L))

    for i, j, L in order:
        x = x0 + j * (CW + GAP)
        y = y0 + i * (CW + GAP)
        s.rect(x, y, CW, CW, fill=lens[L], stroke=INK, sw=1.2, rx=5)
        c.panel(f"c{i}{j}", x, y, CW, CW)
        lbl = str(L)
        s.text(x + CW / 2, y + CW / 2 + 4, lbl, size=13)
        c.text(f"c{i}{j}:l", x + CW / 2, y + CW / 2 + 4, lbl, size=13)

    for i in range(N):
        y = y0 + i * (CW + GAP) + CW / 2
        note(s, c, f"rl{i}", x0 - 16, y + 4, f"i={i}", size=11.5, anchor="end")
    for j in range(N):
        x = x0 + j * (CW + GAP) + CW / 2
        note(s, c, f"cl{j}", x, y0 - 14, f"j={j}", size=11.5, anchor="middle")

    # A legend under the grid instead of in-grid annotations: the cells already
    # print their interval length, and side notes collided with grid rows.
    lx, ly = x0, y0 + N * (CW + GAP) + 18
    note(s, c, "lg-cap", 30, ly + 16, "格子里的数字 = 区间长度：", size=11.5,
         anchor="start")
    for k, (L, col) in enumerate([(1, BLUE), (2, TEAL_TXT), (3, WARM_TXT),
                                  (4, MUTED), (5, MUTED), (6, MUTED)]):
        bx = 250 + k * 118
        s.rect(bx, ly, 26, 20, fill=lens[k + 1], stroke=INK, sw=1, rx=4)
        c.panel(f"lg{k}", bx, ly, 26, 20)
        note(s, c, f"lgt{k}", bx + 34, ly + 16, f"长度 {L}", size=11.5)
    note(s, c, "lg-base", lx, ly + 40,
         "蓝色那一圈（长度 1）就是 base case：单个字符 / 单个元素的区间。",
         size=11.5, fill=BLUE)

    note(s, c, "why", 30, 648,
         "格子里写的是「区间长度」。算长度 L 时只用到长度 L-1 和 L-2 的结果，"
         "所以按 L 从小到大填，用到的格子必然已经算好。", size=11.5)
    note(s, c, "why2", 30, 674,
         "反过来按 i 从小到大填（每行从左到右），长度大的区间会先被访问到，读到空值。",
         size=11.5, fill=WARM_TXT)
    BAD.append(c.run("03-interval-order"))
    s.save(OUT / "03-interval-order.svg")


# --------------------------------------------------------------- figure 4
def fig_stock_states():
    s = Svg(1000, 440); c = Check(s)
    title(s, c, "股票买卖的状态机:两个状态,两条边",
          "「持有 / 不持有」是这张图上仅有的两个节点，交易次数是转移的代价")

    bx, by, bw, bh = 170, 150, 210, 76
    s.rect(bx, by, bw, bh, fill=FILL_BLUE, stroke=BLUE, sw=1.4, rx=9)
    c.panel("nostock", bx, by, bw, bh)
    s.text(bx + bw / 2, by + 34, "不持有", size=16)
    c.text("nostock:l", bx + bw / 2, by + 34, "不持有", size=16)
    s.text(bx + bw / 2, by + 58, "dp[i][0]", size=11.5, fill=MUTED)
    c.text("nostock:s", bx + bw / 2, by + 58, "dp[i][0]", size=11.5)

    hx = 620
    s.rect(hx, by, bw, bh, fill=FILL_WARM, stroke=WARM_TXT, sw=1.4, rx=9)
    c.panel("hold", hx, by, bw, bh)
    s.text(hx + bw / 2, by + 34, "持有", size=16)
    c.text("hold:l", hx + bw / 2, by + 34, "持有", size=16)
    s.text(hx + bw / 2, by + 58, "dp[i][1]", size=11.5, fill=MUTED)
    c.text("hold:s", hx + bw / 2, by + 58, "dp[i][1]", size=11.5)

    # buy: no-stock -> hold, above
    s.arrow(bx + bw, by + 22, hx, by + 22, stroke=WARM_TXT, sw=1.8)
    c.arrow("buy", bx + bw, by + 22, hx, by + 22)
    note(s, c, "buy-l", (bx + bw + hx) / 2, by + 6,
         "买入：不持有 → 持有", size=12, fill=WARM_TXT, anchor="middle")
    note(s, c, "buy-c", (bx + bw + hx) / 2, by + 54,
         "消耗一次额度 k−1，现金 −price", size=11, anchor="middle")

    # sell: hold -> no-stock, below
    s.arrow(hx, by + bh - 22, bx + bw, by + bh - 22, stroke=TEAL_TXT, sw=1.8)
    c.arrow("sell", hx, by + bh - 22, bx + bw, by + bh - 22)
    note(s, c, "sell-l", (bx + bw + hx) / 2, by + bh + 22,
         "卖出：持有 → 不持有", size=12, fill=TEAL_TXT, anchor="middle")
    note(s, c, "sell-c", (bx + bw + hx) / 2, by + bh + 44,
         "结算一次交易，现金 +price", size=11, anchor="middle")

    # self loops
    s.arrow(bx + bw / 2 - 30, by - 30, bx + bw / 2 - 30, by, stroke=LINE, sw=1.5)
    c.arrow("self1", bx + bw / 2 - 30, by - 30, bx + bw / 2 - 30, by)
    note(s, c, "self1-l", bx + bw / 2 - 40, by - 38, "继续观望", size=11,
         anchor="middle")
    s.arrow(hx + bw / 2 + 30, by, hx + bw / 2 + 30, by - 30, stroke=LINE, sw=1.5)
    c.arrow("self2", hx + bw / 2 + 30, by, hx + bw / 2 + 30, by - 30)
    note(s, c, "self2-l", hx + bw / 2 + 40, by - 38, "继续持有", size=11,
         anchor="middle")

    note(s, c, "foot", 30, 400,
         "「买卖股票的最佳时机」整组题只是在这张图上改一件事：额度 k 是无限、还是有限，"
         "以及有没有冷冻期 / 手续费。", size=11.5)
    note(s, c, "foot2", 30, 424,
         "状态数不变，所以状态机画对了，递推式基本是抄下来的。", size=11.5,
         fill=TEAL_TXT)
    BAD.append(c.run("04-stock-states"))
    s.save(OUT / "04-stock-states.svg")


# --------------------------------------------------------------- figure 5
def fig_fenwick_prefix_max():
    s = Svg(1000, 460); c = Check(s)
    title(s, c, "把内层二维查询换成树状数组",
          "下标维度由「扫描顺序」保证，值维度由「前缀查询」保证，两层一叠加就省掉一个 log")

    CW = 74
    x0 = 150

    # before: an LIS-style double loop
    note(s, c, "before-cap", 30, 100,
         "优化前：每个 i 都要回看所有 j < i，并检查 nums[j] < nums[i]", size=12.5)
    y = 118
    for i in range(5):
        s.rect(x0 + i * (CW + 16), y, CW, 40, fill=FILL_WARM, stroke=WARM_TXT,
               sw=1.3, rx=6)
        c.panel(f"b{i}", x0 + i * (CW + 16), y, CW, 40)
        s.text(x0 + i * (CW + 16) + CW / 2, y + 26, f"nums[{i}]", size=12)
        c.text(f"b{i}:l", x0 + i * (CW + 16) + CW / 2, y + 26, f"nums[{i}]", size=12)
    for i in range(1, 5):
        s.arrow(x0 + i * (CW + 16) + CW / 2, y + 46,
                x0 + (CW + 16) / 2 + CW / 2 - 20, y + 70,
                stroke=WARM_TXT, sw=1.2, dash="4 3")
        c.arrow(f"ba{i}", x0 + i * (CW + 16) + CW / 2, y + 46,
                x0 + (CW + 16) / 2 + CW / 2 - 20, y + 70)
    note(s, c, "before-cost", x0, y + 96, "代价：O(n²) —— 内层每次都是一次线性回看",
         size=11.5, fill=WARM_TXT)

    # after: a Fenwick tree over the value dimension
    note(s, c, "after-cap", 30, 268,
         "优化后：把「值」当作树状数组的下标，查询变成前缀 max", size=12.5)
    ty = 300
    tn = 8
    tw = 62
    tx0 = 150
    for k in range(1, tn + 1):
        x = tx0 + (k - 1) * (tw + 10)
        fill = FILL_TEAL if k in (1, 2, 4, 8) else PAPER
        # tree height cue: lowbit determines which range a node covers
        low = k & (-k)
        s.rect(x, ty, tw, 46, fill=fill, stroke=INK, sw=1.2, rx=5)
        c.panel(f"t{k}", x, ty, tw, 46)
        s.text(x + tw / 2, ty + 22, f"[{k}]", size=13)
        c.text(f"t{k}:l", x + tw / 2, ty + 22, f"[{k}]", size=13)
        s.text(x + tw / 2, ty + 38, f"管{low}格", size=9.5, fill=MUTED)
        c.text(f"t{k}:s", x + tw / 2, ty + 38, f"管{low}格", size=9.5)

    # query path: 7 -> 6 -> 4
    for a, b in ((7, 6), (6, 4)):
        xa = tx0 + (a - 1) * (tw + 10) + tw / 2
        xb = tx0 + (b - 1) * (tw + 10) + tw / 2
        s.arrow(xa, ty + 56, xb, ty + 56, stroke=TEAL_TXT, sw=1.5)
        c.arrow(f"q{a}{b}", xa, ty + 56, xb, ty + 56)
    note(s, c, "qpath", tx0 + 6 * (tw + 10), ty + 82,
         "查询前缀 max：7 → 7−lowbit(7)=6 → 6−lowbit(6)=4 → 0，只要 3 步",
         size=11.5, fill=TEAL_TXT, anchor="middle")

    note(s, c, "why", 30, 428,
         "lowbit(k) = k & (−k) 就是 k 管辖的格子数。每次减去 lowbit 恰好剥掉一层管辖范围，"
         "所以前缀查询只走 log n 步。", size=11.5)
    note(s, c, "why2", 30, 450,
         "代价：一次查询 O(log n)，总体从 O(n²) 降到 O(n log n)。", size=11.5,
         fill=TEAL_TXT)
    BAD.append(c.run("05-fenwick-prefix-max"))
    s.save(OUT / "05-fenwick-prefix-max.svg")


# 各图 Check.run() 返回的问题数累计在这里。用 list 而不是 int：
# 函数内部对 int 做 += 会被当成局部变量，得每处写 global，容易漏。
BAD: list[int] = []


if __name__ == "__main__":
    fig_dependency_shapes()
    fig_interval_order()
    fig_stock_states()
    fig_fenwick_prefix_max()
    total = sum(BAD)
    print(f"  layout problem(s): {total}")
    sys.exit(1 if total else 0)
