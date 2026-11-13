#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code gate for _posts/2026-11-24-shortest-path.md.

What it does
------------
1. Extracts every ```python / ```cpp fence straight out of the post — there is
   no second copy of the article's code anywhere in this file.
2. Executes all Python blocks, then runs the article's functions against
   hand-written cases and randomised cross-checks (Dijkstra heap vs dense vs
   Floyd vs Bellman-Ford, Prim vs Kruskal vs brute-force MST, A* vs Dijkstra,
   Hierholzer vs a brute-force Euler-path enumerator).
3. Builds a C++ harness out of the extracted C++ blocks and the *same* cases,
   compiles it with `g++ -std=c++17 -Wall -Wextra -Werror` and runs it.
4. Compares a 64-bit FNV-1a digest computed independently on both sides, so
   "the two languages agree" is a number, not a claim.

The randomised cases are *not* written out as literals: both sides generate
them from the same 64-bit LCG (see Rng / rngNext below), which keeps the
generated .cpp small enough to read.  Divergence in the generator itself would
silently poison every later comparison, so the first eight raw outputs are fed
into the digest first — if the two LCGs ever disagree, the digests differ
immediately and loudly.

Run:  python3 assets/blog/shortest-path-20261124/verify_code.py
"""

import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
POST = os.path.join(ROOT, "_posts", "2026-11-24-shortest-path.md")
GEN_CPP = os.path.join(HERE, "_generated_shortest_path_test.cpp")
GEN_BIN = os.path.join(HERE, "_generated_shortest_path_test")
SEED = 20261124
M64 = (1 << 64) - 1
MASK = M64

# --------------------------------------------------------------------------
# 1. extract the code blocks
# --------------------------------------------------------------------------
src = io.open(POST, encoding="utf-8").read()
blocks = re.findall(r"^```(python|cpp)[ \t]*\n(.*?)^```", src, re.M | re.S)
langs = [lang for lang, _ in blocks]
py_blocks = [b for lang, b in blocks if lang == "python"]
cpp_blocks = [b for lang, b in blocks if lang == "cpp"]

problems = []
if len(py_blocks) != len(cpp_blocks):
    problems.append(f"python/cpp 代码块数量不等: {len(py_blocks)} vs {len(cpp_blocks)}")
# 每个 ## 小节里 python 与 cpp 的数量必须相等（约定 §5：每道题两种语言）
sections = re.split(r"^## ", src, flags=re.M)[1:]
for sec in sections:
    name = sec.splitlines()[0][:28]
    n_py = len(re.findall(r"^```python[ \t]*$", sec, re.M))
    n_cpp = len(re.findall(r"^```cpp[ \t]*$", sec, re.M))
    if n_py != n_cpp:
        problems.append(f"小节「{name}」python/cpp 数量不等: {n_py} vs {n_cpp}")
for i, b in enumerate(cpp_blocks):
    if "bits/stdc++.h" in b:
        problems.append(f"第 {i} 个 C++ 块用了 bits/stdc++.h（本机 clang 没有）")
    if "int main(" in b:
        problems.append(f"第 {i} 个 C++ 块里有 main()，harness 会撞名")
if problems:
    for p in problems:
        print(f"  !! {p}")
    sys.exit(1)

print(f"extracted {len(blocks)} code blocks: "
      f"python {len(py_blocks)}, cpp {len(cpp_blocks)}")

INCLUDES = """#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <queue>
#include <set>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;
"""


def cpp_compiles_alone(block):
    """一个 C++ 块能不能独立编过：能的就是完整实现，不能的就是正文里的片段。"""
    cp = subprocess.run(["g++", "-std=c++17", "-fsyntax-only", "-x", "c++", "-"],
                        input=INCLUDES + "\n" + block + "\nint main() { return 0; }\n",
                        capture_output=True, text=True)
    return cp.returncode == 0


# --------------------------------------------------------------------------
# 2. execute the Python side (all complete blocks share one namespace)
# --------------------------------------------------------------------------
# 「最容易写错的一行」那种片段只有一两行、单独 exec 会 SyntaxError（比如光一个
# if 头、光一条声明）。这类片段照样要过语法检查，只是检查方式不同：包进
# while True: + pass 里编一遍。这是 gate 加的脚手架，不是文章里的代码。
py_complete, py_frag = [], []
for b in py_blocks:
    try:
        compile(b, "<block>", "exec")
        py_complete.append(b)
    except SyntaxError:
        py_frag.append(b)

for i, b in enumerate(py_frag):
    body = "\n".join("    " + ln for ln in b.splitlines() if ln.strip())
    try:
        compile("while True:\n" + body + "\n        pass", f"<frag {i}>", "exec")
    except SyntaxError as exc:
        print(f"  !! python 片段 #{i} 连包起来都编不过: {exc}\n{b}")
        sys.exit(1)
    if len(b.splitlines()) > 8:
        print(f"  !! python 片段 #{i} 有 {len(b.splitlines())} 行，"
              f"不像「一行」的示例了")
        sys.exit(1)

cpp_complete = [b for b in cpp_blocks if cpp_compiles_alone(b)]
cpp_frag = [b for b in cpp_blocks if b not in cpp_complete]
print(f"  完整实现: python {len(py_complete)} / cpp {len(cpp_complete)}；"
      f"一行示例片段: python {len(py_frag)} / cpp {len(cpp_frag)}")
for b in py_frag + cpp_frag:
    print("    · 片段: " + b.strip().splitlines()[0][:66])
if len(py_frag) != len(cpp_frag):
    print("  !! 两种语言的示例片段数量不等——正文里应该成对出现")
    sys.exit(1)

ns = {}
for i, b in enumerate(py_complete):
    try:
        exec(compile(b, f"<py block {i}>", "exec"), ns)
    except SyntaxError as exc:                      # pragma: no cover
        print(f"  !! python 第 {i} 块语法错误: {exc}")
        sys.exit(1)

dijkstra_dense = ns["dijkstra_dense"]
dijkstra = ns["dijkstra"]
bellman_ford = ns["bellman_ford"]
spfa = ns["spfa"]
floyd = ns["floyd"]
floyd_wrong_order = ns["floyd_wrong_order"]
prim = ns["prim"]
kruskal = ns["kruskal"]
astar = ns["astar"]
h_zero = ns["h_zero"]
h_manhattan = ns["h_manhattan"]
h_inadmissible = ns["h_inadmissible"]
euler_start = ns["euler_start"]
hierholzer = ns["hierholzer"]

NEEDED = ["dijkstra_dense", "dijkstra", "bellman_ford", "spfa", "floyd",
          "floyd_wrong_order", "prim", "kruskal", "DSU", "astar", "h_zero",
          "h_manhattan", "h_inadmissible", "euler_start", "hierholzer"]
missing = [nm for nm in NEEDED if nm not in ns]
if missing:
    print(f"  !! 文章里没定义这些函数: {missing}")
    sys.exit(1)

INF = float("inf")

checks = 0
fails = []


def check(label, got, want):
    global checks
    checks += 1
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")


def norm(v):
    """Unreachable -> -1 so the digest is language-independent."""
    if v == INF or v is None or v > 1e30:
        return -1
    return int(v)


def nvec(xs):
    return [norm(x) for x in xs]


# --------------------------------------------------------------------------
# 3. the shared PRNG (identical implementation on the C++ side)
# --------------------------------------------------------------------------
class Rng:
    def __init__(self, seed):
        self.s = seed & M64

    def next(self):
        self.s = (self.s * 6364136223846793005 + 1442695040888963407) & M64
        return self.s >> 33

    def below(self, k):
        return self.next() % k

    def between(self, a, b):
        return a + self.below(b - a + 1)


digest = 1469598103934665603


def feed(v):
    global digest
    digest ^= (v & MASK)
    digest = (digest * 1099511628211) & MASK


def feed_all(xs):
    for x in xs:
        feed(x)


# --------------------------------------------------------------------------
# 4. hand-written cases: the numbers the post actually prints
# --------------------------------------------------------------------------
# --- §1.2 the negative-edge counterexample ---------------------------------
neg_graph = [[(1, 3), (2, 4)], [], [(1, -10)]]          # s=0 -> a=1, b=2
d_heap, _ = dijkstra(neg_graph, 0)
d_dense = dijkstra_dense(neg_graph, 0)
d_dst, _ = dijkstra(neg_graph, 0, 1)                    # 点对点，dst = a
d_bf, neg_cycle = bellman_ford(neg_graph, 0)
check("1.2 朴素版给 3（错的）", norm(d_dense[1]), 3)
check("1.2 堆版 + dst 提前退出给 3（错的）", norm(d_dst[1]), 3)
check("1.2 堆版完整跑完给 -6（侥幸对了）", norm(d_heap[1]), -6)
check("1.2 Bellman-Ford 给 -6", norm(d_bf[1]), -6)
check("1.2 这张图没有负环", neg_cycle, False)
check("1.2 堆版其他点不变", nvec(d_heap), [0, -6, 4])
feed_all(nvec(d_dense) + nvec(d_heap) + nvec(d_dst) + nvec(d_bf))
feed(1 if neg_cycle else 0)

# --- 不可达：显式断言 -----------------------------------------------------
iso = [[] for _ in range(3)]                            # 三个点，一条边都没有
check("不可达 dist 是无穷大", norm(dijkstra_dense(iso, 0)[1]), -1)
check("不可达（堆版）", norm(dijkstra(iso, 0)[0][2]), -1)
check("不可达 + dst 提前退出", norm(dijkstra(iso, 0, 2)[0][2]), -1)
check("不可达 Bellman-Ford", norm(bellman_ford(iso, 0)[0][2]), -1)
_fw = floyd(3, [])
check("不可达 Floyd", norm(_fw[0][2]), -1)
check("Floyd 对角线是 0", [_fw[i][i] for i in range(3)], [0, 0, 0])
check("空图（n=0）Floyd", floyd(0, []), [])
check("单点图 dijkstra", nvec(dijkstra([[]], 0)[0]), [0])
check("单点图 dijkstra_dense", nvec(dijkstra_dense([[]], 0)), [0])
check("单点图 prim 总权重 0", prim([[]]), (0, True))
check("空图 prim（n=0）", prim([]), (0, True))
check("单点图 Kruskal", kruskal(1, [])[:2], (0, []))
check("无边图 prim 不连通", prim([[], [], []])[1], False)
check("无边图 Kruskal 不连通", kruskal(3, [])[2], False)
check("自环不影响最短路", nvec(dijkstra([[(0, 5)], [(0, 1)]], 1)[0]), [1, 0])
check("自环不影响 Kruskal",
      kruskal(2, [(1, 0, 0)])[:2], (0, []))
check("重边留最小的那条",
      nvec(dijkstra([[(1, 7), (1, 2)], []], 0)[0]), [0, 2])
check("重边 Floyd 留最小", norm(floyd(2, [(0, 1, 7), (0, 1, 2)])[0][1]), 2)
check("重边 Kruskal 只用一条",
      kruskal(2, [(7, 0, 1), (2, 0, 1)])[:2], (2, [(0, 1, 2)]))
feed_all([norm(dijkstra_dense(iso, 0)[1]), norm(dijkstra(iso, 0)[0][2]),
          norm(bellman_ford(iso, 0)[0][2]), norm(floyd(3, [])[0][2])])
feed(prim([[]])[0])
feed(prim([[], [], []])[1])

# --- §3.3 Floyd 的循环顺序 -------------------------------------------------
ring4 = [(0, 1, 4), (1, 2, 3), (2, 3, 4), (3, 0, 2)]
check("3.3 正确顺序 dist[1][0] = 9", norm(floyd(4, ring4)[1][0]), 9)
check("3.3 k 在内层给无穷大", norm(floyd_wrong_order(4, ring4)[1][0]), -1)
check("3.3 小图上两版碰巧都是 2（所以光看小样例发现不了）",
      [norm(floyd(3, [(0, 1, 1), (1, 2, 1)])[0][2]),
       norm(floyd_wrong_order(3, [(0, 1, 1), (1, 2, 1)])[0][2])], [2, 2])
check("3.4 负环: 对角线 < 0",
      floyd(2, [(0, 1, 1), (1, 0, -5)])[1][1] < 0, True)
check("3.4 无负环: 对角线 = 0", floyd(2, [(0, 1, 1), (1, 0, -1)])[1][1], 0)
feed_all([norm(floyd(3, [(0, 1, 1), (1, 2, 1)])[0][2]),
          norm(floyd(4, ring4)[1][0]),
          norm(floyd_wrong_order(4, ring4)[1][0])])
feed(1 if floyd(2, [(0, 1, 1), (1, 0, -5)])[1][1] < 0 else 0)

# --- §4.1 「MST 不是最短路」的三角形 --------------------------------------
tri = [(4, 0, 1), (4, 1, 2), (5, 0, 2)]
check("4.1 三角形 MST = 8", kruskal(3, tri)[0], 8)
tri_graph = [[(1, 4), (2, 5)], [(0, 4), (2, 4)], [(0, 5), (1, 4)]]
check("4.1 同一张图 A->C 最短路 = 5", dijkstra_dense(tri_graph, 0)[2], 5)
# 选中的边以 (u, v, w) 的形式返回
check("4.1 最短路那条边不在 MST 里", sorted([e[:2] for e in kruskal(3, tri)[1]]),
      [(0, 1), (1, 2)])
feed(kruskal(3, tri)[0])
feed(dijkstra_dense(tri_graph, 0)[2])

# --- §5.4 A* 的实测三（含不可采纳的 h）-----------------------------------
g5 = [[0] * 5 for _ in range(5)]
g5[3][1] = 1                                            # 墙在 grid[3][1]
g5[4][3] = 1                                            # 墙在 grid[4][3]
a_zero = astar(g5, (0, 0), (4, 4), h_zero)
a_manh = astar(g5, (0, 0), (4, 4), h_manhattan)
a_bad = astar(g5, (0, 0), (4, 4), h_inadmissible)
check("5.4 实测三 真实最短 = 8", a_zero[0], 8)
check("5.4 实测三 曼哈顿仍然最优 = 8", a_manh[0], 8)
check("5.4 实测三 3×曼哈顿 = 10（错的）", a_bad[0], 10)
check("5.4 高估确实更快：扩展 23 -> 11", [a_zero[1], a_bad[1]], [23, 11])
feed_all([a_zero[0], a_manh[0], a_bad[0]])

# --- §6 LC 332 的两个官方样例（城市名按字母序编号）-----------------------
def euler_from_names(tickets):
    names = sorted({c for t in tickets for c in t})
    ids = {nm: i for i, nm in enumerate(names)}
    inv = {i: nm for nm, i in ids.items()}
    edges = [(ids[u], ids[v]) for u, v in tickets]
    st = euler_start(len(names), edges, True)
    if st is None:
        return None
    return [inv[i] for i in hierholzer(len(names), edges, True, st)]

check("6.5 332 样例一",
      euler_from_names([("JFK", "MUC"), ("MUC", "LHR"), ("LHR", "SFO"),
                        ("SFO", "JFK")]),
      ["JFK", "MUC", "LHR", "SFO", "JFK"])
check("6.5 332 样例二",
      euler_from_names([("JFK", "SFO"), ("JFK", "ATL"), ("SFO", "ATL"),
                        ("ATL", "JFK"), ("ATL", "SFO")]),
      ["JFK", "ATL", "JFK", "SFO", "ATL", "SFO"])
feed_all([ord(ch) for ch in "".join(
    euler_from_names([("JFK", "MUC"), ("MUC", "LHR"), ("LHR", "SFO"),
                      ("SFO", "JFK")]))])

# --------------------------------------------------------------------------
# 5. random families, shared with the C++ side
# --------------------------------------------------------------------------
rng = Rng(SEED)
for _ in range(8):                       # LCG self-test, fed first
    feed(rng.next())

# ---- A. 非负权有向图: 堆版 / 朴素版 / Floyd / Bellman-Ford 四方对拍 ------
def rand_graph(rng, lo, hi, wn, wlo, whi):
    n = rng.between(1, wn)
    m = rng.between(0, wn + 5)
    edges = []
    for _ in range(m):
        u = rng.below(n)
        v = rng.below(n)                 # 自环与重边都会出现
        w = rng.between(wlo, whi)
        edges.append((u, v, w))
    g = [[] for _ in range(n)]
    for u, v, w in edges:
        g[u].append((v, w))
    return n, edges, g


A_CASES = 60
a_bad = 0
for it in range(A_CASES):
    n, edges, g = rand_graph(rng, 0, 0, 7, 0, 20)
    s = rng.below(n)
    t = rng.below(n)
    dd = nvec(dijkstra_dense(g, s))
    dh = nvec(dijkstra(g, s)[0])
    fw = nvec(floyd(n, edges)[s])
    bf, neg = bellman_ford(g, s)
    if not (dd == dh == fw == nvec(bf)) or neg:
        a_bad += 1
        if a_bad <= 3:
            print(f"  !! A#{it} 四方不一致: n={n} s={s} edges={edges}\n"
                  f"     dense={dd}\n     heap={dh}\n     floyd={fw}\n"
                  f"     bf={nvec(bf)} neg={neg}")
    check(f"A#{it} 非负权无负环", neg, False)
    # 点对点版本在非负权下必须一致（对比 §1.2 的负权反例）
    check(f"A#{it} dst 提前退出不改答案",
          norm(dijkstra(g, s, t)[0][t]), dh[t])
    feed_all(dh)
    feed_all(nvec(bf))
print(f"A. 非负权有向图 {A_CASES} 张：堆版 / 朴素版 / Floyd / Bellman-Ford "
      f"四方互拍，不一致 {a_bad} 张")

# ---- B. 有负权边但没有负环的 DAG: Bellman-Ford vs Floyd ------------------
B_CASES = 40
b_bad = 0
for it in range(B_CASES):
    n = rng.between(2, 7)
    order = list(range(n))
    for i in range(n - 1, 0, -1):        # Fisher-Yates，用同一个 PRNG
        j = rng.below(i + 1)
        order[i], order[j] = order[j], order[i]
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.below(100) < 45:
                edges.append((order[i], order[j], rng.between(-10, 10)))
    g = [[] for _ in range(n)]
    for u, v, w in edges:
        g[u].append((v, w))
    s = rng.below(n)
    bf, neg = bellman_ford(g, s)
    fw = floyd(n, edges)[s]
    if nvec(bf) != nvec(fw) or neg:
        b_bad += 1
        if b_bad <= 3:
            print(f"  !! B#{it} 不一致: n={n} s={s} edges={edges}\n"
                  f"     bf={nvec(bf)}\n     floyd={nvec(fw)} neg={neg}")
    check(f"B#{it} DAG 无负环", neg, False)
    feed_all(nvec(bf))
    feed_all(nvec(fw))
print(f"B. 带负权边的 DAG {B_CASES} 张：Bellman-Ford vs Floyd，"
      f"不一致 {b_bad} 张")

# ---- C. 负环: Bellman-Ford 必须报出来, Floyd 对角线必须 < 0 --------------
C_CASES = 30
c_bad = 0
for it in range(C_CASES):
    n = rng.between(3, 6)
    edges = []
    for i in range(n - 1):               # 先来一条链，权重非负
        edges.append((i, i + 1, rng.between(0, 5)))
    path_w = sum(w for _, _, w in edges)
    back = rng.between(0, n - 2)
    edges.append((n - 1, back, -(path_w + 1 + rng.below(5))))   # 造一个负环
    g = [[] for _ in range(n)]
    for u, v, w in edges:
        g[u].append((v, w))
    _, neg = bellman_ford(g, 0)
    diag = floyd(n, edges)[back][back]
    if not neg or not (diag < 0):
        c_bad += 1
        if c_bad <= 3:
            print(f"  !! C#{it} 负环漏报: n={n} edges={edges} neg={neg} "
                  f"diag={diag}")
    check(f"C#{it} Bellman-Ford 报负环", neg, True)
    feed(1 if neg else 0)
    feed(1 if diag < 0 else 0)
print(f"C. 带负环的图 {C_CASES} 张：Bellman-Ford 与 Floyd 都查了出来，"
      f"漏报 {c_bad} 张")

# ---- D. MST: Prim vs Kruskal vs 暴力枚举 ---------------------------------
def brute_msf(n, wedges):
    """暴力最小生成森林：枚举所有边子集，取「无环且边数最多」里权重最小的。"""
    best = None
    m = len(wedges)
    for mask in range(1 << m):
        picked = [wedges[i] for i in range(m) if mask >> i & 1]
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        ok = True
        total = 0
        cnt = 0
        for w, u, v in picked:
            ru, rv = find(u), find(v)
            if ru == rv:
                ok = False
                break
            parent[ru] = rv
            total += w
            cnt += 1
        if not ok:
            continue
        # 最小生成森林 = 权值最小的「极大无环子集」。只数边数是不够的：
        # 空集也满足 cnt == n - comps，所以必须检查极大性——任何一条没选的
        # 边，两端都已经连通。
        maximal = True
        for i, (_, u, v) in enumerate(wedges):
            if mask >> i & 1:
                continue
            if find(u) != find(v):
                maximal = False
                break
        if not maximal:
            continue
        if best is None or total < best:
            best = total
    return best


D_CASES = 40
d_bad = 0
for it in range(D_CASES):
    n = rng.between(2, 6)
    wedges = []
    for i in range(1, n):                # 先随机一棵树保证连通
        wedges.append((rng.between(0, 20), i, rng.below(i)))
    for _ in range(rng.between(0, 5)):   # 再加一些边（含重边）
        wedges.append((rng.between(0, 20), rng.below(n), rng.below(n)))
    graph = [[] for _ in range(n)]
    for w, u, v in wedges:
        graph[u].append((v, w))
        graph[v].append((u, w))
    pt, pc = prim(graph)
    kt, chosen, kc = kruskal(n, list(wedges))
    bt = brute_msf(n, wedges)
    if not (pt == kt == bt and pc and kc and len(chosen) == n - 1):
        d_bad += 1
        if d_bad <= 3:
            print(f"  !! D#{it} MST 不一致: n={n} edges={wedges}\n"
                  f"     prim={pt},{pc} kruskal={kt},{kc} brute={bt} "
                  f"chosen={chosen}")
    check(f"D#{it} 连通图的 MST 唯一值", pt, bt)
    feed(pt)
    feed(1 if pc else 0)
    feed(kt)

# 不连通图：两个算法都要给「最小生成森林」并且结果一致
disc_w = [(1, 0, 1), (2, 2, 3)]        # 两组之间没有边，真的不连通
_dg = [[] for _ in range(4)]
for w, u, v in disc_w:
    _dg[u].append((v, w))
    _dg[v].append((u, w))
check("D 不连通图 Prim 森林权重", prim(_dg)[0], 3)
check("D 不连通图 Kruskal 森林权重", kruskal(4, disc_w)[0], 3)
check("D 不连通图两边都不连通", (prim(_dg)[1], kruskal(4, disc_w)[2]),
      (False, False))
feed(prim(_dg)[0])
feed(kruskal(4, disc_w)[0])
print(f"D. 生成树 {D_CASES} 张连通图：Prim vs Kruskal vs 暴力枚举，"
      f"不一致 {d_bad} 张")

# ---- E. A*: h≡0 必须等于 Dijkstra, 可采纳的 h 不改变答案 -----------------
def grid_graph(grid):
    h, w = len(grid), len(grid[0])
    g = [[] for _ in range(h * w)]
    for y in range(h):
        for x in range(w):
            if grid[y][x]:
                continue
            u = y * w + x
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not grid[ny][nx]:
                    g[u].append((ny * w + nx, 1))
    return g


E_CASES = 40
e_bad = 0
exp_zero = 0
exp_manh = 0
for it in range(E_CASES):
    gh = rng.between(4, 6)
    gw = rng.between(4, 6)
    grid = [[1 if rng.below(100) < 22 else 0 for _ in range(gw)]
            for _ in range(gh)]
    grid[0][0] = 0
    grid[gh - 1][gw - 1] = 0
    zero = astar(grid, (0, 0), (gw - 1, gh - 1), h_zero)
    manh = astar(grid, (0, 0), (gw - 1, gh - 1), h_manhattan)
    gg = grid_graph(grid)
    opt = norm(dijkstra_dense(gg, 0)[gh * gw - 1])
    if not (zero[0] == opt and manh[0] == opt):
        e_bad += 1
        if e_bad <= 3:
            print(f"  !! E#{it} A* 与 Dijkstra 不一致: {gh}x{gw} "
                  f"dijkstra={opt} h0={zero[0]} manh={manh[0]} grid={grid}")
    check(f"E#{it} h≡0 等于 Dijkstra", zero[0], opt)
    check(f"E#{it} 曼哈顿仍然最优", manh[0], opt)
    exp_zero += zero[1]
    exp_manh += manh[1]
    feed(zero[0])
    feed(manh[0])
    feed(opt)
print(f"E. A* {E_CASES} 张随机网格：h≡0 与 Dijkstra 逐例相同、曼哈顿不改变"
      f"答案，不一致 {e_bad} 张")
print(f"   扩展格子数合计：h≡0 = {exp_zero}，曼哈顿 = {exp_manh}"
      f"（{(exp_manh / exp_zero - 1) * 100:+.1f}%）")
check("E 曼哈顿的扩展数合计不超过 h≡0", exp_manh <= exp_zero, True)
feed(exp_zero)
feed(exp_manh)

# ---- F. 欧拉路径: 判定对拍暴力 / 合法性 / 字典序最小 ---------------------
def out_adj(n, edges, directed):
    out = [[] for _ in range(n)]
    for eid, (u, v) in enumerate(edges):
        out[u].append((v, eid))
        if not directed:
            out[v].append((u, eid))
    return out


def brute_exists(n, edges, directed):
    if not edges:
        return True
    out = out_adj(n, edges, directed)
    found = [False]

    def rec(u, used, cnt):
        if found[0]:
            return
        if cnt == len(edges):
            found[0] = True
            return
        for v, eid in out[u]:
            if not used[eid]:
                used[eid] = True
                rec(v, used, cnt + 1)
                used[eid] = False

    for s in range(n):
        rec(s, [False] * len(edges), 0)
    return found[0]


def brute_best(n, start, edges, directed):
    out = out_adj(n, edges, directed)
    best = [None]

    def rec(u, used, path):
        if all(used):
            if best[0] is None or path < best[0]:
                best[0] = list(path)
            return
        for v, eid in out[u]:
            if not used[eid]:
                used[eid] = True
                path.append(v)
                rec(v, used, path)
                path.pop()
                used[eid] = False

    rec(start, [False] * len(edges), [start])
    return best[0]


def legal_path(start, edges, directed, path):
    if path is None or not path or path[0] != start:
        return False
    if len(path) != len(edges) + 1:
        return False
    pool = list(edges)
    for a, b in zip(path, path[1:]):
        for i, (u, v) in enumerate(pool):
            if (u, v) == (a, b) or (not directed and (u, v) == (b, a)):
                pool.pop(i)
                break
        else:
            return False
    return not pool


F_ITERS = 6000
judge_n = legal_n = lex_n = 0
bad_judge = bad_legal = bad_lex = 0
for it in range(F_ITERS):
    for directed in (False, True):
        n = rng.between(1, 5)
        m = rng.between(0, 6)
        edges = [(rng.below(n), rng.below(n)) for _ in range(m)]
        st = euler_start(n, edges, directed)
        exists = brute_exists(n, edges, directed)
        judge_n += 1
        if (st is not None) != exists:
            bad_judge += 1
            if bad_judge <= 3:
                print(f"  !! F#{it} 判定不一致 directed={directed} n={n} "
                      f"edges={edges} 判定={st} 暴力={exists}")
        if st is None:
            continue
        path = hierholzer(n, edges, directed, st)
        legal_n += 1
        if not legal_path(st, edges, directed, path):
            bad_legal += 1
            if bad_legal <= 3:
                print(f"  !! F#{it} 路径不合法 directed={directed} n={n} "
                      f"edges={edges} start={st} path={path}")
        lex_n += 1
        best = brute_best(n, st, edges, directed)
        if path != best:
            bad_lex += 1
            if bad_lex <= 3:
                print(f"  !! F#{it} 不是字典序最小 directed={directed} "
                      f"edges={edges} start={st} got={path} best={best}")
        feed(1 if st is not None else 0)
        feed(len(path))
        feed_all(path)
print(f"F. 欧拉路径：判定对拍 {judge_n} 例（不一致 {bad_judge}）；"
      f"路径合法性 {legal_n} 例（不合法 {bad_legal}）；"
      f"字典序最小 {lex_n} 例（不一致 {bad_lex}）")

# ---- G. SPFA: 无负环图上不许误报（§2.4 的实测）-------------------------
G_CASES = 2000
g_pairs = 0
g_false = 0
t_spfa = 0.0
t_bf = 0.0
for it in range(G_CASES):
    n, edges, g = rand_graph(rng, 0, 0, 8, 0, 9)
    for s in range(n):
        t0 = time.perf_counter()
        d_sp, neg = spfa(g, s)
        t_spfa += time.perf_counter() - t0
        t1 = time.perf_counter()
        d_bf, neg_bf = bellman_ford(g, s)
        t_bf += time.perf_counter() - t1
        g_pairs += 1
        if neg or neg_bf or nvec(d_sp) != nvec(d_bf):
            g_false += 1
print(f"G. SPFA：{g_pairs} 个（无负环图, 起点）组合上误报 {g_false} 次；"
      f"同一批图上 SPFA {t_spfa * 1e3:.1f} ms vs Bellman-Ford "
      f"{t_bf * 1e3:.1f} ms（实测，随机器变）")
check("G SPFA 一次误报都没有", g_false, 0)
feed(g_pairs)
feed(g_false)

py_digest = digest
for f in fails:
    print(f"  !! {f}")
print(f"python checks: {checks}, failures: {len(fails)}"
      f"{'  ← 先看这些，再往下走 C++' if fails else ''}")

# --------------------------------------------------------------------------
# 6. the C++ side
# --------------------------------------------------------------------------
CPP_HARNESS = r"""
// ---------------------------------------------------------------- harness
static unsigned long long digest = 1469598103934665603ULL;

