#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code gate for _posts/2026-11-10-chain-reversal.md.

结构（三道小门，最后打印 CODE OK 并 exit 0）：

1. **抽取**：用正则从正文里抓 ```python 与 ```cpp 围栏，断言两边数量相等
   （11 + 11），断言没有 `bits/stdc++.h`、正文的 cpp 块里没有 `main`。
   代码只从 .md 里抽，脚本里不留第二份副本。

2. **Python 侧真跑**：11 个代码块全部 compile() 后 exec 进同一个命名空间
   （块之间互相调用：reverseKGroup → reverseN → reverseList）。

3. **对拍用的是独立的外部参照，不是「自己跟自己的另一个实现比」**：
   - 所有链表题的期望值都由**纯 Python list** 上的下标/切片实现给出
     （`xs[::-1]`、`xs[:n][::-1] + xs[n:]`、按 k 切块重排、`del ys[len(ys)-n]`…）；
     实际结果先转回 list 再比。
   - 环形检测的参照是「哈希集合记录走过的节点，第一个重复的就是环起点」。
   - K 个一组反转的参照是「先转成 list、切片重排、再按结果比 list」。
   - 相交链表的参照是「把 A 的节点放进集合，再沿 B 走」，比的是**节点身份**。
   另有一批「散文断言」的实测：正文与 §6 归纳表里写「这样写会错」，这里就把那个
   错法真写出来跑一遍，看它到底是错、是崩、还是其实等价（§6 表格逐条覆盖：
   206 两行顺序 / 92 只减 m / 25 数 k 个的时机 / 24 换节点还是换值 /
   876 漏 fast.next / 142 不判 null / 160 判 .next / 143 三个零件的组合）。

4. **C++ 侧真编真跑**：把正文的 11 个 cpp 块拼上 `struct ListNode` 和 harness，
   用同一批用例（Python 侧把用例和期望值作为**字面量**写进生成的 .cpp），
   `g++ -std=c++17 -Wall -Wextra -Werror -O1` 零警告，运行后要求
   两边的 64 位 FNV-1a 摘要逐位相同。

