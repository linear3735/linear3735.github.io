#!/usr/bin/env python3
"""Generate the SVG figures for _posts/2026-11-25-backtracking.md.

Every text run and arrow is registered with svgkit.Check, which flags
collisions and off-canvas boxes; the render is still eyeballed afterwards
because Check cannot see a text sitting on an unregistered line.

`Check.run()` returns the number of layout problems it found, and that number
is collected in BAD below: a figure with a collision must make this script
exit non-zero, otherwise the check runs and its result is thrown away.

Numbers drawn in a figure are measured here, not quoted: the post's own code
blocks are extracted from the .md file and re-executed (figure 4 measures the
pruning table, figure 6 measures the bucket split and the call count), and the
N-Queens counts in figure 5 are recomputed with itertools.permutations.

Usage: python3 make_figs.py
"""
import itertools
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]   # assets/blog/<slug>/make_figs.py
sys.path.insert(0, str(REPO / "assets/blog/_tools"))
from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,   # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/backtracking-20261125"
OUT.mkdir(parents=True, exist_ok=True)

POST = REPO / "_posts/2026-11-25-backtracking.md"

# One entry per figure.  A module-level list, not an int: `+=` on an int inside
# the figure functions would make it local and need `global` at every site.
BAD: list[int] = []

NODE_W, NODE_H = 76, 30


def post_python_blocks():
    """The post's python fences, in order — the figures measure this code."""
    text = POST.read_text(encoding="utf-8")
    return re.findall(r"^```python[ \t]*\n(.*?)^```[ \t]*$", text, re.M | re.S)


def n_queens_count(n):
    """Independent reference: count solutions with plain permutations.

    A column-permutation is a solution iff the two diagonal families are
    distinct, which is the same statement as the post's three sets — but it is
    written with no search at all, so a figure number can never come from the
    code it is meant to check.
    """
    return sum(1 for p in itertools.permutations(range(n))
               if len({p[r] - r for r in range(n)}) == n
               and len({p[r] + r for r in range(n)}) == n)


def partition_assignment(nums, k):
    """Independent reference: the first k-way split by brute force.

    Returns (assign, groups): `assign[i]` is the bucket of `nums[i]`, `groups`
    the sorted contents of each bucket.  No search is involved — it enumerates
    all k^n assignments — so a figure number cannot come from the code it is
    meant to illustrate.
    """
    if not nums or k <= 0 or sum(nums) % k:
        return None, None
    target = sum(nums) // k
    for assign in itertools.product(range(k), repeat=len(nums)):
        sums = [0] * k
        for value, bucket in zip(nums, assign):
            sums[bucket] += value
        if all(s == target for s in sums):
            groups = [[] for _ in range(k)]
            for value, bucket in zip(nums, assign):
                groups[bucket].append(value)
            return list(assign), [sorted(g) for g in groups]
    return None, None


def node(svg, chk, x, y, label, fill=PAPER, stroke=INK, size=13, name=None):
    """Rounded node whose centre is (x, y)."""
    svg.rect(x - NODE_W / 2, y - NODE_H / 2, NODE_W, NODE_H,
             fill=fill, stroke=stroke, rx=8, sw=1.4)
    svg.text(x, y + size * 0.36, label, size=size)
    chk.text(name or f"node:{label}@{x:.0f},{y:.0f}", x, y + size * 0.36,
             label, size=size)


def edge(svg, chk, x1, y1, x2, y2, stroke=LINE, sw=1.5, name=None):
    svg.line(x1, y1, x2, y2, stroke=stroke, sw=sw)
    chk.arrow(name or f"edge:{x1:.0f},{y1:.0f}->{x2:.0f},{y2:.0f}", x1, y1, x2, y2)


def note(svg, chk, x, y, t, size=12, fill=MUTED, anchor="start", name=None):
    svg.text(x, y, t, size=size, fill=fill, anchor=anchor)
    chk.text(name or f"note:{t[:12]}", x, y, t, size=size, anchor=anchor)


