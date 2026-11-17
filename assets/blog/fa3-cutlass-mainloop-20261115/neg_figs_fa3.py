#!/usr/bin/env python3
"""反证 make_figures.py 那道图门真的会红 —— 对每一处都造一个必然触发它的错误。

    /opt/miniconda3/bin/python3 /tmp/neg_figs_fa3.py

**为什么必须做这件事（两次）**

第一次：`Check.run()` 的返回值和 `sys.exit()` 最容易接错。历史上的
`exit(1 if BAD else 0)`（BAD 是列表，恒为真）和「永远退出 0」看起来一样绿，
所以对每一类校验各造一个错误，确认门**分别**报出来。

第二次（更有价值）：第一版驱动把突变打在 `s.text()` 上，三处画面全搞坏了，
门**照绿**。原因不是驱动写错，而是图脚本把「画」和「登记」分成了两次调用、
坐标各传一份 —— `Check` 查的是一组和画面无关的幻影。脚本因此改成 `TXT()`
一次做完，驱动也跟着打在 `TXT()` 的坐标上（那才是门真正在查的值）。

用例 5 专门钉住这件事：绕过 `TXT()` 直接 `s.text()`，收尾守卫必须报。

另外：语法错也会让 exit=1，但那不是「门变红」。所以 `run()` 额外检查脚本
有没有真的跑到底（输出里要有 `figure problem(s)`），否则记成 999。
第一版驱动只看关键词，把一个 SyntaxError 误判成了「门没抓到」。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 仓库根由脚本自身位置推导:这个文件在 assets/blog/<slug>-<date>/ 下,
# 上溯三层就是仓库根。写死绝对路径的话,换台机器或换个目录就全失效。
REPO = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO / "assets/blog/fa3-cutlass-mainloop-20261115/make_figures.py"
PY = "/opt/miniconda3/bin/python3"


def run() -> tuple[int, str]:
    # 必须跑**被就地改写的 SCRIPT**,不能跑副本。
    # 调试期间这里曾指向 /tmp/_mut.py,于是所有突变都改在别处、门跑的是原文件:
    # 用例 1–4 的「RED」全是假绿(基线本来就绿),用例 5 的守卫也永远不会响。
    r = subprocess.run([PY, str(SCRIPT)], cwd=REPO, capture_output=True, text=True)
    out = r.stdout + r.stderr
    # 崩掉（语法错 / 导入失败）也会 exit=1，但那是脚本坏了，不是门变红。
    crashed = "Traceback (most recent call last)" in out or "figure problem(s)" not in out
    return (999 if crashed else r.returncode), out


# 每个用例:(名字, 锚点, 替换, 期望门报的关键词)
CASES = [
    # 1) fig1 两个面板标题叠到同一个 x -> text/text
    ("文字重叠",
     'TXT(ck, "pt:" + ptitle, px + PANEL_W / 2 - 12, 112, ptitle,',
     'TXT(ck, "pt:" + ptitle, 356, 112, ptitle,',
     "text/text overlap"),

    # 2) fig1 结论行推到画布外 -> off-canvas
    ("文字出画布",
     'TXT(ck, "concl", W / 2, 390, concl, size=13, weight="600")',
     'TXT(ck, "concl", W / 2, 1200, concl, size=13, weight="600")',
     "off-canvas"),

    # 3) fig1 比率行的文字拉长:中心仍在面板内、两端戳出去 -> spills out of
    #    (把它挪到 px-240 是「出画布」不是「戳出面板」;面板溢出的定义是
    #     文字**中心**在面板内、左右边界超出面板。)
    ("文字戳出面板",
     'note = f"EX2 / WGMMA = {ratio:.2f}"',
     'note = f"EX2 / WGMMA = {ratio:.2f}" + "溢" * 30',
     "spills out of"),

    # 4) fig2 的轨道标签拖到画布右边界外 -> off-canvas(换一张图,确认不是只有 fig1 在查)
    ("fig2 文字出画布",
     'TXT(ck, "tk2", 14, 286,',
     'TXT(ck, "tk2", 1500, 286,',
     "off-canvas"),

    # 5) 绕过 TXT() 直接 s.text():画一处、登记零处 -> 收尾守卫必须报
    ("绕过 TXT() 直接画(守卫必须抓到)",
     '    accept(ck, "fig1")',
     '    s.text(W / 2, 200, "偷偷画的一行", size=12)\n    accept(ck, "fig1")',
     "画的文字数和登记的命中框数不一致"),
]


def main() -> int:
    shutil.copy2(SCRIPT, Path(tempfile.mkdtemp()) / "make_figures.py")
    orig = SCRIPT.read_text(encoding="utf-8")

    rc0, out0 = run()
    print(f"基线:{'绿' if rc0 == 0 else '红'} (exit={rc0})")
    if rc0 != 0:
        print(out0[-2000:])
        print("基线都不绿,后面没意义")
        return 1

    results = []
    for name, old, new, want in CASES:
        if orig.count(old) != 1:
            print(f"  ?? 用例「{name}」锚点出现 {orig.count(old)} 次(应为 1),跳过")
            results.append((name, None))
            continue
        SCRIPT.write_text(orig.replace(old, new, 1), encoding="utf-8")
        rc, out = run()
        hit = want is None or want in out
        ok = (rc == 0) if want is None else (rc != 0 and hit)
        results.append((name, ok))
        tag = "RED" if rc != 0 else "green"
        extra = "  期望仍绿" if want is None else (
            f"  期望 {want!r} {'命中' if hit else '**没命中**'}")
        print(f"  {'ok ' if ok else 'XX '} {name}: exit={rc} ({tag}){extra}")
        if not hit and want:
            print("      门实际报的:")
            for line in out.splitlines():
                if line.strip().startswith("!!"):
                    print("      " + line.strip())
        SCRIPT.write_text(orig, encoding="utf-8")

    SCRIPT.write_text(orig, encoding="utf-8")
    rc1, out1 = run()
    print(f"\n还原后:{'绿' if rc1 == 0 else '红'} (exit={rc1})")
    if rc1 != 0:
        print(out1[-1500:])

    bad = [n for n, ok in results if ok is False]
    skipped = [n for n, ok in results if ok is None]
    print(f"\n用例 {len(results)} 个:{len(results) - len(bad) - len(skipped)} 通过,"
          f" {len(bad)} 失败, {len(skipped)} 跳过")
    if bad:
        print("失败:" + ", ".join(bad))
    if skipped:
        print("跳过(锚点失效,驱动要更新):" + ", ".join(skipped))
    ok_all = not bad and not skipped and rc0 == 0 and rc1 == 0
    print(f"negcontrol-figs exit={'0' if ok_all else '1'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
