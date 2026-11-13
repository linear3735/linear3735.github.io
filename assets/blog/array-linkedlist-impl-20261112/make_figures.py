#!/usr/bin/env python3
"""Generate the 5 diagrams for the hand-written array / linked-list post.

Run:  /opt/miniconda3/bin/python3 make_figures.py
Then eyeball every PNG:
      sips -s format png -Z 1200 <svg> --out /tmp/x.png

Every drawn label is registered in `Check` with the SAME (x, y) that the
visible `Svg.text` got, otherwise the overlap check silently tests the wrong
box.  `ctext` below exists to make that impossible to get wrong.

Geometry lesson that cost real time: a `Check` text hitbox spans
    y - 0.80*size   ..   y + 0.24*size
i.e. it reaches much higher above the baseline than the glyph looks.  Header
rows and row labels need clearance computed from the BOX, not the baseline.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_tools"))

from svgkit import (Check, Svg, BLUE, CANVAS, FILL_BLUE, FILL_GREY,  # noqa: E402
                    FILL_TEAL, FILL_WARM, INK, LINE, MONO, MUTED, PAPER,
                    TEAL_TXT, WARM_TXT)

OUT = HERE.parent.parent / "img" / "array-linkedlist-impl-20261112"
PROBLEMS = 0


def title(s, c, main, sub=None):
    ctext(s, c, "title", 620, 46, main, size=21, weight="700")
    if sub:
        ctext(s, c, "subtitle", 620, 74, sub, size=13, fill=MUTED)


def ctext(s, c, name, x, y, t, **kw):
    """Draw text and register its hitbox at the same coordinates."""
    s.text(x, y, t, **kw)
    c.text(name, x, y, t, size=kw.get("size", 14), anchor=kw.get("anchor", "middle"))


def node_row(s, c, name, x0, y, w, h, labels, fill=PAPER, stroke=INK, size=14):
    """A row of linked-list nodes; returns the x centres."""
    xs = []
    for i, lab in enumerate(labels):
        x = x0 + i * w
        s.rect(x, y, w, h, fill=fill, stroke=stroke, rx=4)
        ctext(s, c, f"{name}{i}", x + w / 2, y + h / 2 + size * 0.36, lab, size=size)
        xs.append(x + w / 2)
    return xs


def strip(s, c, name, x0, y, w, h, labels, fills=None, size=15):
    """An array strip: flush cells, so it reads as one contiguous block."""
    xs = []
    for i, lab in enumerate(labels):
        x = x0 + i * w
        f = fills[i] if fills else PAPER
        s.rect(x, y, w, h, fill=f, stroke=INK, rx=0, sw=1.4)
        ctext(s, c, f"{name}{i}", x + w / 2, y + h / 2 + size * 0.36, lab, size=size)
        xs.append(x + w / 2)
    return xs


# ---------------------------------------------------------------- figure 1
def fig01():
    """顺序存储 vs 链式存储:物理形态的差别是后面所有复杂度的来源。"""
    global PROBLEMS
    s = Svg(1240, 560)
    c = Check(s)
    title(s, c, "顺序存储 vs 链式存储:代价来自物理形态",
          "数组用「连续」换来「地址可计算」;链表用「指针」换来「插入不搬移」")

    # ---- 左:顺序存储 ----
    s.panel(40, 110, 540, 400, fill=CANVAS, stroke=LINE)
    c.panel("p-left", 40, 110, 540, 400)
    ctext(s, c, "l-t", 310, 152, "顺序存储:元素挨着放", size=16, weight="600",
          fill=TEAL_TXT)
    ctext(s, c, "l-s", 310, 178, "第 i 个的地址 = base + i × sizeof(E)", size=12,
          fill=MUTED)

    cw, ch = 76, 56
    x0, y0 = 82, 216
    ctext(s, c, "l-cap", x0, y0 - 46, "一段连续内存", size=12, fill=MUTED,
          anchor="start")
    strip(s, c, "la", x0, y0, cw, ch, ["5", "6", "7", "8", "", ""])
    ctext(s, c, "l-idx", x0 + 2.5 * cw, y0 + ch + 24,
          "下标 0..3 有效,后面是预留容量", size=11.5, fill=MUTED)

    # 地址标注(放在格子下方,留足包围盒空间)
    ctext(s, c, "l-ad", x0 + cw / 2, y0 + ch + 52, "base+0", size=11, fill=TEAL_TXT)
    ctext(s, c, "l-ad1", x0 + 1.5 * cw, y0 + ch + 52, "+4", size=11, fill=TEAL_TXT)
    ctext(s, c, "l-ad2", x0 + 2.5 * cw, y0 + ch + 52, "+8", size=11, fill=TEAL_TXT)
    ctext(s, c, "l-ad3", x0 + 3.5 * cw, y0 + ch + 52, "+12", size=11, fill=TEAL_TXT)

    ctext(s, c, "l-note", 310, y0 + ch + 104,
          "访问 get(i):一次乘法加一次加法就拿到", size=12.5, fill=INK)
    ctext(s, c, "l-note2", 310, y0 + ch + 128, "→ 与 i 无关,O(1)", size=12.5,
          fill=TEAL_TXT, weight="600")
    ctext(s, c, "l-note3", 310, y0 + ch + 164,
          "代价:中间插入要把它后面的全部后移 → O(n)", size=12.5, fill=WARM_TXT)

    # ---- 右:链式存储 ----
    s.panel(660, 110, 540, 400, fill=CANVAS, stroke=LINE)
    c.panel("p-right", 660, 110, 540, 400)
    ctext(s, c, "r-t", 930, 152, "链式存储:节点散落,靠指针串", size=16,
          weight="600", fill=WARM_TXT)
    ctext(s, c, "r-s", 930, 178, "节点 = 值 + 一个指向下一个节点的指针", size=12,
          fill=MUTED)

    nw, nh = 96, 52
    rx0, ry = 684, 226
    # 三个节点,故意画成高低错落,表示内存里不连续
    ys = [ry, ry + 40, ry + 12]
    for i, (v, yy) in enumerate(zip(["5", "6", "7"], ys)):
        x = rx0 + i * 112
        s.rect(x, yy, nw, nh, fill=FILL_WARM, stroke=WARM_TXT, rx=6)
        ctext(s, c, f"rn{i}v", x + 26, yy + nh / 2 + 5, v, size=14)
        s.line(x + 52, yy + 6, x + 52, yy + nh - 6, stroke=WARM_TXT, sw=1.2)
        ctext(s, c, f"rn{i}p", x + 74, yy + nh / 2 + 5, "next", size=11,
              fill=WARM_TXT)
        if i:
            px = rx0 + (i - 1) * 112 + nw
            py = ys[i - 1] + nh / 2
            s.arrow(px + 2, py, x - 4, yy + nh / 2, stroke=BLUE, sw=1.8)
            c.arrow(f"ra{i}", px + 2, py, x - 4, yy + nh / 2)

    ctext(s, c, "r-note", 930, ys[2] + nh + 46,
          "每个节点多存一个指针(64 位下 8 字节)", size=12.5, fill=INK)
    ctext(s, c, "r-note2", 930, ys[2] + nh + 70,
          "存 4 字节的 int 却要付 8 字节指针 → 开销可能到 4 倍", size=12.5,
          fill=WARM_TXT)
    ctext(s, c, "r-note3", 930, ys[2] + nh + 104,
          "访问 get(i):只能从头一个个数 → O(i)", size=12.5, fill=INK)
    ctext(s, c, "r-note4", 930, ys[2] + nh + 128,
          "代价:节点分散,没有空间局部性,cache 命中率低", size=12.5,
          fill=WARM_TXT)

    PROBLEMS += c.run("01-order-vs-chain")
    s.save(OUT / "01-order-vs-chain.svg")


# ---------------------------------------------------------------- figure 2
def fig02():
    """每次翻倍扩容:总搬移次数是等比数列求和,上界是 n,所以摊还 O(1)。"""
    global PROBLEMS
    s = Svg(1240, 600)
    c = Check(s)
    title(s, c, "翻倍扩容:总搬移次数不到 2n",
          "四行分别是容量 1、2、4、8;右边算的是 n 次追加搬了多少个元素")

    cw, ch = 58, 46
    x0, y0 = 210, 196

    ctext(s, c, "hdr", x0 - 26, y0 - 40, "容量", size=12, fill=MUTED, anchor="start")
    ctext(s, c, "hdr2", x0, y0 - 40, "（暖色=已有元素,蓝色=本次从旧数组搬过来的）",
          size=11.5, fill=MUTED, anchor="start")
    steps = [(1, 0), (2, 1), (4, 2), (8, 4)]
    for r, (cap, copies) in enumerate(steps):
        y = y0 + r * 78
        ctext(s, c, f"cap{r}", x0 - 70, y + ch / 2 + 5, f"{cap}", size=13,
              fill=MUTED, anchor="start")
        for i in range(cap):
            fills = FILL_BLUE if i >= copies else FILL_WARM
            s.rect(x0 + i * cw, y, cw, ch, fill=fills, stroke=INK, rx=0, sw=1.2)
        # 标签放在格子右边而不是压在格子上:压在格子上会和竖线重叠,
        # 数字正好落在边框上会读错。右移之后整行一眼能读完。
        if copies:
            ctext(s, c, f"cp{r}", x0 + cap * cw + 24, y + ch / 2 + 5,
                  f"搬 {copies}", size=12, fill=BLUE, weight="600", anchor="start")
        else:
            ctext(s, c, f"cp{r}", x0 + cap * cw + 24, y + ch / 2 + 5, "新开",
                  size=12, fill=BLUE, weight="600", anchor="start")

    # 右侧:总次数的推导。x 起点要避开最长的一行(容量 8 = 8 格),
    # 否则面板会压到第 4 行的格子上。
    px = 790
    s.panel(px, 150, 420, 330, fill=CANVAS, stroke=LINE)
    c.panel("p-sum", px, 150, 420, 330)
    ctext(s, c, "sum-t", px + 210, 190, "总搬移次数", size=16, weight="600")
    lines = [
        "搬移发生在容量 1, 2, 4, …, 2ᵏ 上",
        "2ᵏ 是 ≥ n 的最小 2 的幂(n=10 时是 16)",
        "每次搬当时的 size 个,所以总数是",
        "1 + 2 + 4 + … + 2ᵏ⁻¹ = 2ᵏ − 1",
        "n=10 → 15 次;n=1024 → 1023 次",
        "因为 2ᵏ < 2n,总数 < 2n,所以总共 O(n)",
        "→ 平均每次 O(1)(摊还)",
    ]
    for i, t in enumerate(lines):
        ctext(s, c, f"sum{i}", px + 26, 228 + i * 30, t, size=12,
              anchor="start", fill=INK if i < 5 else TEAL_TXT,
              weight="400" if i < 6 else "600")

    ctext(s, c, "foot", 400, y0 + 4 * 78 + 24,
          "如果改成每次只 +1,总次数是 1+2+...+n = O(n²) —— 摊还 O(1) 就没了",
          size=13, fill=WARM_TXT)

    PROBLEMS += c.run("02-doubling-amortized")
    s.save(OUT / "02-doubling-amortized.svg")


# ---------------------------------------------------------------- figure 3
def fig03():
    """哨兵节点把「头部插入」这个特判变成结构上不存在的情况。"""
    global PROBLEMS
    s = Svg(1240, 660)
    c = Check(s)
    title(s, c, "哨兵节点:把「头部插入」这个特判变成结构上不存在的情况",
          "少一个分支,不是少几行代码 —— 是少一类边界 bug")

    nw, nh = 104, 54

    # ---- 上:没有哨兵 ----
    s.panel(40, 116, 1160, 254, fill=FILL_WARM, stroke=WARM_TXT)
    c.panel("p-no", 40, 116, 1160, 254)
    ctext(s, c, "no-t", 70, 156, "没有哨兵:head 可能为 null,必须分两种情况", size=15,
          weight="600", fill=WARM_TXT, anchor="start")

    y1 = 202
    node_row(s, c, "na", 70, y1, nw, nh, ["1", "2", "3"], fill=PAPER)
    # 标题基线在 156;size=12 的标签包围盒上沿在基线 -9.6,
    # 所以标签基线要放到 200 以下,不能贴着节点放。
    ctext(s, c, "no-l1", 70, y1 + nh + 30,
          "head 指向第一个节点(它可能为 null)", size=12, fill=MUTED,
          anchor="start")
    ctext(s, c, "no-l2", 70 + 2.3 * nw, y1 + nh + 30,
          "头插要改 head 变量本身", size=12.5, fill=WARM_TXT, anchor="start")
    ctext(s, c, "no-l3", 70 + 2.3 * nw, y1 + nh + 58,
          "中间插入只改某个节点的 next", size=12.5, fill=MUTED, anchor="start")

    # ---- 下:有哨兵 ----
    s.panel(40, 388, 1160, 254, fill=FILL_TEAL, stroke=TEAL_TXT)
    c.panel("p-yes", 40, 388, 1160, 254)
    ctext(s, c, "yes-t", 70, 428, "有哨兵:dummy 永远存在,一条路径走到底", size=15,
          weight="600", fill=TEAL_TXT, anchor="start")

    y2 = 474
    s.rect(70, y2, nw, nh, fill=FILL_GREY, stroke=TEAL_TXT, rx=4, dash="5,4")
    ctext(s, c, "dm", 70 + nw / 2, y2 + nh / 2 + 5, "dummy", size=12, fill=TEAL_TXT)
    node_row(s, c, "nb", 70 + nw, y2, nw, nh, ["1", "2", "3"], fill=PAPER)
    ctext(s, c, "yes-l1", 70, y2 + nh + 30,
          "head 永远指向 dummy,不再被修改", size=12, fill=MUTED, anchor="start")
    ctext(s, c, "yes-l2", 70 + 2.3 * nw, y2 + nh + 30,
          "头插 = 在 dummy 后面插入", size=12.5, fill=TEAL_TXT, anchor="start")
    ctext(s, c, "yes-l3", 70 + 2.3 * nw, y2 + nh + 58,
          "和中间插入完全是同一段代码", size=12.5, fill=TEAL_TXT, anchor="start")

    PROBLEMS += c.run("03-sentinel-removes-branches")
    s.save(OUT / "03-sentinel-removes-branches.svg")


def fig04():
    """双链表加双哨兵:插入只发生在 prev 和 next 之间,四指针不必判空。"""
    global PROBLEMS
    s = Svg(1240, 700)
    c = Check(s)
    title(s, c, "双链表的双哨兵:插入永远发生在「prev 和 next 之间」",
          "双链表插入要改四个指针;双哨兵保证这两侧都一定非空")

    nw, nh = 168, 50

    # ---- 空链表 ----
    ctext(s, c, "e-t", 520, 120, "空链表也是两条哨兵互指,不是 null", size=14,
          weight="600")
    ey = 146
    s.rect(330, ey, nw, nh, fill=FILL_GREY, stroke=TEAL_TXT, rx=5, dash="5,4")
    ctext(s, c, "eh", 330 + nw / 2, ey + nh / 2 + 5, "dummyHead", size=12,
          fill=TEAL_TXT)
    s.rect(712, ey, nw, nh, fill=FILL_GREY, stroke=TEAL_TXT, rx=5, dash="5,4")
    ctext(s, c, "et", 712 + nw / 2, ey + nh / 2 + 5, "dummyTail", size=12,
          fill=TEAL_TXT)
    s.arrow(330 + nw + 6, ey + nh / 2 - 11, 712 - 6, ey + nh / 2 - 11,
            stroke=BLUE, sw=1.6)
    c.arrow("ea1", 330 + nw + 6, ey + nh / 2 - 11, 712 - 6, ey + nh / 2 - 11)
    s.arrow(712 - 6, ey + nh / 2 + 11, 330 + nw + 6, ey + nh / 2 + 11,
            stroke=WARM_TXT, sw=1.6)
    c.arrow("ea2", 712 - 6, ey + nh / 2 + 11, 330 + nw + 6, ey + nh / 2 + 11)
    ctext(s, c, "e-l", 605, ey + nh / 2 - 17, "next", size=10.5, fill=BLUE)
    ctext(s, c, "e-l2", 605, ey + nh / 2 + 30, "prev", size=10.5, fill=WARM_TXT)

    # ---- 三节点:prev / node / next,同一个 x 列 ----
    # 竖直箭头必须真的碰到节点边沿,否则箭头会漂在空中,
    # 而且 ④ 的箭头会指进空白处 —— 这两点都是"门过了但图不对"。
    cx = 520
    py, nyy, qy = 250, 356, 462
    for nm, yy, lab, fill, stroke, txt in (
            ("np", py, "prev (= dummyHead)", PAPER, INK, INK),
            ("nn", nyy, "node (新节点)", FILL_WARM, WARM_TXT, WARM_TXT),
            ("nq", qy, "next (= 原来的第 1 个)", PAPER, INK, INK)):
        s.rect(cx - nw / 2, yy, nw, nh, fill=fill, stroke=stroke, rx=5)
        ctext(s, c, nm, cx, yy + nh / 2 + 5, lab, size=12, fill=txt)

    gaps = ((py + nh, nyy), (nyy + nh, qy))
    s.arrow(cx - 34, gaps[0][0] + 2, cx - 34, gaps[0][1] - 2, stroke=BLUE, sw=1.7)
    c.arrow("na1", cx - 34, gaps[0][0] + 2, cx - 34, gaps[0][1] - 2)
    s.arrow(cx + 34, gaps[0][1] - 2, cx + 34, gaps[0][0] + 2, stroke=WARM_TXT,
            sw=1.7)
    c.arrow("na2", cx + 34, gaps[0][1] - 2, cx + 34, gaps[0][0] + 2)
    s.arrow(cx - 34, gaps[1][0] + 2, cx - 34, gaps[1][1] - 2, stroke=BLUE, sw=1.7)
    c.arrow("na3", cx - 34, gaps[1][0] + 2, cx - 34, gaps[1][1] - 2)
    # ④ next.prev = node:从 node 右下方绕回 next 的顶边。
    # 折线的横向长段不登记进 Check —— Check.arrow 记的是轴对齐包围盒,
    # 横跨整幅图的线段会把每一段文字都误报成碰撞。
    midy = (nyy + nh + qy) / 2
    s.raw(f'<line x1="{cx + 34}" y1="{nyy + nh + 2}" x2="{cx + 34}" '
          f'y2="{midy}" stroke="{WARM_TXT}" stroke-width="1.7" '
          f'stroke-linecap="round"/>')
    s.raw(f'<line x1="{cx + 34}" y1="{midy}" x2="{cx + 34}" y2="{midy}" '
          f'stroke="{WARM_TXT}" stroke-width="1.7"/>')
    s.arrow(cx + 34, midy, cx + 34, qy - 2, stroke=WARM_TXT, sw=1.7)
    c.arrow("na4", cx + 34, midy, cx + 34, qy - 2)
    s.raw(f'<line x1="{cx + 34}" y1="{nyy + nh + 2}" x2="{cx + 34}" '
          f'y2="{midy}" stroke="{WARM_TXT}" stroke-width="1.7"/>')

    # ---- 四行指针说明 ----
    lx = 790
    ctext(s, c, "gl-t", lx, py + 18, "四处指针都要改", size=14, weight="600",
          anchor="start")
    for i, (t, col) in enumerate((
            ("① prev.next = node", BLUE),
            ("② node.prev = prev", WARM_TXT),
            ("③ node.next = next", BLUE),
            ("④ next.prev = node", WARM_TXT))):
        ctext(s, c, f"gl{i + 1}", lx, py + 56 + i * 26, t, size=12.5, fill=col,
              anchor="start")
    ctext(s, c, "gl5", lx, py + 196, "双哨兵保证 prev 与 next 都非空,", size=12.5,
          fill=INK, anchor="start")
    ctext(s, c, "gl6", lx, py + 220, "所以这四行不需要任何判空分支。", size=12.5,
          fill=INK, anchor="start")
    ctext(s, c, "gl7", lx, py + 262, "没有哨兵时「在头部插入」意味着 prev 为空指针,", size=12.5,
          fill=MUTED, anchor="start")
    ctext(s, c, "gl8", lx, py + 286, "这四行直接崩 —— 于是又得加特判。", size=12.5,
          fill=MUTED, anchor="start")

    PROBLEMS += c.run("04-double-sentinel")
    s.save(OUT / "04-double-sentinel.svg")


def fig05():
    """快慢指针找中点:fast 走两步 slow 走一步,fast 到底时 slow 正好在中点。"""
    global PROBLEMS
    s = Svg(1240, 620)
    c = Check(s)
    title(s, c, "快慢指针找中点:fast 的速度是 slow 的两倍",
          "fast 走完 n 步时 slow 走了 n/2 步 —— 一趟遍历同时完成「走完」和「停在中点」")

    nw, nh = 92, 50
    x0, y0 = 190, 210
    vals = ["1", "2", "3", "4", "5", "6"]

    xs = node_row(s, c, "n", x0, y0, nw, nh, vals, fill=PAPER)
    ctext(s, c, "row-l", x0, y0 - 42, "偶数长度 n=6", size=12.5, fill=MUTED,
          anchor="start")

    # slow 与 fast 的落点用不同颜色标出
    def mark(i, txt, col, dy):
        x = xs[i]
        s.rect(x - nw / 2 - 3, y0 - 3, nw + 6, nh + 6, fill="none",
               stroke=col, rx=6, sw=2.0)
        ctext(s, c, f"m{txt}{i}", x, y0 + nh + dy, txt, size=12, fill=col,
              weight="600")

    mark(2, "slow", TEAL_TXT, 34)
    mark(5, "fast", BLUE, 34)

    ctext(s, c, "mid-note", 620, y0 + nh + 82,
          "fast 走到末尾(第 6 个节点),slow 停在第 3 个 —— 这是「第二个中点」",
          size=12.5, fill=INK)

    # ---- 循环条件对比 ----
    s.panel(40, 400, 560, 180, fill=FILL_TEAL, stroke=TEAL_TXT)
    c.panel("p-ok", 40, 400, 560, 180)
    ctext(s, c, "ok-t", 320, 442, "取第二个中点", size=15, weight="600",
          fill=TEAL_TXT)
    ctext(s, c, "ok-c", 320, 474, "while fast and fast.next:", size=13)
    ctext(s, c, "ok-n", 320, 508,
          "fast 落在最后一个节点时判到 fast.next 为空就停", size=12, fill=MUTED)
    ctext(s, c, "ok-n2", 320, 534, "适用于找环入口一类的题", size=12, fill=MUTED)

    s.panel(640, 400, 560, 180, fill=FILL_WARM, stroke=WARM_TXT)
    c.panel("p-bad", 640, 400, 560, 180)
    ctext(s, c, "bad-t", 920, 442, "取第一个中点(判回文要用)", size=15,
          weight="600", fill=WARM_TXT)
    ctext(s, c, "bad-c", 920, 474, "while fast.next and fast.next.next:",
          size=13)
    ctext(s, c, "bad-n", 920, 508,
          "先多走一步,slow 才不会包含后半段的中点", size=12, fill=MUTED)
    ctext(s, c, "bad-n2", 920, 534,
          "两种中点的区别就在这里", size=12, fill=MUTED)

    PROBLEMS += c.run("05-fast-slow-middle")
    s.save(OUT / "05-fast-slow-middle.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (fig01, fig02, fig03, fig04, fig05):
        fn()
    print()
    if PROBLEMS:
        print(f"{PROBLEMS} PROBLEM(S) — figures in {OUT}")
        return 1
    print(f"OK — figures in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
