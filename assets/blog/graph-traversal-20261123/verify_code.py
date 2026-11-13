#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code gate for _posts/2026-11-23-graph-traversal.md.

What it does:

1. Pulls every ```python and ```cpp fence out of the post and asserts the
   counts (12 + 12) and the order (they alternate).
2. compile()s every Python block (syntax), then exec()s all of them in one
   namespace -- the blocks reference each other, so they must all be live at
   once.
3. Runs a deterministic suite of hand-computed cases against the Python side:
   空图 / 单点 / 自环 / 不连通 / 有环 / 无环 / 二分图 / 冗余连接 / 等式方程,
   plus the DFS-vs-BFS orders drawn in the figures.
4. Runs randomized cross-checks in Python against independent brute force:
   UnionFind-vs-BFS connectivity, cycle detection vs transitive closure,
   bipartite vs exhaustive 2-colouring, 684 vs incremental BFS, 990 vs
   exhaustive assignment.
5. Emits the very same randomized cases as C++ literals into a generated
   .cpp (inside this directory), concatenates the 12 C++ blocks with a
   harness, compiles it with `g++ -std=c++17 -Wall -Wextra -Werror` and requires
   ZERO warnings, runs it, and compares a 64-bit digest of every result
   against the digest Python computed.  Same cases, two languages.

