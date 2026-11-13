#!/usr/bin/env python3
"""Generate the six diagrams for _posts/2026-11-18-monotonic-stack.md.

Every figure goes through svgkit so it inherits the site palette, and every
text run / arrow is registered with svgkit.Check, which reports at build time
if anything overlaps, leaves the canvas, or spills out of its panel.

Run:  /opt/miniconda3/bin/python3 make_figures.py
Then eyeball the renders (Check's text/text test has known false negatives):
      sips -s format png -Z 1400 <file>.svg --out /tmp/<file>.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "_tools")))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,  # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "img",
                                    "monotonic-stack-20261118"))

problems = 0


def txt(s, c, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Draw a label and register its hitbox in one step."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(t, x, y, t, size=size, anchor=anchor)
    return t


def cell(s, c, x, y, w, h, t, fill=PAPER, size=14, sub=None):
    s.cell(x, y, w, h, t, fill=fill, size=size, sub=sub)
    c.text(t, x + w / 2, y + h / 2 + size * 0.36, t, size=size)
    if sub:
        c.text(sub, x + w / 2, y + h / 2 + 16, sub, size=10)


def arrow(s, c, x1, y1, x2, y2, stroke=BLUE):
    s.arrow(x1, y1, x2, y2, stroke=stroke)
    c.arrow("arrow(%.0f,%.0f->%.0f,%.0f)" % (x1, y1, x2, y2), x1, y1, x2, y2)


def save(s, c, name):
    global problems
    problems += c.run(name)
    s.save(os.path.join(OUT, name))


def bar(s, x, base, w, value, unit, fill=FILL_BLUE, stroke=INK, sw=1.4):
    """A histogram bar of `value` units, growing up from `base`."""
    h = value * unit
    s.rect(x, base - h, w, h, fill=fill, stroke=stroke, sw=sw, rx=3)
    return base - h


def stackcol(s, c, x, base, w, items, cell_h=26, label="栈(栈底→栈顶)"):
    """Draw a stack as a column of index cells growing up from `base`."""
    if label:
        txt(s, c, x + w / 2, base - cell_h * len(items) - 16, label,
            size=10, fill=MUTED)
    for k, (idx, val) in enumerate(items):
        y = base - cell_h * (k + 1)
        cell(s, c, x, y, w, cell_h, "%d:%d" % (idx, val), size=12)


# ---------------------------------------------------------------------------
# 01: 什么信号出现时该想到单调栈
# ---------------------------------------------------------------------------
def fig01():
    W, H = 1000, 360
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 36, "先翻译题面:要的是「第一个比我大/小的邻居」,才轮到单调栈",
        size=15)
    txt(s, c, W / 2, 60, "翻译成功,剩下的就是套模板;翻译不成功,先换别的数据结构",
        size=12, fill=MUTED)

    # left panel: signals that DO mean monotonic stack
    s.panel(30, 84, 460, 214, fill=FILL_BLUE, stroke=LINE)
    txt(s, c, 50, 110, "看到这些说法 → 上单调栈", size=13, anchor="start", weight="600")
    rows = [
        ("右边第一个比它大的数", "下一个更大:496 / 739"),
        ("左边第一根比它矮的挡板", "上一个更小:弹出时读栈顶"),
        ("以它最矮时能撑多宽的矩形", "上一个 + 下一个更小:84"),
        ("环形数组里绕一圈的下一个更大", "翻倍 + 取模:503"),
    ]
    for k, (a, b) in enumerate(rows):
        y = 140 + k * 38
        txt(s, c, 50, y, "· " + a, size=12, anchor="start")
        txt(s, c, 50, y + 15, "    → " + b, size=11, anchor="start", fill=BLUE)

    # right panel: signals that do NOT
    s.panel(510, 84, 460, 214, fill=FILL_GREY, stroke=LINE)
    txt(s, c, 530, 110, "看到这些说法 → 别急", size=13, anchor="start", weight="600")
    bad = [
        ("全局最大 / 最小", "堆、排序"),
        ("随便一个满足条件的元素", "双指针、前缀和"),
        ("窗口内的最值", "单调队列(下一篇)"),
        ("反复随机问某个区间的第一个更大", "单调栈只扫一遍,答不了"),
    ]
    for k, (a, b) in enumerate(bad):
        y = 140 + k * 38
        txt(s, c, 530, y, "· " + a, size=12, anchor="start")
        txt(s, c, 530, y + 15, "    → " + b, size=11, anchor="start", fill=MUTED)

    s.panel(30, 310, 940, 40, fill=FILL_TEAL, stroke=LINE)
    txt(s, c, W / 2, 335,
        "三条同时成立才值得上:「第一个」+「所有元素都要问一遍」+「一次从左到右的扫描能问完」",
        size=12, fill=TEAL_TXT)
    save(s, c, "01-signals.svg")


# ---------------------------------------------------------------------------
# 02: 什么时候弹出 —— [2,1,2,4,3] 的四个瞬间
# ---------------------------------------------------------------------------
def fig02():
    W, H = 1000, 700
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "什么时候弹出:新元素把栈顶所有比它小的结算掉", size=15)
    txt(s, c, W / 2, 58, "nums = [2, 1, 2, 4, 3],求每个元素右边第一个更大的值", size=12,
        fill=MUTED)

    nums = [2, 1, 2, 4, 3]
    unit, bw, gap = 18, 30, 12
    stages = [
        ("① 处理完 i = 1", 1, [0, 1], {},
         ["1 < 2,不弹;1 入栈继续等", "栈里两个人都还没等到答案"]),
        ("② i = 2,nums[2] = 2", 2, [0, 2], {1: 2},
         ["2 > 1 → 弹出 1,res[1] = 2", "2 = 2 不比相等大,2 留在栈里"]),
        ("③ i = 3,nums[3] = 4", 3, [3], {2: 4, 0: 4},
         ["4 一次弹两个:while 不是 if", "res[2] = 4、res[0] = 4"]),
        ("④ i = 4,nums[4] = 3", 4, [3, 4], {},
         ["3 < 4,不弹;3 入栈", "结束时栈里剩 3、4 → 它们是 -1"]),
    ]
    for k, (title, cur, stack, pops, notes) in enumerate(stages):
        px = 24 + (k % 2) * 488
        py = 80 + (k // 2) * 280
        s.panel(px, py, 464, 260, fill=CANVAS, stroke=LINE)
        txt(s, c, px + 16, py + 26, title, size=13, anchor="start", weight="600")
        base = py + 170
        for i, v in enumerate(nums):
            x = px + 16 + i * (bw + gap)
            fill = FILL_WARM if i == cur else FILL_BLUE
            bar(s, x, base, bw, v, unit, fill=fill,
                stroke=WARM_TXT if i == cur else INK, sw=2.0 if i == cur else 1.4)
            txt(s, c, x + bw / 2, base + 16, str(i), size=11, fill=MUTED)
        # 下标标签下面画弹出箭头:从被弹出者的位置指向当前元素
        for order, j in enumerate(sorted(pops)):
            x1 = px + 16 + j * (bw + gap) + bw / 2
            x2 = px + 16 + cur * (bw + gap) + bw / 2
            arrow(s, c, x1, base + 30 + order * 14, x2, base + 30 + order * 14,
                  stroke=WARM_TXT)
        for n, line in enumerate(notes):
            txt(s, c, px + 16, py + 232 + n * 16, line, size=11, anchor="start",
                fill=INK if n == 0 else MUTED)
        stackcol(s, c, px + 330, base, 62, [(i, nums[i]) for i in stack])

    # result strip
    s.panel(24, 640, 952, 46, fill=PAPER, stroke=LINE)
    txt(s, c, 44, 668, "res =", size=13, anchor="start", weight="600")
    res = [4, 2, 4, -1, -1]
    for i, v in enumerate(res):
        x = 110 + i * 96
        fill = FILL_WARM if v != -1 else FILL_GREY
        cell(s, c, x, 648, 80, 30, str(v), fill=fill, size=13)
        txt(s, c, x + 40, 692, "res[%d]" % i, size=10, fill=MUTED)
    save(s, c, "02-pop-trace.svg")


# ---------------------------------------------------------------------------
# 03: 四个方向,同一副骨架
# ---------------------------------------------------------------------------
def fig03():
    W, H = 1000, 420
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "四个方向只差一个比较符号:同一个 nums = [3, 1, 2, 2]",
        size=15)
    txt(s, c, W / 2, 58, "栈的单调方向跟着「等谁」走:等更大用递减栈,等更小用递增栈",
        size=12, fill=MUTED)

    cards = [
        ("下一个更大", "非递增", "nums[top] < nums[i]", "[-1, 2, -1, -1]"),
        ("下一个更大或相等", "严格递减", "nums[top] <= nums[i]", "[-1, 2, 2, -1]"),
        ("下一个更小", "非递减", "nums[top] > nums[i]", "[1, -1, -1, -1]"),
        ("下一个更小或相等", "严格递增", "nums[top] >= nums[i]", "[1, -1, 2, -1]"),
    ]
    for k, (goal, mono, cond, ans) in enumerate(cards):
        px = 24 + (k % 2) * 488
        py = 80 + (k // 2) * 148
        s.panel(px, py, 464, 130, fill=PAPER, stroke=LINE)
        cell(s, c, px + 16, py + 18, 200, 32, goal, fill=FILL_BLUE, size=13)
        txt(s, c, px + 232, py + 32, "答案 = " + ans, size=12, anchor="start",
            fill=BLUE)
        txt(s, c, px + 16, py + 72, "栈(底→顶):" + mono, size=11, anchor="start",
            fill=MUTED)
        txt(s, c, px + 16, py + 92, "弹出条件:" + cond, size=12, anchor="start")
        txt(s, c, px + 16, py + 112, "答案写在被弹出的 j 身上:res[j] = nums[i]",
            size=11, anchor="start", fill=MUTED)

    s.panel(24, 380, 952, 30, fill=FILL_TEAL, stroke=LINE)
    txt(s, c, W / 2, 400,
        "「上一个更小」不用新循环:j 被弹出的那一刻,栈里挨着它下面的就是它左边第一根更矮(或相等)的柱子",
        size=11, fill=TEAL_TXT)
    save(s, c, "03-directions.svg")


# ---------------------------------------------------------------------------
# 04: 环形数组 —— 翻倍 + 取模
# ---------------------------------------------------------------------------
def fig04():
    W, H = 1000, 340
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "环形数组:把数组看成翻倍,下标取模读回来", size=15)
    txt(s, c, W / 2, 58, "扫 2n 步,答案只写前 n 位;只有第一圈才入栈", size=12, fill=MUTED)

    nums = [2, 1, 2, 4, 3]
    cw, ch = 86, 48
    x0, y0 = 62, 120
    for k in range(10):
        x = x0 + k * cw
        v = nums[k % 5]
        fill = FILL_BLUE if k < 5 else FILL_GREY
        if k == 8:
            fill = FILL_WARM
        cell(s, c, x, y0, cw, ch, str(v), fill=fill, size=15)
        txt(s, c, x + cw / 2, y0 + ch + 16, "i = %d" % k, size=10, fill=MUTED)

    # segments: first round is the real array, the copy only feeds answers
    for lo, hi, name, col in ((0, 4, "第一圈:真身,要入栈", BLUE),
                              (5, 9, "副本:只负责送答案", MUTED)):
        a = x0 + lo * cw
        b = x0 + hi * cw + cw
        s.line(a + 4, y0 + ch + 28, b - 4, y0 + ch + 28, stroke=col, sw=1.2)
        txt(s, c, (a + b) / 2, y0 + ch + 46, name, size=11, fill=col)

    # the wrap-around answer, drawn above the row
    txt(s, c, x0 + 6.5 * cw, 84, "末尾的 3 绕出去,在副本里遇到 4:res[4] = 4", size=11,
        fill=WARM_TXT)
    arrow(s, c, x0 + 4 * cw + cw / 2, 100, x0 + 8 * cw + cw / 2, 100, stroke=WARM_TXT)

    s.panel(24, 240, 460, 80, fill=CANVAS, stroke=LINE)
    txt(s, c, 44, 266, "idx = i % n", size=14, anchor="start", weight="600")
    txt(s, c, 44, 288, "i = 5..9 读到的还是下标 0..4,", size=11, anchor="start")
    txt(s, c, 44, 306, "所以 res 只写前 n 位就够了", size=11, anchor="start", fill=MUTED)

    s.panel(510, 240, 466, 80, fill=CANVAS, stroke=LINE)
    txt(s, c, 530, 266, "if i < n: stack.append(idx)", size=14, anchor="start",
        weight="600")
    txt(s, c, 530, 288, "第二圈只负责「送答案」,不再排队;", size=11, anchor="start")
    txt(s, c, 530, 306, "入栈 n 次、出栈至多 n 次,O(n) 的账才算得干净",
        size=11, anchor="start", fill=MUTED)
    save(s, c, "04-circular.svg")


# ---------------------------------------------------------------------------
# 05: 84 柱状图 —— 每根柱子的两笔账
# ---------------------------------------------------------------------------
def fig05():
    W, H = 1000, 500
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "柱状图中最大的矩形:每根柱子认领一段区间", size=15)
    txt(s, c, W / 2, 58, "heights = [2, 1, 5, 6, 2, 3],答案是 10(高 5、宽 2)",
        size=12, fill=MUTED)

    hs = [2, 1, 5, 6, 2, 3]
    unit, bw, gap = 40, 64, 22
    base = 310
    x0 = 80
    for i, v in enumerate(hs):
        x = x0 + i * (bw + gap)
        fill = FILL_WARM if i in (2, 3) else FILL_BLUE
        bar(s, x, base, bw, v, unit, fill=fill)
        txt(s, c, x + bw / 2, base + 18, "i=%d  h=%d" % (i, v), size=11, fill=MUTED)

    # the winning rectangle: j = 2, width = R - L - 1 = 4 - 1 - 1 = 2
    L, R, j = 1, 4, 2
    rect_x = x0 + j * (bw + gap)
    rect_w = (R - L - 1) * (bw + gap) - gap
    s.rect(rect_x, base - 5 * unit, rect_w, 5 * unit, fill="none", stroke=WARM_TXT,
           sw=2.2, rx=3, dash="6 4")
    txt(s, c, rect_x + rect_w / 2, base - 5 * unit + 60, "5 × 2 = 10", size=14,
        fill=WARM_TXT, weight="600")
    txt(s, c, rect_x + rect_w / 2, base - 5 * unit + 82, "柱子 2 说了算的范围", size=11,
        fill=WARM_TXT)

    # annotation card on the right: where L and R come from
    s.panel(648, 76, 328, 234, fill=CANVAS, stroke=LINE)
    txt(s, c, 668, 104, "柱子 j = 2 的两笔账", size=13, anchor="start", weight="600")
    lines = [
        "L(j) = 左边第一根「更矮或相等」 = 1",
        "R(j) = 右边第一根「严格更矮」 = 4",
        "",
        "84:面积 = 高 × (R - L - 1)",
        "          = 5 × (4 - 1 - 1) = 10",
        "907:个数 = (j - L) × (R - j)",
        "          = 1 × 2 = 2 个区间",
    ]
    for k, line in enumerate(lines):
        txt(s, c, 668, 132 + k * 22, line, size=11, anchor="start",
            fill=INK if line else MUTED)
    txt(s, c, 668, 296, "宽度是「一个矩形」,个数是「一堆区间」", size=11, anchor="start",
        fill=TEAL_TXT)

    s.panel(24, 336, 460, 130, fill=PAPER, stroke=LINE)
    txt(s, c, 44, 362, "84 只要一笔账:最大值", size=13, anchor="start", weight="600")
    txt(s, c, 44, 386, "高 = heights[j],宽 = R - L - 1", size=12, anchor="start")
    txt(s, c, 44, 406, "每根柱子算一次,取最大的 → 10", size=12, anchor="start")
    txt(s, c, 44, 430, "柱子 3(h=6)只拿到 6 × 1 = 6,比 10 小", size=11, anchor="start",
        fill=MUTED)

    s.panel(510, 336, 466, 130, fill=PAPER, stroke=LINE)
    txt(s, c, 530, 362, "907 要另一笔账:求和", size=13, anchor="start", weight="600")
    txt(s, c, 530, 386, "个数 = (j - L) × (R - j)", size=12, anchor="start")
    txt(s, c, 530, 406, "左端点 j-L 种选法,右端点 R-j 种选法", size=12, anchor="start")
    txt(s, c, 530, 430, "Σ 高度 × 个数 = 所有子区间的最小值之和", size=11,
        anchor="start", fill=MUTED)
    save(s, c, "05-histogram.svg")


# ---------------------------------------------------------------------------
# 06: 42 接雨水 —— 水是一层一层结算的
# ---------------------------------------------------------------------------
def fig06():
    W, H = 1000, 440
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 34, "接雨水:同一副递减栈,弹出时结算「一层」水", size=15)
    txt(s, c, W / 2, 58, "height = [4, 2, 0, 3, 2, 5],一层一层加,总水量 9",
        size=12, fill=MUTED)

    hs = [4, 2, 0, 3, 2, 5]
    unit, bw, gap = 44, 76, 20
    base = 340
    x0 = 110
    for i, v in enumerate(hs):
        x = x0 + i * (bw + gap)
        bar(s, x, base, bw, v, unit, fill=FILL_BLUE)
        txt(s, c, x + bw / 2, base + 20, "i=%d" % i, size=11, fill=MUTED)
        txt(s, c, x + bw / 2, base + 36, "h=%d" % v, size=11, fill=MUTED)

    # water layers: (level_lo, level_hi, first_index, last_index, tag, tag_x)
    layers = [
        (0, 2, 2, 2, "① 宽 1 × 深 2 = 2", 2),
        (2, 3, 1, 2, "② 宽 2 × 深 1 = 2", 1),
        (2, 3, 4, 4, "③ 宽 1 × 深 1 = 1", 4),
        (3, 4, 1, 4, "④ 宽 4 × 深 1 = 4", 3),
    ]
    for lo, hi, first, last, tag, tagi in layers:
        lx = x0 + first * (bw + gap)
        rx = x0 + last * (bw + gap) + bw
        s.rect(lx + 2, base - hi * unit, rx - lx - 4, (hi - lo) * unit,
               fill=FILL_TEAL, stroke=TEAL_TXT, sw=1.2, rx=2, op=0.85)
        txt(s, c, lx + (rx - lx) / 2, base - (lo + hi) / 2 * unit + 4, tag.split()[0],
            size=14, fill=TEAL_TXT, weight="600")

    # legend for the four layers, placed under the bars
    txt(s, c, W / 2, 404, "  ".join(t for _, _, _, _, t, _ in layers), size=12)
    txt(s, c, W / 2, 426,
        "每一层都很薄:底 = 被弹出的柱子,左壁 = 栈里下一个,右壁 = 新来的柱子;四层相加 = 9",
        size=11, fill=MUTED)
    save(s, c, "06-trap.svg")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    fig01()
    fig02()
    fig03()
    fig04()
    fig05()
    fig06()
    print("problems: %d" % problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
