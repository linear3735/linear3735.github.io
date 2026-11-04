"""Audit: every file:line in the blog post resolves to a real file with that many lines.

A citation matches a file when the file's path *ends with* the cited path, so
`cuda/structure_output.py` is unambiguous while a bare `structure_output.py`
matches three files and gets reported as ambiguous instead of guessed.

    XGRAMMAR2_POST=xgrammar2-post.md \
    VLLM_TREE=/path/to/vllm DEEPINFER_TREE=/path/to/DeepInfer \
    XGRAMMAR_WHEEL=/path/to/site-packages/xgrammar \
    python3 audit_refs.py
"""
import os
import re
import sys
from pathlib import Path

V = Path(os.environ.get("VLLM_TREE", "/path/to/vllm"))
D = Path(os.environ.get("DEEPINFER_TREE", "/path/to/DeepInfer"))
X = Path(os.environ.get("XGRAMMAR_WHEEL", "/path/to/site-packages/xgrammar"))
ROOTS = {"vLLM": V, "DI": D, "XGR": X}
SKIP = ("third_party", "/tests/", "/docs/", "/examples/")

POST = Path(os.environ.get("XGRAMMAR2_POST", "xgrammar2-post.md"))


def _all_files():
    for tag, root in ROOTS.items():
        for p in root.rglob("*"):
            if p.is_file() and not any(s in str(p) for s in SKIP):
                yield tag, p


def resolve(rel: str):
    """Return (tree_tag, path, how) or (None, None, reason).

    A citation matches a file when the file's path *ends with* the cited path.
    `cuda/structure_output.py` therefore matches exactly one file, while a bare
    `structure_output.py` matches three and is reported as ambiguous.
    """
    want = rel.split("/")
    n = len(want)
    cands = [(tag, p) for tag, p in _all_files()
             if str(p).split("/")[-n:] == want]
    if len(cands) == 1:
        return cands[0][0], cands[0][1], f"suffix-match ({n} component{'s' if n > 1 else ''})"
    if not cands:
        return None, None, "NO SUCH FILE"
    shown = ", ".join(
        str(p).replace(str(V) + "/", "vLLM:").replace(str(D) + "/", "DI:").replace(str(X) + "/", "XGR:")
        for _, p in cands[:5])
    return None, None, f"AMBIGUOUS ({len(cands)} candidates): {shown}"


def main() -> int:
    post = POST.read_text()
    refs, seen = [], set()
    for m in re.finditer(r"`([A-Za-z0-9_/.\-]+\.(?:py|txt)):(\d+)(?:-(\d+))?`", post):
        key = (m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else 0)
        if key not in seen:
            seen.add(key)
            refs.append(key)

    problems = []
    print(f"  {'reference':62s} {'tree':5s} {'lines':>6s}  status")
    for rel, a, b in sorted(refs, key=lambda r: (r[0], r[1])):
        tag, f, how = resolve(rel)
        label = f"{rel}:{a}" + (f"-{b}" if b else "")
        if f is None:
            problems.append((label, how))
            print(f"  {label:62s} {'--':5s} {'--':>6s}  {how}")
            continue
        n = len(f.read_text(errors="replace").split("\n"))
        hi = b or a
        ok = 1 <= a <= hi <= n
        if not ok:
            problems.append((label, f"range {a}-{hi} but file has {n} lines"))
        print(f"  {label:62s} {tag:5s} {n:6d}  {'ok' if ok else 'OUT OF RANGE'}  ({how})")

    print()
    if problems:
        print(f"PROBLEMS: {len(problems)}")
        for label, why in problems:
            print(f"  {label}  ->  {why}")
        return 1
    print(f"ALL {len(refs)} CITATIONS RESOLVE to a real file and an existing line")
    return 0


if __name__ == "__main__":
    sys.exit(main())
