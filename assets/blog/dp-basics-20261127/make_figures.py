#!/usr/bin/env python3
"""生成 dp-basics 这篇的 5 张图。

每个文字标签都在 `Check` 里登记一次,越界和碰撞会直接报出来。
另外生成完必须自己渲染看一眼 —— Check 查不到「文字压在没登记的线上」。

    python3 assets/blog/dp-basics-20261127/make_figures.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "assets/blog/_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,   # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/dp-basics-20261127"
OUT.mkdir(parents=True, exist_ok=True)

BAD = 0


def fig1():
    """斐波那契递归树:f(3)/f(2) 被两条路径分别算了一遍。"""
    global BAD
    s = Svg(1240, 620)
    c = Check(s)

    s.text(620, 36, "算 f(5) 的递归树:同一棵子树被两条路径各算了一遍",
           size=17, weight="600")
    c.text("title", 620, 36, "算 f(5) 的递归树:同一棵子树被两条路径各算了一遍", size=17)
    s.text(620, 60, "橙色虚线标出「重复访问同一个状态」的那条路径",
           size=12, fill=MUTED)
    c.text("subtitle", 620, 60, "橙色虚线标出「重复访问同一个状态」的那条路径", size=12)

    # 节点按网格摆放:同一层的所有方框不重叠,连线先画、方框后画盖住线头
    NW, NH = 84, 56
    nodes = [
        (620, 120, "f(5)", None),
        (430, 210, "f(4)", None), (760, 210, "f(3)", "warm"),
        (178, 290, "f(3)", "warm"), (400, 290, "f(2)", "warm"),
        (640, 290, "f(2)", "warm"), (910, 290, "f(1)", None),
        (178, 380, "f(2)", "warm"), (310, 380, "f(1)", None),
        (478, 380, "f(1)", None),   (610, 380, "f(0)", None),
        (778, 380, "f(1)", None),   (910, 380, "f(0)", None),
        (178, 470, "f(1)", None),   (178, 560, "f(0)", None),
    ]
    edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6),
             (3, 7), (3, 8), (4, 9), (4, 10), (5, 11), (5, 12), (7, 13), (13, 14)]
    for a, b in edges:
        ax, ay, _, _ = nodes[a]
        bx, by, _, _ = nodes[b]
        s.line(ax, ay + NH // 2, bx, by - NH // 2, stroke=LINE, sw=1.6)

    # 重复访问:f(4) 也要算 f(3),但这条 f(3) 已经算过一次了
    s.raw('<path d="M 430 238 Q 470 320 598 302" fill="none" '
          'stroke="#b5762a" stroke-width="1.8" stroke-dasharray="6 5"/>')
    s.arrow(600, 301, 594, 296, stroke=WARM_TXT, sw=1.8)

    for x, y, t, fill in nodes:
        f = FILL_WARM if fill == "warm" else PAPER
        st = WARM_TXT if fill == "warm" else INK
        s.box(x - NW // 2, y - NH // 2, NW, NH, t, fill=f, stroke=st)
        c.text(f"node {t}@{x},{y}", x, y + 5, t, size=15)

    s.text(1040, 90, "橙色:走过的状态会被重复计算", size=12, anchor="start",
           fill=WARM_TXT)
    c.text("legend2", 1040, 90, "橙色:走过的状态会被重复计算", size=12, anchor="start")
    s.text(1040, 114, "叶子是 base case f(0)/f(1)", size=12, anchor="start", fill=MUTED)
    c.text("legend1", 1040, 114, "叶子是 base case f(0)/f(1)", size=12, anchor="start")

    s.text(620, 600, "不同的路径 → 相同的状态:这就是重叠子问题", size=13, fill=MUTED)
    c.text("footnote", 620, 600, "不同的路径 → 相同的状态:这就是重叠子问题", size=13)
    BAD += c.run("01-decision-tree")
    s.save(OUT / "01-decision-tree.svg")


def fig2():
    """同一个数组,两种填法:自顶向下的备忘录 vs 自底向上的 DP 表。"""
    global BAD
    s = Svg(1200, 560)
    c = Check(s)

    s.text(600, 36, "同一个 memo 数组,两种填法", size=17, weight="600")
    c.text("title", 600, 36, "同一个 memo 数组,两种填法", size=17)
    s.text(600, 60, "自顶向下先递归到 f(2),再逐层返回;自底向上直接用循环从左往右填",
           size=12, fill=MUTED)
    c.text("subtitle", 600, 60,
           "自顶向下先递归到 f(2),再逐层返回;自底向上直接用循环从左往右填", size=12)

    # ---------------- 左:自顶向下 ----------------
    s.panel(40, 86, 520, 400)
    c.panel("panel-topdown", 40, 86, 520, 400)
    s.text(70, 122, "自顶向下:带备忘录的递归", size=15, anchor="start", weight="600")
    c.text("td-head", 70, 122, "自顶向下:带备忘录的递归", size=15, anchor="start")

    mono = "SFMono-Regular,Consolas,monospace"
    seq = ["dp(5)  → memo[5] 未命中", "dp(4)  → memo[4] 未命中",
           "dp(3)  → memo[3] 未命中", "dp(2)  → memo[2] 未命中",
           "base case 返回 1", "写回 memo[2] = 1",
           "写回 memo[3] = 2", "写回 memo[4] = 3", "写回 memo[5] = 5"]
    for i, line in enumerate(seq):
        y = 156 + i * 28
        c.text(f"td line{i}", 74, y, line, size=12, anchor="start")
        s.text(74, y, line, size=12, anchor="start", 
               fill=TEAL_TXT if line.startswith("写回") else INK)

    for i, t in enumerate(["memo[2]", "memo[3]", "memo[4]", "memo[5]"]):
        x = 74 + i * 122
        s.box(x, 430, 112, 40, t, fill=FILL_BLUE, stroke=BLUE, size=13)
        c.text(f"td-lab{i}", x + 56, 455, t, size=13)
    s.text(310, 424, "填表顺序 →", size=11, fill=MUTED)
    c.text("td-fillorder", 310, 424, "填表顺序 →", size=11)

    # ---------------- 右:自底向上 ----------------
    s.panel(620, 86, 540, 400)
    c.panel("panel-bottomup", 620, 86, 540, 400)
    s.text(650, 122, "自底向上:迭代填 DP 表", size=15, anchor="start", weight="600")
    c.text("bu-head", 650, 122, "自底向上:迭代填 DP 表", size=15, anchor="start")

    vals = ["0", "1", "1", "2", "3", "5"]
    for i, v in enumerate(vals):
        x = 660 + i * 82
        s.cell(x, 170, 82, 56, v, fill=FILL_BLUE if i >= 2 else FILL_GREY)
        c.text(f"bu cell{i}", x + 41, 203, v, size=15)
        s.text(x + 41, 160, str(i), size=11, fill=MUTED)
        c.text(f"bu idx{i}", x + 41, 160, str(i), size=11)

    s.text(650, 262, "dp[0] = 0, dp[1] = 1          ← base case", size=12,
           anchor="start")
    c.text("bu-base", 650, 262, "dp[0] = 0, dp[1] = 1          ← base case", size=12,
           anchor="start")
    s.text(650, 294, "for i in 2..n:", size=12, anchor="start")
    c.text("bu-loop", 650, 294, "for i in 2..n:", size=12, anchor="start")
    s.text(680, 322, "dp[i] = dp[i-1] + dp[i-2]", size=12, anchor="start")
    c.text("bu-body", 680, 322, "dp[i] = dp[i-1] + dp[i-2]", size=12, anchor="start")

    s.text(650, 366, "右边的格子只依赖左边两个格子", size=12, anchor="start", fill=MUTED)
    c.text("bu-note", 650, 366, "右边的格子只依赖左边两个格子", size=12, anchor="start")
    s.text(650, 400, "所以两个滚动变量就够,空间 O(1)", size=12, anchor="start",
           fill=TEAL_TXT)
    c.text("bu-note2", 650, 400, "所以两个滚动变量就够,空间 O(1)", size=12, anchor="start")

    s.arrow(660, 452, 1140, 452, stroke=BLUE)
    s.text(900, 444, "填表顺序", size=11, fill=BLUE)
    c.text("bu-arrowlab", 900, 444, "填表顺序", size=11)

    BAD += c.run("02-memo-and-table")
    s.save(OUT / "02-memo-and-table.svg")


def fig3():
    """LIS 的 dp 表:每个格子记的是「以我为结尾」的长度。"""
    global BAD
    s = Svg(1200, 596)
    c = Check(s)

    s.text(600, 34, "LIS = [10, 9, 2, 5, 3, 7, 101, 18] 的 dp 表", size=17, weight="600")
    c.text("title", 600, 34, "LIS = [10, 9, 2, 5, 3, 7, 101, 18] 的 dp 表", size=17)
    s.text(600, 58, "dp[i] 只承认「以 nums[i] 结尾」的递增子序列,所以答案要看整张表的最大值",
           size=12, fill=MUTED)
    c.text("subtitle", 600, 58,
           "dp[i] 只承认「以 nums[i] 结尾」的递增子序列,所以答案要看整张表的最大值", size=12)

    nums = [10, 9, 2, 5, 3, 7, 101, 18]
    dp = [1, 1, 1, 2, 2, 3, 4, 4]
    best = {5, 6, 7}   # dp 值为 3 和 4 的位置,一眼看出最大值
    CELL, GAP, X0 = 92, 20, 96

    def cx(i):
        return X0 + i * (CELL + GAP) + CELL / 2

    for i, v in enumerate(nums):
        x = X0 + i * (CELL + GAP)
        s.text(cx(i), 116, str(i), size=12, fill=MUTED)
        c.text(f"idx{i}", cx(i), 116, str(i), size=12)
        s.cell(x, 128, CELL, 62, str(v), fill=FILL_GREY)
        c.text(f"val{i}", cx(i), 168, str(v), size=16)
        s.cell(x, 340, CELL, 62, str(dp[i]),
               fill=FILL_WARM if i in best else FILL_BLUE,
               stroke=WARM_TXT if i in best else BLUE)
        c.text(f"dp{i}", cx(i), 380, str(dp[i]), size=16)

    s.text(600, 216, "nums", size=12, fill=MUTED)
    c.text("lab-nums", 600, 216, "nums", size=12)
    s.text(600, 296, "dp[i]:以 nums[i] 结尾的最长递增子序列长度", size=13)
    c.text("lab-dp", 600, 296, "dp[i]:以 nums[i] 结尾的最长递增子序列长度", size=13)

    # 谁给谁贡献了 +1:画从 dp[i] 指向 dp[j]+1 来源的细线
    for i, j in [(3, 2), (4, 2), (5, 4), (6, 5), (7, 5)]:
        s.raw(f'<path d="M {cx(i):.1f} 402 L {cx(i):.1f} 430 L {cx(j):.1f} 430 '
              f'L {cx(j):.1f} 406" fill="none" stroke="{TEAL_TXT}" '
              'stroke-width="1.4" stroke-dasharray="4 4"/>')
    s.text(600, 460, "dp", size=12, fill=MUTED)
    c.text("lab-dp2", 600, 460, "dp", size=12)
    s.text(600, 490, "虚线:dp[i] 的值来自某个更小的 dp[j] + 1(j < i 且 nums[j] < nums[i])",
           size=12, fill=TEAL_TXT, anchor="middle")
    c.text("dash-note", 600, 490,
           "虚线:dp[i] 的值来自某个更小的 dp[j] + 1(j < i 且 nums[j] < nums[i])", size=12)

    s.box(96, 522, 1008, 44, "答案 = max(dp) = 4,不是 dp[7]", fill=FILL_WARM,
          stroke=WARM_TXT, size=14)
    c.text("answer", 600, 549, "答案 = max(dp) = 4,不是 dp[7]", size=14)

    BAD += c.run("03-lis-dp")
    s.save(OUT / "03-lis-dp.svg")


def fig4():
    """耐心排序:8 步把牌分成 4 堆,堆数就是 LIS 长度。"""
    global BAD
    s = Svg(1160, 776)
    c = Check(s)

    s.text(580, 34, "耐心排序:牌堆数 = LIS 长度", size=17, weight="600")
    c.text("title", 580, 34, "耐心排序:牌堆数 = LIS 长度", size=17)
    s.text(580, 58, "每张牌压在最左边那个堆顶不小于它的堆上;压不下去就新建一堆",
           size=12, fill=MUTED)
    c.text("subtitle", 580, 58,
           "每张牌压在最左边那个堆顶不小于它的堆上;压不下去就新建一堆", size=12)

    steps = [
        ("10", 0, 0, [10], []),
        ("9",  0, 0, [9], [10]),
        ("2",  0, 0, [2], [9]),
        ("5",  2, 1, [2, 5], []),
        ("3",  2, 1, [2, 3], [5]),
        ("7",  3, 2, [2, 3, 7], []),
        ("101", 4, 3, [2, 3, 7, 101], []),
        ("18", 4, 3, [2, 3, 7, 18], [101]),
    ]
    actions = ["新建堆 1", "替换堆 1(9 < 10)", "替换堆 1(2 < 9)", "新建堆 2",
               "替换堆 2(3 < 5)", "新建堆 3", "新建堆 4", "替换堆 4(18 < 101)"]

    PX0, PW, PGAP = 300, 106, 18
    CW, CH = 96, 26

    # 每堆的牌从行顶往下叠:先算出这堆在「当前行」一共几张牌
    rows = []
    for r, (num, npile, pos, tops, old) in enumerate(steps):
        y = 96 + r * 66
        counts = []
        for p in range(4):
            placed = sum(1 for rr in range(r) if steps[rr][1] > p)
            counts.append(placed + (1 if p < npile else 0))
        y_card = y if npile > 0 else y
        rows.append((y, y_card, counts))

    for r, (num, npile, pos, tops, old) in enumerate(steps):
        y, y_card, counts = rows[r]
        c.text(f"step{r}", 72, y + 24, f"第 {r + 1} 步: {num}", size=13, anchor="middle")
        s.text(72, y + 24, f"第 {r + 1} 步: {num}", size=13, anchor="middle",
               weight="600")

        # 已经形成的堆:每张牌画在自己该在的高度上
        for p in range(npile):
            x = PX0 + p * (PW + PGAP)
            top_y = y + (counts[p] - 1) * CH
            if p < len(old) and old[p] is not None:
                s.cell(x, top_y - CH, CW, CH, str(old[p]), fill=FILL_GREY)
                c.text(f"r{r} old{p}", x + CW / 2, top_y - CH + 18, str(old[p]), size=12)
            s.cell(x, top_y, CW, CH, str(tops[p]),
                   fill=FILL_WARM if p == pos else FILL_BLUE,
                   stroke=WARM_TXT if p == pos else BLUE)
            c.text(f"r{r} top{p}", x + CW / 2, top_y + 18, str(tops[p]), size=13)

        # 新牌与它要去的那一堆底部对齐
        nx = 700          # 新牌固定在同一个槽位:每行的纵向变化一眼就能比较
        s.cell(nx, y_card, CW, CH, num, fill=PAPER, stroke=WARM_TXT)
        c.text(f"r{r} card", nx + CW / 2, y_card + 18, num, size=13)
        # 箭头停在这一堆左边一点(不插进格子,免得盖住格子里的数字)
        # 箭头终点压在目标堆的右边界上:既不插进格子盖住数字,也不跨过整堆
        s.arrow(674, y_card + CH // 2,
                PX0 + pos * (PW + PGAP) + CW, y_card + CH // 2,
                stroke=WARM_TXT, sw=1.6)
        # 动作文字固定放在「本行卡槽下沿再往下 16px」的位置,
        # 这样即使某堆已经叠了 5 张牌也不会和下一行撞上
        lab_y = y + 52
        s.text(900, lab_y, actions[r], size=11, anchor="start", fill=WARM_TXT)
        c.text(f"r{r} act", 900, lab_y, actions[r], size=11, anchor="start")

    s.rect(60, 708, 1040, 54, fill=FILL_TEAL, stroke=TEAL_TXT, rx=8)
    s.text(580, 740, "跑完 8 步:tails = [2, 3, 7, 18],长度 4 = LIS 长度;"
                     "每堆从上到下递减,堆顶从左到右严格递增",
           size=13, fill=TEAL_TXT)
    c.text("summary", 580, 740,
           "跑完 8 步:tails = [2, 3, 7, 18],长度 4 = LIS 长度;"
           "每堆从上到下递减,堆顶从左到右严格递增", size=13)

    BAD += c.run("04-patience-piles")
    s.save(OUT / "04-patience-piles.svg")


def fig5():
    """零钱兑换的状态依赖:每个 n 回头找 n-c。"""
    global BAD
    s = Svg(1200, 570)
    c = Check(s)

    s.text(600, 34, "零钱兑换:coins = [1, 2, 5], amount = 11", size=17, weight="600")
    c.text("title", 600, 34, "零钱兑换:coins = [1, 2, 5], amount = 11", size=17)
    s.text(600, 58, "每个 dp[n] 都要回头看 dp[n-1]、dp[n-2]、dp[n-5],选其中最小的再加一",
           size=12, fill=MUTED)
    c.text("subtitle", 600, 58,
           "每个 dp[n] 都要回头看 dp[n-1]、dp[n-2]、dp[n-5],选其中最小的再加一", size=12)

    dp = [0, 1, 1, 2, 2, 1, 2, 2, 3, 3, 2, 3]
    CELL, X0 = 84, 96

    def cx(i):
        return X0 + i * CELL + CELL / 2

    s.text(cx(3.5), 132, "dp[n]:凑出金额 n 的最少硬币数", size=13)
    c.text("dp-label", cx(3.5), 132, "dp[n]:凑出金额 n 的最少硬币数", size=13)

    for n, v in enumerate(dp):
        x = X0 + n * CELL
        s.text(cx(n), 168, str(n), size=12, fill=MUTED)
        c.text(f"n{n}", cx(n), 168, str(n), size=12)
        s.cell(x, 180, CELL, 64, str(v),
               fill=FILL_WARM if n == 11 else FILL_BLUE,
               stroke=WARM_TXT if n == 11 else BLUE)
        c.text(f"dp{n}", cx(n), 222, str(v), size=16)

    # 11 的三个来源:6(c=5)、9(c=2)、10(c=1)。
    # 用三条弧线画在格子下面,免得虚线横穿中间的格子
    arc = "M {a} {y0} A 62 56 0 0 0 {b} {y1}"
    for j, depth in [(6, 428), (9, 424), (10, 366)]:
        s.raw(f'<path d="{arc.format(a=cx(j), y0=246, b=cx(11), y1=246).replace("A 62 56 0 0 0", f"A {abs(cx(11)-cx(j))/2:.1f} {depth-246} 0 0 0")}" '
              'fill="none" stroke="#2f7d6d" stroke-width="1.6" stroke-dasharray="5 4"/>')

    for coin, lx, ly in [(5, 600, 424), (2, 1046, 392), (1, 1102, 366)]:
        s.text(lx, ly, f"c={coin}", size=11, fill=TEAL_TXT)
        c.text(f"src{coin}", lx, ly, f"c={coin}", size=11)

    s.rect(96, 462, 1008, 52, fill=FILL_TEAL, stroke=TEAL_TXT, rx=8)
    s.text(600, 495,
           "dp[6] = 2,dp[9] = 3,dp[10] = 2  → dp[11] = min(3, 4, 3) = 3",
           size=14, fill=TEAL_TXT)
    c.text("concl", 600, 495,
           "dp[6] = 2,dp[9] = 3,dp[10] = 2  → dp[11] = min(3, 4, 3) = 3", size=14)

    s.text(600, 544, "兜底规则:如果某个来源是「无解」,它不能参与 min,"
                     "否则假的「无解 + 1」会顶掉真答案", size=12, fill=MUTED)
    c.text("warn", 600, 544,
           "兜底规则:如果某个来源是「无解」,它不能参与 min,"
           "否则假的「无解 + 1」会顶掉真答案", size=12)

    BAD += c.run("05-coin-change")
    s.save(OUT / "05-coin-change.svg")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print(f"\n{'OK' if BAD == 0 else str(BAD) + ' PROBLEM(S)'} — figures in {OUT}")
    sys.exit(1 if BAD else 0)
