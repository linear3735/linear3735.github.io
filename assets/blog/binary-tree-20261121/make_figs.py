#!/usr/bin/env python3
"""Figures for the binary-tree post (2026-11-21).

Five SVGs into assets/img/binary-tree-20261121/.  Run this from the repo root:

    python3 assets/blog/binary-tree-20261121/make_figs.py

Every label is registered with svgkit's Check so geometric collisions fail the
script, and every generated file is parsed back as XML before we exit — a stray
`<` used to produce a file that sips refused to render with no useful message.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "img" / "binary-tree-20261121"

sys.path.insert(0, str(HERE.parent / "_tools"))
from svgkit import (  # noqa: E402
    INK, MUTED, BLUE, LINE, PAPER, CANVAS,
    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
    WARM_TXT, TEAL_TXT,
    Svg, Check,
)

bad = 0

LEVELS = [[1], [2, 3], [4, 5, 6, 7]]          # the running example: a perfect 7-node tree
CHAIN = [[1], [2], [3], [4], [5]]             # a degenerate tree, for the O(N^2) figure


def layout(x0, y0, w, lh, levels):
    """Position every node.  Child index of (d, i) is 2i / 2i+1 in level d+1."""
    rows = []
    for d, row in enumerate(levels):
        n = len(row)
        rows.append([(x0 + (i + 0.5) * (w / n), y0 + d * lh, v)
                     for i, v in enumerate(row)])
    return rows


def draw_tree(s, c, rows, r=19, node_fill=FILL_BLUE, tag="t"):
    """Draw edges then nodes.  Returns the same nested list with coordinates."""
    for d in range(len(rows) - 1):
        for i, (cx, cy, _v) in enumerate(rows[d]):
            for k, ci in enumerate((2 * i, 2 * i + 1)):
                if ci < len(rows[d + 1]):
                    nx, ny, _ = rows[d + 1][ci]
                    s.line(cx, cy + r, nx, ny - r, stroke=MUTED, sw=1.3)
    for d, row in enumerate(rows):
        for i, (cx, cy, v) in enumerate(row):
            if v is None:
                continue
            s.circle(cx, cy, r, fill=node_fill, stroke=INK, sw=1.4)
            s.text(cx, cy + 5, str(v), size=14, fill=INK, weight="600")
            c.text(f"{tag}n{d}{i}", cx, cy + 5, str(v), size=14)
    return rows


def badge(s, c, x, y, t, name, fill=WARM_TXT, size=12):
    s.text(x, y, t, size=size, fill=fill, anchor="middle", weight="600")
    c.text(name, x, y, t, size=size)


def chips(s, c, x0, y, items, w=44, h=26, gap=2, tag="c"):
    """A horizontal strip of small labels.  items: list of (text, kind)."""
    palette = {
        "pre": (FILL_BLUE, BLUE),
        "in": (FILL_WARM, WARM_TXT),
        "post": (FILL_TEAL, TEAL_TXT),
        "grey": (FILL_GREY, MUTED),
    }
    for k, (t, kind) in enumerate(items):
        f, tc = palette[kind]
        cx = x0 + k * (w + gap)
        s.rect(cx, y, w, h, fill=f, stroke=f, rx=5)
        s.text(cx + w / 2, y + h - 8, t, size=12, fill=tc, weight="600")
        c.text(f"{tag}{k}", cx + w / 2, y + h - 8, t, size=12)
    return x0 + len(items) * (w + gap) - gap


# ---------------------------------------------------------------- figure 1
def fig1():
    global bad
    s = Svg(1080, 400)
    c = Check(s)
    s.text(36, 40, "同一棵树,三种遍历顺序:节点没变,变的是「给节点编号的时刻」",
           size=17, fill=INK, anchor="start", weight="600")
    c.text("title", 36, 40, "同一棵树,三种遍历顺序:节点没变,变的是「给节点编号的时刻」", 17, "start")

    orders = [
        ("前序:进入时就记", [1, 2, 4, 5, 3, 6, 7], BLUE),
        ("中序:左子树走完才记", [4, 2, 5, 1, 6, 3, 7], WARM_TXT),
        ("后序:离开时才记", [4, 5, 2, 6, 7, 3, 1], TEAL_TXT),
    ]
    for col, (name, order, col_txt) in enumerate(orders):
        x0 = 30 + col * 360
        s.label(x0, 84, name, size=13, fill=col_txt, weight="600")
        c.text(f"h{col}", x0, 84, name, 13, "start")
        rows = layout(x0, 126, 280, 76, LEVELS)
        draw_tree(s, c, rows, tag=f"t{col}")
        rank = {v: k + 1 for k, v in enumerate(order)}
        for d, row in enumerate(rows):
            for i, (cx, cy, v) in enumerate(row):
                badge(s, c, cx + 22, cy - 13, str(rank[v]), f"b{col}{d}{i}")

    s.label(36, 372, "三种顺序下的编号都是从 1 到 7 的全排列:访问节点的顺序完全一样,只是「记下来」的位置不同。",
            size=12)
    c.text("foot", 36, 372, "三种顺序下的编号都是从 1 到 7 的全排列:访问节点的顺序完全一样,只是「记下来」的位置不同。", 12, "start")
    bad += c.run("fig1")
    s.save(OUT / "01-traversal-orders.svg")


# ---------------------------------------------------------------- figure 2
def fig2():
    global bad
    s = Svg(1080, 430)
    c = Check(s)
    s.text(36, 40, "traverse 指针的游走序列:每个节点被进入一次、离开一次,顺序与插在哪无关",
           size=17, fill=INK, anchor="start", weight="600")
    c.text("title", 36, 40, "traverse 指针的游走序列:每个节点被进入一次、离开一次,顺序与插在哪无关", 17, "start")

    walk = [(f"{v}前", "pre") for v in ()]
    walk = []
    for v, k in [(1, "前"), (2, "前"), (4, "前"), (4, "中"), (4, "后"), (2, "中"),
                 (5, "前"), (5, "中"), (5, "后"), (2, "后"), (1, "中"),
                 (3, "前"), (6, "前"), (6, "中"), (6, "后"), (3, "中"),
                 (7, "前"), (7, "中"), (7, "后"), (3, "后"), (1, "后")]:
        walk.append((f"{v}{k}", {"前": "pre", "中": "in", "后": "post"}[k]))
    l1txt = f"① 游走序列:共 {len(walk)} 次事件(空指针返回已省略;同一节点出现两次——进去一次、离开一次)"
    s.label(36, 72, l1txt, size=13, fill=MUTED)
    c.text("l1", 36, 72, l1txt, 13, "start")
    chips(s, c, 36, 84, walk, w=46, h=28, tag="walk")

    s.label(36, 162, "② 从游走序列里「按位置筛选」,就得到三种遍历结果",
            size=13, fill=MUTED)
    c.text("l2", 36, 162, "② 从游走序列里「按位置筛选」,就得到三种遍历结果", 13, "start")

    picks = [
        ("前序:只取「前」", [(f"{v}", "pre") for v in [1, 2, 4, 5, 3, 6, 7]], BLUE),
        ("中序:只取「中」", [(f"{v}", "in") for v in [4, 2, 5, 1, 6, 3, 7]], WARM_TXT),
        ("后序:只取「后」", [(f"{v}", "post") for v in [4, 5, 2, 6, 7, 3, 1]], TEAL_TXT),
    ]
    for k, (name, items, col) in enumerate(picks):
        y = 182 + k * 48
        s.label(36, y + 18, name, size=12, fill=col, weight="600")
        c.text(f"p{k}", 36, y + 18, name, 12, "start")
        chips(s, c, 210, y, items, w=44, h=28, gap=6, tag=f"pk{k}")

    s.label(36, 372, "前/中/后序不是三套遍历算法,而是同一趟游走里三个固定的时刻;所谓「计算前序遍历结果」", size=12)
    c.text("f1", 36, 372, "前/中/后序不是三套遍历算法,而是同一趟游走里三个固定的时刻;所谓「计算前序遍历结果」", 12, "start")
    s.label(36, 392, "只是把「往结果里塞一个值」这句话放在了「前」这个时刻而已。", size=12)
    c.text("f2", 36, 392, "只是把「往结果里塞一个值」这句话放在了「前」这个时刻而已。", 12, "start")
    bad += c.run("fig2")
    s.save(OUT / "02-traverse-walk.svg")


# ---------------------------------------------------------------- figure 3
def fig3():
    global bad
    s = Svg(1080, 470)
    c = Check(s)
    s.text(36, 40, "层序遍历的三种写法:差别不在遍历顺序,而在「每个节点随身带了多少信息」",
           size=17, fill=INK, anchor="start", weight="600")
    c.text("title", 36, 40, "层序遍历的三种写法:差别不在遍历顺序,而在「每个节点随身带了多少信息」", 17, "start")

    panels = [
        ("写法一", "一个队列,取队头、把左右孩子入队",
         ["能:一层一层从左到右", "不能:不知道当前是第几层", "代码最短,但用得最少"],
         FILL_GREY, MUTED),
        ("写法二(最常用)", "先存 sz = q.size(),再循环 sz 次",
         ["能:知道每层的分界和层号", "关键:sz 必须在循环前存下来", "不能:同一层节点的权重不同时失效"],
         FILL_BLUE, BLUE),
        ("写法三", "每个节点自带 State{node, depth}",
         ["能:每节点携带自己的路径权重和", "适用:边权不是 1 的多源 BFS / Dijkstra", "代价:要多定义一个 State"],
         FILL_TEAL, TEAL_TXT),
    ]
    for k, (name, code, notes, fill, col) in enumerate(panels):
        x = 30 + k * 348
        s.panel(x, 66, 328, 250, fill=CANVAS)
        c.panel(f"pn{k}", x, 66, 328, 250)
        s.rect(x + 14, 80, 300, 40, fill=fill, stroke=fill, rx=7)
        s.text(x + 164, 105, name, size=15, fill=col, weight="600")
        c.text(f"nm{k}", x + 164, 105, name, 15)
        s.label(x + 14, 142, code, size=12, fill=INK)
        c.text(f"cd{k}", x + 14, 142, code, 12, "start")
        for j, note in enumerate(notes):
            y = 176 + j * 34
            s.text(x + 22, y, "·", size=12, fill=col, anchor="start")
            s.label(x + 34, y, note, size=12)
            c.text(f"nt{k}{j}", x + 34, y, note, 12, "start")
        s.label(x + 14, 300, {"0": "queue: 1 → 2,3 → 4,5,6,7",
                              "1": "sz: 1 → 2 → 4",
                              "2": "State.depth: 1 → 2 → 3"}[str(k)],
                size=11, fill=MUTED)

    s.label(36, 348, "同一棵树上的队列演化(写法二):q=[1] → 取 1、入 2,3 → q=[2,3] → 取 2,3、入 4,5,6,7 → q=[4,5,6,7] → q=[]",
            size=12, fill=INK)
    c.text("evo", 36, 348, "同一棵树上的队列演化(写法二):q=[1] → 取 1、入 2,3 → q=[2,3] → 取 2,3、入 4,5,6,7 → q=[4,5,6,7] → q=[]", 12, "start")

    s.label(36, 386, "写法二的 sz 如果不预存,直接写 while q: sz = len(q) 或 for i in range(len(q)),队列在循环里一边出队一边入队,", size=12)
    c.text("w1", 36, 386, "写法二的 sz 如果不预存,直接写 while q: sz = len(q) 或 for i in range(len(q)),队列在循环里一边出队一边入队,", 12, "start")
    s.label(36, 406, "长度会变,一层就切不干净——这是这三种写法里最常见的一个 bug。", size=12)
    c.text("w2", 36, 406, "长度会变,一层就切不干净——这是这三种写法里最常见的一个 bug。", 12, "start")
    bad += c.run("fig3")
    s.save(OUT / "03-bfs-three-ways.svg")


# ---------------------------------------------------------------- figure 4
def fig4():
    global bad
    s = Svg(1080, 430)
    c = Check(s)
    s.text(36, 40, "前中后序位置的能力依次增强:能拿到的信息越来越多",
           size=17, fill=INK, anchor="start", weight="600")
    c.text("title", 36, 40, "前中后序位置的能力依次增强:能拿到的信息越来越多", 17, "start")

    rows = [
        ("前序位置", "函数参数(父节点传下来的)", "打印每个节点的层数", FILL_BLUE, BLUE),
        ("中序位置", "+ 左子树通过返回值传回来的", "BST 场景:中序结果有序", FILL_WARM, WARM_TXT),
        ("后序位置", "+ 左右子树通过返回值传回来的", "543 直径 / 110 平衡 / 124 最大路径和", FILL_TEAL, TEAL_TXT),
    ]
    for k, (pos, info, use, fill, col) in enumerate(rows):
        y = 78 + k * 96
        s.rect(36, y, 240, 74, fill=fill, stroke=fill, rx=8)
        s.text(156, y + 32, pos, size=15, fill=col, weight="600")
        c.text(f"p{k}", 156, y + 32, pos, 15)
        s.text(156, y + 56, f"能力 {k + 1} 档", size=11, fill=col)
        c.text(f"a{k}", 156, y + 56, f"能力 {k + 1} 档", 11)
        s.label(300, y + 30, "能看到:" + info, size=13, fill=INK)
        c.text(f"i{k}", 300, y + 30, "能看到:" + info, 13, "start")
        s.label(300, y + 56, "典型题:" + use, size=12, fill=MUTED)
        c.text(f"u{k}", 300, y + 56, "典型题:" + use, 12, "start")
        if k < 2:
            s.arrow(156, y + 78, 156, y + 94, stroke=col)

    s.label(36, 376, "根本区别在信息的来源:参数是「别人给你」的,返回值是「子树算完给你」的。", size=12)
    c.text("f1", 36, 376, "根本区别在信息的来源:参数是「别人给你」的,返回值是「子树算完给你」的。", 12, "start")
    s.label(36, 396, "所以判断标准很简单:如果一道题要用的信息「子树算完才知道」,那就只能放在后序位置。", size=12)
    c.text("f2", 36, 396, "所以判断标准很简单:如果一道题要用的信息「子树算完才知道」,那就只能放在后序位置。", 12, "start")
    bad += c.run("fig4")
    s.save(OUT / "04-post-order-power.svg")


# ---------------------------------------------------------------- figure 5
def fig5():
    global bad
    s = Svg(1080, 440)
    c = Check(s)
    s.text(36, 40, "为什么「递归里套递归」是危险信号:一条 5 节点的链,深度被重算了 10 次",
           size=17, fill=INK, anchor="start", weight="600")
    c.text("title", 36, 40, "为什么「递归里套递归」是危险信号:一条 5 节点的链,深度被重算了 10 次", 17, "start")

    # left: the naive version, with per-node recomputation counts
    s.label(36, 76, "朴素版:每个节点都重新算一遍左右子树的深度", size=13, fill=WARM_TXT, weight="600")
    c.text("lh", 36, 76, "朴素版:每个节点都重新算一遍左右子树的深度", 13, "start")
    rows = layout(60, 116, 220, 54, CHAIN)
    draw_tree(s, c, rows, r=18, node_fill=FILL_WARM, tag="ch")
    counts = {2: 1, 3: 2, 4: 3, 5: 4}
    for d in range(1, 5):
        cx, cy, v = rows[d][0]
        badge(s, c, cx + 44, cy + 4, f"×{counts[v]}", f"cc{d}")
    s.label(36, 380, "节点 5 的深度被算了 4 次", size=12, fill=WARM_TXT)
    c.text("ln1", 36, 380, "节点 5 的深度被算了 4 次", 12, "start")
    s.label(36, 400, "n 个节点共 1+2+…+(n−1) = n(n−1)/2 次 → O(N²)", size=12, fill=INK)
    c.text("ln2", 36, 400, "n 个节点共 1+2+…+(n−1) = n(n−1)/2 次 → O(N²)", 12, "start")

    # right: the one-pass version
    s.label(560, 76, "后序版:一趟递归,在后序位置顺便算直径", size=13, fill=TEAL_TXT, weight="600")
    c.text("rh", 560, 76, "后序版:一趟递归,在后序位置顺便算直径", 13, "start")
    rows2 = layout(600, 116, 220, 54, CHAIN)
    draw_tree(s, c, rows2, r=18, node_fill=FILL_TEAL, tag="c2")
    for d in range(0, 5):
        cx, cy, _v = rows2[d][0]
        badge(s, c, cx + 44, cy + 4, "×1", f"dd{d}", fill=TEAL_TXT)
    s.label(560, 380, "每个节点的深度只算 1 次", size=12, fill=TEAL_TXT)
    c.text("rn1", 560, 380, "每个节点的深度只算 1 次", 12, "start")
    s.label(560, 400, "n 个节点共 n 次 → O(N)", size=12, fill=INK)
    c.text("rn2", 560, 400, "n 个节点共 n 次 → O(N)", 12, "start")

    s.arrow(470, 220, 520, 220, stroke=MUTED)
    c.arrow("mid", 470, 220, 520, 220)
    s.label(36, 428, "两边的代码只差一件事:算直径的那一行,是写在「另一个递归函数」里,还是写在本函数的后序位置。", size=12)
    c.text("f1", 36, 428, "两边的代码只差一件事:算直径的那一行,是写在「另一个递归函数」里,还是写在本函数的后序位置。", 12, "start")
    bad += c.run("fig5")
    s.save(OUT / "05-diameter-two-ways.svg")


def main():
    global bad
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()

    import xml.dom.minidom
    for f in sorted(OUT.glob("*.svg")):
        try:
            xml.dom.minidom.parse(str(f))
        except Exception as exc:                       # noqa: BLE001
            print(f"  !! {f.name} is not well-formed XML: {exc}")
            bad += 1
        else:
            print(f"  ok {f.name}: parses as XML")
    print(f"\n  layout problems: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
