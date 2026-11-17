#!/usr/bin/env python3
"""画这篇的三张图。

    /opt/miniconda3/bin/python3 make_figures.py

三张图都从**正文里已经出现的数**画，不引入新数：
  fig1  §2    p13 的 cycle 账，FP16 vs FP8 —— 冰柱图
  fig2  §3.1  一个 fwd_step 里谁和谁重叠 —— 时间线
  fig3  §4.1  1024 个 tile 怎么分给 132 个 CTA —— 覆盖图

为什么要包一层 TXT()
--------------------
`svgkit` 里 `Svg.text()` 只负责画，命中框要另调 `Check.text()` 登记，
而且**坐标是分开传的**。这么写很容易「改了画面的位置、忘了改登记的位置」，
于是 `Check` 检查的是一组和实际画面无关的幻影，门会一直绿。

这不是假设。这个脚本的第一版就是分开调的，反证驱动 `/tmp/neg_figs_fa3.py`
把画面故意搞坏三处，门**全部照绿**；而用例「只画不登记」反而变红，
正好指出脱节的就是那一环。

所以现在：`TXT()` 一次画 + 登记，`Svg.label()` 也走它（label 只是
anchor="start" 的 text），收尾断言「登记数 == 画的数」。

顺带一个坑：辅助函数本来叫 `T`，而 fig3 的局部变量也叫 `T`（图标题的字符串）。
`T(ck, ..., T, ...)` 里那个 `T` 到底是函数还是字符串，靠遮蔽规则决定 ——
能跑，但读的人一定误会。所以改叫 `TXT()`，图标题的变量改名 `title`。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "assets/blog/_tools"))

from svgkit import (BLUE, FILL_BLUE, FILL_GREY, FILL_TEAL, FILL_WARM,  # noqa: E402
                    INK, LINE, MUTED, PAPER, TEAL_TXT, WARM_TXT, Check, Svg)

OUT = REPO / "assets/img/fa3-cutlass-mainloop-20261115"

BAD: list[int] = []
N_TEXT = 0          # 通过 TXT() 画的文字数
N_REG = 0           # 通过 TXT() 登记的命中框数


def TXT(ck: Check, name: str, x: float, y: float, t: str, **kw) -> None:
    """画一处文字，同时登记命中框。**两个动作绑在一起，不允许分开调。**

    `kw` 透传给 `Svg.text()`；`Check.text()` 只吃 `size` 和 `anchor`，
    所以只挑这两个过去，否则颜色之类的参数会让它报错。
    """
    global N_TEXT, N_REG
    ck.svg.text(x, y, t, **kw)
    N_TEXT += 1
    ck.text(name, x, y, t, size=kw.get("size", 14), anchor=kw.get("anchor", "middle"))
    N_REG += 1


def accept(ck: Check, label: str) -> None:
    """`Check.run()` 返回的是**问题条数**，不是问题列表。"""
    BAD.append(ck.run(label))


# ==========================================================================
# fig1  两张冰柱图：同一个 block 的 EX2 与 WGMMA 各占多少 cycle
# ==========================================================================

def fig1() -> None:
    W, H = 940, 430
    s = Svg(W, H)
    ck = Check(s)

    title = "同一个 128×192 block：WGMMA 与 EX2 各占多少 cycle"
    TXT(ck, "title", W / 2, 34, title, size=17, weight="600")
    sub = "数字全部由《2 整场演讲里唯一能独立验算的一段》那段脚本算出；柱长按 cycle 等比"
    TXT(ck, "sub", W / 2, 56, sub, size=11.5, fill=MUTED)

    # 两个面板，横向并排。**刻度必须统一** —— 两个面板要做视觉对比，
    # 各用各的缩放就没有可比性了。
    #
    # 第一版这里柱子戳出了面板右边界：3072 cycle 按当时的比例画成 307px，
    # 起点在面板内 156px 处，超出去 16px。几何门没报，因为它只查**文字**的
    # 溢出和碰撞，不查矩形 —— 所以这一处是肉眼看出来的，记在这里。
    PANEL_X, PANEL_W = 70, 384
    # 标签列与柱区分开:标签用 anchor="start" 从 px 起画,柱区必须从
    # px + LBW 之后开始,否则标签右端会伸进柱子里 —— 第一版就是这个错
    # (`MUFU.EX2` 的尾巴被柱子盖住),而 **Check 查不到**:它只校验文字与
    # 文字、文字与箭头,不校验文字与矩形。是看图看出来的。
    LBW = 106                                 # 标签列宽,够放下 "MUFU.EX2"
    BX = LBW + 8
    BW_MAX = 240                              # 柱区最大长度
    SCALE = BW_MAX / 3400.0                   # px per cycle，两个面板共用

    PANELS = [
        ("FP16  张量核 4096 FLOPS/cycle", PANEL_X, [
            ("WGMMA", 3072, FILL_BLUE, BLUE),
            ("MUFU.EX2", 1536, FILL_WARM, WARM_TXT),
        ]),
        ("FP8  张量核 8192 FLOPS/cycle", PANEL_X + PANEL_W + 56, [
            ("WGMMA", 1536, FILL_BLUE, BLUE),
            ("MUFU.EX2", 1536, FILL_WARM, WARM_TXT),
        ]),
    ]
    BH = 46

    for ptitle, px, bars in PANELS:
        ck.panel(ptitle, px - 12, 84, PANEL_W, 268)
        s.panel(px - 12, 84, PANEL_W, 268)
        TXT(ck, "pt:" + ptitle, px + PANEL_W / 2 - 12, 112, ptitle,
            size=13, weight="600")

        y = 146
        for name, cyc, fill, stroke in bars:
            TXT(ck, "nm:" + name + ptitle, px, y + 3, name,
                size=12.5, fill=MUTED, anchor="start")
            bw = cyc * SCALE
            assert BW_MAX + 12 <= PANEL_W - 84, "柱子会戳出面板"
            s.rect(px + BX, y - BH / 2, bw, BH, fill=fill, stroke=stroke, sw=1.3)
            TXT(ck, "v:" + name + ptitle, px + BX + bw / 2, y + 5, str(cyc),
                size=14, weight="600", fill=stroke)
            y += 78

        ratio = bars[1][1] / bars[0][1]
        note = f"EX2 / WGMMA = {ratio:.2f}"
        TXT(ck, "r:" + ptitle, px + PANEL_W / 2 - 12, 330, note,
            size=13, weight="600", fill=WARM_TXT if ratio >= 1 else INK)

    concl = ("FP8 把张量核那一侧砍到 1536 cycle，EX2 一动不动还是 1536 ——"
             "于是它占的比例从一半变成全部。")
    TXT(ck, "concl", W / 2, 390, concl, size=13, weight="600")
    concl2 = ("这张图里的 3072 / 1536 / 1536 三个数，"
              "来自《2 整场演讲里唯一能独立验算的一段》里那段脚本的输出。")
    TXT(ck, "concl2", W / 2, 410, concl2, size=11.5, fill=MUTED)

    accept(ck, "fig1")
    s.save(OUT / "01-ex2-vs-wgmma-cycles.svg")


# ==========================================================================
# fig2  一个 fwd_step 的时间线：wgmma 与 EX2 重叠在哪一段
# ==========================================================================

def fig2() -> None:
    W, H = 940, 470
    s = Svg(W, H)
    ck = Check(s)

    title = "一个 fwd_step 里谁和谁重叠：warpgroup_wait<1>() 等的不是它刚发射的那一批"
    TXT(ck, "title", W / 2, 34, title, size=17, weight="600")
    sub = ("行号是钉住那个 commit（L925–L954）的；横轴按 cycle 等比 —— "
           "两组 wgmma 各 3072 cycle，EX2 占 1536 cycle")
    TXT(ck, "sub", W / 2, 56, sub, size=11.5, fill=MUTED)

    # 横轴**按 cycle 等比**。这是这张图的重点：重叠必须是真重叠，
    # 不能靠手排分数摆出来。
    #
    # 上一版的两个错误：
    #   1) 手排分数，结果 wait<1> 落在 gemm0 结束之后 —— 画出来等于
    #      「gemm0 早跑完了才去等它」，和正文讲的因果反了。
    #   2) 主线程那条道塞了 6 个长标签，756px 装不下，Check 报了 10 处重叠。
    #      按 cycle 等比之后，原来那些「空档」全没了。
    # 改法：不再给主线程画 6 个方块。用虚线标出 wait 的起止，其余交给
    # 下面四行文字。图要说清的只有一件事 ——
    # **EX2 那个方块整个落进 gemm1 的条里**。
    # 柱区从 L 起,左侧 150px 留给轨道名 —— 第一版 L=108,"wgmma 张量核"
    # 的尾巴被 gemm0 的柱子压住了。**Check 查不到**(它不校验文字与矩形),
    # 是看图看出来的。
    N = 3072                       # 一组 wgmma 的 cycle 数
    L, R = 150, 906

    def X(c):
        return L + (R - L) * c / (2 * N)          # 0 .. 6144 cycle

    TXT(ck, "tk1", 14, 190, "wgmma 张量核", size=12, fill=MUTED, anchor="start")
    s.line(14, 186, R + 10, 186, stroke=LINE, sw=1.2)
    TXT(ck, "tk2", 14, 286, "MUFU.EX2", size=12, fill=MUTED, anchor="start")
    s.line(14, 282, R + 10, 282, stroke=LINE, sw=1.2)

    # 两组 wgmma，各 3072 cycle，首尾相接
    for c0, c1, lab in ((0, N, "gemm0  异步发射（wg_wait=-1）   L934"),
                        (N, 2 * N, "gemm1  异步发射   L937")):
        s.rect(X(c0), 169, X(c1) - X(c0), 34, fill=FILL_BLUE, stroke=BLUE,
               sw=1.3, rx=4)
        TXT(ck, "g" + lab, (X(c0) + X(c1)) / 2, 190, lab,
            size=11.5, weight="600", fill=BLUE)

    # EX2：3200 起，1536 cycle，整个落在 gemm1 的条里
    s.rect(X(3200), 265, X(4736) - X(3200), 34, fill=FILL_TEAL, stroke=TEAL_TXT,
           sw=1.3, rx=4)
    TXT(ck, "ex2", (X(3200) + X(4736)) / 2, 286, "EX2 与 online_softmax   L947",
        size=11, weight="600", fill=TEAL_TXT)

    # 重叠区：gemm1 ∩ EX2。左边界从 gemm1 的分界（N）起 —— 上一版从 3200 起，
    # 跨进了 gemm0 一格，画出来像 gemm0 也参与了重叠。
    s.rect(X(N), 158, X(4736) - X(N), 134, fill="none", stroke=WARM_TXT,
           sw=2.0, rx=6, dash="6 4")
    TXT(ck, "ov", (X(N) + X(4736)) / 2, 312, "重叠区", size=12, weight="600",
        fill=WARM_TXT)

    # wait 的起止线
    for c, lab, anc in ((1600, "wait<1> L939 进", "end"),
                        (N, "gemm0 走完，wait<1> 返回", "start"),
                        (2 * N, "gemm1 走完，wait<0> 返回", "end")):
        s.line(X(c), 130, X(c), 300, stroke=WARM_TXT, sw=1.6, dash="5 4")
        TXT(ck, "w" + lab, X(c) + (-6 if anc == "end" else 6), 122, lab,
            size=11, fill=WARM_TXT, anchor=anc)

    notes = [
        ("wait<1> 从 cycle 1600 等到 3072 —— wgmma.wait_group 等的是「最早那组」，"
         "而 gemm0 正好在 3072 走完。", INK, 12, "400"),
        ("它只保证 gemm0 完成（它读的 K 马上要 release）；gemm1 读的 V 要到 "
         "wait<0> 之后才 release，所以 gemm1 继续在飞。", INK, 12, "400"),
        ("于是 EX2 那 1536 cycle 整个落在 gemm1 的条里 —— "
         "这就是 EX2/WGMMA = 1.00 想换到的东西。", WARM_TXT, 12, "600"),
        ("warpgroup_wait<1>() 的 1 不是「第 1 个」，是「最多留 1 个分组在飞」。"
         "我第一遍就是在这里读反的。", MUTED, 11.5, "400"),
    ]
    yy = 352
    for text, col, size, wt in notes:
        TXT(ck, "n" + str(yy), W / 2, yy, text, size=size, fill=col, weight=wt)
        yy += 26

    accept(ck, "fig2")
    s.save(OUT / "02-mainloop-overlap-timeline.svg")


# ==========================================================================
# fig3  1024 个 tile 分给 132 个 CTA
# ==========================================================================

def fig3() -> None:
    """画 CTA 96 —— 它是**最典型**的那种 CTA，不是最好看的那个。

    第一版画的是 CTA 0（它的 8 个 tile 是 0,132,…,924，列起来最省事），
    然后在图注和正文里写「每个 CTA 只碰到 2 个 head」。**这是错的。**
    实际分布（脚本算过）：

        碰到 2 个 head： 24 个 CTA
        碰到 3 个 head： 32 个 CTA
        碰到 4 个 head： 76 个 CTA

    CTA 0 属于那 24 个的**少数**，拿它当例子会让读者以为 2 个是常态。
    CTA 96 才是中间那批：8 个 tile，跨 head 3 和 head 7，四个 batch 全碰。
    """
    W, H = 940, 560
    s = Svg(W, H)
    ck = Check(s)

    title = "1024 个 tile 分给 132 个 CTA：以 CTA 96 为例"
    TXT(ck, "title", W / 2, 34, title, size=17, weight="600")
    sub = ("tile 索引 = ((batch × 8) + head) × 32 + block，"
           "所以同一格（一个 head 的一个 batch）里有 32 个 block 位置")
    TXT(ck, "sub", W / 2, 56, sub, size=11.5, fill=MUTED)

    X0, Y0 = 96, 110
    CWD, RHT = 92, 74
    NW = 32
    CW = (CWD - 10) / NW
    BH = 30

    def tile(head, batch, blk):
        return ((batch * 8) + head) * 32 + blk

    # CTA 96 拿到的 8 个 tile（跨步 132：96, 228, 360, ... 1020）
    MINE = set(range(96, 1024, 132))
    assert len(MINE) == 8, len(MINE)

    for head in range(8):
        cx = X0 + head * CWD
        TXT(ck, f"hc{head}", cx + CWD / 2 - 5, Y0 - 12, f"head {head}",
            size=11.5, fill=MUTED)
    for batch in range(4):
        cy = Y0 + batch * RHT
        TXT(ck, f"bc{batch}", X0 - 14, cy + BH / 2 + 4, f"batch {batch}",
            size=11.5, fill=MUTED, anchor="end")
        for head in range(8):
            cx = X0 + head * CWD
            for blk in range(NW):
                t = tile(head, batch, blk)
                s.rect(cx + blk * CW, cy, CW - 0.7, BH,
                       fill=FILL_WARM if t in MINE else (
                           FILL_BLUE if blk % 4 == 0 else PAPER),
                       stroke=LINE, sw=0.5, rx=0.8)

    for t in sorted(MINE):
        blk = t % 32
        hb = t // 32
        head, batch = hb % 8, hb // 8
        cx = X0 + head * CWD + blk * CW + CW / 2
        cy = Y0 + batch * RHT + BH / 2
        TXT(ck, "m" + str(t), cx, cy + 3.5, f"{blk}",
            size=8.5, weight="600", fill=WARM_TXT)

    yy = Y0 + 4 * RHT + 22
    lines = [
        ("橙色 = CTA 96 拿到的 8 个 tile（96, 228, 360, … 1020），"
         "它们的 block 是 0, 4, 8, 12, 16, 20, 24, 28。", WARM_TXT, 12.5, "600"),
        ("这 8 个落在 head 3 和 head 7 两列上，每列 4 个 batch 各一个。"
         "block 每次前进 4，是因为 132 / 32 = 4。", INK, 12, "400"),
        ("但不是每个 CTA 都这样：碰到 2 个 head 的只有 24 个，"
         "碰到 3 个的有 32 个，碰到 4 个的有 76 个 —— 多数 CTA 会跨过 batch 的边界。",
         INK, 12, "400"),
        ("1024 = 100 × 8 + 32 × 7：编号 0–99 的 CTA 拿 8 个 tile，"
         "编号 100–131 的拿 7 个。没有重复也没有遗漏。", MUTED, 12, "400"),
    ]
    for text, col, size, wt in lines:
        TXT(ck, "n" + str(yy), W / 2, yy, text, size=size, fill=col, weight=wt)
        yy += 22

    accept(ck, "fig3")
    s.save(OUT / "03-tile-to-cta-mapping.svg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    # 守卫:数**所有**被画出来的文字,再和登记的命中框数对比。
    #
    # 不能只靠 `TXT()` 里的自增:那样计数器只数得到走过 `TXT()` 的那些,而
    # 「绕过 TXT() 直接 s.text()」正好是它数不到的一类 —— 计数器和被计数的
    # 东西绑在同一个函数里,守卫永远不会响。反证驱动第 5 个用例就是这么漏的。
    #
    # 所以挂在 `Svg.text` / `Svg.raw_text` 上:不管从哪条路画,都被数到。
    # 挂在类上而不是实例上,`Check(svg)` 内部用的那个 `svg` 也一并覆盖。
    n_drawn = 0

    def _wrap(method_name: str) -> None:
        orig = getattr(Svg, method_name)

        def wrapper(self, *a, **kw):
            global n_drawn
            n_drawn += 1
            return orig(self, *a, **kw)
        setattr(Svg, method_name, wrapper)

    _wrap("text")
    _wrap("raw_text")

    fig1()   # -> 01  §2
    fig2()   # -> 02  §3.1 时间线
    fig3()   # -> 03  §4.1 覆盖图
    total = sum(BAD)
    if n_drawn != N_REG:
        print(f"  !! 画的文字数和登记的命中框数不一致:画了 {n_drawn},"
              f"登记 {N_REG} —— 有文字绕过了 TXT(),Check 看不到它跑到哪去了")
        total += 1
    print(f"\n文字:画 {n_drawn} / 登记 {N_REG}")
    print(f"figure problem(s): {total}")
    sys.exit(1 if total else 0)
