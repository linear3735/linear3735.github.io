#!/usr/bin/env python3
"""Generate the five diagrams for _posts/2026-12-02-math-tricks.md.

Run from anywhere:  /opt/miniconda3/bin/python3 make_figures.py
Output goes to assets/img/math-tricks-20261202/.

Every text run is registered with svgkit.Check at the *same* x/y it is drawn
at, so the geometric self-check is meaningful (Check cannot see what was drawn;
it only knows what the author told it).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent                          # assets/blog
OUT = BLOG.parent / "img" / "math-tricks-20261202"
sys.path.insert(0, str(BLOG / "_tools"))

from svgkit import (Check, Svg, INK, MUTED, BLUE, CANVAS, FILL_BLUE,   # noqa: E402
                    FILL_GREY, FILL_TEAL, FILL_WARM, PAPER, TEAL_TXT,
                    WARM_TXT)


def T(s, c, name, x, y, t, size=14, fill=INK, anchor="middle", weight="400"):
    """Draw a label and register it with the checker at the same coordinates."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)


def P(s, c, name, x, y, w, h, fill=CANVAS):
    s.panel(x, y, w, h, fill=fill)
    c.panel(name, x, y, w, h)


def bit_header(s, c, tag, x0, y, nbits, cell=44, gap=6, size=11):
    for k in range(nbits):
        cx = x0 + k * (cell + gap) + cell / 2
        T(s, c, "%s-h%d" % (tag, k), cx, y, "bit %d" % (nbits - 1 - k),
          size=size, fill=MUTED)


def bit_row(s, c, tag, x0, y, bits, fills=None, cell=44, gap=6, size=20):
    """bits is MSB-first; fills, if given, is one colour per cell."""
    for k, ch in enumerate(bits):
        cx = x0 + k * (cell + gap)
        s.rect(cx, y, cell, cell, fill=(fills[k] if fills else PAPER),
               stroke=INK, sw=1.2, rx=4)
        T(s, c, "%s-%d" % (tag, k), cx + cell / 2, y + cell * 0.66, ch,
          size=size, weight="600")


# --------------------------------------------------------------------------
# 01  n & (n-1)  vs  n & -n
# --------------------------------------------------------------------------

def fig_clear_lowest_bit():
    W, H, CELL, GAP = 1180, 580, 44, 6
    s, c = Svg(W, H), None
    c = Check(s)
    T(s, c, "title", W / 2, 50, "同一个数,两种位级动作:n = 44 = 0b101100",
      size=20, weight="600")

    P(s, c, "pL", 28, 84, 548, 400)
    P(s, c, "pR", 604, 84, 548, 400)
    T(s, c, "lt", 302, 118, "n & (n-1):消掉最低位的 1", size=16, weight="600")
    T(s, c, "rt", 878, 118, "n & -n:只留最低位的 1", size=16, weight="600")

    x0L, x0R = 155, 731
    span = 6 * CELL + 5 * GAP
    warm = [FILL_GREY] * 3 + [FILL_WARM] * 3          # b2 b1 b0 = affected
    greens = [FILL_GREY] * 3 + [FILL_WARM] + [FILL_GREY] * 2

    for x0, tag in ((x0L, "L"), (x0R, "R")):
        bit_header(s, c, tag, x0, 152, 6, cell=CELL, gap=GAP)

    # left: n, n-1, n & (n-1)
    rows = [("n", "101100", warm, 168, "44"),
            ("n - 1", "101011", warm, 246, "43"),
            ("n & (n-1)", "101000", warm, 324, "40")]
    for name, bits, fills, y, val in rows:
        T(s, c, "L-lab-" + val, x0L - 12, y + 29, name, size=13,
          anchor="end", fill=MUTED)
        bit_row(s, c, "L" + val, x0L, y, bits, fills=fills, cell=CELL, gap=GAP)
        T(s, c, "L-val-" + val, x0L + span + 16, y + 29, "= " + val, size=13,
          anchor="start", fill=INK)
    T(s, c, "L-note1", 302, 430,
      "借位只影响最低位的 1 及其右侧:右边 0 全变 1,更高的位两边相同",
      size=13, fill=MUTED)
    T(s, c, "L-note2", 302, 458, "44 & 43 = 40:最低位的 1 被消掉",
      size=13, fill=WARM_TXT)

    # right: n, -n, n & -n
    rows = [("n", "101100", greens, 168, "44"),
            ("-n", "010100", [FILL_GREY] * 3 + [FILL_WARM, FILL_BLUE, FILL_BLUE],
             246, "20"),
            ("n & -n", "000100", greens, 324, "4")]
    for name, bits, fills, y, val in rows:
        T(s, c, "R-lab-" + val, x0R - 12, y + 29, name, size=13,
          anchor="end", fill=MUTED)
        bit_row(s, c, "R" + val, x0R, y, bits, fills=fills, cell=CELL, gap=GAP)
        T(s, c, "R-val-" + val, x0R + span + 16, y + 29, "= " + val, size=13,
          anchor="start", fill=INK)
    T(s, c, "R-note1", 878, 430,
      "-n = ~n + 1:低位的 0 取反成 1 又被进位带回 0,最低位的 1 原地留下",
      size=13, fill=MUTED)
    T(s, c, "R-note2", 878, 458, "44 & -44 = 4 = 2^2,下标 2 就是它的位置",
      size=13, fill=WARM_TXT)

    T(s, c, "foot", W / 2, 536,
      "减一之后做与 = 干掉最低位的 1;取负之后做与 = 留下最低位的 1",
      size=15, fill=INK)
    return s, c, "01-clear-lowest-bit"


