#!/usr/bin/env python3
"""Figures for the binary-tree-advanced post (2026-11-22).

Six SVGs into assets/img/binary-tree-advanced-20261122/.  Run from the repo root:

    python3 assets/blog/binary-tree-advanced-20261122/make_figures.py

Same discipline as the other posts: every label is registered with svgkit's
`Check` (so a text collision is a hard failure, not something a human has to
notice), every generated file is parsed back as XML, and the PNGs still have to
be looked at by eye afterwards.
"""
import sys
import xml.dom.minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "img" / "binary-tree-advanced-20261122"

sys.path.insert(0, str(HERE.parent / "_tools"))
from svgkit import (  # noqa: E402
    INK, MUTED, BLUE, LINE, PAPER, CANVAS,
    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
    WARM_TXT, TEAL_TXT,
    Svg, Check,
)

bad = 0
files = []


def T(s, c, name, x, y, t, size=14, fill=INK, anchor="middle", weight="400"):
    """Draw a text run and register its hitbox in one call.

    svgkit's Check only sees what is registered, so pairing the two here is the
    only way to be sure nothing is drawn invisibly to the checks.
    """
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)


def cell(s, c, name, x, y, w, h, label, fill=INK, tc=INK, size=13):
    s.cell(x, y, w, h, "", fill=fill, stroke=INK)
    T(s, c, name, x + w / 2, y + h / 2 + size * 0.36, label, size=size, fill=tc,
      weight="600")


def tree(s, c, nodes, edges, r=18, fill=FILL_BLUE, tag="t"):
    """nodes: {key: (x, y, label)}; edges: [(keyA, keyB), ...]."""
    for a, b in edges:
        x1, y1, _ = nodes[a]
        x2, y2, _ = nodes[b]
        s.line(x1, y1 + r, x2, y2 - r, stroke=MUTED, sw=1.3)
    for k, (x, y, lab) in nodes.items():
        s.circle(x, y, r, fill=fill, stroke=INK, sw=1.4)
        T(s, c, f"{tag}{k}", x, y + 5, lab, size=14, weight="600")


def finish(s, c, name, w, h):
    global bad
    path = OUT / name
    bad += c.run(name)
    s.save(path)
    files.append(path)


# ---------------------------------------------------------------------------
# 1. how preorder + inorder pin down a tree (LC 105)
# ---------------------------------------------------------------------------
def fig1():
    s = Svg(1080, 470)
    c = Check(s)
    T(s, c, "a1", 44, 36, "力扣 105:前序 + 中序 → 唯一的树", size=16,
      anchor="start", weight="600")

    warm, blue, teal = FILL_WARM, FILL_BLUE, FILL_TEAL
    T(s, c, "a2", 44, 92, "前序", size=13, anchor="start", weight="600")
    pre = [("3", warm, WARM_TXT), ("9", blue, BLUE), ("20", teal, TEAL_TXT),
           ("15", teal, TEAL_TXT), ("7", teal, TEAL_TXT)]
    for i, (lab, f, tc) in enumerate(pre):
        x = 120 + i * 56
        cell(s, c, f"a3{i}", x, 70, 56, 34, lab, fill=f, tc=tc)
        T(s, c, f"a4{i}", x + 28, 118, str(i), size=10, fill=MUTED)

    T(s, c, "a5", 44, 174, "中序", size=13, anchor="start", weight="600")
    ino = [("9", blue, BLUE), ("3", warm, WARM_TXT), ("15", teal, TEAL_TXT),
           ("20", teal, TEAL_TXT), ("7", teal, TEAL_TXT)]
    for i, (lab, f, tc) in enumerate(ino):
        x = 120 + i * 56
        cell(s, c, f"a6{i}", x, 152, 56, 34, lab, fill=f, tc=tc)
        T(s, c, f"a7{i}", x + 28, 200, str(i), size=10, fill=MUTED)

    s.panel(560, 56, 490, 250)
    c.panel("a8", 560, 56, 490, 250)
    T(s, c, "a9", 800, 84, "构造出来的树", size=12, fill=MUTED)
    nodes = {"r": (800, 122, "3"), "l": (690, 202, "9"), "rr": (910, 202, "20"),
             "rl": (860, 276, "15"), "rrr": (960, 276, "7")}
    edges = [("r", "l"), ("r", "rr"), ("rr", "rl"), ("rr", "rrr")]
    tree(s, c, nodes, edges, r=18, tag="a1n")

    s.panel(44, 330, 992, 112)
    c.panel("a10", 44, 330, 992, 112)
    T(s, c, "a11", 64, 362,
      "根 = pre[0] = 3;index = 3 在中序里的下标 = 1;leftSize = index − inStart = 1",
      size=13, anchor="start")
    T(s, c, "a12", 64, 392,
      "左子树:pre[1..1] × in[0..0]      右子树:pre[2..4] × in[2..4]",
      size=13, anchor="start")
    T(s, c, "a13", 64, 422,
      "前序只告诉你「左子树有几个」,中序告诉你「左子树是哪几个」——两者合起来才有唯一解",
      size=13, anchor="start", fill=BLUE)
    finish(s, c, "01-build-from-orders.svg", 1080, 470)


