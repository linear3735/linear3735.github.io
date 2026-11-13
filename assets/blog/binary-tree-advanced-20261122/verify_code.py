#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代码门:把 _posts/2026-11-22-binary-tree-advanced.md 里的代码抽出来真跑。

做法(和 assets/blog/interview-algo-speedrun-20261108/verify_code.py 一致):

1. 从文章里正则抽出 ```python 和 ```cpp 块(AST/编译都针对文章原文,不手抄)。
2. 本脚本先随机生成用例(固定种子的 LCG),写进 build/cases.txt;
   Python 侧和 C++ 侧读的是**同一份**文件,所以两边跑的是完全相同的输入。
3. Python 侧:ast.parse 每个块,再在同一个命名空间里 exec,然后逐组跑用例,
   用 harness 里独立写的暴力算法对拍。
4. C++ 侧:把文章里的 cpp 块拼起来 + 本脚本生成的 harness main,
   用 g++ -std=c++17 -Wall -Wextra -Werror 编译(零警告),读同一份 cases.txt。
5. 两边的 transcript 逐字节比较,并各自打印 ALL PASS。

覆盖的边界:空树、单节点、退化链(全左/全右)、满二叉树、完全二叉树、
随机树、随机 BST、值不重复的排列。
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
POST = REPO / "_posts" / "2026-11-22-binary-tree-advanced.md"
BUILD = HERE / "build"
CASES = BUILD / "cases.txt"
GENERATED_CPP = BUILD / "binary_tree_advanced_generated.cpp"
RUN_CPP = BUILD / "binary_tree_advanced_run"

EXPECTED_PY = 18
EXPECTED_CPP = 18
ROUNDS = 240
PY_ONLY = "--py-only" in sys.argv


# ---------------------------------------------------------------------------
# 1. 从文章里抽代码块
# ---------------------------------------------------------------------------
def fences(text):
    marks = list(re.finditer(r"^```(\w*)\s*$", text, re.M))
    out = []
    for i in range(0, len(marks) - 1, 2):
        out.append((marks[i].group(1), text[marks[i].end():marks[i + 1].start()]))
    return out


def load_post():
    text = POST.read_text(encoding="utf-8")
    blocks = fences(text)
    py = [b for lang, b in blocks if lang == "python"]
    cpp = [b for lang, b in blocks if lang == "cpp"]
    return text, py, cpp


# ---------------------------------------------------------------------------
# 2. 用例生成(固定种子,写进 cases.txt,两边共用)
# ---------------------------------------------------------------------------
class HNode:
    """harness 自己的树节点,只用来生成用例和跑暴力,和文章里的类无关。"""

    __slots__ = ("val", "left", "right")

    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None


_seed = 20261122


def rnd(n):
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed % n


def gen_perm(n):
    vals = list(range(1, n + 1))
    for i in range(n - 1, 0, -1):
        j = rnd(i + 1)
        vals[i], vals[j] = vals[j], vals[i]
    return vals


def gen_shape(n):
    """随机形状:维护"还空着的位置"列表,每次随机挑一个挂上去。"""
    if n == 0:
        return None
    vals = gen_perm(n)
    root = HNode(vals[0])
    slots = [(root, 0), (root, 1)]
    for i in range(1, n):
        j = rnd(len(slots))
        parent, side = slots.pop(j)
        child = HNode(vals[i])
        if side == 0:
            parent.left = child
        else:
            parent.right = child
        slots.append((child, 0))
        slots.append((child, 1))
    return root


def gen_complete(n, vals=None):
    if n == 0:
        return None
    vals = vals or list(range(1, n + 1))
    nodes = [HNode(vals[i]) for i in range(n)]
    for i in range(n):
        if 2 * i + 1 < n:
            nodes[i].left = nodes[2 * i + 1]
        if 2 * i + 2 < n:
            nodes[i].right = nodes[2 * i + 2]
    return nodes[0]


def gen_chain(n, left=True, vals=None):
    if n == 0:
        return None
    vals = vals or list(range(1, n + 1))
    nodes = [HNode(vals[i]) for i in range(n)]
    for i in range(n - 1):
        if left:
            nodes[i].left = nodes[i + 1]
        else:
            nodes[i].right = nodes[i + 1]
    return nodes[0]


def bst_insert(root, val):
    if root is None:
        return HNode(val)
    if val < root.val:
        root.left = bst_insert(root.left, val)
    else:
        root.right = bst_insert(root.right, val)
    return root


def gen_bst(n):
    root = None
    for v in gen_perm(n):
        root = bst_insert(root, v)
    return root


def build_bst_balanced(lo, hi):
    """中位数当根,建一棵"最平衡"的 BST。"""
    if lo > hi:
        return None
    mid = (lo + hi) // 2
    node = HNode(mid)
    node.left = build_bst_balanced(lo, mid - 1)
    node.right = build_bst_balanced(mid + 1, hi)
    return node


def arr(node):
    """层序数组(力扣格式,None -> '#',去尾),空树给空字符串。"""
    if node is None:
        return ""
    out, q, i = [], [node], 0
    while i < len(q):
        cur = q[i]
        i += 1
        if cur is None:
            out.append("#")
            continue
        out.append(str(cur.val))
        q.append(cur.left)
        q.append(cur.right)
    while out and out[-1] == "#":
        out.pop()
    return ",".join(out)


def path_to(node, want):
    """从 node 出发找 want(按身份),返回 'L'/'R' 组成的路径,找不到返回 None。"""
    if node is None:
        return None
    if node is want:
        return ""
    for side, child in (("L", node.left), ("R", node.right)):
        sub = path_to(child, want)
        if sub is not None:
            return side + sub
    return None


def paths_of(node, out=None, cur=""):
    if out is None:
        out = {}
    if node is None:
        return out
    out.setdefault(node, cur)
    paths_of(node.left, out, cur + "L")
    paths_of(node.right, out, cur + "R")
    return out


def nodes_of(node, out=None):
    if out is None:
        out = []
    if node is None:
        return out
    out.append(node)
    nodes_of(node.left, out)
    nodes_of(node.right, out)
    return out


def pick_path(node, want_index):
    ns = nodes_of(node)
    return path_to(node, ns[want_index])


