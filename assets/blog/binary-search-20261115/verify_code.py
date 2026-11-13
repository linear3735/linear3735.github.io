#!/usr/bin/env python3
"""Code gate for _posts/2026-11-15-binary-search.md.

Three things are checked.

1. Block accounting: the post must contain exactly as many ```python blocks as
   ```cpp blocks, and every one of them must be tagged.

2. Python: every ```python block is exec'd into one shared namespace and then
   driven through the claims made in the prose -- including a full comparison
   against `bisect` for both boundary conventions, brute-force references for
   the three binary-search-on-answer problems, and a sampling test for the
   weighted picker.

3. C++: the ```cpp blocks are concatenated with cpp_solutions_test.cpp and
   really compiled and run with

       g++ -std=c++17 -Wall -Wextra -O1

   The compile must produce zero warnings and the binary must exit 0.

Run from the repository root:  python3 assets/blog/binary-search-20261115/verify_code.py
"""
import bisect
import os
import random
import re
import subprocess
import sys
import tempfile

POST_REL = "_posts/2026-11-15-binary-search.md"
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "cpp_solutions_test.cpp")
EXPECTED_PY_BLOCKS = 9
EXPECTED_CPP_BLOCKS = 9

FAILURES = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}: got {got!r}, want {want!r}")
        FAILURES.append(name)


