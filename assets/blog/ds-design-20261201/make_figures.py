#!/usr/bin/env python3
"""Generate the five diagrams for the ds-design post.

Every label is registered with `Check` at the same x it was drawn at, so the
geometric self-check (off-canvas / text-text overlap / spill out of a panel)
actually sees the figure rather than a subset of it.

Run:  /opt/miniconda3/bin/python3 assets/blog/ds-design-20261201/make_figures.py
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "_tools"))
from svgkit import (Check, Svg, BLUE, CANVAS, FILL_BLUE, FILL_GREY,  # noqa: E402
                    FILL_TEAL, FILL_WARM, INK, LINE, MUTED, PAPER,
                    TEAL_TXT, WARM_TXT)

OUT = HERE.parents[2] / "img" / "ds-design-20261201"

PROBLEMS = 0


def T(s, c, name, x, y, t, size=14, fill=INK, anchor="middle", weight="400"):
    """text() + Check registration. x must match exactly or the check is a lie."""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)
    return s


def B(s, c, name, x, y, w, h, label, sub=None, fill=PAPER, stroke=INK,
      size=14, sub_size=11):
    """box() + Check registration of both lines, at box()'s own coordinates."""
    s.box(x, y, w, h, label, sub, fill=fill, stroke=stroke, size=size,
          sub_size=sub_size)
    if sub:
        c.text(name, x + w / 2, y + h / 2 - 3, label, size=size)
        c.text(name + ".sub", x + w / 2, y + h / 2 + 14, sub, size=sub_size)
    else:
        c.text(name, x + w / 2, y + h / 2 + size * 0.36, label, size=size)
    return s


def CELL(s, c, name, x, y, w, h, label, fill=PAPER, size=16):
    s.cell(x, y, w, h, label, fill=fill, size=size)
    c.text(name, x + w / 2, y + h / 2 + size * 0.36, label, size=size)
    return s


def finish(s, c, name):
    global PROBLEMS
    PROBLEMS += c.run(name)
    OUT.mkdir(parents=True, exist_ok=True)
    s.save(OUT / name)


# ---------------------------------------------------------------- figure 1
def fig1():
    """LRU: the two halves and what each one is for."""
    s, c = Svg(860, 480), None
    c = Check(s)
    T(s, c, "t", 430, 34,
      "LRU = 哈希表(找得到) + 双向链表(谁先走)", size=17, weight="600")

    s.panel(36, 60, 788, 200)
    c.panel("pA", 36, 60, 788, 200)
    T(s, c, "pA.t", 430, 88, "双向链表:维持「谁最久没用」的全序", size=13, fill=MUTED)

    labels = ["head", "key 1", "key 2", "key 3", "tail"]
    subs = ["哨兵", "节点", "节点", "节点", "哨兵"]
    xs = [184, 286, 388, 490, 592]
    for i, (lb, sb, x) in enumerate(zip(labels, subs, xs)):
        B(s, c, "n%d" % i, x, 118, 84, 64, lb, sb, size=13, sub_size=10,
          fill=FILL_GREY if i in (0, 4) else FILL_BLUE)
    # 双向:每一段都画一前一后两个箭头
    for x in (268, 370, 472, 574):
        s.arrow(x, 138, x + 18, 138, stroke=BLUE, sw=1.5)
        s.arrow(x + 18, 168, x, 168, stroke=BLUE, sw=1.5)
        c.arrow("fwd%d" % x, x, 138, x + 18, 138)
        c.arrow("bwd%d" % x, x + 18, 168, x, 168)
    T(s, c, "lr", 184, 208, "最久未使用 ← 淘汰这头", size=12,
      fill=WARM_TXT, anchor="start")
    T(s, c, "mr", 676, 208, "→ 最近使用:新访问挂这头", size=12,
      fill=TEAL_TXT, anchor="end")

    s.panel(36, 286, 788, 120)
    c.panel("pB", 36, 286, 788, 120)
    T(s, c, "pB.t", 56, 312, "哈希表:key → 节点", size=13, fill=MUTED,
      anchor="start")
    for i, (lb, x) in enumerate(zip(["key 1 → node", "key 2 → node",
                                     "key 3 → node"], [56, 316, 576])):
        B(s, c, "h%d" % i, x, 330, 240, 44, lb, size=13, fill=PAPER)

    T(s, c, "cap", 430, 440,
      "get 命中:哈希表 O(1) 找到节点 → 摘下来 → 挂到 tail 那端。两件事都由 O(1) 完成",
      size=13)
    finish(s, c, "01-lru-hash-plus-list.svg")