def cases_lines():
    lines = []
    boundary = [None, gen_complete(1), gen_complete(3), gen_complete(7),
                gen_chain(5, True), gen_chain(5, False),
                gen_shape(2), gen_shape(4)]
    trees_small = list(boundary)
    for _ in range(ROUNDS):
        trees_small.append(gen_shape(1 + rnd(15)))
    trees_tiny = [None]
    for _ in range(120):
        t = gen_shape(rnd(10))          # 0..9 个节点,0 就是空树
        for x in nodes_of(t):
            x.val = 1 + rnd(20)         # 值可能重复,值都 >= 1(0 留给"空位")
        trees_tiny.append(t)
    # BST 组必须用真正的 BST 做边界:平衡 BST + 左链(值递减)+ 右链(值递增)
    bsts = [None, build_bst_balanced(1, 1), build_bst_balanced(1, 3),
            build_bst_balanced(1, 7), build_bst_balanced(1, 15),
            gen_chain(6, True, list(range(6, 0, -1))),   # 6-5-4-3-2-1 全左
            gen_chain(6, False, list(range(1, 7)))]      # 1-2-3-4-5-6 全右
    for _ in range(ROUNDS):
        bsts.append(gen_bst(1 + rnd(15)))
    completes = [gen_complete(n) for n in range(0, 41)]
    for _ in range(40):
        completes.append(gen_complete(300 + rnd(900)))
    perfects = [gen_complete((1 << h) - 1) for h in range(0, 7)]

    def add(group, *fields):
        lines.append("|".join([group] + [str(f) for f in fields]))

    for t in trees_small:                       # G01 / G02 构造
        add("G01_build_pre_in", arr(t))
        add("G02_build_in_post", arr(t))
    for t in trees_small:                       # G03 序列化
        add("G03_serialize", arr(t))
    for t in trees_small:                       # G04 236 / G06 1650 / G07 倍增
        ns = nodes_of(t)
        if not ns:
            add("G04_lca_recursive", "", "", "")
            add("G06_lca_parent", "", "", "")
            add("G07_lca_lifting", "", "", "")
            continue
        for _ in range(3):
            a, b = rnd(len(ns)), rnd(len(ns))
            pa, pb = path_to(t, ns[a]), path_to(t, ns[b])
            add("G04_lca_recursive", arr(t), pa, pb)
            add("G06_lca_parent", arr(t), pa, pb)
            add("G07_lca_lifting", arr(t), pa, pb)
    for t in bsts:                              # G05 BST 版 LCA
        ns = nodes_of(t)
        if not ns:
            add("G05_lca_bst", "", "", "")
            continue
        for _ in range(3):
            a, b = rnd(len(ns)), rnd(len(ns))
            add("G05_lca_bst", arr(t), path_to(t, ns[a]), path_to(t, ns[b]))
    for t in bsts:                              # G08 第 K 小
        n = len(nodes_of(t))
        add("G08_kth_smallest", arr(t), 1 + rnd(n) if n else 0)
    for t in bsts:                              # G09 累加树
        add("G09_convert_bst", arr(t))
    for t in trees_small:                       # G10 验证 BST
        add("G10_is_valid_bst", arr(t))
    for t in bsts:                              # G11/G12/G13 BST 增删查
        n = len(nodes_of(t))
        add("G11_search_bst", arr(t), 1 + rnd(n + 3) if n else 1)
        add("G12_insert_bst", arr(t), 1 + rnd(n + 3) if n else 1 + rnd(4))
        add("G13_delete_bst", arr(t), 1 + rnd(n + 2) if n else 1)
    for t in completes:                         # G14 完全二叉树计数
        add("G14_count_nodes", arr(t))
    for t in trees_small:                       # G15 翻转
        add("G15_invert", arr(t))
    for t in trees_small:                       # G16 拍平
        add("G16_flatten", arr(t))
    for t in perfects:                          # G17 连接 next
        add("G17_connect", arr(t))
    for i, t in enumerate(trees_small):         # G18 子树判断
        sub = nodes_of(t)[rnd(len(nodes_of(t)))] if nodes_of(t) else None
        other = trees_small[(i * 7 + 3) % len(trees_small)]
        add("G18_is_subtree", arr(other), arr(sub))
    for i, t in enumerate(trees_small):         # G19 合并
        add("G19_merge", arr(t), arr(trees_small[(i * 5 + 1) % len(trees_small)]))
    for t in trees_tiny:                        # G20 打家劫舍 III
        add("G20_rob", arr(t))
    return lines


# ---------------------------------------------------------------------------
# 3. cases.txt 的解析(两边共用同一份逻辑)
# ---------------------------------------------------------------------------
def parse_arr(s):
    if s == "":
        return []
    return [None if t == "#" else int(t) for t in s.split(",")]


def build_treenode(vals, cls):
    """按力扣层序规则建树,cls 是文章里定义的 TreeNode / PNode / NNode。"""
    if not vals:
        return None
    root = cls(vals[0])
    q, i = [root], 0
    while q and i < len(vals) - 1:
        cur = q.pop(0)
        i += 1
        if i < len(vals) and vals[i] is not None:
            cur.left = cls(vals[i])
            q.append(cur.left)
        i += 1
        if i < len(vals) and vals[i] is not None:
            cur.right = cls(vals[i])
            q.append(cur.right)
    return root


def build_pnode(vals, cls):
    root = build_treenode(vals, cls)
    stack = [root] if root is not None else []
    while stack:
        cur = stack.pop()
        for child in (cur.left, cur.right):
            if child is not None:
                child.parent = cur
                stack.append(child)
    return root


def resolve(root, path):
    cur = root
    for ch in path:
        if cur is None:
            return None
        cur = cur.left if ch == "L" else cur.right
    return cur


def dump(node):
    if node is None:
        return []
    out, q, i = [], [node], 0
    while i < len(q):
        cur = q[i]
        i += 1
        if cur is None:
            out.append(None)
            continue
        out.append(cur.val)
        q.append(cur.left)
        q.append(cur.right)
    while out and out[-1] is None:
        out.pop()
    return out


# ---------------------------------------------------------------------------
# 4. Python 侧跑用例
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self):
        self.lines = []
        self.checks = 0
        self.fails = 0

    def group(self, name, checks, h):
        self.lines.append("%s checks=%d h=%d" % (name, checks, h))
        self.checks += checks

    def fail(self, name, idx, detail):
        self.fails += 1
        self.lines.append("FAIL %s case=%d %s" % (name, idx, detail))

    def out(self):
        return "\n".join(self.lines)


def run_python(ns, case_lines):
    r = Runner()
    for name in sorted({ln.split("|")[0] for ln in case_lines}):
        fn = globals()["py_" + name]
        rows = [ln.split("|")[1:] for ln in case_lines if ln.startswith(name + "|")]
        h, n = fn(ns, rows, r, name)
        r.group(name, n, h)
    return r


def phash(h, x):
    return (h * 131 + (x & 0xFFFFFFFF)) & 0xFFFFFFFF


def hash_path(h, path):
    if path is None:
        return phash(h, 999)
    for ch in path:
        h = phash(h, 1 if ch == "L" else 2)
    return phash(h, 0)


def hash_dump(h, seq):
    """seq 里 0 代表空位,真实值都 >= 1。"""
    for v in seq:
        h = phash(h, v)
    return phash(h, 7777)


def cyc_dump(vals):
    """把层序数组转成可哈希的整数序列(None -> 0,值都 >= 1)。"""
    return [0 if v is None else v for v in vals]


# ---- 每一组的实现 ----------------------------------------------------------