static void feed(long long v) {
    digest ^= (unsigned long long)v;
    digest *= 1099511628211ULL;
}

static void feedAll(const vector<long long>& xs) {
    for (long long x : xs) feed(x);
}

struct Rng {
    unsigned long long s;
    explicit Rng(unsigned long long seed) : s(seed) {}
    unsigned long long next() {
        s = s * 6364136223846793005ULL + 1442695040888963407ULL;
        return s >> 33;
    }
    int below(int k) { return static_cast<int>(next() % static_cast<unsigned long long>(k)); }
    int between(int a, int b) { return a + below(b - a + 1); }
};

static long long norm(long long v) { return v > (1LL << 40) ? -1 : v; }

static vector<long long> nvec(const vector<long long>& xs) {
    vector<long long> out;
    for (long long x : xs) out.push_back(norm(x));
    return out;
}

static int failures = 0;
static int checks = 0;

static void check(const string& label, long long got, long long want) {
    ++checks;
    if (got != want) {
        ++failures;
        cout << "  !! " << label << ": got " << got << ", want " << want << "\n";
    }
}

static void checkVec(const string& label, const vector<long long>& got,
                     const vector<long long>& want) {
    ++checks;
    if (got != want) {
        ++failures;
        cout << "  !! " << label << " 向量不一致\n";
    }
}

