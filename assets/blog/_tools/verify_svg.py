#!/usr/bin/env python3
"""Check every diagram SVG in the repo is something a browser can actually read.

Motivation: `svgkit.text()` used to interpolate its label straight into the
`<text>` node.  A label containing `i < n` or `a && b` therefore produced
invalid XML, and the symptom was `sips` exiting 13 with no message at all —
which reads like a tooling problem rather than a content problem.  The toolkit
now escapes by default, but nothing *checked* the output, so the same class of
bug could come back through `.raw_text()` or hand-written SVG.

What this verifies, per file:
  1. parses as XML (catches unescaped `<`, `&`, unbalanced tags)
  2. has an <svg> root with a viewBox or width/height
  3. every <text> node has non-empty content (an empty one means a label was
     silently dropped — svgkit guards this, hand-written SVG may not)
  4. no font-family attribute, per the site convention that diagrams inherit
     the page font stack (site.css) instead of fighting it
  5. every <text> label is registered in the figure's Check() collision list,
     when a sibling generator script is available to grep

Usage:
    verify_svg.py [PATHS...] [--repo PATH]
    (default: every assets/img/**/*.svg under the repo)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.dom import minidom
from xml.parsers.expat import ExpatError


def check_one(svg: Path) -> list[str]:
    problems: list[str] = []
    raw = svg.read_text(encoding="utf-8", errors="replace")

    # 1. valid XML
    try:
        doc = minidom.parseString(raw)
    except ExpatError as e:
        return [f"{svg.name}: invalid XML ({e}) — usually an unescaped < or &"]

    # 2. root element
    root = doc.documentElement
    if root.tagName != "svg":
        problems.append(f"{svg.name}: root element is <{root.tagName}>, not <svg>")
    if not (root.getAttribute("viewBox") or
            (root.getAttribute("width") and root.getAttribute("height"))):
        problems.append(f"{svg.name}: <svg> has neither viewBox nor width+height")

    # 3. non-empty <text>
    texts = doc.getElementsByTagName("text")
    if len(texts) == 0:
        problems.append(f"{svg.name}: no <text> nodes at all — is the diagram blank?")
    for i, t in enumerate(texts):
        content = "".join(n.data for n in t.childNodes
                          if n.nodeType in (n.TEXT_NODE, n.CDATA_SECTION_NODE))
        if not content.strip():
            problems.append(f"{svg.name}: <text> #{i} is empty")

    # 4. no hardcoded font-family
    for t in texts:
        if t.getAttribute("font-family"):
            problems.append(
                f"{svg.name}: <text> sets font-family — diagrams must inherit "
                f"the page font stack (site.css)")
            break

    # 5. labels registered with Check(), if we can find the generator
    labels = [("".join(n.data for n in t.childNodes
                       if n.nodeType in (n.TEXT_NODE, n.CDATA_SECTION_NODE))).strip()
              for t in texts]
    labels = [l for l in labels if l]
    gens = list(svg.parent.glob("*.py")) + list(svg.parent.parent.glob("*.py"))
    if gens and labels:
        blob = "\n".join(g.read_text(encoding="utf-8", errors="replace") for g in gens)
        if "Check(" in blob:
            missing = [l for l in labels
                       if l not in blob and l.replace("&amp;", "&") not in blob]
            if missing:
                problems.append(
                    f"{svg.name}: {len(missing)} label(s) not registered in Check() "
                    f"— collisions won't be detected: "
                    + "; ".join(repr(m) for m in missing[:3]))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    if args.paths:
        svgs = [Path(p) for p in args.paths]
    else:
        svgs = sorted(Path(args.repo).expanduser().resolve().glob("assets/img/**/*.svg"))

    if not svgs:
        print("  no SVG files found")
        return 0

    all_problems: list[str] = []
    by_dir: dict[str, list[int]] = {}
    for svg in svgs:
        p = check_one(svg)
        all_problems += p
        key = svg.parent.name
        by_dir.setdefault(key, [0, 0])
        by_dir[key][1] += 1
        if not p:
            by_dir[key][0] += 1

    print(f"  checked : {len(svgs)} SVG files")
    for k in sorted(by_dir):
        ok, tot = by_dir[k]
        mark = "ok" if ok == tot else "FAIL"
        print(f"    {mark:>4s}  {k:44s} {ok}/{tot}")
    print()

    if all_problems:
        print(f"  SVG FAIL — {len(all_problems)} problem(s):")
        for p in all_problems:
            print("   - " + p)
        return 1
    print("  SVG OK — every diagram parses, has text, and inherits the page font")
    return 0


if __name__ == "__main__":
    sys.exit(main())
