#!/usr/bin/env python3
"""Generate the four diagrams for the binary-search post.

Every text label is registered with `Check` so the run fails loudly if a
label escapes the canvas or collides with another label.  Check cannot see
labels sitting on top of unregistered lines, so the rendered PNGs were also
inspected by eye (see README.md in this directory).

Usage: python3 make_figures.py
"""
import sys
from pathlib import Path

REPO = Path.home() / "projects/linear3735.github.io"
sys.path.insert(0, str(REPO / "assets/blog/_tools"))
from svgkit import Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS, \
    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY, WARM_TXT, TEAL_TXT   # noqa: E402

OUT = REPO / "assets/img/binary-search-20261115"
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


def array_row(svg, chk, x0, y0, cw, ch, vals, fill_of=None, tag="c"):
    """Draw an array with index labels underneath.  Returns left/right edge."""
    fill_of = fill_of or {}
    for i, v in enumerate(vals):
        cx = x0 + i * cw
        svg.cell(cx, y0, cw, ch, str(v), fill=fill_of.get(i, PAPER))
        T(svg, chk, f"{tag}i{i}", cx + cw / 2, y0 + ch + 16, str(i),
          size=11, fill=MUTED)
    return x0, x0 + len(vals) * cw


# ---------------------------------------------------------------- figure 1
def fig_interval():
    W, H = 900, 400
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 32,
      "同一个数组,两种搜索区间:差别只在 right 指向哪", size=17, weight="600")

    vals = [1, 3, 5, 7, 9, 11]
    cw, ch = 66, 46
    x0 = 150.0
    n = len(vals)

    # ---- top: closed-closed
    y = 82
    T(svg, chk, "t1", 138, y + ch / 2 + 5, "两端都闭", size=13,
      fill=BLUE, anchor="end", weight="600")
    T(svg, chk, "t1b", 138, y + ch / 2 + 24, "right = n - 1 = 5", size=11,
      fill=MUTED, anchor="end")
    array_row(svg, chk, x0, y, cw, ch, vals, tag="a")
    # bracket over the whole closed range
    xl, xr = x0, x0 + n * cw
    svg.line(xl, y - 12, xr, y - 12, stroke=BLUE, sw=2)
    svg.line(xl, y - 18, xl, y - 6, stroke=BLUE, sw=2)
    svg.line(xr, y - 18, xr, y - 6, stroke=BLUE, sw=2)
    T(svg, chk, "t1c", (xl + xr) / 2, y - 22,
      "搜索区间 [left, right] = [0, 5],右端是元素 11 本身", size=12,
      fill=BLUE)
    T(svg, chk, "t1d", xr + 14, y + ch / 2 + 5, "right", size=12, fill=BLUE,
      anchor="start")

    # ---- bottom: half open
    y2 = 236
    T(svg, chk, "t2", 138, y2 + ch / 2 + 5, "左闭右开", size=13, fill=TEAL_TXT,
      anchor="end", weight="600")
    T(svg, chk, "t2b", 138, y2 + ch / 2 + 24, "right = n = 6", size=11,
      fill=MUTED, anchor="end")
    array_row(svg, chk, x0, y2, cw, ch, vals, tag="b")
    # ghost cell for the out-of-range position n
    svg.rect(x0 + n * cw, y2, cw, ch, fill=CANVAS, stroke=MUTED, rx=0, sw=1.4,
             dash="4 3")
    T(svg, chk, "ghost", x0 + n * cw + cw / 2, y2 + ch / 2 + 5, "越界位",
      size=12, fill=MUTED)
    T(svg, chk, "ghosti", x0 + n * cw + cw / 2, y2 + ch + 16, "6", size=11,
      fill=MUTED)
    xl2, xr2 = x0, x0 + n * cw
    svg.line(xl2, y2 - 12, xr2, y2 - 12, stroke=TEAL_TXT, sw=2)
    svg.line(xl2, y2 - 18, xl2, y2 - 6, stroke=TEAL_TXT, sw=2)
    svg.line(xr2, y2 - 18, xr2, y2 - 6, stroke=TEAL_TXT, sw=2)
    T(svg, chk, "t2c", (xl2 + xr2) / 2, y2 - 22,
      "搜索区间 [left, right) = [0, 6),右端只是一个位置,不是元素", size=12,
      fill=TEAL_TXT)
    T(svg, chk, "t2d", xr2 + cw + 14, y2 + ch / 2 + 5, "right", size=12,
      fill=TEAL_TXT, anchor="start")

    # ---- takeaway box
    svg.panel(28, 330, W - 56, 50)
    chk.panel("takeaway", 28, 330, W - 56, 50)
    T(svg, chk, "k1", 48, 361,
      "区间为空的判据:闭区间是 left > right,左闭右开是 left >= right",
      size=12.5, anchor="start")
    T(svg, chk, "k2", 560, 361,
      "→ while 条件只能跟着区间走", size=12.5, anchor="start",
      fill=WARM_TXT, weight="600")

    svg.save(OUT / "01-search-interval.svg")
    return chk.run("01-search-interval")