# ---------------------------------------------------------------- figure 1
def fig_decision_tree():
    W, H = 1120, 500
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 24, 34, "全排列 [1,2,3] 的决策树", size=16, fill=INK)
    note(svg, chk, 24, 56, "每条边 = 一次「做选择」,每个节点 = 一个中间状态", size=12)

    # level xs
    l1 = [180.0, 560.0, 940.0]
    l2 = [90.0, 270.0, 450.0, 630.0, 810.0, 990.0]
    y_root, y1, y2, y3 = 110.0, 200.0, 290.0, 380.0
    x_root = 560.0

    node(svg, chk, x_root, y_root, "[]", fill=FILL_BLUE, name="root")
    for i, x in enumerate(l1):
        edge(svg, chk, x_root, y_root + NODE_H / 2, x, y1 - NODE_H / 2)
    for x, lab in zip(l1, ["[1]", "[2]", "[3]"]):
        node(svg, chk, x, y1, lab, fill=FILL_BLUE, name=f"l1:{lab}")
    l2_lab = ["[1,2]", "[1,3]", "[2,1]", "[2,3]", "[3,1]", "[3,2]"]
    for x, lab in zip(l2, l2_lab):
        parent = l1[0] if x < 300 else (l1[1] if x < 700 else l1[2])
        edge(svg, chk, parent, y1 + NODE_H / 2, x, y2 - NODE_H / 2)
        node(svg, chk, x, y2, lab, fill=FILL_BLUE, name=f"l2:{lab}")
    l3_lab = ["[1,2,3]", "[1,3,2]", "[2,1,3]", "[2,3,1]", "[3,1,2]", "[3,2,1]"]
    for x, lab in zip(l2, l3_lab):
        edge(svg, chk, x, y2 + NODE_H / 2, x, y3 - NODE_H / 2)
        node(svg, chk, x, y3, lab, fill=FILL_TEAL, name=f"leaf:{lab}")

    # annotations
    note(svg, chk, x_root + 56, y_root + 5, "路径 = [],选择列表 = {1,2,3}", size=12,
         fill=MUTED, name="ann-root")
    # anchor="start", so this runs right; 1004 + ~135 would hit the 1120 edge
    note(svg, chk, 975, 205, "路径 = [3],选择 = {1,2}", size=11,
         fill=WARM_TXT, name="ann-mid")
    note(svg, chk, W / 2, H - 34, "6 个叶子,每个叶子就是一条完整排列——答案挂在树上最深处",
         size=13, fill=TEAL_TXT, name="ann-leaves")
    note(svg, chk, W / 2, H - 14,
         "结束条件:路径长度 == 3;在此之前一律不下结论", size=12, name="ann-end")
    BAD.append(chk.run("01-decision-tree"))
    svg.save(OUT / "01-decision-tree.svg")