# --------------------------------------------------------------------------
# 02  bitmap words
# --------------------------------------------------------------------------

def fig_bitmap_words():
    W, H = 1180, 560
    s = Svg(W, H)
    c = Check(s)
    T(s, c, "title", W / 2, 50, "位图:8 字节装 64 个布尔,而不是 8 个",
      size=20, weight="600")

    P(s, c, "pa", 28, 84, 548, 330)
    T(s, c, "pa-t", 302, 118, "boolean[]:每个元素占 1 字节", size=16,
      weight="600")
    bits = "10110010"
    x0, y0, cw = 175, 150, 56
    for k, ch in enumerate(bits):
        col, row = k % 4, k // 4
        x, y = x0 + col * (cw + 10), y0 + row * (cw + 18)
        s.rect(x, y, cw, cw, fill=(FILL_WARM if ch == "1" else PAPER),
               stroke=INK, sw=1.2, rx=4)
        T(s, c, "pa-b%d" % k, x + cw / 2, y + cw * 0.62, ch, size=18,
          weight="600")
    T(s, c, "pa-c1", 302, 316, "8 个布尔 = 8 字节 = 64 比特", size=13.5)
    T(s, c, "pa-c2", 302, 346,
      "真正携带信息的只有 8 比特,其余 56 比特是浪费(7/8)", size=13,
      fill=MUTED)
    T(s, c, "pa-c3", 302, 376, "所以日常开发用布尔数组就够了", size=13,
      fill=MUTED)

    P(s, c, "pb", 604, 84, 548, 330)
    T(s, c, "pb-t", 878, 118, "位图:1 个 64 位字装 64 个布尔", size=16,
      weight="600")
    word = ["1" if i in (0, 3, 13) else "0" for i in range(16)]
    wx, wy, wcw, wgap = 623, 170, 30, 2
    for k, ch in enumerate(word):
        x = wx + k * (wcw + wgap)
        s.rect(x, wy, wcw, 56, fill=(FILL_WARM if ch == "1" else PAPER),
               stroke=INK, sw=1.1, rx=3)
        T(s, c, "pb-b%d" % k, x + wcw / 2, wy + 34, ch, size=13, weight="600")
    T(s, c, "pb-l", 638, 248, "bit 63", size=11, fill=MUTED)
    T(s, c, "pb-r", 1118, 248, "bit 48", size=11, fill=MUTED)
    T(s, c, "pb-mid", 878, 278, "(画的是字里的高 16 位,其余 48 位同理)",
      size=11, fill=MUTED)
    T(s, c, "pb-f1", 878, 314, "第 i 位 → words[i >> 6] 的第 (i & 63) 位",
      size=15, weight="600")
    T(s, c, "pb-f2", 878, 344, "64 = 2^6,所以 i % 64 等价于 i & 63",
      size=13, fill=MUTED)
    T(s, c, "pb-f3", 878, 374, "i = 100 → 字下标 1、位偏移 36", size=13,
      fill=WARM_TXT)

    T(s, c, "foot1", W / 2, 460,
      "代价:字下标与位偏移要自己算,换来的内存是原来的 1/8",
      size=14, fill=INK)
    T(s, c, "foot2", W / 2, 492,
      "集合没大到布尔数组开不下时,不值得换成位图", size=13.5, fill=MUTED)
    return s, c, "02-bitmap-words"


