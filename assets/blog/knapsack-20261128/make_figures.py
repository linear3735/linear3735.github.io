#!/usr/bin/env python3
"""生成 knapsack 这篇的 4 张图。

每个文字标签都在 `Check` 里登记一次,越界和碰撞会直接报出来。
生成完必须自己渲染看一眼 —— Check 查不到「文字压在没登记的线上」。

    python3 assets/blog/knapsack-20261128/make_figures.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "assets/blog/_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,   # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/knapsack-20261128"
OUT.mkdir(parents=True, exist_ok=True)

BAD = 0

# 图 1 用到的具体例子:一件重 3、价值 4 的物品,容量 0..6。
# 下面的文字说明和格子里的数字必须是同一组数,不能各写各的。
W1 = 3
V1 = 4
CAP = 6


def title(s, c, text, sub=None, w=1240):
    s.text(w // 2, 38, text, size=17, weight="600")
    c.text("title", w // 2, 38, text, size=17)
    if sub:
        s.text(w // 2, 62, sub, size=12, fill=MUTED)
        c.text("subtitle", w // 2, 62, sub, size=12)


def ctext(s, c, name, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Svg.text 和 Check.text 的 x 必须完全一致,所以包一层防止写歪。"""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)


def row_cells(s, c, name, x0, y0, cw, ch, labels, fills):
    """一排格子。labels[i] 为 None 表示只画空格子不写字。"""
    for i, lab in enumerate(labels):
        x = x0 + i * cw
        s.rect(x, y0, cw, ch, fill=fills[i], rx=4)
        if lab is not None:
            ctext(s, c, f"{name}{i}", x + cw / 2, y0 + ch / 2 + 5, lab, size=14)


