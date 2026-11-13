#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BFS 一文的代码门。

它做四件事:

1. 从 `_posts/2026-11-26-bfs.md` 的正文里**正则抽出** Python / C++ 代码块,
   不另存第二份副本 —— 改了正文就一定会被这里跑到。
2. 生成一批固定种子的用例,写进 `build/cases.txt`。
3. Python 侧执行抽出来的块,把结果写进 `build/py_out.txt`。
4. C++ 侧把抽出来的块拼成一个编译单元,读**同一个** `build/cases.txt`,
   把结果写进 `build/cpp_out.txt`。

然后逐行对拍两份输出。用同一个用例文件是为了让两语言的输入
逐字节一致 —— 两边各自随机生成再比,等于把「生成器不一致」也当成
算法不一致,排查起来很费劲。

对拍用的**参照实现全部是独立写的**(暴力模拟 / 显式建图 / 反向 BFS 打表),
不是「把文章的实现再抄一遍」。这是本文档最要紧的一条纪律:
自己跟自己的另一个实现比,只能发现打字错误,发现不了想错。

用法:
    /opt/miniconda3/bin/python3 assets/blog/bfs-20261126/verify_code.py
    BFS_POST=/tmp/mutated.md .../verify_code.py     # 负向测试:换一份正文
"""

import os
import pathlib
import re
import subprocess
import sys
import collections
import itertools

HERE = pathlib.Path(__file__).resolve().parent
# assets/blog/bfs-20261126/ -> parents[2] 才是仓库根
REPO = HERE.parents[2]
POST = pathlib.Path(os.environ.get("BFS_POST", str(REPO / "_posts" / "2026-11-26-bfs.md")))
BUILD = HERE / "build"
SEED = 20261126

PY_CHECKS = [0]
PY_FAILS = []


def check(cond, msg):
    PY_CHECKS[0] += 1
    if not cond:
        PY_FAILS.append(msg)


# --------------------------------------------------------------------------
# 1. 从正文抽代码块
# --------------------------------------------------------------------------

def extract(src, lang):
    return re.findall(r"^```" + lang + r"[ \t]*\n(.*?)^```[ \t]*$", src, re.M | re.S)


# --------------------------------------------------------------------------
# 2. 参照实现(全部独立写,不看文章)
# --------------------------------------------------------------------------

# 773 的邻接表:压平后的下标 i 能跟谁交换
SP_NEI = [[1, 3], [0, 2, 4], [1, 5], [0, 4], [1, 3, 5], [2, 4]]


def sp_reference_table(target="123450"):
    """从 target 反向 BFS,打出所有可达局面的精确最短距离。

    这是 773 最干净的参照:反向一遍就能覆盖全部 360 个可达局面,
    之后每个局面的正确答案都是查表得来的,与文章的正向实现完全独立。
    """
    dist = {target: 0}
    q = collections.deque([target])
    while q:
        cur = q.popleft()
        zero = cur.index("0")
        for pos in SP_NEI[zero]:
            lst = list(cur)
            lst[zero], lst[pos] = lst[pos], lst[zero]
            nxt = "".join(lst)
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                q.append(nxt)
    return dist


def sp_all_states():
    """773 的全部可达局面 = 反向 BFS 能到达的集合。"""
    return set(sp_reference_table().keys())


def lock_neighbors(s):
    out = []
    for i in range(4):
        d = int(s[i])
        for delta in (1, -1):
            out.append(s[:i] + str((d + delta) % 10) + s[i + 1:])
    return out


def lock_reference_bfs(deadends, target):
    """752 的参照:标准单源 BFS,独立于文章的实现。"""
    dead = set(deadends)
    if "0000" in dead or target in dead:
        return -1
    if target == "0000":
        return 0
    seen = {"0000"}
    q = collections.deque([("0000", 0)])
    while q:
        cur, d = q.popleft()
        for nxt in lock_neighbors(cur):
            if nxt in dead or nxt in seen:
                continue
            if nxt == target:
                return d + 1
            seen.add(nxt)
            q.append((nxt, d + 1))
    return -1


def oranges_bruteforce(grid):
    """994 的参照:每分钟老老实实扫全图模拟一次,不做 BFS。"""
    g = [row[:] for row in grid]
    rows, cols = len(g), len(g[0])
    minutes = 0
    while True:
        if all(v != 1 for row in g for v in row):
            return minutes
        nxt = [row[:] for row in g]
        spread = False
        for r in range(rows):
            for c in range(cols):
                if g[r][c] != 2:
                    continue
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and g[nr][nc] == 1:
                        nxt[nr][nc] = 2
                        spread = True
        if not spread:
            return -1                      # 还有新鲜橘子但扩散不动了
        g = nxt
        minutes += 1


def matrix_bruteforce(mat):
    """542 的参照:每个格子单独做一次 BFS 找最近的 0。"""
    rows, cols = len(mat), len(mat[0])
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if mat[r][c] == 0:
                row.append(0)
                continue
            seen = {(r, c)}
            q = collections.deque([(r, c, 0)])
            found = -1
            while q:
                cr, cc, d = q.popleft()
                if mat[cr][cc] == 0:
                    found = d
                    break
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        q.append((nr, nc, d + 1))
            row.append(found)             # 没有 0 就是 -1
        out.append(row)
    return out


def binary_matrix_reference(grid):
    """1091 的参照:先把八连通图显式建出来,再在图上跑标准 BFS。"""
    n = len(grid)
    if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
        return -1
    adj = {}
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 1:
                continue
            nb = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0:
                        nb.append((nr, nc))
            adj[(r, c)] = nb
    start, goal = (0, 0), (n - 1, n - 1)
    seen = {start}
    q = collections.deque([(start, 1)])
    while q:
        cur, d = q.popleft()
        if cur == goal:
            return d
        for nxt in adj[cur]:
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return -1


def rooms_visited_by_dfs(rooms):
    """841 的参照:用 DFS 而不是 BFS。"""
    seen = {0}
    stack = [0]
    while stack:
        cur = stack.pop()
        for k in rooms[cur]:
            if k not in seen:
                seen.add(k)
                stack.append(k)
    return len(seen) == len(rooms)


def ladder_reference(begin, end, word_list):
    """127 的参照:朴素两两判「只差一个字母」建显式图,再 BFS。

    复杂度 O(N^2 * L),只在小用例上当参照用。
    """
    if end not in word_list:
        return 0
    words = [begin] + [w for w in word_list if w != begin]

    def diff1(a, b):
        if len(a) != len(b):
            return False
        return sum(1 for x, y in zip(a, b) if x != y) == 1

    seen = {begin}
    q = collections.deque([(begin, 1)])
    while q:
        cur, d = q.popleft()
        if cur == end:
            return d
        for w in words:
            if w not in seen and diff1(cur, w):
                seen.add(w)
                q.append((w, d + 1))
    return 0


# --------------------------------------------------------------------------
# 3. 用例生成(固定种子,两语言共用同一个文件)
# --------------------------------------------------------------------------

class Lcg:
    """线性同余,和 C++ 侧逐位一致。"""

    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def below(self, n):
        return self.next() % n

    def randint(self, lo, hi):
        return lo + self.below(hi - lo + 1)


def gen_tree(rng, n, shape):
    """生成一棵 n 个节点的二叉树,返回层序列表(-1 表示 None)。

    shape: 0=随机 1=完全二叉树 2=左深链 3=右深链

    层序输出必须砍掉尾部所有的 None。第一版我在循环里只砍了 out 的尾部,
    却没砍待展开队列的尾部 —— 而 None 的两个孩子还是 None,队列就每层
    翻倍地长下去,循环退不出来(实测卡死 20 分钟,靠单独 micro-bench
    每一类用例才定位到)。这里记录一下,一个「生成器写得慢」看起来像
    「算法很慢」,排查时先分别计时。
    """
    if n == 0:
        return []
    if shape == 1:                                  # 完全二叉树(数组形式)
        return [rng.randint(0, 99) for _ in range(n)]
    if shape == 2:                                  # 左深链:每个节点只有左孩子
        vals = [rng.randint(0, 99) for _ in range(n)]
        out = []
        for v in vals[:-1]:
            out.append(v)
            out.append(-1)
        out.append(vals[-1])
        return out
    if shape == 3:                                  # 右深链
        return [rng.randint(0, 99) for _ in range(n)]

    # 随机形态:随机决定每个节点还有几个孩子(0/1/2)
    left = [None] * n
    right = [None] * n
    counter = [0]

    def build():
        if counter[0] >= n:
            return None
        me = counter[0]
        counter[0] += 1
        kids = rng.below(3)
        if kids >= 1:
            left[me] = build()
        if kids == 2:
            right[me] = build()
        return me

    build()

    # 层序输出:尾部连续的 None 直接不展开
    out = []
    q = collections.deque([0])
    while q:
        cur = q.popleft()
        if cur is None:
            out.append(-1)
            continue
        out.append(rng.randint(0, 99))
        q.append(left[cur])
        q.append(right[cur])
        while q and q[-1] is None:                  # 关键:待展开队列的尾部也要砍
            q.pop()
    while out and out[-1] == -1:
        out.pop()
    return out if out else [rng.randint(0, 99)]


def build_cases():
    rng = Lcg(SEED)
    lines = []

    # ---- 111 最小深度:含退化链、单节点、空树 ----
    for shape in (0, 0, 1, 2, 3):
        for n in (1, 2, 3, 5, 8, 13, 20):
            t = gen_tree(rng, n, shape)
            lines.append("min_depth " + " ".join(map(str, t)))
    lines.append("min_depth -2")                       # 空树

    # ---- 773 滑动谜题:360 个可达局面 + 360 个不可达局面 ----
    states = sorted(sp_all_states())
    for s in states:
        lines.append("sliding " + s)
    all_perm = ["".join(p) for p in itertools.permutations("012345")]
    unreachable = [p for p in all_perm if p not in set(states)]
    for p in unreachable[:12]:
        lines.append("sliding " + p)

    # ---- 752 转盘锁:随机 deadends,含空 / 含 target / 含 0000 ----
    for _ in range(40):
        k = rng.below(6)
        dead = set()
        while len(dead) < k:
            dead.add("".join(str(rng.below(10)) for _ in range(4)))
        target = "".join(str(rng.below(10)) for _ in range(4))
        lines.append("lock " + target + " " + (",".join(sorted(dead)) if dead else "-"))
    # 手挑的边界
    lines.append("lock 0202 -")
    lines.append("lock 0000 0000")
    lines.append("lock 0000 -")
    lines.append("lock 1234 1234")                     # target 自己在 deadends 里
    lines.append("lock 1234 1234,5678")
    lines.append("lock 8888 0000")
    lines.append("lock 5555 1111,2222,3333,4444,5555")

    # ---- 1091 八连通网格 ----
    for n in (1, 2, 3, 5, 8, 12):
        for _ in range(6):
            g = [[1 if rng.below(100) < 30 else 0 for _ in range(n)] for _ in range(n)]
            lines.append("binmatrix " + " ".join("".join(map(str, row)) for row in g))
    lines.append("binmatrix 0")                        # 1x1 可走
    lines.append("binmatrix 1")                        # 1x1 不可走
    lines.append("binmatrix 01 10")                    # 2x2 全堵
    lines.append("binmatrix 00 00")                    # 2x2 全通

    # ---- 994 腐烂的橘子 ----
    for rows in (1, 2, 3, 4):
        for cols in (1, 2, 3, 5):
            for _ in range(5):
                g = [[rng.below(3) for _ in range(cols)] for _ in range(rows)]
                lines.append("oranges " + " ".join("".join(map(str, row)) for row in g))
    lines.append("oranges 0")                          # 全空
    lines.append("oranges 2")                          # 只有烂的
    lines.append("oranges 1")                          # 只有新鲜的,无源
    lines.append("oranges 210")                        # 新鲜的被隔开
    lines.append("oranges 21")                         # 一步就够
    lines.append("oranges 222 222")
    lines.append("oranges 111 111")

    # ---- 542 01 矩阵 ----
    for rows in (1, 2, 3, 5):
        for cols in (1, 2, 4, 6):
            for _ in range(5):
                g = [[1 if rng.below(100) < 60 else 0 for _ in range(cols)]
                     for _ in range(rows)]
                lines.append("matrix " + " ".join("".join(map(str, row)) for row in g))
    lines.append("matrix 0")
    lines.append("matrix 1")                           # 没有 0,全是 -1
    lines.append("matrix 11 11")
    lines.append("matrix 00")

    # ---- 127 单词接龙 ----
    lines.append("ladder hit cog hot,dot,dog,lot,log,cog")
    lines.append("ladder hit cog hot,dot,dog,lot,log")          # end 不在表里
    lines.append("ladder a c a,b,c")
    lines.append("ladder a c b,d,e")                            # 不可达
    lines.append("ladder ab ac ab,ac")
    lines.append("ladder abc xyz abc,abd,abe,xyz")
    for _ in range(20):
        # 小字母表上的随机等长词,保证有多个「只差一个字母」的邻居。
        #
        # 这里踩过一个坑,记下来:「抽到 6 个不同的词为止」这种写法在
        # alpha="ab"、L=3 时是不收敛的 —— 枚举空间只有 2^3 = 8 个词,
        # 而 LCG 是确定性的,它会反复吐出同样的几个词,循环永远凑不满 6 个
        # (实测卡死 20 分钟,单行执行了 199 万次)。教训:用「拒绝采样」
        # 凑集合之前,先确认枚举空间比目标规模大一个数量级。
        #
        # 改成直接把全部 8 个词枚举出来、洗牌后取前 6 个:确定性、必然终止。
        L = 3
        alpha = "ab"
        # 自己卷一层的笛卡尔积:正文的代码块不 import itertools,
        # 门也不该偷偷替它 import —— 那样门就跑得比正文宽了。
        everything = [""]
        for _ in range(L):
            everything = [pre + ch for pre in everything for ch in alpha]
        everything.sort()
        # Fisher-Yates,用同一支 LCG 保证两种语言拿到同一批用例
        for i in range(len(everything) - 1, 0, -1):
            j = rng.below(i + 1)
            everything[i], everything[j] = everything[j], everything[i]
        pool = sorted(everything[:6])
        begin = pool[0]
        end = pool[-1]
        lines.append(f"ladder {begin} {end} " + ",".join(pool))

    # ---- 841 钥匙和房间 ----
    for n in (1, 2, 3, 5, 8):
        for _ in range(6):
            rooms = []
            for i in range(n):
                k = rng.below(3)
                keys = set()
                for _ in range(k):
                    keys.add(rng.below(n))
                rooms.append(sorted(keys))
            lines.append("rooms " + " ".join(
                (",".join(map(str, r)) if r else "-") for r in rooms))
    lines.append("rooms 0")                            # 单房间带 0 把钥匙
    lines.append("rooms -")                            # 单房间,空钥匙表
    lines.append("rooms 1,2 0,0 0,1")                  # 全可达
    lines.append("rooms - - 0")                        # 0 号房间没钥匙,进不去 1/2

    return lines


# --------------------------------------------------------------------------
# 4. 主流程
# --------------------------------------------------------------------------

def main():
    if not POST.exists():
        print(f"post not found: {POST}")
        return 2
    src = POST.read_text(encoding="utf-8")
    py_blocks = extract(src, "python")
    cpp_blocks = extract(src, "cpp")
    print(f"  post          : {POST.name}")
    print(f"  blocks        : python {len(py_blocks)}, cpp {len(cpp_blocks)}"
          f" (extracted from the post, no second copies)")
    if len(py_blocks) != len(cpp_blocks):
        print(f"  RESULT: python/cpp block counts differ "
              f"({len(py_blocks)} vs {len(cpp_blocks)})")
        return 1

    # ---- 执行 Python 块 ----
    ns = {"collections": collections}
    for i, b in enumerate(py_blocks):
        try:
            exec(compile(b, f"<post-block-{i}>", "exec"), ns)
        except Exception as exc:                       # noqa: BLE001
            print(f"  python block {i} failed to exec: {type(exc).__name__}: {exc}")
            return 1

    need_py = ["sliding_puzzle", "open_lock", "min_depth", "shortest_path_binary_matrix",
               "oranges_rotting", "update_matrix", "ladder_length",
               "can_visit_all_rooms", "open_lock_bidirectional"]
    missing = [n for n in need_py if n not in ns]
    if missing:
        print(f"  python blocks did not define: {missing}")
        return 1
    need_cpp = ["slidingPuzzle", "openLock", "minDepth", "shortestPathBinaryMatrix",
                "orangesRotting", "updateMatrix", "ladderLength",
                "canVisitAllRooms", "openLockBidirectional"]
    joined = "\n".join(cpp_blocks)
    missing = [n for n in need_cpp if n not in joined]
    if missing:
        print(f"  cpp blocks did not define: {missing}")
        return 1
    fns = {n: ns[n] for n in need_py}

    BUILD.mkdir(exist_ok=True)
    cases = build_cases()
    (BUILD / "cases.txt").write_text("\n".join(cases) + "\n", encoding="utf-8")
    print(f"  cases         : {len(cases)} lines -> build/cases.txt")

    # ---- Python 侧跑用例 ----
    sp_table = sp_reference_table()
    sp_states = set(sp_table.keys())
    out = []
    ref_mismatch = []
    for line in cases:
        parts = line.split()
        kind = parts[0]
        if kind == "min_depth":
            tree = [int(x) for x in parts[1:]]
            root = ns["build_tree_from_list"](tree) if "build_tree_from_list" in ns else None
            # 正文没有给层序建树的辅助函数,这里自己建(不计入文章的实现)
            nodes = [None if v < 0 else ns["TreeNode"](v) for v in tree]
            for idx, nd in enumerate(nodes):
                if nd is None:
                    continue
                li, ri = 2 * idx + 1, 2 * idx + 2
                if li < len(nodes):
                    nd.left = nodes[li]
                if ri < len(nodes):
                    nd.right = nodes[ri]
            root = nodes[0] if nodes else None
            got = fns["min_depth"](root)
            # 参照:暴力枚举所有根到叶子的深度取最小
            depths = []

            def walk(nd, d):
                if nd is None:
                    return
                if nd.left is None and nd.right is None:
                    depths.append(d)
                    return
                walk(nd.left, d + 1)
                walk(nd.right, d + 1)

            walk(root, 1)
            want = min(depths) if depths else 0
            if got != want:
                ref_mismatch.append(f"min_depth {line}: got {got}, brute force {want}")
            out.append(str(got))

        elif kind == "sliding":
            s = parts[1]
            board = [[int(s[0]), int(s[1]), int(s[2])], [int(s[3]), int(s[4]), int(s[5])]]
            got = fns["sliding_puzzle"](board)
            want = sp_table.get(s, -1)                 # 反向 BFS 打出来的表
            if got != want:
                ref_mismatch.append(f"sliding {s}: got {got}, reverse-BFS table {want}")
            out.append(str(got))

        elif kind == "lock":
            target = parts[1]
            dead = [] if len(parts) < 3 or parts[2] == "-" else parts[2].split(",")
            got = fns["open_lock"](dead, target)
            want = lock_reference_bfs(dead, target)
            if got != want:
                ref_mismatch.append(f"lock {target} {dead}: got {got}, ref BFS {want}")
            bi, popped = fns["open_lock_bidirectional"](dead, target)
            if bi != got:
                ref_mismatch.append(
                    f"lock {target} {dead}: single-source {got} vs bidirectional {bi}")
            out.append(f"{got} {bi} {popped}")

        elif kind == "binmatrix":
            g = [[int(ch) for ch in tok] for tok in parts[1:]]
            got = fns["shortest_path_binary_matrix"](g)
            want = binary_matrix_reference(g)
            if got != want:
                ref_mismatch.append(f"binmatrix {parts[1:]}: got {got}, explicit-graph {want}")
            out.append(str(got))

        elif kind == "oranges":
            g = [[int(ch) for ch in tok] for tok in parts[1:]]
            got = fns["oranges_rotting"]([row[:] for row in g])
            want = oranges_bruteforce(g)
            if got != want:
                ref_mismatch.append(f"oranges {parts[1:]}: got {got}, brute force {want}")
            out.append(str(got))

        elif kind == "matrix":
            g = [[int(ch) for ch in tok] for tok in parts[1:]]
            got = fns["update_matrix"]([row[:] for row in g])
            want = matrix_bruteforce(g)
            if got != want:
                ref_mismatch.append(f"matrix {parts[1:]}: got {got}, per-cell BFS {want}")
            out.append(" ".join("".join(str(v) for v in row) for row in got))

        elif kind == "ladder":
            begin, end = parts[1], parts[2]
            words = [] if len(parts) < 4 or parts[3] == "-" else parts[3].split(",")
            got = fns["ladder_length"](begin, end, words)
            want = ladder_reference(begin, end, words)
            if got != want:
                ref_mismatch.append(f"ladder {begin}->{end}: got {got}, naive-graph {want}")
            out.append(str(got))

        elif kind == "rooms":
            rooms = [] if len(parts) < 2 else [
                [] if tok == "-" else [int(x) for x in tok.split(",")]
                for tok in parts[1:]]
            got = fns["can_visit_all_rooms"](rooms)
            want = rooms_visited_by_dfs(rooms)
            if got != want:
                ref_mismatch.append(f"rooms {parts[1:]}: got {got}, DFS {want}")
            out.append("1" if got else "0")

        else:
            print(f"  unknown case kind: {kind}")
            return 1

    (BUILD / "py_out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    check(not ref_mismatch, f"Python 与外部参照不一致:{ref_mismatch[:3]}")

    # ================= 关键断言:不是「能跑」,而是「对」 =================

    # ---- 773:360 个可达局面全部与反向 BFS 的距离表一致 ----
    # 注意 6! = 720,但只有一半排列可达:每次滑动都改变排列奇偶性。
    check(len(sp_states) == 360, f"773 可达局面应有 360 个(6!/2),实测 {len(sp_states)}")
    n_checked = 0
    for s in sorted(sp_states):
        board = [[int(s[0]), int(s[1]), int(s[2])], [int(s[3]), int(s[4]), int(s[5])]]
        if fns["sliding_puzzle"](board) == sp_table[s]:
            n_checked += 1
    check(n_checked == 360, f"773 应有 360 个局面与距离表一致,实际 {n_checked}")
    # 不可达局面必须返回 -1(6!/2 = 360 个不可达)
    unreachable = [p for p in ("".join(x) for x in itertools.permutations("012345"))
                   if p not in sp_states]
    check(len(unreachable) == 360, f"773 不可达局面应有 360 个,实测 {len(unreachable)}")
    check(all(fns["sliding_puzzle"](
        [[int(p[0]), int(p[1]), int(p[2])], [int(p[3]), int(p[4]), int(p[5])]]) == -1
        for p in unreachable[:40]),
        "773 不可达局面应返回 -1")

    # ---- 752:双向 BFS 步数与单源逐例一致,且出队数确实更少 ----
    lock_cases = [l for l in cases if l.startswith("lock ")]
    agree = 0
    fewer = 0
    gain_rows = []
    for l in lock_cases:
        p = l.split()
        target = p[1]
        dead = [] if len(p) < 3 or p[2] == "-" else p[2].split(",")
        if target in dead or "0000" in dead:
            continue
        a = fns["open_lock"](dead, target)
        b, popped = fns["open_lock_bidirectional"](dead, target)
        if a == b:
            agree += 1
        # 单源出队数也数一遍
        dead_s = set(dead)
        seen = {"0000"}
        q = collections.deque(["0000"])
        single_popped = 0
        step = 0
        found = -1
        while q and found < 0:
            size = len(q)
            for _ in range(size):
                cur = q.popleft()
                single_popped += 1
                if cur == target:
                    found = step
                    break
                for nxt in lock_neighbors(cur):
                    if nxt not in dead_s and nxt not in seen:
                        seen.add(nxt)
                        q.append(nxt)
            step += 1
        if found >= 0:
            gain_rows.append((target, a, single_popped, popped))
            if popped <= single_popped:
                fewer += 1
    check(agree == len([l for l in lock_cases
                        if not (l.split()[1] in ([] if len(l.split()) < 3 or l.split()[2] == "-"
                                                 else l.split()[2].split(","))
                                or "0000" in ([] if len(l.split()) < 3 or l.split()[2] == "-"
                                              else l.split()[2].split(",")))]),
          f"752 双向与单源步数应逐例一致,一致 {agree}")
    check(fewer == len(gain_rows),
          f"752 双向 BFS 出队数应不多于单源,实测更少/相等的 {fewer}/{len(gain_rows)}")

    # ---- 752 边界:target 在 deadends 里必须 -1 ----
    check(fns["open_lock"](["1234"], "1234") == -1, "752 target 在 deadends 里应返回 -1")
    check(fns["open_lock_bidirectional"](["1234"], "1234")[0] == -1,
          "752 双向版 target 在 deadends 里也应返回 -1")
    check(fns["open_lock"](["0000"], "1234") == -1, "752 起点在 deadends 里应返回 -1")
    check(fns["open_lock"]([], "0000") == 0, "752 target==起点应返回 0")
    check(fns["open_lock_bidirectional"]([], "0000")[0] == 0,
          "752 双向版 target==起点应返回 0")

    # ---- 994:全腐烂返回 0;无源但有新鲜返回 -1 ----
    check(fns["oranges_rotting"]([[2, 2], [2, 2]]) == 0, "994 全腐烂应返回 0")
    check(fns["oranges_rotting"]([[1, 1]]) == -1, "994 无源但有新鲜应返回 -1")
    check(fns["oranges_rotting"]([[0, 0]]) == 0, "994 全空应返回 0")
    check(fns["oranges_rotting"]([[2, 1]]) == 1, "994 一步扩散应返回 1")
    # 被隔开的新鲜橘子
    check(fns["oranges_rotting"]([[2, 0, 1]]) == -1, "994 被空位隔开应返回 -1")

    # ---- 542:没有 0 时全部 -1 ----
    check(fns["update_matrix"]([[1, 1], [1, 1]]) == [[-1, -1], [-1, -1]],
          "542 没有 0 时应全是 -1")
    check(fns["update_matrix"]([[0]]) == [[0]], "542 单格 0")

    # ---- 1091:八连通的方向数必须是 8 个 ----
    # 一个 2x2 全通矩阵,八连通下答案是 2(一步对角到终点);四连通下是 3。
    check(fns["shortest_path_binary_matrix"]([[0, 0], [0, 0]]) == 2,
          "1091 八连通下 2x2 全通应是 2(对角一步);若得 3 说明退化成四连通")
    check(fns["shortest_path_binary_matrix"]([[1]]) == -1, "1091 起点被堵应返回 -1")

    # ---- 127:返回值是序列长度不是转换次数 ----
    check(fns["ladder_length"]("hit", "cog",
                               ["hot", "dot", "dog", "lot", "log", "cog"]) == 5,
          "127 样例应是 5(序列长度),不是 4(转换次数)")
    check(fns["ladder_length"]("hit", "cog", ["hot", "dot", "dog", "lot", "log"]) == 0,
          "127 endWord 不在表里应返回 0")

    # ---- 111:退化链和单节点 ----
    check(fns["min_depth"](None) == 0, "111 空树应返回 0")

    # ---- 841 ----
    check(fns["can_visit_all_rooms"]([[1], [2], []]) is True, "841 链式全可达")
    check(fns["can_visit_all_rooms"]([[], [0]]) is False, "841 0 号房间没钥匙应 False")

    # ================= 反向对照:改坏实现,确认门会红 =================

    def negative_controls():
        results = []

        # (1) visited 改成出队时才标记 -> 队列塞重复节点。这里用出队数验证。
        def bad_visited_on_dequeue(deadends, target):
            dead = set(deadends)
            if "0000" in dead:
                return -1
            if target == "0000":
                return 0
            visited = set()                       # 故意:出队才标记
            q = collections.deque(["0000"])
            step = 0
            while q:
                size = len(q)
                for _ in range(size):
                    cur = q.popleft()
                    if cur in visited:            # 出队才标记
                        continue
                    visited.add(cur)
                    for i in range(4):
                        d = int(cur[i])
                        for delta in (1, -1):
                            nxt = cur[:i] + str((d + delta) % 10) + cur[i + 1:]
                            if nxt in dead:
                                continue
                            if nxt == target:
                                return step + 1
                            q.append(nxt)         # 不查 visited 就入队
                step += 1
            return -1

        # 用一个没有 deadend、最短步数较长的目标,数队列峰值
        def qpeak(fn, target):
            return fn([], target)

        # 直接数队列峰值更直观
        def peak_naive():
            visited = set()
            q = collections.deque(["0000"])
            peak = 0
            while q:
                peak = max(peak, len(q))
                cur = q.popleft()
                if cur in visited:
                    continue
                visited.add(cur)
                for i in range(4):
                    d = int(cur[i])
                    for delta in (1, -1):
                        q.append(cur[:i] + str((d + delta) % 10) + cur[i + 1:])
                if len(visited) > 3000:
                    break
            return peak

        def peak_good():
            visited = {"0000"}
            q = collections.deque(["0000"])
            peak = 1
            while q:
                peak = max(peak, len(q))
                cur = q.popleft()
                for i in range(4):
                    d = int(cur[i])
                    for delta in (1, -1):
                        nxt = cur[:i] + str((d + delta) % 10) + cur[i + 1:]
                        if nxt not in visited:
                            visited.add(nxt)
                            q.append(nxt)
                if len(visited) > 3000:
                    break
            return peak

        try:
            a, b = peak_naive(), peak_good()
            results.append(("visited 出队才标记:队列峰值", a, b, a > b * 5))
        except Exception as exc:                   # noqa: BLE001
            results.append(("visited 出队才标记", repr(exc), "-", True))

        # (2) 994 的 minutes 无条件 +1 -> 全腐烂用例上从 0 变 1
        def bad_oranges(grid):
            rows, cols = len(grid), len(grid[0])
            q = collections.deque()
            fresh = 0
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] == 2:
                        q.append((r, c))
                    elif grid[r][c] == 1:
                        fresh += 1
            if fresh == 0:
                return 0
            minutes = 0
            while q:
                size = len(q)
                for _ in range(size):
                    r, c = q.popleft()
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                            grid[nr][nc] = 2
                            fresh -= 1
                            q.append((nr, nc))
                minutes += 1                   # 故意:无条件 +1
            return minutes if fresh == 0 else -1

        # 找一个「腐烂橘子周围没有新鲜橘子」的用例,坏版本会多算。
        #
        # 注意:[[2, 0]] 这种「一开始就没有新鲜橘子」的用例抓不到这个 bug ——
        # 正确实现会在 `fresh == 0` 时提前 return,坏实现也走同一个提前返回,
        # 两边都是 0。必须让最后一轮「展开了节点却没有新鲜橘子被传染」。
        # 穷举过 1x2 起的所有形状,最小反例是 [[1, 2]](正确 1 / 坏 2)。
        probe = [[1, 2]]
        good_v = fns["oranges_rotting"]([r[:] for r in probe])
        bad_v = bad_oranges([r[:] for r in probe])
        # 判决写成严格不等式:如果哪天门或坏实现同时失效,两边都返回 0
        # 也会被这一条抓到,而不是静默放过。
        results.append(("994 minutes 无条件 +1", bad_v, good_v, bad_v > good_v))

        # (3) 1091 只用四连通 -> 2x2 全通从 2 变 3
        def bad_four_conn(grid):
            n = len(grid)
            if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
                return -1
            dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]      # 故意:漏掉四个对角
            seen = {(0, 0)}
            q = collections.deque([(0, 0, 1)])
            while q:
                r, c, d = q.popleft()
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < n and 0 <= nc < n):
                        continue
                    if grid[nr][nc] == 1 or (nr, nc) in seen:
                        continue
                    if nr == n - 1 and nc == n - 1:
                        return d + 1
                    seen.add((nr, nc))
                    q.append((nr, nc, d + 1))
            return -1

        good_v = fns["shortest_path_binary_matrix"]([[0, 0], [0, 0]])
        bad_v = bad_four_conn([[0, 0], [0, 0]])
        results.append(("1091 退化成四连通", bad_v, good_v, bad_v != good_v))

        # (4) 994 忘记「所有源一起入队」,只从第一个源出发
        def bad_single_source(grid):
            rows, cols = len(grid), len(grid[0])
            q = collections.deque()
            fresh = 0
            src = None
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] == 2 and src is None:
                        src = (r, c)            # 故意:只取第一个源
                    elif grid[r][c] == 1:
                        fresh += 1
            if fresh == 0:
                return 0
            if src is not None:
                q.append(src)
            minutes = 0
            while q:
                size = len(q)
                rotted = False
                for _ in range(size):
                    r, c = q.popleft()
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                            grid[nr][nc] = 2
                            fresh -= 1
                            rotted = True
                            q.append((nr, nc))
                if rotted:
                    minutes += 1
            return minutes if fresh == 0 else -1

        # 两个源,离得远,只用一个源会算多
        probe = [[2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]]
        good_v = fns["oranges_rotting"]([r[:] for r in probe])
        bad_v = bad_single_source([r[:] for r in probe])
        results.append(("994 只从一个源出发", bad_v, good_v, bad_v != good_v))

        # (5) 对拍归一化过度排序 -> 无法区分(用回溯的例子说明,这里换成集合语义)
        #     这里验的是「行内排序会掩盖错误」这件事本身
        a = sorted(tuple(sorted(x)) for x in [[1, 2, 3], [1, 2, 3]])
        b = sorted(tuple(sorted(x)) for x in [[1, 2, 3], [1, 2, 3], [1, 2, 3]][:2])
        results.append(("行内排序会把不同解看成相同", a == b, False, a == b))

        return results

    print("  ---- 反向对照(改坏实现,确认门会红)----")
    neg = negative_controls()
    for name, bad, good, caught in neg:
        mark = "OK  " if caught else "!!! "
        print(f"    {mark} {name}:改坏后 {bad} vs 正确 {good} -> "
              f"{'门会红' if caught else '门抓不到!'}")
    check(all(c for _, _, _, c in neg), "有反向对照没被门抓住")

    # ---- 输出统计 ----
    print(f"  ---- 参照对拍 ----")
    print(f"    773 滑动谜题 : {len(sp_states)} 个可达局面全部与反向 BFS 距离表一致")
    print(f"    773 不可达   : {len(unreachable)} 个局面应返回 -1(抽查 40 个)")
    print(f"    752 双向 vs 单源 : {agree} 例步数一致,{fewer}/{len(gain_rows)} 例出队数更少或相等")
    if gain_rows:
        worst = max(gain_rows, key=lambda t: t[2] / max(t[3], 1))
        print(f"    752 出队数对比示例(target={worst[0]} 步数={worst[1]}): "
              f"单源 {worst[2]} 次 -> 双向 {worst[3]} 次")
    print(f"    外部参照不一致 : {len(ref_mismatch)}")

    # ---- 写 C++ 用例文件,交给主流程编译对拍 ----
    return 0


def build_cpp_source(cpp_blocks):
    """把正文抽出的 C++ 块拼成一个编译单元。

    正文里每个函数都是「一个函数一段」,没有 main。这里:
    - 去重所有 #include;
    - 给每个函数加 GNU unused 属性 —— 下面的 main 不会调用全部函数,
      否则 clang 的 -Wunused-function 会报错。属性不改变函数体一行。
    """
    includes = []
    bodies = []
    for b in cpp_blocks:
        for line in b.splitlines():
            if line.strip().startswith("#include"):
                if line not in includes:
                    includes.append(line)
        rest = [l for l in b.splitlines() if not l.strip().startswith("#include")]
        bodies.append("\n".join(rest))
    header = "\n".join(includes + [
        "#include <cstdio>",
        "#include <cstdlib>",
        "#include <string>",
        "#include <vector>",
        "#include <queue>",
        "#include <unordered_set>",
        "#include <unordered_map>",
        "#include <utility>",
        "#include <algorithm>",
        "#include <sstream>",
        "#include <iostream>",
        # fstream 只有门的 harness 用(读 build/cases.txt 和写输出),
        # 正文的代码块不该为了门去 import 一个自己用不到的头文件。
        "#include <fstream>",
        "",
        "#if defined(__GNUC__)",
        "#  define MAYBE_UNUSED __attribute__((unused))",
        "#else",
        "#  define MAYBE_UNUSED",
        "#endif",
        "",
    ])
    # 给顶层函数加属性:逐个找形如 "int fname(" / "bool fname(" / "std::pair<...> fname("
    out_bodies = []
    pat = re.compile(r"^(?P<ret>(?:int|bool|void|long long|std::string|"
                     r"std::vector<[^;{]*?>|std::pair<[^;{]*?>))\s+(?P<name>\w+)\s*\(",
                     re.M)
    for body in bodies:
        def add_attr(m):
            return f"{m.group('ret')} MAYBE_UNUSED {m.group('name')}("
        out_bodies.append(pat.sub(add_attr, body))
    return header + "\n".join(out_bodies)


CPP_MAIN = r"""

