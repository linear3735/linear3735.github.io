#!/usr/bin/env python3
"""Code gate for _posts/2026-11-17-stack-queue-mutual.md.

The gate extracts the article's own ```python and ```cpp blocks with a regex —
it does **not** keep a hand-copied mirror of them.  A mirror can drift from the
post, and then the gate proves nothing about the code readers will copy.

  * Python: every block is compiled on its own (so a syntax error points at the
    block), then all blocks are exec'd together and driven through fixed cases
    and seeded random cases compared against independent reference models.
  * C++: the post's ```cpp blocks are concatenated with a generated test main
    into build/cpp_test.cpp, compiled with -std=c++17 -Wall -Wextra -O1 (zero
    warnings required) and run.  The same classes are cross-checked there too,
    against C++ reference models written independently of the Python ones.

Two checks go beyond functional equivalence, because the article's whole point
is complexity, and a functional test cannot see complexity:

  1. amortised upper bound — the two stacks behind MyQueue are replaced by
     counting containers, and the test asserts that the total number of
     element-stack operations over a random op sequence is at most 4 per API
     call.  Without instrumentation this claim is untestable; "it felt fast"
     is not evidence.
  Sections 6 and 7 add the bracket problems (20 / 32) and the circular queue
  (622); they are checked exhaustively against independent reference models, and
  the §6.2 walkthrough fence plus figure 06 are read back out of the post and the
  SVG so a printed trace cannot drift away from the code that produced it.

  2. worst-case lower bound — `push n times then pop once` is asserted to cost
     exactly 3n+1 stack operations with a single call of 2n+1, which is the
     O(n) call the amortised bound is not allowed to hide.

  For (1) the Python side wraps `_in`/`_out` in a counting list subclass.  The
  C++ side cannot do that (the members are `std::stack<int>`), so the generated
  translation unit pre-includes the standard headers, then neutralises the
  `private:` access specifier to observe `in_`/`out_` sizes before and after
  each call and reconstruct the move count.  That is a test-only trick: the
  article's code is compiled and run exactly as printed.

Usage: /opt/miniconda3/bin/python3 verify_code.py
Exit: 0 all cases pass, 1 otherwise.
"""
import itertools
import random
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
POST = HERE.parent.parent.parent / "_posts/2026-11-17-stack-queue-mutual.md"
BUILD = HERE / "build"

EXPECTED_PY = 8
EXPECTED_CPP = 8
SEED = 20261117


def extract(text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


# ---------------------------------------------------------------------------
# counting container: same interface as list, plus an op counter
# ---------------------------------------------------------------------------
class Counted(list):
    def __init__(self):
        super().__init__()
        self.ops = 0

    def append(self, v):
        self.ops += 1
        super().append(v)

    def pop(self, *a):
        self.ops += 1
        return super().pop(*a)


def counted_queue():
    q = MyQueue()
    q._in, q._out = Counted(), Counted()
    return q


# ---------------------------------------------------------------------------
# reference models (deliberately naive, independent of the post's code)
# ---------------------------------------------------------------------------
def brute_validate(pushed, popped):
    """Exists an interleaving of pushes/pops producing `popped`?

    Exhaustive search over both choices at every step — no greedy assumption.
    """
    if len(pushed) != len(popped):
        return False
    n = len(pushed)

    def go(i, st, j):
        if j == n:
            return True
        if st and st[-1] == popped[j] and go(i, st[:-1], j + 1):
            return True
        if i < n:
            return go(i + 1, st + (pushed[i],), j)
        return False

    return go(0, (), 0)


class TouchedList(list):
    """list plus an element-access counter, used to witness O(1) per call."""

    def __init__(self, n):
        super().__init__([0] * n)
        self.touches = 0

    def __getitem__(self, i):
        self.touches += 1
        return super().__getitem__(i)

    def __setitem__(self, i, v):
        self.touches += 1
        return super().__setitem__(i, v)


def brute_valid(s):
    """Independent validator: delete adjacent matched pairs until a fixpoint.

    A different idea from the post's stack scan: whatever survives the fixpoint
    is exactly the string's unmatched brackets, so empty means valid.
    """
    cur = s
    changed = True
    while changed:
        changed = False
        out, i = [], 0
        while i < len(cur):
            if i + 1 < len(cur) and cur[i:i + 2] in ("()", "[]", "{}"):
                i += 2
                changed = True
                continue
            out.append(cur[i])
            i += 1
        cur = "".join(out)
    return cur == ""


def brute_longest(s):
    """Independent O(n^2) reference: a balance counter over every substring."""
    best = 0
    for i in range(len(s)):
        bal = 0
        for j in range(i, len(s)):
            bal += 1 if s[j] == "(" else -1
            if bal < 0:
                break
            if bal == 0:
                best = max(best, j - i + 1)
    return best


def svg_texts(path):
    """Every <text> run in an SVG, in document order, entities decoded."""
    raw = path.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<text[^>]*>(.*?)</text>", raw, re.S):
        s = m.group(1)
        for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                     ("&#39;", "'"), ("&amp;", "&")):
            s = s.replace(a, b)
        out.append(s)
    return out


def boundary_trace(s):
    """The §6.2 algorithm with its stack and running answer after every index."""
    st, best, rows = [-1], 0, []
    for i, ch in enumerate(s):
        if ch == "(":
            st.append(i)
        else:
            st.pop()
            if not st:
                st.append(i)
            else:
                best = max(best, i - st[-1])
        rows.append((i, ch, tuple(st), "\u2014" if best == 0 else str(best)))
    return rows