# ---------------------------------------------------------------- figure 2
def fig_bounds():
    W, H = 900, 420
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 30,
      "left_bound 与 right_bound 在同一根坐标轴上", size=17, weight="600")

    cw, ch = 62, 44

    # ---- case A: target present
    vals = [1, 2, 2, 2, 3]
    x0, y = 250.0, 74
    T(svg, chk, "a1", 238, y + ch / 2 + 5, "nums = [1,2,2,2,3]", size=12,
      anchor="end")
    T(svg, chk, "a2", 238, y + ch / 2 + 24, "target = 2", size=12,
      fill=MUTED, anchor="end")
    fill_of = {i: FILL_WARM for i in (1, 2, 3)}
    array_row(svg, chk, x0, y, cw, ch, vals, fill_of=fill_of, tag="A")

    # left_bound = 1 above, right_bound = 3 below
    lx = x0 + 1 * cw
    rx = x0 + 4 * cw
    svg.line(lx, y - 18, lx, y - 40, stroke=BLUE, sw=1.6)
    svg.arrow(lx, y - 40, lx, y - 20, stroke=BLUE, sw=1.6, head=6)
    T(svg, chk, "A_lb", lx + 8, y - 26,
      "left_bound = 1 (第一个 >= target)", size=12, fill=BLUE, anchor="start")

    T(svg, chk, "A_rb", rx + 8, y + ch + 40,
      "right_bound = 3 (最后一个 <= target)", size=12, fill=TEAL_TXT,
      anchor="start")
    svg.line(rx, y + ch + 18, rx, y + ch + 34, stroke=TEAL_TXT, sw=1.6)
    svg.arrow(rx, y + ch + 34, rx, y + ch + 20, stroke=TEAL_TXT, sw=1.6,
              head=6)

    T(svg, chk, "A_span", (lx + rx) / 2, y + ch + 40,
      "target 占据 [1, 3],出现 3 次", size=12, fill=WARM_TXT)

    # ---- case B: target missing
    vals2 = [2, 3, 5, 7]
    x02, y2 = 250.0, 250
    T(svg, chk, "b1", 238, y2 + ch / 2 + 5, "nums = [2,3,5,7]", size=12,
      anchor="end")
    T(svg, chk, "b2", 238, y2 + ch / 2 + 24, "target = 4", size=12,
      fill=MUTED, anchor="end")
    array_row(svg, chk, x02, y2, cw, ch, vals2, tag="B")

    lb2 = x02 + 2 * cw
    rb2 = x02 + 2 * cw
    svg.line(lb2, y2 - 18, lb2, y2 - 40, stroke=BLUE, sw=1.6)
    svg.arrow(lb2, y2 - 40, lb2, y2 - 20, stroke=BLUE, sw=1.6, head=6)
    T(svg, chk, "B_lb", lb2 + 8, y2 - 26, "left_bound = 2", size=12, fill=BLUE,
      anchor="start")
    svg.line(rb2, y2 + ch + 18, rb2, y2 + ch + 34, stroke=TEAL_TXT, sw=1.6)
    svg.arrow(rb2, y2 + ch + 34, rb2, y2 + ch + 20, stroke=TEAL_TXT, sw=1.6,
              head=6)
    T(svg, chk, "B_rb", rb2 + 8, y2 + ch + 40, "right_bound = 1", size=12,
      fill=TEAL_TXT, anchor="start")

    T(svg, chk, "B_note", x02 + 4 * cw + 16, y2 + ch / 2 + 5,
      "right_bound < left_bound => 不存在", size=12, fill=WARM_TXT,
      anchor="start")

    svg.panel(28, 348, W - 56, 52)
    chk.panel("tk", 28, 348, W - 56, 52)
    T(svg, chk, "k1", 48, 380,
      "两种写法返回的是同一个坐标系里的两条界线:", size=12.5, anchor="start")
    T(svg, chk, "k2", 420, 380,
      "left_bound 永远是 lower_bound,right_bound 永远是 upper_bound - 1",
      size=12.5, anchor="start", fill=WARM_TXT, weight="600")

    svg.save(OUT / "02-bound-semantics.svg")
    return chk.run("02-bound-semantics")