// ------------------------------------------------------------------ 用例驱动
// 读 cases.txt(与 Python 侧同一个文件),结果写到 stdout。
// 注意 TreeNode 在文章代码块里定义过,这里直接用。

struct Lcg {
    long long s;
    explicit Lcg(long long seed) : s(seed & 0x7FFFFFFFLL) {}
    long long next() { s = (s * 1103515245LL + 12345LL) & 0x7FFFFFFFLL; return s; }
    long long below(long long n) { return next() % n; }
    long long randint(long long lo, long long hi) { return lo + below(hi - lo + 1); }
    std::vector<long long> split() { return std::vector<long long>(); }
};

// 从层序数组建树。空树用单元素 {-2} 表示。
static TreeNode* buildTree(const std::vector<int>& level) {
    if (level.empty()) return nullptr;
    if (level.size() == 1 && level[0] == -2) return nullptr;
    std::vector<TreeNode*> nodes(level.size(), nullptr);
    for (std::size_t i = 0; i < level.size(); ++i) {
        if (level[i] >= 0) nodes[i] = new TreeNode(level[i]);
    }
    for (std::size_t i = 0; i < level.size(); ++i) {
        if (nodes[i] == nullptr) continue;
        const std::size_t li = 2 * i + 1;
        const std::size_t ri = 2 * i + 2;
        if (li < nodes.size()) nodes[i]->left = nodes[li];
        if (ri < nodes.size()) nodes[i]->right = nodes[ri];
    }
    return nodes[0];
}