static vector<vector<pair<int, int>>> adjOf(int n, const vector<array<int, 3>>& edges) {
    vector<vector<pair<int, int>>> g(n);
    for (const auto& e : edges) g[e[0]].push_back({e[1], e[2]});
    return g;
}

// 暴力最小生成森林：枚举所有边子集，取「极大无环」里权重最小的
static long long bruteMsf(int n, const vector<array<int, 3>>& wedges) {
    int m = static_cast<int>(wedges.size());
    long long best = -1;
    for (int mask = 0; mask < (1 << m); ++mask) {
        vector<int> parent(n);
        for (int i = 0; i < n; ++i) parent[i] = i;
        function<int(int)> find = [&](int x) {
            while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
            return x;
        };
        bool ok = true;
        long long total = 0;
        for (int i = 0; i < m && ok; ++i) {
            if (!((mask >> i) & 1)) continue;
            int u = wedges[i][1], v = wedges[i][2];
            int ru = find(u), rv = find(v);
            if (ru == rv) { ok = false; break; }
            parent[ru] = rv;
            total += wedges[i][0];
        }
        if (!ok) continue;
        // 极大性：没选的边两端必须已经连通（空集不满足，所以不会被当成森林）
        bool maximal = true;
        for (int i = 0; i < m && maximal; ++i) {
            if ((mask >> i) & 1) continue;
            if (find(wedges[i][1]) != find(wedges[i][2])) maximal = false;
        }
        if (!maximal) continue;
        if (best < 0 || total < best) best = total;
    }
    return best;
}

