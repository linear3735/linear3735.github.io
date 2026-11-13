#!/usr/bin/env python3
"""Draw the 6 diagrams for the chain-reversal post.

Every figure is generated, never hand-edited: run this script after any change.

`Check` catches text/text, text/arrow and off-canvas collisions, but it cannot
see text sitting on an unregistered line, and it cannot see an arrow that is
"correct" in the hitbox sense yet unreadable on screen.  So each SVG is also
rendered and eyeballed:

    sips -s format png -Z 1400 <file>.svg --out /tmp/<file>.png

Rendering caught four defects that `Check` did not:

  * a run of arrows drawn pointing the wrong way along the list (a linked-list
    figure whose arrows contradict the pointer story is worse than no figure);
  * a dashed group bracket whose top edge ran straight through a caption line;
  * an 8px arrowhead inside a ~54px node gap, which ate the whole line and made
    every arrow look like a detached triangle;
  * nodes whose aspect ratio was silently wrong, because the height was derived
    from the half-width.  Hence NODE_W / NODE_H below are both explicit.

Usage: python3 make_figures.py
"""
import sys
from pathlib import Path

REPO = Path.home() / "projects/linear3735.github.io"
sys.path.insert(0, str(REPO / "assets/blog/_tools"))
from svgkit import (Svg, Check, INK, MUTED, BLUE,                     # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/chain-reversal-20261110"
BAD = []

PITCH = 140.0       # horizontal distance between two adjacent nodes
NODE_W = 62.0
NODE_H = 50.0
NODE_HW = NODE_W / 2
NODE_GAP = 2.0      # clear space between a node's edge and an arrow's tip
HEAD = 6.0          # arrowhead length; 8.0 inside a short gap eats the line


def node(svg, chk, cx, cy, label, fill=FILL_GREY, stroke=INK, size=16):
    """One list node centred on (cx, cy)."""
    svg.rect(cx - NODE_HW, cy - NODE_H / 2, NODE_W, NODE_H,
             fill=fill, stroke=stroke, sw=1.4)
    svg.text(cx, cy + size * 0.36, label, size=size)
    chk.text(f"n{label}@{cx}", cx, cy + size * 0.36, label, size=size)
    return cy + NODE_H / 2


def arrow(svg, chk, src_cx, dst_cx, y, color=BLUE, dash=None, name="arrow"):
    """Arrow between two adjacent nodes, drawn edge to edge.

    Callers pass node CENTRES (so the code describes the list, not the pixels);
    the drawn segment is derived from them.  Registering the drawn segment --
    not the centre-to-centre span -- is what keeps Check honest: the wider box
    used to start inside the source node and collided with its digit label.
    `dst_cx < src_cx` gives a left-pointing arrow, which is how a reversed
    `next` pointer is drawn here.
    """
    sgn = 1.0 if dst_cx > src_cx else -1.0
    x_from = src_cx + sgn * (NODE_HW + NODE_GAP)
    x_to = dst_cx - sgn * (NODE_HW + NODE_GAP)
    svg.arrow(x_from, y, x_to, y, stroke=color, dash=dash, head=HEAD)
    chk.arrow(name, x_from, y, x_to, y)


def route(svg, chk, x_from, x_to, y, color=TEAL_TXT, name="route"):
    """A link between two non-adjacent nodes: dropped below the row so it does
    not cut through the digit labels of the nodes in between."""
    svg.arrow(x_from, y, x_to, y, stroke=color, head=HEAD)
    chk.arrow(name, x_from, y, x_to, y)


def caption(svg, chk, x, y, t, size=13, color=MUTED, anchor="start",
            weight="400", key=None):
    svg.text(x, y, t, size=size, fill=color, anchor=anchor, weight=weight)
    chk.text(key or f"cap-{t[:12]}", x, y, t, size=size, anchor=anchor)


def ptr(svg, chk, cx, node_bottom, t, color=WARM_TXT, size=12):
    """A pointer name under a node, joined to it by a short vertical arrow."""
    y = node_bottom + 34
    svg.text(cx, y, t, size=size, fill=color, anchor="middle", weight="600")
    chk.text(f"ptr-{t}@{cx}", cx, y, t, size=size)
    svg.arrow(cx, y - 16, cx, node_bottom + 2, stroke=color, sw=1.4, head=HEAD)
    chk.arrow(f"ptr-arrow-{t}@{cx}", cx, y - 16, cx, node_bottom + 2)


def row(n):
    """n node centres, evenly pitched and centred in the 880-wide canvas."""
    span = (n - 1) * PITCH
    return [440 - span / 2 + i * PITCH for i in range(n)]


def chain(svg, chk, xs, y, color=BLUE, name="c"):
    for i in range(len(xs) - 1):
        arrow(svg, chk, xs[i], xs[i + 1], y, color=color, name=f"{name}{i}")


# ---------------------------------------------------------------- figure 1
def fig_iterative():
    """206, iterative: three pointers, and where they end up."""
    svg, chk = Svg(880, 400), None
    chk = Check(svg)

    svg.panel(20, 20, 840, 205)
    chk.panel("top", 20, 20, 840, 205)
    caption(svg, chk, 40, 50, "循环体转到一半:结点 1 已经翻好,它的 next 指向 null",
            key="cap-mid")

    # Shifted right of `row(4)`: the reversed head needs room on its left for the
    # null terminal, and a centred row leaves none.
    xs, cy = [295, 435, 575, 715], 127
    bottom = node(svg, chk, xs[0], cy, "1", fill=FILL_TEAL)     # already done
    for cx, v in zip(xs[1:], "234"):
        node(svg, chk, cx, cy, v, fill=FILL_BLUE)
    # Node 1 is already reversed, so its next is the new terminal.  Draw that
    # leftward dashed run and put `null` *beyond* its tail, the same way the
    # bottom panel draws `4 -> null`.  The arrow used to start at x=240 and the
    # label was right-aligned to x=268, i.e. the two overlapped: the label's box
    # ran 246..268 while the arrow's box ran 240..295.  Shortening the arrow and
    # pushing the label out to x=233 clears it (Check pads text/arrow by 3px).
    arrow(svg, chk, 241, 295, cy, color=MUTED, dash="4 3", name="1-null")
    caption(svg, chk, 233, cy + 4, "null", size=12, anchor="end",
            key="t-null-1")
    # 2.next already points back at 1; the untouched part still runs 2->3->4.
    arrow(svg, chk, xs[1], xs[0], cy, name="2-1")
    arrow(svg, chk, xs[1], xs[2], cy, name="2-3")
    arrow(svg, chk, xs[2], xs[3], cy, name="3-4")
    for cx, t, col in zip(xs[:3], ["pre", "cur", "nxt"],
                          [TEAL_TXT, WARM_TXT, MUTED]):
        ptr(svg, chk, cx, bottom, t, color=col)
    caption(svg, chk, xs[1], bottom + 74,
            "2.next 已经改向,所以它原来的后继必须先存进 nxt", size=12,
            anchor="middle", key="t-mid-note")

    svg.panel(20, 240, 840, 140)
    chk.panel("bot", 20, 240, 840, 140)
    caption(svg, chk, 40, 270,
            "cur 走到 null 时循环结束:pre 停在原来的尾结点上,它就是新头结点",
            key="cap-end")

    xs2, cy2 = row(4), 335
    for cx, v in zip(xs2, "4321"):
        node(svg, chk, cx, cy2, v, fill=FILL_BLUE)
    chain(svg, chk, xs2, cy2, name="r")
    arrow(svg, chk, xs2[3], xs2[3] + 96, cy2, color=MUTED, dash="4 3",
          name="4-null")
    caption(svg, chk, xs2[3] + 104, cy2 + 4, "null", size=12, anchor="start",
            key="t-null-2")
    caption(svg, chk, xs2[0], cy2 - 48, "return pre", size=14,
            color=TEAL_TXT, anchor="middle", weight="600", key="t-ret")

    BAD.append(chk.run("01-iterative-reverse"))
    svg.save(OUT / "01-iterative-reverse.svg")


# ---------------------------------------------------------------- figure 2
def fig_recursive():
    """206, recursive: assume the subproblem is solved, then splice head back."""
    svg, chk = Svg(880, 430), None
    chk = Check(svg)

    svg.panel(20, 20, 840, 190)
    chk.panel("top", 20, 20, 840, 190)
    caption(svg, chk, 40, 50,
            "① 先假设子问题已经解决:last = reverseList(head.next)",
            key="cap-1")

    cy = 125
    node(svg, chk, 120, cy, "1", fill=FILL_WARM)
    caption(svg, chk, 120, cy - 46, "head", size=12, color=WARM_TXT,
            weight="600", key="t-head")
    xs = [260, 400, 540]
    for cx, v in zip(xs, "432"):
        node(svg, chk, cx, cy, v, fill=FILL_BLUE)
    # 1 -> 2 is the OLD link, still present and about to be cut: dashed.
    arrow(svg, chk, 120, xs[0], cy, color=MUTED, dash="5 4", name="1-2-old")
    caption(svg, chk, 190, cy - 14, "旧链接,待断", size=11, anchor="middle",
            key="t-old-link")
    # The sublist has ALREADY been reversed, so its pointers run right-to-left.
    arrow(svg, chk, xs[0], xs[1], cy, name="4-3")
    arrow(svg, chk, xs[1], xs[2], cy, name="3-2")
    arrow(svg, chk, xs[2], xs[2] + 96, cy, color=MUTED, dash="4 3",
          name="2-null")
    caption(svg, chk, xs[2] + 104, cy + 4, "null", size=12, anchor="start",
            key="t-null-1")

    svg.panel(20, 235, 840, 175)
    chk.panel("bot", 20, 235, 840, 175)
    caption(svg, chk, 40, 265,
            "② 再把 head 接到反转后的尾巴上,并断开它自己的 next",
            key="cap-2")

    cy2 = 340
    xs2 = [200, 320, 440, 560]
    for cx, v in zip(xs2, "4321"):
        node(svg, chk, cx, cy2, v,
             fill=FILL_WARM if v == "1" else FILL_BLUE)
    chain(svg, chk, xs2, cy2, name="b")
    caption(svg, chk, 560, cy2 - 50, "head 变成新尾巴", size=12,
            color=WARM_TXT, weight="600", key="t-tail")
    caption(svg, chk, 640, cy2 + 4, "null", size=12, key="t-null-2")
    caption(svg, chk, 200, cy2 + 58, "子链表 2→3→4 已被子问题翻成 4→3→2",
            size=12, key="t-sub-note")

    BAD.append(chk.run("02-recursive-decompose"))
    svg.save(OUT / "02-recursive-decompose.svg")


# ---------------------------------------------------------------- figure 3
def fig_reverse_n():
    """reverseN: the tail of the reversed prefix must point at `successor`."""
    svg, chk = Svg(880, 410), None
    chk = Check(svg)

    svg.panel(20, 20, 840, 180)
    chk.panel("a", 20, 20, 840, 180)
    caption(svg, chk, 40, 50,
            "reverseN(head, 3):只反前 3 个,第 4 个节点必须原样挂回去",
            key="cap-a")

    xs, cy = row(5), 127
    for cx, v in zip(xs, "12345"):
        node(svg, chk, cx, cy, v,
             fill=FILL_WARM if v in "123" else FILL_TEAL)
    chain(svg, chk, xs, cy, name="a")
    caption(svg, chk, xs[3], cy - 50, "successor", size=12, color=TEAL_TXT,
            weight="600", key="t-succ")
    svg.arrow(xs[3], cy - 42, xs[3], cy - NODE_H / 2 - 4, stroke=TEAL_TXT,
              sw=1.4, head=HEAD)
    chk.arrow("succ-arrow", xs[3], cy - 42, xs[3], cy - NODE_H / 2 - 4)

    svg.panel(20, 225, 840, 165)
    chk.panel("b", 20, 225, 840, 165)
    caption(svg, chk, 40, 255,
            "反转后:3→2→1 的尾巴必须指向 successor,而不是 null",
            key="cap-b")

    cy2 = 327
    for cx, v in zip(xs, "32145"):
        node(svg, chk, cx, cy2, v,
             fill=FILL_WARM if v in "321" else FILL_TEAL)
    arrow(svg, chk, xs[1], xs[0], cy2, name="b0")   # 2 -> 1, leftwards
    arrow(svg, chk, xs[2], xs[1], cy2, name="b1")   # 3 -> 2, leftwards
    arrow(svg, chk, xs[2], xs[3], cy2, color=TEAL_TXT, name="b2")   # 1 -> 4
    arrow(svg, chk, xs[3], xs[4], cy2, name="b3")   # 4 -> 5
    caption(svg, chk, xs[0], cy2 + 56, "1.next = successor", size=12,
            color=TEAL_TXT, anchor="middle", weight="600", key="t-fix")

    BAD.append(chk.run("03-reverse-n-successor"))
    svg.save(OUT / "03-reverse-n-successor.svg")


# ---------------------------------------------------------------- figure 4
def fig_reverse_interval():
    """92: the recursion peels off leading nodes until m == 1."""
    svg, chk = Svg(880, 445), None
    chk = Check(svg)

    svg.panel(20, 20, 840, 197)
    chk.panel("a", 20, 20, 840, 197)
    caption(svg, chk, 40, 50,
            "reverseBetween(head, m = 2, n = 4):head 在区间外,它自己不动",
            key="cap-a")

    xs, cy = row(5), 122
    node(svg, chk, xs[0], cy, "1", fill=FILL_GREY)
    for cx, v in zip(xs[1:4], "234"):
        node(svg, chk, cx, cy, v, fill=FILL_WARM)
    node(svg, chk, xs[4], cy, "5", fill=FILL_GREY)
    chain(svg, chk, xs, cy, name="a")
    # The interval bracket sits BELOW the nodes, so its dashed top edge cannot
    # cut through the caption line at y = 50.
    svg.rect(xs[1] - 36, cy + 34, (xs[3] - xs[1]) + 72, 42, fill="none",
             stroke=WARM_TXT, sw=1.6, rx=10, dash="6 4")
    chk.panel("interval", xs[1] - 36, cy + 34, (xs[3] - xs[1]) + 72, 42)
    caption(svg, chk, (xs[1] + xs[3]) / 2, cy + 96, "要反转的区间 [m, n]",
            size=12, color=WARM_TXT, anchor="middle", key="t-interval")

    svg.panel(20, 245, 840, 170)
    chk.panel("b", 20, 245, 840, 170)
    caption(svg, chk, 40, 275,
            "递归一层后:m - 1 = 1,问题退化成 reverseN(head', 3)",
            key="cap-b")

    cy2 = 340
    node(svg, chk, xs[0], cy2, "1", fill=FILL_GREY)
    for cx, v in zip(xs[1:4], "432"):
        node(svg, chk, cx, cy2, v, fill=FILL_BLUE)
    node(svg, chk, xs[4], cy2, "5", fill=FILL_GREY)
    arrow(svg, chk, xs[0], xs[1], cy2, name="b0")   # 1 -> 4
    arrow(svg, chk, xs[2], xs[1], cy2, name="b1")   # 3 -> 2, leftwards
    arrow(svg, chk, xs[3], xs[2], cy2, name="b2")   # 4 -> 3, leftwards
    # 2 -> 5 is NOT adjacent (3 and 4 sit in between), so a straight edge-to-edge
    # arrow would run through their digit labels.  Route it below the row.
    route(svg, chk, xs[1], xs[4], cy2 + 56, name="b3")
    caption(svg, chk, (xs[1] + xs[4]) / 2, cy2 + 84, "2.next = 5", size=12,
            color=TEAL_TXT, anchor="middle", weight="600", key="t-fix")

    BAD.append(chk.run("04-reverse-interval"))
    svg.save(OUT / "04-reverse-interval.svg")


# ---------------------------------------------------------------- figure 5
def fig_k_group():
    """25: count k nodes first, then treat one group as one node."""
    svg, chk = Svg(880, 455), None
    chk = Check(svg)

    svg.panel(20, 20, 840, 210)
    chk.panel("a", 20, 20, 840, 210)
    caption(svg, chk, 40, 50,
            "k = 2:先把前 k 个结点数出来;数不满 k 个就整段不动",
            key="cap-a")

    xs, cy = row(5), 122
    for cx, v in zip(xs, "12345"):
        node(svg, chk, cx, cy, v,
             fill=FILL_WARM if v in "12" else FILL_TEAL)
    chain(svg, chk, xs, cy, name="a")
    svg.rect(xs[0] - 36, cy + 34, (xs[1] - xs[0]) + 72, 42, fill="none",
             stroke=WARM_TXT, sw=1.6, rx=10, dash="6 4")
    chk.panel("g1", xs[0] - 36, cy + 34, (xs[1] - xs[0]) + 72, 42)
    svg.rect(xs[2] - 36, cy + 34, (xs[4] - xs[2]) + 72, 42, fill="none",
             stroke=TEAL_TXT, sw=1.6, rx=10, dash="6 4")
    chk.panel("g2", xs[2] - 36, cy + 34, (xs[4] - xs[2]) + 72, 42)
    caption(svg, chk, (xs[0] + xs[1]) / 2, cy + 96, "第 1 组:反转",
            size=12, color=WARM_TXT, anchor="middle", key="t-g1")
    caption(svg, chk, (xs[2] + xs[4]) / 2, cy + 96, "递归处理剩下的",
            size=12, color=TEAL_TXT, anchor="middle", key="t-g2")

    svg.panel(20, 250, 840, 180)
    chk.panel("b", 20, 250, 840, 180)
    caption(svg, chk, 40, 280,
            "反转前 k 个得到 new_head;原 head 变成本组尾巴,再接上后面的结果",
            key="cap-b")

    cy2 = 350
    for cx, v in zip(xs, "21435"):
        node(svg, chk, cx, cy2, v,
             fill=FILL_WARM if v in "21" else FILL_TEAL)
    chain(svg, chk, xs, cy2, name="b")
    caption(svg, chk, xs[4], cy2 + 58, "5 不足 k 个,原样留下", size=12,
            color=MUTED, anchor="middle", key="t-tail-note")

    BAD.append(chk.run("05-k-group"))
    svg.save(OUT / "05-k-group.svg")


# ---------------------------------------------------------------- figure 6
def fig_palindrome():
    """234: find the middle, reverse the back half, walk inwards."""
    svg, chk = Svg(880, 620), None
    chk = Check(svg)

    xs = row(5)

    svg.panel(20, 20, 840, 180)
    chk.panel("a", 20, 20, 840, 180)
    caption(svg, chk, 40, 50,
            "① 快慢指针找中点:fast 走两步,slow 走一步", key="cap-a")
    cy = 122
    for cx, v in zip(xs, "12321"):
        node(svg, chk, cx, cy, v,
             fill=FILL_WARM if cx in xs[:3] else FILL_TEAL)
    chain(svg, chk, xs, cy, name="a")
    caption(svg, chk, xs[2], cy + 60,
            "slow 停在这里(奇数长度时,正中间归后半段)", size=12,
            anchor="middle", key="t-slow")

    svg.panel(20, 230, 840, 170)
    chk.panel("b", 20, 230, 840, 170)
    caption(svg, chk, 40, 260,
            "② 就地反转后半段:3→2→1 变成 1→2→3", key="cap-b")
    cy2 = 322
    for cx, v in zip(xs, "12123"):
        node(svg, chk, cx, cy2, v,
             fill=FILL_WARM if cx in xs[:2] else FILL_TEAL)
    arrow(svg, chk, xs[0], xs[1], cy2, name="b0")   # front half untouched
    arrow(svg, chk, xs[3], xs[2], cy2, name="b1")   # 2 -> 1, leftwards
    arrow(svg, chk, xs[4], xs[3], cy2, name="b2")   # 3 -> 2, leftwards
    caption(svg, chk, xs[1], cy2 + 58, "后半段已反转(前 2 个节点原地不动)",
            size=12, anchor="middle", key="t-rev")

    svg.panel(20, 430, 840, 170)
    chk.panel("c", 20, 430, 840, 170)
    caption(svg, chk, 40, 460,
            "③ 一个从头、一个从后半段头,同速前进逐对比较", key="cap-c")
    for i, (a, b) in enumerate([("1", "1"), ("2", "2"), ("3", "3")]):
        x = 200 + i * 130
        caption(svg, chk, x, 530, a, size=16, color=INK, key=f"pa{i}")
        caption(svg, chk, x + 46, 530, b, size=16, color=TEAL_TXT,
                key=f"pb{i}")
        caption(svg, chk, x + 23, 530, "=", size=15, color=TEAL_TXT,
                key=f"peq{i}")
    caption(svg, chk, 600, 530, "三对全部相等 → 是回文", size=13,
            color=TEAL_TXT, weight="600", key="t-ok")

    BAD.append(chk.run("06-palindrome"))
    svg.save(OUT / "06-palindrome.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_iterative()
    fig_recursive()
    fig_reverse_n()
    fig_reverse_interval()
    fig_k_group()
    fig_palindrome()
    total = sum(BAD)
    print(f"  {total} layout problem(s) total")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
