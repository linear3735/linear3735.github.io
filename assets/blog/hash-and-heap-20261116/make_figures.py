#!/usr/bin/env python3
"""Generate the three diagrams for the hash-and-heap / tree-index post.

Every text label is registered with `Check` so the run fails loudly if a
label escapes the canvas or collides with another label.  Check cannot see
labels sitting on top of unregistered lines or circles, so the rendered PNGs
were also inspected by eye (see README.md in this directory).

Usage: python3 make_figures.py
"""
import sys
from pathlib import Path

REPO = Path.home() / "projects/linear3735.github.io"
sys.path.insert(0, str(REPO / "assets/blog/_tools"))
from svgkit import Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS, \
    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY, WARM_TXT, TEAL_TXT   # noqa: E402

OUT = REPO / "assets/img/hash-and-heap-20261116"
OUT.mkdir(parents=True, exist_ok=True)


def T(svg, chk, name, x, y, t, size=14, fill=INK, anchor="middle",
      weight="400"):
    """Draw a text and register the same box with the checker.

    `svgkit.text()` already XML-escapes its content (see the note in
    svgkit.py), so the string is passed through verbatim here.  Escaping it
    again would emit `&amp;gt;` and the diagram would literally show `&gt;` —
    which is exactly the bug this helper used to have.
    """
    svg.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    chk.text(name, x, y, t, size=size, anchor=anchor)


# ---------------------------------------------------------------- figure 1
def fig_trie():
    W, H = 900, 590
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 32,
      "Trie:把字符串摊成路径,公共前缀变成共享的边", size=17, weight="600")

    R = 16

    def node(name, x, y, ch, end):
        """A trie node.  Filled = isEnd true, hollow = isEnd false."""
        fill = FILL_WARM if end else PAPER
        stroke = WARM_TXT if end else INK
        svg.circle(x, y, R, fill=fill, stroke=stroke, sw=1.8)
        T(svg, chk, name, x, y + 5, ch, size=13,
          fill=(WARM_TXT if end else INK), weight="600")

    def edge(x1, y1, x2, y2, warm=False):
        # shorten both ends by the radius so the line stops at the circle
        dx, dy = x2 - x1, y2 - y1
        d = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / d, dy / d
        svg.line(x1 + ux * R, y1 + uy * R, x2 - ux * R, y2 - uy * R,
                 stroke=(WARM_TXT if warm else LINE), sw=(2.2 if warm else 1.6))

    # ---- layout: root on the left, one column per character of the key
    root = (70.0, 240.0)
    nodes = {
        "a":  (210.0, 120.0), "p1": (330.0, 120.0), "p2": (450.0, 120.0),
        "l":  (570.0, 120.0), "e":  (690.0, 120.0),
        "t":  (210.0, 350.0), "h":  (330.0, 350.0),
        "a2": (450.0, 280.0), "t2": (570.0, 280.0),
        "e2": (450.0, 420.0), "m":  (570.0, 420.0),
    }
    ends = {"p2", "l", "e", "t2", "e2", "m"}
    chars = {"a": "a", "p1": "p", "p2": "p", "l": "l", "e": "e",
             "t": "t", "h": "h", "a2": "a", "t2": "t", "e2": "e", "m": "m"}
    parents = {"a": root, "p1": nodes["a"], "p2": nodes["p1"],
               "l": nodes["p2"], "e": nodes["l"],
               "t": root, "h": nodes["t"], "a2": nodes["h"],
               "t2": nodes["a2"], "e2": nodes["h"], "m": nodes["e2"]}

    for k, (x, y) in nodes.items():
        px, py = parents[k]
        edge(px, py, x, y, warm=(k == "h"))
    for x, y in (root,):
        svg.circle(x, y, R, fill=FILL_GREY, stroke=INK, sw=1.8)
        T(svg, chk, "root", x, y + 5, "•", size=16, weight="600")

    for k, (x, y) in nodes.items():
        node("n_" + k, x, y, chars[k], k in ends)

    # ---- which keys end where
    word_at = [("w_p2", "p2", "app", 34), ("w_l", "l", "appl", 34),
               ("w_e", "e", "apple", 34), ("w_t2", "t2", "that", -24),
               ("w_e2", "e2", "the", 30), ("w_m", "m", "them", 30)]
    for nm, key, word, dy in word_at:
        wx, wy = nodes[key]
        T(svg, chk, nm, wx, wy + dy, word, size=11, fill=WARM_TXT)

    # ---- the interesting node: "th" is a real path but not a key
    hx, hy = nodes["h"]
    T(svg, chk, "thnote", hx - 6, hy - 30,
      "\"th\" 走得通,但 isEnd = false", size=11.5, fill=BLUE, anchor="middle")

    # ---- legend
    svg.circle(648, 64, 10, fill=FILL_WARM, stroke=WARM_TXT, sw=1.8)
    T(svg, chk, "lg1", 664, 69, "isEnd = true", size=11.5, fill=WARM_TXT,
      anchor="start")
    svg.circle(648, 92, 10, fill=PAPER, stroke=INK, sw=1.8)
    T(svg, chk, "lg2", 664, 97, "isEnd = false", size=11.5, fill=INK,
      anchor="start")

    # ---- two takeaways
    svg.panel(28, 468, W - 56, 106)
    chk.panel("tk", 28, 468, W - 56, 106)
    T(svg, chk, "k1", 48, 494,
      "省内存:HashMap 真的存了 \"apple\"、\"app\"、\"appl\" 三个字符串,占 12 个字符;",
      size=12.5, anchor="start")
    T(svg, chk, "k1b", 48, 514,
      "Trie 不重复存公共前缀,只需要 \"apple\" 这 5 个字符。",
      size=12.5, anchor="start", fill=TEAL_TXT, weight="600")
    T(svg, chk, "k2", 48, 542,
      "前缀查询:hasKeyWithPrefix(\"tha\") 只需要沿 t → h → a 走通,"
      "不必枚举表里所有的键;", size=12.5, anchor="start")
    T(svg, chk, "k2b", 48, 562,
      "而 search(\"th\") 必须是「走得通」且「isEnd」两条同时成立。",
      size=12.5, anchor="start", fill=WARM_TXT, weight="600")

    svg.save(OUT / "01-trie-structure.svg")
    return chk.run("01-trie-structure")