static bool bruteExistsRec(int u, int cnt, int m, const vector<vector<pair<int, int>>>& adj,
                           vector<char>& used, bool& found) {
    if (found) return true;
    if (cnt == m) { found = true; return true; }
    for (auto& e : adj[u]) {
        if (!used[e.second]) {
            used[e.second] = 1;
            bruteExistsRec(e.first, cnt + 1, m, adj, used, found);
            used[e.second] = 0;
            if (found) return true;
        }
    }
    return false;
}

static bool bruteExists(int n, const vector<pair<int, int>>& edges, bool directed) {
    if (edges.empty()) return true;
    vector<vector<pair<int, int>>> adj(n);
    for (int eid = 0; eid < static_cast<int>(edges.size()); ++eid) {
        adj[edges[eid].first].push_back({edges[eid].second, eid});
        if (!directed) adj[edges[eid].second].push_back({edges[eid].first, eid});
    }
    for (int s = 0; s < n; ++s) {
        vector<char> used(edges.size(), 0);
        bool found = false;
        bruteExistsRec(s, 0, static_cast<int>(edges.size()), adj, used, found);
        if (found) return true;
    }
    return false;
}

static void bruteBestRec(int u, const vector<vector<pair<int, int>>>& adj,
                         vector<char>& used, vector<int>& path, int m,
                         vector<int>& best) {
    if (static_cast<int>(path.size()) == m + 1) {
        if (best.empty() || path < best) best = path;
        return;
    }
    for (auto& e : adj[u]) {
        if (!used[e.second]) {
            used[e.second] = 1;
            path.push_back(e.first);
            bruteBestRec(e.first, adj, used, path, m, best);
            path.pop_back();
            used[e.second] = 0;
        }
    }
}