# ---------------------------------------------------------------------------
# 2. uniqueness of a serialization (LC 297)
# ---------------------------------------------------------------------------
def fig2():
    s = Svg(1080, 430)
    c = Check(s)
    T(s, c, "b1", 44, 36, "序列化要想还原得回来,就必须把空位也写进去", size=16,
      anchor="start", weight="600")

    specs = [
        (30, "前序,不写空位", "→ 不唯一 ✗", MUTED),
        (375, "前序,写上空位 #", "→ 唯一 ✓", TEAL_TXT),
        (720, "中序,写上空位 #", "→ 仍不唯一 ✗", WARM_TXT),
    ]
    for i, (x, title, sub, col) in enumerate(specs):
        s.panel(x, 56, 330, 330)
        c.panel(f"b2{i}", x, 56, 330, 330)
        T(s, c, f"b3{i}", x + 165, 86, title, size=13, weight="600")
        T(s, c, f"b4{i}", x + 165, 110, sub, size=12, fill=col, weight="600")

    # panel 1: a left-chain and a right-chain, both with preorder 1 2 3 4 5
    for k in range(5):
        s.circle(140 - k * 16, 160 + k * 34, 13, fill=FILL_BLUE, stroke=INK, sw=1.2)
        T(s, c, f"b5{k}", 140 - k * 16, 165 + k * 34, str(k + 1), size=12)
        s.circle(250 + k * 16, 160 + k * 34, 13, fill=FILL_WARM, stroke=INK, sw=1.2)
        T(s, c, f"b6{k}", 250 + k * 16, 165 + k * 34, str(k + 1), size=12)
        if k < 4:
            s.line(140 - k * 16 - 8, 160 + k * 34 + 10,
                   140 - (k + 1) * 16 + 8, 160 + (k + 1) * 34 - 10,
                   stroke=MUTED, sw=1.2)
            s.line(250 + k * 16 + 8, 160 + k * 34 + 10,
                   250 + (k + 1) * 16 - 8, 160 + (k + 1) * 34 - 10,
                   stroke=MUTED, sw=1.2)
    T(s, c, "b7", 108, 340, "左链", size=11, fill=MUTED)
    T(s, c, "b8", 282, 340, "右链", size=11, fill=MUTED)
    T(s, c, "b9", 195, 368, "pre = 1 2 3 4 5", size=12, weight="600")

    # panel 2: the one tree whose preorder-with-nulls is 1,2,#,4,#,#,3,#,#
    nodes = {"r": (540, 152, "1"), "l": (470, 218, "2"), "rr": (610, 218, "3"),
             "lr": (510, 284, "4")}
    tree(s, c, nodes, [("r", "l"), ("r", "rr"), ("l", "lr")], r=16, tag="b1n")
    T(s, c, "b10", 540, 340, "1,2,#,4,#,#,3,#,#", size=12, weight="600")
    T(s, c, "b11", 540, 368, "空位各占一位", size=11, fill=MUTED)

    # panel 3: left-child-only vs right-child-only, identical inorder-with-nulls
    s.line(790, 168 + 13, 740, 240 - 13, stroke=MUTED, sw=1.3)
    s.circle(790, 168, 16, fill=FILL_BLUE, stroke=INK, sw=1.4)
    T(s, c, "b12", 790, 173, "1", size=14, weight="600")
    s.circle(740, 240, 16, fill=FILL_BLUE, stroke=INK, sw=1.4)
    T(s, c, "b13", 740, 245, "1", size=14, weight="600")
    s.line(950, 168 + 13, 1000, 240 - 13, stroke=MUTED, sw=1.3)
    s.circle(950, 168, 16, fill=FILL_WARM, stroke=INK, sw=1.4)
    T(s, c, "b14", 950, 173, "1", size=14, weight="600")
    s.circle(1000, 240, 16, fill=FILL_WARM, stroke=INK, sw=1.4)
    T(s, c, "b15", 1000, 245, "1", size=14, weight="600")
    T(s, c, "b16", 885, 340, "#,1,#,1,#  两棵都是", size=12, weight="600")
    T(s, c, "b17", 885, 368, "中序定不了根的位置", size=11, fill=MUTED)
    finish(s, c, "02-serialize-unique.svg", 1080, 430)


