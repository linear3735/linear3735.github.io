#!/usr/bin/env python3
"""Generate the six diagrams for _posts/2026-11-17-stack-queue-mutual.md.

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
                                    "stack-queue-mutual-20261117"))

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
    c.arrow(f"arrow({x1},{y1}->{x2},{y2})", x1, y1, x2, y2)


def save(s, c, name):
    global problems
    problems += c.run(name)
    s.save(os.path.join(OUT, name))


# ---------------------------------------------------------------------------
# 01: the whole idea in one line — a stack reverses, two stacks cancel out
# ---------------------------------------------------------------------------
def fig01():
    W, H = 1000, 300
    s, c = Svg(W, H), None
    c = Check(s)
    txt(s, c, W / 2, 36, "一个栈是反转,两个栈是反转两次,而反转两次等于没反转", size=15)

    row_y, cw, ch = 142, 60, 34
    stack_w, slot_h = 90, 34

    # --- stage A: the enqueue order, drawn as a plain row ---
    for i, v in enumerate((1, 2, 3)):
        cell(s, c, 50 + i * cw, row_y, cw, ch, str(v), fill=FILL_BLUE)
    txt(s, c, 140, 74, "① 入队顺序 1 2 3", size=13)
    txt(s, c, 140, 240, "原始顺序:FIFO", size=12, fill=MUTED)

    # --- stage B: s1, pushed in order (top is 3) ---
    for i, v in enumerate((1, 2, 3)):
        cell(s, c, 305, 176 - i * slot_h, stack_w, slot_h, str(v),
             fill=PAPER if v != 3 else FILL_WARM)
    txt(s, c, 350, 74, "② 依次 push 进 s1", size=13)
    txt(s, c, 350, 96, "第一次反转:3 2 1", size=12, fill=MUTED)
    txt(s, c, 350, 240, "栈顶是 3,队头 1 被压在最底下", size=11, fill=MUTED)

    # --- stage C: s2, s1 poured in (top is 1) ---
    for i, v in enumerate((3, 2, 1)):
        cell(s, c, 515, 176 - i * slot_h, stack_w, slot_h, str(v),
             fill=PAPER if v != 1 else FILL_TEAL)
    txt(s, c, 560, 74, "③ 全部倒入 s2", size=13)
    txt(s, c, 560, 96, "第二次反转:1 2 3", size=12, fill=MUTED)
    txt(s, c, 560, 240, "栈顶变成 1,正是队头", size=11, fill=TEAL_TXT)

    # --- stage D: pop order ---
    for i, v in enumerate((1, 2, 3)):
        cell(s, c, 680 + i * cw, row_y, cw, ch, str(v), fill=FILL_BLUE)
    txt(s, c, 770, 74, "④ 依次弹出", size=13)
    txt(s, c, 770, 240, "回到原始顺序:FIFO", size=12, fill=MUTED)

    arrow(s, c, 240, row_y + ch / 2, 296, row_y + ch / 2)
    arrow(s, c, 405, row_y + ch / 2, 506, row_y + ch / 2)
    arrow(s, c, 615, row_y + ch / 2, 671, row_y + ch / 2)
    txt(s, c, 455, 128, "必须一次倒空", size=11, fill=MUTED)
    save(s, c, "01-two-reversals.svg")


# ---------------------------------------------------------------------------
# 02: five frames of a real trace, so the "s2 not empty -> don't move" rule
#     is visible rather than asserted
# ---------------------------------------------------------------------------
def fig02():
    W, H = 1080, 430
    s = Svg(W, H)
    c = Check(s)
    txt(s, c, W / 2, 30, "MyQueue 的五个时刻:注意 s2 没排空之前,新元素一直等在 s1",
        size=15)

    cell_w, slot_h, base_off = 64, 30, 250
    frames = [
        ("push 1,2,3", [1, 2, 3], [],
         ["三个元素都进了 s1", "s2 还是空的"]),
        ("peek()", [], [3, 2, 1],
         ["s2 空,把 s1 一次倒空", "队头 1 到了 s2 栈顶"]),
        ("push(4)", [4], [3, 2, 1],
         ["4 只能等在 s1 里", "它比 s2 里的都晚入队"]),
        ("pop() → 1", [4], [3, 2],
         ["返回队头 1", "s2 没空就绝不搬"]),
        ("pop() x3", [], [],
         ["2 3 出完后 s2 空", "再搬一次,s1 的 4 出队"]),
    ]

    for k, (op, s1, s2, cap) in enumerate(frames):
        x0, y0, pw, ph = 14 + k * 214, 52, 196, 344
        s.panel(x0, y0, pw, ph)
        c.panel(f"frame{k}", x0, y0, pw, ph)
        txt(s, c, x0 + pw / 2, y0 + 30, op, size=14, weight="600")
        txt(s, c, x0 + 50, y0 + 58, "s1", size=12, fill=MUTED)
        txt(s, c, x0 + 146, y0 + 58, "s2", size=12, fill=MUTED)

        for col, vals in ((18, s1), (114, s2)):
            for i in range(3):
                v = vals[i] if i < len(vals) else None
                yy = y0 + base_off - (i + 1) * slot_h
                if v is None:
                    s.rect(x0 + col, yy, cell_w, slot_h, fill=PAPER,
                           stroke=LINE, sw=1.0, rx=0, dash="3 3")
                    continue
                fill = FILL_TEAL if i == len(vals) - 1 else FILL_BLUE
                cell(s, c, x0 + col, yy, cell_w, slot_h, str(v), fill=fill,
                     size=13)

        txt(s, c, x0 + pw / 2, y0 + 292, cap[0], size=10.5)
        txt(s, c, x0 + pw / 2, y0 + 310, cap[1], size=10.5)

    txt(s, c, W / 2, 416, "虚线格 = 空;橙色格 = 该栈的栈顶,也就是队列的队头",
        size=11, fill=MUTED)
    save(s, c, "02-two-stack-frames.svg")


# ---------------------------------------------------------------------------
# 03: where the "amortised" comes from — three readings of the same bound
# ---------------------------------------------------------------------------
def fig03():
    W, H = 1000, 380
    s = Svg(W, H)
    c = Check(s)
    txt(s, c, W / 2, 34, "记账法:代价在 push 的那一刻就已经预付完了", size=15)

    cols = [(60, 250, "阶段"), (310, 220, "谁付这枚硬币"),
            (530, 130, "枚数"), (660, 280, "每个元素发生几次")]
    for x, w, head in cols:
        s.rect(x, 78, w, 36, fill=FILL_GREY, stroke=INK, sw=1.2, rx=0)
        txt(s, c, x + w / 2, 102, head, size=13)

    rows = [
        ("① push 进 s1", "本次 push 当场付", "1", "恰好 1 次"),
        ("② 从 s1 搬到 s2", "用元素自己的存款", "1", "最多 1 次"),
        ("③ 从 s2 弹出", "用元素自己的存款", "1", "最多 1 次"),
    ]
    for r, (a, b, n, cnt) in enumerate(rows):
        y = 114 + r * 40
        for x, w, _ in cols:
            s.rect(x, y, w, 40, fill=PAPER, stroke=INK, sw=1.0, rx=0)
        txt(s, c, cols[0][0] + 14, y + 26, a, size=12.5, anchor="start")
        txt(s, c, cols[1][0] + 14, y + 26, b, size=12.5, anchor="start")
        txt(s, c, cols[2][0] + cols[2][1] / 2, y + 26, n, size=12.5)
        txt(s, c, cols[3][0] + 14, y + 26, cnt, size=12.5, anchor="start")

    txt(s, c, W / 2, 272, "每个元素一生最多 3 枚硬币 → m 个元素 ≤ 3m → 均摊到每次操作是 O(1)",
        size=13.5, fill=TEAL_TXT)

    boxes = [
        ("整体法", "总代价 ≤ 3m + n ≤ 4n", 40),
        ("记账法", "每个元素预付 3 枚硬币", 350),
        ("势能法", "Φ = |s1|,每次均摊 ≤ 2", 660),
    ]
    for title, body, x in boxes:
        s.panel(x, 296, 300, 62)
        c.panel(f"box{title}", x, 296, 300, 62)
        txt(s, c, x + 150, 320, title, size=13, weight="600")
        txt(s, c, x + 150, 342, body, size=12, fill=MUTED)
    save(s, c, "03-amortized-ledger.svg")


# ---------------------------------------------------------------------------
# 04: one queue as a stack — rotating the new element to the front
# ---------------------------------------------------------------------------
def fig04():
    W, H = 1040, 350
    s = Svg(W, H)
    c = Check(s)
    txt(s, c, W / 2, 36, "用一个队列实现栈:push(4) 时把前面的元素依次转到队尾",
        size=15)

    cw, ch, x0 = 90, 42, 220
    # (行标签, 队列内容(队头在前), 右侧注解, 刚被转到队尾的元素下标, 队头下标)
    rows = [
        ("push(4) 之后", [1, 2, 3, 4], "队头还是 1", None, 0),
        ("转 1 次", [2, 3, 4, 1], "1 出队又入队", 3, 0),
        ("转 2 次", [3, 4, 1, 2], "2 出队又入队", 3, 0),
        ("转 3 次", [4, 1, 2, 3], "队头变成 4 = 栈顶", 3, 0),
    ]
    for r, (label, vals, note, moved, front) in enumerate(rows):
        y = 76 + r * 60
        txt(s, c, 40, y + 27, label, size=13, anchor="start", weight="600")
        arrow(s, c, 170, y + ch / 2, 213, y + ch / 2)
        txt(s, c, 120, y - 6, "队头", size=10.5, fill=MUTED)
        for i, v in enumerate(vals):
            if i == front:
                fill = FILL_TEAL
            elif i == moved:
                fill = FILL_WARM
            else:
                fill = FILL_BLUE
            cell(s, c, x0 + i * cw, y, cw, ch, str(v), fill=fill, size=14)
        txt(s, c, x0 + 4 * cw + 26, y + 27, note, size=12, anchor="start")

    txt(s, c, W / 2, 328, "转了 3 次 = 原来的元素个数 = push 之后的 size 减 1", size=12,
        fill=MUTED)
    save(s, c, "04-one-queue-rotate.svg")


# ---------------------------------------------------------------------------
# 05: min stack — the auxiliary stack must be pushed on *every* push
# ---------------------------------------------------------------------------
def fig05():
    W, H = 900, 420
    s = Svg(W, H)
    c = Check(s)
    txt(s, c, W / 2, 36, "最小栈:辅助栈和主栈同步升降,所以两栈永远等长", size=15)

    sw, sh, base = 100, 44, 344
    panels = [
        (40, [(3, 3), (1, 1)],
         "push(3), push(1):两栈等长,mins 栈顶就是最小值 1"),
        (480, [(3, 3), (1, 1), (2, 1)],
         "push(2):2 没刷新纪录,mins 仍然压 1 → 两栈依然等长"),
    ]
    for x0, pairs, cap in panels:
        s.panel(x0, 62, 380, 318)
        c.panel(f"panel{x0}", x0, 62, 380, 318)
        txt(s, c, x0 + 110, 92, "data", size=13, fill=MUTED)
        txt(s, c, x0 + 270, 92, "mins", size=13, fill=MUTED)
        for i, (dv, mv) in enumerate(pairs):
            y = base - (i + 1) * sh
            top = (i == len(pairs) - 1)
            cell(s, c, x0 + 60, y, sw, sh, str(dv),
                 fill=FILL_BLUE if not top else FILL_WARM, size=14)
            cell(s, c, x0 + 220, y, sw, sh, str(mv),
                 fill=FILL_TEAL if top else FILL_BLUE, size=14)
            arrow(s, c, x0 + 166, y + sh / 2, x0 + 214, y + sh / 2, stroke=MUTED)
        txt(s, c, x0 + 190, 388, cap, size=11)
    txt(s, c, W / 2, 408, "橙色 = 数据栈栈顶;绿色 = 辅助栈栈顶,getMin() 直接读它",
        size=10.5, fill=MUTED)
    save(s, c, "05-min-stack.svg")


# ---------------------------------------------------------------------------
# 06: longest valid parentheses — the stack holds the positions that did NOT
#     match, and two neighbouring boundaries bracket one valid run
# ---------------------------------------------------------------------------
def fig06():
    W, H = 1020, 470
    s = Svg(W, H)
    c = Check(s)
    txt(s, c, W / 2, 36,
        "最长有效括号:栈里存的是「配不上的下标」,它把字符串切成若干段", size=15)

    s.panel(30, 58, 960, 366)
    c.panel("panel", 30, 58, 960, 366)
    txt(s, c, 60, 80, "i / 字符", size=12, fill=MUTED, anchor="start")
    txt(s, c, 250, 80, "栈(底 → 顶)", size=12, fill=MUTED, anchor="start")
    txt(s, c, 560, 80, "这一步", size=12, fill=MUTED, anchor="start")
    txt(s, c, 900, 80, "答案", size=12, fill=MUTED, anchor="start")

    rows = [
        ("i=0  ')'", [0], "弹掉 -1,栈空 → 把 0 压回去当新分界", "—"),
        ("i=1  '('", [0, 1], "左括号,压入下标 1", "—"),
        ("i=2  ')'", [0], "弹掉 1,栈顶 0 还在 → 2 - 0 = 2", "2"),
        ("i=3  '('", [0, 3], "左括号,压入下标 3", "2"),
        ("i=4  ')'", [0], "弹掉 3,栈顶 0 还在 → 4 - 0 = 4", "4"),
        ("i=5  ')'", [5], "弹掉 0,栈空 → 把 5 压回去当新分界", "4"),
    ]
    bw, bh, x0 = 52, 40, 250
    for r, (label, st, action, best) in enumerate(rows):
        y = 96 + r * 54
        txt(s, c, 60, y + 26, label, size=12.5, anchor="start", weight="600")
        for j, v in enumerate(st):
            # 栈底那个下标是分界,栈顶那个是还没配上的左括号
            fill = FILL_TEAL if j == 0 else FILL_BLUE
            cell(s, c, x0 + j * (bw + 6), y, bw, bh, str(v), fill=fill, size=14)
        txt(s, c, 560, y + 26, action, size=12, anchor="start")
        txt(s, c, 900, y + 26, best, size=13, anchor="start", weight="600")

    txt(s, c, W / 2, 446,
        "绿色 = 栈底的分界;相邻两个分界之间一定是一段有效括号,所以答案只在配对成功那一步更新",
        size=11, fill=MUTED)
    save(s, c, "06-stack-of-boundaries.svg")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in (fig01, fig02, fig03, fig04, fig05, fig06):
        f()
    print(f"\n  {problems} layout problem(s) across 6 figures")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
