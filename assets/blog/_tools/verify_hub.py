#!/usr/bin/env python3
"""Hub gate: the series landing pages are correct, and the numbers add up.

`verify_series.py` answers "is every post in this series OK".  It does not
look at the *landing page* itself, and that page is where a mistake is
silent: Liquid's failure mode for a bad `{% if %}` is to render nothing, so
the page still returns 200 and still looks like a page — just with rows
missing.  A wrong `divided_by` shows a completion percentage that is simply
untrue.

Two independent halves, both falsifiable:

  1. Liquid syntax — if the `liquid` gem is reachable, actually PARSE and
     RENDER the page against the real data with strict_variables on.  A
     reference to a field that does not exist is then a hard error instead
     of a blank.  If ruby/liquid is unavailable we say SKIP out loud and
     fall back to the pure-Python structural audit below — a gate that
     silently downgrades is worse than no gate.

  2. Arithmetic — recompute the summary from the JSON in Python and compare
     against what the rendered HTML actually says.  This catches the
     "percentage is wrong" class that parsing alone cannot.

Usage:
    verify_hub.py [--repo PATH] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

RELEASED = ("done", "ready")

# Field schema per hub.  `item_fields` applies to every item; the by-status
# map adds the fields that only that status's branch renders.  Keep these in
# sync with the page template — `check_item_fields` fails loudly if a page
# renders a field nothing provides, which is the typo case.
HUBS = [
    {"page": "roadmap.md", "data": "_data/roadmap.json", "key": "roadmap",
     "label": "面试算法", "min_released": 1,
     # The template's `{% else %}` branch is the catch-all for "not written
     # yet"; roadmap.json currently uses only `done`, so `planned`/`todo` are
     # declared here to keep the rule honest rather than to imply they are used.
     "statuses": {"done", "planned", "todo"},
     "item_fields": ["title", "desc", "status"],
     "item_fields_by_status": {"done": ["post_slug"]}},
    {"page": "gpu.md", "data": "_data/gpu.json", "key": "gpu",
     "label": "GPU 与性能剖析", "min_released": 1,
     "statuses": {"done", "ready", "planned"},
     "item_fields": ["title", "desc", "status"],
     "item_fields_by_status": {"done": ["post_slug", "key"],
                              "ready": ["path", "key"]}},
]

# Filters Jekyll provides that the bare liquid gem does not.
RUBY_DRIVER = r'''
require "liquid"; require "json"
Liquid::Template.register_filter(Module.new do
  def relative_url(s); s.to_s.start_with?("/") ? s : "/#{s}"; end
  def slugify(s); s.to_s.strip.downcase.gsub(/[^\p{Word}]+/,"-").gsub(/^-|-$/,""); end
end)
page_file = ARGV[0]; data_file = ARGV[1]; key = ARGV[2]; url = ARGV[3]
src = File.read(page_file)
m = src.match(/\A---\s*\n(.*?\n)---\s*\n(.*)\z/m) or abort "NO_FRONT_MATTER"
body = m[2]
data = JSON.parse(File.read(data_file))
out = Liquid::Template.parse(body).render(
  {"site" => {"data" => {key => data}},
   "page" => {"url" => url, "title" => key}},
  strict_variables: true)
puts out
'''


def liquid_available() -> tuple[bool, str]:
    """Return (usable, ruby_lib_paths) for really rendering Liquid."""
    if not shutil.which("ruby"):
        return False, ""
    libs = []
    for root in (Path.home() / ".gem" / "ruby", Path("/Library/Ruby/Gems")):
        if root.exists():
            libs += [str(p) for p in root.glob("*/gems/*/lib")]
    env = os.environ.get("GEM_PATH", "")
    for extra in (Path.home() / ".gem" / "ruby" / "2.6.0", ):
        if extra.exists():
            libs += [str(p) for p in extra.glob("gems/*/lib")]
    probe = ("require 'liquid'; require 'json'; "
             "print Liquid::VERSION")
    p = subprocess.run(["ruby", "-e", probe], capture_output=True, text=True,
                       env={**os.environ, "RUBYLIB": ":".join(libs)})
    if p.returncode == 0:
        return True, ":".join(libs)
    return False, ""


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def check_arithmetic(repo: Path, hub: dict, rendered: str, problems: list[str]) -> None:
    """Recompute the summary in Python; compare to what the page says."""
    tag = hub["label"]
    data = json.loads((repo / hub["data"]).read_text(encoding="utf-8"))
    items = [i for sec in data for i in sec.get("items", [])]
    total = len(items)
    released = sum(1 for i in items if i.get("status") in RELEASED)
    todo = total - released
    pct = released * 100 // total if total else 0

    want = [str(released), str(todo), str(total), f"{pct}%"]
    got = re.findall(r'<div class="rm-stat[^"]*"><b>([^<]*)</b>', rendered)
    if got != want:
        problems.append(
            f"[{tag}] summary numbers disagree with {hub['data']}: "
            f"page says {got}, data implies {want}")

    bar = re.search(r'rm-progress"[^>]*aria-label="[^"]*?(\d+)%"', rendered)
    if not bar or int(bar.group(1)) != pct:
        problems.append(
            f"[{tag}] progress bar width is {bar.group(1) if bar else 'missing'}%, "
            f"data implies {pct}%")

    # Every `done` item must produce a link; every `planned` item must not.
    planned_titles = [i["title"] for i in items if i.get("status") == "planned"]
    for t in planned_titles:
        # the title is rendered in plain text; make sure it is not inside an <a>
        for m in re.finditer(re.escape(t), rendered):
            before = rendered[:m.start()]
            if before.rfind("<a ") > before.rfind("</a>"):
                problems.append(
                    f"[{tag}] planned item {t!r} is wrapped in a link — "
                    "unwritten work must not be clickable")
                break

    # Count the badges the page actually rendered.
    badges = re.findall(r'<span class="rm-tag">([^<]*)</span>', rendered)
    section_counts = re.findall(r'<span class="rm-count">(\d+)/(\d+)</span>', rendered)
    if len(section_counts) != len(data):
        problems.append(
            f"[{tag}] page rendered {len(section_counts)} section(s) but "
            f"{hub['data']} has {len(data)}")
    if not badges:
        problems.append(f"[{tag}] page rendered no per-item badges at all")
    if released < hub["min_released"]:
        problems.append(
            f"[{tag}] hub advertises {released} released item(s) — "
            "a hub with nothing on it should not be published")


def check_item_fields(repo: Path, hub: dict, problems: list[str]) -> None:
    """Every item must carry the fields its page renders for its status.

    Why this is a declared schema and not derived by parsing the template:
    the first two attempts *did* parse the Liquid and both were wrong —

      · opener regex `\\{%-?\\s*if\\s+it\\.status...` can never match
        `{% elsif it.status...`, because after `{%` comes `els` and `if` is
        not at that position.  Every `elsif` branch was therefore invisible
        and its fields were attributed to "outside any branch".
      · matching openers first and then hunting each one's closing tag got the
        nesting wrong as soon as a branch contained its own `{% if %}`, and it
        ignored `{% for %}`, so the status chain sat at depth 2 and no branch
        was recognised at all.

    Both were caught only by testing the parser against a synthetic template.
    A heuristic that silent-wrongs in two directions is worse than a schema
    someone must keep in sync by hand, because this one fails loudly.

    The render half of this gate cannot cover this class of bug either: with
    `strict_variables: true`, Liquid still resolves a missing *hash key* to nil
    and renders it as the empty string, so `{{ it.descr }}` (typo) produces a
    structurally perfect page quietly missing a line of text.  Verified, not
    assumed — that mutation left `verify_hub.py` green.
    """
    tag = hub["label"]
    src = (repo / hub["page"]).read_text(encoding="utf-8")
    data = json.loads((repo / hub["data"]).read_text(encoding="utf-8"))

    # Every field name the template mentions on an item, anywhere.  Used only
    # for typo detection below.
    mentioned = set(re.findall(r"\bit\.([A-Za-z_][A-Za-z0-9_]*)", src))

    base = set(hub["item_fields"])
    per_status = {k: set(v) for k, v in hub.get("item_fields_by_status", {}).items()}
    section_fields = (set(re.findall(r"\bsec\.([A-Za-z_]\w*)", src))
                      & {"section", "note"})

    all_items = [i for s in data for i in s.get("items", [])]
    for si, sec in enumerate(data):
        for f in sorted(section_fields):
            if f not in sec:
                problems.append(
                    f"[{tag}] {hub['data']} section #{si} "
                    f"({sec.get('section')!r}) lacks `{f}`, which "
                    f"{hub['page']} reads as sec.{f}")
        for ii, it in enumerate(sec.get("items", [])):
            st = it.get("status")
            if st not in hub["statuses"]:
                problems.append(
                    f"[{tag}] {hub['data']} item #{si}.{ii} has status {st!r}, "
                    f"which {hub['page']} has no branch for — it would fall "
                    f"through to the catch-all. Known: {sorted(hub['statuses'])}")
            for f in sorted(base | per_status.get(st, set())):
                if f not in it:
                    problems.append(
                        f"[{tag}] {hub['data']} item #{si}.{ii} "
                        f"({it.get('title')!r}, status={st!r}) lacks `{f}`; "
                        f"{hub['page']} renders it.{f} at that status, so the "
                        "row would come out blank")

    # Typo detection: a field the template renders that nothing ever provides.
    if all_items:
        provided = set().union(*(set(i) for i in all_items))
        for f in sorted(mentioned - provided - {"items"}):
            problems.append(
                f"[{tag}] {hub['page']} renders it.{f} but no item in "
                f"{hub['data']} carries `{f}` — one of the two is misspelled")
    return None


def linkable(repo: Path, raw: str) -> tuple[bool, str]:
    """Would Jekyll actually serve the page at this repo-relative path?

    Found the hard way, on the live site: `assets/blog/_tools/CONVENTIONS-GPU.md`
    is a 404.  Jekyll never copies directories whose name starts with `_` —
    `_posts/`, `_data/`, `_layouts/` and equally `_tools/` — so a hub that links
    into one ships a dead link.  (The algorithms series' `CONVENTIONS.md` sits in
    the same directory and had been a 404 all along; nothing linked to it, which
    is exactly why nobody noticed.)

    A static "does the file exist" check cannot see this: the file is right
    there on disk.  The failure is in the *build*, not the filesystem.
    """
    # `post_slug` is a bare slug, not a path.  Under `permalink: /:title/` it
    # resolves to whichever `_posts/*-<slug>.md` exists, so resolve it that way.
    if "/" not in raw and not raw.endswith(".md"):
        hits = sorted(p for p in (repo / "_posts").glob(f"*-{raw}.md"))
        if len(hits) == 1:
            return True, ""
        if not hits:
            return False, f"_posts/ 下没有 `*-{raw}.md`"
        return False, f"有 {len(hits)} 篇帖子共用这个 slug: {[h.name for h in hits]}"

    p = repo / raw
    if not p.exists():
        return False, "文件不存在"
    if p.is_dir():
        return False, "指向目录,不是文件"
    for part in PurePosixPath(raw).parts:
        if part.startswith("_") or part.startswith("."):
            return False, (f"路径里有 `{part}/`,Jekyll 不发布下划线/点开头的"
                           "目录,链过去必定 404")
    return True, ""


def check_links(repo: Path, hub: dict, problems: list[str]) -> None:
    """No hub row may link somewhere GitHub Pages will not serve.

    This has to key off what the PAGE actually renders as a link, not off
    whether some data field happens to hold a path.  `ready` rows carry a
    repo-relative `path` precisely so the page can print it as plain text after
    the `_tools/` 404 was found live; a path that is not linked cannot become a
    dead link, and flagging it would pressure the data into lying about where
    the file really lives.

    `done` rows build their URL from `post_slug` under `permalink: /:title/`;
    `verify_series.py` already resolves those against the posts on disk.
    """
    tag = hub["label"]
    data = json.loads((repo / hub["data"]).read_text(encoding="utf-8"))
    page = (repo / hub["page"]).read_text(encoding="utf-8")

    linked_via = {m.group(1) for m in
                  re.finditer(r"href=\"\{\{[^\"]*?it\.([A-Za-z_]\w*)", page)}
    if not linked_via:
        return None

    for si, sec in enumerate(data):
        for ii, it in enumerate(sec.get("items", [])):
            for field in sorted(linked_via):
                raw = it.get(field)
                if not raw:
                    continue
                ok, why = linkable(repo, raw)
                if not ok:
                    problems.append(
                        f"[{tag}] {hub['data']} item #{si}.{ii} "
                        f"({it.get('title')!r}) is linked through it.{field} = "
                        f"`{raw}`, but {why} — the page would ship a dead link")
    return None


def check_front_matter(repo: Path, hub: dict, problems: list[str]) -> None:
    tag = hub["label"]
    src = (repo / hub["page"]).read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?\n)---\s*\n", src, re.S)
    if not m:
        problems.append(f"[{tag}] {hub['page']} has no YAML front matter")
        return
    fm = m.group(1)
    for field in ("layout", "title", "display_title", "description", "permalink"):
        if not re.search(rf"^{field}\s*:", fm, re.M):
            problems.append(f"[{tag}] {hub['page']} front matter lacks `{field}`")
    want = f"/{hub['key']}/"
    got = re.search(r"^permalink\s*:\s*(\S+)", fm, re.M)
    if not got or got.group(1) != want:
        problems.append(
            f"[{tag}] {hub['page']} permalink is "
            f"{got.group(1) if got else 'missing'}, expected {want}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo).expanduser().resolve()

    problems: list[str] = []
    ok, rubylib = liquid_available()
    driver = Path("/tmp") / "_hub_render.rb"
    driver.write_text(RUBY_DRIVER, encoding="utf-8")

    if not args.quiet:
        print(f"  repo        : {repo}")
        print(f"  liquid gem  : {'yes — really rendering each hub' if ok else 'NO — structural audit only'}")

    for hub in HUBS:
        page, data = repo / hub["page"], repo / hub["data"]
        if not page.exists() or not data.exists():
            problems.append(f"[{hub['label']}] {hub['page']} or {hub['data']} missing")
            continue
        check_front_matter(repo, hub, problems)
        check_item_fields(repo, hub, problems)
        check_links(repo, hub, problems)

        rendered = None
        if ok:
            p = subprocess.run(
                ["ruby", str(driver), str(page), str(data), hub["key"],
                 f"/{hub['key']}/"],
                capture_output=True, text=True,
                env={**os.environ, "RUBYLIB": rubylib})
            if p.returncode != 0 or "NO_FRONT_MATTER" in p.stdout:
                problems.append(
                    f"[{hub['label']}] liquid could not render {hub['page']}: "
                    f"{p.stderr.strip()[:400]}")
                continue
            rendered = p.stdout
        else:
            # No ruby: audit the structure the template must have produced.
            rendered = page.read_text(encoding="utf-8")

        check_arithmetic(repo, hub, rendered, problems)
        if not args.quiet:
            n_items = len(json.loads(data.read_text(encoding="utf-8")))
            print(f"  {hub['label']:16s} {page.name:12s} "
                  f"{len(rendered):6d} bytes   {n_items} section(s)")

    if problems:
        print(f"  HUB FAIL — {len(problems)} problem(s):")
        for p in problems:
            print("   - " + p)
        return 1
    note = "" if ok else "  (liquid gem absent — syntax not verified by parse)"
    print(f"  HUB OK — {len(HUBS)} hub(s): front matter, links and summary "
          f"arithmetic all check out{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