# ---------------------------------------------------------------------------
# 3. the three LCA situations (LC 236)
# ---------------------------------------------------------------------------
def fig3():
    s = Svg(1080, 430)
    c = Check(s)
    T(s, c, "c1", 44, 36, "力扣 236:最近公共祖先的三种情形", size=16,
      anchor="start", weight="600")

    nodes = {"r": (300, 96, "3"), "p": (185, 176, "5"), "q": (415, 176, "1"),
             "a": (125, 256, "6"), "b": (245, 256, "2"), "d": (355, 256, "0"),
             "e": (475, 256, "8"), "f": (210, 336, "7"), "g": (280, 336, "4")}
    edges = [("r", "p"), ("r", "q"), ("p", "a"), ("p", "b"), ("q", "d"),
             ("q", "e"), ("b", "f"), ("b", "g")]
    for a, b in edges:
        x1, y1, _ = nodes[a]
        x2, y2, _ = nodes[b]
        s.line(x1, y1 + 18, x2, y2 - 18, stroke=MUTED, sw=1.3)
    fills = {"r": FILL_WARM, "p": FILL_BLUE, "q": FILL_BLUE, "g": FILL_TEAL}
    for k, (x, y, lab) in nodes.items():
        s.circle(x, y, 18, fill=fills.get(k, FILL_GREY), stroke=INK, sw=1.4)
        T(s, c, f"c2{k}", x, y + 5, lab, size=14, weight="600")
    T(s, c, "c3", 300, 386, "力扣 236 的样例树", size=11, fill=MUTED)

    rows = [
        (96, "查询 ①  p=5, q=1", INK, "600"),
        (124, "分居 3 的左右两侧", MUTED, "400"),
        (150, "→ 答案就是 3", BLUE, "600"),
        (206, "查询 ②  p=5, q=4", INK, "600"),
        (234, "两个都在 3 的左子树里", MUTED, "400"),
        (260, "→ 答案在左子树的返回值里,即 5", BLUE, "600"),
        (316, "查询 ③  p=3, q=5", INK, "600"),
        (344, "root 自己就是 p", MUTED, "400"),
        (370, "→ 直接返回 root", BLUE, "600"),
    ]
    for i, (y, t, col, wt) in enumerate(rows):
        T(s, c, f"c4{i}", 560, y, t, size=13, anchor="start", fill=col, weight=wt)

    T(s, c, "c5", 44, 414,
      "后序位置最强:只有左右子树的返回值都拿到了,才知道 p、q 是同侧还是分居两侧",
      size=12, anchor="start", fill=MUTED)
    finish(s, c, "03-lca-cases.svg", 1080, 430)