# ---------------------------------------------------------------- figure 1
def fig01():
    """0-1 背包一维数组:dp[w] 要读左边的旧值,所以容量从大到小遍历。"""
    global BAD
    s = Svg(1240, 560)
    c = Check(s)

    title(s, c, "0-1 背包压成一维:dp[w] 读的是左边的 dp[w-wt]",
          "例子:已经装过 wt=2,val=3 这件,现在轮到 wt=3,val=4;读的是 dp[2]")

    cw, ch = 132, 62
    x0 = 40
    y0 = 150

    # 行名写在每排左端的上方,不要放在画布左边 —— 右对齐的长标签会跑出画布。
    for i, lab in enumerate(f"w={w}" for w in range(CAP + 1)):
        ctext(s, c, f"cap{i}", x0 + i * cw + cw / 2, y0 - 22, lab, size=12, fill=MUTED)

    # 老一行:只处理完第一件(wt=2,val=3)。w=6 也放不下两件第一件,所以还是 3。
    old = ["0", "0", "3", "3", "3", "3", "3"]
    ctext(s, c, "oldtag", x0, y0 - 46, "上一行的旧值(只装过 wt=2,val=3)", size=12,
          fill=TEAL_TXT, anchor="start", weight="600")
    row_cells(s, c, "old", x0, y0, cw, ch, old, [FILL_TEAL] * (CAP + 1))

    y1 = y0 + ch + 62
    # 本行:再考虑 wt=3,val=4。dp[5] 从 3 变成 7 —— 7 正好是「两件都装」,
    # 而 dp[6] 也是 7 不是 8:每件只能用一次,装不下第三件。
    new = ["0", "0", "3", "4", "4", "7", "7"]
    ctext(s, c, "newtag", x0, y1 + ch + 24, "本行更新后(再加上 wt=3,val=4)", size=12,
          fill=WARM_TXT, anchor="start", weight="600")
    row_cells(s, c, "new", x0, y1, cw, ch, new, [FILL_WARM] * (CAP + 1))

    # 关键的一格:w=5 要读 w-wt=2。箭头**不能**横穿老那一排——会压在中间
    # 几个格子的文字上。改成走两排之间的留白,两头用竖直引出线接上。
    src_i, dst_i = 2, 5
    sx = x0 + src_i * cw + cw / 2
    dx = x0 + dst_i * cw + cw / 2
    yold_bot = y0 + ch
    ynew_top = y1
    ymid = (yold_bot + ynew_top) / 2
    s.raw(f'<path d="M {sx:.1f} {yold_bot} V {ymid:.1f} H {dx:.1f} '
          f'V {ynew_top - 2:.1f}" fill="none" stroke="{BLUE}" '
          f'stroke-width="2" stroke-linejoin="round"/>')
    s.arrow(dx, ymid, dx, ynew_top - 2, stroke=BLUE, sw=2.0)
    c.arrow("read-a", sx - 3, yold_bot, sx + 3, ymid)
    c.arrow("read-b", dx - 3, ynew_top - 2, dx + 3, ymid)
    # 说明文字放在弧线水平段下方、两排留白的中间偏左处,避开竖直引出线。
    ctext(s, c, "readlab", x0 + 1.15 * cw, ymid + 27,
          f"dp[{dst_i}] 读 dp[{dst_i}−3]=dp[{src_i}]={new[src_i]}，{new[src_i]}+4={new[dst_i]}",
          size=12, fill=BLUE)

    # 两个方向
    yb = y1 + ch + 64
    ctext(s, c, "dir-t", 620, yb - 12, "遍历方向决定读到的是哪一行", size=14, weight="600")

    s.rect(x0, yb + 8, 540, 58, fill=FILL_WARM, stroke=WARM_TXT, rx=8)
    ctext(s, c, "bad", x0 + 270, yb + 32, "从小到大 ✗", size=14,
          fill=WARM_TXT, weight="600")
    ctext(s, c, "bad2", x0 + 270, yb + 54,
          f"处理 w={dst_i} 时 dp[{src_i}] 已被本轮改写 → 读到本行，多算一件", size=11.5)

    s.rect(x0 + 620, yb + 8, 540, 58, fill=FILL_TEAL, stroke=TEAL_TXT, rx=8)
    ctext(s, c, "good", x0 + 620 + 270, yb + 32, "从大到小 ✓", size=14,
          fill=TEAL_TXT, weight="600")
    ctext(s, c, "good2", x0 + 620 + 270, yb + 54,
          f"处理 w={dst_i} 时 dp[{src_i}] 还没被碰过 → 读到上一行，正好两件都装", size=11.5)

    BAD += c.run("01-01-zero-one-reverse")
    s.save(OUT / "01-01-zero-one-reverse.svg")