# --------------------------------------------------------------------------
# 03  Fisher-Yates
# --------------------------------------------------------------------------

def fig_fisher_yates():
    W, H = 1180, 620
    s = Svg(W, H)
    c = Check(s)
    T(s, c, "title", W / 2, 50, "Fisher-Yates:从后往前,已确定的位置不再参与交换",
      size=19, weight="600")

    P(s, c, "pa", 28, 84, 660, 330)
    T(s, c, "pa-t", 358, 118, "第 i 轮:j 在 [0, i] 里均匀取,交换 a[i] 和 a[j]",
      size=14)
    cw, gap = 96, 8
    x0, y0 = 102, 200
    for k, ch in enumerate("abcde"):
        x = x0 + k * (cw + gap)
        s.rect(x, y0, cw, 64, fill=(FILL_GREY if k == 4 else FILL_BLUE),
               stroke=INK, sw=1.2, rx=4)
        T(s, c, "pa-v%d" % k, x + cw / 2, y0 + 42, ch, size=20, weight="600")
        T(s, c, "pa-i%d" % k, x + cw / 2, y0 + 90, str(k), size=12, fill=MUTED)
    br_l, br_r = x0, x0 + 3 * (cw + gap) + cw
    s.line(br_l, 186, br_r, 186, stroke=BLUE, sw=1.6)
    s.line(br_l, 178, br_l, 186, stroke=BLUE, sw=1.6)
    s.line(br_r, 178, br_r, 186, stroke=BLUE, sw=1.6)
    T(s, c, "pa-brk", (br_l + br_r) / 2, 168, "候选区间:j ∈ [0, 3]", size=13,
      fill=BLUE)
    T(s, c, "pa-fix", x0 + 4 * (cw + gap) + cw / 2, 168, "已确定", size=13,
      fill=MUTED)
    s.arrow(br_r, 330, br_l, 330, stroke=BLUE)
    T(s, c, "pa-arr", (br_l + br_r) / 2, 312, "swap(a[i], a[j]):i 与随机的 j 交换",
      size=12.5, fill=BLUE)
    T(s, c, "pa-note", 358, 380, "第 i 轮之后,位置 i 不会再被任何后续步骤碰到",
      size=13, fill=MUTED)

    P(s, c, "pb", 716, 84, 436, 330)
    T(s, c, "pb-t", 934, 118, "为什么是 n! 种等概率的选择序列", size=14,
      weight="600")
    lines = [
        ("pb-l1", 160, "每轮的选择次数:n, n-1, …, 2", MUTED),
        ("pb-l2", 190, "总序列数 = n × (n-1) × … × 1 = n!", INK),
        ("pb-l3", 220, "每种选择序列的概率彼此相等", MUTED),
        ("pb-l4", 250, "每种序列 ↔ 一个不同的排列(一一对应)", INK),
        ("pb-l5", 280, "⇒ 每个排列的概率 = 1/n!", BLUE),
    ]
    for name, y, t, col in lines:
        T(s, c, name, 744, y, t, size=13, fill=col, anchor="start")
    T(s, c, "pb-w1", 744, 320, "已确定的后缀不参与后续交换,", size=13,
      fill=WARM_TXT, anchor="start")
    T(s, c, "pb-w2", 744, 350, "这正是序列与排列一一对应的原因。", size=13,
      fill=WARM_TXT, anchor="start")

    P(s, c, "pc", 28, 442, 1124, 150)
    T(s, c, "pc-t", 56, 478,
      "对照:错误的写法 —— for i in 0 … n-1,每轮 j 都取 [0, n-1]", size=14,
      fill=WARM_TXT, anchor="start")
    T(s, c, "pc-l1", 56, 514,
      "选择序列有 n^n 种且等概率 ⇒ 若结果均匀,则每个排列的概率 = m / n^n,"
      "必须 n! | n^n", size=13, fill=INK, anchor="start")
    T(s, c, "pc-l2", 56, 544,
      "而 n = 3 时 6 不能整除 27,n = 4 时 24 不能整除 256 ⇒ 不可能均匀(纯计数论证,不用跑程序)",
      size=13, fill=INK, anchor="start")
    return s, c, "03-fisher-yates"