# ---------------------------------------------------------------------------
# 4. why counting a complete tree's nodes costs O(log^2 N) (LC 222)
# ---------------------------------------------------------------------------
def fig4():
    s = Svg(1080, 500)
    c = Check(s)
    T(s, c, "d1", 44, 36, "力扣 222:完全二叉树数节点,为什么能到 O(log²N)", size=16,
      anchor="start", weight="600")

    panels = [(30, "左右高度相等 → 整棵是满的"),
              (375, "高度差 1:左子树满"),
              (720, "高度差 1:右子树满")]
    for i, (x, title) in enumerate(panels):
        s.panel(x, 56, 330, 366)
        c.panel(f"d2{i}", x, 56, 330, 366)
        T(s, c, f"d3{i}", x + 165, 86, title, size=13, weight="600")

    # panel 1: perfect tree, 7 nodes
    p1 = {"r": (195, 150, "1"), "a": (145, 220, "2"), "b": (245, 220, "3"),
          "c": (120, 290, "4"), "d": (170, 290, "5"), "e": (220, 290, "6"),
          "f": (270, 290, "7")}
    tree(s, c, p1, [("r", "a"), ("r", "b"), ("a", "c"), ("a", "d"),
                    ("b", "e"), ("b", "f")], r=16, tag="d1n")
    T(s, c, "d4", 195, 360, "2³ − 1 = 7", size=13, weight="600", fill=BLUE)
    T(s, c, "d5", 195, 388, "量两次高度就结束,O(h)", size=11, fill=MUTED)

    # panel 2: 6 nodes; left subtree (2,4,5) is perfect, right (3,6) is not
    p2 = {"r": (540, 150, "1"), "a": (490, 220, "2"), "b": (590, 220, "3"),
          "c": (465, 290, "4"), "d": (515, 290, "5"), "e": (565, 290, "6")}
    for a, b in [("r", "a"), ("r", "b"), ("a", "c"), ("a", "d"), ("b", "e")]:
        x1, y1, _ = p2[a]
        x2, y2, _ = p2[b]
        s.line(x1, y1 + 16, x2, y2 - 16, stroke=MUTED, sw=1.3)
    for k, (x, y, lab) in p2.items():
        f = FILL_BLUE if k in ("a", "c", "d") else FILL_WARM
        s.circle(x, y, 16, fill=f, stroke=INK, sw=1.4)
        T(s, c, f"d6{k}", x, y + 5, lab, size=14, weight="600")
    T(s, c, "d7", 540, 360, "左子树满:2² − 1 = 3", size=12, weight="600", fill=BLUE)
    T(s, c, "d8", 540, 388, "1 + 3 + 递归数右子树", size=11, fill=MUTED)

    # panel 3: 4 nodes; RIGHT subtree is the perfect one -> "always the left" is wrong
    p3 = {"r": (885, 150, "1"), "a": (835, 220, "2"), "b": (935, 220, "3"),
          "c": (810, 290, "4")}
    for a, b in [("r", "a"), ("r", "b"), ("a", "c")]:
        x1, y1, _ = p3[a]
        x2, y2, _ = p3[b]
        s.line(x1, y1 + 16, x2, y2 - 16, stroke=MUTED, sw=1.3)
    for k, (x, y, lab) in p3.items():
        f = FILL_TEAL if k == "b" else FILL_WARM
        s.circle(x, y, 16, fill=f, stroke=INK, sw=1.4)
        T(s, c, f"d9{k}", x, y + 5, lab, size=14, weight="600")
    T(s, c, "d10", 885, 360, "右子树才是满的:1", size=12, weight="600",
      fill=TEAL_TXT)
    T(s, c, "d11", 885, 388, "左子树不满 → 递归左边", size=11, fill=MUTED)

    s.panel(30, 438, 1020, 46)
    c.panel("d12", 30, 438, 1020, 46)
    T(s, c, "d13", 50, 466,
      "每次只往一侧深入,而量一次高度是 O(h) → 总代价 h + (h−1) + … + 1 = O(h²),"
      "又因 h = O(log N),所以是 O(log²N)",
      size=12, anchor="start", fill=BLUE)
    finish(s, c, "04-count-complete.svg", 1080, 500)


# ---------------------------------------------------------------------------
# 5. validating a BST: comparing with your own children is not enough (LC 98)
# ---------------------------------------------------------------------------
def fig5():
    s = Svg(1080, 440)
    c = Check(s)
    T(s, c, "e1", 44, 36, "力扣 98:只和直接孩子比,会把这棵树判成合法", size=16,
      anchor="start", weight="600")

    s.panel(30, 56, 490, 320)
    c.panel("e2", 30, 56, 490, 320)
    nodes = {"r": (265, 140, "10"), "l": (170, 225, "5"), "rr": (360, 225, "15"),
             "rl": (310, 310, "6"), "rrr": (410, 310, "20")}
    edges = [("r", "l"), ("r", "rr"), ("rr", "rl"), ("rr", "rrr")]
    tree(s, c, nodes, edges, r=18, tag="e3")
    T(s, c, "e4", 275, 348, "直接孩子两两比:5<10、15>10、6<15、20>15",
      size=12, fill=WARM_TXT, weight="600")
    T(s, c, "e4b", 275, 374, "四项全过 → 误判成合法 BST ✗",
      size=12, fill=WARM_TXT, weight="600")

    s.panel(560, 56, 490, 320)
    c.panel("e5", 560, 56, 490, 320)
    T(s, c, "e6", 600, 100, "每个节点真正要满足的区间", size=13, anchor="start",
      weight="600")
    rows = [
        "10 ← (−∞, +∞)   ✓",
        "5 ← (−∞, 10)    ✓",
        "15 ← (10, +∞)   ✓",
        "6 ← (10, 15)    ✗  越界!",
        "20 ← (15, +∞)   ✓",
    ]
    for i, t in enumerate(rows):
        col = WARM_TXT if i == 3 else INK
        wt = "600" if i == 3 else "400"
        T(s, c, f"e7{i}", 600, 142 + i * 34, t, size=13, anchor="start",
          fill=col, weight=wt)

    T(s, c, "e8", 44, 410,
      "区间是「参数」,只能自顶向下传:往左走就把上界收紧成当前值,往右走就把下界收紧成当前值",
      size=12, anchor="start", fill=BLUE)
    finish(s, c, "05-bst-constraint.svg", 1080, 440)