# ---------------------------------------------------------------- figure 2
def fig_segtree():
    W, H = 900, 580
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 30,
      "线段树:查询 [1, 6] 只用到 4 个节点,而不是 6 个叶子", size=17,
      weight="600")

    # canonical decomposition of [1, 6] over 8 leaves
    cover = {"[1]", "[2,3]", "[4,5]", "[6]"}
    leaves_x = [70.0 + i * 100 for i in range(8)]
    lvl_y = {0: 72.0, 1: 146.0, 2: 220.0, 3: 294.0}
    bw, bh = 76.0, 30.0

    def seg_x(l, r):
        return (leaves_x[l] + leaves_x[r]) / 2

    boxes = {
        "[0,7]": (seg_x(0, 7), lvl_y[0]),
        "[0,3]": (seg_x(0, 3), lvl_y[1]), "[4,7]": (seg_x(4, 7), lvl_y[1]),
        "[0,1]": (seg_x(0, 1), lvl_y[2]), "[2,3]": (seg_x(2, 3), lvl_y[2]),
        "[4,5]": (seg_x(4, 5), lvl_y[2]), "[6,7]": (seg_x(6, 7), lvl_y[2]),
    }
    for i in range(8):
        boxes[f"[{i}]"] = (leaves_x[i], lvl_y[3])

    edges = [("[0,7]", "[0,3]"), ("[0,7]", "[4,7]"),
             ("[0,3]", "[0,1]"), ("[0,3]", "[2,3]"),
             ("[4,7]", "[4,5]"), ("[4,7]", "[6,7]")]
    for i in range(8):
        par = ("[0,1]" if i < 2 else "[2,3]" if i < 4 else
               "[4,5]" if i < 6 else "[6,7]")
        edges.append((par, f"[{i}]"))

    for p, c in edges:
        px, py = boxes[p]
        cx, cy = boxes[c]
        svg.line(px, py + bh / 2, cx, cy - bh / 2, stroke=LINE, sw=1.6)

    # nodes present in the tree (7 internal + 8 leaves), drawn after the edges
    for name, (x, y) in boxes.items():
        hot = name in cover
        svg.rect(x - bw / 2, y - bh / 2, bw, bh,
                 fill=(FILL_TEAL if hot else PAPER),
                 stroke=(TEAL_TXT if hot else LINE), rx=6, sw=(2.0 if hot else 1.4))
        T(svg, chk, "t" + name, x, y + 4.5, name, size=12,
          fill=(TEAL_TXT if hot else MUTED), weight=("600" if hot else "400"))

    T(svg, chk, "lvl", 34, lvl_y[3] + 46, "叶子 = 单个元素", size=11.5,
      fill=MUTED, anchor="start")
    T(svg, chk, "lvltop", 34, lvl_y[0] + 4, "根 = 整个区间", size=11.5,
      fill=MUTED, anchor="start")

    # ---- the array itself
    ay = 386.0
    cw, ch = 100.0, 40.0
    T(svg, chk, "arrlab", 34, ay + ch / 2 + 5, "nums", size=12.5, anchor="start",
      weight="600")
    for i in range(8):
        hot = 1 <= i <= 6
        svg.cell(leaves_x[i] - cw / 2, ay, cw, ch, str((i + 1) * 10),
                 fill=(FILL_TEAL if hot else FILL_GREY))
        T(svg, chk, f"ai{i}", leaves_x[i], ay + ch + 16, str(i), size=11,
          fill=MUTED)
    T(svg, chk, "arrq", W / 2, ay + ch + 40,
      "查询区间 [1, 6] 覆盖 6 个元素,但树上只需要合并 4 个节点", size=12.5,
      weight="600")

    # ---- merge / identity takeaway
    svg.panel(28, 490, W - 56, 66)
    chk.panel("tk", 28, 490, W - 56, 66)
    T(svg, chk, "m1", 48, 516,
      "求和:merge = a + b,区间外返回的单位元 identity = 0", size=12.5,
      anchor="start", fill=TEAL_TXT)
    T(svg, chk, "m2", 48, 538,
      "求最值:merge = max(a, b),identity 必须是负无穷而不能是 0"
      " —— 否则全是负数的区间会查错", size=12.5, anchor="start", fill=WARM_TXT)

    svg.save(OUT / "02-segtree-interval.svg")
    return chk.run("02-segtree-interval")


