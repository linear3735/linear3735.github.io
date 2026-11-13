#!/usr/bin/env python3
"""Code gate for the binary-tree post.

    python3 assets/blog/binary-tree-20261121/verify_code.py

Design (same as the sliding-window gate, deliberately):

  * The Python and C++ blocks are **extracted from the post itself** by regex.
    There is no hand-copied mirror that can silently drift away from what the
    article actually shows.
  * Python: every block is `ast.parse`d on its own, then all blocks are exec'd
    together in one namespace.
  * C++: the post's cpp blocks are concatenated with a generated `main()` into
    build/binary_tree_generated.cpp, compiled with
    `g++ -std=c++17 -Wall -Wextra -Werror -O1`, and any compiler output at all
    is a failure.
  * Both languages run the same fixed cases and the *same* 260 randomly
    generated trees (a shared 31-bit LCG, so the shapes are identical), each
    checked against its own independent brute-force reference.
  * Finally the two sides print a canonical transcript of every result and the
    gate compares the transcripts byte for byte.  That is what actually proves
    the C++ version agrees with the Python version rather than merely "both
    compiled".
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import re
import subprocess
import sys
from pathlib import Path

REPO = Path.home() / "projects" / "linear3735.github.io"
POST = REPO / "_posts" / "2026-11-21-binary-tree.md"
BUILD = REPO / "assets" / "blog" / "binary-tree-20261121" / "build"

EXPECTED_PY = 11
EXPECTED_CPP = 11
ROUNDS = 260

PY_BLOCK = re.compile(r"```python\n(.*?)```", re.S)
CPP_BLOCK = re.compile(r"```cpp\n(.*?)```", re.S)


# --------------------------------------------------------------------------
# the Python side: appended to the post's blocks and exec'd in the same ns
# --------------------------------------------------------------------------
PY_MAIN = r'''
# ======================= test harness (not part of the post) ===============
import itertools as _it


def to_levels(root):
    """Independent LeetCode-style serializer (used for the build_tree round trip)."""
    if root is None:
        return []
    out, q = [], [root]
    while q:
        node = q.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        q.append(node.left)
        q.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def rand_val(rnd):
    rnd[0] = (rnd[0] * 1103515245 + 12345) & 0x7FFFFFFF
    return rnd[0] % 11 - 5


def random_levels(rnd):
    """A random tree shape, as a LeetCode level-order array.

    Identical logic (and identical LCG) on the C++ side, so both languages
    test the very same trees.
    """
    rnd[0] = (rnd[0] * 1103515245 + 12345) & 0x7FFFFFFF
    n = rnd[0] % 15
    if n == 0:
        return []
    val = [rand_val(rnd)]
    left = [-1]
    right = [-1]
    free = [(0, 0), (0, 1)]
    for _ in range(1, n):
        rnd[0] = (rnd[0] * 1103515245 + 12345) & 0x7FFFFFFF
        j = rnd[0] % len(free)
        pi, side = free[j]
        free[j] = free[-1]
        free.pop()
        val.append(rand_val(rnd))
        left.append(-1)
        right.append(-1)
        if side == 0:
            left[pi] = len(val) - 1
        else:
            right[pi] = len(val) - 1
        free.append((len(val) - 1, 0))
        free.append((len(val) - 1, 1))
    out, q = [], [0]
    while q:
        i = q.pop(0)
        if i == -1:
            out.append(None)
            continue
        out.append(val[i])
        q.append(left[i])
        q.append(right[i])
    while out and out[-1] is None:
        out.pop()
    return out


# ---- independent references.  These deliberately do NOT reuse the post's code.

def ref_orders(root):
    """Explicit-stack traversal, no recursion."""
    pre, ino, post = [], [], []
    st = [(root, 0)] if root is not None else []
    while st:
        node, state = st.pop()
        if state == 0:
            pre.append(node.val)
            st.append((node, 1))
            if node.left is not None:
                st.append((node.left, 0))
        elif state == 1:
            ino.append(node.val)
            st.append((node, 2))
            if node.right is not None:
                st.append((node.right, 0))
        else:
            post.append(node.val)
    return pre, ino, post


def ref_levels(root):
    """Level-by-level lists, built by swapping whole layers."""
    out = []
    cur = [root] if root is not None else []
    while cur:
        out.append([n.val for n in cur])
        cur = [c for n in cur for c in (n.left, n.right) if c is not None]
    return out


def ref_max_depth(root):
    best, st = 0, [(root, 1)] if root is not None else []
    while st:
        node, d = st.pop()
        best = max(best, d)
        if node.left is not None:
            st.append((node.left, d + 1))
        if node.right is not None:
            st.append((node.right, d + 1))
    return best


def ref_adj(root):
    adj = {}
    st = [root] if root is not None else []
    while st:
        n = st.pop()
        adj.setdefault(n, [])
        for c in (n.left, n.right):
            if c is not None:
                adj[n].append(c)
                adj.setdefault(c, []).append(n)
                st.append(c)
    return adj


def ref_diameter(root):
    """All-pairs BFS on the undirected tree; max distance in edges."""
    if root is None:
        return 0
    adj = ref_adj(root)
    best = 0
    for src in list(adj):
        dist = {src: 0}
        q = [src]
        for n in q:
            for m in adj[n]:
                if m not in dist:
                    dist[m] = dist[n] + 1
                    best = max(best, dist[m])
                    q.append(m)
    return best


def ref_height(n):
    if n is None:
        return 0
    return 1 + max(ref_height(n.left), ref_height(n.right))


def ref_balanced(root):
    """Definition, applied to every node (the naive O(N^2) reading)."""
    if root is None:
        return True
    if abs(ref_height(root.left) - ref_height(root.right)) > 1:
        return False
    return ref_balanced(root.left) and ref_balanced(root.right)


def ref_max_path_sum(root):
    """Max sum over every simple path, by brute force from every start node."""
    if root is None:
        return None
    adj = ref_adj(root)
    best = None
    for src in list(adj):
        st = [(src, None, src.val)]
        while st:
            n, par, acc = st.pop()
            if best is None or acc > best:
                best = acc
            for m in adj[n]:
                if m is not par:
                    st.append((m, n, acc + m.val))
    return best


def ref_paths(root):
    """Root-to-leaf paths rebuilt from a parent map, then sorted."""
    if root is None:
        return []
    parent = {root: None}
    st, leaves = [root], []
    while st:
        n = st.pop()
        if n.left is None and n.right is None:
            leaves.append(n)
        for c in (n.left, n.right):
            if c is not None:
                parent[c] = n
                st.append(c)
    out = []
    for leaf in leaves:
        vals, n = [], leaf
        while n is not None:
            vals.append(n.val)
            n = parent[n]
        out.append("->".join(str(v) for v in reversed(vals)))
    out.sort()
    return out


# ---- canonical serialisation, byte-identical with the C++ side ------------

def fmt_ints(xs):
    return ",".join(str(v) for v in xs)


def fmt_levels(ls):
    return ";".join(fmt_ints(r) for r in ls)


def fmt_strs(ss):
    return "|".join(ss)


lines = []
problems = []


def check(tag, got, want):
    if got != want:
        problems.append(f"{tag}: got {got!r} want {want!r}")


def run_case(idx, vals, fixed_expect=None):
    root = build_tree(vals)
    back = to_levels(root)
    check(f"roundtrip#{idx}", back, vals)

    pre, ino, post = ref_orders(root)
    my_pre, my_in, my_post = threeOrders(root)
    check(f"threeOrders.pre#{idx}", my_pre, pre)
    check(f"threeOrders.in#{idx}", my_in, ino)
    check(f"threeOrders.post#{idx}", my_post, post)
    check(f"preorderTraversal#{idx}", preorderTraversal(root), pre)
    check(f"preorderDivide#{idx}", preorderDivide(root), pre)

    lv = ref_levels(root)
    check(f"levelOrder#{idx}", levelOrder(root), lv)
    check(f"rightSideView#{idx}", rightSideView(root), [r[-1] for r in lv])

    md = ref_max_depth(root)
    check(f"maxDepthTraverse#{idx}", maxDepthTraverse(root), md)
    check(f"maxDepthDivide#{idx}", maxDepthDivide(root), md)

    dn = ref_diameter(root)
    check(f"diameterNaive#{idx}", diameterNaive(root), dn)
    check(f"diameterOfBinaryTree#{idx}", diameterOfBinaryTree(root), dn)
    check(f"diameter agree#{idx}", diameterNaive(root), diameterOfBinaryTree(root))

    check(f"isBalanced#{idx}", isBalanced(root), ref_balanced(root))

    if root is None:
        mps = "NA"
    else:
        mps = ref_max_path_sum(root)
        check(f"maxPathSum#{idx}", maxPathSum(root), mps)
    pm = ref_paths(root)
    check(f"binaryTreePaths#{idx}", sorted(binaryTreePaths(root)), pm)

    if fixed_expect is not None:
        for key, want in fixed_expect.items():
            got = {
                "pre": preorderTraversal(root),
                "in": threeOrders(root)[1],
                "post": threeOrders(root)[2],
                "lvl": levelOrder(root),
                "right": rightSideView(root),
                "depth": maxDepthDivide(root),
                "diam": diameterOfBinaryTree(root),
                "bal": isBalanced(root),
                "mps": None if root is None else maxPathSum(root),
                "paths": binaryTreePaths(root),
            }[key]
            check(f"fixed#{idx}.{key}", got, want)

    lines.append(
        f"C{idx} pre=<{fmt_ints(preorderTraversal(root))}> "
        f"in=<{fmt_ints(threeOrders(root)[1])}> "
        f"post=<{fmt_ints(threeOrders(root)[2])}> "
        f"lvl=<{fmt_levels(levelOrder(root))}> "
        f"right=<{fmt_ints(rightSideView(root))}> "
        f"mt={maxDepthTraverse(root)} md={maxDepthDivide(root)} "
        f"dn={diameterNaive(root)} do={diameterOfBinaryTree(root)} "
        f"bal={1 if isBalanced(root) else 0} mps={mps} "
        f"paths=<{fmt_strs(pm)}>"
    )


# ---- fixed cases ----------------------------------------------------------

FIXED = [
    ([], {}),
    ([7], {"pre": [7], "lvl": [[7]], "right": [7], "depth": 1, "diam": 0,
           "bal": True, "paths": ["7"]}),
    ([1, 2, 3, 4, 5, 6, 7], {"pre": [1, 2, 4, 5, 3, 6, 7],
                             "in": [4, 2, 5, 1, 6, 3, 7],
                             "post": [4, 5, 2, 6, 7, 3, 1],
                             "lvl": [[1], [2, 3], [4, 5, 6, 7]],
                             "right": [1, 3, 7], "depth": 3, "diam": 4,
                             "bal": True, "mps": 18,
                             "paths": ["1->2->4", "1->2->5", "1->3->6", "1->3->7"]}),
    ([1, 2, None, 3, None, 4], {"pre": [1, 2, 3, 4], "depth": 4, "diam": 3,
                                "bal": False, "right": [1, 2, 3, 4]}),
    ([1, None, 2, None, 3], {"pre": [1, 2, 3], "post": [3, 2, 1], "depth": 3,
                             "diam": 2, "bal": False}),
    ([1, 2, None, None, 3], {"pre": [1, 2, 3], "in": [2, 3, 1], "depth": 3,
                             "diam": 2, "bal": False}),
    ([1, 2, 3, None, None, None, 4], {"lvl": [[1], [2, 3], [4]], "right": [1, 3, 4],
                                      "bal": True, "diam": 3}),
    ([-10, 9, 20, None, None, 15, 7], {"mps": 42, "diam": 3}),
    ([-3], {"mps": -3, "diam": 0, "bal": True}),
    ([-1, -2, -3], {"mps": -1, "diam": 2}),
    # LC 110 的示例 3:节点 4 的左子树高 2、右子树高 0,差 2 —— 不平衡
    ([5, 4, 8, 11, None, 13, 4, 7, 2], {"depth": 4, "bal": False}),
    ([1, 2, 3, 4, None, None, 5], {"lvl": [[1], [2, 3], [4, 5]], "depth": 3}),
    ([0, 0, 0], {"mps": 0, "bal": True, "right": [0, 0]}),
    ([2, 1, 3], {"mps": 6, "diam": 2, "bal": True}),
    ([1, 2, None, 3, None, 4, None, 5], {"depth": 5, "diam": 4, "bal": False}),
]

for _i, (_vals, _exp) in enumerate(FIXED):
    run_case(_i, _vals, _exp)

# ---- random trees --------------------------------------------------------

_rnd = [20261121]
for _k in range(ROUNDS):
    run_case(len(FIXED) + _k, random_levels(_rnd), None)

print(f"CASES {len(lines)}")
if problems:
    print(f"FAILURES {len(problems)}")
    for _p in problems[:25]:
        print("  - " + _p)
    print("SOME CASES FAILED")
else:
    print("ALL PASS")
print("TRANSCRIPT-BEGIN")
print("\n".join(lines))
print("TRANSCRIPT-END")
'''


# --------------------------------------------------------------------------
# the C++ side
# --------------------------------------------------------------------------
CPP_MAIN = r'''
// ======================= test harness (not part of the post) ===============
#include <algorithm>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <utility>
#include <vector>

static std::vector<int> toLevels(TreeNode* root) {
    std::vector<int> out;
    if (root == nullptr) return out;
    std::vector<TreeNode*> q{root};
    for (std::size_t i = 0; i < q.size(); ++i) {
        TreeNode* node = q[i];
        if (node == nullptr) { out.push_back(NUL); continue; }
        out.push_back(node->val);
        q.push_back(node->left);
        q.push_back(node->right);
    }
    while (!out.empty() && out.back() == NUL) out.pop_back();
    return out;
}

static unsigned int g_seed = 20261121u;

static unsigned int nextRand() {
    g_seed = (g_seed * 1103515245u + 12345u) & 0x7FFFFFFFu;
    return g_seed;
}

static int randVal() { return static_cast<int>(nextRand() % 11u) - 5; }

// Same shape generator as the Python side, same LCG, so both languages test
// exactly the same trees.
static std::vector<int> randomLevels() {
    int n = static_cast<int>(nextRand() % 15u);
    if (n == 0) return {};
    std::vector<int> val{randVal()};
    std::vector<int> left{-1}, right{-1};
    std::vector<std::pair<int, int>> free_slots{{0, 0}, {0, 1}};
    for (int k = 1; k < n; ++k) {
        std::size_t j = nextRand() % free_slots.size();
        int pi = free_slots[j].first;
        int side = free_slots[j].second;
        free_slots[j] = free_slots.back();
        free_slots.pop_back();
        val.push_back(randVal());
        left.push_back(-1);
        right.push_back(-1);
        int idx = static_cast<int>(val.size()) - 1;
        if (side == 0) left[pi] = idx; else right[pi] = idx;
        free_slots.push_back({idx, 0});
        free_slots.push_back({idx, 1});
    }
    std::vector<int> out;
    std::vector<int> q{0};
    for (std::size_t i = 0; i < q.size(); ++i) {
        int idx = q[i];
        if (idx == -1) { out.push_back(NUL); continue; }
        out.push_back(val[static_cast<std::size_t>(idx)]);
        q.push_back(left[static_cast<std::size_t>(idx)]);
        q.push_back(right[static_cast<std::size_t>(idx)]);
    }
    while (!out.empty() && out.back() == NUL) out.pop_back();
    return out;
}

// ---- independent references (no reuse of the post's code) ----------------

static void refOrders(TreeNode* root, std::vector<int>& pre,
                      std::vector<int>& in, std::vector<int>& post) {
    std::vector<std::pair<TreeNode*, int>> st;
    if (root != nullptr) st.push_back({root, 0});
    while (!st.empty()) {
        TreeNode* node = st.back().first;
        int state = st.back().second;
        st.pop_back();
        if (state == 0) {
            pre.push_back(node->val);
            st.push_back({node, 1});
            if (node->left != nullptr) st.push_back({node->left, 0});
        } else if (state == 1) {
            in.push_back(node->val);
            st.push_back({node, 2});
            if (node->right != nullptr) st.push_back({node->right, 0});
        } else {
            post.push_back(node->val);
        }
    }
}

static std::vector<std::vector<int>> refLevels(TreeNode* root) {
    std::vector<std::vector<int>> out;
    std::vector<TreeNode*> cur;
    if (root != nullptr) cur.push_back(root);
    while (!cur.empty()) {
        std::vector<int> vals;
        std::vector<TreeNode*> nxt;
        for (TreeNode* n : cur) {
            vals.push_back(n->val);
            if (n->left != nullptr) nxt.push_back(n->left);
            if (n->right != nullptr) nxt.push_back(n->right);
        }
        out.push_back(vals);
        cur.swap(nxt);
    }
    return out;
}

static int refMaxDepth(TreeNode* root) {
    int best = 0;
    std::vector<std::pair<TreeNode*, int>> st;
    if (root != nullptr) st.push_back({root, 1});
    while (!st.empty()) {
        TreeNode* node = st.back().first;
        int d = st.back().second;
        st.pop_back();
        if (d > best) best = d;
        if (node->left != nullptr) st.push_back({node->left, d + 1});
        if (node->right != nullptr) st.push_back({node->right, d + 1});
    }
    return best;
}

static std::map<TreeNode*, std::vector<TreeNode*>> refAdj(TreeNode* root) {
    std::map<TreeNode*, std::vector<TreeNode*>> adj;
    std::vector<TreeNode*> st;
    if (root != nullptr) st.push_back(root);
    while (!st.empty()) {
        TreeNode* n = st.back();
        st.pop_back();
        adj[n];
        TreeNode* kids[2] = {n->left, n->right};
        for (TreeNode* c : kids) {
            if (c != nullptr) {
                adj[n].push_back(c);
                adj[c].push_back(n);
                st.push_back(c);
            }
        }
    }
    return adj;
}

static int refDiameter(TreeNode* root) {
    if (root == nullptr) return 0;
    std::map<TreeNode*, std::vector<TreeNode*>> adj = refAdj(root);
    int best = 0;
    for (auto& kv : adj) {
        std::map<TreeNode*, int> dist;
        dist[kv.first] = 0;
        std::vector<TreeNode*> q{kv.first};
        for (std::size_t i = 0; i < q.size(); ++i) {
            TreeNode* n = q[i];
            for (TreeNode* m : adj[n]) {
                if (dist.find(m) == dist.end()) {
                    dist[m] = dist[n] + 1;
                    if (dist[m] > best) best = dist[m];
                    q.push_back(m);
                }
            }
        }
    }
    return best;
}

static int refHeight(TreeNode* n) {
    if (n == nullptr) return 0;
    int l = refHeight(n->left);
    int r = refHeight(n->right);
    return 1 + (l > r ? l : r);
}

static bool refBalanced(TreeNode* root) {
    if (root == nullptr) return true;
    if (std::abs(refHeight(root->left) - refHeight(root->right)) > 1) return false;
    return refBalanced(root->left) && refBalanced(root->right);
}

static int refMaxPathSum(TreeNode* root) {
    if (root == nullptr) return 0;
    std::map<TreeNode*, std::vector<TreeNode*>> adj = refAdj(root);
    int best = INT_MIN;
    for (auto& kv : adj) {
        std::vector<std::vector<int>> st;                 // node index, parent, acc
        st.push_back({0, -1, kv.first->val});
        std::vector<TreeNode*> seen{kv.first};
        while (!st.empty()) {
            std::vector<int> cur = st.back();
            st.pop_back();
            TreeNode* n = seen[static_cast<std::size_t>(cur[0])];
            if (cur[2] > best) best = cur[2];
            for (TreeNode* m : adj[n]) {
                bool is_parent = (cur[1] >= 0 &&
                                  m == seen[static_cast<std::size_t>(cur[1])]);
                if (is_parent) continue;
                seen.push_back(m);
                st.push_back({static_cast<int>(seen.size()) - 1,
                              cur[0], cur[2] + m->val});
            }
        }
    }
    return best;
}

static void refPathsDfs(TreeNode* n, TreeNode* par,
                        std::map<TreeNode*, TreeNode*>& parent,
                        std::vector<TreeNode*>& leaves) {
    parent[n] = par;
    if (n->left == nullptr && n->right == nullptr) leaves.push_back(n);
    if (n->left != nullptr) refPathsDfs(n->left, n, parent, leaves);
    if (n->right != nullptr) refPathsDfs(n->right, n, parent, leaves);
}

static std::vector<std::string> refPaths(TreeNode* root) {
    std::vector<std::string> out;
    if (root == nullptr) return out;
    std::map<TreeNode*, TreeNode*> parent;
    std::vector<TreeNode*> leaves;
    refPathsDfs(root, nullptr, parent, leaves);
    for (TreeNode* leaf : leaves) {
        std::vector<int> vals;
        for (TreeNode* n = leaf; n != nullptr; n = parent[n]) vals.push_back(n->val);
        std::reverse(vals.begin(), vals.end());
        std::string s;
        for (std::size_t i = 0; i < vals.size(); ++i) {
            if (i > 0) s += "->";
            s += std::to_string(vals[i]);
        }
        out.push_back(s);
    }
    std::sort(out.begin(), out.end());
    return out;
}

// ---- canonical serialisation, byte-identical with the Python side --------

static std::vector<std::string> g_lines;
static std::vector<std::string> g_problems;
static int g_case = 0;

static void check(const std::string& tag, bool ok) {
    if (!ok) g_problems.push_back(tag);
}

static std::string fmtInts(const std::vector<int>& xs) {
    std::string s;
    for (std::size_t i = 0; i < xs.size(); ++i) {
        if (i > 0) s += ",";
        s += std::to_string(xs[i]);
    }
    return s;
}

static std::string fmtLevels(const std::vector<std::vector<int>>& ls) {
    std::string s;
    for (std::size_t i = 0; i < ls.size(); ++i) {
        if (i > 0) s += ";";
        s += fmtInts(ls[i]);
    }
    return s;
}

static std::string fmtStrs(const std::vector<std::string>& ss) {
    std::string s;
    for (std::size_t i = 0; i < ss.size(); ++i) {
        if (i > 0) s += "|";
        s += ss[i];
    }
    return s;
}

static void runCase(const std::vector<int>& vals) {
    int idx = g_case++;
    TreeNode* root = buildTree(vals);
    check("roundtrip#" + std::to_string(idx), toLevels(root) == vals);

    std::vector<int> pre, in, post;
    refOrders(root, pre, in, post);
    std::vector<int> my_pre, my_in, my_post;
    threeOrders(root, my_pre, my_in, my_post);
    check("threeOrders.pre#" + std::to_string(idx), my_pre == pre);
    check("threeOrders.in#" + std::to_string(idx), my_in == in);
    check("threeOrders.post#" + std::to_string(idx), my_post == post);
    check("preorderTraversal#" + std::to_string(idx), preorderTraversal(root) == pre);
    check("preorderDivide#" + std::to_string(idx), preorderDivide(root) == pre);

    std::vector<std::vector<int>> lv = refLevels(root);
    check("levelOrder#" + std::to_string(idx), levelOrder(root) == lv);
    std::vector<int> right;
    for (const std::vector<int>& r : lv) right.push_back(r.back());
    check("rightSideView#" + std::to_string(idx), rightSideView(root) == right);

    int md = refMaxDepth(root);
    check("maxDepthTraverse#" + std::to_string(idx), maxDepthTraverse(root) == md);
    check("maxDepthDivide#" + std::to_string(idx), maxDepthDivide(root) == md);

    int dn = refDiameter(root);
    check("diameterNaive#" + std::to_string(idx), diameterNaive(root) == dn);
    check("diameterOfBinaryTree#" + std::to_string(idx),
          diameterOfBinaryTree(root) == dn);
    check("diameter agree#" + std::to_string(idx),
          diameterNaive(root) == diameterOfBinaryTree(root));

    check("isBalanced#" + std::to_string(idx), isBalanced(root) == refBalanced(root));

    std::string mps = "NA";
    if (root != nullptr) {
        int want = refMaxPathSum(root);
        check("maxPathSum#" + std::to_string(idx), maxPathSum(root) == want);
        mps = std::to_string(want);
    }
    std::vector<std::string> pmid = refPaths(root);
    std::vector<std::string> pgot = binaryTreePaths(root);
    std::sort(pgot.begin(), pgot.end());
    check("binaryTreePaths#" + std::to_string(idx), pgot == pmid);

    // the fixed cases below are asserted on the Python side; here we only need
    // the transcript, which is identical either way.
    g_lines.push_back(
        "C" + std::to_string(idx) +
        " pre=<" + fmtInts(preorderTraversal(root)) + ">" +
        " in=<" + fmtInts(my_in) + ">" +
        " post=<" + fmtInts(my_post) + ">" +
        " lvl=<" + fmtLevels(levelOrder(root)) + ">" +
        " right=<" + fmtInts(rightSideView(root)) + ">" +
        " mt=" + std::to_string(maxDepthTraverse(root)) +
        " md=" + std::to_string(maxDepthDivide(root)) +
        " dn=" + std::to_string(diameterNaive(root)) +
        " do=" + std::to_string(diameterOfBinaryTree(root)) +
        " bal=" + (isBalanced(root) ? "1" : "0") +
        " mps=" + mps +
        " paths=<" + fmtStrs(pmid) + ">");
}

int main() {
    std::vector<std::vector<int>> fixed = {
        {},
        {7},
        {1, 2, 3, 4, 5, 6, 7},
        {1, 2, NUL, 3, NUL, 4},
        {1, NUL, 2, NUL, 3},
        {1, 2, NUL, NUL, 3},
        {1, 2, 3, NUL, NUL, NUL, 4},
        {-10, 9, 20, NUL, NUL, 15, 7},
        {-3},
        {-1, -2, -3},
        {5, 4, 8, 11, NUL, 13, 4, 7, 2},
        {1, 2, 3, 4, NUL, NUL, 5},
        {0, 0, 0},
        {2, 1, 3},
        {1, 2, NUL, 3, NUL, 4, NUL, 5},
    };
    for (const std::vector<int>& v : fixed) runCase(v);
    for (int k = 0; k < ''' + str(ROUNDS) + r'''; ++k) runCase(randomLevels());

    std::cout << "CASES " << g_lines.size() << "\n";
    if (!g_problems.empty()) {
        std::cout << "FAILURES " << g_problems.size() << "\n";
        for (std::size_t i = 0; i < g_problems.size() && i < 25; ++i)
            std::cout << "  - " << g_problems[i] << "\n";
        std::cout << "SOME CASES FAILED\n";
    } else {
        std::cout << "ALL PASS\n";
    }
    std::cout << "TRANSCRIPT-BEGIN\n";
    for (const std::string& l : g_lines) std::cout << l << "\n";
    std::cout << "TRANSCRIPT-END\n";
    return 0;
}
'''


# --------------------------------------------------------------------------
def transcript(out: str):
    if "TRANSCRIPT-BEGIN" not in out or "TRANSCRIPT-END" not in out:
        return None
    body = out.split("TRANSCRIPT-BEGIN", 1)[1].split("TRANSCRIPT-END", 1)[0]
    return body.strip("\n")


def main() -> int:
    text = POST.read_text(encoding="utf-8")
    py_blocks = PY_BLOCK.findall(text)
    cpp_blocks = CPP_BLOCK.findall(text)

    print(f"  post          : {POST.name}")
    print(f"  python blocks : {len(py_blocks)}  (expect {EXPECTED_PY})")
    print(f"  cpp blocks    : {len(cpp_blocks)}  (expect {EXPECTED_CPP})")

    ok = True
    if len(py_blocks) != EXPECTED_PY:
        print(f"  !! python block count drifted: {len(py_blocks)} != {EXPECTED_PY}")
        ok = False
    if len(cpp_blocks) != EXPECTED_CPP:
        print(f"  !! cpp block count drifted: {len(cpp_blocks)} != {EXPECTED_CPP}")
        ok = False

    for i, b in enumerate(py_blocks):
        try:
            ast.parse(b)
        except SyntaxError as exc:
            print(f"  !! python block {i + 1} does not parse standalone: {exc}")
            ok = False

    # ---- Python ---------------------------------------------------------
    ns: dict = {"__name__": "__post__", "ROUNDS": ROUNDS}
    buf = io.StringIO()
    try:
        exec(compile("\n\n".join(py_blocks), "<post-python>", "exec"), ns)
        with contextlib.redirect_stdout(buf):
            exec(compile(PY_MAIN, "<harness-python>", "exec"), ns)
    except Exception as exc:                       # noqa: BLE001
        print(f"  !! python side raised: {type(exc).__name__}: {exc}")
        return 1

    py_out = buf.getvalue()
    py_pass = "ALL PASS" in py_out
    py_cases = py_out.splitlines()[0].split(" ", 1)[-1] if py_out else "?"
    print(f"  python cases  : {py_cases} cases, "
          f"{'all pass' if py_pass else 'FAILURES'} (vs brute force)")
    if not py_pass:
        ok = False
        for line in py_out.splitlines():
            if line.startswith("  - ") or line.startswith("FAILURES"):
                print("      " + line.strip())

    # ---- C++ ------------------------------------------------------------
    BUILD.mkdir(parents=True, exist_ok=True)
    gen = BUILD / "binary_tree_generated.cpp"
    gen.write_text("\n\n".join(cpp_blocks) + "\n" + CPP_MAIN, encoding="utf-8")
    exe = BUILD / "binary_tree_generated"

    cp = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
         str(gen), "-o", str(exe)],
        capture_output=True, text=True)
    warn = (cp.stderr or "").strip()
    if cp.returncode != 0 or warn:
        ok = False
        print(f"  !! cpp compile failed (rc={cp.returncode})")
        for line in warn.splitlines()[:25]:
            print("      " + line)
    else:
        print("  cpp compile   : clean  (g++ -std=c++17 -Wall -Wextra -Werror -O1)")

    cpp_out = ""
    if cp.returncode == 0:
        rp = subprocess.run([str(exe)], capture_output=True, text=True)
        cpp_out = rp.stdout
        cpp_pass = "ALL PASS" in cpp_out
        cpp_cases = cpp_out.splitlines()[0] if cpp_out else "?"
        print(f"  cpp cases     : {cpp_cases.split(' ', 1)[-1]} cases, "
              f"{'all pass' if cpp_pass else 'FAILURES'} (vs brute force)")
        if rp.returncode != 0 or not cpp_pass:
            ok = False
            for line in cpp_out.splitlines():
                if line.startswith("  - ") or line.startswith("FAILURES"):
                    print("      " + line.strip())

    # ---- cross-language agreement ---------------------------------------
    tp, tc = transcript(py_out), transcript(cpp_out)
    if tp is None or tc is None:
        ok = False
        print("  !! could not extract a transcript from one of the sides")
    elif tp != tc:
        ok = False
        lp, lc = tp.splitlines(), tc.splitlines()
        print(f"  !! transcripts differ ({len(lp)} vs {len(lc)} lines)")
        for i in range(min(len(lp), len(lc))):
            if lp[i] != lc[i]:
                print(f"      first diff at line {i}:")
                print(f"        py  : {lp[i][:160]}")
                print(f"        cpp : {lc[i][:160]}")
                break
    else:
        h = hashlib.sha256(tp.encode()).hexdigest()[:16]
        print(f"  cross-check   : transcripts identical, {len(tp.splitlines())} lines, "
              f"sha256 {h}")

    print()
    if ok:
        print("  CODE OK — every case passes in both languages, and the two "
              "languages agree line for line")
        return 0
    print("  CODE FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