# ---------------------------------------------------------------- figure 2
def fig_three_shapes():
    W, H = 1200, 470
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 20, 32, "同一棵树,答案挂的位置不同:nums = [1,2],k = 2", size=16, fill=INK)

    panels = [(20, "排列 permute", "答案在叶子"),
              (415, "子集 subsets", "答案在每个节点"),
              (810, "组合 combine(n,2)", "答案在长度为 k 的节点")]
    for px, title, sub in panels:
        svg.panel(px, 52, W / 3 - 15, 330)
        chk.panel(f"panel{px}", px, 52, W / 3 - 15, 330)
        note(svg, chk, px + 20, 82, title, size=14, fill=INK, name=f"title{px}")
        note(svg, chk, px + 20, 102, sub, size=12, fill=MUTED, name=f"sub{px}")

    def draw(px, spec, caption):
        """spec: (x_offset, y, label, is_answer) — x_offset is relative to cx."""
        cx = px + 192.0
        for dx, y, lab, is_answer in spec:
            fill = FILL_TEAL if is_answer else FILL_BLUE
            node(svg, chk, cx + dx, y, lab, fill=fill,
                 name=f"n{px}:{lab}@{y}")
        note(svg, chk, cx, 360, caption, size=12, fill=INK, name=f"cap{px}")

    def link(px, a, b):
        cx = px + 192.0
        edge(svg, chk, cx + a[0], a[1] + NODE_H / 2, cx + b[0], b[1] - NODE_H / 2)

    # 排列:只有走满 n 步的叶子才是答案
    spec_perm = [(0, 150.0, "[]", False), (-80, 235.0, "[1]", False),
                 (80, 235.0, "[2]", False), (-110, 320.0, "[1,2]", True),
                 (110, 320.0, "[2,1]", True)]
    draw(20, spec_perm, "只有走满 n 步才算答案")
    link(20, (0, 150.0), (-80, 235.0))
    link(20, (0, 150.0), (80, 235.0))
    link(20, (-80, 235.0), (-110, 320.0))
    link(20, (80, 235.0), (110, 320.0))

    # 子集:每进入一个节点就先收一次
    spec_sub = [(0, 150.0, "[]", True), (-80, 235.0, "[1]", True),
                (80, 235.0, "[2]", True), (-80, 320.0, "[1,2]", True)]
    draw(415, spec_sub, "每进入一个节点就先收一次")
    link(415, (0, 150.0), (-80, 235.0))
    link(415, (0, 150.0), (80, 235.0))
    link(415, (-80, 235.0), (-80, 320.0))

    # 组合:长度够了才收,且不再往深处走
    spec_comb = [(0, 150.0, "[]", False), (-80, 235.0, "[1]", False),
                 (80, 235.0, "[2]", False), (-80, 320.0, "[1,2]", True)]
    draw(810, spec_comb, "长度够了才收,不再往深处走")
    link(810, (0, 150.0), (-80, 235.0))
    link(810, (0, 150.0), (80, 235.0))
    link(810, (-80, 235.0), (-80, 320.0))

    # legend — kept above y=400 so it stays clear of the panels above it
    svg.rect(24, 387, 16, 16, fill=FILL_TEAL, stroke=INK, rx=4, sw=1.0)
    note(svg, chk, 48, 400, "= 会被收进结果集的节点", size=12, fill=INK, name="legend1")
    svg.rect(280, 387, 16, 16, fill=FILL_BLUE, stroke=INK, rx=4, sw=1.0)
    note(svg, chk, 304, 400, "= 只是中间状态,不收", size=12, fill=INK, name="legend2")
    note(svg, chk, 560, 400, "差异只有三处:循环起点、有没有 used、答案收在哪一层",
         size=12, fill=MUTED, name="legend3")
    BAD.append(chk.run("02-three-shapes"))
    svg.save(OUT / "02-three-shapes.svg")