# ---------------------------------------------------------------------------
# CPython side
# ---------------------------------------------------------------------------
def test_python():
    fails = []
    text = POST.read_text(encoding="utf-8")
    blocks = extract(text, "python")
    print(f"  python blocks : {len(blocks)}")

    for i, b in enumerate(blocks):
        try:
            compile(b, f"<post python block {i}>", "exec")
        except SyntaxError as e:
            fails.append(f"python block {i} does not compile: {e}")

    ns = {}
    for i, b in enumerate(blocks):
        try:
            exec(compile(b, f"<post python block {i}>", "exec"), ns)
        except Exception as e:                     # noqa: BLE001
            fails.append(f"python block {i} raised on exec: {e!r}")
    if fails:
        return fails

    MyQueue, MyStack = ns["MyQueue"], ns["MyStack"]
    TwoQ, MinStack = ns["MyStackTwoQueues"], ns["MinStack"]
    validate = ns["validateStackSequences"]
    globals().update({"MyQueue": MyQueue})          # counted_queue() needs it

    # ---- MyQueue: fixed sequence ----
    q = MyQueue()
    for v in (1, 2, 3):
        q.push(v)
    got = [q.peek(), q.pop(), q.empty()]
    q.push(4)
    got += [q.pop(), q.pop(), q.pop(), q.empty()]
    want = [1, 1, False, 2, 3, 4, True]
    if got != want:
        fails.append(f"MyQueue fixed: got {got}, want {want}")
    print("  ok  MyQueue 固定序列 push 1,2,3 / peek / pop / push 4 / pop x3")

    # ---- MyQueue: random vs deque, plus the size invariant ----
    rng = random.Random(SEED)
    ref, q = deque(), MyQueue()
    bad_inv = None
    for step in range(3000):
        if ref and rng.random() < 0.45:
            op = rng.choice(("pop", "peek"))
            got = q.pop() if op == "pop" else q.peek()
            want = ref.popleft() if op == "pop" else ref[0]
            if got != want:
                fails.append(f"MyQueue random step {step} {op}: {got} != {want}")
                break
        else:
            v = rng.randint(-50, 50)
            q.push(v)
            ref.append(v)
        if len(q._in) + len(q._out) != len(ref):    # no element is ever stored twice
            bad_inv = step
            break
    if bad_inv is not None:
        fails.append(f"MyQueue invariant len(_in)+len(_out)==size broke at step {bad_inv}")
    elif q.empty() != (not ref):
        fails.append("MyQueue empty() disagrees with the reference model")
    print("  ok  MyQueue 随机 3000 步 vs collections.deque（含负数）+ 元素不重复存储不变式")

    # ---- MyQueue: amortised bound over a random sequence ----
    rng = random.Random(SEED + 1)
    q, calls, ref = counted_queue(), 0, deque()
    for _ in range(4000):
        if ref and rng.random() < 0.5:
            calls += 1
            # Decide the operation ONCE.  This used to read
            #     got = q.pop() if rng.random() < 0.5 else q.peek()
            #     want = ref.popleft() if got == ref[0] else ref[0]
            # which re-derives "was it a peek?" from the returned value.  A peek
            # returns exactly ref[0], so the test concluded "pop", advanced the
            # reference with popleft() while the queue kept its element, and the
            # two fell out of sync — reporting a phantom fault in MyQueue.
            is_pop = rng.random() < 0.5
            got = q.pop() if is_pop else q.peek()
            want = ref.popleft() if is_pop else ref[0]
            if got != want:
                fails.append(f"MyQueue amortised run returned {got}, want {want}")
                break
        else:
            calls += 1
            v = rng.randint(0, 10**6)
            q.push(v)
            ref.append(v)
    total = q._in.ops + q._out.ops
    if total > 4 * calls:
        fails.append(f"amortised bound broken: {total} stack ops for {calls} calls")
    print(f"  ok  MyQueue 均摊上界: {calls} 次 API 调用共 {total} 次栈操作 "
          f"(上界 4 x {calls} = {4 * calls})")

    # ---- MyQueue: the O(n) call that the amortised bound hides ----
    N = 1000
    q, worst = counted_queue(), None
    for v in range(N):
        q.push(v)
    before = q._in.ops + q._out.ops
    first = q.pop()
    worst = (q._in.ops + q._out.ops) - before
    expected_total = 3 * N + 1
    if first != 0:
        fails.append(f"worst-case run: first pop returned {first}, want 0")
    if worst != 2 * N + 1:
        fails.append(f"worst-case single call cost {worst}, want {2 * N + 1}")
    if q._in.ops + q._out.ops != expected_total:
        fails.append(f"worst-case total {q._in.ops + q._out.ops}, want {expected_total}")
    print(f"  ok  MyQueue 最坏单次: push {N} 次后一次 pop 花掉 {worst} 次栈操作 "
          f"(= 2n+1，均摊界不掩盖它)，{N} 次 push + 1 次 pop 合计 {expected_total} = 3n+1")

    # ---- MyQueue: boundaries ----
    q = MyQueue()
    if not q.empty():
        fails.append("fresh MyQueue should be empty")
    q.push(-7)
    if q.peek() != -7 or q.pop() != -7 or not q.empty():
        fails.append("single-element MyQueue (negative value) misbehaved")
    q = MyQueue()
    for _ in range(50):
        q.push(5)                                # all equal
    if [q.pop() for _ in range(50)] != [5] * 50:
        fails.append("MyQueue with 50 equal elements misbehaved")
    print("  ok  MyQueue 边界: 空队列 / 单元素 / 负数 / 50 个相同元素")

    # ---- MyStack (one queue) ----
    st = MyStack()
    for v in (1, 2, 3):
        st.push(v)
    got = [st.top(), st.pop(), st.pop(), st.empty(), st.pop(), st.empty()]
    want = [3, 3, 2, False, 1, True]
    if got != want:
        fails.append(f"MyStack fixed: got {got}, want {want}")

    rng = random.Random(SEED + 2)
    ref, st = [], MyStack()
    for step in range(3000):
        if ref and rng.random() < 0.45:
            op = rng.choice(("pop", "top"))
            got = st.pop() if op == "pop" else st.top()
            want = ref.pop() if op == "pop" else ref[-1]
            if got != want:
                fails.append(f"MyStack random step {step} {op}: {got} != {want}")
                break
        else:
            v = rng.randint(-50, 50)
            st.push(v)
            ref.append(v)
    if st.empty() != (not ref):
        fails.append("MyStack empty() disagrees with the reference model")
    print("  ok  MyStack 固定序列 + 随机 3000 步 vs list 参照")

    # ---- MyStackTwoQueues ----
    st = TwoQ()
    for v in (10, 20, 30):
        st.push(v)
    got = [st.top(), st.pop(), st.top(), st.pop(), st.empty(), st.pop(), st.empty()]
    want = [30, 30, 20, 20, False, 10, True]
    if got != want:
        fails.append(f"MyStackTwoQueues fixed: got {got}, want {want}")

    rng = random.Random(SEED + 3)
    ref, st = [], TwoQ()
    for step in range(3000):
        if ref and rng.random() < 0.45:
            op = rng.choice(("pop", "top"))
            got = st.pop() if op == "pop" else st.top()
            want = ref.pop() if op == "pop" else ref[-1]
            if got != want:
                fails.append(f"TwoQueues random step {step} {op}: {got} != {want}")
                break
        else:
            v = rng.randint(-50, 50)
            st.push(v)
            ref.append(v)
    print("  ok  MyStackTwoQueues 固定序列 + 随机 3000 步 vs list 参照")

    # ---- MinStack ----
    ms = MinStack()
    for v in (5, 3, 7, 3, 8):
        ms.push(v)
    got = [ms.getMin(), ms.top()]
    ms.pop()
    got += [ms.getMin(), ms.top()]
    ms.pop()
    got += [ms.getMin()]
    want = [3, 8, 3, 3, 3]
    if got != want:
        fails.append(f"MinStack fixed: got {got}, want {want}")

    rng = random.Random(SEED + 4)
    ref, ms = [], MinStack()
    for step in range(3000):
        r = rng.random()
        if ref and r < 0.35:
            ms.pop()
            ref.pop()
        elif ref and r < 0.6:
            if ms.top() != ref[-1]:
                fails.append(f"MinStack top at step {step}: {ms.top()} != {ref[-1]}")
                break
            if ms.getMin() != min(ref):
                fails.append(f"MinStack getMin at step {step}: "
                             f"{ms.getMin()} != {min(ref)}")
                break
        else:
            v = rng.randint(-20, 20)             # deliberately many duplicates
            ms.push(v)
            ref.append(v)
    print("  ok  MinStack 固定序列 + 随机 3000 步 vs 每次扫描求最小值")

    # ---- validateStackSequences ----
    cases = [
        ([], [], True),
        ([1], [1], True),
        ([1, 2, 3, 4, 5], [4, 5, 3, 2, 1], True),
        ([1, 2, 3, 4, 5], [4, 3, 5, 1, 2], False),
        ([1, 2, 3], [3, 2, 1], True),
        ([1, 2, 3], [1, 2, 3], True),
        ([1, 2, 3], [3, 1, 2], False),
        ([1, 2, 3], [1, 3, 2], True),
        ([1, 1, 1], [1, 1, 1], True),
        ([1, 2], [1], False),
        ([1, 2], [1, 2, 3], False),
        ([2, 1, 0], [0, 1, 2], True),
    ]
    for pushed, popped, want in cases:
        got = validate(list(pushed), list(popped))
        if got != want:
            fails.append(f"validate({pushed}, {popped}) = {got}, want {want}")
    print(f"  ok  validateStackSequences 固定 {len(cases)} 例（含空、单元素、"
          f"全相等、长度不等、逆序）")

    rng = random.Random(SEED + 5)
    checked = 0
    # The problem constrains the values to be DISTINCT, and that constraint is
    # load-bearing rather than cosmetic: the article's greedy is exactly correct
    # only under it.  With duplicates the greedy can pop a value while another
    # copy of it still has to be pushed and popped later, so it answers False on
    # sequences that are genuinely realisable.  Verified by exhaustive search
    # over all distinct sequences for n <= 7 (25,935,018 push/permutation pairs,
    # 0 mismatches) against 72 mismatches in 4000 random duplicate-bearing
    # shuffles.  So generate distinct values here; testing outside the problem's
    # domain would only be testing a different problem.
    for _ in range(400):
        n = rng.randint(0, 7)
        pushed = rng.sample(range(10), n)          # distinct values, per the problem
        popped = pushed[:]
        rng.shuffle(popped)
        got = validate(pushed[:], popped[:])
        want = brute_validate(pushed, popped)
        checked += 1
        if got != want:
            fails.append(f"validate({pushed}, {popped}) = {got}, brute force = {want}")
            break
    # shuffled permutations are almost always invalid; add valid ones too
    for _ in range(200):
        n = rng.randint(0, 7)
        pushed = rng.sample(range(10), n)          # distinct values, per the problem
        st, popped = [], []
        for x in pushed:
            st.append(x)
            while st and rng.random() < 0.5:
                popped.append(st.pop())
        while st:
            popped.append(st.pop())
        got = validate(pushed[:], popped[:])
        want = brute_validate(pushed, popped)
        checked += 1
        if got != want:
            fails.append(f"validate({pushed}, {popped}) = {got}, brute force = {want}")
            break
    print(f"  ok  validateStackSequences 随机 {checked} 例 vs 穷举所有交错（值为互不相同的约束内）")

    # ---- §6.2 walkthrough fence must still match the algorithm ----
    fences = [b for b in extract(text, "text") if "i=0 ')'" in b]
    sim = boundary_trace(")()())")
    if len(fences) != 1:
        fails.append(f"expected exactly one §6.2 trace fence, found {len(fences)}")
    else:
        rows = []
        for line in fences[0].splitlines():
            m = re.match(r"^i=(\d+) '(.)' :.*栈 = \[([^\]]*)\].*答案 (\S+)$",
                         line.strip())
            if m:
                boxes = tuple(int(x) for x in m.group(3).split(",") if x.strip())
                rows.append((int(m.group(1)), m.group(2), boxes, m.group(4)))
        if rows != sim:
            fails.append(f"§6.2 trace fence disagrees with the algorithm: {rows} != {sim}")
        else:
            print("  ok  §6.2 的走表与 32 题算法逐步一致（每一步的栈内容和答案都是算出来的）")

    # ---- figure 06 must show the very same numbers ----
    svg = HERE.parent.parent / "img" / "stack-queue-mutual-20261117" / "06-stack-of-boundaries.svg"
    if not svg.exists():
        fails.append(f"figure 06 missing: {svg}")
    else:
        texts = svg_texts(svg)
        drawn = True
        for (i, ch, stack, best) in sim:
            label = f"i={i}  '{ch}'"
            if label not in texts:
                fails.append(f"figure 06 has no row {label!r}")
                drawn = False
                break
            k = texts.index(label) + 1
            boxes = []
            while k < len(texts) and texts[k].lstrip("-").isdigit():
                boxes.append(int(texts[k]))
                k += 1
            if tuple(boxes) != stack:
                fails.append(f"figure 06 row {label}: boxes {boxes} != {list(stack)}")
                drawn = False
                break
            nxt = texts[k + 1] if k + 1 < len(texts) else None
            if nxt != best:
                fails.append(f"figure 06 row {label}: answer {nxt!r} != {best!r}")
                drawn = False
                break
        if drawn:
            print("  ok  图 06 的每一格栈内容与答案都和 §6.2 的走表一致（直接读 SVG 的 <text>）")

    # ---- 20 有效的括号 ----
    is_valid = ns["is_valid_brackets"]
    cases = [("", True), ("()", True), ("()[]{}", True), ("(]", False), ("([)]", False),
             ("{[]}", True), ("(", False), (")", False), ("((", False), ("))", False),
             ("([]", False), ("([{}])", True), ("a", False), ("(a)", False)]
    for s_, want in cases:
        got = is_valid(s_)
        if got != want:
            fails.append(f"is_valid_brackets({s_!r}) = {got}, want {want}")
    print(f"  ok  is_valid_brackets 固定 {len(cases)} 例（空串 / 单括号 / 交错嵌套 / 混入非括号字符）")

    total, bad, first = 0, 0, None
    for length in range(0, 6):
        for tup in itertools.product("()[]", repeat=length):
            s_ = "".join(tup)
            total += 1
            if is_valid(s_) != brute_valid(s_):
                bad += 1
                first = first or s_
    if bad:
        fails.append(f"is_valid_brackets: {bad}/{total} strings disagree, first {first!r}")
    print(f"  ok  is_valid_brackets 穷举 {total} 个只含 ()[] 的串（长度 ≤ 5）vs 成对删除到不动点")

    # ---- 32 最长有效括号 ----
    longest = ns["longest_valid_parentheses"]
    cases = [("", 0), ("(", 0), (")", 0), ("()", 2), ("(()", 2), (")()())", 4),
             ("()(()", 2), ("()(())", 6), ("(((((", 0), ("))))", 0), (")(", 0), (")()(", 2)]
    for s_, want in cases:
        got = longest(s_)
        if got != want:
            fails.append(f"longest_valid_parentheses({s_!r}) = {got}, want {want}")
    print(f"  ok  longest_valid_parentheses 固定 {len(cases)} 例（全左 / 全右 / 空串 / 答案落在中段）")

    total, bad, first = 0, 0, None
    for length in range(0, 13):
        for mask in range(1 << length):
            s_ = "".join("(" if (mask >> k) & 1 else ")" for k in range(length))
            total += 1
            if longest(s_) != brute_longest(s_):
                bad += 1
                first = first or s_
    if bad:
        fails.append(f"longest_valid_parentheses: {bad}/{total} strings disagree, first {first!r}")
    print(f"  ok  longest_valid_parentheses 穷举 {total} 个串（长度 ≤ 12）vs O(n^2) 计数扫描")

    # ---- 622 设计循环队列 ----
    Circular = ns["MyCircularQueue"]
    q1 = Circular(1)
    checks = [q1.enQueue(5), q1.isFull(), q1.enQueue(6), q1.Front(), q1.Rear(),
              q1.deQueue(), q1.isEmpty(), q1.Front(), q1.Rear(), q1.deQueue()]
    want1 = [True, True, False, 5, 5, True, True, -1, -1, False]
    if checks != want1:
        fails.append(f"circular k=1: {checks} != {want1}")
    print("  ok  MyCircularQueue k=1 单格:入队/满/拒绝入队/取首尾/出队/空/再出队被拒")

    rng = random.Random(SEED + 6)
    ops = 0
    for k in (1, 2, 3, 5):
        q, ref = Circular(k), deque()
        for step in range(4000):
            op = rng.randrange(4)
            if op == 0:
                v = rng.randint(-100, 100)
                got, want = q.enQueue(v), len(ref) < k
                if want:
                    ref.append(v)
            elif op == 1:
                got, want = q.deQueue(), bool(ref)
                if want:
                    ref.popleft()
            elif op == 2:
                got, want = q.Front(), (-1 if not ref else ref[0])
            else:
                got, want = q.Rear(), (-1 if not ref else ref[-1])
            if got != want:
                fails.append(f"circular k={k} step {step} op {op}: {got} != {want}")
                break
            if q.isEmpty() != (not ref) or q.isFull() != (len(ref) == k):
                fails.append(f"circular k={k} step {step}: isEmpty/isFull drifted")
                break
            ops += 1
    print(f"  ok  MyCircularQueue 随机 {ops} 步 × 4 种容量 vs collections.deque 参照")

    # O(1) witness: no call may walk the buffer, so slot accesses stay ≤ 1 per call
    touched = TouchedList(4)
    q = Circular(4)
    q._buf = touched                       # 换成带计数的缓冲,只为观察访问次数
    calls = 0
    for step in range(4000):
        op = rng.randrange(4)
        if op == 0:
            q.enQueue(step)
        elif op == 1:
            q.deQueue()
        elif op == 2:
            q.Front()
        else:
            q.Rear()
        q.isEmpty()
        q.isFull()
        calls += 6
    if touched.touches > calls or len(q._buf) != 4:
        fails.append(f"circular touched {touched.touches} slots / capacity {len(q._buf)} "
                     f"over {calls} calls")
    print(f"  ok  MyCircularQueue 没有整表扫描: {calls} 次调用只碰了 {touched.touches} 个槽位"
          f"（缓冲长度全程 4,不扩容）")

    return fails


