"""代码门:把正文里 ```python 块抽出来真跑,核对它印出的数字。

规矩(和 `_tools/CONVENTIONS.md` 第 7 节一致):**不要手抄一份代码去测**,
那样测的不是文章里的代码。这里从 `_posts/2026-11-14-nsight-bogus-copies.md`
里正则抽块,exec 后比对其 stdout 和正文里那段 ```text 输出。

用法:
    /opt/miniconda3/bin/python3 verify_code.py
退出码 0 = 全过。
"""

from __future__ import annotations

import io
import re
import sys
import contextlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent                  # assets/blog/<slug>-<date> -> repo
POST = REPO / "_posts" / "2026-11-14-nsight-bogus-copies.md"

import nsight_data as D                            # noqa: E402

BAD: list[str] = []


def blocks(text: str, lang: str) -> list[str]:
    """抽出所有 ```<lang> 围栏的内容。"""
    pat = re.compile(r"^```" + lang + r"\s*$\n(.*?)^```\s*$",
                     re.M | re.S)
    return [m.group(1) for m in pat.finditer(text)]


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        if detail:
            for line in detail.splitlines():
                print(f"         {line}")
        BAD.append(name)


def main() -> int:
    if not POST.exists():
        raise SystemExit(f"找不到文章: {POST}")
    text = POST.read_text(encoding="utf-8")

    # ---- 1. 正文里的 python 块要能跑,且输出要和文中的 text 块一致 ----
    py = blocks(text, "python")
    print(f"正文 python 块: {len(py)} 个")
    check("正文至少有一个 python 块", len(py) >= 1)

    # 正文那段代码只负责算,不负责打印 —— 打印语句由验证脚本补上,
    # 这样文章里贴的是可复用的函数,而不是为了凑输出写的一段脚本。
    # 路径是相对仓库根的,所以必须在仓库根下跑。
    # 正文里每个 python 块各自配一段「打印」尾巴:文章里贴的是可复用的
    # 函数,不为了让正文好看而塞一堆 print。路径相对仓库根。
    TAILS = [
        # 块 0:空隙统计
        """
print(f"在算  {good['busy']:.3f} -> {sync['busy']:.3f} ms "
      f"({sync['busy'] - good['busy']:+.3f})")
print(f"在等  {good['span'] - good['busy']:.3f} -> "
      f"{sync['span'] - sync['busy']:.3f} ms "
      f"({(sync['span'] - sync['busy']) - (good['span'] - good['busy']):+.3f})")
print(f"跨度  {good['span']:.3f} -> {sync['span']:.3f} ms "
      f"({sync['span'] - good['span']:+.3f})")
""",
        # 块 1:从作业日志重算墙钟表。它自己在正文里就打印,
        # 这里不用补尾巴(补了会打两遍,对照必然失败)。
        "",
    ]
    if len(TAILS) < len(py):
        raise SystemExit(f"正文有 {len(py)} 个 python 块,但 TAILS 只写了 "
                         f"{len(TAILS)} 段 —— 补上再跑")

    import os
    cwd = Path.cwd()
    try:
        os.chdir(REPO)
        txts = [t.rstrip("\n") for t in blocks(text, "text")]
        for i, code in enumerate(py):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(code + TAILS[i],
                                 f"<post python block {i}>", "exec"), {})
            except Exception as e:                  # noqa: BLE001
                check(f"python 块 {i} 能跑通", False, f"{type(e).__name__}: {e}")
                continue
            got = buf.getvalue().rstrip("\n")
            print(f"  ---- python 块 {i} 的输出 ----")
            for line in got.splitlines():
                print(f"    | {line}")

            # 和正文里**对应顺序**的 text 块对照。第一版是「和任意一个
            # text 块相等就算过」,那样两个块可以互相顶替,等于没测。
            #
            # 注意:正文里 text 块的顺序和 python 块的顺序并不一致
            # (python 输出、墙钟表、第 9 节的文件树),所以不能直接拿
            # text_blocks[i] 去比 —— 那样第二个 python 块会去和墙钟表比。
            # 真实输出必须以「模式」表头开头才算墙钟表,以此筛出来。
            if i == 1:
                cand = [t for t in txts if t.lstrip().startswith("模式")]
                if cand:
                    check(f"python 块 {i} 的输出与正文墙钟表一致",
                          got == cand[0],
                          f"正文墙钟表:\n{cand[0]}\n实际输出:\n{got}")
                    continue
            if i < len(txts):
                check(f"python 块 {i} 的输出与正文第 {i} 个 text 块一致",
                      got == txts[i],
                      f"正文 text 块 {i}:\n{txts[i] if i < len(txts) else '(无)'}"
                      f"\n实际输出:\n{got}")
            else:
                check(f"python 块 {i} 在正文里有对应的 text 输出", False,
                      "正文里 text 块不够")
    finally:
        os.chdir(cwd)

    # ---- 5. cpu_side 的两种运行要能解析出来 ----
    #
    # 正文第 5.1 节的核心论点是「batch=4 的 +34.8% 没复现」,所以这里必须
    # 同时核对**两遍**。只核对第 1 遍就发现不了那个结论站不住 —— 那正是
    # 这篇文章的教训本身。
    print("\n核对 cpu_side 的两遍运行(第 5.1 / 5.2 节):")
    runs = {
        1: D.RUN_LOG.read_text(encoding="utf-8"),
        2: (D.DATA / "run_434347.log").read_text(encoding="utf-8"),
    }

    # 每遍抽出 batch -> (cond, spin, gain)
    def z1b(text: str) -> dict:
        out = {}
        for m in re.finditer(r"batch=\s*(\d+) \(同步点\s*(\d+)\)\s+"
                             r"cond\s+([\d.]+) ms\s+spin\s+([\d.]+) ms\s+"
                             r"gain\s+(-?[\d.]+) %", text):
            out[int(m.group(1))] = (float(m.group(3)), float(m.group(4)),
                                    float(m.group(5)))
        return out

    z = {k: z1b(v) for k, v in runs.items()}
    for k, v in z.items():
        check(f"第 {k} 遍解析出 4 个 batch 档", len(v) == 4, f"实际 {sorted(v)}")

    if all(len(z[k]) == 4 for k in z):
        # 正文写的是 +34.8% vs +5.2% —— 差异必须真的存在
        g1, g2 = z[1][4][2], z[2][4][2]
        check(f"batch=4 两遍不一致(正文写 +34.8% / +5.2%)",
              abs(g1 - 34.8) < 0.1 and abs(g2 - 5.2) < 0.1,
              f"实际 {g1:+.1f}% / {g2:+.1f}%")

        # 正文第 5.1 节说:方向两遍一致(都是条件变量赢),但**幅度不一致**
        # —— 158 µs 对 388 µs。第一版这里断言「两遍都是 405 µs」,那是我
        # 在正文里写错、又抄进验证脚本的数(1.227 - 1.069 = 0.158,不是
        # 0.405)。断言一跑就红了 —— 这个断言存在的意义就是这个。
        d1 = (z[1][1][1] - z[1][1][0]) * 1000      # spin - cond, ms -> us
        d2 = (z[2][1][1] - z[2][1][0]) * 1000
        check("batch=1 两遍方向一致(都是条件变量赢,即 d > 0)",
              d1 > 0 and d2 > 0, f"两遍分别 {d1:.0f} µs / {d2:.0f} µs")
        check(f"batch=1 两遍的绝对差是 158 / 388 µs(正文给的是区间)",
              abs(d1 - 158) < 1.0 and abs(d2 - 388) < 1.0,
              f"两遍分别 {d1:.0f} µs / {d2:.0f} µs")
        # 正文说「优势大小不可复现,只能给区间」——区间得真的有宽度
        check("batch=1 的优势幅度确实不可复现(两遍不等)",
              abs(d1 - d2) > 100, f"两遍 {d1:.0f} / {d2:.0f} µs,差得太小")

        # 正文说 batch>=4 时自旋侧撞地板(几乎不随 batch 变)
        floors = [z[k][b][1] for k in z for b in (4, 16, 64)]
        check("batch>=4 时自旋侧确实平(地板在 0.135–0.139)",
              max(floors) - min(floors) < 0.005,
              f"跨两遍 6 个读数: {sorted(floors)}")

    # ---- 6. Z2 两遍:异步化落在 12–22%,零拷贝远大于 20% ----
    print("\n核对 Z2 两遍(第 5.2 节):")
    for k, text in runs.items():
        m = re.search(r"A -> C 异步化\s+:\s+([\d.]+) %", text)
        n = re.search(r"C -> B 零拷贝\s+:\s+([\d.]+) %", text)
        check(f"第 {k} 遍有 A->C / C->B", m and n)
    if all(re.search(r"A -> C 异步化\s+:\s+([\d.]+) %", t) for t in runs.values()):
        ac = [float(re.search(r"A -> C 异步化\s+:\s+([\d.]+) %", t).group(1))
              for t in runs.values()]
        cb = [float(re.search(r"C -> B 零拷贝\s+:\s+([\d.]+) %", t).group(1))
              for t in runs.values()]
        check(f"异步化落在正文写的 11.9–22.4% 区间",
              abs(min(ac) - 11.9) < 0.1 and abs(max(ac) - 22.4) < 0.1,
              f"实际 {ac}")
        check(f"零拷贝落在正文写的 295–323% 区间",
              abs(min(cb) - 295.0) < 0.1 and abs(max(cb) - 323.4) < 0.1,
              f"实际 {cb}")
        # 正文的论点是「零拷贝那一步远大于 20%」,两遍都要成立
        check("两遍的零拷贝都远大于 20%(正文论断的前提)",
              all(v > 200 for v in cb), f"实际 {cb}")

    # ---- 7. 正文引用的两遍倍数(第 7 节那张表) ----
    print("\n核对第 7 节表里的两遍数字:")
    for k, text in runs.items():
        m = re.search(r"shared atomics\s+:\s+([\d.]+) ms", text)
        s = re.search(r"speedup\s+:\s+([\d.]+)x", text)
        check(f"第 {k} 遍有 kernels 的 speedup", m is not None)
    kx = [float(re.search(r"speedup\s+:\s+([\d.]+)x", t).group(1))
          for t in runs.values()]
    check("正文第 7 节写 7.37x / 7.36x",
          abs(kx[0] - 7.37) < 0.01 and abs(kx[1] - 7.36) < 0.01, f"实际 {kx}")

    total = len(BAD)
    print(f"\n  code problem(s): {total}")
    if BAD:
        print("  失败项:")
        for b in BAD:
            print(f"    - {b}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