static vector<int> bruteBest(int n, int start, const vector<pair<int, int>>& edges,
                             bool directed) {
    vector<vector<pair<int, int>>> adj(n);
    for (int eid = 0; eid < static_cast<int>(edges.size()); ++eid) {
        adj[edges[eid].first].push_back({edges[eid].second, eid});
        if (!directed) adj[edges[eid].second].push_back({edges[eid].first, eid});
    }
    vector<char> used(edges.size(), 0);
    vector<int> path{start}, best;
    bruteBestRec(start, adj, used, path, static_cast<int>(edges.size()), best);
    return best;
}

static bool legalPath(int start, const vector<pair<int, int>>& edges, bool directed,
                      const vector<int>& path) {
    if (path.empty() || path[0] != start) return false;
    if (static_cast<int>(path.size()) != static_cast<int>(edges.size()) + 1) return false;
    vector<char> used(edges.size(), 0);
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        bool hit = false;
        for (int eid = 0; eid < static_cast<int>(edges.size()); ++eid) {
            if (used[eid]) continue;
            int u = edges[eid].first, v = edges[eid].second;
            if ((u == path[i] && v == path[i + 1]) ||
                (!directed && u == path[i + 1] && v == path[i])) {
                used[eid] = 1;
                hit = true;
                break;
            }
        }
        if (!hit) return false;
    }
    for (char c : used) if (!c) return false;
    return true;
}