运行：python3 assets/blog/chain-reversal-20261110/verify_code.py
"""

from __future__ import annotations

import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # assets/blog/<slug>/ -> 仓库根
POST = ROOT / "_posts" / "2026-11-10-chain-reversal.md"
GEN_CPP = HERE / "_generated_chain_reversal_test.cpp"
GEN_BIN = Path(tempfile.gettempdir()) / "chain_reversal_test"   # 别落进 assets/
SEED = 20261110

EXPECT_PY, EXPECT_CPP = 11, 11

MASK64 = (1 << 64) - 1
checks = 0
failures: list[str] = []
digest = 1469598103934665603


def feed(v: int) -> None:
    global digest
    digest ^= (v & MASK64)
    digest = (digest * 1099511628211) & MASK64


def feed_all(xs) -> None:
    for x in xs:
        feed(x)


# --------------------------------------------------------------------------
# 0. 链表节点 + 参照实现（全部只依赖 Python list）
# --------------------------------------------------------------------------
class ListNode:
    """文章的代码块直接用这个名字，正文没有给定义，所以由门提供。"""

    def __init__(self, val: int = 0, next=None):
        self.val = val
        self.next = next


def build(xs, cycle_entry: int | None = None, tail=None):
    """按 list 建一条链；cycle_entry 给定时把尾巴接回第 entry 个节点。"""
    head = tail
    nodes = []
    for v in reversed(xs):
        head = ListNode(v, head)
        nodes.append(head)
    nodes.reverse()
    if cycle_entry is not None and nodes:
        nodes[-1].next = nodes[cycle_entry]
    return head


def build_nodes(xs) -> tuple:
    """建链并同时返回节点表：F2 要按**身份**把返回的节点映射回下标。"""
    head = None
    nodes = []
    for v in reversed(xs):
        head = ListNode(v, head)
        nodes.append(head)
    nodes.reverse()
    return head, nodes


def prepend(xs, tail):
    """在 tail 前面接一条 xs 造的链，返回新头（xs 为空就直接返回 tail）。"""
    head = tail
    for v in reversed(xs):
        head = ListNode(v, head)
    return head


def to_list_capped(head, cap: int) -> list:
    """带步数上限的遍历：和 C++ 侧 toVecCapped 一一对应（含环时截断）。"""
    out = []
    cur = head
    while cur is not None and len(out) <= cap:
        out.append(cur.val)
        cur = cur.next
    return out


def has_cycle(head) -> bool:
    slow = fast = head
    while fast is not None and fast.next is not None:
        slow, fast = slow.next, fast.next.next
        if slow is fast:
            return True
    return False


def node_index(nodes, p) -> int:
    for i, n in enumerate(nodes):
        if n is p:
            return i
    return -1


def oracle_rev(xs):
    return xs[::-1]


def oracle_rev_n(xs, n):
    """reverseN 的契约：1 <= n；n 超过长度时整条反转。"""
    if n >= len(xs):
        return xs[::-1]
    return xs[:n][::-1] + xs[n:]


def oracle_rev_between(xs, m, n):
    if m >= n:
        return list(xs)                      # 代码里 m >= n 直接返回原链表
    if m == 1:
        return oracle_rev_n(xs, n)
    return xs[: m - 1] + xs[m - 1: n][::-1] + xs[n:]


def oracle_rev_k(xs, k):
    if k <= 1 or not xs:
        return list(xs)
    out = []
    for i in range(0, len(xs), k):
        chunk = xs[i: i + k]
        out += chunk[::-1] if len(chunk) == k else chunk
    return out


def oracle_pal(xs):
    return xs == xs[::-1]


def oracle_remove_nth(xs, n):
    if n > len(xs):
        return list(xs)                      # 代码里有「n 越界保护」
    ys = list(xs)
    del ys[len(ys) - n]
    return ys


def oracle_middle(xs):
    return xs[len(xs) // 2:]


def oracle_detect_cycle(head):
    """环检测的外部参照：哈希集合记录走过的节点，第一个重复的就是环起点。

    注意它**只靠走**——不看构造这条链时记下的 entry，所以是真外部参照。
    """
    seen = set()
    cur = head
    while cur is not None:
        if id(cur) in seen:
            return cur
        seen.add(id(cur))
        cur = cur.next
    return None


def oracle_intersection(ha, hb):
    """相交链表的外部参照：把 A 的节点全放进哈希集合，再沿 B 走。

    第一个「已经在集合里」的节点就是交点；B 走完还没撞上就是不相交。
    """
    seen = set()
    p = ha
    while p is not None:
        seen.add(id(p))
        p = p.next
    p = hb
    while p is not None:
        if id(p) in seen:
            return p
        p = p.next
    return None


# --------------------------------------------------------------------------
# 1. 断言与喂摘要（Python 侧；与 C++ 侧 harness 一一对应）
# --------------------------------------------------------------------------
def check(label: str, got, want) -> None:
    global checks
    checks += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def check_long(label: str, got: int, want: int) -> None:
    """与 C++ 的 expectLong 对齐：先 feed(got) 再比。"""
    feed(got)
    check(label, got, want)


def check_vec(label: str, got_node, want: list) -> None:
    """与 C++ 的 expectVec 对齐：先 feed(len(want))，再 feed(实际结果)。"""
    feed(len(want))
    if got_node is not None and has_cycle(got_node):
        failures.append(f"{label}: 结果成环（不该有环）")
        return
    got = to_list_capped(got_node, len(want) + 8)
    feed_all(got)
    check(label, got, list(want))


# --------------------------------------------------------------------------
# 2. 门 1：抽取代码块
# --------------------------------------------------------------------------
def extract(src: str):
    py = re.findall(r"^```python[ \t]*\n(.*?)^```[ \t]*$", src, re.M | re.S)
    cpp = re.findall(r"^```cpp[ \t]*\n(.*?)^```[ \t]*$", src, re.M | re.S)
    return py, cpp


def gate_extract() -> tuple[list[str], list[str]]:
    global checks
    print("== 门 1：从正文抽取代码块 ==")
    src = POST.read_text(encoding="utf-8")
    py, cpp = extract(src)
    print(f"  {POST.name}: python {len(py)} 块, cpp {len(cpp)} 块")
    checks += 1
    if len(py) != EXPECT_PY or len(cpp) != EXPECT_CPP:
        failures.append(f"围栏数量: python {len(py)} / cpp {len(cpp)}，"
                        f"期望 {EXPECT_PY} / {EXPECT_CPP}")
    checks += 1
    if len(py) != len(cpp):
        failures.append(f"两种语言围栏数量不等: {len(py)} vs {len(cpp)}")
    checks += 1
    if "bits/stdc++.h" in src:
        failures.append("正文里出现了 bits/stdc++.h（clang 没有这个头）")
    checks += 1
    if any(re.search(r"\bint\s+main\s*\(", b) for b in cpp):
        failures.append("正文的 cpp 块里出现了 main（harness 才该提供 main）")
    return py, cpp


# --------------------------------------------------------------------------
# 3. 门 2：Python 侧真跑 + 对拍
# --------------------------------------------------------------------------
F1_OPS = [
    # (名字, 是否返回节点, Python 调用, C++ 调用模板, 期望值)
    ("reverseList", "vec",
     lambda ns, xs, p: ns["reverseList"](build(xs)),
     "reverseList(build(xs))",
     lambda xs, p: oracle_rev(xs)),
    ("reverseListRec", "vec",
     lambda ns, xs, p: ns["reverseListRec"](build(xs)),
     "reverseListRec(build(xs))",
     lambda xs, p: oracle_rev(xs)),
    ("reverseN", "vec",
     lambda ns, xs, p: ns["reverseN"](build(xs), p["n1"]),
     "reverseN(build(xs), {n1})",
     lambda xs, p: oracle_rev_n(xs, p["n1"])),
    ("reverseBetween", "vec",
     lambda ns, xs, p: ns["reverseBetween"](build(xs), p["m"], p["n"]),
     "reverseBetween(build(xs), {m}, {n})",
     lambda xs, p: oracle_rev_between(xs, p["m"], p["n"])),
    ("reverseKGroup", "vec",
     lambda ns, xs, p: ns["reverseKGroup"](build(xs), p["k"]),
     "reverseKGroup(build(xs), {k})",
     lambda xs, p: oracle_rev_k(xs, p["k"])),
    ("isPalindromeList", "long",
     lambda ns, xs, p: 1 if ns["isPalindromeList"](build(xs)) else 0,
     "isPalindromeList(build(xs)) ? 1 : 0",
     lambda xs, p: 1 if oracle_pal(xs) else 0),
    ("isPalindromeRec", "long",
     lambda ns, xs, p: 1 if ns["isPalindromeRec"](build(xs)) else 0,
     "isPalindromeRec(build(xs)) ? 1 : 0",
     lambda xs, p: 1 if oracle_pal(xs) else 0),
    ("removeNthFromEnd", "vec",
     lambda ns, xs, p: ns["removeNthFromEnd"](build(xs), p["n2"]),
     "removeNthFromEnd(build(xs), {n2})",
     lambda xs, p: oracle_remove_nth(xs, p["n2"])),
    ("middleNode", "vec",
     lambda ns, xs, p: ns["middleNode"](build(xs)),
     "middleNode(build(xs))",
     lambda xs, p: oracle_middle(xs)),
]


def make_f1_cases() -> list[tuple[list, dict]]:
    """用例参数由这一处决定，Python 与 C++ 两侧都从这里取（单一事实来源）。"""
    rnd = random.Random(SEED)
    cases: list[tuple[list, dict]] = []

    def add(xs, n1=None, m=None, n=None, k=None, n2=None):
        L = len(xs)
        p = {
            "n1": L if n1 is None else n1,
            "m": 1 if m is None else m,
            "n": L if n is None else n,
            "k": 1 if k is None else k,
            "n2": 1 if n2 is None else n2,
        }
        cases.append((list(xs), p))

    # --- 边界：空表 / 单节点 / 两节点 / 全相等值 / k=1 / k=n / k>n / k=0 ---
    add([])
    add([7])
    add([1, 2])
    add([5, 5, 5, 5], k=1)
    add([1, 2, 3], k=3)
    add([1, 2, 3], k=4)
    add([1, 2, 3, 4], k=0)
    add([1, 2, 3, 4], k=2)
    add([1, 2, 3, 4], m=2, n=3, n1=2)
    add([1, 2, 3, 4], m=1, n=4, n1=4)
    add([1, 2, 3, 4], m=3, n=3, n1=1, n2=2)        # m == n：区间长度 1
    add([1, 2, 3, 4], m=3, n=2, n1=2)              # m > n：原样返回
    add([1, 2, 3, 4], n1=9, n2=9)                  # 两个「越界保护」分支
    add([1, 2, 3], n2=3)                           # 删头结点：必须靠 dummy
    add([1, 2, 3], n2=1)                           # 删尾结点
    add([9, 9, 9, 9, 9], n2=4, k=2)

    # --- 随机：长度 0..8，取值 0..3（全相等值出现得足够频繁） ---
    for _ in range(140):
        L = rnd.randint(0, 8)
        xs = [rnd.randint(0, 3) for _ in range(L)]
        k = rnd.choice([0, 1, 2, 3, L, L + 1, rnd.randint(1, 5)])
        n1 = rnd.choice([1, max(1, L), L + 1, rnd.randint(1, max(1, L))])
        m = rnd.randint(1, max(1, L))
        n = rnd.randint(m, max(m, L))
        n2 = rnd.choice([1, max(1, L), L + 1, rnd.randint(1, max(1, L))])
        add(xs, n1=n1, m=m, n=n, k=k, n2=n2)
    return cases


def make_f2_cases() -> list[tuple[list, int]]:
    """detectCycle：随机环形链 + 若干确定性形状。"""
    rnd = random.Random(SEED + 1)
    cases = [([1], 0), ([1, 2], 0), ([1, 2], 1), ([1, 2, 3, 4], -1),
             ([5, 5, 5], 1), ([1, 2, 3, 4, 5, 6], 3)]
    for _ in range(60):
        L = rnd.randint(1, 8)
        xs = [rnd.randint(0, 3) for _ in range(L)]
        entry = -1 if rnd.random() < 0.35 else rnd.randrange(L)
        cases.append((xs, entry))
    return cases


def make_f3_cases() -> list[tuple[list, list, list]]:
    """getIntersectionNode：(A 私有部分, B 私有部分, 公共尾巴)。"""
    rnd = random.Random(SEED + 2)
    cases = [([], [], []), ([1], [], []), ([], [2], []),
             ([1, 2], [3], [4, 5]), ([1], [2, 3, 4], [9])]
    for _ in range(40):
        a = [rnd.randint(0, 3) for _ in range(rnd.randint(0, 6))]
        b = [rnd.randint(0, 3) for _ in range(rnd.randint(0, 6))]
        c = [] if rnd.random() < 0.3 else [rnd.randint(0, 3)
                                          for _ in range(rnd.randint(1, 4))]
        cases.append((a, b, c))
    return cases


def gate_python(py_blocks: list[str], f1, f2, f3):
    print("\n== 门 2：Python 侧真跑 + 对拍（参照物是纯 list 实现） ==")
    ns: dict = {"ListNode": ListNode}
    for i, body in enumerate(py_blocks):
        try:
            code = compile(body, f"<block {i}>", "exec")
        except SyntaxError as exc:
            failures.append(f"第 {i} 块语法错误: {exc}")
            print(f"  !! 第 {i} 块语法错误: {exc}")
            return ns
        exec(code, ns)                                   # noqa: S102
    print(f"  {len(py_blocks)} 块 compile + exec 完成，命名空间 {len(ns)} 个名字")

    print(f"  用例：F1 {len(f1)} 张随机/边界链表 × {len(F1_OPS)} 个函数、"
          f"F2 {len(f2)} 条环形链、F3 {len(f3)} 对相交链表")

    # ---- F1：9 个函数逐个与 list 参照比 ----
    for i, (xs, p) in enumerate(f1):
        for name, kind, call, _expr, want in F1_OPS:
            if kind == "vec":
                check_vec(f"F1#{i} {name}", call(ns, xs, p), want(xs, p))
            else:
                check_long(f"F1#{i} {name}", call(ns, xs, p), want(xs, p))

    # ---- F2：环形检测 vs 哈希集合 ----
    for i, (xs, entry) in enumerate(f2):
        head, nodes = build_nodes(xs)
        if entry >= 0 and nodes:
            nodes[-1].next = nodes[entry]        # 接成环，环起点是 entry
        got = ns["detectCycle"](head)
        ref = oracle_detect_cycle(head)          # 哈希集合参照物
        check_long(f"F2#{i} detectCycle", node_index(nodes, got),
                   node_index(nodes, ref))
        check(f"F2#{i} 与哈希集合参照返回同一个节点", got, ref)

    # ---- F3：相交链表（比节点身份） ----
    for i, (a, b, c) in enumerate(f3):
        tail = build(c) if c else None
        ha = prepend(a, tail)
        hb = prepend(b, tail)
        got = ns["getIntersectionNode"](ha, hb)
        want = oracle_intersection(ha, hb)       # 哈希集合参照给出的交点
        check_long(f"F3#{i} getIntersectionNode", 1 if got is want else 0, 1)

    print(f"  {checks} 项断言，{len(failures)} 项失败")
    return ns


# --------------------------------------------------------------------------
# 4. 散文断言实测：正文说「这样写会错」，这里就把错法真跑一遍
# --------------------------------------------------------------------------
def reverse_rec_buggy(head):
    """§1.3：漏掉 `head.next = None`。"""
    if head is None or head.next is None:
        return head
    last = reverse_rec_buggy(head.next)
    head.next.next = head
    return last                      # 故意不拆旧链接


def reverse_n_buggy(head, n):
    """§2.1：把 `seg.next = rest` 写成 `new_seg.next = rest`（其余一模一样）。"""
    if head is None:
        return None
    dummy = ListNode(-1, head)
    tail = dummy
    for _ in range(n):
        if tail.next is None:
            break
        tail = tail.next
    seg, rest = dummy.next, tail.next
    tail.next = None
    # 手写一份整体反转，避免依赖文章里的函数（等价于 reverseList(seg)）
    pre, cur = None, seg
    while cur:
        nxt = cur.next
        cur.next = pre
        pre, cur = cur, nxt
    new_seg = pre
    new_seg.next = rest              # 故意：接的是段首
    return new_seg


def pal_compare_buggy(head):
    """§4.2：比较循环写成 `while left and right`。"""
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
    p, rev = slow, None
    while p:
        nxt = p.next
        p.next = rev
        rev = p
        p = nxt
    left, right = head, rev
    while left and right:            # 故意：多加了 left
        if left.val != right.val:
            return False
        left, right = left.next, right.next
    return True


def gate_prose_claims(ns: dict, f1) -> None:
    print("\n== 散文断言实测（正文说会怎样，就真跑一遍） ==")

    # §1.2 「只有两个节点的链表跑一遍」：出循环时 cur 为空、pre 停在 2
    def trace_two_node():
        pre, cur = None, build([1, 2])
        while cur:
            nxt = cur.next
            cur.next = pre
            pre, cur = cur, nxt
        return cur, pre.val
    cur, pre_val = trace_two_node()
    check("§1.2 两节点：[1,2] 出循环 cur 为空、pre 停在 2", (cur, pre_val),
          (None, 2))

    # §1.3 「省掉 head.next = None，尾部出现一个环」
    buggy_head = reverse_rec_buggy(build([1, 2]))
    check("§1.3 漏 head.next=None 真的成环", has_cycle(buggy_head), True)
    check("§1.3 加回那一行就不成环", has_cycle(ns["reverseListRec"](build([1, 2]))),
          False)

    # §2.1 正文说：「长度恰好等于 n（rest 为 null）时两种写法结果一样」
    b3 = to_list_capped(reverse_n_buggy(build([1, 2, 3]), 3), 8)
    g3 = to_list_capped(ns["reverseN"](build([1, 2, 3]), 3), 8)
    print(f"     · [1,2,3] 反转前 3 个（rest 为 null）：正确 {g3}，"
          f"写成 new_seg.next=rest 得到 {b3}")
    # 错法到底什么时候才「看不出来」：把全部用例跑一遍找规律
    hidden, diff = [], []
    for xs, p in f1:
        n = p["n1"]
        b = to_list_capped(reverse_n_buggy(build(xs), n), 64)
        g = to_list_capped(ns["reverseN"](build(xs), n), 64)
        (hidden if b == g else diff).append((len(xs), n))
    seg_len_le_1 = all(min(L, n) <= 1 for L, n in hidden)
    check("§2.1 错法碰巧对 ⟺ 反转段长度 ≤ 1（与 rest 是否为空无关）",
          seg_len_le_1 and all(min(L, n) > 1 for L, n in diff), True)
    print(f"     · 全部 {len(f1)} 个用例：错法结果相同的 {len(hidden)} 个"
          f"（反转段长度分别是 {sorted({min(L, n) for L, n in hidden})}），"
          f"不同的 {len(diff)} 个（反转段长度 ≥ {min(min(L, n) for L, n in diff)}）")

    # §2.1 「这个函数有下界」：n = 0 会成环，n = 1 / 2 正常。
    # 正文写的是「1 <= n <= 链表长度」这个前置条件，所以断言分两半钉住：
    #   ① n = 0 时真的成环（不然那句警告就是空话）
    #   ② n = 1、n = 2 时不成环（不然「下界」就变成了「这个函数到处都坏」）
    # 注意必须走 check_long / check_vec 而不是裸 check：前者才 feed 摘要，
    # 和 C++ 侧的 expectLong / expectVec 一一对应。裸 check 不 feed，
    # 两边的操作序列就会错开，跨语言摘要当场不一致。
    check_long("§2.1 n=0 会成环（所以文档字符串写 1 <= n）",
               1 if has_cycle(ns["reverseN"](build([1, 2, 3]), 0)) else 0, 1)
    z0 = to_list_capped(ns["reverseN"](build([1, 2, 3]), 0), 8)
    print(f"     · n=0 输入 [1,2,3] -> 走 {z0}（尾部回到 1，成环）")
    check_long("§2.1 n=1 不成环",
               1 if has_cycle(ns["reverseN"](build([1, 2, 3]), 1)) else 0, 0)
    check_vec("§2.1 n=1 结果", ns["reverseN"](build([1, 2, 3]), 1), [1, 2, 3])
    check_vec("§2.1 n=2 结果", ns["reverseN"](build([1, 2, 3]), 2), [2, 1, 3])

    # §2.2 m >= n 时原样返回；m == 1 时退化成 reverseN
    xs4 = [1, 2, 3, 4]
    check("§2.2 m == n 原样返回",
          to_list_capped(ns["reverseBetween"](build(xs4), 2, 2), 8), xs4)
    check("§2.2 m > n 原样返回",
          to_list_capped(ns["reverseBetween"](build(xs4), 3, 2), 8), xs4)
    check("§2.2 m == 1 时等于 reverseN",
          to_list_capped(ns["reverseBetween"](build(xs4), 1, 3), 8),
          to_list_capped(ns["reverseN"](build(xs4), 3), 8))

    # §2.3 「两两交换是 K 个一组的特例」：reverseKGroup(head, 2) 就是两两交换
    for xs in ([], [1], [1, 2], [1, 2, 3], [1, 2, 3, 4, 5], [7, 7, 7, 7]):
        want = []
        for i in range(0, len(xs), 2):
            pair = xs[i:i + 2]
            want += pair[::-1] if len(pair) == 2 else pair
        check(f"§2.3 两两交换 == reverseKGroup(2) on {xs}",
              to_list_capped(ns["reverseKGroup"](build(xs), 2), 16), want)

    # §2.3 反过来：把一个节点当成一组，k=n 就是整体反转
    check("§3 k == 长度时等于整体反转",
          to_list_capped(ns["reverseKGroup"](build([1, 2, 3]), 3), 8),
          oracle_rev([1, 2, 3]))

    # §3 「递归传 head.next 而不是 node 会错」
    ns_buggy = dict(ns)
    src_buggy = (
        "def reverseKGroupBuggy(head, k):\n"
        "    if k <= 1 or head is None:\n"
        "        return head\n"
        "    node = head\n"
        "    for _ in range(k):\n"
        "        if node is None:\n"
        "            return head\n"
        "        node = node.next\n"
        "    new_head = reverseN(head, k)\n"
        "    head.next = reverseKGroupBuggy(head.next, k)\n"
        "    return new_head\n"
    )
    exec(compile(src_buggy, "<buggy>", "exec"), ns_buggy)          # noqa: S102
    kdiff = []
    for xs, p in f1:
        k = p["k"]
        if k <= 1 or not xs:
            continue
        bad = to_list_capped(ns_buggy["reverseKGroupBuggy"](build(xs), k), 64)
        good = to_list_capped(ns["reverseKGroup"](build(xs), k), 64)
        if bad != good:
            kdiff.append((xs, k, bad, good))
    check("§3 实测：把 node 换成 head.next，全部用例结果不变", kdiff, [])
    print(f"     · 把 `reverseKGroup(node, k)` 写成 `reverseKGroup(head.next, k)`："
          f"{len(f1)} 个用例里 {len(kdiff)} 个结果不同")
    print(f"     · 原因：reverseN 最后一行是 seg.next = rest，head 反转后正"
          f"是本组尾巴，它的 next 就等于下一组首个节点（= 提前存下的 node）")

    # §4.2 「比较循环写成 while left and right」：到底会不会不一样？
    diff = []
    seen = []
    for xs, _p in f1:
        want = oracle_pal(xs)
        got_mut = pal_compare_buggy(build(xs))
        seen.append(xs)
        if got_mut != want:
            diff.append((xs, got_mut, want))
    check("§4.2 while left and right 变体在所有用例上都还对", diff, [])
    print(f"     · `while left and right` 变体在 {len(seen)} 个用例上"
          f"与正确版结果相同（不同 {len(diff)} 个）")

    # §4.2 「思路 A 改坏了输入」
    check("§4.2 思路 A 对非回文返回 False",
          ns["isPalindromeList"](build([1, 2, 3, 4])), False)
    for xs6 in ([1, 2, 2, 1], [1, 2, 3, 2, 1]):
        h = build(xs6)
        ok = ns["isPalindromeList"](h)
        mut = to_list_capped(h, 16)
        check(f"§4.2 思路 A 返回值正确 on {xs6}", ok, True)
        check(f"§4.2 思路 A 确实改坏了输入 on {xs6}", mut != xs6, True)
        print(f"     · {xs6} 调用后从原头遍历得到 {mut}（输入被就地改坏）")

    # §5.2 「偶数长度返回靠后的那个中点」
    check("§5.2 [1,2,3,4] 返回 3",
          ns["middleNode"](build([1, 2, 3, 4])).val, 3)
    check("§5.2 [1,2,3] 返回 2",
          ns["middleNode"](build([1, 2, 3])).val, 2)

    # §5.3 「判身份要用 is」：给节点加上按值比较后，== 版判环会变味
    def eq_node(self, other):
        return isinstance(other, ListNode) and self.val == other.val
    ListNode.__eq__ = eq_node
    try:
        head2, nodes2 = build_nodes([1, 2, 1])
        nodes2[-1].next = nodes2[1]                # 环起点是第 2 个节点
        got = ns["detectCycle"](head2)
        check("§5.3 detectCycle 用 is，加了按值的 __eq__ 也不受影响",
              node_index(nodes2, got), 1)
    finally:
        del ListNode.__eq__


# --------------------------------------------------------------------------
# 4b. §6 归纳表「最容易错的那一行」逐条实测
# --------------------------------------------------------------------------
def gate_table_claims(ns: dict, f1) -> None:
    print("\n== §6 归纳表「最容易错的那一行」逐条实测 ==")

    # 206 迭代：`nxt = cur.next` 必须写在 `cur.next = pre` 之前
    def rev_wrong_order(head):
        pre, cur = None, head
        while cur:
            cur.next = pre           # 先改向……
            nxt = cur.next           # ……再备份，备份到的是 pre
            pre, cur = cur, nxt
        return pre
    check("§6 206 迭代：两行颠倒 → 链表被截断",
          to_list_capped(rev_wrong_order(build([1, 2, 3])), 8), [1])
    check("§6 206 迭代：正确顺序 → 完整反转",
          to_list_capped(ns["reverseList"](build([1, 2, 3])), 8), [3, 2, 1])

    # 92：每层要同时减 m 和 n
    def between_only_m(head, m, n):
        if head is None or m >= n:
            return head
        if m == 1:
            return ns["reverseN"](head, n)
        head.next = between_only_m(head.next, m - 1, n)   # 故意：n 没减
        return head
    check("§6 92：只减 m 不减 n → 区间错位",
          to_list_capped(between_only_m(build([1, 2, 3, 4]), 2, 3), 8)
          != to_list_capped(ns["reverseBetween"](build([1, 2, 3, 4]), 2, 3), 8),
          True)

    # 25：数够 k 个必须写在反转之前
    def kgroup_reverse_first(head, k):
        if k <= 1 or head is None:
            return head
        new_head = ns["reverseN"](head, k)      # 故意：先反转
        node = head                             # 再数，此时 head.next 已被改成下一段
        for _ in range(k):
            if node is None:
                return new_head
            node = node.next
        head.next = kgroup_reverse_first(node, k)
        return new_head
    bad = to_list_capped(kgroup_reverse_first(build([1, 2, 3, 4]), 2), 64)
    good = to_list_capped(ns["reverseKGroup"](build([1, 2, 3, 4]), 2), 64)
    check("§6 25：先反转后数 k 个 → 结果不同", bad != good, True)
    print(f"     · [1,2,3,4] k=2：正确 {good}，先反转后数数得到 {bad}")

    # 24：换的是节点还是值？（用节点身份检查）
    head, nodes = build_nodes([1, 2, 3, 4])
    out = ns["reverseKGroup"](head, 2)
    check("§6 24：reverseKGroup(k=2) 换的是节点对象，不是值",
          (out is nodes[1], out.next is nodes[0]), (True, True))

    # 876：循环条件漏掉 fast.next
    def middle_no_check(head):
        slow = fast = head
        while fast:
            slow = slow.next
            fast = fast.next.next       # 故意：没有 fast.next 判断
        return slow
    def run_middle_no_check(xs):
        """返回 ("crash", None) 或 ("ok", 中点值)。"""
        try:
            return "ok", middle_no_check(build(xs)).val
        except AttributeError:
            return "crash", None
    check("§6 876：漏掉 fast.next → 奇数长度（3 个）直接崩",
          run_middle_no_check([1, 2, 3]), ("crash", None))
    check("§6 876：漏掉 fast.next → 奇数长度（5 个）也崩",
          run_middle_no_check([1, 2, 3, 4, 5]), ("crash", None))
    check("§6 876：漏掉 fast.next → 单节点也崩",
          run_middle_no_check([1]), ("crash", None))
    check("§6 876：偶数长度时错法碰巧返回对的中点",
          run_middle_no_check([1, 2, 3, 4]), ("ok", 3))
    check("§6 876：正确写法 → 奇数长度返回中间那个",
          ns["middleNode"](build([1, 2, 3])).val, 2)

    # 141/142：break 之后必须先判 null
    def detect_no_null_check(head):
        slow = fast = head
        while fast and fast.next:
            fast = fast.next.next
            slow = slow.next
            if slow is fast:
                break
        slow = head                     # 故意：少了「走到头」的判空
        while slow is not fast:
            slow = slow.next
            fast = fast.next
        return slow
    crashed = False
    try:
        detect_no_null_check(build([1, 2, 3]))      # 无环
    except AttributeError:
        crashed = True
    check("§6 142：无环时不判 null → 第二段同速走会走出链尾"
          "（Python AttributeError，C++ 是空指针解引用）", crashed, True)
    check("§6 142：正确写法对无环链表返回 None",
          ns["detectCycle"](build([1, 2, 3])), None)
    head_c, nodes_c = build_nodes([1, 2, 3, 4])
    nodes_c[-1].next = nodes_c[2]
    check("§6 142：有环时不判 null 也能找到起点（判空只影响无环的情况）",
          node_index(nodes_c, detect_no_null_check(head_c)), 2)

    # 160：判 p1 == null，而不是 p1.next == null
    def inter_wrong_null_test(ha, hb, cap=200):
        p1, p2, steps = ha, hb, 0
        while p1 is not p2 and steps < cap:
            p1 = hb if p1.next is None else p1.next     # 故意：只看 .next
            p2 = ha if p2.next is None else p2.next
            steps += 1
        return steps
    steps = inter_wrong_null_test(build([1, 2]), build([3]))
    check("§6 160：判 p1.next == null → 两条不相交的链永远走不到一起",
          steps >= 200, True)
    print(f"     · [1,2] 与 [3] 不相交：错法 {steps} 步之后仍在绕圈"
          f"（正确写法走 a+b 步就同时变成 None）")

    # 143：§5.5 说「找中点 + 反转后半 + 交替合并」——用本篇的零件组合一遍
    def reorder143(head, xs):
        L = len(xs)
        if L < 2:
            return head
        mid = ns["middleNode"](head)              # §5.2 的零件
        if L % 2 == 0:
            second = mid                          # 偶数：中点就是后半段开头
            p = head
            for _ in range(L // 2 - 1):
                p = p.next
            p.next = None
        else:
            second = mid.next                     # 奇数：中点是前半段最后一个
            mid.next = None
        second = ns["reverseList"](second)        # §1 的零件
        dummy = ListNode(-1)
        t, a, b = dummy, head, second
        while a and b:                            # 交替合并
            t.next = a
            a = a.next
            t = t.next
            t.next = b
            b = b.next
            t = t.next
        if a:
            t.next = a
        return dummy.next
    bad143 = []
    for xs, _p in f1:
        want, i, j = [], 0, len(xs) - 1
        while i <= j:
            want.append(xs[i])
            if i != j:
                want.append(xs[j])
            i += 1
            j -= 1
        got = to_list_capped(reorder143(build(xs), xs), 64)
        if got != want:
            bad143.append((xs, got, want))
    check("§5.5 143：中点 + 反转 + 交替合并（用本篇零件）与重排参照一致",
          bad143, [])
    print(f"     · 143 重排：{len(f1)} 个用例里 {len(bad143)} 个不符"
          f"（参照是 [L0,Ln,L1,Ln-1,…] 的 list 实现）")


# --------------------------------------------------------------------------
# 5. 门 3：生成 C++、编译（零警告）、跑同一批用例、比摘要
# --------------------------------------------------------------------------
CPP_HARNESS_HEAD = r"""
// ======================= harness =======================
static int checks = 0;
static int failures = 0;
static unsigned long long digest = 1469598103934665603ULL;