Run:  python3 assets/blog/graph-traversal-20261123/verify_code.py
"""

import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
POST = os.path.join(ROOT, "_posts", "2026-11-23-graph-traversal.md")
GEN_CPP = os.path.join(HERE, "_generated_graph_traversal_test.cpp")
# 编出来的二进制放临时目录：assets/ 会被 Jekyll 原样发布，不该进去
GEN_BIN = os.path.join(tempfile.gettempdir(), "graph_traversal_test")
SEED = 20261123

EXPECT_PY, EXPECT_CPP = 12, 12

failures = []
checks = 0


def check(name, got, want):
    global checks
    checks += 1
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


# ------------------------------------------------------------------ extract
def extract():
    src = open(POST, encoding="utf-8").read()
    blocks = re.findall(r"^```(python|cpp)[ \t]*\n(.*?)^```", src, re.M | re.S)
    langs = [l for l, _ in blocks]
    py = [c for l, c in blocks if l == "python"]
    cpp = [c for l, c in blocks if l == "cpp"]
    print(f"  post          : {os.path.basename(POST)}")
    print(f"  code fences   : {len(blocks)} (python {len(py)}, cpp {len(cpp)})")
    if len(py) != EXPECT_PY or len(cpp) != EXPECT_CPP:
        failures.append(f"fence counts: python {len(py)}/{EXPECT_PY}, "
                        f"cpp {len(cpp)}/{EXPECT_CPP}")
    if langs != ["python", "cpp"] * EXPECT_PY:
        failures.append("fences do not alternate python/cpp from the top")
    return py, cpp


# ------------------------------------------------------------------- digest
MASK = (1 << 64) - 1


class Digest:
    """FNV-1a over 64 bits; C++ mirrors this exactly."""

    def __init__(self):
        self.h = 1469598103934665603

    def mix(self, v):
        self.h ^= (v & MASK)
        self.h = (self.h * 1099511628211) & MASK

    def mix_vec(self, xs):
        self.mix(len(xs))
        for x in xs:
            self.mix(x)


# ------------------------------------------------------- brute-force oracles
def brute_components(n, pairs):
    adj = [[] for _ in range(n)]
    for u, v in pairs:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n
    comps = 0
    for s in range(n):
        if seen[s]:
            continue
        comps += 1
        seen[s] = True
        stack = [s]
        while stack:
            u = stack.pop()
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True
                    stack.append(w)
    return comps


def brute_reach(n, pairs, symmetric=False):
    """Transitive closure by repeated relaxation -- no DFS, no colours."""
    reach = [[False] * n for _ in range(n)]
    for u, v in pairs:
        reach[u][v] = True
        if symmetric:                      # 无向边 = 两个方向都有
            reach[v][u] = True
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                row_i, row_k = reach[i], reach[k]
                for j in range(n):
                    if row_k[j]:
                        row_i[j] = True
    return reach


def brute_has_cycle(n, dpairs):
    reach = brute_reach(n, dpairs)
    return any(reach[i][i] for i in range(n))


def brute_bipartite(n, pairs):
    """Exhaustive 2-colouring; independent of the BFS colouring code."""
    adj = [[] for _ in range(n)]
    for u, v in pairs:
        adj[u].append(v)
        adj[v].append(u)
    for mask in range(1 << n):
        ok = True
        for u in range(n):
            for w in adj[u]:
                if ((mask >> u) & 1) == ((mask >> w) & 1):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return True
    return False


def brute_redundant(edges):
    """684 by incremental BFS: the first edge joining two already-connected
    nodes is the redundant one."""
    n = len(edges)
    adj = [[] for _ in range(n + 1)]

    def connected(a, b):
        seen = [False] * (n + 1)
        seen[a] = True
        stack = [a]
        while stack:
            u = stack.pop()
            if u == b:
                return True
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True
                    stack.append(w)
        return False

    for u, v in edges:
        if connected(u, v):
            return [u, v]
        adj[u].append(v)
        adj[v].append(u)
    return []


def brute_equations(eqs):
    """990 by exhaustive assignment over the (at most 3) variables used."""
    names = sorted({e[0] for e in eqs} | {e[3] for e in eqs})
    idx = {c: i for i, c in enumerate(names)}
    for mask in range(1 << len(names)):
        ok = True
        for e in eqs:
            same = ((mask >> idx[e[0]]) & 1) == ((mask >> idx[e[3]]) & 1)
            if (e[1] == "=") != same:
                ok = False
                break
        if ok:
            return True
    return False


# ------------------------------------------------------------- random cases
def graph_cases(count=40):
    rnd = random.Random(SEED)
    out = []
    for _ in range(count):
        n = rnd.randint(0, 8)
        upairs = []
        if n:
            for _ in range(rnd.randint(0, 11)):
                u, v = rnd.randrange(n), rnd.randrange(n)
                if u != v:                     # 简单图: 不要自环
                    upairs.append((u, v))
        dpairs = []
        if n:
            for _ in range(rnd.randint(0, 9)):
                dpairs.append((rnd.randrange(n), rnd.randrange(n)))
        out.append((n, upairs, dpairs))
    return out


def rc_cases(count=25):
    rnd = random.Random(SEED + 1)
    out = []
    for _ in range(count):
        n = rnd.randint(3, 7)
        perm = list(range(1, n + 1))
        rnd.shuffle(perm)
        tree = [(perm[i], perm[i + 1]) for i in range(n - 1)]
        tset = {tuple(sorted(e)) for e in tree}
        cand = [(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1)
                if (u, v) not in tset]
        extra = rnd.choice(cand)
        out.append(tree + [extra])
    return out


def eq_cases(count=30):
    rnd = random.Random(SEED + 2)
    out = []
    for _ in range(count):
        k = rnd.randint(1, 5)
        eqs = []
        for _ in range(k):
            a = rnd.choice("abc")
            b = rnd.choice("abc")
            op = rnd.choice("=!")
            eqs.append(f"{a}{op}{op}{b}")
        out.append(eqs)
    return out


# ------------------------------------------------------- deterministic suite
def deterministic(ns, cases_g, cases_rc, cases_eq):
    """Hand-computed expectations, asserted on the Python side now and
    re-asserted on the C++ side later from the same table."""
    build_graph = ns["build_graph"]
    dfs = ns["dfs"]
    dfs_iterative = ns["dfs_iterative"]
    bfs_levels = ns["bfs_levels"]
    has_cycle_directed = ns["has_cycle_directed"]
    topo_sort_dfs = ns["topo_sort_dfs"]
    topo_sort_kahn = ns["topo_sort_kahn"]
    is_bipartite = ns["is_bipartite"]
    UnionFind = ns["UnionFind"]
    count_components = ns["count_components"]
    find_redundant_connection = ns["find_redundant_connection"]
    equations_possible = ns["equations_possible"]

    def ug(n, pairs):
        return build_graph(n, [[u, v] for u, v in pairs], False)

    def dg(n, pairs):
        return build_graph(n, [[u, v] for u, v in pairs], True)

    # 建图本身
    check("建图: 无向带权", build_graph(3, [[0, 1, 7]], False),
          [[(1, 7)], [(0, 7)], []])
    check("建图: 有向只加一次", build_graph(2, [[0, 1, 5]], True),
          [[(1, 5)], []])
    check("建图: 缺权重默认 1", build_graph(2, [[0, 1]], False),
          [[(1, 1)], [(0, 1)]])
    check("建图: 空图", build_graph(0, [], False), [])

    # A. 空图
    check("空图: 分量数", count_components(0, []), 0)
    check("空图: DFS 拓扑", topo_sort_dfs(dg(0, [])), [])
    check("空图: Kahn 拓扑", topo_sort_kahn(dg(0, [])), [])
    check("空图: 二分图", is_bipartite(ug(0, [])), True)
    check("空图: 无环", has_cycle_directed(dg(0, [])), False)

    # B. 单点
    check("单点: 分量数", count_components(1, []), 1)
    check("单点: BFS 距离", bfs_levels(ug(1, []), 0), [0])
    check("单点: DFS 拓扑", topo_sort_dfs(dg(1, [])), [0])
    check("单点: Kahn 拓扑", topo_sort_kahn(dg(1, [])), [0])
    check("单点: 二分图", is_bipartite(ug(1, [])), True)
    check("单点: 无环", has_cycle_directed(dg(1, [])), False)

    # C. 自环
    check("自环: 有向图判环", has_cycle_directed(dg(1, [(0, 0)])), True)
    check("自环: DFS 拓扑不存在", topo_sort_dfs(dg(1, [(0, 0)])), [])
    check("自环: Kahn 拓扑不存在", topo_sort_kahn(dg(1, [(0, 0)])), [])
    check("自环: 无向自环不是二分图", is_bipartite(ug(1, [(0, 0)])), False)
    check("自环: 无向自环不影响分量数", count_components(1, [(0, 0)]), 1)
    uf_self = UnionFind(1)
    check("自环: union(x,x) 返回 false", uf_self.union(0, 0), False)
    check("自环: union(x,x) 后分量数不变", uf_self.count, 1)

    # D. 不连通
    check("不连通: 4 点 1 边 -> 3 个分量", count_components(4, [(0, 1)]), 3)
    check("不连通: BFS 到不了的点是 -1",
          bfs_levels(ug(4, [(0, 1)]), 0), [0, 1, -1, -1])
    check("不连通: 两个二点分量仍在同一张图里是二分图",
          is_bipartite(ug(4, [(0, 1), (2, 3)])), True)
    check("不连通: 两条边两个分量", count_components(4, [(0, 1), (2, 3)]), 2)
    check("不连通: 判环也要扫所有起点",
          has_cycle_directed(dg(4, [(2, 3), (3, 2)])), True)

    # E. 有环 / 无环 + 两种拓扑排序
    dag4 = [(0, 1), (0, 2), (1, 3), (2, 3)]
    check("无环: has_cycle 为假", has_cycle_directed(dg(4, dag4)), False)
    check("无环: DFS 后序反转", topo_sort_dfs(dg(4, dag4)), [0, 2, 1, 3])
    check("无环: Kahn 出队顺序", topo_sort_kahn(dg(4, dag4)), [0, 1, 2, 3])
    cyc3 = [(0, 1), (1, 2), (2, 0)]
    check("有环: has_cycle 为真", has_cycle_directed(dg(3, cyc3)), True)
    check("有环: DFS 拓扑返回空", topo_sort_dfs(dg(3, cyc3)), [])
    check("有环: Kahn 拓扑返回空", topo_sort_kahn(dg(3, cyc3)), [])
    check("链: 两种拓扑都给 0 1 2", topo_sort_dfs(dg(3, [(0, 1), (1, 2)])),
          [0, 1, 2])
    check("链: Kahn 也给 0 1 2", topo_sort_kahn(dg(3, [(0, 1), (1, 2)])),
          [0, 1, 2])
    check("无环但入度不唯一: Kahn 仍是合法序",
          topo_sort_kahn(dg(3, [(0, 1), (0, 2)])), [0, 1, 2])

    # F. 二分图 (785 的两个例子)
    e1 = [(0, 1), (0, 2), (0, 3), (1, 2), (2, 3)]
    e2 = [(0, 1), (0, 3), (1, 2), (2, 3)]
    check("二分图: 785 例 1 是奇环", is_bipartite(ug(4, e1)), False)
    check("二分图: 785 例 2 是偶环", is_bipartite(ug(4, e2)), True)
    check("二分图: 三角形不是", is_bipartite(ug(3, [(0, 1), (1, 2), (2, 0)])),
          False)
    check("二分图: 四边形是", is_bipartite(ug(4, [(0, 1), (1, 2), (2, 3),
                                                  (3, 0)])), True)

    # G. 冗余连接 (684)
    check("冗余连接: 例 1", find_redundant_connection([[1, 2], [1, 3], [2, 3]]),
          [2, 3])
    check("冗余连接: 例 2",
          find_redundant_connection([[1, 2], [2, 3], [3, 4], [1, 4], [1, 5]]),
          [1, 4])

    # H. 等式方程 (990)
    check("等式方程: a==b, b!=a", equations_possible(["a==b", "b!=a"]), False)
    check("等式方程: b==a, a==b", equations_possible(["b==a", "a==b"]), True)
    check("等式方程: 传递链成立",
          equations_possible(["a==b", "b==c", "a==c"]), True)
    check("等式方程: 传递链矛盾",
          equations_possible(["a==b", "b!=c", "c==a"]), False)
    check("等式方程: 空表", equations_possible([]), True)

    # I. 图 2 里画的那张图: DFS 与 BFS 的访问顺序
    g5 = ug(5, [(0, 1), (0, 2), (1, 3), (1, 4)])
    order = []
    dfs(g5, 0, [False] * 5, order)
    check("顺序: 递归 DFS", order, [0, 1, 3, 4, 2])
    check("顺序: 迭代 DFS 不一样", dfs_iterative(g5, 0), [0, 2, 1, 4, 3])
    check("顺序: 迭代 DFS 访问集合相同", sorted(dfs_iterative(g5, 0)),
          sorted(order))
    check("顺序: BFS 层号", bfs_levels(g5, 0), [0, 1, 1, 2, 2])
    check("顺序: 这 5 个点连通", count_components(5, [(0, 1), (0, 2), (1, 3),
                                                      (1, 4)]), 1)

    # J. 随机图: 并查集 vs 暴力 BFS / 闭包 / 穷举染色
    d = Digest()
    for i, (n, upairs, dpairs) in enumerate(cases_g):
        Ug, Dg = ug(n, upairs), dg(n, dpairs)

        comps = count_components(n, upairs)
        check(f"随机图{i}: 分量数 vs BFS", comps, brute_components(n, upairs))

        uf = UnionFind(n)
        for u, v in upairs:
            uf.union(u, v)
        bits = []
        for a in range(n):
            for b in range(a + 1, n):
                bits.append(1 if uf.connected(a, b) else 0)
        reach = brute_reach(n, upairs, symmetric=True)
        check(f"随机图{i}: connected vs 可达",
              bits, [1 if reach[a][b] else 0
                     for a in range(n) for b in range(a + 1, n)])

        cyc = has_cycle_directed(Dg)
        check(f"随机图{i}: 判环 vs 传递闭包",
              cyc, brute_has_cycle(n, dpairs))

        dord = []
        if n:
            dfs(Ug, 0, [False] * n, dord)
        iord = dfs_iterative(Ug, 0) if n else []
        bdist = bfs_levels(Ug, 0) if n else []
        if n:
            check(f"随机图{i}: 迭代 DFS 访问集合",
                  sorted(iord), sorted(dord))

        dtopo, ktopo = topo_sort_dfs(Dg), topo_sort_kahn(Dg)
        if cyc:
            check(f"随机图{i}: 有环时 DFS 拓扑为空", dtopo, [])
            check(f"随机图{i}: 有环时 Kahn 拓扑为空", ktopo, [])
        else:
            check(f"随机图{i}: DFS 拓扑是排列", sorted(dtopo),
                  list(range(n)))
            check(f"随机图{i}: Kahn 拓扑是排列", sorted(ktopo),
                  list(range(n)))
            pos = {u: i for i, u in enumerate(dtopo)}
            check(f"随机图{i}: DFS 拓扑满足所有边",
                  all(pos[u] < pos[v] for u, v in dpairs), True)
            posk = {u: i for i, u in enumerate(ktopo)}
            check(f"随机图{i}: Kahn 拓扑满足所有边",
                  all(posk[u] < posk[v] for u, v in dpairs), True)

        bi = is_bipartite(Ug)
        check(f"随机图{i}: 二分图 vs 穷举染色",
              bi, brute_bipartite(n, upairs))

        d.mix(n)
        d.mix(comps)
        for x in bits:
            d.mix(x)
        d.mix(1 if cyc else 0)
        d.mix_vec(dord)
        d.mix_vec(iord)
        d.mix_vec(bdist)
        d.mix_vec(dtopo)
        d.mix_vec(ktopo)
        d.mix(1 if bi else 0)

    # K. 随机 684
    rc_bits = []
    for i, edges in enumerate(cases_rc):
        got = find_redundant_connection([list(e) for e in edges])
        check(f"684-{i}: vs 增量 BFS", got, brute_redundant(edges))
        d.mix(got[0] if got else -1)
        d.mix(got[1] if got else -1)
        rc_bits.append(got)

    # L. 随机 990
    eq_bits = []
    for i, eqs in enumerate(cases_eq):
        got = equations_possible(eqs)
        check(f"990-{i}: vs 穷举赋值", got, brute_equations(eqs))
        d.mix(1 if got else 0)
        eq_bits.append(got)

    return d.h, cases_g, cases_rc, cases_eq


# ------------------------------------------------------------ C++ generation
CPP_PRELUDE = """// GENERATED by verify_code.py -- do not edit by hand.
#include <algorithm>
#include <array>
#include <cstdio>
#include <queue>
#include <string>
#include <utility>
#include <vector>
using namespace std;