def check_true(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def load_blocks(post_text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", post_text, re.S)


def section(title):
    print(f"\n{title}")


# --------------------------------------------------------------- references
def ref_binary_search(nums, target):
    i = bisect.bisect_left(nums, target)
    return i if i < len(nums) and nums[i] == target else -1


def ref_koko(piles, h):
    for k in range(1, max(piles) + 1):
        if sum((p + k - 1) // k for p in piles) <= h:
            return k
    return -1


def ref_ship(weights, days):
    for c in range(max(weights), sum(weights) + 1):
        used, load = 1, 0
        for w in weights:
            if load + w > c:
                used += 1
                load = 0
            load += w
        if used <= days:
            return c
    return -1


def ref_split(nums, m):
    """Brute force: try every placement of m-1 cut points."""
    n = len(nums)
    best = None
    for mask in range(1 << (n - 1)):
        if bin(mask).count("1") != m - 1:
            continue
        worst, run = 0, 0
        for i in range(n):
            run += nums[i]
            if i == n - 1 or (mask >> i) & 1:
                worst = max(worst, run)
                run = 0
        best = worst if best is None else min(best, worst)
    return best


def adjacent_distinct(vals):
    """LeetCode 162 guarantees nums[i] != nums[i+1]; enforce it."""
    out = list(vals)
    for i in range(1, len(out)):
        while out[i] == out[i - 1]:
            out[i] += 1
    return out


def is_peak(nums, i):
    if not 0 <= i < len(nums):
        return False
    left = i == 0 or nums[i] > nums[i - 1]
    right = i == len(nums) - 1 or nums[i] > nums[i + 1]
    return left and right


# ------------------------------------------------------------------- gates
def gate_python(post_text):
    ns = {}
    py_blocks = load_blocks(post_text, "python")
    section("Python: exec every ```python block in one namespace")
    for i, block in enumerate(py_blocks, 1):
        try:
            exec(compile(block, f"<python block {i}>", "exec"), ns)
        except Exception as exc:                       # noqa: BLE001
            print(f"  FAIL block {i} raised {type(exc).__name__}: {exc}")
            FAILURES.append(f"py-block-{i}")
            return
    print(f"  ok   {len(py_blocks)} blocks executed without error")
    check_true("all names defined",
               all(k in ns for k in (
                   "binary_search", "left_bound", "right_bound",
                   "binary_search_open", "left_bound_open", "right_bound_open",
                   "min_eating_speed", "ship_within_days", "split_array",
                   "find_peak_element", "WeightedPicker")))

    section("Sections 2-3: both boundary conventions vs bisect")
    random.seed(20261115)
    pairs = 0
    mismatch = []
    for n in range(0, 21):
        for _ in range(40):
            nums = sorted(random.randint(-6, 6) for _ in range(n))
            for target in range(-8, 9):
                pairs += 1
                lb = bisect.bisect_left(nums, target)
                ub = bisect.bisect_right(nums, target)
                # The four *boundary* functions have an exact contract.
                got = {
                    "left_bound": ns["left_bound"](nums, target),
                    "right_bound": ns["right_bound"](nums, target),
                    "left_bound_open": ns["left_bound_open"](nums, target),
                    "right_bound_open": ns["right_bound_open"](nums, target),
                }
                want = {
                    "left_bound": lb,
                    "right_bound": ub - 1,
                    "left_bound_open": lb,
                    "right_bound_open": ub - 1,
                }
                if got != want:
                    mismatch.append((nums, target, got, want))
                # "Find a number" only promises *some* index of the target, so
                # it is checked against the weaker contract, not against
                # bisect_left (which is the leftmost index).
                for fn in ("binary_search", "binary_search_open"):
                    idx = ns[fn](nums, target)
                    ok = (idx >= 0) == (target in nums) and (
                        idx < 0 or nums[idx] == target)
                    if not ok:
                        mismatch.append((nums, target, fn, idx))
                # section 2.4's existence criterion
                if (lb > ub - 1) != (target not in nums):
                    mismatch.append((nums, target, "existence", None))
                # occurrence count formula
                if ub - lb != nums.count(target):
                    mismatch.append((nums, target, "count", None))
    check(f"({pairs} array,target pairs) all six functions match bisect",
          len(mismatch), 0)
    if mismatch:
        print(f"       first mismatch: {mismatch[0]}")

    section("Section 2.4: the article's two worked examples")
    nums = [1, 2, 2, 2, 3]
    check("nums=[1,2,2,2,3] t=2 left_bound", ns["left_bound"](nums, 2), 1)
    check("nums=[1,2,2,2,3] t=2 right_bound", ns["right_bound"](nums, 2), 3)
    nums = [2, 3, 5, 7]
    check("nums=[2,3,5,7] t=4 left_bound", ns["left_bound"](nums, 4), 2)
    check("nums=[2,3,5,7] t=4 right_bound", ns["right_bound"](nums, 4), 1)
    check_true("nums=[2,3,5,7] t=4 -> left_bound > right_bound",
               ns["left_bound"](nums, 4) > ns["right_bound"](nums, 4))

    section("Section 3.2: left_bound == right_bound + 1 whenever target is absent")
    random.seed(7)
    bad = 0
    for _ in range(3000):
        nums = sorted(random.randint(-4, 4) for _ in range(random.randint(0, 12)))
        t = random.randint(-6, 6)
        if t in nums:
            continue
        if ns["left_bound_open"](nums, t) != ns["right_bound_open"](nums, t) + 1:
            bad += 1
    check("3000 random absent-target cases", bad, 0)

    section("Section 4: the three binary-search-on-answer problems vs brute force")
    random.seed(875)
    bad = 0
    for _ in range(300):
        piles = [random.randint(1, 30) for _ in range(random.randint(1, 8))]
        h = random.randint(len(piles), sum(piles))
        if ns["min_eating_speed"](piles, h) != ref_koko(piles, h):
            bad += 1
    check("875 koko, 300 cases (h >= len(piles))", bad, 0)
    check("875 example piles=[3,6,7,11] h=8",
          ns["min_eating_speed"]([3, 6, 7, 11], 8), 4)

    random.seed(1011)
    bad = 0
    for _ in range(300):
        weights = [random.randint(1, 20) for _ in range(random.randint(1, 8))]
        days = random.randint(1, len(weights) + 3)
        if ns["ship_within_days"](weights, days) != ref_ship(weights, days):
            bad += 1
    check("1011 ship, 300 cases", bad, 0)
    check("1011 example weights=1..10 days=5",
          ns["ship_within_days"](list(range(1, 11)), 5), 15)

    random.seed(410)
    bad = 0
    for _ in range(400):
        nums = [random.randint(0, 15) for _ in range(random.randint(1, 8))]
        m = random.randint(1, len(nums))
        if ns["split_array"](nums, m) != ref_split(nums, m):
            bad += 1
    check("410 split array, 400 cases vs exhaustive cut enumeration", bad, 0)
    check("410 example nums=[7,2,5,10,8] m=2",
          ns["split_array"]([7, 2, 5, 10, 8], 2), 18)

    section("Section 4.4: 1011 and 410 really do share one decision function")
    random.seed(99)
    bad = 0
    for _ in range(500):
        nums = [random.randint(0, 15) for _ in range(random.randint(1, 8))]
        m = random.randint(1, len(nums))
        # the ship answer with days=m over the same array must equal splitArray
        if ns["ship_within_days"](nums, m) != ns["split_array"](nums, m):
            bad += 1
    check("shipWithinDays(nums, m) == splitArray(nums, m), 500 cases", bad, 0)

    section("Section 5.1: peak element")
    random.seed(162)
    bad = 0
    for _ in range(3000):
        nums = adjacent_distinct(
            [random.randint(-50, 50) for _ in range(random.randint(1, 25))])
        if not is_peak(nums, ns["find_peak_element"](nums)):
            bad += 1
    check("3000 random arrays return a genuine peak", bad, 0)
    check("[1,2,3,4]", ns["find_peak_element"]([1, 2, 3, 4]), 3)
    check("[4,3,2,1]", ns["find_peak_element"]([4, 3, 2, 1]), 0)
    check("[7]", ns["find_peak_element"]([7]), 0)

    section("Section 6: weighted picker -- distribution and zero weights")
    w = [1, 3, 0, 2, 4, 0, 6]
    picker = ns["WeightedPicker"](w)
    total = sum(w)
    trials = 400000
    hits = [0] * len(w)
    rng = random.Random(20261115)
    saved = random.random
    try:
        # The class uses the module-level `random`; seed it for reproducibility.
        random.seed(20261115)
        for _ in range(trials):
            hits[picker.pick_index()] += 1
    finally:
        random.random = saved
    print(f"       observed: {hits}")
    print(f"       expected: {[round(trials * x / total) for x in w]}")
    zero_ok = all(hits[i] == 0 for i, x in enumerate(w) if x == 0)
    check_true("zero-weight indices are never selected", zero_ok)
    worst = 0.0
    for i, x in enumerate(w):
        if x == 0:
            continue
        want = x / total
        got = hits[i] / trials
        worst = max(worst, abs(got - want))
    # 4 sigma for n = 400000 is at most 0.004 (sigma <= 0.0008)
    check_true(f"max |observed - w[i]/total| = {worst:.5f} < 0.004",
               worst < 0.004)
    check_true("picker of all-equal weights is uniform",
               _uniform_ok(ns, rng))

    section("Section 6.3: the claimed bisect_left pitfall is real")
    prefix = [0]
    for x in w:
        prefix.append(prefix[-1] + x)
    left_version = [bisect.bisect_left(prefix, t_) - 1 for t_ in range(total)]
    right_version = [bisect.bisect_right(prefix, t_) - 1 for t_ in range(total)]
    check_true("bisect_left version does go out of range (-1)",
               min(left_version) < 0, f"min={min(left_version)}")
    check_true("bisect_right version never goes out of range",
               min(right_version) >= 0 and max(right_version) < len(w))
    left_counts = [left_version.count(i) for i in range(len(w))]
    right_counts = [right_version.count(i) for i in range(len(w))]
    # both conventions must realise the weights exactly, when they do not
    # fall off the left end
    check("bisect_right counts equal the weights exactly", right_counts, w)
    # The left version realises the weights everywhere except t = 0, which it
    # maps to -1 -- so the last index is short by exactly one unit.
    check("bisect_left counts match except the missing t=0 unit",
          left_counts, w[:-1] + [w[-1] - 1])
    return ns


def _uniform_ok(ns, rng):
    picker = ns["WeightedPicker"]([1] * 5)
    hits = [0] * 5
    for _ in range(50000):
        hits[picker.pick_index()] += 1
    return all(abs(h / 50000 - 0.2) < 0.02 for h in hits)


def gate_cpp(post_text):
    section("C++: compile and run the concatenated blocks (zero warnings required)")
    if not os.path.exists(HARNESS):
        print(f"  FAIL harness missing: {HARNESS}")
        FAILURES.append("cpp-harness")
        return
    cpp_blocks = load_blocks(post_text, "cpp")
    body = "\n\n".join(cpp_blocks)
    harness = open(HARNESS, encoding="utf-8").read()
    source = (body + "\n\n// ---- harness ----\n" + harness +
              "\nint main() { return run_all_tests(); }\n")
    tmpdir = tempfile.mkdtemp(prefix="bs-cpp-")
    src = os.path.join(tmpdir, "combined.cpp")
    exe = os.path.join(tmpdir, "combined")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(source)
    print(f"       {len(cpp_blocks)} blocks -> {len(source)} bytes of C++")
    proc = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", "-O1", "-o", exe, src],
        capture_output=True, text=True)
    warn = (proc.stdout or "") + (proc.stderr or "")
    if warn.strip():
        print("  FAIL compiler emitted diagnostics:")
        print("\n".join("       " + ln for ln in warn.strip().splitlines()))
        FAILURES.append("cpp-warnings")
        return
    print("  ok   g++ -std=c++17 -Wall -Wextra -O1: 0 warnings")
    if proc.returncode != 0:
        print(f"  FAIL compile exit {proc.returncode}")
        FAILURES.append("cpp-compile")
        return
    run = subprocess.run([exe], capture_output=True, text=True)
    print("\n".join("       " + ln for ln in run.stdout.strip().splitlines()))
    if run.stderr.strip():
        print("  stderr:", run.stderr.strip())
    check("C++ test binary exit code", run.returncode, 0)


def main():
    if not os.path.exists(POST_REL):
        print(f"FATAL: {POST_REL} not found; run from the repository root")
        return 1
    post_text = open(POST_REL, encoding="utf-8").read()

    section("Block accounting")
    py_blocks = load_blocks(post_text, "python")
    cpp_blocks = load_blocks(post_text, "cpp")
    check("python block count", len(py_blocks), EXPECTED_PY_BLOCKS)
    check("cpp block count", len(cpp_blocks), EXPECTED_CPP_BLOCKS)
    check("python == cpp (verify_post.py requires this)",
          len(py_blocks), len(cpp_blocks))
    opens = re.findall(r"^```(\w+)\s*$", post_text, re.M)
    closes = re.findall(r"^```\s*$", post_text, re.M)
    text_blocks = len(re.findall(r"^```text\s*$", post_text, re.M))
    check("tagged opening fences == closing fences", len(opens), len(closes))
    check("every fence is tagged",
          len(opens), len(py_blocks) + len(cpp_blocks) + text_blocks)
    check("languages used",
          sorted(set(opens)), ["cpp", "python", "text"])
    if FAILURES:
        print("\nABORTING: fix block accounting first")
        return 1

    gate_python(post_text)
    gate_cpp(post_text)

    section("Summary")
    if FAILURES:
        print(f"  {len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("  CODE CHECKS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