static void feed(long long v) {
    digest ^= static_cast<unsigned long long>(v);
    digest *= 1099511628211ULL;
}
static void feedAll(const std::vector<int>& xs) {
    for (int x : xs) feed(x);
}
static std::string join(const std::vector<int>& xs) {
    std::string s = "[";
    for (size_t i = 0; i < xs.size(); ++i) {
        if (i) s += ", ";
        s += std::to_string(xs[i]);
    }
    return s + "]";
}
static ListNode* build(const std::vector<int>& xs) {
    ListNode* head = nullptr;
    for (int i = static_cast<int>(xs.size()) - 1; i >= 0; --i) {
        ListNode* n = new ListNode(xs[i]);
        n->next = head;
        head = n;
    }
    return head;
}
static ListNode* prepend(const std::vector<int>& xs, ListNode* tail) {
    ListNode* head = tail;
    for (int i = static_cast<int>(xs.size()) - 1; i >= 0; --i) {
        ListNode* n = new ListNode(xs[i]);
        n->next = head;
        head = n;
    }
    return head;
}
static ListNode* buildCyclic(const std::vector<int>& xs, int entry,
                            std::vector<ListNode*>& nodes) {
    ListNode* head = nullptr;
    for (int i = static_cast<int>(xs.size()) - 1; i >= 0; --i) {
        ListNode* n = new ListNode(xs[i]);
        n->next = head;
        head = n;
        nodes.insert(nodes.begin(), n);
    }
    if (entry >= 0 && !nodes.empty()) nodes.back()->next = nodes[entry];
    return head;
}
static int indexOf(const std::vector<ListNode*>& nodes, ListNode* p) {
    for (size_t i = 0; i < nodes.size(); ++i) if (nodes[i] == p) return static_cast<int>(i);
    return -1;
}
static bool hasCycle(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast != nullptr && fast->next != nullptr) {
        slow = slow->next;
        fast = fast->next->next;
        if (slow == fast) return true;
    }
    return false;
}
static std::vector<int> toVecCapped(ListNode* head, int cap) {
    std::vector<int> out;
    while (head != nullptr && static_cast<int>(out.size()) <= cap) {
        out.push_back(head->val);
        head = head->next;
    }
    return out;
}
static void expectLong(const std::string& label, long long got, long long want) {
    ++checks;
    feed(got);
    if (got != want) {
        ++failures;
        if (failures <= 20) std::cout << "  !! " << label << ": got " << got << " want " << want << "\n";
    }
}
static void expectVec(const std::string& label, ListNode* gotNode,
                      const std::vector<int>& want) {
    ++checks;
    feed(static_cast<long long>(want.size()));
    if (gotNode != nullptr && hasCycle(gotNode)) {
        ++failures;
        if (failures <= 20) std::cout << "  !! " << label << ": 结果成环\n";
        return;
    }
    std::vector<int> got = toVecCapped(gotNode, static_cast<int>(want.size()) + 8);
    feedAll(got);
    if (got != want) {
        ++failures;
        if (failures <= 20) std::cout << "  !! " << label << ": got " << join(got) << " want " << join(want) << "\n";
    }
}
"""


def cpp_vec(xs) -> str:
    return "{" + ", ".join(str(int(v)) for v in xs) + "}"


def gen_cpp(cpp_blocks: list[str], f1, f2, f3) -> str:
    out: list[str] = []
    out.append("// 由 verify_code.py 生成：正文的 11 个 cpp 块 + struct ListNode + harness")
    out.append("#include <algorithm>")
    out.append("#include <cstdint>")
    out.append("#include <iostream>")
    out.append("#include <string>")
    out.append("#include <vector>")
    out.append("")
    out.append("struct ListNode {")
    out.append("    int val;")
    out.append("    ListNode* next;")
    out.append("    explicit ListNode(int v) : val(v), next(nullptr) {}")
    out.append("};")
    out.append("")
    out.append("// ------------------- 正文的 cpp 代码块（原样） -------------------")
    for i, body in enumerate(cpp_blocks):
        out.append(f"// ---- 块 #{i} ----")
        out.append(body.rstrip("\n"))
        out.append("")
    out.append(CPP_HARNESS_HEAD.strip("\n"))
    out.append("")
    out.append("int main() {")

    # F1
    out.append("    // ---- F1：与 list 参照实现同一批用例 ----")
    for i, (xs, p) in enumerate(f1):
        out.append(f"    {{  // F1#{i}  xs={xs} n1={p['n1']} m={p['m']} "
                   f"n={p['n']} k={p['k']} n2={p['n2']}")
        out.append(f"        std::vector<int> xs{cpp_vec(xs)};")
        for name, kind, _call, expr, want in F1_OPS:
            call = expr.format(**p)
            expected = want(xs, p)
            if kind == "vec":
                out.append(f'        expectVec("F1#{i} {name}", {call}, '
                           f'{cpp_vec(expected)});')
            else:
                out.append(f'        expectLong("F1#{i} {name}", {call}, '
                           f'{int(expected)});')
        out.append("    }")

    # F2
    out.append("    // ---- F2：环形检测（与「哈希集合记录访问过的节点」比） ----")
    for i, (xs, entry) in enumerate(f2):
        out.append(f"    {{  // F2#{i}  xs={xs} entry={entry}")
        out.append(f"        std::vector<int> xs{cpp_vec(xs)};")
        out.append("        std::vector<ListNode*> nodes;")
        out.append(f"        ListNode* h = buildCyclic(xs, {entry}, nodes);")
        want = entry if entry >= 0 else -1
        out.append(f'        expectLong("F2#{i} detectCycle", '
                   f'indexOf(nodes, detectCycle(h)), {want});')
        out.append("    }")

    # §2.1 n = 0：正文说「C++ 版是同一份逻辑，所以同样成环」。
    # 这句话必须自己跑一遍才算数——两边是分别重写的，不是同一份源码。
    #
    # 这一段**故意不用 expectLong / expectVec**：那两个会 feed 跨语言摘要，
    # 而摘要的适用范围是 F1/F2/F3 那一批（Python 侧在 gate_python 之后冻结）。
    # 这里用不 feed 的裸检查，摘要就仍然只覆盖两边共有的那批用例。
    out.append("    // ---- §2.1 n=0 下界：C++ 侧也必须成环（不 feed 摘要） ----")
    out.append("    {")
    out.append("        std::vector<int> xs{1, 2, 3};")
    out.append("        auto rawCheck = [](const char* what, bool ok) {")
    out.append("            ++checks;")
    out.append("            if (!ok) { ++failures;")
    out.append("                if (failures <= 20) std::cout << \"  !! \" << what << \"\\n\"; }")
    out.append("        };")
    out.append("        ListNode* z = reverseN(build(xs), 0);")
    out.append("        rawCheck(\"§2.1 cpp n=0 成环\", hasCycle(z));")
    out.append("        ListNode* o1 = reverseN(build(xs), 1);")
    out.append("        rawCheck(\"§2.1 cpp n=1 不成环\", !hasCycle(o1));")
    out.append("        rawCheck(\"§2.1 cpp n=1 结果正确\", "
               "toVecCapped(o1, 8) == std::vector<int>{1, 2, 3});")
    out.append("        ListNode* o2 = reverseN(build(xs), 2);")
    out.append("        rawCheck(\"§2.1 cpp n=2 结果正确\", "
               "toVecCapped(o2, 8) == std::vector<int>{2, 1, 3});")
    out.append("    }")

    # F3
    out.append("    // ---- F3：相交链表（比节点身份） ----")
    for i, (a, b, c) in enumerate(f3):
        out.append(f"    {{  // F3#{i}  a={a} b={b} common={c}")
        out.append(f"        std::vector<int> a{cpp_vec(a)}, b{cpp_vec(b)}, "
                   f"c{cpp_vec(c)};")
        out.append("        ListNode* tail = c.empty() ? nullptr : build(c);")
        out.append("        ListNode* ha = prepend(a, tail);")
        out.append("        ListNode* hb = prepend(b, tail);")
        expect_ptr = "nullptr" if not c else "tail"
        out.append('        expectLong("F3#%d getIntersectionNode", '
                   'getIntersectionNode(ha, hb) == %s ? 1 : 0, 1);'
                   % (i, expect_ptr))
        out.append("    }")

    out.append('    std::cout << "cpp checks: " << checks << ", failures: " '
               '<< failures << "\\n";')
    out.append('    std::cout << "cpp digest: " << digest << "\\n";')
    out.append('    if (failures == 0) std::cout << "CPP GATE OK, digest " '
               '<< digest << "\\n";')
    out.append("    return failures == 0 ? 0 : 1;")
    out.append("}")
    return "\n".join(out) + "\n"


def gate_cpp(cpp_blocks: list[str], py_digest: int, f1, f2, f3) -> None:
    print("\n== 门 3：C++ 侧生成 + 编译 + 跑同一批用例 ==")
    src = gen_cpp(cpp_blocks, f1, f2, f3)
    GEN_CPP.write_text(src, encoding="utf-8")
    print(f"  写了 {GEN_CPP.relative_to(ROOT)}（{len(src.splitlines())} 行）")
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1", "-o",
           str(GEN_BIN), str(GEN_CPP)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = (proc.stderr or "").strip()
    print(f"  g++ exit={proc.returncode}, 警告/错误: "
          f"{'无' if not stderr else repr(stderr[:400])}")
    check("g++ 编译通过", proc.returncode, 0)
    check("g++ 零警告（-Werror）", stderr, "")
    if proc.returncode != 0:
        return
    run = subprocess.run([str(GEN_BIN)], capture_output=True, text=True)
    for line in run.stdout.strip().splitlines():
        print(f"  | {line}")
    check("C++ harness 退出码", run.returncode, 0)
    check("C++ harness 没有写 stderr", run.stderr.strip(), "")
    m = re.search(r"cpp digest: (\d+)", run.stdout)
    cpp_digest = int(m.group(1)) if m else None
    check("两个语言的摘要一致（同一批用例、同样的结果）", cpp_digest, py_digest)


# --------------------------------------------------------------------------
def main() -> int:
    print("== 链式反转代码门 ==")
    py_blocks, cpp_blocks = gate_extract()
    if failures:
        print("\n== 结果 ==")
        for f in failures:
            print(f"  !! {f}")
        print("CODE FAIL：抽取阶段就出错了，先修这个")
        return 1
    f1, f2, f3 = make_f1_cases(), make_f2_cases(), make_f3_cases()
    ns = gate_python(py_blocks, f1, f2, f3)
    # 跨语言摘要的适用范围就是 gate_python 跑的那一批（F1/F2/F3）：
    # C++ 侧生成出来的 main 也只长这样。所以摘要在 gate_python 之后立刻冻结，
    # 后面 gate_prose_claims 里的断言（它们同样会 feed）不参与比较 —— 那些是
    # Python 侧的正文核查，C++ 侧没有对应物，混进来只会让两边对不上。
    # 与之配套：gen_cpp 里任何新增的 expect 调用都必须在两侧同时加，
    # 否则摘要会红，这是好事 —— 它正好提醒你「C++ 侧多跑了一批东西」。
    py_digest = digest
    gate_prose_claims(ns, f1)
    gate_table_claims(ns, f1)
    gate_cpp(cpp_blocks, py_digest, f1, f2, f3)

    print("\n== 结果 ==")
    for f in failures:
        print(f"  !! {f}")
    print(f"  python checks: {checks}, failures: {len(failures)}")
    print(f"  python digest: {py_digest}")
    if failures:
        print("CODE FAIL")
        return 1
    print("CODE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