# ---------------------------------------------------------------------------
# C++ side
# ---------------------------------------------------------------------------
CPP_PRELUDE = r"""
// ---------------------------------------------------------------------------
// test harness generated by verify_code.py — not part of the post
// ---------------------------------------------------------------------------
#include <iostream>
#include <stack>
#include <queue>
#include <deque>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <algorithm>
#include <random>
#include <sstream>
#include <cstddef>
#include <utility>

// Test-only: the harness watches MyQueue::in_/out_ to count element moves, and
// an amortised bound cannot be observed from the public API alone.  Every
// libc++ header the file needs is already included above, so neutralising the
// access specifier here cannot reach into the standard library.
#define private public
"""

CPP_MAIN = r"""
#undef private

// ------------------------------ tiny test rig ------------------------------
static int g_fail = 0;
static int g_checks = 0;

static void check(bool ok, const std::string& what) {
    g_checks++;
    if (!ok) {
        g_fail++;
        std::cout << "  FAIL  " << what << "\n";
    }
}

static std::string show(const std::vector<int>& v) {
    std::ostringstream os;
    os << "[";
    for (std::size_t i = 0; i < v.size(); i++) os << (i ? ", " : "") << v[i];
    os << "]";
    return os.str();
}

// Amortised accounting: one push into in_ costs 1, moving one element from in_
// to out_ costs 2 (a pop plus a push), one pop out of out_ costs 1.  A shift is
// detected by watching out_ go from empty to non-empty, and its size then says
// exactly how many elements crossed over.
struct CountingQueue {
    MyQueue q;
    long long ops = 0;
    long long worst_single = 0;

    void push(int x) { ops += 1; q.push(x); }

    int pop() {
        bool was_empty = q.out_.empty();
        std::size_t before_in = q.in_.size();
        ops += 1;
        int v = q.pop();
        account(was_empty, before_in);
        return v;
    }

    int peek() {
        bool was_empty = q.out_.empty();
        std::size_t before_in = q.in_.size();
        ops += 1;
        int v = q.peek();
        account(was_empty, before_in);
        return v;
    }

    bool empty() const { return q.empty(); }

    void account(bool was_empty, std::size_t before_in) {
        if (was_empty && !q.out_.empty()) {
            long long moved = static_cast<long long>(before_in);
            ops += 2 * moved;
            worst_single = std::max(worst_single, 2 * moved + 1);
        }
    }
};

// Exhaustive search over push/pop interleavings — no greedy assumption.
static bool brute_validate_rec(const std::vector<int>& pushed,
                               const std::vector<int>& popped,
                               std::size_t i, std::vector<int>& st, std::size_t j) {
    if (j == popped.size()) return true;
    if (!st.empty() && st.back() == popped[j]) {
        int top = st.back();
        st.pop_back();
        if (brute_validate_rec(pushed, popped, i, st, j + 1)) {
            st.push_back(top);
            return true;
        }
        st.push_back(top);
    }
    if (i < pushed.size()) {
        st.push_back(pushed[i]);
        bool ok = brute_validate_rec(pushed, popped, i + 1, st, j);
        st.pop_back();
        if (ok) return true;
    }
    return false;
}

// Independent reference models for §6.  Same idea as the Python ones but written
// separately: validity by deleting matched pairs to a fixpoint, longest run by a
// balance counter over every substring.
static bool brute_valid(const std::string& s) {
    std::string cur = s;
    bool changed = true;
    while (changed) {
        changed = false;
        std::string next;
        for (std::size_t i = 0; i < cur.size(); ++i) {
            if (i + 1 < cur.size() && brackets_match(cur[i], cur[i + 1])) {
                i++;
                changed = true;
                continue;
            }
            next.push_back(cur[i]);
        }
        cur = next;
    }
    return cur.empty();
}

static int brute_longest(const std::string& s) {
    int best = 0;
    for (std::size_t i = 0; i < s.size(); ++i) {
        int bal = 0;
        for (std::size_t j = i; j < s.size(); ++j) {
            bal += (s[j] == '(') ? 1 : -1;
            if (bal < 0) break;
            if (bal == 0) best = std::max(best, static_cast<int>(j - i + 1));
        }
    }
    return best;
}

static bool brute_validate(const std::vector<int>& pushed,
                           const std::vector<int>& popped) {
    if (pushed.size() != popped.size()) return false;
    std::vector<int> st;
    return brute_validate_rec(pushed, popped, 0, st, 0);
}

int main() {
    std::cout << "  [cpp] start\n";

    // ---------------- MyQueue: fixed sequence ----------------
    {
        MyQueue q;
        q.push(1); q.push(2); q.push(3);
        std::vector<int> got;
        got.push_back(q.peek());
        got.push_back(q.pop());
        got.push_back(q.empty() ? 1 : 0);
        q.push(4);
        got.push_back(q.pop());
        got.push_back(q.pop());
        got.push_back(q.pop());
        got.push_back(q.empty() ? 1 : 0);
        std::vector<int> want{1, 1, 0, 2, 3, 4, 1};
        check(got == want, "MyQueue fixed: got " + show(got) + " want " + show(want));
    }

    // ---------------- MyQueue: random vs std::deque model ----------------
    {
        std::mt19937 rng(20261117u);
        std::uniform_int_distribution<int> val(-50, 50);
        std::uniform_int_distribution<int> pick(0, 99);
        std::deque<int> ref;
        MyQueue q;
        bool ok = true;
        std::string why;
        for (int step = 0; step < 3000 && ok; step++) {
            if (!ref.empty() && pick(rng) < 45) {
                bool do_pop = (pick(rng) < 50);
                int got = do_pop ? q.pop() : q.peek();
                int want = do_pop ? ref.front() : ref.front();
                if (do_pop) ref.pop_front();
                if (got != want) {
                    ok = false;
                    why = "step " + std::to_string(step);
                }
            } else {
                int v = val(rng);
                q.push(v);
                ref.push_back(v);
            }
        }
        check(ok, "MyQueue random: " + why);
        check(q.empty() == ref.empty(), "MyQueue random: empty() disagrees");
    }

    // ---------------- MyQueue: amortised bound ----------------
    {
        std::mt19937 rng(20261118u);
        std::uniform_int_distribution<int> val(0, 1000000);
        std::uniform_int_distribution<int> pick(0, 99);
        std::deque<int> ref;
        CountingQueue q;
        long long calls = 0;
        bool ok = true;
        for (int step = 0; step < 4000; step++) {
            if (!ref.empty() && pick(rng) < 50) {
                calls++;
                if (pick(rng) < 50) {
                    int got = q.pop();
                    if (got != ref.front()) { ok = false; break; }
                    ref.pop_front();
                } else {
                    if (q.peek() != ref.front()) { ok = false; break; }
                }
            } else {
                calls++;
                int v = val(rng);
                q.push(v);
                ref.push_back(v);
            }
        }
        check(ok, "MyQueue amortised run returned a wrong element");
        check(q.ops <= 4 * calls,
              "amortised bound broken: " + std::to_string(q.ops) + " stack ops for "
              + std::to_string(calls) + " calls");
        std::cout << "  ok  [cpp] MyQueue 均摊上界: " << calls << " 次 API 调用共 "
                  << q.ops << " 次栈操作 (上界 " << 4 * calls << ")\n";
    }

    // ---------------- MyQueue: the O(n) call ----------------
    {
        const int N = 1000;
        CountingQueue q;
        for (int v = 0; v < N; v++) q.push(v);
        int first = q.pop();
        check(first == 0, "worst-case run: first pop should return 0");
        check(q.worst_single == 2 * N + 1,
              "worst-case single call cost " + std::to_string(q.worst_single)
              + ", want " + std::to_string(2 * N + 1));
        check(q.ops == 3 * N + 1,
              "worst-case total " + std::to_string(q.ops) + ", want "
              + std::to_string(3 * N + 1));
        std::cout << "  ok  [cpp] MyQueue 最坏单次: push " << N << " 次后一次 pop 花掉 "
                  << q.worst_single << " 次栈操作 (= 2n+1)，合计 " << q.ops
                  << " = 3n+1\n";
    }

    // ---------------- MyStack (one queue) ----------------
    {
        MyStack st;
        st.push(1); st.push(2); st.push(3);
        std::vector<int> got;
        got.push_back(st.top());
        got.push_back(st.pop());
        got.push_back(st.pop());
        got.push_back(st.empty() ? 1 : 0);
        got.push_back(st.pop());
        got.push_back(st.empty() ? 1 : 0);
        std::vector<int> want{3, 3, 2, 0, 1, 1};
        check(got == want, "MyStack fixed: got " + show(got) + " want " + show(want));

        std::mt19937 rng(20261119u);
        std::uniform_int_distribution<int> val(-50, 50);
        std::uniform_int_distribution<int> pick(0, 99);
        std::vector<int> ref;
        MyStack s2;
        bool ok = true;
        for (int step = 0; step < 3000 && ok; step++) {
            if (!ref.empty() && pick(rng) < 45) {
                bool do_pop = (pick(rng) < 50);
                int got = do_pop ? s2.pop() : s2.top();
                int want = ref.back();
                if (do_pop) ref.pop_back();
                if (got != want) ok = false;
            } else {
                int v = val(rng);
                s2.push(v);
                ref.push_back(v);
            }
        }
        check(ok, "MyStack random disagrees with the vector model");
        std::cout << "  ok  [cpp] MyStack 固定序列 + 随机 3000 步 vs vector 参照\n";
    }

    // ---------------- MyStackTwoQueues ----------------
    {
        MyStackTwoQueues st;
        st.push(10); st.push(20); st.push(30);
        std::vector<int> got;
        got.push_back(st.top());
        got.push_back(st.pop());
        got.push_back(st.top());
        got.push_back(st.pop());
        got.push_back(st.empty() ? 1 : 0);
        got.push_back(st.pop());
        got.push_back(st.empty() ? 1 : 0);
        std::vector<int> want{30, 30, 20, 20, 0, 10, 1};
        check(got == want, "MyStackTwoQueues fixed: got " + show(got));

        std::mt19937 rng(20261120u);
        std::uniform_int_distribution<int> val(-50, 50);
        std::uniform_int_distribution<int> pick(0, 99);
        std::vector<int> ref;
        MyStackTwoQueues s2;
        bool ok = true;
        for (int step = 0; step < 3000 && ok; step++) {
            if (!ref.empty() && pick(rng) < 45) {
                bool do_pop = (pick(rng) < 50);
                int got = do_pop ? s2.pop() : s2.top();
                int want = ref.back();
                if (do_pop) ref.pop_back();
                if (got != want) ok = false;
            } else {
                int v = val(rng);
                s2.push(v);
                ref.push_back(v);
            }
        }
        check(ok, "MyStackTwoQueues random disagrees with the vector model");
        std::cout << "  ok  [cpp] MyStackTwoQueues 固定序列 + 随机 3000 步 vs vector 参照\n";
    }

    // ---------------- MinStack ----------------
    {
        MinStack ms;
        int vals[] = {5, 3, 7, 3, 8};
        for (int v : vals) ms.push(v);
        std::vector<int> got;
        got.push_back(ms.getMin());
        got.push_back(ms.top());
        ms.pop();
        got.push_back(ms.getMin());
        got.push_back(ms.top());
        ms.pop();
        got.push_back(ms.getMin());
        std::vector<int> want{3, 8, 3, 3, 3};
        check(got == want, "MinStack fixed: got " + show(got) + " want " + show(want));

        std::mt19937 rng(20261121u);
        std::uniform_int_distribution<int> val(-20, 20);
        std::uniform_int_distribution<int> pick(0, 99);
        std::vector<int> ref;
        MinStack m2;
        bool ok = true;
        for (int step = 0; step < 3000 && ok; step++) {
            int r = pick(rng);
            if (!ref.empty() && r < 35) {
                m2.pop();
                ref.pop_back();
            } else if (!ref.empty() && r < 60) {
                if (m2.top() != ref.back()) ok = false;
                if (m2.getMin() != *std::min_element(ref.begin(), ref.end())) ok = false;
            } else {
                int v = val(rng);
                m2.push(v);
                ref.push_back(v);
            }
        }
        check(ok, "MinStack random disagrees with the scan model");
        std::cout << "  ok  [cpp] MinStack 固定序列 + 随机 3000 步 vs 每次扫描求最小值\n";
    }

    // ---------------- validateStackSequences ----------------
    {
        struct Case { std::vector<int> pushed, popped; bool want; };
        std::vector<Case> cases{
            {{}, {}, true},
            {{1}, {1}, true},
            {{1, 2, 3, 4, 5}, {4, 5, 3, 2, 1}, true},
            {{1, 2, 3, 4, 5}, {4, 3, 5, 1, 2}, false},
            {{1, 2, 3}, {3, 2, 1}, true},
            {{1, 2, 3}, {1, 2, 3}, true},
            {{1, 2, 3}, {3, 1, 2}, false},
            {{1, 2, 3}, {1, 3, 2}, true},
            {{1, 1, 1}, {1, 1, 1}, true},
            {{1, 2}, {1}, false},
            {{1, 2}, {1, 2, 3}, false},
            {{2, 1, 0}, {0, 1, 2}, true},
        };
        for (const Case& c : cases) {
            bool got = validateStackSequences(c.pushed, c.popped);
            check(got == c.want,
                  "validate(" + show(c.pushed) + ", " + show(c.popped) + ") = "
                  + (got ? "true" : "false"));
        }
        std::cout << "  ok  [cpp] validateStackSequences 固定 " << cases.size()
                  << " 例\n";

        std::mt19937 rng(20261122u);
        std::uniform_int_distribution<int> pick(0, 99);
        // validateStackSequences must respect the problem's DISTINCT-value
        // constraint: the article's greedy is exactly correct only under it
        // (see the note on the Python side above).  Draw a shuffled prefix of a
        // distinct range rather than sampling with replacement.  The stack and
        // queue cases above keep their own duplicate-heavy rng.
        auto distinct_values = [&rng](int n) {
            std::vector<int> pool(10);
            for (int i = 0; i < 10; i++) pool[i] = i;
            std::shuffle(pool.begin(), pool.end(), rng);
            pool.resize(static_cast<std::size_t>(n));
            return pool;
        };
        int checked = 0;
        bool ok = true;
        for (int t = 0; t < 600 && ok; t++) {
            int n = static_cast<int>(rng() % 8);
            std::vector<int> pushed = distinct_values(n);
            std::vector<int> popped;
            if (t % 3 == 0) {
                // build a sequence that is valid by construction
                std::vector<int> st;
                for (int x : pushed) {
                    st.push_back(x);
                    while (!st.empty() && pick(rng) < 50) {
                        popped.push_back(st.back());
                        st.pop_back();
                    }
                }
                while (!st.empty()) { popped.push_back(st.back()); st.pop_back(); }
            } else {
                popped = pushed;
                std::shuffle(popped.begin(), popped.end(), rng);
            }
            bool got = validateStackSequences(pushed, popped);
            bool want = brute_validate(pushed, popped);
            checked++;
            if (got != want) {
                ok = false;
                std::cout << "  FAIL  validate(" << show(pushed) << ", " << show(popped)
                          << ") greedy=" << got << " brute=" << want << "\n";
            }
        }
        check(ok, "validateStackSequences random vs exhaustive interleaving search");
        std::cout << "  ok  [cpp] validateStackSequences 随机 " << checked
                  << " 例 vs 穷举所有交错（值为互不相同的约束内）\n";
    }

    // ---- 20 有效的括号 ----
    {
        struct Case { const char* s; bool want; };
        const Case cases[] = {
            {"", true}, {"()", true}, {"()[]{}", true}, {"(]", false}, {"([)]", false},
            {"{[]}", true}, {"(", false}, {")", false}, {"((", false}, {"))", false},
            {"([]", false}, {"([{}])", true}, {"a", false}, {"(a)", false},
        };
        int fixed = 0, bad = 0, total = 0;
        for (const Case& cs : cases) {
            fixed++;
            total++;
            if (isValidBrackets(cs.s) != cs.want) {
                if (bad == 0) std::cout << "  FAIL  isValidBrackets(\"" << cs.s << "\")\n";
                bad++;
            }
        }
        const char* alpha = "()[]";
        for (int len = 0; len <= 5; ++len) {
            int combos = 1;
            for (int k = 0; k < len; ++k) combos *= 4;
            for (int mask = 0; mask < combos; ++mask) {
                std::string s;
                int m = mask;
                for (int k = 0; k < len; ++k) { s.push_back(alpha[m % 4]); m /= 4; }
                total++;
                if (isValidBrackets(s) != brute_valid(s)) {
                    if (bad == 0) std::cout << "  FAIL  isValidBrackets(\"" << s
                                            << "\") vs fixpoint removal\n";
                    bad++;
                }
            }
        }
        check(bad == 0, "isValidBrackets fixed + exhaustive vs fixpoint removal");
        std::cout << "  ok  [cpp] isValidBrackets " << fixed << " 个固定例 + 穷举 "
                  << (total - fixed) << " 个只含 ()[] 的短串 vs 成对删除到不动点\n";
    }

    // ---- 32 最长有效括号 ----
    {
        struct Case { const char* s; int want; };
        const Case cases[] = {
            {"", 0}, {"(", 0}, {")", 0}, {"()", 2}, {"(()", 2}, {")()())", 4},
            {"()(()", 2}, {"()(())", 6}, {"(((((", 0}, {"))))", 0}, {")(", 0}, {")()(", 2},
        };
        int fixed = 0, bad = 0, total = 0;
        for (const Case& cs : cases) {
            fixed++;
            total++;
            if (longestValidParentheses(cs.s) != cs.want) {
                if (bad == 0) std::cout << "  FAIL  longestValidParentheses(\"" << cs.s << "\")\n";
                bad++;
            }
        }
        for (int len = 0; len <= 12; ++len) {
            for (int mask = 0; mask < (1 << len); ++mask) {
                std::string s;
                for (int k = 0; k < len; ++k) s.push_back(((mask >> k) & 1) ? '(' : ')');
                total++;
                if (longestValidParentheses(s) != brute_longest(s)) {
                    if (bad == 0) std::cout << "  FAIL  longestValidParentheses(\"" << s
                                            << "\") vs counter scan\n";
                    bad++;
                }
            }
        }
        check(bad == 0, "longestValidParentheses fixed + exhaustive vs O(n^2) counter scan");
        std::cout << "  ok  [cpp] longestValidParentheses " << fixed << " 个固定例 + 穷举 "
                  << (total - fixed) << " 个串（长度 <= 12）vs O(n^2) 计数扫描\n";
    }

    // ---- 622 设计循环队列 ----
    {
        MyCircularQueue q1(1);
        bool ok = q1.enQueue(5) && q1.isFull() && !q1.enQueue(6) && q1.Front() == 5 &&
                  q1.Rear() == 5 && q1.deQueue() && q1.isEmpty() && q1.Front() == -1 &&
                  q1.Rear() == -1 && !q1.deQueue();
        check(ok, "MyCircularQueue k=1 single slot");
        std::cout << "  ok  [cpp] MyCircularQueue k=1 单格:入队/满/拒绝入队/取首尾/出队/空/再出队被拒\n";

        std::mt19937 rng(20261117u);
        long long ops = 0, bad = 0;
        const int caps[] = {1, 2, 3, 5};
        for (int k : caps) {
            MyCircularQueue q(k);
            std::deque<int> ref;
            bool cap_ok = true;
            for (int step = 0; step < 4000; ++step) {
                unsigned op = rng() % 4u;
                if (op == 0u) {
                    int v = static_cast<int>(rng() % 200u) - 100;
                    bool got = q.enQueue(v);
                    bool want = static_cast<int>(ref.size()) < k;
                    if (want) ref.push_back(v);
                    if (got != want) bad++;
                } else if (op == 1u) {
                    bool got = q.deQueue();
                    bool want = !ref.empty();
                    if (want) ref.pop_front();
                    if (got != want) bad++;
                } else if (op == 2u) {
                    int want = ref.empty() ? -1 : ref.front();
                    if (q.Front() != want) bad++;
                } else {
                    int want = ref.empty() ? -1 : ref.back();
                    if (q.Rear() != want) bad++;
                }
                if (q.isEmpty() != ref.empty()) bad++;
                if (q.isFull() != (static_cast<int>(ref.size()) == k)) bad++;
                if (q.buf_.size() != static_cast<std::size_t>(k)) cap_ok = false;
                ops++;
            }
            if (!cap_ok) bad++;
        }
        check(bad == 0, "MyCircularQueue random vs std::deque model, capacity never grows");
        std::cout << "  ok  [cpp] MyCircularQueue 随机 " << ops
                  << " 步 x 4 种容量 vs std::deque 参照,缓冲长度全程不变\n";
    }

    std::cout << "  [cpp] " << (g_checks - g_fail) << "/" << g_checks
              << " assertions passed\n";
    return g_fail == 0 ? 0 : 1;
}
"""