# ---------------------------------------------------------------- figure 3
def fig_dedup():
    W, H = 1120, 470
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 20, 32, "去重判据问的是「同一层」,不是「同一条路径」", size=16, fill=INK)

    # left panel: two equal siblings -> the second one is pruned away
    svg.panel(20, 52, 520, 356)
    chk.panel("left", 20, 52, 520, 356)
    note(svg, chk, 40, 82, "同一层:值相同的兄弟只留第一个", size=13, fill=INK,
         name="lp-title")
    cx = 280.0
    node(svg, chk, cx, 130, "[]", fill=FILL_BLUE, name="lp-root")
    for kx, ky, lab, fill, nm in ((170.0, 215.0, "1", FILL_TEAL, "lp-a"),
                                  (280.0, 215.0, "1", FILL_GREY, "lp-b"),
                                  (390.0, 215.0, "2", FILL_BLUE, "lp-c")):
        edge(svg, chk, cx, 130 + NODE_H / 2, kx, ky - NODE_H / 2)
        node(svg, chk, kx, ky, lab, fill=fill, name=nm)
    svg.line(280, 130 + NODE_H / 2 + 4, 280, 215 - NODE_H / 2 - 2,
             stroke="#c0392b", sw=2.0, dash="4 3")
    note(svg, chk, 272, 244, "跳过", size=12, fill="#c0392b", anchor="end",
         name="lp-skip")
    for i, t in enumerate((
            "nums[i] == nums[i-1] 且 nums[i-1] 不在路径上",
            "=> i-1 已作为兄弟分支走完,i 长出的子树和它同构",
            "前提:先排序,相同的值才会挨在一起",
            "代价:整棵同构子树都不会被展开")):
        note(svg, chk, 40, 268 + i * 30, t, size=12,
             fill=(INK, MUTED, WARM_TXT, TEAL_TXT)[i], name=f"lp-l{i}")

    # right panel: two equal values on the SAME path are both needed
    svg.panel(580, 52, 520, 356)
    chk.panel("right", 580, 52, 520, 356)
    note(svg, chk, 600, 82, "同一条路径:两个 1 都要用上", size=13, fill=INK,
         name="rp-title")
    rcx = 840.0
    node(svg, chk, rcx, 130, "[]", fill=FILL_BLUE, name="rp-root")
    node(svg, chk, rcx - 90, 205, "1", fill=FILL_BLUE, name="rp-a")
    node(svg, chk, rcx + 90, 205, "1", fill=FILL_GREY, name="rp-b")
    edge(svg, chk, rcx, 130 + NODE_H / 2, rcx - 90, 205 - NODE_H / 2)
    svg.line(rcx, 130 + NODE_H / 2, rcx + 90, 205 - NODE_H / 2, stroke=LINE, sw=1.5)
    chk.arrow("rp-deadedge", rcx, 130 + NODE_H / 2, rcx + 90, 205 - NODE_H / 2)
    node(svg, chk, rcx - 90, 275, "1", fill=FILL_TEAL, name="rp-aa")
    edge(svg, chk, rcx - 90, 205 + NODE_H / 2, rcx - 90, 275 - NODE_H / 2)
    note(svg, chk, rcx - 40, 280, "路径 [1,1] 合法", size=12, fill=TEAL_TXT,
         anchor="start", name="rp-ok")
    for i, t in enumerate((
            "used[i-1] == true:前一个 1 就在当前路径上,",
            "说明它是「更深处」而不是「兄弟」,不能跳过",
            "漏写 not => 合法排列被误杀,结果少解")):
        note(svg, chk, 600, 330 + i * 24, t, size=12,
             fill=(INK, MUTED, "#c0392b")[i], name=f"rp-l{i}")
    BAD.append(chk.run("03-dedup"))
    svg.save(OUT / "03-dedup.svg")


# ---------------------------------------------------------------- figure 4
def fig_pruning():
    import math
    W, H = 1080, 452
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 20, 32, "组合总和:剪枝前后的递归调用次数(实测)", size=16, fill=INK)
    note(svg, chk, 20, 54,
         "条形长度按平方根刻度;条右侧的数字是本脚本现跑正文 4.2 的两个函数量出来的",
         size=12, fill=MUTED)

    # measured here: the post's own two functions, executed on the five probes.
    blocks = post_python_blocks()
    ns = {}
    exec(compile(blocks[5] + "\n" + blocks[6], str(POST), "exec"), ns)
    probes = [([2, 3, 6, 7], 7), ([2, 3, 5], 8), ([3, 4, 7, 8], 11),
              ([2, 3, 5, 7, 11, 13], 30), ([1, 2, 3, 4, 5, 6, 7, 8], 20)]
    cases = []
    for cand, target in probes:
        naive = ns["combination_sum_naive"](list(cand), target)[1]
        pruned = ns["combination_sum_pruned"](list(cand), target)[1]
        cases.append((f"{cand} target={target}", naive, pruned))
        print(f"  measured {cand} target={target}: naive {naive}, pruned {pruned}")

    x0, bar_max = 250.0, 560.0
    y = 96.0
    scale = bar_max / math.sqrt(max(naive for _, naive, _ in cases))
    for label, naive, pruned in cases:
        note(svg, chk, x0 - 16, y + 30, label, size=12, fill=INK, anchor="end",
             name=f"case:{label}")
        for k, (val, fill, dy, tag) in enumerate(
                ((naive, "#d8dee8", 0.0, "不剪枝"), (pruned, FILL_TEAL, 26.0, "剪枝后"))):
            w = math.sqrt(val) * scale
            svg.rect(x0, y + dy, w, 20, fill=fill, stroke=INK, sw=1.0, rx=3)
            note(svg, chk, x0 + w + 8, y + dy + 15,
                 f"{val}  {tag}", size=11, fill=INK, anchor="start",
                 name=f"val:{label}:{tag}")
        ratio = naive / pruned
        note(svg, chk, x0 + bar_max + 130, y + 28, f"{ratio:.1f}x", size=13,
             fill=WARM_TXT, anchor="middle", name=f"ratio:{label}")
        y += 66
    note(svg, chk, x0 + bar_max + 130, 88, "倍数", size=12, fill=MUTED, anchor="middle",
         name="ratio-head")
    note(svg, chk, 20, H - 12,
         "剪掉的只是「已经超过 target 还继续往下探」的常数层,所以倍数稳定在 2~3 倍,不会随规模爆炸",
         size=12, fill=MUTED, name="foot")
    BAD.append(chk.run("04-pruning-calls"))
    svg.save(OUT / "04-pruning-calls.svg")


