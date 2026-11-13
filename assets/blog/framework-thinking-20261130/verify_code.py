#!/usr/bin/env python3
"""Code gate for the framework-thinking post.

Same principle as the other posts' gates: the code is extracted **from the
article body**, not duplicated here.  If someone edits a snippet in the post,
this gate immediately tests the edited version instead of a stale mirror.

Two things get checked:

  1. every ```python block is exec-able and its functions behave on real inputs
  2. every ```cpp block compiles and runs, with -Wall -Wextra treated as fatal

The C++ side is stitched into one translation unit, because the post presents
related snippets as separate fences (recursive vs iterative, etc.).

Usage:
    verify_code.py [POST.md]
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SLUG = "framework-thinking"
DEFAULT_POST = REPO / "_posts" / f"2026-11-30-{SLUG}.md"

EXPECTED_PY_BLOCKS = 7
EXPECTED_CPP_BLOCKS = 7


def blocks(text: str, lang: str) -> list[str]:
    return re.findall(rf"^```{lang}\n(.*?)^```", text, re.M | re.S)


# ---------------------------------------------------------------- Python side

PY_HARNESS = r'''
# ---- harness supplied by verify_code.py (mirrors the post's type usage) ----
class ListNode:
    def __init__(self, val=0, nxt=None):
        self.val, self.next = val, nxt


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


COLLECTED = []


def visit(x):
    COLLECTED.append(x)


def collect(fn, *a, **kw):
    del COLLECTED[:]
    fn(*a, **kw)
    return list(COLLECTED)
'''

PY_CHECKS = r'''
# ============================ behavioural checks ============================
def mk_tree(vals):
    """Build a tree from a level-order list; None means 'no node'."""
    if not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    q, i = [root], 1
    while q and i < len(vals):
        node = q.pop(0)
        if i < len(vals) and vals[i] is not None:
            node.left = TreeNode(vals[i]); q.append(node.left)
        i += 1
        if i < len(vals) and vals[i] is not None:
            node.right = TreeNode(vals[i]); q.append(node.right)
        i += 1
    return root


def mk_list(vals):
    dummy = ListNode(0)
    p = dummy
    for v in vals:
        p.next = ListNode(v); p = p.next
    return dummy.next


FAILS = []


def eq(name, got, want):
    if got != want:
        FAILS.append(f"{name}: got {got!r}, want {want!r}") 
    else:
        print(f"  ok  {name}")


# --- section 3.1: the four traversals are genuinely different structures ----
eq("traverse_array", collect(traverse_array, [3, 1, 4, 1, 5]), [3, 1, 4, 1, 5])
eq("traverse_linked_list", collect(traverse_linked_list, mk_list([7, 8, 9])), [7, 8, 9])
eq("traverse_array empty", collect(traverse_array, []), [])
eq("traverse_linked_list None", collect(traverse_linked_list, None), [])

t = mk_tree([5, 3, 8, None, 4])
eq("traverse_tree preorder", collect(traverse_tree, t), [5, 3, 4, 8])
eq("traverse_tree None", collect(traverse_tree, None), [])

# --- section 3.1: graph traversal handles cycles and disconnected parts -----
g = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}
got = sorted(collect(traverse_graph, g, 0))
eq("traverse_graph visits each node once", got, [0, 1, 2, 3])

g2 = {0: [1], 1: [0], 2: [3], 3: [2]}
eq("traverse_graph stays in its component", sorted(collect(traverse_graph, g2, 0)), [0, 1])
eq("traverse_graph from 2", sorted(collect(traverse_graph, g2, 2)), [2, 3])

# a self-loop must not hang: this is the bug the post warns about
eq("traverse_graph self-loop", collect(traverse_graph, {0: [0]}, 0), [0])

# --- section 3.2: the unified skeleton reproduces the specific ones ---------
# same tree, expressed through the skeleton
kids_tree = {}
for _v in [5, 3, 8, 4]:
    kids_tree[_v] = []
kids_tree[5] = [3, 8]; kids_tree[3] = [4]
eq("traverse_unified as tree preorder",
   collect(traverse_unified, 5, lambda n: kids_tree[n], lambda n: False)[:1], [5])
eq("traverse_unified as tree (set)",
   sorted(collect(traverse_unified, 5, lambda n: kids_tree[n], lambda n: False)),
   [3, 4, 5, 8])
eq("traverse_unified as graph",
   sorted(collect(traverse_unified, 0, lambda n: g[n], lambda n: False)),
   [0, 1, 2, 3])
# should_skip is honoured.  Compare as a SET: the skeleton is an explicit
# stack, so the visit order is LIFO and deliberately not specified.  Asserting
# an exact sequence here would be asserting the traversal order, which the post
# never promises (and which differs between the Python and C++ versions).
eq("traverse_unified honours should_skip",
   sorted(collect(traverse_unified, 0, lambda n: g[n], lambda n: n == 3)), [0, 1, 2])
eq("traverse_unified no duplicates with a diamond",
   len(collect(traverse_unified, 0, lambda n: g[n], lambda n: False)), 4)

# --- section 4.2: backtracking enumerates without omission ------------------
def is_solution(path):
    return len(path) == 3


def is_valid(path, c):
    return c not in path


def next_choices(choices, c):
    return choices


res = []
backtrack([], [1, 2, 3], res)
eq("backtrack permutations of 3", sorted(tuple(p) for p in res),
   sorted(set(__import__("itertools").permutations([1, 2, 3]))))
eq("backtrack result is not aliased", all(len(p) == 3 for p in res), True)

# the actual bug the post calls out: forgetting to copy path
bad = []
def backtrack_bad(path, choices, result):
    if len(path) == 3:
        result.append(path)          # no [:] -- the bug
        return
    for c in choices:
        if c in path: continue
        path.append(c); backtrack_bad(path, choices, result); path.pop()
backtrack_bad([], [1, 2, 3], bad)
eq("without [:] the answers collapse to empty", [len(p) for p in bad], [0, 0, 0, 0, 0, 0])

# --- section 5.1: the three positions really do order differently ----------
eq("traverse root=None", collect(traverse, None), [])

# --- section 5.2: decomposition trusts the recursion -----------------------
eq("max_depth of [5,3,8,None,4]", max_depth(mk_tree([5, 3, 8, None, 4])), 3)
eq("max_depth of None", max_depth(None), 0)
eq("max_depth single node", max_depth(mk_tree([1])), 1)
eq("max_depth left-chain", max_depth(mk_tree([1, 2, None, 3])), 3)
eq("max_depth perfect tree", max_depth(mk_tree([1, 2, 3, 4, 5, 6, 7])), 3)

# --- section 6: the routing helper returns a framework for every combo -----
eq("route linear", route(True, False, False), "双指针 / 滑动窗口 / 前缀和 / 二分")
eq("route non-linear, all solutions", route(False, True, False), "回溯")
eq("route non-linear, optimal, overlapping", route(False, False, True), "DP")
eq("route non-linear, optimal, no overlap", route(False, False, False), "BFS/DFS 搜索")

# --- cross-check: the post's recursion vs an independent implementation -----
# The post shows the iterative C++ version as "same result, longer code".  The
# Python side of the post doesn't repeat it (that would be noise), so the
# harness supplies its own iterative reference.  If the post's recursion and
# this reference ever disagree, one of them is wrong.
def max_depth_iter_ref(root):
    if root is None:
        return 0
    best = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        best = max(best, depth)
        if node.left:
            stack.append((node.left, depth + 1))
        if node.right:
            stack.append((node.right, depth + 1))
    return best


for vals in ([1], [1, 2], [1, 2, None, 3], [1, 2, 3, 4, 5, 6, 7],
             [5, 3, 8, None, 4], [1, None, 2, None, 3]):
    tr = mk_tree(vals)
    rec = max_depth(tr)
    it = max_depth_iter_ref(tr)
    eq(f"max_depth == iterative reference on {vals}", rec, it)

if FAILS:
    print("\n  PYTHON FAILURES:")
    for f in FAILS:
        print("   - " + f)
    raise SystemExit(1)
print(f"\n  python checks : all pass")
'''


def run_python(text: str) -> int:
    py = blocks(text, "python")
    print(f"  python blocks : {len(py)}  (expect {EXPECTED_PY_BLOCKS})")
    if len(py) != EXPECTED_PY_BLOCKS:
        print(f"  python block count changed: {len(py)} != {EXPECTED_PY_BLOCKS}")
        return 1
    src = PY_HARNESS + "\n\n".join(py) + "\n" + PY_CHECKS
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(src)
        path = fh.name
    r = subprocess.run([sys.executable, path], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    print("  " + out.replace("\n", "\n  "))
    return r.returncode


# ------------------------------------------------------------------- C++ side

CPP_HARNESS_HEAD = r'''
#include <algorithm>
#include <functional>
#include <iostream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

struct ListNode {
    int val;
    ListNode* next;
    explicit ListNode(int v = 0, ListNode* n = nullptr) : val(v), next(n) {}
};

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    explicit TreeNode(int v = 0, TreeNode* l = nullptr, TreeNode* r = nullptr)
        : val(v), left(l), right(r) {}
};

static std::vector<int> GATHERED;
static void visit(int x) { GATHERED.push_back(x); }

static int g_failures = 0;
static void eq(const std::string& name, const std::vector<int>& got,
               const std::vector<int>& want) {
    if (got == want) { std::cout << "  ok  " << name << "\n"; return; }
    ++g_failures;
    std::cout << "  FAIL " << name << "  got [";
    for (std::size_t i = 0; i < got.size(); ++i) std::cout << (i ? "," : "") << got[i];
    std::cout << "] want [";
    for (std::size_t i = 0; i < want.size(); ++i) std::cout << (i ? "," : "") << want[i];
    std::cout << "]\n";
}
static void eqInt(const std::string& name, int got, int want) {
    if (got == want) { std::cout << "  ok  " << name << "\n"; return; }
    ++g_failures;
    std::cout << "  FAIL " << name << "  got " << got << " want " << want << "\n";
}
'''

CPP_MAIN = r'''
// ============================ behavioural checks ============================
static TreeNode* mkTree(const std::vector<int>& v, int i = 0) {
    if (i >= (int)v.size() || v[i] == -1) return nullptr;
    TreeNode* n = new TreeNode(v[i]);
    n->left  = mkTree(v, 2 * i + 1);
    n->right = mkTree(v, 2 * i + 2);
    return n;
}
static ListNode* mkList(const std::vector<int>& v) {
    ListNode dummy;
    ListNode* p = &dummy;
    for (int x : v) { p->next = new ListNode(x); p = p->next; }
    return dummy.next;
}

int main() {
    // --- 3.1 array / linked list ---
    GATHERED.clear(); { std::vector<int> a{3,1,4,1,5}; traverseArray(a); }
    eq("traverseArray", GATHERED, {3,1,4,1,5});
    GATHERED.clear(); traverseLinkedList(mkList({7,8,9}));
    eq("traverseLinkedList", GATHERED, {7,8,9});
    GATHERED.clear(); traverseLinkedList(nullptr);
    eq("traverseLinkedList nullptr", GATHERED, {});

    // --- 3.1 tree preorder ---
    TreeNode* t = mkTree({5,3,8,-1,4});      // 5 / (3,8) / (-,4)
    GATHERED.clear(); traverseTree(t);
    eq("traverseTree preorder", GATHERED, {5,3,4,8});
    GATHERED.clear(); traverseTree(nullptr);
    eq("traverseTree nullptr", GATHERED, {});

    // --- 3.1 graph, incl. a self-loop that must not hang ---
    std::vector<std::vector<int>> g{{1,2},{0,3},{0,3},{1,2}};
    std::vector<bool> seen(g.size(), false);
    GATHERED.clear(); traverseGraph(g, 0, seen);
    { std::vector<int> got = GATHERED; std::sort(got.begin(), got.end());
      eq("traverseGraph each node once", got, {0,1,2,3}); }
    std::vector<std::vector<int>> selfLoop{{0}};
    std::vector<bool> s2(1, false);
    GATHERED.clear(); traverseGraph(selfLoop, 0, s2);
    eq("traverseGraph self-loop", GATHERED, {0});

    // --- 3.2 unified skeleton over the same graph ---
    GATHERED.clear();
    traverseUnified(0,
        [&](int n) { return g[n]; },
        [](int) { return false; });
    { std::vector<int> got = GATHERED; std::sort(got.begin(), got.end());
      eq("traverseUnified as graph", got, {0,1,2,3}); }
    GATHERED.clear();
    traverseUnified(0, [&](int n) { return g[n]; }, [](int n) { return n == 3; });
    { std::vector<int> got = GATHERED; std::sort(got.begin(), got.end());
      eq("traverseUnified honours shouldSkip", got, {0,1,2}); }

    // --- 3.3 recursive vs iterative inorder must agree ---
    std::vector<int> rec, it;
    inorderRec(t, rec);
    it = inorderIter(t);
    eq("inorderRec == inorderIter", rec, it);
    eq("inorder on 5/(3,8)/(-,4)", rec, {3,4,5,8});

    // --- 4.2 backtracking: no omissions ---
    { std::vector<int> path; std::vector<std::vector<int>> res;
      backtrack(path, res, 3);
      eqInt("backtrack permutations of 3", (int)res.size(), 6);
      bool allLen3 = true;
      for (auto& p : res) if (p.size() != 3) allLen3 = false;
      eqInt("backtrack results not aliased", allLen3 ? 1 : 0, 1); }

    // --- 5.2 decomposition, and its iterative twin ---
    eqInt("maxDepthRec on 5/(3,8)/(-,4)", maxDepthRec(t), 3);
    eqInt("maxDepthIter on same tree", maxDepthIter(t), 3);
    eqInt("maxDepthRec nullptr", maxDepthRec(nullptr), 0);
    eqInt("maxDepthIter nullptr", maxDepthIter(nullptr), 0);
    TreeNode* chain = mkTree({1,2,-1,3});
    eqInt("maxDepthRec left chain", maxDepthRec(chain), 3);
    eqInt("maxDepthIter left chain", maxDepthIter(chain), 3);
    TreeNode* perfect = mkTree({1,2,3,4,5,6,7});
    eqInt("maxDepthRec perfect", maxDepthRec(perfect), 3);
    eqInt("maxDepthIter perfect", maxDepthIter(perfect), 3);

    // --- 6 routing helper covers every branch ---
    eqInt("route linear", (int)route(true, false, false), (int)Framework::TwoPointers);
    eqInt("route all solutions", (int)route(false, true, false), (int)Framework::Backtracking);
    eqInt("route overlapping", (int)route(false, false, true), (int)Framework::DynamicProgramming);
    eqInt("route plain search", (int)route(false, false, false), (int)Framework::Search);

    if (g_failures) { std::cout << "\n  CPP FAILURES: " << g_failures << "\n"; return 1; }
    std::cout << "\n  cpp checks    : all pass\n";
    return 0;
}
'''


def run_cpp(text: str) -> int:
    cpp = blocks(text, "cpp")
    print(f"  cpp blocks    : {len(cpp)}  (expect {EXPECTED_CPP_BLOCKS})")
    if len(cpp) != EXPECTED_CPP_BLOCKS:
        print(f"  cpp block count changed: {len(cpp)} != {EXPECTED_CPP_BLOCKS}")
        return 1
    src = CPP_HARNESS_HEAD + "\n\n".join(cpp) + "\n" + CPP_MAIN
    with tempfile.TemporaryDirectory() as td:
        cpp_path = Path(td) / "t.cpp"
        cpp_path.write_text(src, encoding="utf-8")
        exe = Path(td) / "t"
        c = subprocess.run(
            ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
             "-o", str(exe), str(cpp_path)],
            capture_output=True, text=True)
        if c.returncode != 0:
            print("  cpp compile FAILED (warnings are errors here):")
            print("  " + (c.stdout + c.stderr).strip().replace("\n", "\n  "))
            return 1
        print("  cpp compile   : clean  (g++ -std=c++17 -Wall -Wextra -Werror -O1)")
        r = subprocess.run([str(exe)], capture_output=True, text=True)
        print("  " + (r.stdout + r.stderr).strip().replace("\n", "\n  "))
        return r.returncode


def main() -> int:
    post = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_POST
    text = post.read_text(encoding="utf-8")
    print(f"  post          : {post.name}")
    # the javas note: this series never ships Java
    java = blocks(text, "java")
    if java:
        print(f"  FAIL: {len(java)} java block(s) — this series is Python 3 + C++ only")
        return 1
    rc_py = run_python(text)
    rc_cpp = run_cpp(text)
    if rc_py or rc_cpp:
        print("\n  CODE FAIL")
        return 1
    print("\n  CODE OK — every snippet in the article runs in both languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