static vector<vector<pair<int, int>>> gridGraph(const vector<vector<int>>& grid) {
    int h = static_cast<int>(grid.size()), w = static_cast<int>(grid[0].size());
    vector<vector<pair<int, int>>> g(h * w);
    const int dy[4] = {1, -1, 0, 0};
    const int dx[4] = {0, 0, 1, -1};
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (grid[y][x]) continue;
            int u = y * w + x;
            for (int d = 0; d < 4; ++d) {
                int ny = y + dy[d], nx = x + dx[d];
                if (ny >= 0 && ny < h && nx >= 0 && nx < w && !grid[ny][nx])
                    g[u].push_back({ny * w + nx, 1});
            }
        }
    }
    return g;
}

int main() {
    // ---- 手写用例：正文里印出来的那些数字 ----------------------------
    vector<vector<pair<int, int>>> negGraph{{{1, 3}, {2, 4}}, {}, {{1, -10}}};
    auto dHeap = dijkstra(negGraph, 0);
    auto dDense = dijkstraDense(negGraph, 0);
    auto dDst = dijkstra(negGraph, 0, 1);
    auto dNegBf = bellmanFord(negGraph, 0);
    check("1.2 朴素版给 3（错的）", norm(dDense[1]), 3);
    check("1.2 堆版 + dst 给 3（错的）", norm(dDst.first[1]), 3);
    check("1.2 堆版完整跑完给 -6（侥幸对了）", norm(dHeap.first[1]), -6);
    check("1.2 Bellman-Ford 给 -6", norm(dNegBf.first[1]), -6);
    check("1.2 这张图没有负环", dNegBf.second ? 1 : 0, 0);
    checkVec("1.2 堆版其他点不变", nvec(dHeap.first), {0, -6, 4});
    feedAll(nvec(dDense));
    feedAll(nvec(dHeap.first));
    feedAll(nvec(dDst.first));
    feedAll(nvec(dNegBf.first));
    feed(dNegBf.second ? 1 : 0);

    int iso_n = 3;
    vector<vector<pair<int, int>>> iso(iso_n);
    check("不可达 dist 是无穷大", norm(dijkstraDense(iso, 0)[1]), -1);
    check("不可达（堆版）", norm(dijkstra(iso, 0).first[2]), -1);
    check("不可达 + dst 提前退出", norm(dijkstra(iso, 0, 2).first[2]), -1);
    check("不可达 Bellman-Ford", norm(bellmanFord(iso, 0).first[2]), -1);
    auto fwEmpty = floyd(3, {});
    check("不可达 Floyd", norm(fwEmpty[0][2]), -1);
    check("Floyd 对角线是 0", fwEmpty[1][1], 0);
    check("空图（n=0）Floyd 行数", static_cast<long long>(floyd(0, {}).size()), 0);
    check("单点图 dijkstra", norm(dijkstra({{}}, 0).first[0]), 0);
    check("单点图 dijkstra_dense", norm(dijkstraDense({{}}, 0)[0]), 0);
    check("单点图 prim 总权重 0", prim({{}}).first, 0);
    check("空图 prim（n=0）", prim({}).first, 0);
    check("单点图 Kruskal", kruskal(1, {}).first, 0);
    check("无边图 prim 不连通", prim({{}, {}, {}}).second ? 1 : 0, 0);
    check("无边图 Kruskal 不连通", kruskal(3, {}).second ? 1 : 0, 0);
    {
        vector<vector<pair<int, int>>> selfLoop{{{0, 5}}, {{0, 1}}};
        checkVec("自环不影响最短路", nvec(dijkstra(selfLoop, 1).first), {1, 0});
        check("自环不影响 Kruskal", kruskal(2, {{1, 0, 0}}).first, 0);
        vector<vector<pair<int, int>>> par{{{1, 7}, {1, 2}}, {}};
        checkVec("重边留最小的那条", nvec(dijkstra(par, 0).first), {0, 2});
        check("重边 Floyd 留最小", norm(floyd(2, {{0, 1, 7}, {0, 1, 2}})[0][1]), 2);
        check("重边 Kruskal 只用一条", kruskal(2, {{7, 0, 1}, {2, 0, 1}}).first, 2);
    }
    feed(norm(dijkstraDense(iso, 0)[1]));
    feed(norm(dijkstra(iso, 0).first[2]));
    feed(norm(bellmanFord(iso, 0).first[2]));
    feed(norm(floyd(3, {})[0][2]));
    feed(prim({{}}).first);
    feed(prim({{}, {}, {}}).second ? 1 : 0);

    // ---- §3.3 Floyd 的循环顺序 --------------------------------------
    vector<array<int, 3>> ring4{{0, 1, 4}, {1, 2, 3}, {2, 3, 4}, {3, 0, 2}};
    check("3.3 正确顺序 dist[1][0] = 9", norm(floyd(4, ring4)[1][0]), 9);
    check("3.3 k 在内层给无穷大", norm(floydWrongOrder(4, ring4)[1][0]), -1);
    {
        vector<array<int, 3>> small{{0, 1, 1}, {1, 2, 1}};
        check("3.3 小图上两版碰巧都是 2", norm(floyd(3, small)[0][2]), 2);
        check("3.3 小图上错版也是 2", norm(floydWrongOrder(3, small)[0][2]), 2);
        feed(norm(floyd(3, small)[0][2]));
    }
    check("3.4 负环: 对角线 < 0",
          floyd(2, {{0, 1, 1}, {1, 0, -5}})[1][1] < 0 ? 1 : 0, 1);
    feed(norm(floyd(4, ring4)[1][0]));
    feed(norm(floydWrongOrder(4, ring4)[1][0]));
    feed(floyd(2, {{0, 1, 1}, {1, 0, -5}})[1][1] < 0 ? 1 : 0);

    // ---- §4.1 MST 不是最短路 ----------------------------------------
    {
        vector<array<int, 3>> tri{{4, 0, 1}, {4, 1, 2}, {5, 0, 2}};
        check("4.1 三角形 MST = 8", kruskal(3, tri).first, 8);
        vector<vector<pair<int, int>>> triG{{{1, 4}, {2, 5}}, {{0, 4}, {2, 4}},
                                            {{0, 5}, {1, 4}}};
        check("4.1 A->C 最短路 = 5", dijkstraDense(triG, 0)[2], 5);
        feed(kruskal(3, tri).first);
        feed(dijkstraDense(triG, 0)[2]);
    }

    // ---- §5.4 A* 的三个实测 -----------------------------------------
    {
        vector<vector<int>> g5(5, vector<int>(5, 0));
        g5[3][1] = 1;
        g5[4][3] = 1;
        auto aZero = astarGrid(g5, 0, 0, 4, 4, hZero);
        auto aManh = astarGrid(g5, 0, 0, 4, 4, hManhattan);
        auto aBad = astarGrid(g5, 0, 0, 4, 4, hInadmissible);
        check("5.4 实测三 真实最短 = 8", aZero.first, 8);
        check("5.4 实测三 曼哈顿仍然最优 = 8", aManh.first, 8);
        check("5.4 实测三 3×曼哈顿 = 10（错的）", aBad.first, 10);
        check("5.4 高估扩展 23 -> 11", aZero.second * 100 + aBad.second, 2311);
        feed(aZero.first);
        feed(aManh.first);
        feed(aBad.first);
    }

    // ---- §6 LC 332 的两个官方样例 -----------------------------------
    {
        vector<string> names{"ATL", "JFK", "LHR", "MUC", "SFO"};
        auto idOf = [&](const string& s) {
            for (size_t i = 0; i < names.size(); ++i) if (names[i] == s) return static_cast<int>(i);
            return -1;
        };
        vector<pair<string, string>> t1{{"JFK", "MUC"}, {"MUC", "LHR"},
                                        {"LHR", "SFO"}, {"SFO", "JFK"}};
        vector<pair<int, int>> e1;
        for (auto& t : t1) e1.push_back({idOf(t.first), idOf(t.second)});
        int s1 = eulerStart(5, e1, true);
        vector<int> p1 = s1 < 0 ? vector<int>{} : hierholzer(5, e1, true, s1);
        vector<int> want1{idOf("JFK"), idOf("MUC"), idOf("LHR"), idOf("SFO"), idOf("JFK")};
        checkVec("6.5 332 样例一", vector<long long>(p1.begin(), p1.end()),
                 vector<long long>(want1.begin(), want1.end()));
        vector<pair<string, string>> t2{{"JFK", "SFO"}, {"JFK", "ATL"}, {"SFO", "ATL"},
                                        {"ATL", "JFK"}, {"ATL", "SFO"}};
        vector<pair<int, int>> e2;
        for (auto& t : t2) e2.push_back({idOf(t.first), idOf(t.second)});
        int s2 = eulerStart(5, e2, true);
        vector<int> p2 = s2 < 0 ? vector<int>{} : hierholzer(5, e2, true, s2);
        vector<int> want2{idOf("JFK"), idOf("ATL"), idOf("JFK"), idOf("SFO"),
                          idOf("ATL"), idOf("SFO")};
        checkVec("6.5 332 样例二", vector<long long>(p2.begin(), p2.end()),
                 vector<long long>(want2.begin(), want2.end()));
        for (int v : p1)
            for (char c : names[v]) feed(static_cast<long long>(c));
    }

    // ---- 随机家族：与 Python 侧同一个 LCG、同一批用例 ---------------
    Rng rng(20261124ULL);
    for (int i = 0; i < 8; ++i) feed(static_cast<long long>(rng.next()));

    // A. 非负权有向图：堆版 / 朴素版 / Floyd / Bellman-Ford
    long long aBad = 0;
    for (int it = 0; it < 60; ++it) {
        int n = rng.between(1, 7);
        int m = rng.between(0, 12);
        vector<array<int, 3>> edges;
        for (int i = 0; i < m; ++i) {
            int u = rng.below(n), v = rng.below(n), w = rng.between(0, 20);
            edges.push_back({u, v, w});
        }
        auto g = adjOf(n, edges);
        int s = rng.below(n), t = rng.below(n);
        auto dd = nvec(dijkstraDense(g, s));
        auto dh = nvec(dijkstra(g, s).first);
        auto fw = nvec(floyd(n, edges)[s]);
        auto bf = nvec(bellmanFord(g, s).first);
        bool bad = !(dd == dh && dh == fw && fw == bf) || bellmanFord(g, s).second;
        if (bad) ++aBad;
        check("A 非负权无负环", bellmanFord(g, s).second ? 1 : 0, 0);
        check("A dst 提前退出不改答案", norm(dijkstra(g, s, t).first[t]), dh[t]);
        feedAll(dh);
        feedAll(bf);
    }
    cout << "A. 非负权有向图 60 张：四方互拍不一致 " << aBad << " 张\n";

    // B. 带负权边的 DAG：Bellman-Ford vs Floyd
    long long bBad = 0;
    for (int it = 0; it < 40; ++it) {
        int n = rng.between(2, 7);
        vector<int> order(n);
        for (int i = 0; i < n; ++i) order[i] = i;
        for (int i = n - 1; i > 0; --i) {
            int j = rng.below(i + 1);
            swap(order[i], order[j]);
        }
        vector<array<int, 3>> edges;
        for (int i = 0; i < n; ++i)
            for (int j = i + 1; j < n; ++j)
                if (rng.below(100) < 45)
                    edges.push_back({order[i], order[j], rng.between(-10, 10)});
        auto g = adjOf(n, edges);
        int s = rng.below(n);
        auto bf = nvec(bellmanFord(g, s).first);
        auto fw = nvec(floyd(n, edges)[s]);
        if (bf != fw || bellmanFord(g, s).second) ++bBad;
        check("B DAG 无负环", bellmanFord(g, s).second ? 1 : 0, 0);
        feedAll(bf);
        feedAll(fw);
    }
    cout << "B. 带负权边的 DAG 40 张：不一致 " << bBad << " 张\n";

    // C. 负环
    long long cBad = 0;
    for (int it = 0; it < 30; ++it) {
        int n = rng.between(3, 6);
        vector<array<int, 3>> edges;
        long long pathW = 0;
        for (int i = 0; i < n - 1; ++i) {
            int w = rng.between(0, 5);
            edges.push_back({i, i + 1, w});
            pathW += w;
        }
        int back = rng.between(0, n - 2);
        edges.push_back({n - 1, back, static_cast<int>(-(pathW + 1 + rng.below(5)))});
        auto g = adjOf(n, edges);
        bool neg = bellmanFord(g, 0).second;
        long long diag = norm(floyd(n, edges)[back][back]);
        if (!neg || diag >= 0) ++cBad;
        check("C Bellman-Ford 报负环", neg ? 1 : 0, 1);
        feed(neg ? 1 : 0);
        feed(diag < 0 ? 1 : 0);
    }
    cout << "C. 带负环的图 30 张：漏报 " << cBad << " 张\n";

    // D. MST：Prim vs Kruskal vs 暴力
    long long dBad = 0;
    for (int it = 0; it < 40; ++it) {
        int n = rng.between(2, 6);
        vector<array<int, 3>> wedges;                 // {w, u, v}
        for (int i = 1; i < n; ++i) wedges.push_back({rng.between(0, 20), i, rng.below(i)});
        int extra = rng.between(0, 5);
        for (int i = 0; i < extra; ++i)
            wedges.push_back({rng.between(0, 20), rng.below(n), rng.below(n)});
        vector<vector<pair<int, int>>> graph(n);
        for (auto& e : wedges) {
            graph[e[1]].push_back({e[2], e[0]});
            graph[e[2]].push_back({e[1], e[0]});
        }
        auto pr = prim(graph);
        auto kr = kruskal(n, wedges);
        long long bt = bruteMsf(n, wedges);
        if (!(pr.first == kr.first && kr.first == bt && pr.second && kr.second)) ++dBad;
        check("D MST 三方一致", pr.first, bt);
        feed(pr.first);
        feed(pr.second ? 1 : 0);
        feed(kr.first);
    }
    {
        vector<array<int, 3>> disc{{1, 0, 1}, {2, 2, 3}};
        vector<vector<pair<int, int>>> dg(4);
        for (auto& e : disc) {
            dg[e[1]].push_back({e[2], e[0]});
            dg[e[2]].push_back({e[1], e[0]});
        }
        check("D 不连通图 Prim 森林权重", prim(dg).first, 3);
        check("D 不连通图 Kruskal 森林权重", kruskal(4, disc).first, 3);
        check("D 不连通图两边都不连通",
              (prim(dg).second ? 1 : 0) + (kruskal(4, disc).second ? 1 : 0), 0);
        feed(prim(dg).first);
        feed(kruskal(4, disc).first);
    }
    cout << "D. 生成树 40 张连通图：三方不一致 " << dBad << " 张\n";

    // E. A*：h≡0 必须等于 Dijkstra
    long long eBad = 0, expZero = 0, expManh = 0;
    for (int it = 0; it < 40; ++it) {
        int gh = rng.between(4, 6), gw = rng.between(4, 6);
        vector<vector<int>> grid(gh, vector<int>(gw, 0));
        for (int y = 0; y < gh; ++y)
            for (int x = 0; x < gw; ++x)
                if (rng.below(100) < 22) grid[y][x] = 1;
        grid[0][0] = 0;
        grid[gh - 1][gw - 1] = 0;
        auto zero = astarGrid(grid, 0, 0, gw - 1, gh - 1, hZero);
        auto manh = astarGrid(grid, 0, 0, gw - 1, gh - 1, hManhattan);
        auto gg = gridGraph(grid);
        long long opt = norm(dijkstraDense(gg, 0)[gh * gw - 1]);
        if (zero.first != opt || manh.first != opt) ++eBad;
        check("E h≡0 等于 Dijkstra", zero.first, opt);
        check("E 曼哈顿仍然最优", manh.first, opt);
        expZero += zero.second;
        expManh += manh.second;
        feed(zero.first);
        feed(manh.first);
        feed(opt);
    }
    cout << "E. A* 40 张随机网格：不一致 " << eBad << " 张；扩展格子数 h≡0 = "
         << expZero << "，曼哈顿 = " << expManh << "\n";
    feed(expZero);
    feed(expManh);

    // F. 欧拉路径：判定 / 合法性 / 字典序
    long long judgeN = 0, legalN = 0, lexN = 0, badJudge = 0, badLegal = 0, badLex = 0;
    for (int it = 0; it < 6000; ++it) {
        for (int d = 0; d < 2; ++d) {
            bool directed = d == 1;
            int n = rng.between(1, 5);
            int m = rng.between(0, 6);
            vector<pair<int, int>> edges;
            for (int i = 0; i < m; ++i)
                edges.push_back({rng.below(n), rng.below(n)});
            int st = eulerStart(n, edges, directed);
            bool exists = bruteExists(n, edges, directed);
            ++judgeN;
            if ((st >= 0) != exists) {
                ++badJudge;
                if (badJudge <= 3)
                    cout << "  !! F 判定不一致 directed=" << d << " n=" << n
                         << " m=" << m << " 判定=" << st << " 暴力=" << exists << "\n";
            }
            if (st < 0) continue;
            vector<int> path = hierholzer(n, edges, directed, st);
            ++legalN;
            if (!legalPath(st, edges, directed, path)) {
                ++badLegal;
                if (badLegal <= 3) cout << "  !! F 路径不合法 n=" << n << " m=" << m << "\n";
            }
            ++lexN;
            vector<int> best = bruteBest(n, st, edges, directed);
            if (path != best) {
                ++badLex;
                if (badLex <= 3) cout << "  !! F 不是字典序最小 n=" << n << " m=" << m << "\n";
            }
            feed(1);
            feed(static_cast<long long>(path.size()));
            for (int v : path) feed(v);
        }
    }
    cout << "F. 欧拉路径：判定 " << judgeN << " 例（不一致 " << badJudge
         << "）；合法性 " << legalN << " 例（不合法 " << badLegal
         << "）；字典序 " << lexN << " 例（不一致 " << badLex << "）\n";

    // G. SPFA：无负环图上不许误报
    long long gPairs = 0, gFalse = 0;
    for (int it = 0; it < 2000; ++it) {
        int n = rng.between(1, 8);
        int m = rng.between(0, 13);
        vector<array<int, 3>> edges;
        for (int i = 0; i < m; ++i)
            edges.push_back({rng.below(n), rng.below(n), rng.between(0, 9)});
        auto g = adjOf(n, edges);
        for (int s = 0; s < n; ++s) {
            auto sp = spfa(g, s);
            auto bf = bellmanFord(g, s);
            ++gPairs;
            if (sp.second || bf.second || nvec(sp.first) != nvec(bf.first)) ++gFalse;
        }
    }
    cout << "G. SPFA：" << gPairs << " 个组合上误报 " << gFalse << " 次\n";
    check("G SPFA 一次误报都没有", gFalse, 0);
    feed(gPairs);
    feed(gFalse);

    cout << "cpp checks: " << checks << ", failures: " << failures << "\n";
    cout << "cpp digest: " << digest << "\n";
    return failures == 0 ? 0 : 1;
}
"""

cpp_src = INCLUDES + "\n" + "\n\n".join(cpp_complete) + "\n" + CPP_HARNESS
io.open(GEN_CPP, "w", encoding="utf-8").write(cpp_src)
print(f"wrote {os.path.relpath(GEN_CPP, ROOT)} "
      f"({len(cpp_src)} bytes, 文章代码块 + harness)")

compile_cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
               "-o", GEN_BIN, GEN_CPP]
t0 = time.perf_counter()
cp = subprocess.run(compile_cmd, capture_output=True, text=True)
build_ms = (time.perf_counter() - t0) * 1e3
if cp.returncode != 0:
    print("  !! C++ 编译失败:")
    print(cp.stderr[-4000:])
    sys.exit(1)
warnings = [ln for ln in cp.stderr.splitlines() if ln.strip()]
if warnings:
    print(f"  !! 编译有 {len(warnings)} 条输出（-Werror 下不该有警告）:")
    for ln in warnings[:20]:
        print("     " + ln)
    sys.exit(1)
print(f"g++ -std=c++17 -Wall -Wextra -Werror: 零警告，{build_ms:.0f} ms")

cp = subprocess.run([GEN_BIN], capture_output=True, text=True)
if cp.returncode != 0:
    print("  !! C++ 运行失败:")
    print(cp.stdout[-3000:])
    print(cp.stderr[-3000:])
    sys.exit(1)
out = cp.stdout
print(out.rstrip())

m = re.search(r"^cpp digest: (\d+)$", out, re.M)
if not m:
    print("  !! 没找到 C++ 报出来的 digest")
    sys.exit(1)
cpp_digest = int(m.group(1))
m = re.search(r"^cpp checks: (\d+), failures: (\d+)$", out, re.M)
cpp_checks, cpp_failures = int(m.group(1)), int(m.group(2))
check("C++ 侧没有失败项", cpp_failures, 0)

# --------------------------------------------------------------------------
# 7. verdict
# --------------------------------------------------------------------------
for f in fails:
    print(f"  !! {f}")
print()
print(f"文章里的完整实现都跑过了：python {len(py_complete)} 块、"
      f"cpp {len(cpp_complete)} 块；示例片段 {len(py_frag)}+{len(cpp_frag)} 块"
      f"（只过语法检查，不含算法）")
print(f"python checks: {checks}, failures: {len(fails)}")
print(f"cpp    checks: {cpp_checks}(+{checks - cpp_checks} 语言无关项)")
print(f"digest: python {py_digest} / cpp {cpp_digest} "
      f"{'一致' if py_digest == cpp_digest else '不一致 !!'}")
if fails or cpp_failures or py_digest != cpp_digest:
    print("CODE FAIL")
    sys.exit(1)
print("CODE OK")