# ---------------------------------------------------------------- figure 2
def fig02():
    """完全背包:转移读本行已更新过的值,所以容量从小到大遍历。"""
    global BAD
    s = Svg(1240, 560)
    c = Check(s)

    title(s, c, "完全背包:转移读的是本行已经更新过的那一格",
          f"同一件物品 wt={W1}、val={V1} 可以重复拿。右图把 w={CAP} 的完整推导链摊开")

    cw, ch = 132, 62
    x0 = 40
    y0 = 150

    for i in range(CAP + 1):
        ctext(s, c, f"cap{i}", x0 + i * cw + cw / 2, y0 - 22, f"w={i}",
              size=12, fill=MUTED)

    # 完全背包一维:从小到大, dp[w] = max(dp[w], dp[w-wt]+val)。
    # 同一件可以重复拿,所以 w=6 能放两件 → 8。
    stage = ["0", "0", "0", "4", "4", "4", "8"]
    ctext(s, c, "rowtag", x0, y0 - 46, "本行(压成一维后就只有这一行)", size=12,
          fill=WARM_TXT, anchor="start", weight="600")
    fills = [FILL_WARM] * (CAP + 1)
    fills[CAP] = FILL_GREY
    row_cells(s, c, "row", x0, y0, cw, ch, stage, fills)

    # 读同一行的左边。这里**不能**直接画一条横穿的直线:它会正好压在 w=4/w=5
    # 两个格子的文字上(Check 会报 text/arrow overlap)。改成从格子下沿绕一条弧,
    # 走格子下方的留白,两头用竖直引出线接上。
    s3x = x0 + 3 * cw + cw / 2
    d6x = x0 + 6 * cw + cw / 2
    ybot = y0 + ch
    s.raw(f'<path d="M {s3x:.1f} {ybot} V {ybot + 30:.1f} '
          f'H {d6x:.1f} V {ybot + 2:.1f}" fill="none" stroke="{BLUE}" '
          f'stroke-width="2" stroke-linejoin="round"/>')
    s.arrow(d6x, ybot + 30, d6x, ybot + 2, stroke=BLUE, sw=2.0)
    # 只登记两头那段,弧线中段悬在空格子上方,没有碰到任何文字。
    c.arrow("read2a", s3x - 3, ybot, s3x + 3, ybot + 30)
    c.arrow("read2b", d6x - 3, ybot + 2, d6x + 3, ybot + 30)
    ctext(s, c, "read2lab", (s3x + d6x) / 2, y0 - 48,
          f"dp[{CAP}] 读 dp[{CAP}−{W1}] = dp[3]，是同一行", size=12, fill=BLUE)

    # 推导链
    # 推导链:每一步 +4,步长是 wt=3。**不能**写 dp[9] —— 这一行只到 w=6,
    # w=6 是最后一个格子;写出 dp[9]=12 会凭空多出一个不存在列。
    yb = y0 + ch + 72
    ctext(s, c, "chain-t", 620, yb - 14, "推导链:每次多拿一件,容量就 +3", size=14,
          weight="600")
    chain = [("dp[0]=0", "ch0"), ("dp[3]=4", "ch1"), ("dp[6]=8", "ch2")]
    xs = [270, 620, 970]
    for i, ((lab, nm), x) in enumerate(zip(chain, xs)):
        s.rect(x - 80, yb + 6, 160, 46, fill=FILL_TEAL, stroke=TEAL_TXT, rx=6)
        ctext(s, c, nm, x, yb + 35, lab, size=14, fill=TEAL_TXT)
        if i:
            s.arrow(xs[i - 1] + 82, yb + 29, x - 84, yb + 29, stroke=LINE, sw=1.8)
            c.arrow(f"cha{i}", xs[i - 1] + 82, yb + 29, x - 84, yb + 29)
    ctext(s, c, "chain-note", 620, yb + 78, "每步都是 +4，所以拿的次数不受限制",
          size=12, fill=MUTED)

    yc = yb + 108
    s.rect(x0, yc, 1160, 46, fill=FILL_WARM, stroke=WARM_TXT, rx=8)
    ctext(s, c, "warn2", 620, yc + 29,
          f"两个背包只差一个循环方向:0-1 从大到小(读旧值)，完全从小到大(读本行)", size=13)

    BAD += c.run("02-unbounded-forward")
    s.save(OUT / "02-unbounded-forward.svg")


