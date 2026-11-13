#!/usr/bin/env python3
"""Generate the five diagrams for _posts/2026-11-19-monotonic-queue.md.

Every figure goes through svgkit so it inherits the site palette, and every
text run / arrow is registered with svgkit.Check, which reports at build time
if anything overlaps, leaves the canvas, or spills out of its panel.

Run:  python3 make_figures.py
Then eyeball the renders (Check's text/text test has known false negatives):
      sips -s format png -Z 1200 <file>.svg --out /tmp/<file>.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "_tools")))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,  # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "img",
                                    "monotonic-queue-20261119"))

problems = 0


def txt(s, c, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Draw a label and register its hitbox in one step."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(t, x, y, t, size=size, anchor=anchor)
    return t


def cell(s, c, x, y, w, h, t, fill=PAPER, size=14, stroke=INK):
    s.cell(x, y, w, h, t, fill=fill, size=size)
    c.text(t, x + w / 2, y + h / 2 + size * 0.36, t, size=size)
    return t


def arrow(s, c, x1, y1, x2, y2, stroke=BLUE, dash=None):
    s.arrow(x1, y1, x2, y2, stroke=stroke, dash=dash)
    c.arrow("arrow(%.0f,%.0f->%.0f,%.0f)" % (x1, y1, x2, y2), x1, y1, x2, y2)


def save(s, c, name):
    global problems
    problems += c.run(name)
    s.save(os.path.join(OUT, name))


def card(s, c, x, y, w, h, title, lines, fill=FILL_BLUE, tsize=14,
         lsize=12, lfill=MUTED, tfill=INK):
    s.panel(x, y, w, h, fill=fill)
    txt(s, c, x + w / 2, y + 30, title, size=tsize, fill=tfill, weight="600")
    for k, line in enumerate(lines):
        txt(s, c, x + w / 2, y + 58 + k * 22, line, size=lsize, fill=lfill)


def numrow(s, c, x, y, w, h, items, fill=PAPER, size=14, gap=8):
    """A row of cells; returns the x just past the last cell."""
    for k, t in enumerate(items):
        cell(s, c, x + k * (w + gap), y, w, h, t, fill=fill, size=size)
    return x + len(items) * (w + gap) - gap


def numrow_head(s, c, x, y, w, h, items, fills, size=14, gap=8):
    for k, t in enumerate(items):
        cell(s, c, x + k * (w + gap), y, w, h, t, fill=fills[k], size=size)
    return x + len(items) * (w + gap) - gap


# ---------------------------------------------------------------------------
# 01: 为什么需要单调队列
# ---------------------------------------------------------------------------
def fig01():
    W, H = 1000, 386
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 36, "两个需求卡在一起,所以需要一个新结构", size=16)
    txt(s, c, W / 2, 60, "既要按入队时间出队,又要在 O(1) 时间拿到最值", size=12,
        fill=MUTED)

    cw, ch, gap = 290, 168, 22
    x0 = (W - 3 * cw - 2 * gap) / 2
    card(s, c, x0, 84, cw, ch, "① 加一个数", [
        "拿新元素和当前最大值比一下",
        "一次比较就够",
    ], fill=FILL_TEAL, tfill=TEAL_TXT)
    card(s, c, x0 + cw + gap, 84, cw, ch, "② 删一个数", [
        "如果出去的正好是最大值",
        "剩下谁是最大?只能重扫一遍",
    ], fill=FILL_WARM, tfill=WARM_TXT)
    card(s, c, x0 + 2 * (cw + gap), 84, cw, ch, "③ 用堆行不行", [
        "堆顶是最值,但出队顺序是",
        "元素大小,不是入队时间",
    ], fill=FILL_GREY)

    arrow(s, c, x0 + cw / 2, 262, x0 + cw + gap + cw / 2, 262, stroke=MUTED,
          dash="4 4")
    arrow(s, c, x0 + cw + gap + cw / 2, 262, x0 + 2 * (cw + gap) + cw / 2, 262,
          stroke=MUTED, dash="4 4")

    s.panel(42, 282, W - 84, 78, fill=FILL_BLUE)
    txt(s, c, W / 2, 314, "单调队列 = 一个仍然是队列的容器,同时 O(1) 给出最值",
        size=15, weight="600")
    txt(s, c, W / 2, 340, "队头是答案,队里其余的是候补;被压扁的候补永远不会成为答案",
        size=12, fill=MUTED)
    save(s, c, "01-why-not-heap.svg")


# ---------------------------------------------------------------------------
# 02: 239 样例走一遍
# ---------------------------------------------------------------------------
def fig02():
    W, H = 1000, 404
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 32, "样例走一遍:nums = [1, 3, -1, -3, 5, 3, 6, 7], k = 3",
        size=15)
    txt(s, c, W / 2, 54, "队列存下标,值从队头到队尾递减;每一步的队头就是本窗口的答案",
        size=12, fill=MUTED)

    hx_i, hx_in, hx_crush, q_left, hx_ans = 58, 110, 232, 330, 906
    txt(s, c, hx_i, 84, "i", size=11, fill=MUTED)
    txt(s, c, hx_in, 84, "进来的数", size=11, fill=MUTED)
    txt(s, c, hx_crush, 84, "被压扁的下标", size=11, fill=MUTED)
    txt(s, c, q_left + 120, 84, "队列(队头 → 队尾)", size=11, fill=MUTED)
    txt(s, c, hx_ans, 84, "本步答案", size=11, fill=MUTED)

    s.line(q_left, 92, q_left, 372, stroke=LINE, sw=1.4, dash="4 4")
    txt(s, c, q_left, 78, "队头", size=11, fill=BLUE)

    # i, 进来的数, 被压扁, 队列(下标:值), 窗口, 答案
    rows = [
        (0, 1, "-", [(0, 1)], "-"),
        (1, 3, "0", [(1, 3)], "-"),
        (2, -1, "-", [(1, 3), (2, -1)], "3"),
        (3, -3, "-", [(1, 3), (2, -1), (3, -3)], "3"),
        (4, 5, "3, 2, 1", [(4, 5)], "5"),
        (5, 3, "-", [(4, 5), (5, 3)], "5"),
        (6, 6, "5, 4", [(6, 6)], "6"),
        (7, 7, "6", [(7, 7)], "7"),
    ]
    cw, chh, cgap = 58, 26, 4
    for k, (i, x, crush, q, ans) in enumerate(rows):
        yc = 106 + k * 34
        if k:
            s.line(42, yc - 17, W - 42, yc - 17, stroke=LINE, sw=1.0)
        txt(s, c, hx_i, yc + 5, str(i), size=12, fill=MUTED)
        cell(s, c, hx_in - 26, yc - chh / 2, 52, chh, str(x),
             fill=FILL_WARM if k == 4 else PAPER, size=12)
        txt(s, c, hx_crush, yc + 4, crush, size=11,
            fill=WARM_TXT if crush != "-" else MUTED)
        for m, (idx, val) in enumerate(q):
            cell(s, c, q_left + m * (cw + cgap), yc - chh / 2, cw, chh,
                 "%d:%d" % (idx, val), fill=FILL_GREY if m else FILL_TEAL,
                 size=12)
        if ans != "-":
            cell(s, c, hx_ans - 26, yc - chh / 2, 52, chh, ans, fill=FILL_BLUE,
                 size=12)

    txt(s, c, W / 2, 388, "i = 4 连弹三次;这个样例里过期一次都没发生",
        size=11, fill=MUTED)
    save(s, c, "02-crush-trace.svg")


# ---------------------------------------------------------------------------
# 03: 存值 vs 存下标
# ---------------------------------------------------------------------------
def fig03():
    W, H = 1000, 396
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "同一个窗口,两种存法", size=16)
    txt(s, c, W / 2, 58, "窗口是 [5, 5, 3],现在左端的 5 要滑出去", size=12,
        fill=MUTED)

    pw, px0, px1 = 444, 42, 514

    # ---- 左:存值 ----
    s.panel(px0, 78, pw, 214, fill=FILL_WARM)
    txt(s, c, px0 + pw / 2, 110, "存值:pop(n) 得带参数", size=15, fill=WARM_TXT,
        weight="600")
    txt(s, c, px0 + 22, 146, "窗口", size=11, fill=MUTED, anchor="start")
    numrow(s, c, px0 + 74, 132, 62, 30, ["5", "5", "3"], size=13)
    txt(s, c, px0 + 22, 194, "队列", size=11, fill=MUTED, anchor="start")
    numrow(s, c, px0 + 74, 180, 62, 30, ["5", "3"], fill=FILL_GREY, size=13)
    txt(s, c, px0 + pw / 2, 240, "出去的是前一个 5,可队列里存的是值,", size=12)
    txt(s, c, px0 + pw / 2, 262, "认不出该删哪一个,只能问调用方:", size=12)
    txt(s, c, px0 + pw / 2, 284, "if 队头 == n: 弹出", size=12, fill=WARM_TXT,
        weight="600")

    # ---- 右:存下标 ----
    s.panel(px1, 78, pw, 214, fill=FILL_TEAL)
    txt(s, c, px1 + pw / 2, 110, "存下标:过期只看两个整数", size=15,
        fill=TEAL_TXT, weight="600")
    txt(s, c, px1 + 22, 146, "窗口", size=11, fill=MUTED, anchor="start")
    numrow(s, c, px1 + 74, 132, 62, 30, ["0:5", "1:5", "2:3"], size=12)
    txt(s, c, px1 + 22, 194, "队列", size=11, fill=MUTED, anchor="start")
    numrow(s, c, px1 + 74, 180, 62, 30, ["1:5", "2:3"], fill=FILL_GREY, size=12)
    txt(s, c, px1 + pw / 2, 240, "下标唯一,相等值不会认错人;", size=12)
    txt(s, c, px1 + pw / 2, 262, "队头该不该走,比一次就够了:", size=12)
    txt(s, c, px1 + pw / 2, 284, "if q[0] <= i - k: 弹出", size=12,
        fill=TEAL_TXT, weight="600")

    cw, gap = 290, 22
    x0 = (W - 3 * cw - 2 * gap) / 2
    for k, (t, sub) in enumerate([
        ("pop 不用带参数", "队列自己知道时间顺序"),
        ("相等值不会认错", "位置唯一,值不唯一"),
        ("size 做得到", "另存一份顺序记录即可"),
    ]):
        x = x0 + k * (cw + gap)
        s.panel(x, 310, cw, 66, fill=FILL_BLUE)
        txt(s, c, x + cw / 2, 338, t, size=13, weight="600")
        txt(s, c, x + cw / 2, 360, sub, size=11, fill=MUTED)
    save(s, c, "03-index-vs-value.svg")


# ---------------------------------------------------------------------------
# 04: 通用实现的三副队列
# ---------------------------------------------------------------------------
def fig04():
    W, H = 1000, 420
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "通用实现:每一次 push,三副队列同时更新", size=16)
    txt(s, c, W / 2, 58, "push(3) push(1) push(4) pop() 之后的状态", size=12,
        fill=MUTED)

    s.panel(42, 80, W - 84, 250, fill=CANVAS)

    cols = [
        (150, "_data 保先进先出", [(1, 1), (2, 4)], FILL_BLUE, BLUE),
        (500, "_max 候补最大值", [(2, 4)], FILL_TEAL, TEAL_TXT),
        (850, "_min 候补最小值", [(1, 1), (2, 4)], FILL_WARM, WARM_TXT),
    ]
    for cx, title, items, fill, zfill in cols:
        txt(s, c, cx, 112, title, size=13, weight="600")
        for k, (t, v) in enumerate(items):
            cell(s, c, cx - 60, 132 + k * 44, 120, 34, "t=%d, %d" % (t, v),
                 fill=fill, size=13)
        if not items:
            txt(s, c, cx, 154, "空", size=12, fill=MUTED)

    txt(s, c, 150, 236, "t=0 已经被 pop 走了", size=11, fill=MUTED)
    txt(s, c, 500, 236, "队头就是 max()", size=11, fill=TEAL_TXT)
    txt(s, c, 850, 236, "队头就是 min()", size=11, fill=WARM_TXT)

    arrow(s, c, 190, 200, 440, 200, stroke=MUTED, dash="4 4")
    txt(s, c, 315, 182, "pop() 出队的是 t=0", size=12)
    txt(s, c, 315, 220, "它不在 max/min 的队头,那两副队列不动", size=11,
        fill=MUTED)
    arrow(s, c, 560, 200, 776, 200, stroke=MUTED, dash="4 4")

    txt(s, c, W / 2, 300, "size() = len(_data) = 2   ·   max() = 4   ·   min() = 1",
        size=13, weight="600")

    s.panel(42, 346, W - 84, 60, fill=FILL_GREY)
    txt(s, c, W / 2, 370, "push 均摊 O(1) · pop 均摊 O(1) · size / max / min 都是 O(1)",
        size=13)
    txt(s, c, W / 2, 392, "每个元素一生只入队一次、出队一次;队列空时不要调用 max / min",
        size=11, fill=MUTED)
    save(s, c, "04-generic-class.svg")


# ---------------------------------------------------------------------------
# 05: 862 前缀和 + 单调队列
# ---------------------------------------------------------------------------
def fig05():
    W, H = 1000, 470
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "862:nums = [2, -1, 2], K = 3,答案是 3", size=16)
    txt(s, c, W / 2, 58, "把「子数组的和」换成前缀和之差,再在左边找「还可能有用的」下标",
        size=12, fill=MUTED)

    # ---- 左:数组与前缀和 ----
    txt(s, c, 130, 92, "nums", size=12, fill=MUTED, anchor="start")
    numrow(s, c, 104, 100, 74, 44, ["2", "-1", "2"], size=15)
    for k in range(3):
        txt(s, c, 104 + k * 82 + 37, 160, str(k), size=11, fill=MUTED)

    txt(s, c, 56, 200, "pre", size=12, fill=MUTED, anchor="start")
    numrow(s, c, 104, 208, 74, 44, ["0", "2", "1", "3"], fill=FILL_GREY,
           size=15)
    for k in range(4):
        txt(s, c, 104 + k * 82 + 37, 268, str(k), size=11, fill=MUTED)
    txt(s, c, 104 + 3 * 82 + 37, 288, "pre[j] = nums[0..j-1] 的和", size=11,
        fill=MUTED)

    txt(s, c, 250, 324, "nums[0..2] 的和 = pre[3] - pre[0] = 3 >= K", size=13,
        fill=TEAL_TXT, weight="600")

    # ---- 右:两条规则 ----
    card(s, c, 470, 80, 488, 84, "能结算谁:队头满足 pre[j] - pre[队头] >= K", [
        "记下长度 j - 队头,然后把它弹掉",
    ], fill=FILL_TEAL, tsize=13, tfill=TEAL_TXT)
    card(s, c, 470, 172, 488, 84, "能压扁谁:队尾的 pre >= pre[j]", [
        "它更靠左、前缀和还更大,两条都吃亏",
    ], fill=FILL_WARM, tsize=13, tfill=WARM_TXT)
    card(s, c, 470, 264, 488, 84, "两个都不满足就入队,等后面的 j", [
        "队列里始终是 pre 递增的候选左端点",
    ], fill=FILL_BLUE, tsize=13)

    # ---- 底:队列状态 ----
    s.panel(42, 356, W - 84, 96, fill=CANVAS)
    groups = [
        (170, "j = 1 之后", ["0", "1"], "-"),
        (500, "j = 2 之后", ["0", "2"], "1 被压扁( pre 更大且更靠左 )"),
        (830, "j = 3 之后", ["2", "3"], "0 被结算( best = 3 - 0 = 3 )"),
    ]
    for cx, label, items, note in groups:
        txt(s, c, cx, 380, label, size=12, weight="600")
        x = cx - (len(items) * 62 - 4) / 2
        for k, t in enumerate(items):
            cell(s, c, x + k * 62, 392, 58, 30, t,
                 fill=FILL_TEAL if k == 0 else FILL_GREY, size=13)
        txt(s, c, cx, 440, note, size=11,
            fill=WARM_TXT if note != "-" else MUTED)
    save(s, c, "05-prefix-sum.svg")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig01()
    fig02()
    fig03()
    fig04()
    fig05()
    if problems:
        print("problems: %d" % problems)
        sys.exit(1)
    print("figures: 5 written, problems: 0")