# ---------------------------------------------------------------- figure 2
def fig2():
    """LFU: freq buckets, and why minFreq is O(1) to maintain."""
    s, c = Svg(860, 470), None
    c = Check(s)
    T(s, c, "t", 430, 34,
      "LFU = 哈希表 + 频率桶(每个桶自己是一条 LRU)+ minFreq", size=17,
      weight="600")

    s.panel(36, 60, 300, 310)
    c.panel("pA", 36, 60, 300, 310)
    T(s, c, "pA.t", 186, 86, "两张映射表", size=13, fill=MUTED)
    rows = ["a  →  val 10 ,  freq 2", "b  →  val 20 ,  freq 1",
            "c  →  val 30 ,  freq 1", "d  →  val 40 ,  freq 3"]
    for i, lb in enumerate(rows):
        B(s, c, "r%d" % i, 56, 106 + i * 50, 260, 40, lb, size=12)

    s.panel(356, 60, 468, 310)
    c.panel("pB", 356, 60, 468, 310)
    T(s, c, "pB.t", 590, 86, "freqToKeys:频率 → 桶(桶内按进入先后排序)",
      size=13, fill=MUTED)

    # freq 1 is the minFreq row -> warm; it is also where eviction happens
    B(s, c, "f1l", 376, 106, 76, 48, "freq 1", size=12, fill=FILL_WARM,
      stroke=WARM_TXT)
    B(s, c, "f1a", 468, 106, 76, 48, "a", size=14, fill=FILL_WARM,
      stroke=WARM_TXT)
    B(s, c, "f1b", 560, 106, 76, 48, "b", size=14, fill=FILL_WARM,
      stroke=WARM_TXT)
    s.arrow(544, 130, 560, 130, stroke=WARM_TXT, sw=1.5)
    c.arrow("f1ar", 544, 130, 560, 130)
    T(s, c, "f1n", 792, 130, "← minFreq", size=12, fill=WARM_TXT)

    B(s, c, "f2l", 376, 176, 76, 48, "freq 2", size=12, fill=FILL_BLUE)
    B(s, c, "f2a", 468, 176, 76, 48, "c", size=14, fill=FILL_BLUE)
    B(s, c, "f3l", 376, 246, 76, 48, "freq 3", size=12, fill=FILL_TEAL)
    B(s, c, "f3a", 468, 246, 76, 48, "d", size=14, fill=FILL_TEAL)

    T(s, c, "ev", 590, 320, "淘汰 = minFreq 那一行的桶头(同频里最旧)",
      size=12, fill=WARM_TXT)
    T(s, c, "up", 590, 346, "升频:freq f → f+1,从旧桶摘走、挂到新桶尾部",
      size=12, fill=TEAL_TXT)

    T(s, c, "cap", 430, 412,
      "旧的最小桶空了,新最小值必然正好是 f+1 —— 因为频率每次只 +1,不会跳档",
      size=13)
    T(s, c, "cap2", 430, 442,
      "所以 minFreq 只需常数时间维护;若写成「无条件 minFreq = f+1」,就会淘汰错对象",
      size=12, fill=MUTED)
    finish(s, c, "02-lfu-freq-buckets.svg")


# ---------------------------------------------------------------- figure 3
def fig3():
    """MinStack: same pushes, two encodings."""
    s, c = Svg(860, 440), None
    c = Check(s)
    T(s, c, "t", 430, 34, "最小栈:push 5 → 3 → 4 之后,两种解法各存了什么",
      size=17, weight="600")

    s.panel(36, 60, 380, 280)
    c.panel("pA", 36, 60, 380, 280)
    T(s, c, "pA.t", 226, 88, "双栈法:历史最小值原样留一份", size=13, fill=MUTED)
    T(s, c, "dh", 121, 116, "data", size=12, fill=BLUE)
    T(s, c, "mh", 271, 116, "mins", size=12, fill=TEAL_TXT)
    for i, (d, m) in enumerate([("4", "3"), ("3", "3"), ("5", "5")]):
        CELL(s, c, "d%d" % i, 76, 130 + i * 50, 90, 46, d,
             fill=FILL_BLUE if i == 0 else PAPER)
        CELL(s, c, "m%d" % i, 226, 130 + i * 50, 90, 46, m, fill=FILL_TEAL)
    T(s, c, "pA.c", 226, 314, "mins[i] = min(data[0..i]),两栈同增同减",
      size=12, fill=MUTED)

    s.panel(444, 60, 380, 280)
    c.panel("pB", 444, 60, 380, 280)
    T(s, c, "pB.t", 634, 88, "差值法:只存「与当时最小值的差」", size=13,
      fill=MUTED)
    T(s, c, "dfh", 545, 116, "diff", size=12, fill=WARM_TXT)
    for i, v in enumerate(["1", "-2", "0"]):
        CELL(s, c, "x%d" % i, 500, 130 + i * 50, 90, 46, v,
             fill=FILL_WARM if i == 0 else PAPER)
    B(s, c, "mv", 654, 176, 116, 48, "min_val", "= 3", size=12, sub_size=12,
      fill=FILL_GREY)
    T(s, c, "pB.c", 634, 314, "d < 0 说明这一层存的正是最小值本身",
      size=12, fill=MUTED)

    T(s, c, "cap", 430, 384,
      "双栈法对每个元素各留一份最小值;差值法把信息编码进这一个数里,只多一个变量",
      size=13)
    T(s, c, "cap2", 430, 414,
      "代价:差值法要 x - min_val,极端值下会溢出 32 位 int",
      size=12, fill=WARM_TXT)
    finish(s, c, "03-minstack-two-vs-diff.svg")


