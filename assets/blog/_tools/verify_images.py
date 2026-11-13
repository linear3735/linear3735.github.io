#!/usr/bin/env python3
"""校验文章里的图片引用:文件存在、alt 非空、没有孤儿 SVG、没有被重复使用。

为什么不复用 verify_post.py 的正则
----------------------------------
`verify_post.py` 里数图片用的是 `!\\[([^\\]]*)\\]\\(([^)]+)\\)` 这类正则。
`[^\\]]*` 遇到 alt 文本里的方括号就提前收尾 —— 而本系列大量 alt 写的是
`dp[11]`、`preSum[0]`、`[1,2,3]` 这种方括号内容。后果是那一条引用**整条被
跳过**,既不报错也不计数,门却照样显示 OK。这个坑在写 bfs 那篇时已经踩过一次
(alt 里带 `[1,2,3]` 导致 `images: 4` 而不是 6)。

所以这个脚本自己写扫描器:对 `![` 之后的 alt 做**方括号配对计数**,
对 `(` 之后的路径做**圆括号配对计数**,允许嵌套。

用法:
    python3 assets/blog/_tools/verify_images.py                 # 扫全部本系列文章
    python3 assets/blog/_tools/verify_images.py _posts/x.md ...  # 只扫指定文件
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # assets/blog/_tools
REPO = HERE.parents[2]                          # 仓库根

# 本系列的文章;别的在制文章(定量化/推理那些)不归这里管
SERIES_GLOB = "2026-1[12]-*.md"
NOT_SERIES = re.compile(r"2026-11-0[467]-")     # 11-04 / 11-06 / 11-07 是别的系列


def find_images(src: str) -> list[tuple[int, str, str]]:
    """返回 [(行号, alt, 路径), ...],alt 允许含方括号。"""
    out: list[tuple[int, str, str]] = []
    i, n = 0, len(src)
    while True:
        i = src.find("![", i)
        if i < 0:
            break
        # 行首才算图片:排除 `![` 出现在行内代码或正文里的情形
        line_start = src.rfind("\n", 0, i) + 1
        if src[line_start:i].strip():
            i += 2
            continue
        # --- 定位 alt / 路径 的分界 ---
        #
        # 这一段我改了四版才稳,把结论写在这儿:**不要试图「配对」方括号**。
        #
        # 原因是 alt 里可以有**不成对**的方括号。sliding-window 那篇 L55 的 alt 是
        # 「窗口 [left, right)：右指针只往前扩,左指针只往前缩」—— 那个 `[` 配的是
        # 一个**全角**「）」,不是 `]`。按半角规则数,深度永远回不到 0:
        #   · 如果放任它跨界扫 -> 一路吃到文件末尾,这条引用连同后面的全被吞掉;
        #   · 如果限制在本行内   -> 深度仍不归零,这条引用被跳过,
        #     而且它的 `]` 正好在行尾(`\n` 之前),边界情况更难看出来。
        #
        # 可靠的做法是找**结构标记** `](`:markdown 图片是 `![alt](src)`,
        # alt 里出现一个字面 `](` 的可能性极低。所以在**本行内**从左往右
        # 找第一个后面紧跟 `(` 的 `]`,它就是 alt 的收尾。
        # 方括号仍按嵌套计数,用来跳过 `![a[b]c](x)` 里的 `]`。
        line_end = src.find("\n", i)
        if line_end < 0:
            line_end = n
        j, depth, found = i + 2, 1, -1
        while j < line_end:
            ch = src[j]
            if ch == "\\":
                j += 2
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0 or src[j + 1:j + 2] == "(":
                    found = j
                    break
            j += 1
        if found < 0:
            i += 2
            continue
        j = found
        alt = src[i + 2:j]
        # --- 配对扫描路径 ---
        #
        # j 指向 alt 的收尾 `]`,所以 j+1 就是那个 `(`。先把它消费掉(k = j+2),
        # 再从 depth2 = 1 开始找配对的 `)`:收尾时 k-1 就是 `)` 的下标,
        # 于是路径正好是 src[j+2 : k-1]。
        #
        # 这里连着踩了两个坑,都记下来:
        # (a) 不能从 k = j+1 起扫 —— 那个 `(` 会被当成第一个嵌套括号,
        #     深度多算一层,扫描器以为还欠一个 `)`,一路吃穿全文;
        # (b) 走到收尾的 `)` 时要**先记下标再 break**。如果一边自减一边 break,
        #     深度变成 -1,后面的合法性判断就会误判成「没找到」。
        #     (b) 的表现很阴:路径会少掉最后一个字符(`.svg` 变成 `.sv`),
        #     于是**每一条引用**都报「文件不存在」——126 个假警报。
        #
        # 另:只数**半角**括号。alt 里出现全角「）」是常态(中文标点),
        # 它是普通字符、不参与配对;一旦也去数,深度永远平不了。
        k, depth2 = j + 2, 1
        end = -1
        while k < n:
            if src[k] == "\\":
                k += 2
                continue
            if src[k] == "(":
                depth2 += 1
            elif src[k] == ")":
                depth2 -= 1
                if depth2 == 0:
                    end = k
                    break
            k += 1
        if end < 0:
            i += 2
            continue
        target = src[j + 2:end].strip()
        lineno = src.count("\n", 0, i) + 1
        out.append((lineno, alt, target))
        i = k
    return out


def series_posts() -> list[Path]:
    return [p for p in sorted((REPO / "_posts").glob(SERIES_GLOB))
            if not NOT_SERIES.match(p.name)]


def main(argv: list[str]) -> int:
    posts = ([Path(a) for a in argv[1:]] if len(argv) > 1 else series_posts())
    problems: list[str] = []
    used: dict[str, list[str]] = {}
    total = 0

    for post in posts:
        if not post.exists():
            problems.append(f"{post}: 文件不存在")
            continue
        src = post.read_text(encoding="utf-8")
        for lineno, alt, target in find_images(src):
            total += 1
            if not alt.strip():
                problems.append(f"{post.name}:{lineno}: alt 为空 -> {target}")
            if target.startswith(("http://", "https://")):
                continue
            rel = target.lstrip("/")
            used.setdefault(rel, []).append(f"{post.name}:{lineno}")
            if not (REPO / rel).exists():
                problems.append(f"{post.name}:{lineno}: 文件不存在 -> {target}")

    on_disk = {str(f.relative_to(REPO))
               for f in (REPO / "assets/img").glob("*-2026*/*.svg")}
    orphans = sorted(on_disk - set(used))

    print(f"  文章      : {len(posts)} 篇")
    print(f"  图片引用  : {total} 条")
    print(f"  盘上 SVG  : {len(on_disk)} 个")
    for rel, where in sorted(used.items()):
        if len(where) > 1 and rel in on_disk:
            problems.append(f"同一张图被多处引用: {rel} <- {', '.join(where)}")
    if orphans:
        print(f"\n  未被引用的 SVG ({len(orphans)}):")
        for o in orphans:
            print(f"    {o}")
    if problems:
        print(f"\n  问题 ({len(problems)}):")
        for p in problems:
            print(f"    {p}")
        print("\nIMAGES FAIL")
        return 1
    print("\nIMAGES OK — 每条引用都指向真实文件,alt 非空,无重复引用")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
