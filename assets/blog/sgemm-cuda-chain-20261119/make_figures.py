#!/usr/bin/env python3
"""画这篇的两张图。

注意:图里的 <text> 不能设 font-family —— 图门(verify_svg.py)会拦。
图是内联在正文旁边的,必须继承 site.css 的字体栈,否则会和页面字体打架。

    cd assets/blog/sgemm-cuda-chain-20261119 && /opt/miniconda3/bin/python3 make_figures.py

  fig1  §2  优化链的实测数值与「编号顺序 != 行顺序」  —— 阶梯图
  fig2  §1  一个 warp 的地址落在几个 32 字节 sector 上 —— 条纹对比

两张图都只画正文已经出现的数,不引入新数。所有数由 CHAIN / SECTORS 这两处
原始数据算出来,不手抄。

为什么要包一层 TXT()
--------------------
`svgkit` 的 `Svg.text()` 只负责画,命中框要另调 `Check.text()` 登记。分开调很容易
「改了画的位置、忘了改登记的位置」,于是 Check 检查的是一组和画面无关的幻影,
门会一直绿。所以 TXT() 把两个动作绑成一次调用,收尾再断言「登记数 == 画的数」。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_tools"))
# 像素数据直接从代码门 import,不在图里抄第二遍 —— 抄一遍就多一个会漂移的副本。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_code as vc

from svgkit import (BLUE, CANVAS, FILL_BLUE, FILL_GREY, FILL_TEAL, FILL_WARM,
                    INK, LINE, MUTED, PAPER, TEAL_TXT, WARM_TXT, Check, Svg)

OUT = Path(__file__).resolve().parents[3] / "assets/img/sgemm-cuda-chain-20261119"
OUT.mkdir(parents=True, exist_ok=True)

BAD: list[int] = []
N_TEXT = 0
N_REG = 0


def TXT(ck: Check, name: str, x: float, y: float, t: str, **kw) -> None:
    """画一处文字,同时登记命中框。两个动作绑在一起,不允许分开调。"""
    global N_TEXT, N_REG
    ck.svg.text(x, y, t, **kw)
    N_TEXT += 1
    ck.text(name, x, y, t, size=kw.get("size", 14), anchor=kw.get("anchor", "middle"))
    N_REG += 1


def accept(ck: Check, label: str) -> None:
    """`Check.run()` 返回的是问题条数,不是问题列表。"""
    BAD.append(ck.run(label))


# ==========================================================================
# 原始数据:README 性能表(A6000, FP32, 4096x4096x4096)
# 按**表里的行顺序**抄,不是按数值排序 —— 顺序本身就是这篇要讲的事之一。
# ==========================================================================
# 链路数据也从代码门 import —— 图上画的和门上断言的必须是同一个数。
# 手抄第二份的下场是:改了门里的值,图还画着旧数,而且没人会发现。
CHAIN = [(num, name.replace("Bank Conflicts (Linearize)", "Bank Conflicts 线性化")
                     .replace("Bank Conflicts (Offset)", "Bank Conflicts 补列"),
          g) for num, name, g in vc.CHAIN]
CUBLAS = vc.chain()["cublas"]
BASE = vc.chain()["base"]

# fig2 的数据全部由 verify_code.py 的地址算术现算
NROW, NCOL = 6, 8          # 6 行 x 8 列 = 48 格,每格 = 一个 32 字节 sector


def sector_footprint():
    """三处访存在 48 格网格里各占几格 —— 直接调代码门的模型函数算。"""
    a1, b1, c1 = vc.k1()
    a2, b2, c2 = vc.k2()
    rows = [
        ("kernel 1  朴素版", "A[x*K + i]",    a1, "warp 内 x 连续 -> 32 个地址散在 32 行,各占一个 sector"),
        ("kernel 1  朴素版", "B[i*N + y]",    b1, "y 恒定 -> 广播,32 个线程读同一个地址"),
        ("kernel 1  朴素版", "C[x*N + y]",    c1, "跨行写,步长 N,每行只碰 1 个 float"),
        ("kernel 2  合并版", "A[cRow*K + i]", a2, "cRow 恒定 -> 也是广播,与 kernel 1 正好相反"),
        ("kernel 2  合并版", "B[i*N + cCol]", b2, "cCol 连续 -> 32 个 float 挤进 4 个 sector"),
        ("kernel 2  合并版", "C[cRow*N + cCol]", c2, "连续写,同样合并成 4 个 sector"),
    ]
    return [(p, e, vc.report(addrs)[1], note) for p, e, addrs, note in rows]


# ==========================================================================
# fig1  优化链阶梯图
# ==========================================================================
def fig1() -> None:
    W, H = 1180, 700
    s = Svg(W, H)
    ck = Check(s)
    s.panel(0, 0, W, H, fill=PAPER, stroke=LINE, rx=0)

    TXT(ck, "t", 40, 44, "SGEMM 优化链:一样一样加上去,性能是这样涨的",
        size=19, weight="700", anchor="start")
    TXT(ck, "st", 40, 70,
        "A6000 / FP32 / 4096x4096x4096,数字取自该仓库 README 的性能表 —— 不是我在本机测的",
        size=12, fill=MUTED, anchor="start")

    # 坐标:左侧文字区 + 右侧条区
    x_num, x_name, x_bar = 44, 76, 386
    bar_max = W - x_bar - 190
    top, rowh = 134, 38

    # 表头基线要比首行文字盒的上沿(top - size*0.80 = 123.6)再高出一个字高,
    # 否则 Check 会把表头和首行判成重叠 —— 它算的是文字盒,不是基线。
    TXT(ck, "nl", x_num, top - 24, "编号", size=11, fill=MUTED, anchor="start")
    TXT(ck, "nm", x_name, top - 24, "优化手段", size=11, fill=MUTED, anchor="start")
    TXT(ck, "nv", x_bar, top - 24, "相对于 cuBLAS 的占比", size=11, fill=MUTED, anchor="start")

    prev = None
    for i, (num, name, g) in enumerate(CHAIN):
        y = top + i * rowh
        # 行底色:最后一行(cuBLAS)是基准,单独标出
        is_ref = num == "0"
        if is_ref:
            s.rect(34, y - 13, W - 68, rowh - 4, fill=FILL_TEAL, stroke=TEAL_TXT, sw=1.0, rx=5)
        # 编号
        TXT(ck, f"n{i}", x_num, y, num, size=13, weight="700",
            fill=TEAL_TXT if is_ref else INK, anchor="start")
        # 名称
        TXT(ck, f"m{i}", x_name + 26, y, name, size=12.5,
            fill=TEAL_TXT if is_ref else INK, anchor="start")
        # 条
        pct = g / CUBLAS * 100
        bw = max(2.0, bar_max * pct / 100.0)
        fill = FILL_TEAL if is_ref else FILL_BLUE
        s.rect(x_bar, y - 9, bw, 18, fill=fill, stroke=BLUE if not is_ref else TEAL_TXT,
               sw=0.9, rx=3)
        TXT(ck, f"p{i}", x_bar + bw + 10, y, f"{pct:.1f}%   {g:.1f} GFLOPs",
            size=11.5, fill=TEAL_TXT if is_ref else MUTED, anchor="start")

        # 「编号不连续」的位置打标记:把断点标在**跳变的那一行**
        if prev is not None and int(num) != prev + 1 and not is_ref:
            s.arrow(x_num + 20, y - 4, x_num + 20, y + 4, stroke=WARM_TXT, sw=1.6, head=5)
            TXT(ck, f"brk{i}", x_name + 8, y - 15, "编号在这里断了", size=10,
                fill=WARM_TXT, anchor="start")
        if not is_ref:
            prev = int(num)

    # 结论行
    yc = top + len(CHAIN) * rowh + 18
    s.line(34, yc - 14, W - 34, yc - 14, stroke=LINE, sw=1.0)
    TXT(ck, "c1", 40, yc + 8,
        f"从第 1 级到最高一级: {CHAIN[0][2]:.1f} -> {CHAIN[-2][2]:.1f} GFLOPs,"
        f"即 {CHAIN[-2][2] / BASE:.1f} 倍",
        size=13.5, weight="600", anchor="start")
    TXT(ck, "c2", 40, yc + 32,
        f"手写最优的一级(10 Warptiling)到 cuBLAS 还差 {CUBLAS - CHAIN[-2][2]:.1f} GFLOPs,"
        f"也就是 {100 - CHAIN[-2][2] / CUBLAS * 100:.1f} 个点",
        size=12.5, fill=MUTED, anchor="start")
    TXT(ck, "c3", 40, yc + 56,
        "表里的行顺序是作者讲故事的顺序,编号是事后补的 —— 第 6 行的编号是 7,第 8 行是 11,第 9 行才是 6",
        size=12, fill=WARM_TXT, anchor="start")

    s.save(OUT / "01-chain.svg")
    accept(ck, "fig1")


# ==========================================================================
# fig2  一个 warp 的地址落在几个 sector 上
# ==========================================================================
def fig2() -> None:
    """三处访存各占几个 32 字节 sector。

    左边两栏是**未命中数**(代价),右边是**命中数**。两栏之和 = 48 格 = 这个
    warp 在 48 个 32 字节 sector 的窗口里触及的范围。填色格越少 = 同样的数据
    用了越少的事务。
    """
    W, H = 1180, 620
    s = Svg(W, H)
    ck = Check(s)
    s.panel(0, 0, W, H, fill=PAPER, stroke=LINE, rx=0)

    data = sector_footprint()
    # 注意别写 sum(n for _, _, n, _ in data if _.startswith(...)) —— 那个 `_`
    # 既是表达式位又是过滤位,取到的是同一个值,过滤条件恒为假。
    t1 = sum(r[2] for r in data if r[0].startswith("kernel 1"))
    t2 = sum(r[2] for r in data if r[0].startswith("kernel 2"))

    TXT(ck, "t", 40, 44, "同样是 32 个线程,访存代价差了 7 倍多",
        size=19, weight="700", anchor="start")
    TXT(ck, "st", 40, 70,
        f"每格 = 一个 32 字节 sector。填色格 = 这个 warp 真正用掉的事务,灰格 = 没用到的。"
        f"kernel 1 合计 {t1} 格,kernel 2 合计 {t2} 格",
        size=12, fill=MUTED, anchor="start")

    col_w, gap = 540, 60
    panels = [
        (40, "kernel 1  朴素版  blockDim(32, 32)", 0),
        (40 + col_w + gap, "kernel 2  合并版  blockDim(1024)", 1),
    ]

    cellw, cellh, cellgap = 56.0, 22.0, 6.0
    for px, ptitle, half in panels:
        rows = [r for r in data if r[0].startswith(f"kernel {half + 1}")]
        s.panel(px, 92, col_w, 386, fill=CANVAS, stroke=LINE, rx=10)
        TXT(ck, "pt" + ptitle, px + col_w / 2, 116, ptitle, size=13.5, weight="600")

        for ri, (_, expr, nsec, note) in enumerate(rows):
            ry = 140 + ri * 116
            TXT(ck, f"e{ptitle}{ri}", px + 20, ry, expr, size=12.5,
                weight="700", anchor="start")
            good = nsec <= 4
            TXT(ck, f"s{ptitle}{ri}", px + col_w - 20, ry, f"{nsec} / {NROW * NCOL} 格",
                size=12.5, weight="700", fill=TEAL_TXT if good else WARM_TXT,
                anchor="end")

            # 网格:先铺灰,再把命中的格涂上
            for c in range(NCOL):
                cx = px + 20 + c * (cellw + cellgap)
                fill = FILL_WARM if c < nsec else FILL_GREY
                s.rect(cx, ry + 12, cellw, cellh, fill=fill,
                       stroke=WARM_TXT if c < nsec else LINE,
                       sw=1.0 if c < nsec else 0.8, rx=3)
            TXT(ck, f"nt{ptitle}{ri}", px + 20, ry + 58, note, size=11,
                fill=INK, anchor="start")

    yc = 512
    s.line(40, yc - 26, W - 40, yc - 26, stroke=LINE, sw=1.0)
    TXT(ck, "c1", 40, yc,
        f"kernel 1: A 与 C 各 32 格,B 是广播只占 1 格 —— 合计 {t1} 格",
        size=13, weight="600", anchor="start")
    TXT(ck, "c2", 40, yc + 26,
        f"kernel 2: A 变成广播(1 格),B 与 C 各 4 格 —— 合计 {t2} 格,"
        f"是 kernel 1 的 {t1 / t2:.1f} 分之一",
        size=13, weight="600", fill=TEAL_TXT, anchor="start")
    TXT(ck, "c3", 40, yc + 52,
        "换的只是线程到元素的映射,算法一行没动。README 里这一步是 309.0 -> 1986.5 GFLOPs",
        size=12, fill=MUTED, anchor="start")
    TXT(ck, "c4", 40, yc + 76,
        "所以那 6.4 倍来自访存,不是来自算得更快 —— 每条线程做的乘加次数完全没变",
        size=12, fill=MUTED, anchor="start")

    s.save(OUT / "02-sectors.svg")
    accept(ck, "fig2")



def main() -> int:
    fig1()
    fig2()
    total = sum(BAD)
    if N_TEXT != N_REG:
        print(f"  !! 画的文字数 {N_TEXT} != 登记的命中框数 {N_REG}"
              f" —— 有文字绕过了 TXT(),Check 看不到它跑到哪去了")
        total += 1
    print(f"文字:画 {N_TEXT} / 登记 {N_REG}")
    print(f"figure problem(s): {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