# ---------------------------------------------------------------- figure 3
def fig_skiplist():
    W, H = 900, 520
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 30,
      "跳表:多层索引 + 抛硬币决定层数,期望 O(log n)", size=17, weight="600")

    vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    x0, x1 = 150.0, 830.0
    xs = {v: x0 + (v - 10) / 90.0 * (x1 - x0) for v in vals}
    head_x = 96.0
    lvl_y = {3: 92.0, 2: 166.0, 1: 240.0, 0: 322.0}
    present = {3: [40], 2: [40, 80], 1: [20, 40, 60, 80, 100], 0: vals}

    R = 13.0
    CH_W, CH_H = 62.0, 30.0

    # ---- horizontal chains
    for lv in (3, 2, 1, 0):
        y = lvl_y[lv]
        chain = [head_x] + [xs[v] for v in present[lv]]
        for a, b in zip(chain, chain[1:]):
            warm = ((lv == 3 and a == head_x and b == xs[40]) or
                    (lv == 1 and a == xs[40] and b == xs[60]) or
                    (lv == 0 and a == xs[60] and b == xs[70]))
            svg.line(a + (R if a != head_x else 12), y, b - R, y,
                     stroke=(WARM_TXT if warm else LINE), sw=(2.4 if warm else 1.6))
        # head sentinel
        svg.rect(head_x - 24, y - 13, 26, 26, fill=FILL_GREY, stroke=INK,
                 rx=5, sw=1.4)
        T(svg, chk, f"hd{lv}", head_x - 11, y + 4.5, "H", size=11.5,
          weight="600")
        T(svg, chk, f"lv{lv}", 10, y + 4.5, f"第 {lv} 层", size=11.5,
          fill=(MUTED if lv else BLUE), anchor="start",
          weight=("600" if lv == 0 else "400"))
        for v in present[lv]:
            if lv == 0:
                svg.rect(xs[v] - CH_W / 2, y - CH_H / 2, CH_W, CH_H,
                         fill=PAPER, stroke=INK, rx=6, sw=1.4)
            else:
                svg.circle(xs[v], y, R, fill=FILL_BLUE, stroke=BLUE, sw=1.6)
            col = WARM_TXT if (v in (40, 60, 70)) else INK
            T(svg, chk, f"v{lv}_{v}", xs[v], y + 4.5, str(v),
              size=(11.5 if lv == 0 else 11), fill=col,
              weight=("600" if col == WARM_TXT else "400"))

    # ---- the search path for 70: three horizontal moves and two drops
    # two segments so the dashed drop does not run through the level-2 node
    svg.line(xs[40], lvl_y[3] + R, xs[40], lvl_y[2] - R, stroke=WARM_TXT,
             sw=1.8, dash="5 4")
    svg.line(xs[40], lvl_y[2] + R, xs[40], lvl_y[1] - R, stroke=WARM_TXT,
             sw=1.8, dash="5 4")
    svg.arrow(xs[40], lvl_y[3] + R, xs[40], lvl_y[3] + R + 14, stroke=WARM_TXT,
              sw=1.8, head=6)
    svg.line(xs[60], lvl_y[1] + R, xs[60], lvl_y[0] - CH_H / 2, stroke=WARM_TXT,
             sw=1.8, dash="5 4")
    svg.arrow(xs[60], lvl_y[1] + R, xs[60], lvl_y[1] + R + 14, stroke=WARM_TXT,
              sw=1.8, head=6)

    T(svg, chk, "p1", xs[40] + 12, lvl_y[3] - 22,
      "从最高层出发:第 3 层只有 40,走到它就停", size=11.5, fill=WARM_TXT,
      anchor="start")
    T(svg, chk, "p2", xs[40] + 12, lvl_y[2] - 22,
      "第 2 层:40 的下一个 80 已经超过 70,往下掉", size=11.5, fill=WARM_TXT,
      anchor="start")
    T(svg, chk, "p3", xs[60] + 12, lvl_y[1] - 22,
      "第 1 层:40 → 60,再往右是 80,往下掉", size=11.5, fill=WARM_TXT,
      anchor="start")
    T(svg, chk, "p4", xs[70] + 12, lvl_y[0] - 24,
      "第 0 层:60 的下一个就是 70,命中", size=11.5, fill=WARM_TXT,
      anchor="start")

    # ---- takeaway
    svg.panel(28, 380, W - 56, 120)
    chk.panel("tk", 28, 380, W - 56, 120)
    T(svg, chk, "k1", 48, 406,
      "抛硬币决定层数:P(层数 >= h) = (1/2)^(h-1),所以第 h 层的期望节点数是 "
      "n / 2^(h-1)", size=12.5, anchor="start")
    T(svg, chk, "k1b", 48, 426,
      "—— 正好就是原文简化示例里「每上一层减半」的理想情况。",
      size=12.5, anchor="start", fill=TEAL_TXT, weight="600")
    T(svg, chk, "k2", 48, 454,
      "每层最多移动 2 次,一共 log n 层 => 期望 O(log n);", size=12.5,
      anchor="start")
    T(svg, chk, "k2b", 48, 474,
      "但这是期望而不是最坏:硬币全抛成反面时所有节点都在第 0 层,退化成 O(n)。",
      size=12.5, anchor="start", fill=WARM_TXT, weight="600")

    svg.save(OUT / "03-skiplist-levels.svg")
    return chk.run("03-skiplist-levels")


if __name__ == "__main__":
    bad = 0
    for fn in (fig_trie, fig_segtree, fig_skiplist):
        bad += fn()
    print(f"\n  {'ALL FIGURES CLEAN' if not bad else str(bad) + ' problem(s)'}")
    sys.exit(1 if bad else 0)