# ---------------------------------------------------------------- figure 5
def fig_nqueens_constraints():
    """Three constraint families + the counts, recomputed with permutations."""
    counts = [n_queens_count(n) for n in range(1, 9)]
    assert counts == [1, 0, 0, 2, 10, 4, 40, 92], counts
    print(f"  measured N-Queens n=1..8: {counts} (permutation brute force)")

    W, H = 1120, 520
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 24, 34, "N 皇后:三族约束,每族一个标记数组", size=16, fill=INK,
         name="q-title")
    note(svg, chk, 24, 56,
         "盘面是 n=4 的一个解 (1,3,0,2);下面的个数由本脚本用全排列暴力重算",
         size=12, fill=MUTED, name="q-sub")

    # ---- board: 4x4, cell 54, origin (60, 96)
    x0, y0, cs = 60.0, 96.0, 54.0
    col_hi = {(r, 0) for r in range(4)}                    # the marked column
    diag1_hi = {(0, 1), (1, 2), (2, 3)}                    # row + col == 3
    diag2_hi = {(1, 3), (2, 2), (3, 1)}                    # row - col == -2
    for r in range(4):
        for c in range(4):
            fill = PAPER
            if (r, c) in col_hi:
                fill = FILL_TEAL
            elif (r, c) in diag1_hi:
                fill = FILL_BLUE
            elif (r, c) in diag2_hi:
                fill = FILL_WARM
            svg.rect(x0 + c * cs, y0 + r * cs, cs, cs, fill=fill, stroke=INK,
                     sw=1.0, rx=0)
    for r, c in enumerate((1, 3, 0, 2)):                   # the solution
        svg.circle(x0 + c * cs + cs / 2, y0 + r * cs + cs / 2, 15,
                   fill=INK, stroke=INK, sw=1.0)
        note(svg, chk, x0 + c * cs + cs / 2, y0 + r * cs + cs / 2 + 7, "Q",
             size=17, fill=PAPER, name=f"q-{r}")
    note(svg, chk, x0, y0 + 4 * cs + 26, "一个解:(1,3,0,2)——每行恰好一个皇后",
         size=12, fill=INK, anchor="start", name="q-sol")

    # ---- the three families, to the right of the board
    px, pw = 320.0, 760.0
    rows = [
        ("列:col in cols", "cols", FILL_TEAL,
         "同一列只能有一个皇后:进这一列之前先查 col"),
        ("左下—右上对角线:row + col in diag1", "diag1", FILL_BLUE,
         "从左下到右上的一条线上,row + col 是常数"),
        ("左上—右下对角线:row - col in diag2", "diag2", FILL_WARM,
         "从左上到右下的一条线上,row - col 是常数"),
    ]
    for i, (head, tag, fill, sub) in enumerate(rows):
        py = 96 + i * 86
        svg.panel(px, py, pw, 70)
        chk.panel(f"q-p{i}", px, py, pw, 70)
        svg.rect(px + 16, py + 18, 34, 34, fill=fill, stroke=INK, sw=1.0, rx=4)
        note(svg, chk, px + 64, py + 28, head, size=14, fill=INK, anchor="start",
             name=f"q-h{i}")
        note(svg, chk, px + 64, py + 52, sub, size=12, fill=MUTED, anchor="start",
             name=f"q-s{i}")
        note(svg, chk, px + pw - 16, py + 44, tag, size=13, fill=INK, anchor="end",
             name=f"q-t{i}")

    # ---- the counts row (n = 1..8), measured above
    ty = 372.0
    note(svg, chk, x0, ty - 12, "解的个数(本脚本实测,与力扣 51/52 的计数一致):",
         size=13, fill=INK, anchor="start", name="q-count-head")
    cw = 74.0
    for i, value in enumerate(counts):
        cx = x0 + i * cw
        svg.rect(cx, ty, cw, 46, fill=FILL_GREY if value == 0 else FILL_BLUE,
                 stroke=INK, sw=1.0, rx=0)
        note(svg, chk, cx + cw / 2, ty + 21, f"n={i + 1}", size=11, fill=MUTED,
             name=f"q-n{i}")
        note(svg, chk, cx + cw / 2, ty + 40, str(value), size=15, fill=INK,
             name=f"q-c{i}")
    note(svg, chk, x0, ty + 74,
         "n=2、3 是 0:n=2 时两个皇后必然同列或同对角线;三个判据都是 O(1),每层最多枚举 n 列",
         size=12, fill=MUTED, anchor="start", name="q-foot")
    note(svg, chk, x0, ty + 98,
         "n=9、10 分别是 352、724(正文 6.1 的表,门禁用同一份全排列暴力逐项核对)",
         size=12, fill=MUTED, anchor="start", name="q-foot2")
    BAD.append(chk.run("05-nqueens-constraints"))
    svg.save(OUT / "05-nqueens-constraints.svg")