# ---------------------------------------------------------------- figure 3
def fig_answer():
    W, H = 900, 400
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 30,
      "二分答案:在值域上找一个单调谓词的翻转点", size=17, weight="600")

    # value axis
    n = 9
    cw, ch = 74, 48
    x0, y = 150.0, 92
    T(svg, chk, "ax", 138, y + ch / 2 + 5, "候选值 x", size=13, fill=BLUE,
      anchor="end", weight="600")
    for i in range(n):
        cx = x0 + i * cw
        ok = i >= 4
        svg.cell(cx, y, cw, ch, str(i + 1),
                 fill=(FILL_TEAL if ok else FILL_GREY))
    T(svg, chk, "lo", x0, y + ch + 18, "lo = 1", size=11, fill=MUTED)
    T(svg, chk, "hi", x0 + n * cw, y + ch + 18, "hi = 9 (开区间上界)", size=11,
      fill=MUTED)

    # verdict row
    yv = y + ch + 40
    T(svg, chk, "vv", 138, yv + 5, "feasible(x)", size=12, fill=MUTED,
      anchor="end")
    for i in range(n):
        cx = x0 + i * cw
        ok = i >= 4
        svg.rect(cx, yv - 12, cw, 26, fill=PAPER, stroke=LINE, rx=0, sw=1.2)
        T(svg, chk, f"v{i}", cx + cw / 2, yv + 6,
          "true" if ok else "false", size=11,
          fill=(TEAL_TXT if ok else MUTED))

    # the flip point
    fx = x0 + 4 * cw
    svg.line(fx, yv + 26, fx, yv + 62, stroke=WARM_TXT, sw=1.8)
    svg.arrow(fx, yv + 62, fx, yv + 30, stroke=WARM_TXT, sw=1.8, head=7)
    T(svg, chk, "flip", fx + 10, yv + 48,
      "第一个 true 就是答案:x = 5", size=13, fill=WARM_TXT, anchor="start",
      weight="600")

    T(svg, chk, "left", x0 + 1.6 * cw, yv + 92, "false 区", size=12,
      fill=MUTED)
    T(svg, chk, "right", x0 + 6.5 * cw, yv + 92, "true 区", size=12,
      fill=TEAL_TXT)

    svg.panel(28, 300, W - 56, 84)
    chk.panel("code", 28, 300, W - 56, 84)
    T(svg, chk, "c1", 48, 328,
      "while lo < hi:   mid = lo + (hi - lo) // 2", size=12.5, anchor="start",
      weight="600")
    T(svg, chk, "c2", 48, 352,
      "if feasible(mid):  hi = mid        # 可行 → 答案在 mid 或更左",
      size=12.5, anchor="start", fill=TEAL_TXT)
    T(svg, chk, "c3", 48, 374,
      "else:              lo = mid + 1    # 不可行 → 答案一定在右边",
      size=12.5, anchor="start", fill=WARM_TXT)

    svg.save(OUT / "03-binary-search-answer.svg")
    return chk.run("03-binary-search-answer")


