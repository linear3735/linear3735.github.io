#!/usr/bin/env python3
"""Draw the four diagrams for the array-two-pointers post.

Generated, never hand-edited.  Run after any change:

    python3 make_figs.py

`Check` (from svgkit) catches text/text, text/arrow, off-canvas and
text-spilling-out-of-panel problems; it cannot see a label sitting on an
unregistered line, so every SVG is additionally rendered with

    sips -s format png -Z 1200 <file>.svg --out /tmp/<file>.png

and looked at.
"""
import sys
from pathlib import Path

REPO = Path.home() / "projects/linear3735.github.io"
sys.path.insert(0, str(REPO / "assets/blog/_tools"))
from svgkit import (Svg, Check, INK, MUTED, BLUE, PAPER,        # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/array-two-pointers-20261111"
BAD = []


def row(svg, chk, x0, y, vals, fills=None, w=64, h=48, gap=4, size=17, tag="r"):
    """One row of array cells.  Returns the centre x of every cell."""
    if fills is None:
        fills = [PAPER] * len(vals)
    centers, x = [], x0
    for i, (v, f) in enumerate(zip(vals, fills)):
        svg.rect(x, y, w, h, fill=f, stroke=INK, sw=1.4, rx=6)
        cx = x + w / 2
        svg.text(cx, y + h / 2 + size * 0.36, v, size=size)
        chk.text(f"{tag}-cell-{i}", cx, y + h / 2 + size * 0.36, v, size=size)
        centers.append(cx)
        x += w + gap
    return centers


def idx_row(svg, chk, centers, y, size=11, tag="r"):
    """Small 0-based index labels for a cell row."""
    for i, cx in enumerate(centers):
        svg.text(cx, y, str(i), size=size, fill=MUTED)
        chk.text(f"{tag}-idx-{i}", cx, y, str(i), size=size)


def ptr(svg, chk, cx, y, label, color=WARM_TXT, size=13, up=14, name=None):
    """A pointer name with a short arrow going up towards the cell above."""
    svg.text(cx, y, label, size=size, fill=color, weight="600")
    chk.text(name or f"ptr-{label}@{cx}", cx, y, label, size=size)
    svg.arrow(cx, y - up, cx, y - up - 16, stroke=color, sw=1.4, head=6.5)
    chk.arrow(f"ptr-arrow-{label}@{cx}", cx, y - up, cx, y - up - 16)


def caption(svg, chk, x, y, t, size=13, fill=MUTED, anchor="start", tag=None):
    svg.text(x, y, t, size=size, fill=fill, anchor=anchor)
    chk.text(tag or f"cap-{x}-{y}", x, y, t, size=size, anchor=anchor)


# ------------------------------------------------------------------ figure 1
def fig_separation():
    svg = Svg(880, 340)
    chk = Check(svg)

    svg.panel(20, 20, 840, 190)
    chk.panel("main", 20, 20, 840, 190)
    caption(svg, chk, 40, 52, "力扣 26 的中间状态:fast 在前面探路,slow 是写指针",
            tag="cap1")

    vals = ["0", "1", "2", "1", "1", "2", "2", "3"]
    fills = [FILL_TEAL] * 3 + [FILL_GREY] * 5
    centers = row(svg, chk, 70, 100, vals, fills)

    # the write itself: nums[fast] -> nums[slow]
    svg.arrow(centers[5], 84, centers[2], 84, stroke=WARM_TXT, sw=1.5, head=7)
    chk.arrow("write-arrow", centers[5], 84, centers[2], 84)
    caption(svg, chk, (centers[5] + centers[2]) / 2, 76,
            "nums[fast] 写进 nums[slow]", size=12, fill=WARM_TXT,
            anchor="middle", tag="cap-write")
    idx_row(svg, chk, centers, 164)

    for ci, label, col in ((2, "slow", WARM_TXT), (5, "fast", TEAL_TXT)):
        ptr(svg, chk, centers[ci], 204, label, color=col)

    svg.panel(20, 224, 840, 96)
    chk.panel("foot", 20, 224, 840, 96)
    caption(svg, chk, 40, 258,
            "slow 停在 2 上:它是「最后一个有效元素的下标」,返回长度要写 slow + 1",
            tag="cap3")
    caption(svg, chk, 40, 286,
            "fast 走完 N 步就结束,slow 从没超过 fast —— 覆盖踩不到还没读的数据",
            size=12, tag="cap4")

    BAD.append(chk.run("01-slow-fast-separation"))
    svg.save(OUT / "01-slow-fast-separation.svg")


# ------------------------------------------------------------------ figure 2
def fig_write_pointer():
    svg = Svg(880, 400)
    chk = Check(svg)

    svg.panel(20, 20, 840, 160)
    chk.panel("before", 20, 20, 840, 160)
    caption(svg, chk, 40, 50, "① 原数组:重复项挨在一起(前提是有序)", tag="cap-b1")
    centers = row(svg, chk, 70, 78, ["0", "0", "1", "1", "1", "2", "2", "3"],
                  [PAPER] * 8, tag="b")
    idx_row(svg, chk, centers, 68, tag="b")
    caption(svg, chk, 70, 156,
            "每发现一个重复项就删掉的话,后面的元素都要往前搬一格 —— 最坏 O(N^2)",
            size=12, tag="cap-b2")

    svg.panel(20, 200, 840, 180)
    chk.panel("after", 20, 200, 840, 180)
    caption(svg, chk, 40, 228, "② 覆盖之后:前 3 格就是答案,后面是脏数据",
            tag="cap-a1")
    centers2 = row(svg, chk, 70, 258, ["0", "1", "2", "1", "1", "2", "2", "3"],
                   [FILL_TEAL] * 3 + [FILL_GREY] * 5, tag="a")
    idx_row(svg, chk, centers2, 250, tag="a")
    svg.rect(64, 252, 200, 60, fill="none", stroke=TEAL_TXT, sw=1.5, rx=9,
             dash="6 4")
    caption(svg, chk, 190, 340, "nums[0..slow] = 答案前缀", size=12,
            fill=TEAL_TXT, anchor="middle", tag="cap-a2")
    caption(svg, chk, 620, 340, "返回 slow + 1 = 3,后面不重要", size=12,
            anchor="middle", tag="cap-a3")

    BAD.append(chk.run("02-dedup-write-pointer"))
    svg.save(OUT / "02-dedup-write-pointer.svg")


# ------------------------------------------------------------------ figure 3
def fig_converging():
    svg = Svg(880, 420)
    chk = Check(svg)

    svg.panel(20, 20, 840, 180)
    chk.panel("step1", 20, 20, 840, 180)
    caption(svg, chk, 40, 50, "① 1 + 11 = 12 > 10,right 这一格可以永远丢掉",
            tag="cap-s1")
    centers = row(svg, chk, 70, 80, ["1", "3", "4", "6", "8", "11"], tag="s1")
    idx_row(svg, chk, centers, 70, tag="s1")
    ptr(svg, chk, centers[0], 164, "left", name="left1")
    ptr(svg, chk, centers[5], 164, "right", color=TEAL_TXT, name="right1")
    svg.raw(f'<line x1="{centers[5] - 24}" y1="88" x2="{centers[5] + 24}" '
            f'y2="120" stroke="{MUTED}" stroke-width="1.6"/>')
    svg.raw(f'<line x1="{centers[5] + 24}" y1="88" x2="{centers[5] - 24}" '
            f'y2="120" stroke="{MUTED}" stroke-width="1.6"/>')
    caption(svg, chk, 500, 104, "丢掉 right:它是区间里最大的数,", size=12,
            tag="cap-cut1")
    caption(svg, chk, 500, 124, "和谁都凑不出 target", size=12, tag="cap-cut2")

    svg.panel(20, 220, 840, 180)
    chk.panel("step2", 20, 220, 840, 180)
    caption(svg, chk, 40, 250, "② 收敛到 4 + 6 = 10,命中", tag="cap-s2")
    centers2 = row(svg, chk, 70, 280, ["1", "3", "4", "6", "8", "11"],
                   [FILL_GREY, FILL_GREY, FILL_TEAL, FILL_TEAL, FILL_GREY,
                    FILL_GREY], tag="s2")
    idx_row(svg, chk, centers2, 270, tag="s2")
    ptr(svg, chk, centers2[2], 364, "left", name="left2")
    ptr(svg, chk, centers2[3], 364, "right", color=TEAL_TXT, name="right2")
    caption(svg, chk, 500, 300, "返回 [left + 1, right + 1]", size=12,
            fill=TEAL_TXT, tag="cap-ans")
    caption(svg, chk, 500, 320, "= [3, 5](题目要求 1 起始)", size=12,
            tag="cap-ans2")

    BAD.append(chk.run("03-converging-pointers"))
    svg.save(OUT / "03-converging-pointers.svg")


# ------------------------------------------------------------------ figure 4
def fig_center_expand():
    svg = Svg(880, 440)
    chk = Check(svg)

    svg.panel(20, 20, 840, 180)
    chk.panel("even", 20, 20, 840, 180)
    caption(svg, chk, 40, 50,
            "① 偶数中心:中心是两个字符之间的缝,对应 expand(i, i + 1)",
            tag="cap-e1")
    centers = row(svg, chk, 130, 80, ["c", "b", "b", "d"],
                  [FILL_GREY, FILL_TEAL, FILL_TEAL, FILL_GREY], tag="e")
    idx_row(svg, chk, centers, 70, tag="e")
    seam = (centers[1] + centers[2]) / 2
    svg.raw(f'<line x1="{seam}" y1="74" x2="{seam}" y2="134" stroke="{TEAL_TXT}" '
            f'stroke-width="1.6" stroke-dasharray="5 4"/>')
    svg.arrow(centers[1] - 10, 152, centers[0] + 12, 152, stroke=BLUE, sw=1.4,
              head=6.5)
    chk.arrow("expand-left", centers[1] - 10, 152, centers[0] + 12, 152)
    svg.arrow(centers[2] + 10, 152, centers[3] - 12, 152, stroke=BLUE, sw=1.4,
              head=6.5)
    chk.arrow("expand-right", centers[2] + 10, 152, centers[3] - 12, 152)
    caption(svg, chk, 440, 176, "s[1] == s[2],先得到 \"bb\";再往外扩 c != d,停",
            size=12, anchor="middle", tag="cap-e2")

    svg.panel(20, 240, 840, 180)
    chk.panel("odd", 20, 240, 840, 180)
    caption(svg, chk, 40, 268, "② 奇数中心:中心是一个字符,对应 expand(i, i)",
            tag="cap-o1")
    centers2 = row(svg, chk, 130, 300, ["a", "b", "a"],
                   [FILL_TEAL, FILL_WARM, FILL_TEAL], tag="o")
    idx_row(svg, chk, centers2, 290, tag="o")
    svg.raw(f'<line x1="{centers2[1]}" y1="294" x2="{centers2[1]}" y2="354" '
            f'stroke="{WARM_TXT}" stroke-width="1.6" stroke-dasharray="5 4"/>')
    svg.arrow(centers2[1] - 16, 372, centers2[0] + 12, 372, stroke=BLUE, sw=1.4,
              head=6.5)
    chk.arrow("expand-left-odd", centers2[1] - 16, 372, centers2[0] + 12, 372)
    svg.arrow(centers2[1] + 16, 372, centers2[2] - 12, 372, stroke=BLUE, sw=1.4,
              head=6.5)
    chk.arrow("expand-right-odd", centers2[1] + 16, 372, centers2[2] - 12, 372)
    caption(svg, chk, 440, 400,
            "只用奇数中心的话,\"cbbd\" 会返回 \"c\" 而不是 \"bb\":2n - 1 个中心都要试",
            size=12, anchor="middle", tag="cap-o2")

    BAD.append(chk.run("04-expand-from-center"))
    svg.save(OUT / "04-expand-from-center.svg")


def matrix(svg, chk, x0, y0, vals, w=44, h=40, gap=3, size=15, fills=None, tag="m"):
    """A square matrix of cells.  Returns the centre of every cell."""
    n = len(vals)
    if fills is None:
        fills = [[PAPER] * n for _ in range(n)]
    out = []
    for i in range(n):
        line = []
        for j in range(n):
            x, y = x0 + j * (w + gap), y0 + i * (h + gap)
            svg.rect(x, y, w, h, fill=fills[i][j], stroke=INK, sw=1.3, rx=5)
            cx, cy = x + w / 2, y + h / 2 + size * 0.36
            svg.text(cx, cy, vals[i][j], size=size)
            chk.text(f"{tag}-{i}-{j}", cx, cy, vals[i][j], size=size)
            line.append((cx, cy))
        out.append(line)
    return out


def fig_trap_bottleneck():
    """42: why the shorter side may be settled at once."""
    svg = Svg(880, 400)
    chk = Check(svg)

    svg.panel(20, 20, 840, 232)
    chk.panel("main", 20, 20, 840, 232)
    caption(svg, chk, 40, 52, "力扣 42 双指针的中间状态:lmax = 3 锁死了左侧水位",
            tag="cap-t1")

    base = 214
    unit = 26
    # left side: lmax wall (3), current column (1), water band 1 -> 3
    svg.rect(110, base - 3 * unit, 132, 3 * unit, fill=FILL_BLUE, stroke=BLUE, sw=1.4, rx=6)
    svg.rect(110, base - 1 * unit, 132, 1 * unit, fill=FILL_GREY, stroke=INK, sw=1.4, rx=6)
    caption(svg, chk, 176, base - 3 * unit - 12, "lmax = 3", size=13, fill=BLUE,
            anchor="middle", tag="cap-lmax")
    caption(svg, chk, 176, base - 13, "height[left] = 1", size=12, anchor="middle", tag="cap-hl")
    svg.arrow(300, base - 2 * unit, 250, base - 2 * unit, stroke=TEAL_TXT, sw=1.5, head=7)
    chk.arrow("water-left", 300, base - 2 * unit, 250, base - 2 * unit)
    caption(svg, chk, 312, base - 2 * unit - 8,
            "这一格的水位 = min(lmax, rmax) = lmax = 3,已经确定", size=13, fill=TEAL_TXT,
            tag="cap-wl")

    # right side: rmax wall (5), current column (2)
    svg.rect(650, base - 5 * unit, 132, 5 * unit, fill=FILL_BLUE, stroke=BLUE, sw=1.4, rx=6)
    svg.rect(650, base - 2 * unit, 132, 2 * unit, fill=FILL_GREY, stroke=INK, sw=1.4, rx=6)
    caption(svg, chk, 716, base - 5 * unit - 12, "rmax = 5", size=13, fill=BLUE,
            anchor="middle", tag="cap-rmax")
    caption(svg, chk, 716, base - 13, "height[right] = 2", size=12, anchor="middle",
            tag="cap-hr")
    svg.arrow(596, base - 3.5 * unit, 642, base - 3.5 * unit, stroke=MUTED, sw=1.4,
              dash="5 4", head=7)
    chk.arrow("water-right", 596, base - 3.5 * unit, 642, base - 3.5 * unit)
    caption(svg, chk, 586, base - 3.5 * unit - 8, "rmax 更大,这一侧还得等", size=13,
            fill=MUTED, anchor="end", tag="cap-wr")

    caption(svg, chk, 40, 240,
            "lmax <= rmax 时,左侧水位只由 lmax 决定:右边再高,水也从左边流走。"
            "所以 left 这一格可以立刻结算,left += 1。", size=13, tag="cap-t2")

    svg.panel(20, 264, 840, 116)
    chk.panel("foot", 20, 264, 840, 116)
    caption(svg, chk, 40, 296,
            "这就是 §1.1 那条判据的又一次复用:「这一步凭什么能丢掉这一格」——"
            "答案仍然是 min(lmax, rmax) 由较矮的一侧锁死。", tag="cap-t3")
    caption(svg, chk, 40, 326,
            "顺序不能反:先更新 lmax / rmax,再结算。挪到循环末尾,实测 [4,2,0,3,2,5] 算出 -1"
            "(正确 9),[0,1,0,2,1,0,1,3,2,1,2,1] 算出 5(正确 6)。", size=12,
            fill=WARM_TXT, tag="cap-t4")
    caption(svg, chk, 40, 356,
            "单调栈是同一道题的另一种视角:横向分层,每一层由「栈顶左边第一个更高」和"
            "「当前这个更高」夹出来。", size=12, tag="cap-t5")

    BAD.append(chk.run("05-trap-shorter-side"))
    svg.save(OUT / "05-trap-shorter-side.svg")


def fig_dutch_flag():
    """75: the three-pointer sweep and the element swapped in from the right."""
    svg = Svg(880, 380)
    chk = Check(svg)

    svg.panel(20, 20, 840, 200)
    chk.panel("main", 20, 20, 840, 200)
    caption(svg, chk, 40, 44, "力扣 75 的中间状态:p0 / i / p2 三个指针各管一件事",
            tag="cap-d1")

    # p0 = 2, i = 3, p2 = 5: nums[0..p0-1] are all 0 and nums[p2+1..] are all 2,
    # which is exactly what the remaining loop keeps true.
    vals = ["0", "0", "1", "2", "1", "2", "2", "2"]
    fills = [FILL_TEAL, FILL_TEAL, FILL_GREY, FILL_WARM, FILL_GREY, FILL_WARM,
             FILL_WARM, FILL_WARM]
    centers = row(svg, chk, 70, 96, vals, fills, w=70, h=52, tag="d")
    idx_row(svg, chk, centers, 168, tag="d")

    for ci, label, col in ((2, "p0", TEAL_TXT), (3, "i", WARM_TXT), (5, "p2", WARM_TXT)):
        ptr(svg, chk, centers[ci], 206, label, color=col, name=f"d-ptr-{label}")

    svg.panel(20, 236, 840, 130)
    chk.panel("foot", 20, 236, 840, 130)
    caption(svg, chk, 40, 268,
            "i 撞上 2:和 p2 交换。换进来的那一个(可能是 0 也可能是 2)落在 i 上,"
            "还没检查过。", tag="cap-d2")
    svg.arrow(centers[3] + 10, 88, centers[5] - 10, 88, stroke=WARM_TXT, sw=1.5, head=7)
    chk.arrow("d-swap-out", centers[3] + 10, 88, centers[5] - 10, 88)
    svg.arrow(centers[5] - 10, 78, centers[3] + 10, 78, stroke=WARM_TXT, sw=1.3,
              dash="4 3", head=6)
    chk.arrow("d-swap-in", centers[5] - 10, 78, centers[3] + 10, 78)
    caption(svg, chk, (centers[3] + centers[5]) / 2, 64, "swap(nums[i], nums[p2])",
            size=12, fill=WARM_TXT, anchor="middle", tag="cap-d-swap")
    caption(svg, chk, 40, 300,
            "所以 p2 -= 1 之后 i 不能跟着加:实测加上 i += 1,500 组随机数组里 125 组排错。",
            size=13, fill=WARM_TXT, tag="cap-d3")
    caption(svg, chk, 40, 330,
            "循环条件是 i <= p2 而不是 i < p2:i 和 p2 撞上时那一格还要判一次,否则漏掉"
            "最后一个元素(实测 109 组排错)。", size=12, tag="cap-d4")

    BAD.append(chk.run("06-dutch-flag-sweep"))
    svg.save(OUT / "06-dutch-flag-sweep.svg")


def fig_rotate_matrix():
    """48: transpose the upper triangle, then flip every row."""
    svg = Svg(880, 360)
    chk = Check(svg)

    svg.panel(20, 20, 840, 240)
    chk.panel("main", 20, 20, 840, 240)
    caption(svg, chk, 40, 52, "力扣 48:转置(只换上三角) + 每行水平翻转 = 顺时针 90°",
            tag="cap-r1")

    a = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
    hi = [[FILL_WARM if i < j else PAPER for j in range(3)] for i in range(3)]
    b = [[a[j][i] for j in range(3)] for i in range(3)]
    cc = [list(reversed(r)) for r in b]

    ca = matrix(svg, chk, 60, 84, a, fills=hi, tag="rot-a")
    cb = matrix(svg, chk, 340, 84, b, tag="rot-b")
    ccc = matrix(svg, chk, 620, 84, cc, tag="rot-c")
    caption(svg, chk, 130, 76, "① 原矩阵", size=13, anchor="middle", tag="cap-r2")
    caption(svg, chk, 410, 76, "② 转置(交换上三角)", size=13, anchor="middle", tag="cap-r3")
    caption(svg, chk, 690, 76, "③ 每行 reverse", size=13, anchor="middle", tag="cap-r4")

    svg.arrow(250, 120, 330, 120, stroke=BLUE, sw=1.6, head=7)
    chk.arrow("rot-1", 250, 120, 330, 120)
    svg.arrow(530, 120, 610, 120, stroke=BLUE, sw=1.6, head=7)
    chk.arrow("rot-2", 530, 120, 610, 120)
    svg.arrow(ca[0][1][0], ca[0][1][1] + 18, cb[1][0][0], cb[1][0][1] - 18,
              stroke=WARM_TXT, sw=1.3, dash="4 3", head=6)
    chk.arrow("rot-trace", ca[0][1][0], ca[0][1][1] + 18, cb[1][0][0], cb[1][0][1] - 18)
    caption(svg, chk, 250, 214, "2 走到 [1][0]", size=12, fill=WARM_TXT, anchor="middle",
            tag="cap-r5")

    caption(svg, chk, 40, 250,
            "上三角用 for j in range(i + 1, n):每一对 (i, j) 只交换一次。"
            "写成 range(n) 会把每对交换两次 ——", size=13, tag="cap-r6")

    svg.panel(20, 280, 840, 62)
    chk.panel("foot", 20, 280, 840, 62)
    caption(svg, chk, 40, 310,
            "两次叠加等于没转置,但第二步的水平翻转照做,于是结果是左右镜像:"
            "实测 [[1, 2], [3, 4]] 会得到 [[2, 1], [4, 3]]。", size=13, fill=WARM_TXT,
            tag="cap-r7")
    caption(svg, chk, 40, 336,
            "这种错不报异常、矩阵也确实「变了」,所以一定要拿不对称的输入试。", size=12,
            tag="cap-r8")

    BAD.append(chk.run("07-matrix-rotate-decompose"))
    svg.save(OUT / "07-matrix-rotate-decompose.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_separation()
    fig_write_pointer()
    fig_converging()
    fig_center_expand()
    fig_trap_bottleneck()
    fig_dutch_flag()
    fig_rotate_matrix()
    total = sum(BAD)
    print(f"  {total} layout problem(s) total")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
