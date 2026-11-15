"""生成这一篇的所有 SVG 图。

规矩:**每个数字都从 nsight_data 重算**,图里不出现手写常量。
所以改了实验、换了日志,重跑这个脚本图就跟着变 —— 不会出现
「正文是新的、图是旧的」。

用法:
    /opt/miniconda3/bin/python3 make_figs.py
产物:
    ../../nsight-bogus-copies-20261114-*.svg  (由 FIGDIR 决定)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_tools"))
sys.path.insert(0, str(HERE))

import svgkit as K                                    # noqa: E402
import nsight_data as D                               # noqa: E402

OUT = HERE / "figs"
BAD: list[int] = []


def _finish(svg, check, name: str) -> None:
    bad = check.run(name)
    BAD.append(bad)
    OUT.mkdir(exist_ok=True)
    svg.save(OUT / f"{name}.svg")
    print(f"  {name}.svg   {'ok' if bad == 0 else f'{bad} 处问题'}")


def _med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


# =====================================================================
# 图 1:GPU 时间线 —— 把「等」画出来
#
# 这是全篇的主图。它回答的问题是:优化前优化的不是「算得快不快」,
# 而是「有多少时间根本不在算」。
# =====================================================================

def fig_timeline() -> None:
    W, H = 1080, 540
    svg = K.Svg(W, H)
    ck = K.Check(svg)

    svg.text(W / 2, 34, "同一份计算,三种同步方式:GPU 到底有多少时间在干活",
             size=19, weight="600")
    ck.text("title", W / 2, 34,
            "同一份计算,三种同步方式:GPU 到底有多少时间在干活", size=19)

    traces = D.gaps()
    order = ["good", "sync", "errsync"]
    label = {
        "good": "good",
        "sync": "sync",
        "errsync": "errsync",
    }
    desc = {
        "good": "只读写该写的地方",
        "sync": "每轮同步拷贝回来",
        "errsync": "每轮多一次多余同步",
    }

    # x0 要给左侧标签留够 190px:第一版只留了 130,标签最长那条
    # 直接跑到负坐标去了。
    x0, bw = 200.0, 700.0
    # 统一用最大跨度当坐标尺,三条才能横向比较
    full = max(traces[m].span_ms for m in order)

    top = 84.0
    rowh = 112.0
    track_h = 26.0

    for k, mode in enumerate(order):
        t = traces[mode]
        y = top + k * rowh
        scale = bw / full

        svg.text(x0 - 16, y + track_h * 0.62, label[mode], size=14,
                 anchor="end", fill=K.INK, weight="600")
        ck.text(f"lab{k}", x0 - 16, y + track_h * 0.62, label[mode], size=14,
                anchor="end")
        svg.label(x0 - 16, y + track_h * 0.62 + 17, desc[mode], size=11.5,
                  anchor="end")
        ck.text(f"desc{k}", x0 - 16, y + track_h * 0.62 + 17, desc[mode],
                size=11.5, anchor="end")

        # 轨道底色 = 整个跨度(也就是「墙钟时间」)
        svg.rect(x0, y, bw, track_h, fill=K.FILL_WARM, stroke=K.LINE, rx=3)

        # 把 kernel 区间画成实心块
        for s, e in D.busy_segments(mode):
            bx = x0 + s * scale
            bwd = max(0.6, (e - s) * scale)
            svg.rect(bx, y, bwd, track_h, fill=K.BLUE, stroke="none", rx=0)

        # 跨度端点
        ex = x0 + t.span_ms * scale
        svg.line(ex, y - 6, ex, y + track_h + 6, stroke=K.MUTED, sw=1.2,
                 dash="3 3")

        # 右侧:等的时间占比
        pct = t.gap_duty * 100
        ptxt = f"{pct:.0f}% 在等"
        svg.text(x0 + bw + 14, y + track_h * 0.62, ptxt, size=13.5,
                 anchor="start", fill=K.WARM_TXT, weight="600")
        ck.text(f"pct{k}", x0 + bw + 14, y + track_h * 0.62, ptxt, size=13.5,
                anchor="start")

        # 轨道下方数字注
        note = (f"kernel {t.kernels} 个 · 在算 {t.busy_ms:.3f} ms · "
                f"总跨度 {t.span_ms:.3f} ms · 空隙 {t.gap_ms:.3f} ms")
        svg.label(x0, y + track_h + 20, note, size=12)
        ck.text(f"note{k}", x0, y + track_h + 20, note, size=12,
                anchor="start")

    # 图例
    ly = top + 3 * rowh - 6
    svg.rect(x0, ly, 26, 13, fill=K.BLUE, stroke="none", rx=2)
    svg.label(x0 + 34, ly + 11, "GPU 在跑 kernel", size=12)
    ck.text("leg1", x0 + 34, ly + 11, "GPU 在跑 kernel", size=12, anchor="start")
    svg.rect(x0 + 190, ly, 26, 13, fill=K.FILL_WARM, stroke=K.LINE, rx=2)
    svg.label(x0 + 224, ly + 11, "GPU 在等(空隙)", size=12)
    ck.text("leg2", x0 + 224, ly + 11, "GPU 在等(空隙)", size=12,
            anchor="start")

    # 这句话里的每个数都必须和正文口径一致。
    # 踩过的坑:原来写的是「sync 多等 {gap 差} ms」—— gap 是「kernel 之间
    # 的空隙」,而正文说的「在等」是 idle = gap + tail。两者不等:
    # gap 差 1.412 = idle 差 1.387 + tail 差 0.025。图里把 gap 差叫成
    # 「多等」,就和正文的 1.387 对不上了。现在两个数都给,并写明关系。
    g_good, g_sync = traces["good"], traces["sync"]
    tail = ("三条轨道的「在算」时间一模一样,差别全在等:"
            f"在等多 {g_sync.idle_ms - g_good.idle_ms:.3f} ms"
            f"(其中空隙 {g_sync.gap_ms - g_good.gap_ms:.3f}"
            f" + 尾 {g_sync.tail_ms - g_good.tail_ms:+.3f}),"
            f"总跨度 +{(g_sync.span_ms / g_good.span_ms - 1) * 100:.0f}%。")
    svg.label(x0, ly + 40, tail, size=12.5)
    ck.text("tail", x0, ly + 40, tail, size=12.5, anchor="start")

    _finish(svg, ck, "fig-timeline")


# =====================================================================
# 图 2:三种「多余操作」各自要付多少
# =====================================================================

def fig_wallclock() -> None:
    W, H = 940, 440
    svg = K.Svg(W, H)
    ck = K.Check(svg)

    title = "三种多余操作,各自的代价(同一份 kernel,同一次迭代)"
    svg.text(W / 2, 34, title, size=19, weight="600")
    ck.text("title", W / 2, 34, title, size=19)

    w = D.wallclock()
    base = w["good"].elapsed_ms
    order = [("good", "good\n基线"), ("sync", "sync\n同步拷贝"),
             ("errsync", "errsync\n多余同步"), ("alloc", "alloc\n每轮分配"),
             ("all", "all\n三者全开")]

    x0, plot_h = 150.0, 240.0
    top = 76.0
    row_h = plot_h / len(order)
    bar_h = row_h * 0.56
    scale = (W - x0 - 200) / max(w[m].elapsed_ms for m, _ in order)

    for k, (mode, lbl) in enumerate(order):
        v = w[mode].elapsed_ms
        y = top + k * row_h + (row_h - bar_h) / 2
        bw = v * scale

        fill = K.FILL_GREY if mode == "good" else K.FILL_WARM
        svg.rect(x0, y, bw, bar_h, fill=fill, stroke=K.LINE, rx=3)

        # 标签(两行,斜杠分隔的写法不用,免得 hitbox 算错)
        for j, part in enumerate(lbl.split("\n")):
            svg.text(x0 - 14, y + bar_h / 2 + (j - 0.5) * 15 + 5, part,
                     size=13, anchor="end",
                     fill=K.INK, weight="600" if j == 0 else "400")
            ck.text(f"lbl{k}{j}", x0 - 14,
                    y + bar_h / 2 + (j - 0.5) * 15 + 5, part, size=13,
                    anchor="end")

        mult = v / base
        txt = f"{v:.1f} ms" + ("" if mode == "good" else f"   {mult:.2f}x")
        svg.text(x0 + bw + 12, y + bar_h / 2 + 5, txt, size=13,
                 anchor="start", weight="600" if mode != "good" else "400",
                 fill=K.MUTED if mode == "good" else K.WARM_TXT)
        ck.text(f"val{k}", x0 + bw + 12, y + bar_h / 2 + 5, txt, size=13,
                anchor="start")

    note = (f"iters={w['good'].iters} n={w['good'].n}  "
            f"五种模式 checksum 全部等于 {w['good'].checksum} —— "
            "它们算的是同一件事,差别只在夹带的多余操作。")
    svg.label(x0, top + plot_h + 34, note, size=12)
    ck.text("note", x0, top + plot_h + 34, note, size=12, anchor="start")

    _finish(svg, ck, "fig-wallclock")


# =====================================================================
# 图 3:共享内存原子操作 / 打包传输
# =====================================================================

def fig_kernels() -> None:
    W, H = 1000, 440
    svg = K.Svg(W, H)
    ck = K.Check(svg)

    title = "两个只在 kernel 里做的优化"
    svg.text(W / 2, 34, title, size=19, weight="600")
    ck.text("title", W / 2, 34, title, size=19)

    k = D.kernels()

    panels = [
        ("[X] 归并计数:全局原子 vs 共享内存原子",
         f"n={k.n:,}  ngroups={k.ngroups}",
         [("全局 atomicAdd", k.global_ms, K.FILL_WARM),
          ("共享内存 atomicAdd", k.shared_ms, K.FILL_TEAL)],
         f"{k.shared_speedup:.2f}x"),
        ("[Y] 邻居交换:6 次小拷贝 vs 打包成 1 次",
         f"face_len={k.face_len:,}  nfaces={k.nfaces}",
         [("6 次独立拷贝", k.separate_ms, K.FILL_WARM),
          ("打包后 1 次拷贝", k.packed_ms, K.FILL_TEAL)],
         f"{k.packed_speedup:.2f}x"),
    ]

    ph = 140.0
    top = 72.0
    # 条形起点要给左侧标签留出 230px:第一版 bx=58 减 10 当标签右边界,
    # 「共享内存 atomicAdd」这种长标签左端直接被推到负坐标。
    bx = 290.0
    for pi, (name, sub, bars, verdict) in enumerate(panels):
        y = top + pi * (ph + 44)
        svg.rect(40, y, W - 80, ph, fill=K.CANVAS, stroke=K.LINE, rx=8)

        svg.text(60, y + 28, name, size=14.5, anchor="start", weight="600")
        ck.text(f"pn{pi}", 60, y + 28, name, size=14.5, anchor="start")
        svg.label(60, y + 48, sub, size=12)
        ck.text(f"ps{pi}", 60, y + 48, sub, size=12, anchor="start")

        bscale = 330.0 / max(v for _, v, _ in bars)
        for bi, (bl, bv, fill) in enumerate(bars):
            by = y + 68 + bi * 28
            bw = max(3.0, bv * bscale)
            svg.rect(bx, by, bw, 19, fill=fill, stroke=K.LINE, rx=3)
            svg.text(bx - 12, by + 14, bl, size=12.5, anchor="end", fill=K.INK)
            ck.text(f"b{pi}{bi}l", bx - 12, by + 14, bl, size=12.5,
                    anchor="end")
            vt = f"{bv:.4f} ms"
            svg.text(bx + bw + 12, by + 14, vt, size=12.5, anchor="start",
                     fill=K.MUTED)
            ck.text(f"b{pi}{bi}v", bx + bw + 12, by + 14, vt, size=12.5,
                    anchor="start")

        svg.text(W - 80, y + 92, verdict, size=28, anchor="end",
                 weight="700", fill=K.TEAL_TXT)
        ck.text(f"verdict{pi}", W - 80, y + 92, verdict, size=28, anchor="end")

    note = "两组都在计时前先和 CPU 参考实现对过答案,数值不一致就不进统计。"
    svg.label(40, top + 2 * ph + 44 + 14, note, size=12)
    ck.text("note", 40, top + 2 * ph + 44 + 14, note, size=12, anchor="start")

    _finish(svg, ck, "fig-kernels")


# =====================================================================
# 图 4:sync 的账本 —— 多出来的时间到底花在哪
# =====================================================================

def fig_ledger() -> None:
    W, H = 940, 440
    svg = K.Svg(W, H)
    ck = K.Check(svg)

    title = "多出来的时间,一分钱都没花在计算上"
    svg.text(W / 2, 34, title, size=19, weight="600")
    ck.text("title", W / 2, 34, title, size=19)

    t = D.gaps()
    b, s = t["good"], t["sync"]

    # 堆叠条:good 的构成 -> sync 的构成
    x0, bw = 130.0, 560.0
    top = 96.0
    bh = 46.0
    scale = bw / s.span_ms

    for k, (mode, tr) in enumerate([("good", b), ("sync", s)]):
        y = top + k * 112
        svg.text(x0 - 16, y + bh / 2 + 6, mode, size=15, anchor="end",
                 weight="600")
        ck.text(f"m{k}", x0 - 16, y + bh / 2 + 6, mode, size=15, anchor="end")

        # 整条轨道 = 总跨度(底色调 = 在等)
        svg.rect(x0, y, tr.span_ms * scale, bh, fill=K.FILL_WARM,
                 stroke=K.LINE, rx=3)
        # 在算的部分
        svg.rect(x0, y, tr.busy_ms * scale, bh, fill=K.BLUE,
                 stroke="none", rx=3)
        mx = x0 + tr.busy_ms * scale
        svg.line(mx, y - 6, mx, y + bh + 6, stroke=K.INK, sw=1.6)

        bt = f"在算 {tr.busy_ms:.3f} ms"
        svg.text(x0 + tr.busy_ms * scale / 2, y + bh / 2 + 5, bt, size=12.5,
                 fill="#ffffff", weight="600")
        ck.text(f"bt{k}", x0 + tr.busy_ms * scale / 2, y + bh / 2 + 5, bt,
                size=12.5)

        # 「在等」和「总跨度」都放到轨道下方。第一版把「在等」塞在
        # 等待区正中、把「总跨度」放在轨道右侧 —— good 的等待区只有
        # 57px 宽,两个标签直接压在一起。
        s1 = f"在等 {tr.idle_ms:.3f} ms"
        s2 = f"总跨度 {tr.span_ms:.3f} ms"
        s3 = f"(= 空隙 {tr.gap_ms:.3f} + 尾 {tr.tail_ms:.3f})"
        ck.text(f"gt{k}", x0, y + bh + 20, s1, size=12.5, anchor="start")
        svg.text(x0, y + bh + 20, s1, size=12.5, anchor="start",
                 fill=K.WARM_TXT, weight="600")
        ck.text(f"st{k}", x0 + 150, y + bh + 20, s2, size=12.5, anchor="start")
        svg.label(x0 + 150, y + bh + 20, s2, size=12.5)
        ck.text(f"tp{k}", x0 + 300, y + bh + 20, s3, size=12.5, anchor="start")
        svg.label(x0 + 300, y + bh + 20, s3, size=12.5)

    # 差额:用恒等式收尾,不出现无法解释的余数
    ly = top + 2 * 112 + 6
    svg.line(x0 - 90, ly, x0 + bw, ly, stroke=K.LINE, sw=1.2)

    head = "sync 比 good:"
    svg.text(x0 - 90, ly + 30, head, size=13.5, anchor="start", weight="600")
    ck.text("head", x0 - 90, ly + 30, head, size=13.5, anchor="start")

    lines = [
        f"总跨度  {s.span_ms - b.span_ms:+.3f} ms",
        f"在算    {s.busy_ms - b.busy_ms:+.3f} ms    <- 零",
        f"在等    {s.idle_ms - b.idle_ms:+.3f} ms    (= 总跨度的增量)",
    ]
    for j, ln in enumerate(lines):
        yy = ly + 30 + (j + 1) * 24
        hit = "<- 零" in ln
        svg.text(x0 - 90, yy, ln, size=13.5, anchor="start",
                 weight="600" if hit else "400",
                 fill=K.WARM_TXT if hit else K.INK)
        ck.text(f"ln{j}", x0 - 90, yy, ln, size=13.5, anchor="start")

    _finish(svg, ck, "fig-ledger")


def main() -> int:
    print("生成图:")
    fig_timeline()
    fig_wallclock()
    fig_kernels()
    fig_ledger()

    total = sum(BAD)
    print(f"  layout problem(s): {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