def py_G01_build_pre_in(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        want = parse_arr(a)
        t = build_treenode(want, ns["TreeNode"])
        pre = preorder(t)
        ino = inorder(t)
        got = dump(ns["buildTreePreIn"](pre, ino))
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        h = hash_dump(h, cyc_dump(got))
        n += 1
    return h, n


def py_G02_build_in_post(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        want = parse_arr(a)
        t = build_treenode(want, ns["TreeNode"])
        ino = inorder(t)
        post = postorder(t)
        got = dump(ns["buildTreeInPost"](ino, post))
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        h = hash_dump(h, cyc_dump(got))
        n += 1
    return h, n


def py_G03_serialize(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        want = parse_arr(a)
        t = build_treenode(want, ns["TreeNode"])
        s = ns["serialize"](t)
        back = dump(ns["deserialize"](s))
        if back != want:
            r.fail(name, i, "ser=%r got %s want %s" % (s, back, want))
        toks = s.split(ns["SEP"]) if s else []
        size = len(nodes_of(t))
        if len(toks) != 2 * size + 1:
            r.fail(name, i, "token count %d want %d" % (len(toks), 2 * size + 1))
        if size == 0 and s != ns["NULL"]:
            r.fail(name, i, "empty tree serialized to %r" % s)
        for ch in s:
            h = phash(h, ord(ch))
        h = hash_dump(h, cyc_dump(back))
        n += 3
    return h, n


def py_G04_lca_recursive(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, pa, pb) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        p, q = resolve(t, pa), resolve(t, pb)
        if t is None:
            n += 1
            continue
        got = ns["lowestCommonAncestor"](t, p, q)
        want = brute_lca(t, p, q)
        if got is not want:
            r.fail(name, i, "got %r want %r" % (val_of(got), val_of(want)))
        h = hash_path(h, path_to(t, got))
        n += 1
    return h, n


def py_G06_lca_parent(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, pa, pb) in enumerate(rows):
        vals = parse_arr(a)
        t = build_pnode(vals, ns["PNode"])
        if t is None:
            n += 1
            continue
        p, q = resolve(t, pa), resolve(t, pb)
        got = ns["lowestCommonAncestorParent"](p, q)
        want = brute_lca_parent(p, q)
        if got is not want:
            r.fail(name, i, "got %r want %r" % (val_of(got), val_of(want)))
        h = hash_path(h, path_to(t, got))
        n += 1
    return h, n


def py_G07_lca_lifting(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, pa, pb) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        if t is None:
            n += 1
            continue
        p, q = resolve(t, pa), resolve(t, pb)
        got = ns["lcaBinaryLifting"](t, p, q)
        want = brute_lca(t, p, q)
        if got is not want:
            r.fail(name, i, "got %r want %r" % (val_of(got), val_of(want)))
        h = hash_path(h, path_to(t, got))
        n += 1
    return h, n


def py_G05_lca_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, pa, pb) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        if t is None:
            n += 1
            continue
        p, q = resolve(t, pa), resolve(t, pb)
        got = ns["lowestCommonAncestorBST"](t, p, q)
        want = brute_lca(t, p, q)
        if got is not want:
            r.fail(name, i, "got %r want %r" % (val_of(got), val_of(want)))
        h = hash_path(h, path_to(t, got))
        n += 1
    return h, n


def py_G08_kth_smallest(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, k) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        k = int(k)
        if t is None:
            n += 1
            continue
        got = ns["kthSmallest"](t, k)
        want = sorted(values_of(t))[k - 1]
        if got != want:
            r.fail(name, i, "k=%d got %d want %d" % (k, got, want))
        h = phash(h, got)
        n += 1
    return h, n


def py_G09_convert_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        want_tree = build_treenode(vals, ns["TreeNode"])
        want = convert_expected(want_tree)
        t = build_treenode(vals, ns["TreeNode"])
        ns["convertBST"](t)
        got = path_values(t)
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        h = hash_dump(h, cyc_dump(dump(t)))
        n += 1
    return h, n


def py_G10_is_valid_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        got = ns["isValidBST"](t)
        seq = inorder(t)
        want = all(seq[j] < seq[j + 1] for j in range(len(seq) - 1))
        if bool(got) != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        h = phash(h, 1 if got else 0)
        n += 1
    return h, n


def py_G11_search_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, tgt) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        got = ns["searchBST"](t, int(tgt))
        want = None
        for x in nodes_of(t):
            if x.val == int(tgt):
                want = x
                break
        if got is not want:
            r.fail(name, i, "target=%s got %r want %r"
                   % (tgt, val_of(got), val_of(want)))
        h = phash(h, -1 if got is None else got.val)
        n += 1
    return h, n


def py_G12_insert_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, val) in enumerate(rows):
        vals = parse_arr(a)
        val = int(val)
        t = build_treenode(vals, ns["TreeNode"])
        before = sorted(values_of(t))
        root = ns["insertIntoBST"](t, val)
        seq = inorder(root)
        # 文章的实现遇到重复值直接原样返回,不插入第二个
        want = before if val in before else sorted(before + [val])
        if seq != want:
            r.fail(name, i, "val=%d inorder %s want %s" % (val, seq, want))
        if seq != sorted(set(seq)):
            r.fail(name, i, "重复值出现了: %s" % seq)
        h = hash_dump(h, cyc_dump(dump(root)))
        n += 2
    return h, n


def py_G13_delete_bst(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, key) in enumerate(rows):
        vals = parse_arr(a)
        key = int(key)
        t = build_treenode(vals, ns["TreeNode"])
        before = sorted(values_of(t))
        want = list(before)
        if key in want:
            want.remove(key)
        root = ns["deleteNode"](t, key)
        seq = inorder(root)
        if seq != want:
            r.fail(name, i, "key=%d inorder %s want %s" % (key, seq, want))
        if seq != sorted(set(seq)):
            r.fail(name, i, "删除后出现了重复值: %s" % seq)
        h = hash_dump(h, cyc_dump(dump(root)))
        n += 2
    return h, n