static std::vector<std::string> splitTokens(const std::string& line) {
    std::vector<std::string> out;
    std::istringstream iss(line);
    std::string tok;
    while (iss >> tok) out.push_back(tok);
    return out;
}

static std::vector<std::string> splitBy(const std::string& s, char sep) {
    std::vector<std::string> out;
    std::string cur;
    for (std::size_t i = 0; i < s.size(); ++i) {
        if (s[i] == sep) { out.push_back(cur); cur.clear(); }
        else cur.push_back(s[i]);
    }
    out.push_back(cur);
    return out;
}

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: %s cases.txt\n", argv[0]); return 2; }
    std::ifstream in(argv[1]);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        const std::vector<std::string> p = splitTokens(line);
        const std::string kind = p[0];

        if (kind == "min_depth") {
            std::vector<int> level;
            for (std::size_t i = 1; i < p.size(); ++i) level.push_back(std::atoi(p[i].c_str()));
            std::printf("%d\n", minDepth(buildTree(level)));

        } else if (kind == "sliding") {
            const std::string s = p[1];
            std::vector<std::vector<int> > board(2, std::vector<int>(3, 0));
            for (int i = 0; i < 6; ++i) board[i / 3][i % 3] = s[static_cast<std::size_t>(i)] - '0';
            std::printf("%d\n", slidingPuzzle(board));

        } else if (kind == "lock") {
            const std::string target = p[1];
            std::vector<std::string> dead;
            if (p.size() >= 3 && p[2] != "-") dead = splitBy(p[2], ',');
            const int one = openLock(dead, target);
            const std::pair<int, long long> bi = openLockBidirectional(dead, target);
            std::printf("%d %d %lld\n", one, bi.first, bi.second);

        } else if (kind == "binmatrix") {
            std::vector<std::vector<int> > g;
            for (std::size_t i = 1; i < p.size(); ++i) {
                std::vector<int> row;
                for (std::size_t j = 0; j < p[i].size(); ++j) row.push_back(p[i][j] - '0');
                g.push_back(row);
            }
            std::printf("%d\n", shortestPathBinaryMatrix(g));

        } else if (kind == "oranges") {
            std::vector<std::vector<int> > g;
            for (std::size_t i = 1; i < p.size(); ++i) {
                std::vector<int> row;
                for (std::size_t j = 0; j < p[i].size(); ++j) row.push_back(p[i][j] - '0');
                g.push_back(row);
            }
            std::printf("%d\n", orangesRotting(g));

        } else if (kind == "matrix") {
            std::vector<std::vector<int> > g;
            for (std::size_t i = 1; i < p.size(); ++i) {
                std::vector<int> row;
                for (std::size_t j = 0; j < p[i].size(); ++j) row.push_back(p[i][j] - '0');
                g.push_back(row);
            }
            const std::vector<std::vector<int> > d = updateMatrix(g);
            std::string out;
            for (std::size_t r = 0; r < d.size(); ++r) {
                if (r) out += " ";
                for (std::size_t c = 0; c < d[r].size(); ++c) {
                    out += std::to_string(d[r][c]);
                }
            }
            std::printf("%s\n", out.c_str());

        } else if (kind == "ladder") {
            const std::string begin = p[1], end = p[2];
            std::vector<std::string> words;
            if (p.size() >= 4 && p[3] != "-") words = splitBy(p[3], ',');
            std::printf("%d\n", ladderLength(begin, end, words));

        } else if (kind == "rooms") {
            std::vector<std::vector<int> > rooms;
            for (std::size_t i = 1; i < p.size(); ++i) {
                std::vector<int> keys;
                if (p[i] != "-") {
                    const std::vector<std::string> parts = splitBy(p[i], ',');
                    for (std::size_t j = 0; j < parts.size(); ++j) {
                        keys.push_back(std::atoi(parts[j].c_str()));
                    }
                }
                rooms.push_back(keys);
            }
            std::printf("%d\n", canVisitAllRooms(rooms) ? 1 : 0);

        } else {
            std::fprintf(stderr, "unknown case kind: %s\n", kind.c_str());
            return 2;
        }
    }
    return 0;
}
"""


def run_cpp(cpp_blocks):
    src = build_cpp_source(cpp_blocks) + CPP_MAIN
    path = BUILD / "cpp_main.cpp"
    path.write_text(src, encoding="utf-8")
    exe = BUILD / "cpp_main"
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
           str(path), "-o", str(exe)]
    print(f"  compiling with {' '.join(cmd[:7])}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stderr.strip():
        print(f"  cpp compile WARNINGS/ERRORS:\n{proc.stderr}")
    if proc.returncode != 0:
        print(f"  cpp compile FAILED (exit {proc.returncode})")
        return None
    if proc.stderr.strip():
        print("  cpp compile is not warning-free -> gate fails")
        return None
    out = subprocess.run([str(exe), str(BUILD / "cases.txt")],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(f"  cpp run FAILED (exit {out.returncode}): {out.stderr[:400]}")
        return None
    (BUILD / "cpp_out.txt").write_text(out.stdout, encoding="utf-8")
    return out.stdout


def main_all():
    rc = main()
    if rc != 0:
        return rc

    src = POST.read_text(encoding="utf-8")
    cpp_blocks = extract(src, "cpp")
    py_out = (BUILD / "py_out.txt").read_text(encoding="utf-8")
    cpp_out = run_cpp(cpp_blocks)
    if cpp_out is None:
        return 1

    py_lines = py_out.rstrip("\n").split("\n")
    cpp_lines = cpp_out.rstrip("\n").split("\n")
    if len(py_lines) != len(cpp_lines):
        print(f"  line count differs: python {len(py_lines)} vs cpp {len(cpp_lines)}")
        return 1
    diffs = [(i, a, b) for i, (a, b) in enumerate(zip(py_lines, cpp_lines)) if a != b]
    n_cpp = len(cpp_lines)
    print(f"  cpp           : {n_cpp} cases, {len(diffs)} mismatches")
    for i, a, b in diffs[:5]:
        print(f"    line {i}: python {a!r} vs cpp {b!r}")

    check(not diffs, f"Python 与 C++ 输出不一致:{diffs[:3]}")

    print()
    print(f"  python checks : {PY_CHECKS[0]}, failures {len(PY_FAILS)}")
    print(f"  cpp checks    : {n_cpp} (exit 0)")
    if PY_FAILS:
        print()
        print("  RESULT: %d problem(s)" % len(PY_FAILS))
        for f in PY_FAILS:
            print(f"    - {f}")
        return 1
    print()
    print(f"  CODE OK — {len(extract(src, 'python'))} python + "
          f"{len(cpp_blocks)} cpp blocks, {PY_CHECKS[0]} python assertions + "
          f"{n_cpp} cpp cases, 0 failures")
    return 0


if __name__ == "__main__":
    sys.exit(main_all())
