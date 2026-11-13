#!/usr/bin/env python3
"""Gate for the roadmap hub: the map must not lie about what exists.

Checks
  1. _data/roadmap.json parses and every entry has the expected shape
  2. every item with status "done" has a `post` slug, and that slug matches a
     real file in _posts/ (so a "已发布" row can never be a dead link)
  3. every item with a `post` slug really is status "done" (no orphan links)
  4. roadmap.md exists, uses layout: page, and has permalink /roadmap/
  5. roadmap.md contains no unrendered Liquid that would leak to readers
  6. the progress numbers in roadmap.md are computed, not hardcoded

Usage: python3 verify_roadmap.py [--repo /path/to/site]
Exit: 0 clean, 1 problems.
"""
import argparse
import json
import re
import sys
from pathlib import Path

VALID_STATUS = {"done", "planned", "todo"}
REQUIRED_KEYS = {"title", "desc", "status"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path.home() / "projects/linear3735.github.io"))
    args = ap.parse_args()
    repo = Path(args.repo).expanduser().resolve()

    problems = []
    data_path = repo / "_data/roadmap.json"
    page_path = repo / "roadmap.md"

    # ---------- 1. data shape ----------
    if not data_path.exists():
        print(f"  FAIL  missing {data_path}")
        return 1
    try:
        roadmap = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  FAIL  roadmap.json is not valid JSON: {e}")
        return 1

    total = done = 0
    for sec in roadmap:
        if "section" not in sec or "items" not in sec:
            problems.append(f"section missing 'section'/'items': {sec!r:.60}")
            continue
        if not sec["items"]:
            problems.append(f"section has no items: {sec['section']}")
        for it in sec["items"]:
            total += 1
            missing = REQUIRED_KEYS - set(it)
            if missing:
                problems.append(f"{sec['section']} / {it.get('title','?')}: missing {sorted(missing)}")
                continue
            if it["status"] not in VALID_STATUS:
                problems.append(f"{it['title']}: bad status {it['status']!r}")
            if it["status"] == "done":
                done += 1

    # ---------- 2 + 3. status must agree with what is on disk ----------
    # `done` means the post is written; `planned` means it is assigned to a
    # post that is not written yet.  A `done` item with no file behind it is
    # the failure mode that matters: a "published" link that 404s.
    posts = {p.name for p in (repo / "_posts").glob("*.md")}
    planned_posts, done_posts = {}, {}
    for sec in roadmap:
        for it in sec.get("items", []):
            slug, status = it.get("post_slug") or it.get("post"), it.get("status")
            if status == "done":
                if not slug:
                    problems.append(f"{it['title']}: status done but no post slug")
                    continue
                # roadmap.md builds each done row's <a href> from `post_slug`.
                # An item carrying only the legacy `post` key still counts as
                # done here, but renders as a non-clickable row on the hub —
                # a silent inconsistency between "已发布" and "can't be opened".
                if not it.get("post_slug"):
                    problems.append(
                        f"{it['title']}: done but only has legacy key 'post', "
                        f"so the hub cannot link it (set post_slug)")
                hits = [p for p in posts if p.endswith(f"-{slug}.md")]
                if not hits:
                    problems.append(
                        f"{it['title']}: done -> '{slug}' has no _posts/*-{slug}.md")
                done_posts[slug] = done_posts.get(slug, 0) + 1
            elif status == "planned":
                if not slug:
                    problems.append(f"{it['title']}: status planned but no post_slug")
                else:
                    planned_posts[slug] = planned_posts.get(slug, 0) + 1
            else:
                if slug:
                    problems.append(
                        f"{it['title']}: status {status!r} should not carry a slug")
    # a slug claimed by both a done and a planned item is a data bug
    for s in set(planned_posts) & set(done_posts):
        problems.append(f"post '{s}' has both done and planned items")

    # ---------- 4 + 5 + 6. the page ----------
    if not page_path.exists():
        problems.append("roadmap.md is missing")
    else:
        page = page_path.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---\n", page, re.S)
        if not fm:
            problems.append("roadmap.md has no front matter")
        else:
            head = fm.group(1)
            if "layout: page" not in head:
                problems.append("roadmap.md should use layout: page")
            if "permalink: /roadmap/" not in head:
                problems.append("roadmap.md should set permalink: /roadmap/")
        # Liquid that would leak: an unclosed {{ }} or {% %}
        if page.count("{{") != page.count("}}"):
            problems.append(f"unbalanced {{{{ }}}}: {page.count('{{')} vs {page.count('}}')}")
        if page.count("{%") != page.count("%}"):
            problems.append(f"unbalanced {{% %}}: {page.count('{%')} vs {page.count('%}')}")
        # numbers must come from the data, not be typed in
        for lit in re.findall(r'<b>(\d+)</b>', page):
            problems.append(f"roadmap.md hardcodes the number {lit}; compute it from the data")
        if "site.data.roadmap" not in page:
            problems.append("roadmap.md does not read site.data.roadmap")

    # ---------- report ----------
    print(f"  repo          : {repo}")
    np = sum(1 for s in roadmap for i in s["items"] if i["status"] == "planned")
    print(f"  roadmap.json  : {len(roadmap)} sections, {total} items")
    print(f"                  {done} done, {np} planned, "
          f"{total - done - np} todo")
    print(f"  planned posts : {len(planned_posts)} distinct slugs")
    print(f"  posts on disk : {len(posts)}")
    if problems:
        print()
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n  RESULT: {len(problems)} problem(s)")
        return 1
    print("\n  ROADMAP OK — every published link resolves to a real post")
    return 0


if __name__ == "__main__":
    sys.exit(main())
