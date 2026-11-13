#!/usr/bin/env python3
"""Code gate for _posts/2026-11-16-hash-and-heap.md.

The point of this file is that it never trusts a copy of the article's code.
It reads the post, pulls the fenced ```python and ```cpp blocks straight out of
the body, and runs *those*:

  * every ```python block is exec'd, then driven against an independent
    reference implementation (a plain dict / a brute-force O(n) scan / a
    sorted list) over randomised operation sequences and the boundary cases
    the prose calls out -- empty, single element, all equal, duplicate key,
    out of range;
  * the ```cpp blocks are concatenated in front of cpp_structures_test.cpp,
    compiled with

        g++ -std=c++17 -Wall -Wextra -Werror

    so a single warning fails the gate, and then executed.  The C++ harness
    runs the same cross-checks as the Python one.

If a section of the article is edited, this gate either follows it or fails.
Run it from anywhere:

    python3 assets/blog/hash-and-heap-20261116/verify_code.py
"""

from __future__ import annotations

import bisect
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
POST = os.path.join(REPO, "_posts", "2026-11-16-hash-and-heap.md")
HARNESS = os.path.join(HERE, "cpp_structures_test.cpp")

EXPECTED_PY_BLOCKS = 11
EXPECTED_CPP_BLOCKS = 11

FAILURES: list[str] = []
MEASURED: list[str] = []


# --------------------------------------------------------------- reporting
def section(title: str) -> None:
    print(f"\n== {title}")


def check(label: str, ok: bool) -> None:
    if ok:
        print(f"   ok   {label}")
    else:
        print(f"   FAIL {label}")
        FAILURES.append(label)


def check_eq(label: str, got, want) -> None:
    if got == want:
        print(f"   ok   {label}")
    else:
        print(f"   FAIL {label}: got {got!r}, want {want!r}")
        FAILURES.append(f"{label} (got {got!r}, want {want!r})")


def measure(label: str, value: str) -> None:
    line = f"{label}: {value}"
    MEASURED.append(line)
    print(f"   ->   {line}")


# ------------------------------------------------------------ block loader
def load_blocks(text: str, lang: str) -> list[str]:
    """Every fenced ```lang block in the article, in order."""
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def mixed_fnv(s: str) -> int:
    """The same hash ConsistentHash uses (FNV-1a + murmur3 finalizer).  Its own
    hash_of is a staticmethod we could call, but 2.4's get_node is what we
    actually want to test -- this copy only exists for the modulo contrast."""
    h = 1469598103934665603
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 1099511628211) % (1 << 64)
    h ^= h >> 33
    h = (h * 0xff51afd7ed558ccd) % (1 << 64)
    h ^= h >> 33
    h = (h * 0xc4ceb9fe1a85ec53) % (1 << 64)
    h ^= h >> 33
    return h


def distinct_keys(rnd: random.Random, n: int) -> list[str]:
    """Distinct keys: 1.3/1.4 delete in strides, and a repeated key would make
    the second remove() correctly return False and look like a bug."""
    return [f"key-{rnd.randrange(1000000)}-{i}" for i in range(n)]


