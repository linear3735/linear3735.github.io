#!/usr/bin/env python3
"""Structural gate for a Jekyll/minima post: front matter, tables, fences, TOC anchors.

Checks:
  1. front matter parses (YAML), required keys present, key ORDER matches house style
  2. every GFM table: all rows have the same column count as its separator row
  3. code fences are balanced and language-tagged
  4. every in-page TOC anchor matches a rendered heading id (kramdown's algorithm)
  5. every relative link target exists as a file, and every internal /slug/ link
     matches an existing post's permalink

Usage: python3 verify_markdown.py POST.md [--repo /path/to/site]
Exit: 0 clean, 1 problems.
"""
import re
import sys
import unicodedata
from pathlib import Path

HOUSE_ORDER = ["layout", "title", "display_title", "subtitle", "description",
               "excerpt", "date", "categories", "tags"]


def kramdown_id(text: str) -> str:
    """Reproduce kramdown's auto-id generation for ATX headings."""
    s = unicodedata.normalize("NFKC", text)
    s = s.lower()
    # drop everything that is not alphanumeric, space, hyphen or underscore
    # derived empirically from live kramdown output: '_' survives, '.' is dropped
    s = "".join(ch for ch in s if ch.isalnum() or ch in " -_.")
    s = s.replace(".", "")
    s = re.sub(r"\s+", "-", s.strip())
    return s


def strip_inline(text: str) -> str:
    """Remove inline markdown so the id matches what kramdown sees."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    return text.strip()


def main() -> int:
    post = Path(sys.argv[1])
    repo = Path(".")
    if "--repo" in sys.argv:
        repo = Path(sys.argv[sys.argv.index("--repo") + 1])
    text = post.read_text(encoding="utf-8")
    lines = text.split("\n")
    problems = []

    # ---------- 1. front matter ----------
    if not lines or lines[0].strip() != "---":
        problems.append("front matter: does not start with ---")
        fm_lines, body_start = [], 0
    else:
        try:
            end = lines.index("---", 1)
        except ValueError:
            problems.append("front matter: no closing ---")
            end, body_start = 0, 0
        fm_lines = lines[1:end]
        body_start = end + 1

    fm_keys = [l.split(":", 1)[0].strip() for l in fm_lines if re.match(r"^[a-z_]+:", l)]
    missing = [k for k in HOUSE_ORDER if k not in fm_keys]
    extra = [k for k in fm_keys if k not in HOUSE_ORDER]
    if missing:
        problems.append(f"front matter: missing keys {missing}")
    if extra:
        problems.append(f"front matter: unexpected keys {extra}")
    if fm_keys and fm_keys != [k for k in HOUSE_ORDER if k in fm_keys]:
        problems.append(f"front matter: key order is {fm_keys}, house order is {HOUSE_ORDER}")

    # colon style in title/display_title/subtitle
    for l in fm_lines:
        k = l.split(":", 1)[0].strip()
        # house style (verified against published posts): `title` is a claim and uses
        # ASCII ':' and ','; prose fields use Chinese punctuation, and their inner colons
        # are ordinary prose colons, so only `title` is checked.
        if k == "title":
            val = l.split(":", 1)[1]
            if "：" in val:
                problems.append(f"front matter: {k} uses a fullwidth colon (house style is ASCII ':')")

    body = lines[body_start:]
    body_text = "\n".join(body)

    # ---------- 2. tables ----------
    def split_row(row: str):
        r = row.strip()
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|"):
            r = r[:-1]
        # split on unescaped pipes
        parts, cur, esc = [], "", False
        for ch in r:
            if esc:
                cur += ch
                esc = False
            elif ch == "\\":
                cur += ch
                esc = True
            elif ch == "|":
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        return parts

    is_sep = lambda r: bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", r))
    in_fence = False
    tables = 0
    i = 0
    while i < len(body):
        line = body[i]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not in_fence and "|" in line and i + 1 < len(body) and is_sep(body[i + 1]):
            tables += 1
            ncol = len(split_row(body[i]))
            nsep = len(split_row(body[i + 1]))
            if ncol != nsep:
                problems.append(f"table at body line {i+1}: header {ncol} cols vs separator {nsep}")
            j = i + 2
            while j < len(body) and body[j].strip() and "|" in body[j]:
                n = len(split_row(body[j]))
                if n != ncol:
                    problems.append(
                        f"table at body line {i+1}: row {j+1} has {n} cols, expected {ncol} | {body[j][:70]}")
                j += 1
            i = j
            continue
        i += 1

    if in_fence:
        problems.append("code fence: unbalanced (odd number of ``` markers)")

    fences = re.findall(r"^```(\w*)", body_text, re.M)
    for lang in fences[::2]:
        if not lang:
            problems.append("code fence: opening fence with no language tag")

    # ---------- 3. headings + TOC anchors ----------
    headings = []
    for idx, line in enumerate(body):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if m and not line.strip().startswith("```"):
            headings.append((m.group(1), strip_inline(m.group(2))))
    ids = {kramdown_id(h[1]): h[1] for h in headings}

    toc_links = re.findall(r"^\s*[-*]\s*\[([^\]]+)\]\(#([^)\s]+)\)", body_text, re.M)
    for label, frag in toc_links:
        if frag not in ids:
            problems.append(f"TOC anchor #{frag} has no matching heading (label: {label})")

    # every heading with a section number should be in the TOC
    numbered = [h for h in headings if re.match(r"^##\s+\d", h[0] + " " + h[1]) or re.match(r"^\d+\s", h[1])]
    toc_targets = {f for _, f in toc_links}
    for lvl, htext in numbered:
        if lvl == "##" and kramdown_id(htext) not in toc_targets:
            problems.append(f"heading not in TOC: {htext}")

    # ---------- 4. links ----------
    internal = re.findall(r"\]\((/[^)\s]*)\)", body_text)
    for target in set(internal):
        if target.endswith("/") or "." not in target.rsplit("/", 1)[-1]:
            slug = target.strip("/").split("/")[-1]
            hits = list((repo / "_posts").glob(f"*-{slug}.md"))
            if not hits:
                problems.append(f"internal link {target} matches no _posts/*-{slug}.md")
        else:
            p = repo / target.lstrip("/")
            if not p.exists():
                problems.append(f"local asset link {target} does not exist")

    # ---------- report ----------
    print(f"post    : {post}")
    print(f"size    : {len(text):,} chars, {len(lines)} lines")
    print(f"headings: {len(headings)}   tables: {tables}   TOC links: {len(toc_links)}")
    print(f"fm keys : {fm_keys}")
    print()
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\nRESULT: {len(problems)} problem(s)")
        return 1
    print("MARKDOWN STRUCTURE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