def py_G14_count_nodes(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        got = ns["countNodes"](t)
        want = len(nodes_of(t))
        if got != want:
            r.fail(name, i, "got %d want %d" % (got, want))
        h = phash(h, got)
        n += 1
    return h, n


def py_G15_invert(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t1 = build_treenode(vals, ns["TreeNode"])
        ns["invertTreeTraverse"](t1)
        t2 = build_treenode(vals, ns["TreeNode"])
        ns["invertTreeDivide"](t2)
        if dump(t1) != dump(t2):
            r.fail(name, i, "两个版本不一致: %s vs %s" % (dump(t1), dump(t2)))
        # 独立校验:每个节点的路径把 L/R 互换之后,值应该对上
        got = path_values(t1)
        want = {}
        for path, val in path_values(build_treenode(vals, ns["TreeNode"])).items():
            want[swap_lr(path)] = val
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        h = hash_dump(h, cyc_dump(dump(t1)))
        n += 2
    return h, n


def py_G16_flatten(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        want = preorder(t)
        ns["flatten"](t)
        got, cur, guard = [], t, 0
        while cur is not None and guard <= len(want) + 1:
            got.append(cur.val)
            if cur.left is not None:
                r.fail(name, i, "left 没有置空: %s" % dump(t))
                break
            cur = cur.right
            guard += 1
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        if cur is not None:
            r.fail(name, i, "right 链有环")
        for v in got:
            h = phash(h, v)
        h = phash(h, 555)
        n += 1
    return h, n


def py_G17_connect(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["NNode"])
        ns["connect"](t)
        levels, q = [], [t] if t is not None else []
        while q:
            levels.append(list(q))
            nxt = []
            for x in q:
                if x.left is not None:
                    nxt.append(x.left)
                if x.right is not None:
                    nxt.append(x.right)
            q = nxt
        idx = {}
        for lv in levels:
            for j, x in enumerate(lv):
                idx[x] = (id(lv), j)
        for lv in levels:
            for j, x in enumerate(lv):
                want = lv[j + 1] if j + 1 < len(lv) else None
                if x.next is not want:
                    r.fail(name, i, "第 %d 层第 %d 个 next 不对" % (levels.index(lv), j))
                h = phash(h, -1 if x.next is None else idx[x.next][1] + 1)
        n += 1
    return h, n


def py_G18_is_subtree(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, b) in enumerate(rows):
        t = build_treenode(parse_arr(a), ns["TreeNode"])
        s = build_treenode(parse_arr(b), ns["TreeNode"])
        got = ns["isSubtree"](t, s)
        want = False
        if s is None:
            want = True
        else:
            for x in nodes_of(t):
                if same_tree(x, s):
                    want = True
                    break
        if bool(got) != want:
            r.fail(name, i, "got %s want %s (%s in %s)" % (got, want, b, a))
        h = phash(h, 1 if got else 0)
        n += 1
    return h, n


def py_G19_merge(ns, rows, r, name):
    h, n = 0, 0
    for i, (a, b) in enumerate(rows):
        ta = build_treenode(parse_arr(a), ns["TreeNode"])
        tb = build_treenode(parse_arr(b), ns["TreeNode"])
        want = {}
        for src in (a, b):
            for path, val in path_values(build_treenode(parse_arr(src), ns["TreeNode"])).items():
                want[path] = want.get(path, 0) + val
        got = path_values(ns["mergeTrees"](ta, tb))
        if got != want:
            r.fail(name, i, "got %s want %s" % (got, want))
        for path in sorted(got):
            h = phash(h, got[path])
            h = phash(h, sum(ord(c) for c in path))
        h = phash(h, 444)
        n += 1
    return h, n


def py_G20_rob(ns, rows, r, name):
    h, n = 0, 0
    for i, (a,) in enumerate(rows):
        vals = parse_arr(a)
        t = build_treenode(vals, ns["TreeNode"])
        got = ns["rob"](t)
        want = rob_brute(build_treenode(vals, ns["TreeNode"]))
        if got != want:
            r.fail(name, i, "got %d want %d (%s)" % (got, want, a))
        h = phash(h, got)
        n += 1
    return h, n


# ---- harness 的独立工具(和文章里的实现无关) --------------------------------

def val_of(x):
    return None if x is None else x.val


def values_of(t):
    return [x.val for x in nodes_of(t)]


def preorder(t):
    out = []
    stack = [t] if t is not None else []
    while stack:
        x = stack.pop()
        out.append(x.val)
        if x.right is not None:
            stack.append(x.right)
        if x.left is not None:
            stack.append(x.left)
    return out


def inorder(t):
    out, stack, cur = [], [], t
    while stack or cur is not None:
        while cur is not None:
            stack.append(cur)
            cur = cur.left
        cur = stack.pop()
        out.append(cur.val)
        cur = cur.right
    return out


def postorder(t):
    out, stack = [], [t] if t is not None else []
    while stack:
        x = stack.pop()
        out.append(x.val)
        if x.left is not None:
            stack.append(x.left)
        if x.right is not None:
            stack.append(x.right)
    return out[::-1]


def parent_map(t):
    out = {}
    stack = [(t, None)] if t is not None else []
    while stack:
        x, p = stack.pop()
        out[x] = p
        if x.left is not None:
            stack.append((x.left, x))
        if x.right is not None:
            stack.append((x.right, x))
    return out


def brute_lca(t, p, q):
    """暴力:分别走出两条到根的路径,第一个公共节点就是 LCA。"""
    pm = parent_map(t)
    up_p, cur = set(), p
    while cur is not None:
        up_p.add(id(cur))
        cur = pm.get(cur)
    cur = q
    while cur is not None:
        if id(cur) in up_p:
            return cur
        cur = pm.get(cur)
    return None


def brute_lca_parent(p, q):
    seen, cur = set(), p
    while cur is not None:
        seen.add(id(cur))
        cur = cur.parent
    cur = q
    while cur is not None:
        if id(cur) in seen:
            return cur
        cur = cur.parent
    return None


def path_values(t):
    out, stack = {}, [(t, "")] if t is not None else []
    while stack:
        x, path = stack.pop()
        out[path] = x.val
        if x.left is not None:
            stack.append((x.left, path + "L"))
        if x.right is not None:
            stack.append((x.right, path + "R"))
    return out


def swap_lr(path):
    return "".join("R" if c == "L" else "L" for c in path)


def same_tree(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return (a.val == b.val and same_tree(a.left, b.left)
            and same_tree(a.right, b.right))


def rob_brute(t):
    """暴力:枚举所有"没有父子同时被选中"的子集,取最大和。"""
    nodes = []
    stack = [(t, -1)] if t is not None else []
    while stack:
        x, p = stack.pop()
        i = len(nodes)
        nodes.append((x.val, p))
        if x.left is not None:
            stack.append((x.left, i))
        if x.right is not None:
            stack.append((x.right, i))
    best, n = 0, len(nodes)
    for mask in range(1 << n):
        total, ok = 0, True
        for i in range(n):
            if mask >> i & 1:
                p = nodes[i][1]
                if p >= 0 and (mask >> p & 1):
                    ok = False
                    break
                total += nodes[i][0]
        if ok and total > best:
            best = total
    return best


def subtree_sum(t):
    return sum(values_of(t))


def convert_expected(t, carry=0):
    """独立算法:自顶向下带 carry 算 538 的期望结果。

    反中序访问顺序是 右 -> 根 -> 左,所以进入某个节点时,
    已经被访问过的节点 = carry(这棵子树之前的所有节点)+ 整个右子树。
    """
    out = {}
    stack = [(t, carry)] if t is not None else []
    while stack:
        node, carry = stack.pop()
        if node is None:
            continue
        rs = subtree_sum(node.right)
        out[path_of(node, t)] = carry + rs + node.val
        stack.append((node.right, carry))
        stack.append((node.left, carry + rs + node.val))
    return out


def path_of(node, root):
    p = path_to(root, node)
    return p


# ---------------------------------------------------------------------------
# 5. C++ 侧
# ---------------------------------------------------------------------------
CPP_PREAMBLE = """// 本文件由 verify_code.py 生成,不要手改。
#include <algorithm>
#include <climits>
#include <cstddef>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <queue>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
"""


def main():
    text, py_blocks, cpp_blocks = load_post()
    problems = []
    if len(py_blocks) != EXPECTED_PY:
        problems.append("python blocks: %d, want %d" % (len(py_blocks), EXPECTED_PY))
    if len(cpp_blocks) != EXPECTED_CPP:
        problems.append("cpp blocks: %d, want %d" % (len(cpp_blocks), EXPECTED_CPP))
    print("  post        : %s" % POST.name)
    print("  python block: %d   cpp block: %d" % (len(py_blocks), len(cpp_blocks)))
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)
    case_lines = cases_lines()
    CASES.write_text("\n".join(case_lines) + "\n", encoding="utf-8")
    print("  cases       : %d lines -> %s" % (len(case_lines), CASES.name))

    ns = {"__name__": "__post__"}
    for i, b in enumerate(py_blocks):
        try:
            ast.parse(b)
        except SyntaxError as exc:
            print("  FAIL  python block %d 语法错误: %s" % (i, exc))
            return 1
        exec(compile(b, "<post-python-%d>" % i, "exec"), ns)

    r = run_python(ns, case_lines)
    py_out = r.out()
    (BUILD / "transcript_py.txt").write_text(py_out + "\n", encoding="utf-8")
    print("  python      : %d checks, %d fail" % (r.checks, r.fails))
    print(py_out)
    if r.fails:
        print("  RESULT: python 侧有 %d 个用例失败" % r.fails)
        return 1
    if PY_ONLY:
        return 0

    # ---- C++ ----
    generated = CPP_PREAMBLE + "\n".join(cpp_blocks) + "\n" + CPP_MAIN
    GENERATED_CPP.write_text(generated, encoding="utf-8")
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
           str(GENERATED_CPP), "-o", str(RUN_CPP)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        print("  FAIL  C++ 编译失败(-Wall -Wextra -Werror)")
        print(cp.stderr)
        return 1
    if cp.stderr.strip():
        print("  FAIL  C++ 编译有警告")
        print(cp.stderr)
        return 1
    print("  c++         : 编译通过,零警告")

    cp = subprocess.run([str(RUN_CPP), str(CASES)], capture_output=True, text=True)
    cpp_out = cp.stdout.strip()
    if cp.returncode != 0:
        print("  FAIL  C++ 运行失败 (exit %d)" % cp.returncode)
        print(cp.stdout)
        print(cp.stderr)
        return 1

    py_l = py_out.splitlines()
    cpp_l = cpp_out.splitlines()
    if py_l != cpp_l:
        print("  FAIL  Python 和 C++ 的输出不一致")
        for i in range(max(len(py_l), len(cpp_l))):
            a = py_l[i] if i < len(py_l) else "<缺>"
            b = cpp_l[i] if i < len(cpp_l) else "<缺>"
            if a != b:
                print("    行 %d: py=%r cpp=%r" % (i + 1, a, b))
                break
        return 1

    print("  compare     : python == cpp,逐字节一致")
    print("  RESULT: ALL PASS  %d checks" % r.checks)
    return 0


CPP_MAIN = r"""
// ===================== harness(由 verify_code.py 生成) =====================
namespace H {

static std::vector<int> g_lines;
static int g_checks = 0;
static int g_fails = 0;
static std::vector<std::string> g_out;

static unsigned int phash(unsigned int h, long long x) {
    return static_cast<unsigned int>((h * 131u + static_cast<unsigned int>(x & 0xFFFFFFFFLL)) & 0xFFFFFFFFu);
}

static std::vector<std::string> split(const std::string &s, char sep) {
    std::vector<std::string> out;
    std::string cur;
    for (char ch : s) {
        if (ch == sep) { out.push_back(cur); cur.clear(); }
        else cur += ch;
    }
    out.push_back(cur);
    return out;
}

static std::vector<int> parse_arr(const std::string &s) {
    std::vector<int> out;
    if (s.empty()) return out;
    for (const std::string &t : split(s, ',')) out.push_back(t == "#" ? -1 : std::stoi(t));
    return out;
}

static std::string dump(TreeNode *root) {
    if (root == nullptr) return "";
    std::vector<TreeNode *> q;
    std::vector<std::string> out;
    q.push_back(root);
    std::size_t i = 0;
    while (i < q.size()) {
        TreeNode *cur = q[i++];
        if (cur == nullptr) { out.push_back("#"); continue; }
        out.push_back(std::to_string(cur->val));
        q.push_back(cur->left);
        q.push_back(cur->right);
    }
    while (!out.empty() && out.back() == "#") out.pop_back();
    std::string s;
    for (std::size_t j = 0; j < out.size(); ++j) {
        if (j) s += ",";
        s += out[j];
    }
    return s;
}

template <typename T>
static std::string dump_generic(T *root) {
    if (root == nullptr) return "";
    std::vector<T *> q;
    std::vector<std::string> out;
    q.push_back(root);
    std::size_t i = 0;
    while (i < q.size()) {
        T *cur = q[i++];
        if (cur == nullptr) { out.push_back("#"); continue; }
        out.push_back(std::to_string(cur->val));
        q.push_back(cur->left);
        q.push_back(cur->right);
    }
    while (!out.empty() && out.back() == "#") out.pop_back();
    std::string s;
    for (std::size_t j = 0; j < out.size(); ++j) {
        if (j) s += ",";
        s += out[j];
    }
    return s;
}

static TreeNode *build(const std::vector<int> &vals) {
    if (vals.empty() || vals[0] < 0) return nullptr;
    TreeNode *root = new TreeNode(vals[0]);
    std::vector<TreeNode *> q;
    q.push_back(root);
    std::size_t i = 0, k = 0;
    while (k + 1 < vals.size() && i < q.size()) {
        TreeNode *cur = q[i++];
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->left = new TreeNode(vals[k]); q.push_back(cur->left); }
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->right = new TreeNode(vals[k]); q.push_back(cur->right); }
    }
    return root;
}

static PNode *build_pnode(const std::vector<int> &vals) {
    if (vals.empty() || vals[0] < 0) return nullptr;
    PNode *root = new PNode(vals[0]);
    std::vector<PNode *> q;
    q.push_back(root);
    std::size_t i = 0, k = 0;
    while (k + 1 < vals.size() && i < q.size()) {
        PNode *cur = q[i++];
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->left = new PNode(vals[k]); cur->left->parent = cur; q.push_back(cur->left); }
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->right = new PNode(vals[k]); cur->right->parent = cur; q.push_back(cur->right); }
    }
    return root;
}

static NNode *build_nnode(const std::vector<int> &vals) {
    if (vals.empty() || vals[0] < 0) return nullptr;
    NNode *root = new NNode(vals[0]);
    std::vector<NNode *> q;
    q.push_back(root);
    std::size_t i = 0, k = 0;
    while (k + 1 < vals.size() && i < q.size()) {
        NNode *cur = q[i++];
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->left = new NNode(vals[k]); q.push_back(cur->left); }
        ++k;
        if (k < vals.size() && vals[k] >= 0) { cur->right = new NNode(vals[k]); q.push_back(cur->right); }
    }
    return root;
}

static void collect(TreeNode *x, std::vector<TreeNode *> &out) {
    if (x == nullptr) return;
    out.push_back(x);
    collect(x->left, out);
    collect(x->right, out);
}

static std::string path_to(TreeNode *root, TreeNode *want) {
    if (root == nullptr) return "\x01";
    if (root == want) return "";
    std::string sub = path_to(root->left, want);
    if (sub != "\x01") return "L" + sub;
    sub = path_to(root->right, want);
    if (sub != "\x01") return "R" + sub;
    return "\x01";
}

static TreeNode *resolve(TreeNode *root, const std::string &path) {
    TreeNode *cur = root;
    for (char ch : path) {
        if (cur == nullptr) return nullptr;
        cur = (ch == 'L') ? cur->left : cur->right;
    }
    return cur;
}

static void inorder(TreeNode *x, std::vector<int> &out) {
    if (x == nullptr) return;
    inorder(x->left, out);
    out.push_back(x->val);
    inorder(x->right, out);
}

static std::vector<int> preorder(TreeNode *x) {
    std::vector<int> out;
    std::vector<TreeNode *> st;
    if (x) st.push_back(x);
    while (!st.empty()) {
        TreeNode *cur = st.back();
        st.pop_back();
        out.push_back(cur->val);
        if (cur->right) st.push_back(cur->right);
        if (cur->left) st.push_back(cur->left);
    }
    return out;
}

static std::vector<int> postorder(TreeNode *x) {
    std::vector<int> out;
    std::vector<TreeNode *> st;
    if (x) st.push_back(x);
    while (!st.empty()) {
        TreeNode *cur = st.back();
        st.pop_back();
        out.push_back(cur->val);
        if (cur->left) st.push_back(cur->left);
        if (cur->right) st.push_back(cur->right);
    }
    std::reverse(out.begin(), out.end());
    return out;
}

static std::unordered_map<TreeNode *, TreeNode *> parent_map(TreeNode *root) {
    std::unordered_map<TreeNode *, TreeNode *> out;
    std::vector<std::pair<TreeNode *, TreeNode *>> st;
    if (root) st.push_back({root, nullptr});
    while (!st.empty()) {
        std::pair<TreeNode *, TreeNode *> pr = st.back();
        st.pop_back();
        out[pr.first] = pr.second;
        if (pr.first->left) st.push_back({pr.first->left, pr.first});
        if (pr.first->right) st.push_back({pr.first->right, pr.first});
    }
    return out;
}

static TreeNode *brute_lca(TreeNode *root, TreeNode *p, TreeNode *q) {
    std::unordered_map<TreeNode *, TreeNode *> pm = parent_map(root);
    std::unordered_set<TreeNode *> seen;
    for (TreeNode *cur = p; cur != nullptr; cur = pm[cur]) seen.insert(cur);
    for (TreeNode *cur = q; cur != nullptr; cur = pm[cur]) {
        if (seen.count(cur)) return cur;
    }
    return nullptr;
}

static PNode *brute_lca_parent(PNode *p, PNode *q) {
    std::unordered_set<PNode *> seen;
    for (PNode *cur = p; cur != nullptr; cur = cur->parent) seen.insert(cur);
    for (PNode *cur = q; cur != nullptr; cur = cur->parent) {
        if (seen.count(cur)) return cur;
    }
    return nullptr;
}

static void path_values(TreeNode *x, const std::string &path,
                        std::vector<std::pair<std::string, int>> &out) {
    if (x == nullptr) return;
    out.push_back({path, x->val});
    path_values(x->left, path + "L", out);
    path_values(x->right, path + "R", out);
}

static std::vector<std::pair<std::string, int>> path_values(TreeNode *x) {
    std::vector<std::pair<std::string, int>> out;
    path_values(x, "", out);
    std::sort(out.begin(), out.end());
    return out;
}

static std::string swap_lr(const std::string &path) {
    std::string out = path;
    for (char &ch : out) ch = (ch == 'L') ? 'R' : 'L';
    return out;
}

static bool same_tree(TreeNode *a, TreeNode *b) {
    if (a == nullptr && b == nullptr) return true;
    if (a == nullptr || b == nullptr) return false;
    return a->val == b->val && same_tree(a->left, b->left) &&
           same_tree(a->right, b->right);
}

static int rob_brute(TreeNode *root) {
    std::vector<std::pair<int, int>> nodes;   // (val, parent index)
    std::vector<std::pair<TreeNode *, int>> st;
    if (root) st.push_back({root, -1});
    while (!st.empty()) {
        std::pair<TreeNode *, int> pr = st.back();
        st.pop_back();
        int i = static_cast<int>(nodes.size());
        nodes.push_back({pr.first->val, pr.second});
        if (pr.first->left) st.push_back({pr.first->left, i});
        if (pr.first->right) st.push_back({pr.first->right, i});
    }
    int n = static_cast<int>(nodes.size());
    int best = 0;
    for (int mask = 0; mask < (1 << n); ++mask) {
        int total = 0;
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            if ((mask >> i) & 1) {
                int p = nodes[static_cast<std::size_t>(i)].second;
                if (p >= 0 && ((mask >> p) & 1)) { ok = false; break; }
                total += nodes[static_cast<std::size_t>(i)].first;
            }
        }
        if (ok && total > best) best = total;
    }
    return best;
}

static unsigned int hash_dump(unsigned int h, const std::vector<int> &seq) {
    for (std::size_t i = 0; i < seq.size(); ++i) h = phash(h, seq[i]);
    return phash(h, 7777);
}

static unsigned int hash_path(unsigned int h, const std::string &path) {
    if (path.size() == 1 && path[0] == '\x01') return phash(h, 999);   // Python 侧的 None
    for (char ch : path) h = phash(h, ch == 'L' ? 1 : 2);
    return phash(h, 0);
}

static void fail(const std::string &name, int idx, const std::string &detail) {
    ++g_fails;
    g_out.push_back("FAIL " + name + " case=" + std::to_string(idx) + " " + detail);
}

static void group(const std::string &name, int checks, unsigned int h) {
    g_out.push_back(name + " checks=" + std::to_string(checks) + " h=" + std::to_string(h));
    g_checks += checks;
}


typedef std::vector<std::string> Row;
typedef std::pair<int, unsigned int> Res;

static std::vector<int> dump_ints(TreeNode *root) {
    std::vector<int> out;
    if (root == nullptr) return out;
    std::vector<TreeNode *> q;
    q.push_back(root);
    std::size_t i = 0;
    while (i < q.size()) {
        TreeNode *cur = q[i++];
        if (cur == nullptr) { out.push_back(0); continue; }
        out.push_back(cur->val);
        q.push_back(cur->left);
        q.push_back(cur->right);
    }
    while (!out.empty() && out.back() == 0) out.pop_back();
    return out;
}

static int count_nodes(TreeNode *x) {
    if (x == nullptr) return 0;
    return 1 + count_nodes(x->left) + count_nodes(x->right);
}

static int subtree_sum(TreeNode *x) {
    if (x == nullptr) return 0;
    return x->val + subtree_sum(x->left) + subtree_sum(x->right);
}

// 独立算法:自顶向下带 carry 算 538 的期望结果(镜像 Python 的 convert_expected)
static std::vector<std::pair<std::string, int>> convert_expected(TreeNode *root) {
    std::vector<std::pair<std::string, int>> out;
    std::vector<std::pair<TreeNode *, std::pair<std::string, int>>> st;
    if (root != nullptr) st.push_back({root, {"", 0}});
    while (!st.empty()) {
        std::pair<TreeNode *, std::pair<std::string, int>> pr = st.back();
        st.pop_back();
        if (pr.first == nullptr) continue;
        int rs = subtree_sum(pr.first->right);
        out.push_back({pr.second.first, pr.second.second + rs + pr.first->val});
        st.push_back({pr.first->right, {pr.second.first + "R", pr.second.second}});
        st.push_back({pr.first->left,
                      {pr.second.first + "L", pr.second.second + rs + pr.first->val}});
    }
    std::sort(out.begin(), out.end());
    return out;
}

static std::string path_to_p(PNode *root, PNode *want) {
    if (root == nullptr) return "\x01";
    if (root == want) return "";
    std::string sub = path_to_p(root->left, want);
    if (sub != "\x01") return "L" + sub;
    sub = path_to_p(root->right, want);
    if (sub != "\x01") return "R" + sub;
    return "\x01";
}

static PNode *resolve_p(PNode *root, const std::string &path) {
    PNode *cur = root;
    for (char ch : path) {
        if (cur == nullptr) return nullptr;
        cur = (ch == 'L') ? cur->left : cur->right;
    }
    return cur;
}

static bool has_value(const std::vector<int> &v, int x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}

static bool has_duplicate(const std::vector<int> &v) {
    for (std::size_t i = 1; i < v.size(); ++i)
        if (v[i] == v[i - 1]) return true;
    return false;
}

static Res g01(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        const std::string &want_s = rows[i][0];
        TreeNode *want = build(parse_arr(want_s));
        std::vector<int> pre = preorder(want), ino;
        inorder(want, ino);
        TreeNode *got = buildTreePreIn(pre, ino);
        std::string gs = dump(got);
        if (gs != want_s) fail("G01_build_pre_in", static_cast<int>(i), "got " + gs + " want " + want_s);
        h = hash_dump(h, dump_ints(got));
        ++n;
    }
    return Res(n, h);
}

static Res g02(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        const std::string &want_s = rows[i][0];
        TreeNode *want = build(parse_arr(want_s));
        std::vector<int> ino, post = postorder(want);
        inorder(want, ino);
        TreeNode *got = buildTreeInPost(ino, post);
        std::string gs = dump(got);
        if (gs != want_s) fail("G02_build_in_post", static_cast<int>(i), "got " + gs + " want " + want_s);
        h = hash_dump(h, dump_ints(got));
        ++n;
    }
    return Res(n, h);
}

static Res g03(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        const std::string &want_s = rows[i][0];
        TreeNode *want = build(parse_arr(want_s));
        std::string str = serialize(want);
        TreeNode *back = deserialize(str);
        std::string bs = dump(back);
        if (bs != want_s) fail("G03_serialize", static_cast<int>(i), "ser=" + str + " got " + bs + " want " + want_s);
        int size = count_nodes(want);
        std::vector<std::string> toks = str.empty() ? std::vector<std::string>() : split(str, ',');
        if (static_cast<int>(toks.size()) != 2 * size + 1) {
            fail("G03_serialize", static_cast<int>(i),
                 "token count " + std::to_string(toks.size()) + " want " + std::to_string(2 * size + 1));
        }
        if (size == 0 && str != "#") fail("G03_serialize", static_cast<int>(i), "空树序列化成 " + str);
        for (std::size_t k = 0; k < str.size(); ++k) h = phash(h, static_cast<unsigned char>(str[k]));
        h = hash_dump(h, dump_ints(back));
        n += 3;
    }
    return Res(n, h);
}

static Res g04(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        if (t == nullptr) { ++n; continue; }
        TreeNode *p = resolve(t, rows[i][1]);
        TreeNode *q = resolve(t, rows[i][2]);
        TreeNode *got = lowestCommonAncestor(t, p, q);
        TreeNode *want = brute_lca(t, p, q);
        if (got != want) {
            fail("G04_lca_recursive", static_cast<int>(i),
                 "got " + (got ? std::to_string(got->val) : std::string("null")) +
                 " want " + (want ? std::to_string(want->val) : std::string("null")));
        }
        h = hash_path(h, path_to(t, got));
        ++n;
    }
    return Res(n, h);
}

static Res g05(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        if (t == nullptr) { ++n; continue; }
        TreeNode *p = resolve(t, rows[i][1]);
        TreeNode *q = resolve(t, rows[i][2]);
        TreeNode *got = lowestCommonAncestorBST(t, p, q);
        TreeNode *want = brute_lca(t, p, q);
        if (got != want) {
            fail("G05_lca_bst", static_cast<int>(i),
                 "got " + (got ? std::to_string(got->val) : std::string("null")) +
                 " want " + (want ? std::to_string(want->val) : std::string("null")));
        }
        h = hash_path(h, path_to(t, got));
        ++n;
    }
    return Res(n, h);
}

static Res g06(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        PNode *t = build_pnode(parse_arr(rows[i][0]));
        if (t == nullptr) { ++n; continue; }
        PNode *p = resolve_p(t, rows[i][1]);
        PNode *q = resolve_p(t, rows[i][2]);
        PNode *got = lowestCommonAncestorParent(p, q);
        PNode *want = brute_lca_parent(p, q);
        if (got != want) {
            fail("G06_lca_parent", static_cast<int>(i),
                 "got " + (got ? std::to_string(got->val) : std::string("null")) +
                 " want " + (want ? std::to_string(want->val) : std::string("null")));
        }
        h = hash_path(h, path_to_p(t, got));
        ++n;
    }
    return Res(n, h);
}

static Res g07(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        if (t == nullptr) { ++n; continue; }
        TreeNode *p = resolve(t, rows[i][1]);
        TreeNode *q = resolve(t, rows[i][2]);
        TreeNode *got = lcaBinaryLifting(t, p, q);
        TreeNode *want = brute_lca(t, p, q);
        if (got != want) {
            fail("G07_lca_lifting", static_cast<int>(i),
                 "got " + (got ? std::to_string(got->val) : std::string("null")) +
                 " want " + (want ? std::to_string(want->val) : std::string("null")));
        }
        h = hash_path(h, path_to(t, got));
        ++n;
    }
    return Res(n, h);
}

static Res g08(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        if (t == nullptr) { ++n; continue; }
        int k = std::stoi(rows[i][1]);
        int got = kthSmallest(t, k);
        std::vector<int> srt;
        inorder(t, srt);
        int want = srt[static_cast<std::size_t>(k - 1)];
        if (got != want) {
            fail("G08_kth_smallest", static_cast<int>(i),
                 "k=" + std::to_string(k) + " got " + std::to_string(got) +
                 " want " + std::to_string(want));
        }
        h = phash(h, got);
        ++n;
    }
    return Res(n, h);
}

static Res g09(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        std::vector<int> vals = parse_arr(rows[i][0]);
        std::vector<std::pair<std::string, int>> want = convert_expected(build(vals));
        TreeNode *t = build(vals);
        convertBST(t);
        std::vector<std::pair<std::string, int>> got = path_values(t);
        if (got != want) {
            fail("G09_convert_bst", static_cast<int>(i), "转换结果和独立算法不一致");
        }
        h = hash_dump(h, dump_ints(t));
        ++n;
    }
    return Res(n, h);
}

static Res g10(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        bool got = isValidBST(t);
        std::vector<int> seq;
        inorder(t, seq);
        bool want = true;
        for (std::size_t j = 1; j < seq.size(); ++j)
            if (!(seq[j - 1] < seq[j])) want = false;
        if (got != want) {
            fail("G10_is_valid_bst", static_cast<int>(i),
                 std::string("got ") + (got ? "True" : "False") + " want " + (want ? "True" : "False"));
        }
        h = phash(h, got ? 1 : 0);
        ++n;
    }
    return Res(n, h);
}

static Res g11(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        int target = std::stoi(rows[i][1]);
        TreeNode *got = searchBST(t, target);
        TreeNode *want = nullptr;
        std::vector<TreeNode *> all;
        collect(t, all);
        for (TreeNode *x : all) {
            if (x->val == target) { want = x; break; }
        }
        if (got != want) {
            fail("G11_search_bst", static_cast<int>(i),
                 "target=" + std::to_string(target) + " got " +
                 (got ? std::to_string(got->val) : std::string("null")) + " want " +
                 (want ? std::to_string(want->val) : std::string("null")));
        }
        h = phash(h, got == nullptr ? -1 : got->val);
        ++n;
    }
    return Res(n, h);
}

static Res g12(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        int val = std::stoi(rows[i][1]);
        std::vector<int> before;
        inorder(t, before);
        TreeNode *root = insertIntoBST(t, val);
        std::vector<int> seq;
        inorder(root, seq);
        std::vector<int> want = before;                 // 重复值直接原样返回
        if (!has_value(before, val)) {
            want.push_back(val);
            std::sort(want.begin(), want.end());
        }
        if (seq != want) fail("G12_insert_bst", static_cast<int>(i), "val=" + std::to_string(val) + " 中序不对");
        if (has_duplicate(seq)) fail("G12_insert_bst", static_cast<int>(i), "插入后出现重复值");
        h = hash_dump(h, dump_ints(root));
        n += 2;
    }
    return Res(n, h);
}

static Res g13(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        int key = std::stoi(rows[i][1]);
        std::vector<int> before;
        inorder(t, before);
        std::vector<int> want = before;
        for (std::size_t j = 0; j < want.size(); ++j) {
            if (want[j] == key) { want.erase(want.begin() + static_cast<std::ptrdiff_t>(j)); break; }
        }
        TreeNode *root = deleteNode(t, key);
        std::vector<int> seq;
        inorder(root, seq);
        if (seq != want) fail("G13_delete_bst", static_cast<int>(i), "key=" + std::to_string(key) + " 中序不对");
        if (has_duplicate(seq)) fail("G13_delete_bst", static_cast<int>(i), "删除后出现重复值");
        h = hash_dump(h, dump_ints(root));
        n += 2;
    }
    return Res(n, h);
}

static Res g14(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        int got = countNodes(t);
        int want = count_nodes(t);
        if (got != want) {
            fail("G14_count_nodes", static_cast<int>(i),
                 "got " + std::to_string(got) + " want " + std::to_string(want));
        }
        h = phash(h, got);
        ++n;
    }
    return Res(n, h);
}

static Res g15(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        std::vector<int> vals = parse_arr(rows[i][0]);
        TreeNode *t1 = build(vals);
        invertTreeTraverse(t1);
        TreeNode *t2 = build(vals);
        invertTreeDivide(t2);
        if (dump(t1) != dump(t2)) {
            fail("G15_invert", static_cast<int>(i), "两个版本不一致");
        }
        // 独立校验:每个节点的路径把 L/R 互换之后,值应该对上
        std::vector<std::pair<std::string, int>> got = path_values(t1);
        std::vector<std::pair<std::string, int>> want;
        for (const std::pair<std::string, int> &pr : path_values(build(vals)))
            want.push_back({swap_lr(pr.first), pr.second});
        std::sort(want.begin(), want.end());
        if (got != want) fail("G15_invert", static_cast<int>(i), "路径镜像对不上");
        h = hash_dump(h, dump_ints(t1));
        n += 2;
    }
    return Res(n, h);
}

static Res g16(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        std::vector<int> want = preorder(t);
        flatten(t);
        std::vector<int> got;
        TreeNode *cur = t;
        int guard = 0;
        while (cur != nullptr && guard <= static_cast<int>(want.size()) + 1) {
            got.push_back(cur->val);
            if (cur->left != nullptr) {
                fail("G16_flatten", static_cast<int>(i), "left 没有置空");
                break;
            }
            cur = cur->right;
            ++guard;
        }
        if (got != want) fail("G16_flatten", static_cast<int>(i), "right 链和前序不一致");
        if (cur != nullptr) fail("G16_flatten", static_cast<int>(i), "right 链有环");
        for (std::size_t k = 0; k < got.size(); ++k) h = phash(h, got[k]);
        h = phash(h, 555);
        ++n;
    }
    return Res(n, h);
}

static Res g17(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        NNode *t = build_nnode(parse_arr(rows[i][0]));
        connect(t);
        std::vector<std::vector<NNode *>> levels;
        std::vector<NNode *> q;
        if (t != nullptr) q.push_back(t);
        while (!q.empty()) {
            levels.push_back(q);
            std::vector<NNode *> nxt;
            for (NNode *x : q) {
                if (x->left != nullptr) nxt.push_back(x->left);
                if (x->right != nullptr) nxt.push_back(x->right);
            }
            q = nxt;
        }
        std::map<NNode *, int> pos;
        for (std::size_t lv = 0; lv < levels.size(); ++lv)
            for (std::size_t j = 0; j < levels[lv].size(); ++j) pos[levels[lv][j]] = static_cast<int>(j);
        for (std::size_t lv = 0; lv < levels.size(); ++lv) {
            for (std::size_t j = 0; j < levels[lv].size(); ++j) {
                NNode *x = levels[lv][j];
                NNode *want = (j + 1 < levels[lv].size()) ? levels[lv][j + 1] : nullptr;
                if (x->next != want) {
                    fail("G17_connect", static_cast<int>(i),
                         "第 " + std::to_string(lv) + " 层第 " + std::to_string(j) + " 个 next 不对");
                }
                h = phash(h, x->next == nullptr ? -1 : pos[x->next] + 1);
            }
        }
        ++n;
    }
    return Res(n, h);
}

static Res g18(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *t = build(parse_arr(rows[i][0]));
        TreeNode *s = build(parse_arr(rows[i][1]));
        bool got = isSubtree(t, s);
        bool want = false;
        if (s == nullptr) {
            want = true;
        } else {
            std::vector<TreeNode *> all;
            collect(t, all);
            for (TreeNode *x : all) {
                if (same_tree(x, s)) { want = true; break; }
            }
        }
        if (got != want) {
            fail("G18_is_subtree", static_cast<int>(i),
                 std::string("got ") + (got ? "True" : "False") + " want " + (want ? "True" : "False"));
        }
        h = phash(h, got ? 1 : 0);
        ++n;
    }
    return Res(n, h);
}

static Res g19(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        TreeNode *ta = build(parse_arr(rows[i][0]));
        TreeNode *tb = build(parse_arr(rows[i][1]));
        std::map<std::string, int> want;
        for (int k = 0; k < 2; ++k) {
            std::vector<std::pair<std::string, int>> pv =
                path_values(build(parse_arr(rows[i][static_cast<std::size_t>(k)])));
            for (const std::pair<std::string, int> &pr : pv) want[pr.first] += pr.second;
        }
        std::vector<std::pair<std::string, int>> wv(want.begin(), want.end());
        std::vector<std::pair<std::string, int>> got = path_values(mergeTrees(ta, tb));
        if (got != wv) fail("G19_merge", static_cast<int>(i), "合并结果和独立算法不一致");
        for (const std::pair<std::string, int> &pr : got) {
            h = phash(h, pr.second);
            int sum = 0;
            for (char ch : pr.first) sum += ch;
            h = phash(h, sum);
        }
        h = phash(h, 444);
        ++n;
    }
    return Res(n, h);
}

static Res g20(const std::vector<Row> &rows) {
    unsigned int h = 0; int n = 0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        std::vector<int> vals = parse_arr(rows[i][0]);
        int got = rob(build(vals));
        int want = rob_brute(build(vals));
        if (got != want) {
            fail("G20_rob", static_cast<int>(i),
                 "got " + std::to_string(got) + " want " + std::to_string(want));
        }
        h = phash(h, got);
        ++n;
    }
    return Res(n, h);
}

struct GroupDef {
    const char *name;
    Res (*run)(const std::vector<Row> &);
};

}  // namespace H

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "usage: binary_tree_advanced_run <cases.txt>\n";
        return 2;
    }
    std::ifstream in(argv[1]);
    if (!in) {
        std::cerr << "cannot open " << argv[1] << "\n";
        return 2;
    }
    std::vector<std::pair<std::string, H::Row>> all;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::vector<std::string> parts = H::split(line, '|');
        H::Row payload(parts.begin() + 1, parts.end());
        all.push_back({parts[0], payload});
    }
    const H::GroupDef groups[] = {
        {"G01_build_pre_in", H::g01}, {"G02_build_in_post", H::g02},
        {"G03_serialize", H::g03}, {"G04_lca_recursive", H::g04},
        {"G05_lca_bst", H::g05}, {"G06_lca_parent", H::g06},
        {"G07_lca_lifting", H::g07}, {"G08_kth_smallest", H::g08},
        {"G09_convert_bst", H::g09}, {"G10_is_valid_bst", H::g10},
        {"G11_search_bst", H::g11}, {"G12_insert_bst", H::g12},
        {"G13_delete_bst", H::g13}, {"G14_count_nodes", H::g14},
        {"G15_invert", H::g15}, {"G16_flatten", H::g16},
        {"G17_connect", H::g17}, {"G18_is_subtree", H::g18},
        {"G19_merge", H::g19}, {"G20_rob", H::g20},
    };
    for (const H::GroupDef &g : groups) {
        std::vector<H::Row> rows;
        for (const std::pair<std::string, H::Row> &pr : all)
            if (pr.first == g.name) rows.push_back(pr.second);
        H::Res res = g.run(rows);
        H::group(g.name, res.first, res.second);
    }
    for (std::size_t i = 0; i < H::g_out.size(); ++i) std::cout << H::g_out[i] << "\n";
    return H::g_fails ? 1 : 0;
}
"""

if __name__ == "__main__":
    sys.exit(main())
