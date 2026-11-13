#!/usr/bin/env python3
"""Series-wide gate: run every post's own gates and cross-check the hub.

Individual post gates (`verify_post.py`, each post's `verify_code.py`) answer
"is this one post OK".  This answers the different question the Lead cares
about before publishing: *is the series as a whole coherent* — does the hub
link every published post, does every published post appear on the hub, and
do all per-post gates actually pass right now.

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


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def slug_of(post: Path) -> str:
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", post.name)
    return m.group(1) if m else post.stem


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo).expanduser().resolve()

    problems: list[str] = []
    rows: list[tuple[str, str, int, int]] = []

    roadmap = json.loads((repo / "_data" / "roadmap.json").read_text(encoding="utf-8"))
    hub_slugs = {i["post_slug"] for s in roadmap for i in s["items"] if i.get("post_slug")}
    done_slugs = {i["post_slug"] for s in roadmap for i in s["items"]
                  if i.get("status") == "done" and i.get("post_slug")}

    # ---------- 1. every series post: run its structural gate ----------
    # Only posts the roadmap knows about belong to this series.  The repo also
    # holds unrelated posts from other sessions; they are out of scope.
    posts = sorted(p for p in (repo / "_posts").glob("*.md")
                   if slug_of(p) in hub_slugs)
    in_progress: list[str] = []
    for post in posts:
        slug = slug_of(post)
        rc, out = run([PY, "assets/blog/_tools/verify_post.py", str(post.relative_to(repo))], repo)
        n_img = len(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", post.read_text(encoding="utf-8")))
        if rc != 0:
            # A writer may not have drawn its SVGs yet, and it may still be
            # adding the sections its 目录 already promises.  Both are IN
            # PROGRESS, not defects — they only count as failures once the
            # roadmap says the post is `done`.
            wip_signs = ("image missing on disk", "anchor matches no heading")
            if slug not in done_slugs and any(s in out for s in wip_signs):
                in_progress.append(slug)
            else:
                problems.append(f"{slug}: verify_post.py failed\n{out}")
        # its own code gate, if it has one
        gate = repo / "assets" / "blog" / f"{slug}-" / "verify_code.py"
        # Path.glob treats ** as "this dir and below", so {slug}-* alone only
        # finds files sitting directly in assets/blog/.  The gates live one
        # level deeper, in assets/blog/<slug>-<date>/.  The old pattern
        # silently reported "n/a" for gates that were right there.
        cands = sorted((repo / "assets" / "blog").glob(f"{slug}-*/verify_code.py"))
        crc = None
        if cands:
            crc, cout = run([PY, str(cands[0].relative_to(repo))], repo)
            if crc != 0:
                # Same reasoning as above: a gate that fails while its post is
                # still being written is wip.  Once the post is `done`, a
                # failing gate is a hard failure.
                if slug not in done_slugs:
                    in_progress.append(slug)
                    crc = -2
                else:
                    problems.append(f"{slug}: verify_code.py failed\n{cout}")
        rows.append((slug, "ok" if rc == 0 else "FAIL", n_img, crc if crc is not None else -1))

    # ---------- 2. hub <-> posts consistency (series posts only) ----------
    on_disk = {slug_of(p) for p in posts}
    for s in sorted(done_slugs - on_disk):
        problems.append(f"roadmap says {s!r} is done (published) but there is no _posts/*-{s}.md")

    # ---------- 3. nav entry point ----------
    nav = (repo / "_layouts" / "default.html").read_text(encoding="utf-8")
    if "/roadmap/" not in nav:
        problems.append("_layouts/default.html has no link to /roadmap/ — the hub is unreachable")
    if not (repo / "roadmap.md").exists():
        problems.append("roadmap.md is missing")

    # ---------- 4. series posts must be dual-language Python/C++ ----------
    for post in posts:
        body = post.read_text(encoding="utf-8")
        py = len(re.findall(r"^```python\b", body, re.M))
        cpp = len(re.findall(r"^```cpp\b", body, re.M))
        java = len(re.findall(r"^```java\b", body, re.M))
        if java:
            problems.append(f"{slug_of(post)}: has {java} ```java fence(s)")
        if py != cpp:
            problems.append(f"{slug_of(post)}: {py} python vs {cpp} cpp fences (must be equal)")

    # ---------- report ----------
    if not args.quiet:
        print(f"  repo      : {repo}")
        print(f"  posts     : {len(posts)}")
        print(f"  hub slugs : {len(hub_slugs)}  (done {len(done_slugs)})")
        print()
        print(f"  {'post':44s} {'struct':>8s} {'imgs':>5s} {'code':>6s}")
        for slug, st, n_img, crc in rows:
            code = {None: "n/a", -1: "n/a", -2: "wip", 0: "ok"}.get(crc, "FAIL")
            mark = "wip" if slug in in_progress else st
            print(f"  {slug:44s} {mark:>8s} {n_img:>5d} {code:>6s}")
        print()
        if in_progress:
            print(f"  in progress (still being written): {sorted(set(in_progress))}")
            print()

    if problems:
        print(f"  SERIES FAIL — {len(problems)} problem(s):")
        for p in problems:
            print("   - " + p.replace("\n", "\n     "))
        return 1
    print("  SERIES OK — every post passes its gates and the hub is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