# ================================================================== PYTHON
def python_checks(ns: dict, rnd: random.Random) -> None:
    ChainingHashMap = ns["ChainingHashMap"]
    LinearProbingMap = ns["LinearProbingMap"]
    ArrayHashMap = ns["ArrayHashMap"]
    ConsistentHash = ns["ConsistentHash"]
    MinPQ = ns["MinPQ"]
    sink_in_place = ns["sink_in_place"]
    build_heap_floyd = ns["build_heap_floyd"]
    build_heap_by_swim = ns["build_heap_by_swim"]
    heap_sort = ns["heap_sort"]
    TrieMap = ns["TrieMap"]
    SegTree = ns["SegTree"]
    LazySegTree = ns["LazySegTree"]
    Fenwick = ns["Fenwick"]
    SkipList = ns["SkipList"]

    # ------------------------------------------------ 1.3 chaining
    section("1.3 ChainingHashMap vs dict")
    m, ref = ChainingHashMap(), {}
    keys = distinct_keys(rnd, 4000)
    for i, k in enumerate(keys):
        m.put(k, i % 977)
        ref[k] = i % 977
    check_eq("size matches dict", m.size, len(ref))
    check("every key reads back", all(m.get(k) == ref[k] for k in keys))
    before = m.size
    m.put(keys[0], 12345)
    check_eq("duplicate key does not grow the table", m.size, before)
    check_eq("duplicate key overwrites the value", m.get(keys[0]), 12345)
    check_eq("missing key returns None", m.get("no-such-key"), None)
    for k in keys[::3]:
        m.remove(k)
        del ref[k]
    check_eq("size after removals", m.size, len(ref))
    check("survivors all correct",
          all((m.get(k) is None) == (k not in ref) and
              (k not in ref or m.get(k) == ref[k]) for k in keys))
    check_eq("removing twice returns False", m.remove(keys[0]), False)

    empty = ChainingHashMap()
    check_eq("empty: size 0", empty.size, 0)
    check_eq("empty: get returns None", empty.get("x"), None)
    check_eq("empty: remove returns False", empty.remove("x"), False)
    one = ChainingHashMap()
    one.put("only", 7)
    check_eq("single element: get", one.get("only"), 7)
    check("single element: remove", one.remove("only"))
    check_eq("single element: size back to 0", one.size, 0)
    flat = ChainingHashMap()
    for i in range(500):
        flat.put(f"k{i}", 42)
    check("all values equal stays consistent",
          all(flat.get(f"k{i}") == 42 for i in range(500)))

    # ------------------------------------------------ 1.4 linear probing
    section("1.4 LinearProbingMap vs dict (tombstones)")
    m, ref = LinearProbingMap(), {}
    keys = distinct_keys(rnd, 4000)
    for i, k in enumerate(keys):
        m.put(k, i % 991)
        ref[k] = i % 991
    check_eq("size matches dict", m.size, len(ref))
    check("every key reads back", all(m.get(k) == ref[k] for k in keys))
    before = m.size
    m.put(keys[0], -1)
    check_eq("duplicate key does not grow the table", m.size, before)
    half = len(keys) // 2
    for k in keys[:half]:
        m.remove(k)
        del ref[k]
    check_eq("size after removals", m.size, len(ref))
    check("keys behind a tombstone are still reachable",
          all((m.get(k) is None) == (k not in ref) and
              (k not in ref or m.get(k) == ref[k]) for k in keys))
    for i, k in enumerate(keys[:half]):
        m.put(k, i)
        ref[k] = i
    check_eq("size after reinserting over the tombstones", m.size, len(ref))
    check("state after churn", all(m.get(k) == ref[k] for k in keys))

    empty = LinearProbingMap()
    check_eq("empty: get returns None", empty.get("x"), None)
    check_eq("empty: remove returns False", empty.remove("x"), False)
    one = LinearProbingMap()
    one.put("only", 5)
    check_eq("single element: get", one.get("only"), 5)
    check("single element: remove", one.remove("only"))
    check_eq("single element: get after remove", one.get("only"), None)

    # ------------------------------------------------ 2.3 array hash map
    section("2.3 ArrayHashMap: O(1) randomKey")
    m, ref = ArrayHashMap(), {}
    keys = distinct_keys(rnd, 2000)
    for i, k in enumerate(keys):
        m.put(k, i)
        ref[k] = i
    check_eq("len matches dict", len(m), len(ref))
    check("every key reads back", all(m.get(k) == ref[k] for k in keys))
    random.seed(20261116)
    seen = {}
    bad = False
    for _ in range(40000):
        k = m.random_key()
        if k not in ref:
            bad = True
            break
        seen[k] = seen.get(k, 0) + 1
    check("random_key never returns an absent key", not bad)
    check_eq("random_key reaches every key", len(seen), len(ref))
    for k in keys[::2]:
        m.remove(k)
        del ref[k]
    check_eq("len after swap-fill removals", len(m), len(ref))
    check("swap-fill keeps the index correct",
          all((m.get(k) is None) == (k not in ref) and
              (k not in ref or m.get(k) == ref[k]) for k in keys))
    empty = ArrayHashMap()
    check_eq("empty: get returns None", empty.get("x"), None)
    check_eq("empty: remove returns False", empty.remove("x"), False)
    check_eq("empty: len is 0", len(empty), 0)
    one = ArrayHashMap()
    one.put("only", 3)
    check("single element: remove (pos == last, no swap)", one.remove("only"))
    check_eq("single element: len is 0", len(one), 0)
    dup = ArrayHashMap()
    dup.put("a", 1)
    dup.put("a", 2)
    check_eq("duplicate key updates in place", (len(dup), dup.get("a")), (1, 2))

    # ------------------------------------------------ 2.4 consistent hash
    section("2.4 ConsistentHash ring")
    ring = ConsistentHash(200)
    check_eq("empty ring returns None", ring.get_node("anything"), None)
    nodes = ["node-A", "node-B", "node-C"]
    for n in nodes:
        ring.add_node(n)
    check_eq("ring holds N*V virtual nodes", len(ring.ring_keys), len(nodes) * 200)
    keys = [f"user-{i}" for i in range(10000)]
    before = [ring.get_node(k) for k in keys]
    check("no key maps to None", all(x is not None for x in before))
    dist = {n: before.count(n) for n in nodes}
    check_eq("all three nodes are used", len([v for v in dist.values() if v]), 3)
    check(f"each node owns roughly a third (got {dist})",
          all(2800 <= v <= 3900 for v in dist.values()))
    check("the mapping is deterministic",
          all(ring.get_node(k) == before[i] for i, k in enumerate(keys)))
    ring.add_node("node-D")
    check_eq("ring after adding a node", len(ring.ring_keys), 4 * 200)
    moved = sum(1 for i, k in enumerate(keys) if ring.get_node(k) != before[i])
    ring.remove_node("node-D")
    check_eq("removing the node restores the ring size", len(ring.ring_keys), 3 * 200)
    check_eq("removing the node restores the mapping exactly",
             sum(1 for i, k in enumerate(keys) if ring.get_node(k) == before[i]),
             len(keys))
    nodes4 = nodes + ["node-D"]
    mod_moved = sum(1 for k in keys if nodes[mixed_fnv(k) % 3] !=
                    nodes4[mixed_fnv(k) % 4])
    measure("consistent hash, 10000 keys, 3 nodes x 200 vnodes",
            " / ".join(str(dist[n]) for n in nodes))
    measure("consistent hash, add a 4th node",
            f"{moved} keys move ({moved * 100.0 / len(keys):.2f}%)")
    measure("plain modulo, 3 nodes -> 4 nodes",
            f"{mod_moved} keys move ({mod_moved * 100.0 / len(keys):.2f}%)")
    check("adding one node moves about a quarter, not three quarters",
          0 < moved < mod_moved / 2)
    check("modulo really does move about 3/4", mod_moved > 6 * len(keys) // 10)

    # ------------------------------------------------ 3.2 MinPQ
    section("3.2 MinPQ vs sorted list")
    pq = MinPQ()
    ref = []
    for _ in range(5000):
        v = rnd.randrange(-1000, 1001)
        pq.push(v)
        bisect.insort(ref, v)
    check_eq("size", len(pq), len(ref))
    check_eq("top is the minimum", pq.top(), ref[0])
    order_ok = True
    while ref:
        if pq.top() != ref[0] or pq.pop() != ref[0]:
            order_ok = False
            break
        ref.pop(0)
    check("pops come out in sorted order", order_ok)
    check_eq("empty after draining", len(pq), 0)
    one = MinPQ()
    one.push(7)
    check_eq("single element: top", one.top(), 7)
    check_eq("single element: pop", one.pop(), 7)
    check_eq("single element: empty", len(one), 0)
    flat = MinPQ()
    for _ in range(200):
        flat.push(5)
    check("all equal pops 5 every time", [flat.pop() for _ in range(200)] == [5] * 200)
    desc = MinPQ()
    for i in range(100, 0, -1):
        desc.push(i)
    check("descending insertion still pops ascending",
          [desc.pop() for _ in range(100)] == list(range(1, 101)))
    asc = MinPQ()
    for i in range(1, 101):
        asc.push(i)
    check("ascending insertion still pops ascending",
          [asc.pop() for _ in range(100)] == list(range(1, 101)))

    # ------------------------------------------------ 3.4 heap sort
    section("3.4 in-place heap build and heap sort")
    cases = [
        ("empty", []),
        ("single", [1]),
        ("two swapped", [2, 1]),
        ("all equal", [7] * 50),
        ("all negative", [-5, -3, -9, -1, -7]),
        ("already sorted", list(range(1, 9))),
        ("reverse sorted", list(range(8, 0, -1))),
    ]
    for _ in range(60):
        cases.append(("random",
                      [rnd.randrange(-10, 11) for _ in range(rnd.randrange(0, 40))]))
    ok = True
    for name, a in cases:
        arr = list(a)
        heap_sort(arr)                 # sorts in place, returns the comparison count
        if arr != sorted(a):
            ok = False
            print(f"        heap_sort disagrees on {name}: {a} -> {arr}")
    check("heap_sort matches sorted() on every shape", ok)

    heap_ok = True
    for _ in range(60):
        a = [rnd.randrange(51) for _ in range(rnd.randrange(1, 40))]
        build_heap_floyd(a)
        if any(a[(i - 1) // 2] < a[i] for i in range(1, len(a))):
            heap_ok = False
    check("build_heap_floyd leaves a valid max-heap", heap_ok)

    bound_ok, beats = True, True
    for _ in range(30):
        a = [rnd.randrange(100000) for _ in range(rnd.randrange(1, 2000))]
        cf = build_heap_floyd(list(a))
        cs = build_heap_by_swim(list(a))
        if cf > 2 * len(a):
            bound_ok = False
        if cs <= cf:
            beats = False
    check("Floyd build stays under 2n comparisons", bound_ok)
    check("swim build always costs more than Floyd", beats)

    print("   .. measuring the n = 2^20 build (this takes a few seconds)")
    big = [rnd.randrange(1000000) for _ in range(1 << 20)]
    floyd = build_heap_floyd(list(big))
    swim = build_heap_by_swim(list(big))
    measure("Floyd build, n = 2^20 (python)",
            f"{floyd} comparisons ({floyd / (1 << 20):.4f}n)")
    measure("swim build, n = 2^20 (python)",
            f"{swim} comparisons ({swim / (1 << 20):.4f}n)")
    check("Floyd build is linear in n", floyd < 2 * (1 << 20))
    check("swim build is more expensive", swim > floyd)
    small = [rnd.randrange(100000) for _ in range(1 << 16)]
    heap_sort(small)
    check("heap_sort on 2^16 matches sorted()", small == sorted(small))

    # ------------------------------------------------ 4.2 TrieMap
    section("4.2 TrieMap vs a dict of dicts")
    trie = TrieMap()
    words = ["that", "the", "them", "apple"]
    for w in words:
        trie.insert(w)
    check("search finds every inserted word", all(trie.search(w) for w in words))
    check_eq('search("th") is False, "th" is a path and not a key', trie.search("th"), False)
    check_eq('startsWith("th") is True', trie.starts_with("th"), True)
    check_eq('startsWith("tha") is True', trie.starts_with("tha"), True)
    check_eq('startsWith("thz") is False', trie.starts_with("thz"), False)
    check_eq('search("thz") is False', trie.search("thz"), False)
    check_eq('search("app") is False', trie.search("app"), False)
    check_eq('startsWith("app") is True', trie.starts_with("app"), True)
    check_eq('search("applex") is False', trie.search("applex"), False)
    check_eq('startsWith("z") is False', trie.starts_with("z"), False)
    trie.insert("the")
    check("duplicate insert is idempotent", trie.search("the"))
    check_eq("keys_with_prefix('th') is the sorted key list",
             sorted(trie.keys_with_prefix("th")), ["that", "the", "them"])
    trie.insert("")
    check_eq("the empty string is a legal key", trie.search(""), True)
    check_eq("startsWith('') is True", trie.starts_with(""), True)
    trie.insert("a")
    check_eq("single character key", trie.search("a"), True)

    big = TrieMap()
    ref = set()
    for _ in range(2000):
        w = "".join(rnd.choice("abc") for _ in range(rnd.randrange(1, 9)))
        big.insert(w)
        ref.add(w)
    ok = True
    for _ in range(3000):
        w = "".join(rnd.choice("abcd") for _ in range(rnd.randrange(0, 6)))
        if big.search(w) != (w in ref):
            ok = False
        want = any(k.startswith(w) for k in ref)
        if big.starts_with(w) != want:
            ok = False
    check("search/startsWith agree with a set reference over 5000 probes", ok)

    # ------------------------------------------------ 5.1 segment tree
    section("5.1 SegTree vs brute force (sum and max)")
    add = lambda a, b: a + b                       # noqa: E731
    maxf = max
    neg_inf = float("-inf")

    SegTree([], add, 0)                            # empty: must not raise
    check("empty array can be built", True)
    t1 = SegTree([42], add, 0)
    check_eq("single element: query", t1.query(0, 0), 42)
    t1.update(0, -42)
    check_eq("single element: after update", t1.query(0, 0), -42)
    flat = SegTree([6] * 64, add, 0)
    check_eq("all equal: full range", flat.query(0, 63), 64 * 6)
    check_eq("all equal: partial range", flat.query(10, 20), 11 * 6)
    neg = [-5, -3, -9, -1, -7]
    check_eq("all negative max: full range", SegTree(neg, maxf, neg_inf).query(0, 4), -1)
    check_eq("all negative max: partial range", SegTree(neg, maxf, neg_inf).query(1, 2), -3)
    check_eq("all negative sum: full range", SegTree(neg, add, 0).query(0, 4), -25)

    sum_ok = max_ok = upd_ok = True
    for _ in range(40):
        n = rnd.randrange(1, 40)
        a = [rnd.randrange(-100, 101) for _ in range(n)]
        st = SegTree(a, add, 0)
        mt = SegTree(a, maxf, neg_inf)
        for l in range(n):
            for r in range(l, n):
                if st.query(l, r) != sum(a[l:r + 1]):
                    sum_ok = False
                if mt.query(l, r) != max(a[l:r + 1]):
                    max_ok = False
        for _ in range(20):
            i = rnd.randrange(n)
            a[i] = rnd.randrange(-100, 101)
            st.update(i, a[i])
            mt.update(i, a[i])
            for l in range(n):
                for r in range(l, n):
                    if st.query(l, r) != sum(a[l:r + 1]):
                        upd_ok = False
                    if mt.query(l, r) != max(a[l:r + 1]):
                        upd_ok = False
    check("sum tree matches brute force on every (l, r)", sum_ok)
    check("max tree matches brute force on every (l, r)", max_ok)
    check("both trees stay correct across point updates", upd_ok)

    # ------------------------------------------------ 5.2 lazy segment tree
    section("5.2 LazySegTree vs brute force")
    t = LazySegTree([5])
    check_eq("single element: range_sum", t.range_sum(0, 0), 5)
    t.range_add(0, 0, -3)
    check_eq("single element: after range_add", t.range_sum(0, 0), 2)
    t = LazySegTree([4] * 32)
    t.range_add(0, 31, 6)
    check_eq("all equal: full range after +6", t.range_sum(0, 31), 32 * 10)
    check_eq("all equal: partial range after +6", t.range_sum(7, 9), 3 * 10)
    t.range_add(0, 31, -10)
    check_eq("full range after -10 is all zeros", t.range_sum(0, 31), 0)
    t.range_add(0, 31, 4)
    check_eq("full range back to 4 each", t.range_sum(0, 31), 32 * 4)

    n = 64
    a = [0] * n
    t = LazySegTree(list(a))
    lazy_ok = True
    for rnd_i in range(300):
        l = rnd.randrange(n)
        r = rnd.randrange(l, n)
        d = rnd.randrange(-20, 21)
        t.range_add(l, r, d)
        for i in range(l, r + 1):
            a[i] += d
        if rnd_i % 7 == 0:
            ql = rnd.randrange(n)
            qr = rnd.randrange(ql, n)
            if t.range_sum(ql, qr) != sum(a[ql:qr + 1]):
                lazy_ok = False
    check("interleaved range_add / range_sum matches brute force", lazy_ok)
    check("every (l, r) is correct at the end",
          all(t.range_sum(l, r) == sum(a[l:r + 1])
              for l in range(n) for r in range(l, n)))

    # ------------------------------------------------ 5.3 Fenwick
    section("5.3 Fenwick vs brute force")
    f = Fenwick(1)
    check_eq("single element: prefix_sum on a fresh tree", f.prefix_sum(1), 0)
    f.add(1, 9)
    check_eq("single element: prefix_sum", f.prefix_sum(1), 9)
    check_eq("single element: range_sum", f.range_sum(1, 1), 9)
    f.add(1, -9)
    check_eq("single element: back to zero", f.prefix_sum(1), 0)

    prefix_ok = range_ok = True
    for n in range(1, 41):
        a = [0] * (n + 1)
        f = Fenwick(n)
        for _ in range(60):
            i = rnd.randrange(1, n + 1)
            d = rnd.randrange(-20, 21)
            a[i] += d
            f.add(i, d)
            for k in range(1, n + 1):
                if f.prefix_sum(k) != sum(a[1:k + 1]):
                    prefix_ok = False
                    break
            for l in range(1, n + 1):
                for r in range(l, n + 1):
                    if f.range_sum(l, r) != sum(a[l:r + 1]):
                        range_ok = False
    check("prefix_sum matches brute force for every n, i", prefix_ok)
    check("range_sum matches brute force for every (l, r)", range_ok)

    f = Fenwick(16)
    for i in range(1, 17):
        f.add(i, 3)
    check_eq("all equal: prefix_sum(n)", f.prefix_sum(16), 48)
    check_eq("all equal: range_sum(1, n)", f.range_sum(1, 16), 48)
    for i in range(1, 17):
        f.add(i, -5)
    check_eq("all negative: prefix_sum(n)", f.prefix_sum(16), -32)
    check_eq("all negative: single element", f.range_sum(4, 4), -2)
    for i in range(1, 17):
        f.add(i, 2)
    check_eq("back to all zeros", f.prefix_sum(16), 0)

    check_eq("lowbit(0)", Fenwick.lowbit(0), 0)
    check_eq("lowbit(1)", Fenwick.lowbit(1), 1)
    check_eq("lowbit(6)", Fenwick.lowbit(6), 2)
    check_eq("lowbit(12)", Fenwick.lowbit(12), 4)
    check_eq("lowbit(1024)", Fenwick.lowbit(1024), 1024)
    check("lowbit agrees with i & -i for every i up to 4096",
          all(Fenwick.lowbit(i) == (i & -i) and
              Fenwick.lowbit(i) <= i and i % Fenwick.lowbit(i) == 0
              for i in range(1, 4097)))

    n = 1024
    max_prefix = max(sum(1 for _ in iter_steps(i, n, "prefix")) for i in range(1, n + 1))
    max_add = max(sum(1 for _ in iter_steps(i, n, "add")) for i in range(1, n + 1))
    measure("Fenwick, n = 1024",
            f"max prefix_sum hops = {max_prefix}, max add hops = {max_add}, "
            f"log2(n) = 10")
    check_eq("max prefix_sum hops is popcount(1023)", max_prefix, 10)
    check_eq("max add hops is 1,2,4,...,1024", max_add, 11)

    # ------------------------------------------------ 6.1 skip list
    section("6.1 SkipList vs a dict plus a sorted list")
    sl = SkipList()
    check_eq("empty: size", sl.size, 0)
    check_eq("empty: contains", sl.contains(1), False)
    check_eq("empty: erase", sl.erase(1), False)
    sl.insert(1)
    check("single element: contains", sl.contains(1))
    check("single element: erase", sl.erase(1))
    check_eq("single element: size back to 0", sl.size, 0)

    sl = SkipList()
    for _ in range(200):
        sl.insert(7)
    check_eq("all equal: duplicates are refused", sl.size, 1)
    check_eq("all equal: value is present", sl.contains(7), True)
    check("all equal: erase", sl.erase(7))
    check_eq("all equal: size back to 0", sl.size, 0)

    sl = SkipList()
    ref = {}
    ordered = []
    agree = True
    for _ in range(20000):
        v = rnd.randrange(3000)
        op = rnd.randrange(3)
        if op == 0:
            sl.insert(v)
            if v not in ref:
                ref[v] = True
                bisect.insort(ordered, v)
        elif op == 1:
            if sl.contains(v) != (v in ref):
                agree = False
        else:
            pos = bisect.bisect_left(ordered, v)
            want = pos < len(ordered) and ordered[pos] == v
            if sl.erase(v) != want:
                agree = False
            if want:
                ordered.pop(pos)
                del ref[v]
    check("insert/contains/erase agree with a dict + sorted list", agree)
    check_eq("size matches the reference", sl.size, len(ref))
    check("every value 0..2999 agrees",
          all(sl.contains(v) == (v in ref) for v in range(3000)))
    for v in list(ordered):
        sl.erase(v)
    check_eq("erasing everything empties the list", sl.size, 0)
    check_eq("and the level falls back to 1", sl.level, 1)

    sl = SkipList()
    ref = set()
    insert_steps = 0
    for _ in range(65536):
        v = rnd.randrange(10000000)
        sl.insert(v)
        ref.add(v)
        insert_steps += sl.steps
    lookup_steps = 0
    hits = 0
    for _ in range(20000):
        v = rnd.randrange(10000000)
        if sl.contains(v):
            hits += 1
        lookup_steps += sl.steps
    check_eq("65536 inserts match the reference set", sl.size, len(ref))
    measure("SkipList, 65536 random inserts",
            f"{sl.size} distinct values stored, level = {sl.level} "
            f"(max_level = {sl.max_level}), "
            f"avg insert steps = {insert_steps / 65536:.2f}, "
            f"avg lookup steps = {lookup_steps / 20000:.2f}, "
            f"hits = {hits}/20000")
    check("average walk is far below n (the O(log n) claim)",
          insert_steps / 65536 < 100 and lookup_steps / 20000 < 100)
    check("the list is taller than one level", sl.level > 1)

    # ------------------------------------------------ 1.5 rehash accounting
    section("1.5 amortised rehash cost (the O(1) claim)")
    m = ChainingHashMap()
    n = 1 << 20
    for i in range(n):
        m.put(f"k{i}", i)
    ops = m.rehash_ops
    measure("ChainingHashMap, n = 2^20 inserts",
            f"rehash_ops = {ops} ({ops / n:.5f}n), capacity = {len(m.table)}, "
            f"bound 1.5n = {int(1.5 * n)}")
    check_eq("every key landed", m.size, n)
    check("total rehash work is linear, not n log n", 1.4 * n < ops <= 1.5 * n + 64)
    # The exact count is  sum(0.75*cap_k + 1)  over the 18 resizes.  That is
    # 0.75*8*(2^18 - 1) + 18 = 1572858 + 18 = 1572876, and 1.5n = 1572864, so
    # the excess is 18 (one extra element per resize) - 6 (the dropped last
    # term of the geometric series) = 12.  Both languages agree on 12.
    check_eq("the excess over 1.5n reconciles to +12", ops - (n + n // 2), 12)


def iter_steps(i: int, n: int, kind: str):
    """Hop counts for the two Fenwick loops, independent of the article's code
    (which does not instrument itself)."""
    if kind == "prefix":
        j = i
        while j > 0:
            yield j
            j -= j & -j
    else:
        j = i
        while j <= n:
            yield j
            j += j & -j


# ===================================================================== C++
def cpp_checks(cpp_blocks: list[str]) -> None:
    section("C++17: the same structures, compiled with -Wall -Wextra -Werror")
    gxx = shutil.which("g++")
    if gxx is None:
        check("g++ is available", False)
        return
    check("g++ is available", True)

    with open(HARNESS, encoding="utf-8") as fh:
        harness = fh.read()
    source = ("\n\n".join(cpp_blocks) + "\n\n// ---- harness ----\n" + harness +
              "\nint main() { return run_all_tests(); }\n")

    tmp = tempfile.mkdtemp(prefix="hash-and-heap-cpp-")
    src = os.path.join(tmp, "all.cpp")
    exe = os.path.join(tmp, "all")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(source)

    cmd = [gxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1", "-o", exe, src]
    print(f"   $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    diagnostics = (proc.stdout or "") + (proc.stderr or "")
    check_eq("compiles with zero warnings under -Werror", (proc.returncode, diagnostics.strip()),
             (0, ""))
    if proc.returncode != 0:
        print(diagnostics)
        return
    print("   ok   compiled with zero warnings under -Werror")

    run = subprocess.run([exe], capture_output=True, text=True, timeout=1800)
    for line in run.stdout.splitlines():
        print(line)
    if run.stderr.strip():
        print("   stderr:", run.stderr.strip())
    check_eq("the C++ harness exits 0", run.returncode, 0)
    check_eq("no C++ diagnostic output", run.stderr.strip(), "")
    tail = [l for l in run.stdout.splitlines() if "assertions" in l]
    check("the C++ harness reports its assertion count", bool(tail))
    for line in run.stdout.splitlines():
        if line.strip().startswith("["):
            MEASURED.append("C++ " + line.strip().lstrip("["))


# ===================================================================== main
def main() -> int:
    if not os.path.exists(POST):
        print(f"missing post: {POST}")
        return 2
    with open(POST, encoding="utf-8") as fh:
        text = fh.read()

    rnd = random.Random(20261116)

    section("block accounting: the gate must see the article's own code")
    py_blocks = load_blocks(text, "python")
    cpp_blocks = load_blocks(text, "cpp")
    text_blocks = load_blocks(text, "text")
    bash_blocks = load_blocks(text, "bash")
    opens = re.findall(r"^```(\w+)", text, re.M)
    check_eq("python blocks", len(py_blocks), EXPECTED_PY_BLOCKS)
    check_eq("cpp blocks", len(cpp_blocks), EXPECTED_CPP_BLOCKS)
    check_eq("the two languages have equal block counts",
             len(py_blocks), len(cpp_blocks))
    check_eq("every fence is tagged and accounted for",
             sorted(opens), sorted(["python"] * len(py_blocks) +
                                   ["cpp"] * len(cpp_blocks) +
                                   ["text"] * len(text_blocks) +
                                   ["bash"] * len(bash_blocks)))
    check("the article still contains the gate commands",
          len(bash_blocks) == 1 and "verify_code.py" in bash_blocks[0])
    check("no unfilled measurement placeholder is left",
          "@@MEASURED" not in text or os.environ.get("ALLOW_PLACEHOLDERS") == "1")

    section("executing every ```python block from the article body")
    ns: dict = {}
    exec_ok = True
    for i, block in enumerate(py_blocks, 1):
        try:
            exec(compile(block, f"<post python block {i}>", "exec"), ns)
        except Exception as exc:                       # noqa: BLE001
            exec_ok = False
            print(f"   FAIL block {i} raised {type(exc).__name__}: {exc}")
            FAILURES.append(f"python block {i} raised {type(exc).__name__}")
    check("all python blocks execute", exec_ok)
    for name in ["ChainingHashMap", "LinearProbingMap", "ArrayHashMap",
                 "ConsistentHash", "MinPQ", "sink_in_place", "build_heap_floyd",
                 "build_heap_by_swim", "heap_sort", "TrieMap", "SegTree",
                 "LazySegTree", "Fenwick", "SkipList"]:
        check(f"the article defines {name}", name in ns)
    if not exec_ok:
        return 1

    python_checks(ns, rnd)
    cpp_checks(cpp_blocks)

    section("MEASUREMENTS (recorded by this run)")
    for line in MEASURED:
        print(f"   {line}")

    section("RESULT")
    if FAILURES:
        print(f"   {len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"     - {f}")
        return 1
    print("   CODE OK - every block runs, every cross-check matches, "
          "C++ compiles warning-free")
    return 0


if __name__ == "__main__":
    sys.exit(main())