# --------------------------------------------------------------------------
# 04  reservoir sampling
# --------------------------------------------------------------------------

def fig_reservoir_sampling():
    W, H = 1180, 620
    s = Svg(W, H)
    c = Check(s)
    T(s, c, "title", W / 2, 50, "水塘抽样:第 j 个元素活到最后的概率是 1/n",
      size=19, weight="600")

    P(s, c, "pa", 28, 84, 520, 300)
    T(s, c, "pa-t1", 288, 118, "第 i 个元素(i > k)到达时:", size=13.5)
    T(s, c, "pa-t2", 288, 146, "以 k/i 的概率替换一个槽位", size=13.5,
      weight="600")
    cw, gap = 60, 8
    x0, y0 = 122, 190
    for k, ch in enumerate(["j", "j+1", "j+2", "…", "n"]):
        x = x0 + k * (cw + gap)
        fill = FILL_GREY
        if k == 0:
            fill = FILL_WARM
        elif k == 4:
            fill = FILL_BLUE
        s.rect(x, y0, cw, 50, fill=fill, stroke=INK, sw=1.2, rx=4)
        T(s, c, "pa-e%d" % k, x + cw / 2, y0 + 32, ch, size=13, weight="600")
    T(s, c, "pa-ord", 270, 264, "到达顺序:共 n 个", size=11.5, fill=MUTED,
      anchor="end")
    s.arrow(x0 + 2 * (cw + gap) + cw / 2, 250, x0 + 2 * (cw + gap) + cw / 2, 286,
            stroke=BLUE)
    s.rect(122, 292, 332, 60, fill=FILL_TEAL, stroke=INK, sw=1.2, rx=6)
    T(s, c, "pa-res", 288, 328, "水塘:k 个槽位,每个槽位机会相同", size=12.5)

    P(s, c, "pb", 576, 84, 576, 300)
    T(s, c, "pb-t", 604, 118, "两个条件相乘(相互独立):", size=13.5,
      weight="600", anchor="start")
    T(s, c, "pb-l1", 604, 152, "① 它到达时被选中:概率 1/j", size=13,
      anchor="start")
    T(s, c, "pb-l2", 604, 182, "② 之后每个 i 都没替换它:1 - 1/i = (i-1)/i",
      size=13, anchor="start")
    T(s, c, "pb-l3", 604, 222, "P = (1/j) · (j/(j+1)) · ((j+1)/(j+2)) · …",
      size=13, anchor="start")
    T(s, c, "pb-l4", 604, 252, "     · ((n-1)/n)", size=13, anchor="start")
    T(s, c, "pb-l5", 604, 300, "= 1/n,和 j 无关", size=15, fill=BLUE,
      weight="600", anchor="start")
    T(s, c, "pb-l6", 604, 340, "k > 1 时:被挤掉 = (k/i)·(1/k) = 1/i,同一个连乘",
      size=12.5, fill=TEAL_TXT, anchor="start")

    P(s, c, "pc", 28, 416, 1124, 176)
    T(s, c, "pc-t", 56, 452, "连锁约掉:中间的 j、j+1、…、n-1 两两抵消",
      size=14, weight="600", anchor="start")
    T(s, c, "pc-l1", 56, 492,
      "P = (1/j) × [j/(j+1)] × [(j+1)/(j+2)] × … × [(n-1)/n] = 1/n", size=13.5,
      anchor="start")
    T(s, c, "pc-l2", 56, 526, "k = 1, n = 3, j = 1 时:(1/1) × (1/2) × (2/3) = 1/3",
      size=13, fill=MUTED, anchor="start")
    T(s, c, "pc-l3", 56, 560, "换成 k 个槽位:每个元素被留下的概率都是 k/n",
      size=13, fill=TEAL_TXT, anchor="start")
    return s, c, "04-reservoir-sampling"


