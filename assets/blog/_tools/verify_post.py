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


# 标题锚点的危险字符:凡是 NFKC 之后会「长出 ASCII 字母或数字」的字符,
# 本地和线上就会给出不同的 id,而本地门没法自己发现这件事。
#
# 真实踩过的坑(2026-11-13 线上实测):
#   `## 5 完全二叉树的节点个数:O(log²n) 是怎么推出来的`
#     本地 kramdown_id -> `...olog2n...`   (² NFKC 成 2,isalnum 为真,留下)
#     GitHub Pages     -> `...ologn...`    (² 被丢掉)
#   目录写的是本地的那个 id,于是线上那一条锚点是死的,24 篇里唯一一条。
#
# 判定:字符不是 ASCII、又不是 CJK 汉字/假名/谚文,就报出来,
# 让人把它换成纯 ASCII 写法(如 O(log n * log n))或显式给 id。
_HAZARD_OK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def anchor_hazards(text: str) -> list:
    """返回标题里会导致 id 随渲染器版本变化的字符。"""
    out = []
    for ch in text:
        if ord(ch) < 128:
            continue
        if _HAZARD_OK.match(ch):
            continue
        if ch in "，。、；：？！（）「」『』《》—…·【】":
            continue          # 中文标点:本地线上都是直接丢,一致
        out.append(ch)
    return out


def github_id(text: str) -> str:
    """GitHub Pages 的标题 id(**只对安全字符集有把握**)。

    有把握的规则:CJK 原样保留;ASCII 字母数字转小写;空白折成一个 `-`;
    其余字符丢掉。凡是标题里出现 ASCII 标点(括号、冒号、`*` 等),
    连字符的**个数和位置我没能反推出来**,所以那种标题一律按
    anchor_hazards / anchor_key 的路子处理,不要依赖这个函数的输出。

    已实测确认的样本:
      `1 哈希表:O(1) 是怎么挣来的` -> `1-哈希表o1-是怎么挣来的`
      `0 先说明材料和我的写法`     -> `0-先说明材料和我的写法`
      `O(log²n) 是怎么推出来的`    -> `ologn-是怎么推出来的`
      `O(log n * log n)`          -> `olog-n--log-n-`   (连字符数:没把握)

    注意 `²` 这一类上标:本地 kramdown 走 NFKC 会把它变成 ASCII `2`,
    线上则直接丢掉 —— 这正是 2026-11-13 那条线上死锚点的成因。
    """
    keep = []
    for ch in text:
        if _HAZARD_OK.match(ch):                     # CJK 原样留
            keep.append(ch)
        elif ch.isspace():
            keep.append(" ")
        elif ch.isascii() and (ch.isalnum() or ch in "-_"):
            keep.append(ch)
        # 其余(含全部 ASCII 标点、括号、冒号、上标)丢掉
    s = "".join(keep).lower()
    return re.sub(r"\s+", "-", s).strip("-")


def anchor_key(slug: str) -> str:
    """把 id 折成「忽略连字符个数与位置」的比较键。

    为什么要这样:线上 id 里连字符的个数取决于标点如何参与折叠,
    这个规则我没能可靠反推(见 github_id)。但**去掉连字符之后**,
    字符本身是否一致是可以判定的 —— 而真实事故(`olog2n` vs `ologn`)
    差别正是在字符上,不是在连字符上。所以:
      · 字符级差异(上标被丢、字母不同)   -> 报错  ✅ 抓得住
      · 仅连字符个数/位置不同              -> 放过  ✅ 不误报
    """
    return re.sub(r"[-_]+", "", slug).lower()


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

    # 标题锚点里出现「本地线上会分叉」的字符就直接报出来。这类字符没法在
    # 本地验证 —— 只能要求作者换成纯 ASCII 写法。见 github_id 的注释。
    for lvl, t in headings:
        hz = anchor_hazards(t)
        if hz:
            problems.append(
                f"标题含锚点危险字符 {hz} (U+{', U+'.join(f'{ord(c):04X}' for c in hz)}): "
                f"{t!r} —— 本地与线上生成的 id 会不一致,请换成纯 ASCII 写法")

    if not toc:
        notes.append("no 目录 block; the theme builds a TOC from headings anyway")
    else:
        # 用线上真正生效的 id 做比对,但按 anchor_key 忽略连字符差异。
        # 旧版这里是 `want in i` 的子串包含,所以 `...olog2n...` 被
        # `...ologn...` 判成"包含即通过",真实死锚点就这样溜过去了。
        h2_keys = {anchor_key(github_id(t)): t for lvl, t in headings if lvl == 2}
        for lvl, t in headings:
            if lvl != 2:
                continue
            want = github_id(t)
            if anchor_key(want) not in {anchor_key(i) for i in toc_ids}:
                problems.append(f"heading not linked from 目录: {t!r} (id {want!r})")
        for _, i in toc:
            # 锚点必须对应某个 h2,允许连字符个数/位置不同,但不允许字符不同
            if anchor_key(i) not in h2_keys:
                near = [k for k in h2_keys if k[:8] == anchor_key(i)[:8]]
                hint = f", 最接近的标题是 {h2_keys[near[0]]!r}" if near else ""
                problems.append(f"目录 anchor matches no heading: #{i}{hint}")
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