static int g_fail = 0;

static string join(const vector<int>& v) {
    string s = "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += to_string(v[i]);
    }
    return s + "]";
}

static void expect(const string& name, long long got, long long want) {
    if (got != want) {
        printf("  FAIL %s: got %lld, want %lld\\n", name.c_str(), got, want);
        ++g_fail;
    }
}

static void expectVec(const string& name, const vector<int>& got,
                      const vector<int>& want) {
    if (got != want) {
        printf("  FAIL %s: got %s, want %s\\n", name.c_str(),
               join(got).c_str(), join(want).c_str());
        ++g_fail;
    }
}

static vector<array<int, 3>> E3(const vector<pair<int, int>>& es) {
    vector<array<int, 3>> r;
    for (const auto& e : es) r.push_back({e.first, e.second, 1});
    return r;
}

struct Digest {
    unsigned long long h = 1469598103934665603ULL;
    void mix(long long v) {
        h ^= static_cast<unsigned long long>(v);
        h *= 1099511628211ULL;
    }
    void mixVec(const vector<int>& v) {
        mix(static_cast<long long>(v.size()));
        for (int x : v) mix(x);
    }
};
"""

CPP_MAIN_HEAD = """
static vector<vector<pair<int, int>>> UG(int n,
                                         const vector<pair<int, int>>& es) {
    return buildGraph(n, E3(es), false);
}