# ---------------------------------------------------------------- figure 3
def fig03():
    """组合数与排列数的唯一差别是外层循环是谁。"""
    global BAD
    s = Svg(1240, 600)
    c = Check(s)

    title(s, c, "同样的两层循环,换个嵌套顺序就从「组合」变成「排列」",
          "面额 = {1, 2, 3}，目标 amount = 3。两边的转移方程一字不差")

    # 左:面额外层 -> 组合
    lx, rx = 40, 640
    pw, ph = 560, 330
    py = 130

    s.rect(lx, py, pw, ph, fill=PAPER, stroke=LINE, rx=10)
    ctext(s, c, "lt", lx + pw / 2, py + 30,
          "面额在外层 → 组合数", size=15, fill=TEAL_TXT, weight="600")
    ctext(s, c, "lt2", lx + pw / 2, py + 54,
          "for c in coins:  for a in range(c, A+1):", size=12.5)

    combos = ["{1,1,1}", "{1,2}", "{2,1}", "{3}"]
    keep = [True, True, False, True]
    for i, (t, k) in enumerate(zip(combos, keep)):
        y = py + 82 + i * 40
        s.rect(lx + 40, y, pw - 80, 32, fill=FILL_TEAL if k else FILL_GREY, rx=5)
        ctext(s, c, f"lc{i}", lx + pw / 2, y + 21, t, size=13,
              fill=TEAL_TXT if k else MUTED)
        ctext(s, c, f"lk{i}", lx + pw - 54, y + 21, "算入" if k else "重复，不计",
              size=11, fill=TEAL_TXT if k else MUTED)
    ctext(s, c, "lres", lx + pw / 2, py + ph - 28,
          "答案 = 3（{1,1,1} / {1,2} / {3}）", size=13, fill=TEAL_TXT, weight="600")

    # 右:容量外层 -> 排列
    s.rect(rx, py, pw, ph, fill=PAPER, stroke=LINE, rx=10)
    ctext(s, c, "rt", rx + pw / 2, py + 30,
          "容量在外层 → 排列数", size=15, fill=WARM_TXT, weight="600")
    ctext(s, c, "rt2", rx + pw / 2, py + 54,
          "for a in range(1, A+1):  for c in coins:", size=12.5)

    perms = ["{1,1,1}", "{1,2}", "{2,1}", "{3}"]
    for i, t in enumerate(perms):
        y = py + 82 + i * 40
        s.rect(rx + 40, y, pw - 80, 32, fill=FILL_WARM, rx=5)
        ctext(s, c, f"rc{i}", rx + pw / 2, y + 21, t, size=13, fill=WARM_TXT)
        ctext(s, c, f"rk{i}", rx + pw - 54, y + 21, "算入", size=11, fill=WARM_TXT)
    ctext(s, c, "rres", rx + pw / 2, py + ph - 28,
          "答案 = 4（{1,2} 与 {2,1} 算两种）", size=13, fill=WARM_TXT, weight="600")

    # 结论:差别只在于「谁钉住了顺序」
    yb = py + ph + 46
    s.rect(40, yb, 1160, 56, fill=FILL_BLUE, stroke=BLUE, rx=8)
    ctext(s, c, "concl3", 620, yb + 24,
          "面额在外层时,每个面额只有一轮,顺序被钉死 → 组合", size=13, fill=BLUE)
    ctext(s, c, "concl3b", 620, yb + 45,
          "容量在外层时,每个容量都能重新挑任意面额 → 顺序自由 → 排列", size=13, fill=BLUE)

    ctext(s, c, "foot3", 620, yb + 82,
          "转移方程两边完全一样,唯一的差别就是哪一层在外面", size=12, fill=MUTED)

    BAD += c.run("03-combinations-vs-permutations")
    s.save(OUT / "03-combinations-vs-permutations.svg")