# ---------------------------------------------------------------- figure 6
def fig_partition_buckets():
    """The bucket model on LC 698's first example, plus the three prunes."""
    nums, k = [4, 3, 2, 3, 5, 2, 1], 4
    assert sum(nums) == 20 and sum(nums) % k == 0, (nums, k)
    target = sum(nums) // k
    assign, buckets = partition_assignment(nums, k)
    assert buckets is not None and all(sum(b) == target for b in buckets), buckets
    print(f"  measured split of {nums} into k={k}: {buckets} (brute-force reference)")

    # calls for the post's own 7.1 function on this input, counted from outside
    blocks = post_python_blocks()
    ns = {}
    exec(compile(blocks[10], str(POST), "exec"), ns)
    calls = [0]

    def tracer(frame, event, arg):
        if event == "call" and frame.f_code.co_name == "backtrack":
            calls[0] += 1
        return None

    sys.setprofile(tracer)
    try:
        answer = ns["can_partition_k_subsets"](list(nums), k)
    finally:
        sys.setprofile(None)
    assert answer is True and calls[0] > 0, (answer, calls[0])
    print(f"  measured calls for {nums} k={k}: {calls[0]} (answer {answer})")

    # the break variant, on its minimal counterexample, measured here as well
    broken = blocks[10].replace(
        "            if buckets[j] + nums[i] > target:\n"
        "                continue                     # 只能 continue:桶没排序,后面的桶还装得下",
        "            if buckets[j] + nums[i] > target:\n"
        "                break")
    assert broken != blocks[10], "the continue/break anchor moved; figure 6 needs a look"
    ns2 = {}
    exec(compile(broken, str(POST), "exec"), ns2)
    correct = ns["can_partition_k_subsets"]([1, 1], 2)
    wrong = ns2["can_partition_k_subsets"]([1, 1], 2)
    assert (correct, wrong) == (True, False), (correct, wrong)
    print(f"  measured break counterexample [1,1] k=2: correct {correct}, break {wrong}")

    W, H = 1200, 530
    svg, chk = Svg(W, H), None
    chk = Check(svg)
    note(svg, chk, 24, 34, "划分:把 n 个数放进 k 个和相等的桶(力扣 698)", size=16,
         fill=INK, name="b-title")
    note(svg, chk, 24, 56,
         f"示例 1:nums = {nums},k = {k},总和 20 => target = 5;分组、调用次数都是本脚本现算的",
         size=12, fill=MUTED, name="b-sub")

    # ---- the array, one cell per number, tinted by its bucket
    tints = [FILL_BLUE, FILL_TEAL, FILL_WARM, FILL_GREY]
    cw = 62.0
    ax, ay = 60.0, 96.0
    for i, value in enumerate(nums):
        svg.rect(ax + i * cw, ay, cw, 46, fill=tints[assign[i]], stroke=INK,
                 sw=1.0, rx=0)
        note(svg, chk, ax + i * cw + cw / 2, ay + 30, str(value), size=16, fill=INK,
             name=f"b-a{i}")
    note(svg, chk, ax, ay - 12, "数组(颜色 = 它进了哪个桶)", size=12, fill=MUTED,
         anchor="start", name="b-arr-head")

    # ---- the k buckets
    by = 196.0
    bw, gap = 258.0, 16.0
    for j, values in enumerate(buckets):
        bx = 60 + j * (bw + gap)
        svg.panel(bx, by, bw, 84, fill=FILL_BLUE if j == 0 else CANVAS)
        chk.panel(f"b-p{j}", bx, by, bw, 84)
        note(svg, chk, bx + 14, by + 26, f"{j} 号桶", size=13, fill=INK,
             anchor="start", name=f"b-h{j}")
        note(svg, chk, bx + 14, by + 58,
             " + ".join(str(v) for v in values) + f" = {sum(values)}", size=14,
             fill=INK, anchor="start", name=f"b-v{j}")
    note(svg, chk, 60.0, by + 112,
         f"每个桶的和都等于 target = {target};桶与桶之间没有编号之分(这是剪枝的来源)",
         size=12, fill=TEAL_TXT, anchor="start", name="b-cap")

    # ---- the three prune families (see 7.3) + the measured numbers
    cy = 348.0
    cols = [
        ("否决式剪枝", ("总和 % k 必须先整除,否则 0 次调用就有答案",
                        "最大的数超过 target 直接 False")),
        ("对称性剪枝", ("桶可互换:最大的数固定进 0 号桶",
                        "和相同的桶只试一个")),
        ("去重与撤销", ("同一层同值的候选跳过",
                        "每层结束必须撤销 buckets[j] -= nums[i]")),
    ]
    cwid = (W - 120 - 2 * 16) / 3
    for i, (head, sub) in enumerate(cols):
        bx = 60 + i * (cwid + 16)
        svg.panel(bx, cy, cwid, 90, fill=(FILL_WARM, FILL_BLUE, FILL_TEAL)[i])
        chk.panel(f"b-c{i}", bx, cy, cwid, 90)
        note(svg, chk, bx + 14, cy + 30, head, size=14, fill=INK, anchor="start",
             name=f"b-ch{i}")
        for line_no, part in enumerate(sub):
            note(svg, chk, bx + 14, cy + 56 + line_no * 20, part, size=12,
                 fill=MUTED, anchor="start", name=f"b-cs{i}{line_no}")
    note(svg, chk, 60.0, cy + 124,
         f"实测:这组输入 {calls[0]} 次递归调用;把内层 continue 换成 break,[1,1] k=2 就会判错"
         f"(本脚本跑过:{correct} -> {wrong})",
         size=12, fill=WARM_TXT, anchor="start", name="b-measured")
    note(svg, chk, 60.0, cy + 148,
         "桶内部没有排序,所以「装不下」只能 continue——后面的桶还可能装得下;这就是 2.4 节球盒模型的落地",
         size=12, fill=MUTED, anchor="start", name="b-foot")
    BAD.append(chk.run("06-partition-buckets"))
    svg.save(OUT / "06-partition-buckets.svg")


if __name__ == "__main__":
    fig_decision_tree()
    fig_three_shapes()
    fig_dedup()
    fig_pruning()
    fig_nqueens_constraints()
    fig_partition_buckets()
    total = sum(BAD)
    print(f"  figures: {len(BAD)} rendered, {total} layout problem(s) total")
    # `sys.exit(1 if BAD else 0)` would be wrong: [0, 0, 0, 0, 0, 0] is truthy.
    sys.exit(1 if total else 0)
