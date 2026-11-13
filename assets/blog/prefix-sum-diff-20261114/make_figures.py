#!/usr/bin/env python3
"""Regenerate the SVG figures for the prefix-sum / difference-array post.

Run:  /opt/miniconda3/bin/python3 make_figures.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent
OUT = BLOG.parent / "img" / "prefix-sum-diff-20261114"
sys.path.insert(0, str(BLOG / "_tools"))

from svgkit import (Svg, Check, PAPER, CANVAS, INK, MUTED, LINE, BLUE,       # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT.mkdir(parents=True, exist_ok=True)

NUMS = [-2, 0, 3, -5, 2, -1]
PRESUM = [0, -2, -2, 1, -4, -2, -3]
DIFF = [-2, 2, 3, -8, 7, -3]


def title(s, c, t, sub=None):
    s.text(34, 40, t, size=18, anchor="start", weight="600")
    c.text("title", 34, 40, t, size=18, anchor="start")
    if sub:
        s.text(34, 63, sub, size=12, fill=MUTED, anchor="start")
        c.text("subtitle", 34, 63, sub, size=12, anchor="start")


def note(s, c, name, x, y, t, size=12, fill=MUTED, anchor="start"):
    s.text(x, y, t, size=size, fill=fill, anchor=anchor)
    c.text(name, x, y, t, size=size, anchor=anchor)


def caption(s, c, y, lines, h=None):
    """A canvas-coloured footer holding left-aligned explanation lines."""
    h = h or (len(lines) * 28 + 26)
    s.rect(30, y, 940, h, fill=CANVAS, stroke=LINE, sw=1, rx=9)
    c.panel("caption", 30, y, 940, h)
    for i, t in enumerate(lines):
        size = 12 if i else 12.5
        fill = INK if i else INK
        s.text(46, y + 30 + i * 28, t, size=size, fill=fill, anchor="start")
        c.text(f"cap{i}", 46, y + 30 + i * 28, t, size=size, anchor="start")


# --------------------------------------------------------------- figure 1
def fig_offset():
    s = Svg(1000, 430); c = Check(s)
    title(s, c, "preSum 的那一格偏移：哨兵为什么必须存在",
          "nums = [-2, 0, 3, -5, 2, -1]，preSum = [0, -2, -2, 1, -4, -2, -3]")

    # nums 一行:6 格
    for k, v in enumerate(NUMS):
        x = 100 + 120 * k
        note(s, c, f"ni{k}", x + 60, 108, str(k), size=12, fill=MUTED)
        fill = FILL_BLUE if k <= 3 else PAPER
        s.cell(x, 120, 120, 52, str(v), fill=fill, size=17)
        c.text(f"nv{k}", x + 60, 120 + 52 / 2 + 17 * 0.36, str(v), size=17)
    # nums[i] 的中心,正好落在 preSum[i] / preSum[i+1] 的接缝上
    for k in range(6):
        s.line(160 + 120 * k, 174, 160 + 120 * k, 212, stroke=LINE, sw=1.2, dash="3 4")

    # preSum 一行:7 格,整体左移半格
    for k, v in enumerate(PRESUM):
        x = 40 + 120 * k
        note(s, c, f"pi{k}", x + 60, 200, str(k), size=12, fill=MUTED)
        if k == 0:
            fill = FILL_GREY
        elif k == 4:
            fill = FILL_BLUE
        else:
            fill = PAPER
        s.cell(x, 216, 120, 52, str(v), fill=fill, stroke=INK, size=17)
        c.text(f"pv{k}", x + 60, 216 + 52 / 2 + 17 * 0.36, str(v), size=17)

    note(s, c, "n1", 100, 296, "哨兵：空数组的和 = 0", size=11.5, fill=MUTED)
    note(s, c, "n2", 580, 296, "= nums[0..3] 的和", size=11.5, fill=BLUE)
    note(s, c, "n3", 800, 296, "整个数组的和", size=11.5, fill=MUTED)

    caption(s, c, 318, [
        "nums[i] 正落在 preSum[i] 和 preSum[i+1] 的接缝上：第一个包含 nums[i] 的前缀和是 preSum[i+1]。",
        "所以 preSum[i] 的含义是「前 i 个元素」，不是「到下标 i 为止」——下标 i 变成了元素个数 i。",
    ])
    bad = c.run("01-offset")
    s.save(OUT / "01-offset.svg")
    return bad


# --------------------------------------------------------------- figure 2
def fig_subtract():
    s = Svg(1000, 440); c = Check(s)
    title(s, c, "区间和 = 两次相减：公共前缀自己消掉",
          "要 nums[1..4] 的和：preSum[5] - preSum[1] = -2 - (-2) = 0")

    for k, v in enumerate(NUMS):
        x = 100 + 120 * k
        note(s, c, f"ni{k}", x + 60, 98, str(k), size=12, fill=MUTED)
        fill = FILL_BLUE if 1 <= k <= 4 else PAPER
        s.cell(x, 110, 120, 50, str(v), fill=fill, size=17, stroke=LINE)
        c.text(f"nv{k}", x + 60, 110 + 50 / 2 + 17 * 0.36, str(v), size=17)

    # 条 1:preSum[5] 覆盖 [0, 5)
    s.rect(100, 190, 600, 36, fill=FILL_BLUE, stroke=BLUE, sw=1.3, rx=6)
    c.panel("barA", 100, 190, 600, 36)
    c.text("barAl", 400, 213, "preSum[5]：前 5 个元素的和 = -2", size=13)
    s.text(400, 213, "preSum[5]：前 5 个元素的和 = -2", size=13)

    # 条 2:preSum[1] 覆盖 [0, 1),被减掉
    s.rect(100, 240, 120, 36, fill=FILL_WARM, stroke=WARM_TXT, sw=1.3, rx=6)
    note(s, c, "barB", 232, 263, "- preSum[1]：前 1 个元素的和 = -2（公共前缀）",
         size=12, fill=WARM_TXT)

    # 结果:剩下的 [1, 5)
    s.rect(220, 290, 480, 36, fill=FILL_TEAL, stroke=TEAL_TXT, sw=1.3, rx=6)
    c.panel("barR", 220, 290, 480, 36)
    c.text("barRl", 460, 313, "剩下的正好是 nums[1..4] 的和 = 0", size=13)
    s.text(460, 313, "剩下的正好是 nums[1..4] 的和 = 0", size=13)

    # 把三条和上面的数组格子对齐:左边都从 nums[0] 开始,右边落在 nums[4] 的右边界
    for x, y1, y2 in ((100, 162, 190), (700, 162, 190), (220, 276, 290),
                      (700, 226, 290)):
        s.line(x, y1, x, y2, stroke=LINE, sw=1.2, dash="3 4")

    caption(s, c, 348, [
        "两项相减,公共部分被精确消掉,所以查询是 O(1):不看区间有多长,永远只有一次减法。",
        "换个说法：preSum[r+1] 是「前 r+1 个」的和,preSum[l] 是「前 l 个」的和,差的正是第 l+1 到第 r+1 个。",
    ])
    bad = c.run("02-subtract")
    s.save(OUT / "02-subtract.svg")
    return bad


# --------------------------------------------------------------- figure 3
def fig_inclusion_exclusion():
    s = Svg(1000, 430); c = Check(s)
    title(s, c, "二维容斥：A - B - C + D",
          "以 4x4 矩阵上查询 [1..2][1..2] 为例，深色格是被算进去的部分")

    step = 32
    top = 140
    grids = [
        (30, "preSum[3][3] = A", lambda i, j: i <= 2 and j <= 2, FILL_BLUE, BLUE),
        (230, "- preSum[1][3] = B", lambda i, j: i == 0 and j <= 2, FILL_WARM, WARM_TXT),
        (430, "- preSum[3][1] = C", lambda i, j: i <= 2 and j == 0, FILL_WARM, WARM_TXT),
        (630, "+ preSum[1][1] = D", lambda i, j: i == 0 and j == 0, FILL_TEAL, TEAL_TXT),
        (830, "= 目标 [1..2][1..2]", lambda i, j: 1 <= i <= 2 and 1 <= j <= 2,
         FILL_BLUE, BLUE),
    ]
    for gx, label, cov, fill, stroke in grids:
        # 最后一格的标题右对齐,否则会顶出画布(Check 就是这么抓到它的)
        if gx + 64 + len(label) * 7 > 992:
            note(s, c, f"g{gx}", gx + 128, 112, label, size=12, fill=stroke, anchor="end")
        else:
            note(s, c, f"g{gx}", gx + 64, 112, label, size=12, fill=stroke)
        for i in range(4):
            for j in range(4):
                s.rect(gx + j * step, top + i * step, step, step,
                       fill=fill if cov(i, j) else PAPER, stroke=LINE, sw=1.1, rx=0)

    for op, x in (("-", 190), ("-", 390), ("+", 590), ("=", 790)):
        s.text(x, 205, op, size=20, fill=INK, weight="600")
        c.text(f"op{x}", x, 205, op, size=20)

    caption(s, c, 300, [
        "A 是整个左上角矩形,B 和 C 各切掉一条边 —— 左上角那一块被切了两次,所以 D 要加回来一次。",
        "每多一个维度,项数翻一倍(2 的 d 次方)：一维两项,二维四项,三维八项,符号是越界次数的奇偶。",
        "最容易写错的是那三项的下标:是 preSum[row1][col2+1] 和 preSum[row2+1][col1],用 row1,不是 row1-1。",
    ], h=104)
    bad = c.run("03-inclusion-exclusion")
    s.save(OUT / "03-inclusion-exclusion.svg")
    return bad


# --------------------------------------------------------------- figure 4
def fig_difference():
    s = Svg(1000, 470); c = Check(s)
    title(s, c, "差分：一次区间加 = 两次单点修改",
          "给 nums[1..3] 全部加 3：diff[1] += 3，diff[4] -= 3，其它一格不动")

    note(s, c, "l0", 30, 92, "nums（修改前）", size=12.5, fill=MUTED)
    for k, v in enumerate(NUMS):
        x = 100 + 120 * k
        note(s, c, f"bi{k}", x + 60, 118, str(k), size=12, fill=MUTED)
        s.cell(x, 130, 120, 48, str(v), size=17, stroke=LINE)
        c.text(f"bv{k}", x + 60, 130 + 48 / 2 + 17 * 0.36, str(v), size=17)

    note(s, c, "l1", 30, 216, "diff（只有两格变了）", size=12.5, fill=MUTED)
    note(s, c, "e1", 280, 216, "+3", size=14, fill=WARM_TXT)
    note(s, c, "e2", 640, 216, "-3", size=14, fill=WARM_TXT)
    for k, v in enumerate(DIFF):
        x = 100 + 120 * k
        if k == 1:
            s.cell(x, 228, 120, 48, "5", fill=FILL_WARM, stroke=WARM_TXT, size=17,
                   sub="2 + 3")
            c.text("dv1", x + 60, 228 + 48 / 2 - 2, "5", size=17)
            c.text("ds1", x + 60, 228 + 48 / 2 + 14, "2 + 3", size=10)
        elif k == 4:
            s.cell(x, 228, 120, 48, "4", fill=FILL_WARM, stroke=WARM_TXT, size=17,
                   sub="7 - 3")
            c.text("dv4", x + 60, 228 + 48 / 2 - 2, "4", size=17)
            c.text("ds4", x + 60, 228 + 48 / 2 + 14, "7 - 3", size=10)
        else:
            s.cell(x, 228, 120, 48, str(v), size=17, stroke=LINE)
            c.text(f"dv{k}", x + 60, 228 + 48 / 2 + 17 * 0.36, str(v), size=17)

    note(s, c, "brk", 400, 306, "这两格一动,还原出来的 nums[1..3] 整段被抬高 3",
         size=12, fill=WARM_TXT)

    note(s, c, "l2", 30, 348, "nums（还原后）", size=12.5, fill=MUTED)
    after = [-2, 3, 6, -2, 2, -1]
    for k, v in enumerate(after):
        x = 100 + 120 * k
        fill = FILL_TEAL if 1 <= k <= 3 else PAPER
        s.cell(x, 360, 120, 48, str(v), fill=fill, size=17,
               stroke=TEAL_TXT if 1 <= k <= 3 else LINE)
        c.text(f"av{k}", x + 60, 360 + 48 / 2 + 17 * 0.36, str(v), size=17)

    note(s, c, "foot", 30, 442,
         "还原就是前缀和 res[i] = res[i-1] + diff[i]：diff[1] 的 +3 会一路传下去,diff[4] 的 -3 正好把它收住。",
         size=12)
    bad = c.run("04-difference")
    s.save(OUT / "04-difference.svg")
    return bad


# --------------------------------------------------------------- figure 5
def fig_duality():
    s = Svg(1000, 470); c = Check(s)
    title(s, c, "对偶：两个算子互为逆运算，便宜的正好错开",
          "nums 是 diff 的前缀和，diff 是 nums 的差分；S(D(x)) = x 且 D(S(x)) = x")

    s.box(120, 116, 240, 84, "nums", "原数组")
    c.panel("bnums", 120, 116, 240, 84)
    c.text("bnumsl", 240, 116 + 84 / 2 - 3, "nums", size=15)
    c.text("bnumss", 240, 116 + 84 / 2 + 14, "原数组", size=11)
    s.box(640, 116, 240, 84, "diff", "差分数组")
    c.panel("bdiff", 640, 116, 240, 84)
    c.text("bdiffl", 760, 116 + 84 / 2 - 3, "diff", size=15)
    c.text("bdiffs", 760, 116 + 84 / 2 + 14, "差分数组", size=11)

    s.arrow(372, 140, 628, 140, stroke=BLUE, sw=1.8)
    c.arrow("ar1", 372, 140, 628, 140)
    # 标签放在两个框之间的空隙里:第一版压在 diff 框上,Check 查不出这种重叠,是渲染出来才看见的
    note(s, c, "ar1a", 500, 108, "D：相邻相减", size=12, fill=BLUE)
    note(s, c, "ar1b", 500, 126, "diff[i] = nums[i] - nums[i-1]", size=11.5, fill=BLUE)
    s.arrow(628, 186, 372, 186, stroke=TEAL_TXT, sw=1.8)
    c.arrow("ar2", 628, 186, 372, 186)
    note(s, c, "ar2l", 500, 210, "S：逐项累加 nums[i] = nums[i-1] + diff[i]",
         size=12, fill=TEAL_TXT)

    cols = [(100, 210), (310, 280), (590, 310)]
    heads = ["", "区间查询", "区间修改（整段加减）"]
    rows = [
        ("前缀和 preSum", "O(1)：两次相减", "O(n)：改一个点后面全失效", FILL_BLUE),
        ("差分 diff", "O(n)：得先还原整个数组", "O(1)：两次单点修改", FILL_TEAL),
    ]
    y0 = 268
    for (x, w), h in zip(cols, heads):
        if h:
            s.cell(x, y0, w, 38, h, fill=FILL_GREY, size=13)
            c.text(f"th{x}", x + w / 2, y0 + 38 / 2 + 13 * 0.36, h, size=13)
    for r, (name, q, m, fill) in enumerate(rows):
        y = y0 + 38 + r * 44
        for (x, w), t in zip(cols, (name, q, m)):
            s.cell(x, y, w, 44, t, fill=fill if x == 100 else PAPER, size=12.5,
                   stroke=LINE)
            c.text(f"c{r}{x}", x + w / 2, y + 44 / 2 + 12.5 * 0.36, t, size=12.5)

    note(s, c, "foot", 30, 448,
         "谁也做不到两全：前缀和把查询变便宜、把修改变贵，差分反过来；两个都要 O(1)，就得上线段树。",
         size=12)
    bad = c.run("05-duality")
    s.save(OUT / "05-duality.svg")
    return bad


if __name__ == "__main__":
    bad = 0
    for f in (fig_offset, fig_subtract, fig_inclusion_exclusion,
              fig_difference, fig_duality):
        bad += f()
    print("total layout problems:", bad)
