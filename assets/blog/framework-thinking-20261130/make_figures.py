#!/usr/bin/env python3
"""Diagrams for the framework-thinking post.

Four figures, each answering one question the prose raises:

  01  how one skeleton covers four structures (the post's central claim)
  02  the storage trade-off: contiguous vs. scattered
  03  the four basic operations, and why LRU needs two structures at once
  04  the two tree thinking modes, side by side on one tree

Every label is registered with Check() so label/arrow collisions are caught
mechanically rather than by eye.  Labels go through svgkit.text(), which
XML-escapes by default -- important here because several labels contain `<`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # assets/blog/<slug>/
BLOG = HERE.parent                               # assets/blog/
OUT = BLOG.parent / "img" / "framework-thinking-20261130"
sys.path.insert(0, str(BLOG / "_tools"))

from svgkit import (BLUE, CANVAS, Check, FILL_BLUE, FILL_GREY, FILL_TEAL,  # noqa: E402
                    FILL_WARM, INK, LINE, MUTED, PAPER, Svg, TEAL_TXT,
                    WARM_TXT)

OUT.mkdir(parents=True, exist_ok=True)


def save(s: Svg, c: Check, name: str) -> None:
    bad = c.run(name)
    s.save(str(OUT / f"{name}.svg"))
    if bad:
        sys.exit(f"{name}: {bad} collision(s)")


# ---------------------------------------------------------------- figure 01
def fig01() -> None:
    W, H = 1180, 620
    s = Svg(W, H)
    c = Check(s)
    s.rect(0, 0, W, H, fill=CANVAS, stroke=CANVAS, rx=0)
    s.text(W / 2, 46, "一套骨架,四种结构:差别只在「下一个是谁」", size=20, weight="600")
    c.text("t", W / 2, 46, "一套骨架,四种结构:差别只在「下一个是谁」", size=20)
    s.text(W / 2, 74, "起点 + next_of + 是否查环 —— 循环体完全一样",
           size=13, fill=MUTED)
    c.text("t2", W / 2, 74, "起点 + next_of + 是否查环 —— 循环体完全一样", size=13)

    cards = [
        ("数组", "下标 + 1", "不需要", FILL_BLUE, BLUE),
        ("链表", "p.next", "不需要(但可有环)", FILL_TEAL, TEAL_TXT),
        ("二叉树", "left / right", "不需要", FILL_WARM, WARM_TXT),
        ("图", "邻接表的每个邻居", "必须", FILL_GREY, MUTED),
    ]
    x0, y0, cw, ch, gap = 48, 120, 262, 150, 22
    for i, (name, nxt, cyc, fill, stroke) in enumerate(cards):
        x = x0 + i * (cw + gap)
        s.rect(x, y0, cw, ch, fill=fill, stroke=stroke, sw=1.6)
        s.text(x + cw / 2, y0 + 38, name, size=19, weight="600", fill=stroke)
        c.text(f"n{i}", x + cw / 2, y0 + 38, name, size=19)
        s.text(x + cw / 2, y0 + 74, "next_of:", size=11, fill=MUTED)
        c.text(f"k{i}", x + cw / 2, y0 + 74, "next_of:", size=11)
        s.text(x + cw / 2, y0 + 100, nxt, size=14)
        c.text(f"v{i}", x + cw / 2, y0 + 100, nxt, size=14)
        s.line(x + 30, y0 + 118, x + cw - 30, y0 + 118, stroke=stroke, sw=1, dash="3 3")
        tag = "不查环" if cyc == "不需要" else cyc
        col = MUTED if cyc != "必须" else "#b5762a"
        s.text(x + cw / 2, y0 + 138, tag, size=12, fill=col,
               weight="600" if cyc == "必须" else "400")
        c.text(f"c{i}", x + cw / 2, y0 + 138, tag, size=12)
        if i < 3:
            s.arrow(x + cw + 3, y0 + ch / 2, x + cw + gap - 3, y0 + ch / 2,
                    stroke=MUTED, sw=1.4)

    # the shared skeleton, written out once
    s.panel(48, 316, W - 96, 196)
    c.panel("skel", 48, 316, W - 96, 196)
    s.text(72, 350, "同一个骨架", size=15, weight="600", anchor="start")
    c.text("skelh", 72, 350, "同一个骨架", size=15, anchor="start")
    lines = [
        (0, "while stack:"),
        (4, "cur = stack.pop()"),
        (4, "if should_skip(cur): continue"),
        (4, "visit(cur)"),
        (4, "for nxt in next_of(cur):"),
        (8, "if nxt not in seen:"),
        (12, "seen.add(nxt); stack.append(nxt)"),
    ]
    # Indentation is the whole point of this figure, so draw the indent as
    # spaces that Check() can measure rather than as a separate x offset --
    # otherwise the collision boxes would ignore the leading whitespace.
    for i, (indent, ln) in enumerate(lines):
        y = 386 + i * 21
        shown = " " * indent + ln
        s.text(76, y, shown, size=13, anchor="start",
               fill=INK if "seen.add" not in ln else "#b5762a")
        c.text(f"sl{i}", 76, y, shown, size=13, anchor="start")
    s.text(W - 76, 560 - 96, "seen.add 必须在「入栈前」", size=13,
           anchor="end", fill="#b5762a", weight="600")
    c.text("warn", W - 76 - 130, 464, "seen.add 必须在「入栈前」", size=13)

    s.text(W / 2, 578, "骨架的价值是理解层面的:知道它们同构,技巧才能跨结构迁移",
           size=12, fill=MUTED)
    c.text("foot", W / 2, 578, "骨架的价值是理解层面的:知道它们同构,技巧才能跨结构迁移", size=12)
    save(s, c, "01-one-skeleton-four-structures")


# ---------------------------------------------------------------- figure 02
def fig02() -> None:
    W, H = 1100, 520
    s = Svg(W, H)
    c = Check(s)
    s.rect(0, 0, W, H, fill=CANVAS, stroke=CANVAS, rx=0)
    s.text(W / 2, 44, "顺序存储 vs 链式存储:能力是取舍,不是优劣", size=20, weight="600")
    c.text("t", W / 2, 44, "顺序存储 vs 链式存储:能力是取舍,不是优劣", size=20)

    # left: contiguous
    s.panel(40, 82, 480, 360)
    c.panel("pL", 40, 82, 480, 360)
    s.text(280, 118, "顺序存储(数组)", size=16, weight="600", fill=BLUE)
    c.text("lh", 280, 118, "顺序存储(数组)", size=16)
    s.text(280, 142, "地址 = 起始 + 下标 × 元素大小", size=11, fill=MUTED)
    c.text("lh2", 280, 142, "地址 = 起始 + 下标 × 元素大小", size=11)
    for i in range(5):
        x = 68 + i * 88
        s.cell(x, 176, 80, 56, str(i), fill=FILL_BLUE if i == 2 else PAPER, stroke=BLUE)
        c.text(f"la{i}", x + 40, 208, str(i), size=15)
        s.text(x + 40, 248, f"+{i * 4}", size=10, fill=MUTED)
        c.text(f"lo{i}", x + 40, 248, f"+{i * 4}", size=10)
    s.text(280, 274, "一块连续内存,下标直接算出地址", size=12, fill=MUTED)
    c.text("lc", 280, 274, "一块连续内存,下标直接算出地址", size=12)
    s.text(68, 314, "✓ 随机访问 O(1)", size=13, anchor="start", fill=TEAL_TXT, weight="600")
    c.text("l1", 68 + 70, 314, "✓ 随机访问 O(1)", size=13, anchor="start")
    s.text(68, 344, "✗ 中间插入要搬数据 O(n)", size=13, anchor="start", fill="#b5762a")
    c.text("l2", 68 + 86, 344, "✗ 中间插入要搬数据 O(n)", size=13, anchor="start")
    s.text(68, 374, "✓ 尾部追加均摊 O(1)", size=13, anchor="start", fill=TEAL_TXT)
    c.text("l3", 68 + 74, 374, "✓ 尾部追加均摊 O(1)", size=13, anchor="start")
    s.text(68, 404, "✗ 扩容时要整块搬迁", size=13, anchor="start", fill="#b5762a")
    c.text("l4", 68 + 68, 404, "✗ 扩容时要整块搬迁", size=13, anchor="start")

    # right: scattered
    s.panel(576, 82, 484, 360)
    c.panel("pR", 576, 82, 484, 360)
    s.text(818, 118, "链式存储(链表)", size=16, weight="600", fill=TEAL_TXT)
    c.text("rh", 818, 118, "链式存储(链表)", size=16)
    s.text(818, 142, "节点分散,靠指针串起来", size=11, fill=MUTED)
    c.text("rh2", 818, 142, "节点分散,靠指针串起来", size=11)
    for i in range(3):
        x = 610 + i * 150
        y = 190 + (i % 2) * 60
        s.rect(x, y, 108, 46, fill=FILL_TEAL, stroke=TEAL_TXT)
        s.text(x + 34, y + 30, str(i), size=15)
        c.text(f"rv{i}", x + 34, y + 30, str(i), size=15)
        s.text(x + 82, y + 30, "•", size=20, fill=TEAL_TXT)
        c.text(f"rp{i}", x + 82, y + 30, "•", size=20)
        if i < 2:
            nx = 610 + (i + 1) * 150
            ny = 190 + ((i + 1) % 2) * 60
            s.arrow(x + 104, y + 23, nx + 2, ny + 23, stroke=TEAL_TXT, sw=1.6)
    s.text(818, 322, "每个节点多花一个指针的空间", size=12, fill=MUTED)
    c.text("rc", 818, 322, "每个节点多花一个指针的空间", size=12)
    s.text(610, 368, "✓ 已知前驱时插入删除 O(1)", size=13, anchor="start", fill=TEAL_TXT, weight="600")
    c.text("r1", 610 + 96, 368, "✓ 已知前驱时插入删除 O(1)", size=13, anchor="start")
    s.text(610, 398, "✗ 不支持随机访问,要走一遍 O(n)", size=13, anchor="start", fill="#b5762a")
    c.text("r2", 610 + 106, 398, "✗ 不支持随机访问,要走一遍 O(n)", size=13, anchor="start")

    s.text(W / 2, 480, "哈希表、栈、队列、堆、树、图 —— 都是这两者加约束的结果",
           size=12, fill=MUTED)
    c.text("foot", W / 2, 480, "哈希表、栈、队列、堆、树、图 —— 都是这两者加约束的结果", size=12)
    save(s, c, "02-storage-tradeoff")


# ---------------------------------------------------------------- figure 03
def fig03() -> None:
    W, H = 1120, 470
    s = Svg(W, H)
    c = Check(s)
    s.rect(0, 0, W, H, fill=CANVAS, stroke=CANVAS, rx=0)
    s.text(W / 2, 44, "为什么 LRU 必须同时用哈希表和双向链表", size=20, weight="600")
    c.text("t", W / 2, 44, "为什么 LRU 必须同时用哈希表和双向链表", size=20)

    # requirement -> structure
    reqs = [("按 key 查 O(1)", "数组做不到,链表更做不到"),
            ("删掉任意节点 O(1)", "单链表要 O(n) 找前驱"),
            ("移动到头部 O(1)", "需要能同时拿到前后"),
            ("淘汰尾部 O(1)", "要维护尾部指针")]
    s.panel(40, 82, 470, 300)
    c.panel("p1", 40, 82, 470, 300)
    s.text(275, 116, "① 先列出需求", size=15, weight="600", anchor="middle")
    c.text("h1", 275, 116, "① 先列出需求", size=15)
    for i, (a, b) in enumerate(reqs):
        y = 156 + i * 54
        s.text(70, y, a, size=14, anchor="start", weight="600", fill=BLUE)
        c.text(f"ra{i}", 70, y, a, size=14, anchor="start")
        s.text(70, y + 20, b, size=11, anchor="start", fill=MUTED)
        c.text(f"rb{i}", 70, y + 20, b, size=11, anchor="start")

    s.arrow(516, 232, 556, 232, stroke=INK, sw=2)
    s.text(536, 218, "反推", size=11, fill=MUTED)
    c.text("push", 536, 218, "反推", size=11)

    s.panel(566, 82, 514, 300)
    c.panel("p2", 566, 82, 514, 300)
    s.text(823, 116, "② 需求逼出的组合", size=15, weight="600")
    c.text("h2", 823, 116, "② 需求逼出的组合", size=15)
    s.rect(600, 148, 200, 66, fill=FILL_BLUE, stroke=BLUE)
    s.text(700, 176, "哈希表", size=15, weight="600", fill=BLUE)
    c.text("hsh", 700, 176, "哈希表", size=15)
    s.text(700, 198, "key → 节点指针", size=11, fill=MUTED)
    c.text("hsh2", 700, 198, "key → 节点指针", size=11)
    s.rect(846, 148, 200, 66, fill=FILL_TEAL, stroke=TEAL_TXT)
    s.text(946, 176, "双向链表", size=15, weight="600", fill=TEAL_TXT)
    c.text("dll", 946, 176, "双向链表", size=15)
    s.text(946, 198, "维护使用顺序", size=11, fill=MUTED)
    c.text("dll2", 946, 198, "维护使用顺序", size=11)
    s.text(823, 240, "哈希表负责「找到」,链表负责「顺序」", size=13)
    c.text("mid", 823, 240, "哈希表负责「找到」,链表负责「顺序」", size=13)
    s.text(823, 268, "单用任何一个都凑不齐四条需求", size=12, fill="#b5762a")
    c.text("mid2", 823, 268, "单用任何一个都凑不齐四条需求", size=12)
    s.text(823, 306, "O(1) + O(1) = 查、删、移、淘汰全是常数", size=13, fill=TEAL_TXT)
    c.text("mid3", 823, 306, "O(1) + O(1) = 查、删、移、淘汰全是常数", size=13)
    s.text(823, 340, "交替使用两种结构,是这个系列最常见的套路", size=12, fill=MUTED)
    c.text("mid4", 823, 340, "交替使用两种结构,是这个系列最常见的套路", size=12)

    s.text(W / 2, 424, "结论:先有你想要的「能力」,才有结构的设计", size=13, weight="600")
    c.text("foot", W / 2, 424, "结论:先有你想要的「能力」,才有结构的设计", size=13)
    save(s, c, "03-requirements-drive-structure")


# ---------------------------------------------------------------- figure 04
def fig04() -> None:
    W, H = 1120, 540
    s = Svg(W, H)
    c = Check(s)
    s.rect(0, 0, W, H, fill=CANVAS, stroke=CANVAS, rx=0)
    s.text(W / 2, 44, "同一棵树,两种思维模式", size=20, weight="600")
    c.text("t", W / 2, 44, "同一棵树,两种思维模式", size=20)

    # the tree, drawn once in the middle
    nodes = [(560, 108, "1"), (470, 196, "2"), (650, 196, "3"),
             (424, 284, "4"), (516, 284, "5"), (650, 284, "6")]
    for x, y, lab in nodes[1:3]:
        s.line(560, 128, x, y - 20, stroke=MUTED, sw=1.3)
    for x, y, lab in nodes[3:5]:
        s.line(470, 216, x, y - 20, stroke=MUTED, sw=1.3)
    s.line(650, 216, 650, 264, stroke=MUTED, sw=1.3)
    for x, y, lab in nodes:
        s.circle(x, y, 21, fill=PAPER, stroke=INK)
        s.text(x, y + 5, lab, size=15)
        c.text(f"n{x}", x, y + 5, lab, size=15)

    # left: traversal mode
    s.panel(36, 330, 500, 160)
    c.panel("L", 36, 330, 500, 160)
    s.text(286, 362, "① 遍历模式:在「位置」上做事", size=15, weight="600", fill=WARM_TXT)
    c.text("Lh", 286, 362, "① 遍历模式:在「位置」上做事", size=15)
    s.text(60, 396, "前序位置 → 拿到「从根下来的路径」", size=12, anchor="start")
    c.text("L1", 60 + 100, 396, "前序位置 → 拿到「从根下来的路径」", size=12, anchor="start")
    s.text(60, 422, "后序位置 → 拿到「子树算完的结果」", size=12, anchor="start")
    c.text("L2", 60 + 100, 422, "后序位置 → 拿到「子树算完的结果」", size=12, anchor="start")
    s.text(60, 452, "适合:路径和、深度、祖先、序列化", size=12, anchor="start", fill=MUTED)
    c.text("L3", 60 + 96, 452, "适合:路径和、深度、祖先、序列化", size=12, anchor="start")
    s.text(60, 476, "不关心函数返回什么,只关心在哪一步做事", size=11,
           anchor="start", fill=MUTED)
    c.text("L4", 60 + 116, 476, "不关心函数返回什么,只关心在哪一步做事", size=11, anchor="start")

    # right: decomposition mode
    s.panel(584, 330, 500, 160)
    c.panel("R", 584, 330, 500, 160)
    s.text(834, 362, "② 分解模式:定义语义,然后信任它", size=15, weight="600", fill=TEAL_TXT)
    c.text("Rh", 834, 362, "② 分解模式:定义语义,然后信任它", size=15)
    s.text(608, 396, 'max_depth(node) 返回「以它为根的深度」', size=12, anchor="start")
    c.text("R1", 608 + 116, 396, "max_depth(node) 返回「以它为根的深度」", size=12, anchor="start")
    s.text(608, 422, "不去追踪子树内部,只假设它算对了", size=12, anchor="start")
    c.text("R2", 608 + 100, 422, "不去追踪子树内部,只假设它算对了", size=12, anchor="start")
    s.text(608, 452, "适合:高度、直径、是否平衡、子树聚合", size=12, anchor="start", fill=MUTED)
    c.text("R3", 608 + 100, 452, "适合:高度、直径、是否平衡、子树聚合", size=12, anchor="start")
    s.text(608, 476, "难点是「信任递归」,不是写不出循环", size=11,
           anchor="start", fill=MUTED)
    c.text("R4", 608 + 100, 476, "难点是「信任递归」,不是写不出循环", size=11, anchor="start")

    save(s, c, "04-two-thinking-modes")


if __name__ == "__main__":
    fig01()
    fig02()
    fig03()
    fig04()
    print(f"\nOK — figures in {OUT}")