# ---------------------------------------------------------------- figure 4
def fig04():
    """编辑距离的三个转移来源:删除看上面、插入看左边、替换看左上角。"""
    global BAD
    s = Svg(1240, 830)
    c = Check(s)

    title(s, c, "编辑距离 dp[i][j] 的三个来源",
          "以 word1 = \"cat\"、word2 = \"cut\" 为例，看 dp[3][3] 是从哪几格走过来的")

    cw, ch = 96, 64
    # Check 的文字包围盒是「基线往上约 0.8*size、往下 0.24*size」——比看着的位置
    # 高得多。表头留白必须按包围盒算,不能按基线算(这里是踩过的坑):
    # 15px 的字上下各要 ~12/~4,所以基线离格子上沿至少留 30 才安全。
    gx, gy = 250, 230

    w1 = "cat"
    w2 = "cut"
    # 列名写在列的上方;行名不逐个写(会和格子撞),改成左侧两行说明。
    for j in range(3):
        ctext(s, c, f"h2{j}", gx + j * cw + cw / 2, gy - 100, w2[j], size=15,
              weight="600")
    ctext(s, c, "hdr-row", gx - 96, gy + ch / 2 + 5, "word1", size=13,
          fill=MUTED, anchor="start")
    ctext(s, c, "hdr-row2", gx - 96, gy + 3 * ch / 2 + 5, "word2", size=13,
          fill=MUTED, anchor="start")
    ctext(s, c, "hdr-note", gx + 1.5 * cw, gy - 150,
          f"s1 = \"{w1}\"   s2 = \"{w2}\"", size=12.5, fill=MUTED)

    # 手工算好的编辑距离表(前缀 "cat" 与 "cut")
    #        ""  c  u  t
    #   ""    0  1  2  3
    #   c     1  0  1  2
    #   a     2  1  1  2
    #   t     3  2  2  1
    tab = [[0, 1, 2, 3],
           [1, 0, 1, 2],
           [2, 1, 1, 2],
           [3, 2, 2, 1]]
    for i in range(4):
        for j in range(4):
            x = gx + (j - 1) * cw
            y = gy + (i - 1) * ch
            hot = (i, j) == (3, 3)
            s.rect(x, y, cw, ch,
                   fill=FILL_WARM if hot else (FILL_GREY if i == 0 or j == 0 else PAPER),
                   rx=4)
            ctext(s, c, f"c{i}{j}", x + cw / 2, y + ch / 2 + 6, str(tab[i][j]),
                  size=16, weight="600" if hot else "400",
                  fill=WARM_TXT if hot else INK)

    # dp[3][3] 的位置
    tx = gx + 2 * cw + cw / 2
    ty = gy + 2 * ch + ch / 2

    # 三个来源:上(删除) 左(插入) 左上(替换)。
    # 起点取源格中心、终点取目标格中心,但两头各缩 10px 留出箭头的呼吸空间;
    # 缩太多三支箭头会挤在格子角上糊成一团(这里踩过)。
    up_x, up_y = tx, ty - ch
    lf_x, lf_y = tx - cw, ty
    dl_x, dl_y = tx - cw, ty - ch

    for (nx, ny, col, name) in [(up_x, up_y, BLUE, "up"),
                                (lf_x, lf_y, TEAL_TXT, "lf"),
                                (dl_x, dl_y, WARM_TXT, "dl")]:
        s.arrow(nx + 10, ny + 10, tx - 10, ty - 10, stroke=col, sw=2.0)
        c.arrow("arr-" + name, nx + 10, ny + 10, tx - 10, ty - 10)

    # 图例
    yl = gy + 3 * ch + 44
    legend = [(BLUE, "删除:删掉 s1[i]", "看上面 dp[i-1][j] + 1"),
              (TEAL_TXT, "插入:插入 s2[j]", "看左边 dp[i][j-1] + 1"),
              (WARM_TXT, "替换:s1[i]→s2[j]", "看左上 dp[i-1][j-1] + 1")]
    for k, (col, name, detail) in enumerate(legend):
        x = 70 + k * 380
        s.rect(x, yl, 16, 16, fill=col, stroke=col, rx=3)
        ctext(s, c, f"lg-n{k}", x + 26, yl + 13, name, size=13, fill=col,
              anchor="start", weight="600")
        ctext(s, c, f"lg-d{k}", x + 26, yl + 34, detail, size=11.5, fill=MUTED,
              anchor="start")

    yc = yl + 74
    s.rect(70, yc, 1100, 54, fill=FILL_BLUE, stroke=BLUE, rx=8)
    ctext(s, c, "f4-concl", 620, yc + 22,
          "s1[3]=='t' 与 s2[3]=='t' 相等 → 直接继承左上 dp[2][2]=1，不加代价", size=13,
          fill=BLUE)
    ctext(s, c, "f4-concl2", 620, yc + 43,
          "写反左右两次的代价还可以互换，只有长度差很大时才露馅", size=12, fill=BLUE)

    BAD += c.run("04-edit-distance-arrows")
    s.save(OUT / "04-edit-distance-arrows.svg")


if __name__ == "__main__":
    fig01()
    fig02()
    fig03()
    fig04()
    print(f"\n{'OK' if BAD == 0 else str(BAD) + ' PROBLEM(S)'} — figures in {OUT}")
    sys.exit(1 if BAD else 0)
