#!/usr/bin/env python3
"""Series-wide gate: run every post's own gates and cross-check each hub.

Individual post gates (`verify_post.py`, each post's `verify_code.py`) answer
"is this one post OK".  This answers the different question the Lead cares
about before publishing: *is the series as a whole coherent* — does the hub
link every published post, does every published post appear on the hub, and
do all per-post gates actually pass right now.

There are two independent series, and they must not contaminate each other:

  hub          数据              页面         导航
  -----------  ----------------  -----------  ------
  /roadmap/    _data/roadmap.json  roadmap.md  路线图   面试算法(76 条)
  /gpu/        _data/gpu.json      gpu.md      GPU     GPU 与性能剖析

They used to share one data file, which meant adding a GPU post moved the
*algorithm* series' completion percentage.  Keeping the data separate is the
whole point; this gate iterates the registry below so neither series can be
half-wired.

Usage:
    verify_series.py [--repo PATH] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PY = sys.executable
SKIP_GATES = {"interview-algo-speedrun"}  # gates live in its own dir, run separately

# A hub item is "released" when its content is actually reachable.  `done`
# means a published post; `ready` means a file already in the repo (used by
# the GPU hub for the series conventions doc).  `planned` has no link at all,
# and the template must not render one.
RELEASED = ("done", "ready")

HUBS = [
    {
        "name": "面试算法",
        "data": "_data/roadmap.json",
        "page": "roadmap.md",
        "nav": "/roadmap/",
        "nav_label": "路线图",
        # The algorithm series promises Python 3 + C++ in every post, and the
        # author asked for no Java anywhere.  The GPU series makes no such
        # promise (its posts are CUDA + Python), so this is per-hub.
        "dual_language": True,
    },
    {
        "name": "GPU 与性能剖析",
        "data": "_data/gpu.json",
        "page": "gpu.md",
        "nav": "/gpu/",
        "nav_label": "GPU",
        "dual_language": False,
    },
]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def slug_of(post: Path) -> str:
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", post.name)
    return m.group(1) if m else post.stem


def check_hub(repo: Path, hub: dict, problems: list[str],
              quiet: bool) -> list[tuple[str, str, int, int]]:
    """Validate one series end to end.  Appends to `problems`, returns rows."""
    tag = hub["name"]
    rows: list[tuple[str, str, int, int]] = []

    data_path = repo / hub["data"]
    if not data_path.exists():
        problems.append(f"[{tag}] {hub['data']} is missing")
        return rows
    data = json.loads(data_path.read_text(encoding="utf-8"))

    def items():
        for sec in data:
            for it in sec.get("items", []):
                yield it

    # A released item must be reachable; a planned one must not claim a link.
    for it in items():
        st = it.get("status")
        if st == "done" and not it.get("post_slug"):
            problems.append(f"[{tag}] done item {it.get('title')!r} has no post_slug")
        if st == "ready" and not it.get("path"):
            problems.append(f"[{tag}] ready item {it.get('title')!r} has no path")
        if st == "planned" and (it.get("post_slug") or it.get("path")):
            problems.append(
                f"[{tag}] planned item {it.get('title')!r} carries a link — "
                "the page would render a clickable entry for unwritten work")

    # ---------- 1. every series post: run its structural gate ----------
    # Only posts this hub knows about belong to this series.  The repo also
    # holds unrelated posts from other sessions; they are out of scope.
    hub_slugs = {i["post_slug"] for i in items() if i.get("post_slug")}
    done_slugs = {i["post_slug"] for i in items()
                  if i.get("status") == "done" and i.get("post_slug")}

    posts = sorted(p for p in (repo / "_posts").glob("*.md")
                   if slug_of(p) in hub_slugs)
    in_progress: list[str] = []
    for post in posts:
        slug = slug_of(post)
        rc, out = run([PY, "assets/blog/_tools/verify_post.py",
                       str(post.relative_to(repo))], repo)
        n_img = len(re.findall(r"!\[[^\]]*\]\(([^)]+)\)",
                               post.read_text(encoding="utf-8")))
        if rc != 0:
            # A writer may not have drawn its SVGs yet, and it may still be
            # adding the sections its 目录 already promises.  Both are IN
            # PROGRESS, not defects — they only count as failures once the
            # hub says the post is `done`.
            wip_signs = ("image missing on disk", "anchor matches no heading")
            if slug not in done_slugs and any(s in out for s in wip_signs):
                in_progress.append(slug)
            else:
                problems.append(f"[{tag}] {slug}: verify_post.py failed\n{out}")
        # its own code gate, if it has one
        # Path.glob treats ** as "this dir and below", so {slug}-* alone only
        # finds files sitting directly in assets/blog/.  The gates live one
        # level deeper, in assets/blog/<slug>-<date>/.  The old pattern
        # silently reported "n/a" for gates that were right there.
        cands = sorted((repo / "assets" / "blog").glob(f"{slug}-*/verify_code.py"))
        crc = None
        if cands and slug not in SKIP_GATES:
            crc, cout = run([PY, str(cands[0].relative_to(repo))], repo)
            if crc != 0:
                if slug not in done_slugs:
                    in_progress.append(slug)
                    crc = -2
                else:
                    problems.append(f"[{tag}] {slug}: verify_code.py failed\n{cout}")
        rows.append((slug, "ok" if rc == 0 else "FAIL", n_img,
                     crc if crc is not None else -1))

    # ---------- 2. hub <-> posts consistency ----------
    on_disk = {slug_of(p) for p in posts}
    for s in sorted(done_slugs - on_disk):
        problems.append(
            f"[{tag}] hub says {s!r} is done (published) but there is no "
            "_posts/*-{}.md".format(s))
    # `ready` items point at a repo file, which must actually be there.
    for it in items():
        if it.get("status") == "ready" and it.get("path"):
            if not (repo / it["path"]).exists():
                problems.append(
                    f"[{tag}] ready item {it.get('title')!r} points at "
                    f"{it['path']}, which does not exist")

    # ---------- 3. nav entry point ----------
    nav = (repo / "_layouts" / "default.html").read_text(encoding="utf-8")
    if hub["nav"] not in nav:
        problems.append(
            f"[{tag}] _layouts/default.html has no link to {hub['nav']} — "
            "the hub is unreachable")
    if not (repo / hub["page"]).exists():
        problems.append(f"[{tag}] {hub['page']} is missing")

    # ---------- 4. per-hub language rule ----------
    if hub["dual_language"]:
        for post in posts:
            body = post.read_text(encoding="utf-8")
            py = len(re.findall(r"^```python\b", body, re.M))
            cpp = len(re.findall(r"^```cpp\b", body, re.M))
            java = len(re.findall(r"^```java\b", body, re.M))
            if java:
                problems.append(f"[{tag}] {slug_of(post)}: has {java} ```java fence(s)")
            if py != cpp:
                problems.append(
                    f"[{tag}] {slug_of(post)}: {py} python vs {cpp} cpp fences "
                    "(must be equal)")

    # ---------- report ----------
    if not quiet:
        released = sum(1 for i in items() if i.get("status") in RELEASED)
        print(f"  ── {tag}  ({hub['nav']}, {hub['data']}) ──")
        print(f"  posts     : {len(posts)}   hub items: {len(list(items()))} "
              f"(released {released})")
        print(f"  {'post':44s} {'struct':>8s} {'imgs':>5s} {'code':>6s}")
        for slug, st, n_img, crc in rows:
            code = {None: "n/a", -1: "n/a", -2: "wip", 0: "ok"}.get(crc, "FAIL")
            mark = "wip" if slug in in_progress else st
            print(f"  {slug:44s} {mark:>8s} {n_img:>5d} {code:>6s}")
        if in_progress:
            print(f"  in progress: {sorted(set(in_progress))}")
        print()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo).expanduser().resolve()

    problems: list[str] = []
    if not args.quiet:
        print(f"  repo      : {repo}")
        print()
    for hub in HUBS:
        check_hub(repo, hub, problems, args.quiet)

    if problems:
        print(f"  SERIES FAIL — {len(problems)} problem(s):")
        for p in problems:
            print("   - " + p.replace("\n", "\n     "))
        return 1
    print(f"  SERIES OK — {len(HUBS)} hub(s); every post passes its gates "
          "and each hub is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