# ---------------------------------------------------------------- figure 4
def fig4():
    """RandomisedSet: delete-by-swap keeps the array dense."""
    s, c = Svg(860, 440), None
    c = Check(s)
    T(s, c, "t", 430, 34, "删除 O(1):把末尾元素换进空洞,再砍掉末尾",
      size=17, weight="600")

    T(s, c, "t1", 60, 74, "remove(7) 之前:vals 稠密,idx 记着每个值的下标",
      size=13, fill=MUTED, anchor="start")
    for i, (v, f) in enumerate(zip(["3", "7", "1", "9"],
                                   [PAPER, FILL_WARM, PAPER, FILL_BLUE])):
        CELL(s, c, "a%d" % i, 60 + i * 100, 92, 96, 54, v, fill=f)
    for i, v in enumerate(["0", "1", "2", "3"]):
        T(s, c, "ai%d" % i, 108 + i * 100, 170, v, size=12, fill=MUTED)
    T(s, c, "aix", 60, 170, "下标", size=12, fill=MUTED, anchor="start")
    T(s, c, "idx1", 60, 208, "idx = { 3→0,  7→1,  1→2,  9→3 }    要删 7,它在 i = 1",
      size=13, anchor="start")

    s.arrow(430, 224, 430, 258, stroke=BLUE, sw=1.8)
    c.arrow("down", 430, 224, 430, 258)

    T(s, c, "t2", 60, 288, "remove(7) 之后:把末尾的 9 搬到 i = 1,再 pop 掉末尾",
      size=13, fill=MUTED, anchor="start")
    for i, (v, f) in enumerate(zip(["3", "9", "1"],
                                   [PAPER, FILL_BLUE, PAPER])):
        CELL(s, c, "b%d" % i, 60 + i * 100, 306, 96, 54, v, fill=f)
    for i, v in enumerate(["0", "1", "2"]):
        T(s, c, "bi%d" % i, 108 + i * 100, 384, v, size=12, fill=MUTED)
    T(s, c, "bix", 60, 384, "下标", size=12, fill=MUTED, anchor="start")
    T(s, c, "idx2", 460, 330, "idx = { 3→0,  9→1,  1→2 }", size=13,
      anchor="start")
    T(s, c, "why", 460, 362, "只碰 i 和末尾两个位置,与 n 无关", size=12,
      fill=TEAL_TXT, anchor="start")
    finish(s, c, "04-swap-to-end.svg")


# ---------------------------------------------------------------- figure 5
def fig5():
    """Twitter: k-way merge of per-user chains, only ever 10 deep."""
    s, c = Svg(860, 470), None
    c = Check(s)
    T(s, c, "t", 430, 34, "信息流 = k 条已排序链表的归并(每条只深入前 10 格)",
      size=17, weight="600")

    s.panel(36, 58, 500, 300)
    c.panel("pA", 36, 58, 500, 300)
    T(s, c, "pA.t", 286, 84, "每个用户的推文链(左 = 最新)", size=13, fill=MUTED)
    chains = [("user 1", ["t5", "t3", "t1"]),
              ("user 2", ["t6", "t4"]),
              ("user 3", ["t7", "t2"])]
    for r, (who, items) in enumerate(chains):
        y = 104 + r * 76
        T(s, c, "u%d" % r, 88, y + 30, who, size=12, anchor="end")
        for i, it in enumerate(items):
            x = 92 + i * 108
            B(s, c, "c%d_%d" % (r, i), x, y, 84, 52, it, size=14,
              fill=FILL_BLUE if i == 0 else PAPER)
            if i:
                s.arrow(x - 24, y + 26, x - 4, y + 26, stroke=BLUE, sw=1.5)
                c.arrow("ca%d_%d" % (r, i), x - 24, y + 26, x - 4, y + 26)

    s.panel(556, 58, 268, 300)
    c.panel("pB", 556, 58, 268, 300)
    T(s, c, "pB.t", 690, 84, "归并输出(最新 3 条)", size=13, fill=MUTED)
    for i, it in enumerate(["t7", "t6", "t5"]):
        B(s, c, "o%d" % i, 612, 104 + i * 62, 156, 50, it, size=14,
          fill=FILL_TEAL if i == 0 else PAPER)

    T(s, c, "hint", 430, 392,
      "堆里始终只有「每条链当前最新的那一个」;取走一个,就把它所属的链往回退一格补上",
      size=13)
    T(s, c, "cap", 430, 424,
      "所以最多碰 k + 10 个元素 —— 与「关注的人一共发过多少条」完全无关",
      size=13, fill=TEAL_TXT)
    T(s, c, "cap2", 430, 452,
      "漏掉「往回退一格」这步不会报错:信息流会退化成每个关注对象只剩最新一条",
      size=12, fill=WARM_TXT)
    finish(s, c, "05-twitter-kway-merge.svg")


def main():
    for f in (fig1, fig2, fig3, fig4, fig5):
        f()
    print("\nTOTAL layout problems: %d" % PROBLEMS)
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
