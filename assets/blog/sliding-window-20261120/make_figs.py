#!/usr/bin/env python3
"""Generate the five figures for the sliding-window post.

Every label is registered with `Check`, so an off-canvas or colliding text run
fails loudly instead of shipping.  Run:

    python3 assets/blog/sliding-window-20261120/make_figs.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "assets/blog/_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,   # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/sliding-window-20261120"
OUT.mkdir(parents=True, exist_ok=True)

bad = 0


# --------------------------------------------------------------------------
def fig1():
    global bad
    """The window as a frame with two monotone pointers."""
    s = Svg(980, 340)
    c = Check(s)
    vals = ["3", "1", "4", "1", "5", "9", "2", "6", "5", "3", "5"]
    n = len(vals)
    cw, ch, x0, y0 = 64, 54, 60, 116

    s.text(36, 40, "窗口 [left, right):右指针只往前扩,左指针只往前缩",
           size=17, anchor="start", weight="600")
    c.text("title", 36, 40, "窗口 [left, right):右指针只往前扩,左指针只往前缩",
           size=17, anchor="start")
    s.label(36, 66, "两个指针都不回头,所以每个元素最多进窗口一次、出窗口一次")
    c.text("sub", 36, 66, "两个指针都不回头,所以每个元素最多进窗口一次、出窗口一次", size=12,
           anchor="start")

    # the window sits behind the cells
    lw, rw = 3, 9                      # window covers indices [3, 9)
    wx0, wx1 = x0 + lw * cw - 6, x0 + rw * cw + 6
    s.rect(wx0, y0 - 6, wx1 - wx0, ch + 12, fill=FILL_BLUE, stroke=BLUE, sw=1.6, rx=10)
    c.panel("window", wx0, y0 - 6, wx1 - wx0, ch + 12)

    for i, v in enumerate(vals):
        inw = lw <= i < rw
        s.cell(x0 + i * cw, y0, cw, ch, v,
               fill=FILL_BLUE if inw else PAPER,
               stroke=BLUE if inw else INK, size=16)
        c.text(f"v{i}", x0 + i * cw + cw / 2, y0 + ch / 2 + 6, v, size=16)
        s.text(x0 + i * cw + cw / 2, y0 + ch + 20, str(i), size=11, fill=MUTED)
        c.text(f"i{i}", x0 + i * cw + cw / 2, y0 + ch + 20, str(i), size=11)

    s.text(x0 + lw * cw + cw / 2, y0 + ch + 44, "left", size=12, fill=BLUE, weight="600")
    c.text("leftlbl", x0 + lw * cw + cw / 2, y0 + ch + 44, "left", size=12)
    s.text(x0 + (rw - 1) * cw + cw / 2, y0 + ch + 44, "right", size=12, fill=BLUE, weight="600")
    c.text("rightlbl", x0 + (rw - 1) * cw + cw / 2, y0 + ch + 44, "right", size=12)

    s.text(wx0 + 4, y0 - 18, "窗口内的元素:left ≤ i ≤ right−1", size=12,
           fill=BLUE, anchor="start")
    c.text("wlabel", wx0 + 4, y0 - 18, "窗口内的元素:left ≤ i ≤ right−1", size=12, anchor="start")

    # right pointer advances -> expand
    s.arrow(520, 84, 720, 84, stroke=TEAL_TXT)
    c.arrow("ar1", 520, 84, 720, 84)
    s.text(770, 88, "right++ → 扩大", size=13, fill=TEAL_TXT, anchor="start", weight="600")
    c.text("ar1t", 770, 88, "right++ → 扩大", size=13, anchor="start")

    # left pointer advances -> shrink
    s.arrow(720, 300, 520, 300, stroke=WARM_TXT)
    c.arrow("ar2", 520, 300, 720, 300)
    s.text(770, 304, "left++ → 收缩", size=13, fill=WARM_TXT, anchor="start", weight="600")
    c.text("ar2t", 770, 304, "left++ → 收缩", size=13, anchor="start")

    s.label(36, 308, "入窗:right 扫过的元素各一次  ·  出窗:left 扫过的元素各一次  →  合计 O(N)")
    c.text("foot", 36, 308, "入窗:right 扫过的元素各一次  ·  出窗:left 扫过的元素各一次  →  合计 O(N)",
           size=12, anchor="start")
    bad += c.run("01-window-two-pointers")
    s.save(OUT / "01-window-two-pointers.svg")


# --------------------------------------------------------------------------
def fig2():
    global bad
    """Two families of window problems, and which way the loop is written."""
    s = Svg(1000, 400)
    c = Check(s)
    s.text(36, 40, "先问一句:你要的是「最小」还是「最大」——它决定循环体里两件事的先后",
           size=17, anchor="start", weight="600")
    c.text("t", 36, 40, "先问一句:你要的是「最小」还是「最大」——它决定循环体里两件事的先后",
           size=17, anchor="start")

    for i, (bx, head, colour, fill) in enumerate([
            (36, "① 求最小窗口(76 最小覆盖子串)", BLUE, FILL_BLUE),
            (516, "② 求最大窗口(3 无重复最长子串)", TEAL_TXT, FILL_TEAL)]):
        s.panel(bx, 62, 448, 300, fill=CANVAS)
        c.panel(f"p{i}", bx, 62, 448, 300)
        s.rect(bx + 18, 80, 412, 34, fill=fill, stroke=colour, sw=1.4, rx=8)
        s.text(bx + 224, 102, head, size=14, weight="600")
        c.text(f"h{i}", bx + 224, 102, head, size=14)

        if i == 0:
            rows = [
                ("1", "right++ 先扩,直到窗口「满足条件」", TEAL_TXT),
                ("2", "满足后立刻:先更新答案,再 left++", WARM_TXT),
                ("3", "一直缩到「不再满足」为止,回到 1", MUTED),
            ]
            tail = "答案在【收缩过程中】越缩越小"
        else:
            rows = [
                ("1", "right++ 先扩,把新元素并进窗口状态", TEAL_TXT),
                ("2", "只要「违反条件」就 left++ 一直缩", WARM_TXT),
                ("3", "循环退出时窗口必然合法,此刻更新答案", MUTED),
            ]
            tail = "答案在【扩张之后】越扩越大"

        for j, (num, txt, col) in enumerate(rows):
            ry = 146 + j * 52
            s.circle(bx + 40, ry, 13, fill=PAPER, stroke=col, sw=1.6)
            s.text(bx + 40, ry + 5, num, size=13, fill=col, weight="600")
            c.text(f"n{i}{j}", bx + 40, ry + 5, num, size=13)
            s.text(bx + 64, ry + 5, txt, size=13, anchor="start", fill=INK)
            c.text(f"r{i}{j}", bx + 64, ry + 5, txt, size=13, anchor="start")
        s.text(bx + 224, 336, tail, size=13, fill=colour, weight="600")
        c.text(f"tail{i}", bx + 224, 336, tail, size=13)

    s.label(36, 386, "共同点:收缩条件永远是「窗口合法」的取反;差别只在「合法」之后还缩不缩")
    c.text("foot", 36, 386, "共同点:收缩条件永远是「窗口合法」的取反;差别只在「合法」之后还缩不缩",
           size=12, anchor="start")
    bad += c.run("02-expand-or-shrink")
    s.save(OUT / "02-expand-or-shrink.svg")


# --------------------------------------------------------------------------
def fig3():
    global bad
    """LC 76 traced on ADOBECODEBANC / ABC."""
    s = Svg(1120, 452)
    c = Check(s)
    S = "ADOBECODEBANC"
    n = len(S)
    cw, ch, x0 = 40, 38, 96
    s.text(36, 40, "力扣 76 现场:s = ADOBECODEBANC,t = ABC(窗口是 s[left..right] 闭区间)",
           size=17, anchor="start", weight="600")
    c.text("t", 36, 40, "力扣 76 现场:s = ADOBECODEBANC,t = ABC(窗口是 s[left..right] 闭区间)",
           size=17, anchor="start")

    # (row_y, left, right, note1, note2)
    rows = [
        (100, 0, 5, "① 扩:right 扫到 5,窗口 ADOBEC 集齐 ABC",
         "valid=3 → 记 ans=ADOBEC(长 6),再开始缩"),
        (190, 6, 10, "② 缩到缩不动:再缩掉 C 就 valid=2",
         "left 停在 6,窗口 ODEBA 缺 C,ans 不变"),
        (280, 6, 12, "③ 再扩:right 扫到 12,ODEBANC 又集齐",
         "valid=3 → 进入第二轮收缩"),
        (370, 9, 12, "④ 再缩:这一轮里 O→D→E 连缩三步",
         "长 4 的 BANC 刷新答案;再缩掉 B 就 valid=2"),
    ]
    for k, (ry, l, r, note1, note2) in enumerate(rows):
        for i, chx in enumerate(S):
            inw = l <= i <= r
            s.cell(x0 + i * cw, ry, cw, ch, chx,
                   fill=FILL_BLUE if inw else PAPER,
                   stroke=BLUE if inw else LINE, size=15)
            c.text(f"c{k}{i}", x0 + i * cw + cw / 2, ry + ch / 2 + 6, chx, size=15)
        s.text(36, ry + ch / 2 + 6, f"第 {k + 1} 行", size=12, fill=MUTED, anchor="start")
        c.text(f"rl{k}", 36, ry + ch / 2 + 6, f"第 {k + 1} 行", size=12, anchor="start")
        # left / right markers under the window edges
        s.text(x0 + l * cw + cw / 2, ry + ch + 18, "↑left", size=11, fill=WARM_TXT)
        c.text(f"lm{k}", x0 + l * cw + cw / 2, ry + ch + 18, "↑left", size=11)
        s.text(x0 + r * cw + cw / 2, ry + ch + 18, "↑right", size=11, fill=TEAL_TXT)
        c.text(f"rm{k}", x0 + r * cw + cw / 2, ry + ch + 18, "↑right", size=11)
        for j, note in enumerate((note1, note2)):
            s.text(700, ry + 18 + j * 22, note, size=13, anchor="start",
                   fill=INK if j == 0 else MUTED)
            c.text(f"nt{k}{j}", 700, ry + 18 + j * 22, note, size=13, anchor="start")

    s.label(36, 440, "④ 之前的三次收缩都发生在同一个内层 while 里:全程 right 只走 0→12,left 只走 0→10")
    c.text("foot", 36, 440, "④ 之前的三次收缩都发生在同一个内层 while 里:全程 right 只走 0→12,left 只走 0→10",
           size=12, anchor="start")
    bad += c.run("03-min-window-walkthrough")
    s.save(OUT / "03-min-window-walkthrough.svg")


# --------------------------------------------------------------------------
def fig4():
    global bad
    """Rabin-Karp: slide the hash instead of the characters."""
    s = Svg(1000, 420)
    c = Check(s)
    B, M = 131, 1000000007
    s.text(36, 40, "Rabin-Karp 的全部秘密:窗口滑动一位,哈希只做「一减一乘一加」",
           size=17, anchor="start", weight="600")
    c.text("t", 36, 40, "Rabin-Karp 的全部秘密:窗口滑动一位,哈希只做「一减一乘一加」",
           size=17, anchor="start")

    S = "abcde"
    cw, ch, x0, y0 = 52, 46, 60, 116
    steps = ["① 先算第一个窗口的哈希(整个窗口扫一遍,只有这一次是 O(L))",
             "② 窗口右移一位:去掉 a,乘 B,补上 d —— O(1)",
             "③ 再滑一位:去掉 b,补上 e —— 依然是 O(1)"]
    for k, (l, r) in enumerate([(0, 2), (1, 3), (2, 4)]):
        ry = y0 + k * 78
        s.label(x0, ry - 14, steps[k], size=12)
        c.text(f"s{k}", x0, ry - 14, steps[k], size=12, anchor="start")
        for i, chx in enumerate(S):
            inw = l <= i <= r
            s.cell(x0 + i * cw, ry, cw, ch, chx,
                   fill=FILL_WARM if inw else PAPER,
                   stroke=WARM_TXT if inw else LINE, size=15)
            c.text(f"c{k}{i}", x0 + i * cw + cw / 2, ry + ch / 2 + 6, chx, size=15)
        lw = ord(S[l]) * B ** 2 + ord(S[l + 1]) * B + ord(S[l + 2])
        h = lw % M
        s.text(x0 + 5 * cw + 20, ry + ch / 2 + 6,
               f"h({S[l:l + 3]}) = {chat(S[l:l + 3])} = {h}", size=13,
               anchor="start", fill=WARM_TXT)
        c.text(f"h{k}", x0 + 5 * cw + 20, ry + ch / 2 + 6,
               f"h({S[l:l + 3]}) = {chat(S[l:l + 3])} = {h}", size=13, anchor="start")

    box_x, box_y = 60, 386
    s.rect(box_x, box_y - 26, 880, 40, fill=FILL_TEAL, stroke=TEAL_TXT, sw=1.4, rx=8)
    s.text(box_x + 440, box_y, "h(下一位) = ( h(当前) − 离开字符 × B^(L−1) ) × B + 进入字符   (再对 M 取模)",
           size=13, weight="600")
    c.text("f", box_x + 440, box_y,
           "h(下一位) = ( h(当前) − 离开字符 × B^(L−1) ) × B + 进入字符   (再对 M 取模)", size=13)
    bad += c.run("04-rolling-hash")
    s.save(OUT / "04-rolling-hash.svg")


def chat(sub):
    """Render h(abc) as ord('a')*131^2 + ... without exploding the label."""
    return " + ".join(f"{ord(ch)}·131^{2 - i}" if i < 2 else f"{ord(ch)}"
                      for i, ch in enumerate(sub))


# --------------------------------------------------------------------------
def fig5():
    global bad
    """Same hash, different string: why the verify step is not optional."""
    s = Svg(1000, 330)
    c = Check(s)
    s.text(36, 40, "哈希相等 ≠ 子串相等:命中的时候必须逐字符回验一次",
           size=17, anchor="start", weight="600")
    c.text("t", 36, 40, "哈希相等 ≠ 子串相等:命中的时候必须逐字符回验一次",
           size=17, anchor="start")

    for i, (bx, lbl, sub, h, ok) in enumerate([
            (36, "真命中", "abc", "h = 97·131²+98·131+99", True),
            (516, "假命中(碰撞)", "xqz", "h 恰好相同", False)]):
        s.panel(bx, 62, 448, 190, fill=CANVAS)
        c.panel(f"p{i}", bx, 62, 448, 190)
        s.text(bx + 224, 88, lbl, size=14, weight="600",
               fill=TEAL_TXT if ok else WARM_TXT)
        c.text(f"l{i}", bx + 224, 88, lbl, size=14)
        for j, chx in enumerate(sub):
            s.cell(bx + 120 + j * 52, 106, 52, 44, chx,
                   fill=FILL_TEAL if ok else FILL_WARM,
                   stroke=TEAL_TXT if ok else WARM_TXT, size=15)
            c.text(f"c{i}{j}", bx + 120 + j * 52 + 26, 106 + 28, chx, size=15)
        s.text(bx + 224, 176, h, size=12, fill=MUTED)
        c.text(f"h{i}", bx + 224, 176, h, size=12)
        verdict = ("逐字符比对 → 通过,返回下标" if ok
                   else "逐字符比对 → 失败,继续往后滑")
        s.text(bx + 224, 214, verdict, size=13,
               fill=TEAL_TXT if ok else WARM_TXT, weight="600")
        c.text(f"v{i}", bx + 224, 214, verdict, size=13)

    s.label(36, 288, "期望 O(n+m):哈希把「几乎每一步都要比对」变成「几乎不用比对」;最坏 O(nm) 来自蓄意构造的碰撞")
    c.text("f1", 36, 288, "期望 O(n+m):哈希把「几乎每一步都要比对」变成「几乎不用比对」;最坏 O(nm) 来自蓄意构造的碰撞",
           size=12, anchor="start")
    s.label(36, 310, "实用做法:随机化底数 B,或者像力扣 187 那样用 4 进制 + 位运算做到无模数、无碰撞")
    c.text("f2", 36, 310, "实用做法:随机化底数 B,或者像力扣 187 那样用 4 进制 + 位运算做到无模数、无碰撞",
           size=12, anchor="start")
    bad += c.run("05-hash-collision")
    s.save(OUT / "05-hash-collision.svg")


fig1()
fig2()
fig3()
fig4()
fig5()

# `Check` only reasons about geometry, so a raw '<' or '&' in a label would
# still ship a file that no SVG parser (and therefore no browser) accepts.
# Parse every file back before declaring success.
import xml.dom.minidom                                                    # noqa: E402

for svg_file in sorted(OUT.glob("*.svg")):
    try:
        xml.dom.minidom.parse(str(svg_file))
    except Exception as exc:                                             # noqa: BLE001
        print(f"  !! {svg_file.name} is not well-formed XML: {exc}")
        bad += 1
    else:
        print(f"  ok {svg_file.name}: parses as XML")

print(f"\n  layout problems: {bad}")
sys.exit(1 if bad else 0)