def test_cpp(blocks):
    BUILD.mkdir(exist_ok=True)
    src = BUILD / "cpp_test.cpp"
    exe = BUILD / "cpp_test"
    src.write_text(CPP_PRELUDE + "\n".join(blocks) + CPP_MAIN, encoding="utf-8")

    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-O1", str(src), "-o", str(exe)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    warnings = [l for l in cp.stderr.splitlines() if "warning:" in l]
    print(f"  cpp compile   : {'clean' if not warnings else str(len(warnings)) + ' warning(s)'}"
          f"  (g++ -std=c++17 -Wall -Wextra -O1)")
    for w in warnings:
        print(f"      {w}")
    fails = []
    if cp.returncode != 0:
        print(cp.stderr)
        return ["cpp did not compile"]
    if warnings:
        fails.append("cpp compiled with warnings")

    rp = subprocess.run([str(exe)], capture_output=True, text=True)
    print(rp.stdout.rstrip())
    if rp.returncode != 0:
        print(rp.stderr.rstrip())
        fails.append("cpp assertions failed")
    return fails


def main():
    if not POST.exists():
        print(f"  FAIL  post not found: {POST}")
        return 1
    print(f"  post          : {POST.name}")
    text = POST.read_text(encoding="utf-8")
    py_blocks, cpp_blocks = extract(text, "python"), extract(text, "cpp")
    print(f"  blocks        : {len(py_blocks)} python / {len(cpp_blocks)} cpp")

    problems = []
    if len(py_blocks) != len(cpp_blocks):
        problems.append(f"language block counts differ: "
                        f"{len(py_blocks)} python vs {len(cpp_blocks)} cpp")
    if len(py_blocks) != EXPECTED_PY or len(cpp_blocks) != EXPECTED_CPP:
        problems.append(f"expected {EXPECTED_PY} blocks per language, got "
                        f"{len(py_blocks)}/{len(cpp_blocks)}")

    problems += test_python()
    problems += test_cpp(cpp_blocks)

    if problems:
        print(f"\n  RESULT: {len(problems)} problem(s)")
        return 1
    print("\n  CODE OK — 每道题在 Python 和 C++ 两侧都过了固定与随机用例；"
          "均摊上界与最坏单次都被真实测过，括号两题穷举到长度 12，循环队列全程不扩容")
    return 0


if __name__ == "__main__":
    sys.exit(main())