# ---------------------------------------------------------------------------
# 6. tree DP: return a pair, not a single number (LC 337)
# ---------------------------------------------------------------------------
def fig6():
    s = Svg(1080, 460)
    c = Check(s)
    T(s, c, "f1", 44, 36, "力扣 337:每个节点返回 (不偷, 偷) 两个数", size=16,
      anchor="start", weight="600")

    nodes = {"r": (330, 120, "3"), "l": (215, 210, "2"), "rr": (445, 210, "3"),
             "lr": (290, 300, "3"), "rrr": (520, 300, "1")}
    edges = [("r", "l"), ("r", "rr"), ("l", "lr"), ("rr", "rrr")]
    for a, b in edges:
        x1, y1, _ = nodes[a]
        x2, y2, _ = nodes[b]
        s.line(x1, y1 + 20, x2, y2 - 20, stroke=MUTED, sw=1.3)
    pairs = {"r": "(6, 7)", "l": "(3, 2)", "rr": "(1, 3)", "lr": "(0, 3)",
             "rrr": "(0, 1)"}
    for k, (x, y, lab) in nodes.items():
        f = FILL_TEAL if k in ("r", "lr", "rrr") else FILL_GREY
        s.circle(x, y, 20, fill=f, stroke=INK, sw=1.4)
        T(s, c, f"f2{k}", x, y + 5, lab, size=14, weight="600")
        T(s, c, f"f3{k}", x + 32, y + 5, pairs[k], size=12, anchor="start",
          fill=TEAL_TXT, weight="600")
    T(s, c, "f4", 330, 372, "力扣 337 样例:答案是 7(选 3、3、1 三个节点)",
      size=12, fill=MUTED)

    rows = [
        (100, "叶子:(不偷=0,偷=自己的值)", INK, "400", 13),
        (140, "内部节点", INK, "600", 13),
        (168, "偷 = val + 左.不偷 + 右.不偷", BLUE, "400", 13),
        (196, "不偷 = max(左两值) + max(右两值)", BLUE, "400", 13),
        (240, "根:(不偷=6, 偷=7)", INK, "600", 13),
        (268, "7 = 3 + 3(左.不偷) + 1(右.不偷)", TEAL_TXT, "400", 12),
        (296, "6 = max(3,2) + max(1,3)", TEAL_TXT, "400", 12),
    ]
    for i, (y, t, col, wt, sz) in enumerate(rows):
        T(s, c, f"f5{i}", 620, y, t, size=sz, anchor="start", fill=col, weight=wt)

    T(s, c, "f6", 44, 424,
      "一个返回值不够用时,就返回一个元组:子节点需要把「偷自己」和「不偷自己」两种答案都交给父节点",
      size=12, anchor="start", fill=BLUE)
    finish(s, c, "06-tree-dp-rob.svg", 1080, 460)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()

    problems = 0
    for p in files:
        try:
            xml.dom.minidom.parse(str(p))
        except Exception as exc:                      # noqa: BLE001
            print(f"  !! {p.name} is not well-formed XML: {exc}")
            problems += 1
        if "<text></text>" in p.read_text(encoding="utf-8"):
            print(f"  !! {p.name} has an empty <text> node")
            problems += 1

    print(f"  layout problems: {bad}")
    print(f"  xml problems   : {problems}")
    return 1 if (bad or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