# --------------------------------------------------------------------------
# 05  fast power
# --------------------------------------------------------------------------

def fig_fast_pow():
    W, H = 1180, 580
    s = Svg(W, H)
    c = Check(s)
    T(s, c, "title", W / 2, 50, "快速幂:b = 13 = 0b1101,指数拆成 8 + 4 + 1",
      size=19, weight="600")

    P(s, c, "pa", 28, 84, 1124, 216)
    centers = [290, 490, 690, 890]
    bitsv = ["1", "1", "0", "1"]
    weights = ["权 8", "权 4", "权 2", "权 1"]
    use = ["乘进 res", "乘进 res", "跳过", "乘进 res"]
    for k, cx in enumerate(centers):
        T(s, c, "pa-h%d" % k, cx, 124, "bit %d" % (3 - k), size=12, fill=MUTED)
        s.rect(cx - 28, 150, 56, 56,
               fill=(FILL_GREY if bitsv[k] == "0" else FILL_WARM),
               stroke=INK, sw=1.2, rx=4)
        T(s, c, "pa-b%d" % k, cx, 187, bitsv[k], size=22, weight="600")
        T(s, c, "pa-w%d" % k, cx, 232, weights[k], size=12.5, fill=MUTED)
        T(s, c, "pa-u%d" % k, cx, 262, use[k], size=12.5,
          fill=(MUTED if use[k] == "跳过" else WARM_TXT))
    T(s, c, "pa-note", 590, 288, "13 的二进制里,第 0、2、3 位是 1", size=12,
      fill=MUTED)

    P(s, c, "pb", 28, 324, 1124, 190)
    T(s, c, "pb-t", 590, 356, "底数逐次平方:a^(2^t) 由上一项平方得到", size=14,
      weight="600")
    bx, by, bw, bh = [190, 450, 710, 970], 396, 120, 56
    labels = ["a^1", "a^2", "a^4", "a^8"]
    used = [True, False, True, True]
    for k, cx in enumerate(bx):
        s.rect(cx - bw / 2, by, bw, bh,
               fill=(FILL_WARM if used[k] else FILL_BLUE), stroke=INK, sw=1.2,
               rx=6)
        T(s, c, "pb-v%d" % k, cx, by + 36, labels[k], size=16, weight="600")
    for k in range(3):
        x1, x2 = bx[k] + bw / 2 + 8, bx[k + 1] - bw / 2 - 8
        s.arrow(x1, by + bh / 2, x2, by + bh / 2, stroke=BLUE)
        c.arrow("pb-a%d" % k, x1, by + bh / 2, x2, by + bh / 2)
        T(s, c, "pb-s%d" % k, (x1 + x2) / 2, by + bh / 2 - 18, "平方", size=12,
          fill=BLUE)
    notes = ["bit 0 用到", "bit 1:跳过", "bit 2 用到", "bit 3 用到"]
    for k, cx in enumerate(bx):
        T(s, c, "pb-n%d" % k, cx, 478, notes[k], size=12, fill=MUTED)

    T(s, c, "foot", W / 2, 548,
      "res = a^1 × a^4 × a^8 = a^13;乘法次数 = b 的位数 ≈ log2 b,而不是 b",
      size=14, fill=MUTED)
    return s, c, "05-fast-pow-binary"


FILL_TEAL = "#e4f1ee"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for build in (fig_clear_lowest_bit, fig_bitmap_words, fig_fisher_yates,
                  fig_reservoir_sampling, fig_fast_pow):
        s, c, name = build()
        bad = c.run(name)
        s.save(OUT / (name + ".svg"))
        total += bad
    print("  %d figure(s), %d layout problem(s)" % (5, total))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