static vector<vector<pair<int, int>>> DG(int n,
                                         const vector<pair<int, int>>& es) {
    return buildGraph(n, E3(es), true);
}

int main() {
    Digest d;
"""


def lit_vec(xs):
    return "{" + ", ".join(str(x) for x in xs) + "}"


def gen_cpp(cpp_blocks, cases_g, cases_rc, cases_eq):
    out = [CPP_PRELUDE]
    out.append("\n// ---- the 12 C++ blocks from the post, in order ----\n")
    for i, b in enumerate(cpp_blocks, 1):
        out.append(f"\n// >>> block {i}\n{b.rstrip()}\n")
    out.append(CPP_MAIN_HEAD)

    # 1. hand-computed deterministic suite, mirrored from the Python side
    def exp(name, expr, want):
        out.append(f'    expect("{name}", (long long)({expr}), {want});\n')

    def expv(name, expr, want):
        out.append(f'    expectVec("{name}", {expr}, {lit_vec(want)});\n')

    out.append("\n    // 建图本身\n")
    exp("建图: 无向带权",
        "UG(3, {{0,1}}).size() == 3 && UG(3, {{0,1}})[0][0].second == 1",
        1)
    out.append('    { auto g = buildGraph(3, {{{0,1,7}}}, false);\n'
               '      expect("建图: 无向带权 (邻居)", g[0][0].first, 1);\n'
               '      expect("建图: 无向带权 (权重)", g[0][0].second, 7);\n'
               '      expect("建图: 无向带权 (反向也有)", g[1][0].first, 0);\n'
               '      expect("建图: 无向带权 (2 空)", (long long)g[2].size(), 0); }\n')
    out.append('    { auto g = buildGraph(2, {{{0,1,5}}}, true);\n'
               '      expect("建图: 有向只加一次", (long long)g[0].size(), 1);\n'
               '      expect("建图: 有向反向为空", (long long)g[1].size(), 0); }\n'
               '    { auto g = buildGraph(2, {{{0,1,1}}}, false);\n'
               '      expect("建图: 缺权重默认 1", g[0][0].second, 1); }\n'
               '    { auto g = buildGraph(0, {}, false);\n'
               '      expect("建图: 空图", (long long)g.size(), 0); }\n')

    out.append("\n    // A. 空图\n")
    exp("空图: 分量数", "countComponents(0, {})", 0)
    expv("空图: DFS 拓扑", "topoSortDfs(DG(0, {}))", [])
    expv("空图: Kahn 拓扑", "topoSortKahn(DG(0, {}))", [])
    exp("空图: 二分图", "isBipartite(UG(0, {}))", 1)
    exp("空图: 无环", "hasCycleDirected(DG(0, {}))", 0)

    out.append("\n    // B. 单点\n")
    exp("单点: 分量数", "countComponents(1, {})", 1)
    expv("单点: BFS 距离", "bfsLevels(UG(1, {}), 0)", [0])
    expv("单点: DFS 拓扑", "topoSortDfs(DG(1, {}))", [0])
    expv("单点: Kahn 拓扑", "topoSortKahn(DG(1, {}))", [0])
    exp("单点: 二分图", "isBipartite(UG(1, {}))", 1)
    exp("单点: 无环", "hasCycleDirected(DG(1, {}))", 0)

    out.append("\n    // C. 自环\n")
    exp("自环: 有向图判环", "hasCycleDirected(DG(1, {{0,0}}))", 1)
    expv("自环: DFS 拓扑不存在", "topoSortDfs(DG(1, {{0,0}}))", [])
    expv("自环: Kahn 拓扑不存在", "topoSortKahn(DG(1, {{0,0}}))", [])
    exp("自环: 无向自环不是二分图", "isBipartite(UG(1, {{0,0}}))", 0)
    exp("自环: 无向自环不影响分量数", "countComponents(1, {{0,0}})", 1)
    out.append('    { UnionFind uf(1);\n'
               '      expect("自环: union(x,x) 返回 false", uf.unite(0, 0), 0);\n'
               '      expect("自环: union(x,x) 后分量数不变", uf.count(), 1); }\n')

    out.append("\n    // D. 不连通\n")
    exp("不连通: 4 点 1 边 -> 3 个分量", "countComponents(4, {{0,1}})", 3)
    expv("不连通: BFS 到不了的点是 -1", "bfsLevels(UG(4, {{0,1}}), 0)",
         [0, 1, -1, -1])
    exp("不连通: 两个二点分量仍是二分图",
        "isBipartite(UG(4, {{0,1},{2,3}}))", 1)
    exp("不连通: 两条边两个分量",
        "countComponents(4, {{0,1},{2,3}})", 2)
    exp("不连通: 判环也要扫所有起点",
        "hasCycleDirected(DG(4, {{2,3},{3,2}}))", 1)

    out.append("\n    // E. 有环 / 无环 + 两种拓扑排序\n")
    exp("无环: has_cycle 为假",
        "hasCycleDirected(DG(4, {{0,1},{0,2},{1,3},{2,3}}))", 0)
    expv("无环: DFS 后序反转",
         "topoSortDfs(DG(4, {{0,1},{0,2},{1,3},{2,3}}))", [0, 2, 1, 3])
    expv("无环: Kahn 出队顺序",
         "topoSortKahn(DG(4, {{0,1},{0,2},{1,3},{2,3}}))", [0, 1, 2, 3])
    exp("有环: has_cycle 为真",
        "hasCycleDirected(DG(3, {{0,1},{1,2},{2,0}}))", 1)
    expv("有环: DFS 拓扑返回空",
         "topoSortDfs(DG(3, {{0,1},{1,2},{2,0}}))", [])
    expv("有环: Kahn 拓扑返回空",
         "topoSortKahn(DG(3, {{0,1},{1,2},{2,0}}))", [])
    expv("链: 两种拓扑都给 0 1 2",
         "topoSortDfs(DG(3, {{0,1},{1,2}}))", [0, 1, 2])
    expv("链: Kahn 也给 0 1 2", "topoSortKahn(DG(3, {{0,1},{1,2}}))",
         [0, 1, 2])
    expv("无环但入度不唯一: Kahn 仍是合法序",
         "topoSortKahn(DG(3, {{0,1},{0,2}}))", [0, 1, 2])

    out.append("\n    // F. 二分图\n")
    exp("二分图: 785 例 1 是奇环",
        "isBipartite(UG(4, {{0,1},{0,2},{0,3},{1,2},{2,3}}))", 0)
    exp("二分图: 785 例 2 是偶环",
        "isBipartite(UG(4, {{0,1},{0,3},{1,2},{2,3}}))", 1)
    exp("二分图: 三角形不是",
        "isBipartite(UG(3, {{0,1},{1,2},{2,0}}))", 0)
    exp("二分图: 四边形是",
        "isBipartite(UG(4, {{0,1},{1,2},{2,3},{3,0}}))", 1)

    out.append("\n    // G. 冗余连接\n")
    expv("冗余连接: 例 1",
         "findRedundantConnection({{1,2},{1,3},{2,3}})", [2, 3])
    expv("冗余连接: 例 2",
         "findRedundantConnection({{1,2},{2,3},{3,4},{1,4},{1,5}})", [1, 4])

    out.append("\n    // H. 等式方程\n")
    exp('等式方程: a==b, b!=a',
        'equationsPossible({"a==b", "b!=a"})', 0)
    exp('等式方程: b==a, a==b',
        'equationsPossible({"b==a", "a==b"})', 1)
    exp('等式方程: 传递链成立',
        'equationsPossible({"a==b", "b==c", "a==c"})', 1)
    exp('等式方程: 传递链矛盾',
        'equationsPossible({"a==b", "b!=c", "c==a"})', 0)
    exp('等式方程: 空表', 'equationsPossible({})', 1)

    out.append("\n    // I. 图 2 里画的那张图\n")
    out.append('    { vector<pair<int,int>> es = {{0,1},{0,2},{1,3},{1,4}};\n'
               '      auto g = UG(5, es);\n'
               '      vector<char> vis(5, 0); vector<int> ord;\n'
               '      dfs(g, 0, vis, ord);\n'
               '      expectVec("顺序: 递归 DFS", ord, {0,1,3,4,2});\n'
               '      expectVec("顺序: 迭代 DFS 不一样", dfsIterative(g, 0),\n'
               '                {0,2,1,4,3});\n'
               '      expectVec("顺序: BFS 层号", bfsLevels(g, 0),\n'
               '                {0,1,1,2,2});\n'
               '      expect("顺序: 这 5 个点连通", countComponents(5, es), 1); }\n')

    # 2. randomized battery, same cases as Python
    out.append("\n    // J. 随机图: 同一批用例, C++ 侧复算\n")
    for i, (n, upairs, dpairs) in enumerate(cases_g):
        out.append(f"    {{ // random graph {i}\n")
        out.append(f"      int n = {n};\n")
        out.append(f"      vector<pair<int,int>> ue = "
                   f"{lit_vec([f'{{{u},{v}}}' for u, v in upairs]) or '{}'};\n")
        out.append(f"      vector<pair<int,int>> de = "
                   f"{lit_vec([f'{{{u},{v}}}' for u, v in dpairs]) or '{}'};\n")
        out.append("      auto Ug = UG(n, ue); auto Dg = DG(n, de);\n")
        out.append("      long long comps = countComponents(n, ue);\n")
        out.append("      expect(\"随机图 分量数 >= 1\", "
                   "n == 0 ? comps == 0 : comps >= 1, 1);\n")
        out.append("      UnionFind uf(n);\n"
                   "      for (const auto& e : ue) uf.unite(e.first, e.second);\n")
        out.append("      d.mix(n); d.mix(comps);\n")
        out.append("      for (int a = 0; a < n; ++a)\n"
                   "        for (int b = a + 1; b < n; ++b)\n"
                   "          d.mix(uf.connected(a, b) ? 1 : 0);\n")
        out.append("      long long cyc = hasCycleDirected(Dg) ? 1 : 0;\n")
        out.append("      d.mix(cyc);\n")
        out.append("      vector<int> dord, iord, bdist;\n")
        out.append("      if (n) { vector<char> vis(n, 0); dfs(Ug, 0, vis, dord);\n"
                   "               iord = dfsIterative(Ug, 0);\n"
                   "               bdist = bfsLevels(Ug, 0); }\n")
        out.append("      d.mixVec(dord); d.mixVec(iord); d.mixVec(bdist);\n")
        out.append("      vector<int> dtopo = topoSortDfs(Dg);\n"
                   "      vector<int> ktopo = topoSortKahn(Dg);\n")
        out.append("      if (cyc) {\n"
                   "        expect(\"随机图: 有环时 DFS 拓扑为空\",\n"
                   "               (long long)dtopo.size(), 0);\n"
                   "        expect(\"随机图: 有环时 Kahn 拓扑为空\",\n"
                   "               (long long)ktopo.size(), 0);\n"
                   "      } else {\n"
                   "        expect(\"随机图: DFS 拓扑是排列\",\n"
                   "               (long long)dtopo.size(), n);\n"
                   "        expect(\"随机图: Kahn 拓扑是排列\",\n"
                   "               (long long)ktopo.size(), n);\n"
                   "      }\n")
        out.append("      d.mixVec(dtopo); d.mixVec(ktopo);\n")
        out.append("      d.mix(isBipartite(Ug) ? 1 : 0);\n")
        out.append("    }\n")

    out.append("\n    // K. 随机 684\n")
    for i, edges in enumerate(cases_rc):
        out.append(f"    {{ // redundant connection {i}\n")
        out.append(f"      vector<pair<int,int>> es = "
                   f"{lit_vec([f'{{{u},{v}}}' for u, v in edges])};\n")
        out.append("      vector<int> r = findRedundantConnection(es);\n")
        out.append("      d.mix(r.empty() ? -1 : r[0]);\n"
                   "      d.mix(r.empty() ? -1 : r[1]);\n")
        out.append("    }\n")

    out.append("\n    // L. 随机 990\n")
    for i, eqs in enumerate(cases_eq):
        out.append(f"    {{ // equations {i}\n")
        out.append(f"      vector<string> eq = "
                   f"{lit_vec([f'\"{e}\"' for e in eqs])};\n")
        out.append("      d.mix(equationsPossible(eq) ? 1 : 0);\n")
        out.append("    }\n")

    out.append('\n    if (g_fail) {\n'
               '        printf("CPP GATE FAILED: %d assertion(s)\\n", g_fail);\n'
               '        return 1;\n'
               '    }\n'
               '    printf("CPP GATE OK, digest %llu\\n", d.h);\n'
               '    return 0;\n'
               '}\n')
    return "".join(out)


# --------------------------------------------------------------------- main
def main():
    print("== gate 2: code ==")
    py_blocks, cpp_blocks = extract()

    print("\n-- Python: syntax --")
    for i, b in enumerate(py_blocks, 1):
        try:
            compile(b, f"<python block {i}>", "exec")
        except SyntaxError as exc:
            failures.append(f"python block {i} does not compile: {exc}")
    print(f"  {len(py_blocks)} blocks compile()d")

    print("\n-- Python: exec all blocks in one namespace --")
    ns = {}
    for i, b in enumerate(py_blocks, 1):
        try:
            exec(compile(b, f"<python block {i}>", "exec"), ns)
        except Exception as exc:                      # noqa: BLE001
            failures.append(f"python block {i} failed at import time: {exc!r}")
    print(f"  namespace now holds {len(ns)} names")

    print("\n-- Python: deterministic + randomized cross-checks --")
    cases_g, cases_rc, cases_eq = graph_cases(), rc_cases(), eq_cases()
    py_digest, _, _, _ = deterministic(ns, cases_g, cases_rc, cases_eq)
    print(f"  {checks} checks, {len(failures)} failure(s) so far")
    print(f"  python digest : {py_digest}")

    print("\n-- C++: generate + compile + run (same cases) --")
    src = gen_cpp(cpp_blocks, cases_g, cases_rc, cases_eq)
    with open(GEN_CPP, "w", encoding="utf-8") as fh:
        fh.write(src)
    print(f"  wrote {os.path.relpath(GEN_CPP, ROOT)} "
          f"({len(src.splitlines())} lines)")

    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1", "-o",
           GEN_BIN, GEN_CPP]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    warn = (proc.stderr or "").strip()
    print(f"  g++ exit={proc.returncode}, warnings/errors: "
          f"{'none' if not warn else repr(warn[:400])}")
    if proc.returncode != 0:
        failures.append("g++ failed to compile the generated test")
    elif warn:
        failures.append(f"g++ emitted warnings under -Wall -Wextra: {warn}")
    if proc.returncode == 0:
        run = subprocess.run([GEN_BIN], capture_output=True, text=True)
        print(f"  run exit={run.returncode}")
        for line in run.stdout.strip().splitlines():
            print(f"  | {line}")
        if run.returncode != 0:
            failures.append("C++ harness reported failing assertions")
        if run.stderr.strip():
            failures.append(f"C++ harness wrote to stderr: {run.stderr[:300]}")
        m = re.search(r"digest (\d+)", run.stdout)
        cpp_digest = int(m.group(1)) if m else None
        print(f"  cpp digest    : {cpp_digest}")
        if cpp_digest != py_digest:
            failures.append(f"digest mismatch: python {py_digest} vs "
                            f"C++ {cpp_digest} -- the two languages "
                            f"disagree on the same {len(cases_g)} random cases")

    print("\n== result ==")
    if failures:
        print(f"  CODE GATE FAILED: {len(failures)} problem(s)")
        for f in failures[:40]:
            print(f"    - {f}")
        return 1
    print(f"  CODE GATE OK: {checks} Python checks, C++ re-ran the same "
          f"{len(cases_g)} random graphs + {len(cases_rc)} 冗余连接 + "
          f"{len(cases_eq)} 等式方程 cases, digest {py_digest} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
