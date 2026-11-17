"""代码门:把正文里 ```python 块抽出来真跑,核对它印出的结果。

规矩(和 `_tools/CONVENTIONS-GPU.md` 第 7 节一致):**不要手抄一份代码去测**,
那样测的不是文章里的代码。这里从 `_posts/2026-11-15-fa3-cutlass-mainloop.md`
里正则抽块,exec 后比对它的 stdout 和正文里那段 ```text 输出。

这一篇的配对比上一篇难,因为正文的 ```text 块不止一种用途:

  * 第 3 节那张「五环」结构图
  * 第 6.2 节的 sm100 文件树
  * 第 3.1 节和第 6.1 节里的**上游原文**(那句注释,前后两版)
  * 剩下的才是 python 块的真实输出

所以**不能按下标配对**。上一版按 `text_blocks[i]` 比过,在这个结构下
第二个 python 块会去和结构图比,必然失败 —— 而且失败信息会指向错误的
位置。这里改成:每个 python 块在 `OUTPUT_MARKER` 里声明自己输出里
**独有**的一行,拿它去筛出对应的 text 块,筛不中就直接报错。

用法(必须在仓库根目录下跑,正文里的路径是相对仓库根的):
    /opt/miniconda3/bin/python3 assets/blog/fa3-cutlass-mainloop-20261115/verify_code.py
退出码 0 = 全过。
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent                  # assets/blog/<slug>-<date> -> repo
POST = REPO / "_posts" / "2026-11-15-fa3-cutlass-mainloop.md"

BAD: list[int] = []

# 每个 python 块输出里独有的一行。用它把对应的 ```text 块筛出来。
# 顺序必须和正文里 python 块的出现顺序一致;数量对不上就报错,
# 这样「正文加了一个 python 块但忘了在这里登记」不会静默通过。
OUTPUT_MARKER = [
    "合计 49 条",                      # 块 0 §0   总账
    "FP8  时 EX2 / WGMMA = 1.00",      # 块 1 §2   p13 的 cycle 算术
    "1024 个 tile 映射到",              # 块 2 §4.1 p20 的 tile 映射
    "  sha256 d8f7bef971566efe",       # 块 3 §4.4 快照与锚点核对
    "幻灯片报的 FP8    1300 TFLOP/s",   # 块 4 §5   硬件包络
    "FP16 加速比             论文",      # 块 5 §5   论文 vs 幻灯片
    "  sha256  d8f7bef97156  ->",      # 块 6 §6.1 快照 vs main
]


def blocks(text: str, lang: str) -> list[str]:
    """抽出所有 ```<lang> 围栏的内容。"""
    pat = re.compile(r"^```" + lang + r"\s*$\n(.*?)^```\s*$", re.M | re.S)
    return [m.group(1) for m in pat.finditer(text)]


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        if detail:
            for line in detail.splitlines():
                print(f"         {line}")
        BAD.append(1)


def main() -> int:
    if not POST.exists():
        raise SystemExit(f"找不到文章: {POST}")
    text = POST.read_text(encoding="utf-8")

    # ---- 1. 正文里的 python 块要能跑,且输出要和文中的 text 块逐字符一致 ----
    py = blocks(text, "python")
    txts = [t.rstrip("\n") for t in blocks(text, "text")]
    print(f"正文 python 块 {len(py)} 个 / text 块 {len(txts)} 个")

    check("正文 python 块数量与 OUTPUT_MARKER 登记一致",
          len(py) == len(OUTPUT_MARKER),
          f"正文 {len(py)} 个,登记 {len(OUTPUT_MARKER)} 个")
    if len(py) != len(OUTPUT_MARKER):
        print("\ncode problem(s): 1")
        return 1

    # 正文里那几段上游原文(text 块)不含 marker,这里先确认它们**不会**
    # 被任何 marker 误筛 —— 否则配对就串了。
    #
    # 这句话在正文里出现在 3 个 text 块里,不是 2 个:
    #   a) §3.1 引的旧版(相对偏移)
    #   b) §4.4 那个核对脚本的输出末尾(它也把注释打出来了)
    #   c) §6.1 main 上的新版(绝对索引)
    # 第一版这里写的是 2,门直接报了 3 —— 是**检查写错了**,不是正文错了。
    upstream_quotes = [t for t in txts if "// Each step does" in t]
    check("含那句注释的 text 块恰好 3 个(§3.1 旧版 / §4.4 输出 / §6.1 新版)",
          len(upstream_quotes) == 3, f"实得 {len(upstream_quotes)} 段")
    check("旧版用相对偏移、新版用绝对索引,两版确实不一样",
          any("iter n_block - 1" in t for t in upstream_quotes)
          and any("gemm1 for iter n_block + 1" in t for t in upstream_quotes),
          "两版的上游原文没有同时出现")

    cwd = Path.cwd()
    try:
        os.chdir(REPO)
        for i, code in enumerate(py):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(code, f"<post python block {i}>", "exec"), {})
            except Exception as e:                  # noqa: BLE001
                check(f"python 块 {i} 能跑通", False, f"{type(e).__name__}: {e}")
                continue

            got = buf.getvalue().rstrip("\n")
            print(f"  ---- python 块 {i} 的输出 ----")
            for line in got.splitlines():
                print(f"    | {line}")

            marker = OUTPUT_MARKER[i]
            cand = [t for t in txts if marker in t]
            if len(cand) != 1:
                check(f"python 块 {i} 能唯一定位到正文的 text 块",
                      False,
                      f"marker {marker!r} 命中 {len(cand)} 个 text 块")
                continue
            check(f"python 块 {i} 的输出与正文 text 块逐字符一致",
                  got == cand[0],
                  f"正文:\n{cand[0]}\n实际:\n{got}")
    finally:
        os.chdir(cwd)

    print(f"\ncode problem(s): {sum(BAD)}")
    return 1 if sum(BAD) else 0


if __name__ == "__main__":
    sys.exit(main())
