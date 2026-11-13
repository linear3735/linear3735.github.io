#!/usr/bin/env python3
"""Structural gate for any labuladong-series post.

Checks the house style this series follows, so twenty-odd posts stay
consistent and nothing silently regresses:

  * front matter present, keys in the house order, date format correct
  * `layout: post`, ASCII `:` and `,` in `title` (Chinese punctuation there
    breaks the feed and the og:title)
  * headings are `## N 标题:副题` and every `##`/`###` is reachable from the
    post's own 目录 block
  * fences are balanced and every fence carries a language tag — an untagged
    fence renders as an unstyled block on this site
  * code fences are `python` or `cpp` only (this series is Python 3 + C++)
  * every referenced image exists on disk and is a real SVG
  * no unrendered Liquid

Usage: python3 verify_post.py POST.md [--repo PATH]
Exit: 0 clean, 1 problems.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FM_ORDER = ["layout", "title", "display_title", "subtitle", "description",
            "excerpt", "date", "categories", "tags"]
ALLOWED_LANGS = {"python", "cpp", "text", "bash", "json", "yaml"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$")


def kramdown_id(text: str) -> str:
    """kramdown's auto-id: NFKC, lowercase, keep alnum/space/-/_/., drop '.',
    collapse whitespace runs to a single hyphen."""
    import unicodedata
    s = unicodedata.normalize("NFKC", text).lower()
    s = "".join(c for c in s if c.isalnum() or c in " -_.")
    s = s.replace(".", "")
    return re.sub(r"\s+", "-", s).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("post")
    ap.add_argument("--repo", default=str(Path.home() / "projects/linear3735.github.io"))
    args = ap.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    path = Path(args.post)
    if not path.is_absolute():
        path = (repo / path).resolve()

    problems, notes = [], []
    text = path.read_text(encoding="utf-8")

    # ---------- front matter ----------
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        problems.append("no front matter")
        fm_keys = []
    else:
        fm_keys, seen, last = [], set(), -1
        for line in m.group(1).splitlines():
            km = re.match(r"^([A-Za-z_]+):", line)
            if not km:
                continue
            k = km.group(1)
            if k in seen:
                problems.append(f"front matter key repeated: {k}")
            seen.add(k)
            fm_keys.append(k)
            if k in FM_ORDER:
                idx = FM_ORDER.index(k)
                if idx < last:
                    problems.append(f"front matter out of house order: {k}")
                last = idx
        for k in ("layout", "title", "date"):
            if k not in seen:
                problems.append(f"front matter missing {k}")
        if "layout: post" not in m.group(1):
            problems.append("layout should be `post`")
        dm = re.search(r"^date:\s*(.+)$", m.group(1), re.M)
        if dm and not DATE_RE.match(dm.group(1).strip()):
            problems.append(f"date format wrong: {dm.group(1)!r}")
        tm = re.search(r'^title:\s*"?(.*?)"?\s*$', m.group(1), re.M)
        if tm:
            t = tm.group(1)
            for ch, why in (("：", "fullwidth colon"), ("，", "fullwidth comma")):
                if ch in t:
                    problems.append(f"title contains {why}; use ASCII in `title` ({t!r})")

    # ---------- fences ----------
    fences = list(re.finditer(r"^```(\w*)\s*$", text, re.M))
    if len(fences) % 2:
        problems.append(f"odd number of fence lines ({len(fences)}) — unbalanced")
    langs, blocks = [], []
    for i in range(0, len(fences) - 1, 2):
        lang = fences[i].group(1)
        langs.append(lang)
        blocks.append(text[fences[i].end():fences[i + 1].start()])
    if not fences:
        notes.append("no fences in this post")
    untagged = langs.count("")
    if untagged:
        problems.append(f"{untagged} fence(s) with no language tag")
    bad_lang = sorted({l for l in langs if l and l not in ALLOWED_LANGS})
    if bad_lang:
        problems.append(f"disallowed fence language(s): {bad_lang} (series is python + cpp)")
    n_py, n_cpp = langs.count("python"), langs.count("cpp")
    if fences and n_py == 0:
        problems.append("no ```python block")
    if fences and n_cpp == 0:
        problems.append("no ```cpp block")
    if n_py and n_py != n_cpp:
        problems.append(f"python/cpp blocks unequal: {n_py} vs {n_cpp} "
                        "(series shows both for every solution)")

    # ---------- headings + TOC ----------
    headings = [(len(h.group(1)), h.group(2).strip())
                for h in re.finditer(r"^(#{2,4})\s+(.*)$", text, re.M)]
    h2 = [t for lvl, t in headings if lvl == 2]
    if len(h2) < 2:
        problems.append(f"only {len(h2)} level-2 headings")
    toc = re.findall(r"\[([^\]]+)\]\(#([^)]+)\)", text)
    toc_ids = {i for _, i in toc}
    if not toc:
        notes.append("no 目录 block; the theme builds a TOC from headings anyway")
    else:
        for lvl, t in headings:
            if lvl != 2:
                continue
            want = kramdown_id(t)
            # the TOC may point at the heading directly or at a slug variant
            if want not in toc_ids and not any(want in i for i in toc_ids):
                problems.append(f"heading not linked from 目录: {t!r} (id {want!r})")
        for _, i in toc:
            # an id must correspond to some heading, else it is a dead anchor
            if not any(kramdown_id(t).startswith(i[:12]) or i in kramdown_id(t)
                       for _, t in headings):
                problems.append(f"目录 anchor matches no heading: #{i}")
        if len(toc) != len(h2):
            notes.append(f"目录 has {len(toc)} links for {len(h2)} level-2 headings")

    # ---------- images ----------
    #
    # 原来这里写的是 `re.findall(r"!\[[^\]]*\]\(([^)\s]+)", text)`。
    # `[^\]]*` 遇到 alt 文本里的方括号就提前收尾,于是**整条引用被静默跳过**:
    # 既不报「文件不存在」,也不报「SVG 没有文字」。本系列里 `dp[11]`、
    # `preSum[0]`、`[left, right)` 这种 alt 很常见,所以这个洞是真的漏。
    # 实测:dp-basics 与 knapsack 各有一条引用被漏掉,而门一直显示 OK。
    #
    # 改成调用 verify_images.find_images() 的扫描器(它按 `](` 这个结构标记
    # 定位,不依赖方括号配对,理由见那边的注释)。import 失败时退回旧正则,
    # 只影响计数,不会把门弄崩。
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from verify_images import find_images as _find_images
        imgs = [t for _, _, t in _find_images(text)]
    except Exception:                                  # noqa: BLE001
        imgs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", text)
    for src in imgs:
        rel = src.lstrip("/")
        if src.startswith("http"):
            notes.append(f"remote image: {src}")
            continue
        p = repo / rel
        if not p.exists():
            problems.append(f"image missing on disk: {src}")
        elif p.suffix != ".svg":
            notes.append(f"image is not SVG: {src}")
        else:
            body = p.read_text(encoding="utf-8")
            if "<text" not in body:
                problems.append(f"SVG has no <text>: {src}")
            if re.search(r"<text[^>]*>\s*</text>", body):
                problems.append(f"SVG has an empty <text>: {src}")
            if 'font-family="' in body:
                notes.append(f"SVG hardcodes a font-family (should inherit): {src}")

    # ---------- Liquid ----------
    if text.count("{{") != text.count("}}") or text.count("{%") != text.count("%}"):
        problems.append("unbalanced Liquid braces")

    # ---------- report ----------
    print(f"  post      : {path.name}")
    print(f"  size      : {len(text):,} chars, {text.count(chr(10))} lines")
    print(f"  headings  : {len(headings)} ({len(h2)} h2)   TOC links: {len(toc)}")
    print(f"  fences    : {len(blocks)} (python {n_py}, cpp {n_cpp}, text {langs.count('text')})")
    print(f"  images    : {len(imgs)}")
    print(f"  fm keys   : {fm_keys}")
    for n in notes:
        print(f"  note      : {n}")
    if problems:
        print()
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n  RESULT: {len(problems)} problem(s)")
        return 1
    print("\n  POST STRUCTURE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