# ---------------------------------------------------------------- figure 4
def fig_prefix():
    W, H = 900, 424
    svg = Svg(W, H)
    chk = Check(svg)
    T(svg, chk, "title", W / 2, 30,
      "前缀和 + 二分:每个下标占据一段长度等于权重的区间", size=17,
      weight="600")

    w = [1, 3, 2, 4]
    prefix = [0, 1, 4, 6, 10]
    total = 10
    fills = [FILL_BLUE, FILL_TEAL, FILL_WARM, FILL_GREY]
    txts = [BLUE, TEAL_TXT, WARM_TXT, MUTED]

    # ---- weight row
    cw, ch = 90, 44
    x0, y = 120.0, 64
    T(svg, chk, "wl", 108, y + ch / 2 + 5, "w", size=13, anchor="end",
      weight="600")
    for i, v in enumerate(w):
        svg.cell(x0 + i * cw, y, cw, ch, str(v), fill=fills[i])
        T(svg, chk, f"wi{i}", x0 + i * cw + cw / 2, y + ch + 16, f"下标 {i}",
          size=11, fill=MUTED)

    # ---- prefix row
    y2 = 166
    T(svg, chk, "pl", 108, y2 + ch / 2 + 5, "prefix", size=13, anchor="end",
      weight="600")
    for i, v in enumerate(prefix):
        svg.cell(x0 + i * cw, y2, cw, ch, str(v), fill=CANVAS)
        T(svg, chk, f"pi{i}", x0 + i * cw + cw / 2, y2 + ch + 16, f"j = {i}",
          size=11, fill=MUTED)

    # ---- number line, drawn at real scale so segment length == weight
    y3 = 300
    ax0, ax1 = x0, x0 + 5 * cw
    scale = (ax1 - ax0) / total
    T(svg, chk, "nll", 108, y3 + 5, "区间", size=13, anchor="end", weight="600")
    for i in range(4):
        a = ax0 + prefix[i] * scale
        b = ax0 + prefix[i + 1] * scale
        svg.rect(a, y3 - 18, b - a, 36, fill=fills[i], stroke=PAPER, rx=0,
                 sw=1.6)
        T(svg, chk, f"seg{i}", (a + b) / 2, y3 + 6, str(i), size=13,
          fill=txts[i], weight="600")
    for p in prefix:
        px = ax0 + p * scale
        svg.line(px, y3 + 20, px, y3 + 32, stroke=MUTED, sw=1.2)
        T(svg, chk, f"tick{p}", px, y3 + 48, str(p), size=11, fill=MUTED)

    # ---- the random point t = 5, marked above the bar so it never covers a digit
    tx = ax0 + 5 * scale
    svg.circle(tx, y3 - 32, 4.5, fill=WARM_TXT, stroke=WARM_TXT, sw=1)
    svg.line(tx, y3 - 27, tx, y3 - 19, stroke=WARM_TXT, sw=2)
    T(svg, chk, "tlab", tx + 12, y3 - 26,
      "t = 5 均匀取自 [0, 10),落在下标 2 这一段", size=12, fill=WARM_TXT,
      anchor="start")

    T(svg, chk, "formula", W / 2, 376,
      "bisect_right(prefix, 5) - 1 = 3 - 1 = 2   =>   返回下标 2", size=13.5,
      weight="600")
    T(svg, chk, "proof", W / 2, 398,
      "P(返回 i) = 区间长度 / total = w[i] / sum(w)", size=12, fill=MUTED)

    svg.save(OUT / "04-prefix-weight.svg")
    return chk.run("04-prefix-weight")


if __name__ == "__main__":
    bad = 0
    for fn in (fig_interval, fig_bounds, fig_answer, fig_prefix):
        bad += fn()
    print(f"\n  {'ALL FIGURES CLEAN' if not bad else str(bad) + ' problem(s)'}")
    sys.exit(1 if bad else 0)
