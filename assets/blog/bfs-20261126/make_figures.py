#!/usr/bin/env python3
"""生成 BFS 这篇的 4 张图。

**图里没有一个手写数字。** 每个数字都由本文件里的模拟算出来，再用 f-string
插进标签里，所以图和模拟不可能各说各话：

  * 图 1 / 图 2 的层数、出队顺序、入队次数、队列峰值 —— `bfs_*` 真跑
  * 图 3 每个格子的「第几分钟腐烂」 —— 多源 / 单源 BFS 真跑同一个网格
  * 图 4 的出队节点数 —— 752 转盘锁的单源与双向 BFS 真跑（b=8、d=6）

生成完必须自己渲染看一眼：`Check` 只查文字/文字、文字/箭头、越界，
查不到「文字压在没登记的线或矩形上」这一类问题。

    python3 assets/blog/bfs-20261126/make_figures.py
    sips -s format png -Z 1200 assets/img/bfs-20261126/0X-*.svg --out /tmp/0X.png
"""
import sys
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "assets/blog/_tools"))

from svgkit import (Svg, Check, INK, MUTED, BLUE, LINE, PAPER, CANVAS,   # noqa: E402
                    FILL_BLUE, FILL_WARM, FILL_TEAL, FILL_GREY,
                    WARM_TXT, TEAL_TXT)

OUT = REPO / "assets/img/bfs-20261126"
OUT.mkdir(parents=True, exist_ok=True)

PROBLEMS = 0

# ---------------------------------------------------------------------------
# 参考模拟：图上的每个数字都从这里来
# ---------------------------------------------------------------------------

# 图 1：4 层小图。S 是起点、T 是终点，b 约为 2，但有汇聚（D 有两个父亲）。
G1 = {"S": ["A", "B"], "A": ["C", "D"], "B": ["D", "E"],
      "C": ["T"], "D": ["T"], "E": ["T"], "T": []}

# 图 2：菱形 + 汇聚。C、D 各有 2 个父亲，E 有 2 个父亲。
G2 = {"S": ["A", "B"], "A": ["C", "D"], "B": ["C", "D"],
      "C": ["E"], "D": ["E"], "E": ["T"], "T": []}


def bfs_layers(adj, start):
    """按层返回节点（每一层内部按字母序），用来在图上标「第几层」。"""
    out, seen, cur = [], {start}, [start]
    while cur:
        out.append(sorted(cur))
        nxt = []
        for u in cur:
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    nxt.append(v)
        cur = nxt
    return out


def bfs_enqueue_mark(adj, start, target):
    """模板二：visited 在入队时标记。返回 (步数, 总入队次数, 队列峰值, 出队序)。"""
    seen, q = {start}, deque([start])
    pushes, peak, step, order = 1, 1, 0, []
    while q:
        size = len(q)
        for _ in range(size):
            cur = q.popleft()
            order.append(cur)
            if cur == target:
                return step, pushes, peak, order
            for v in adj[cur]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
                    pushes += 1
        peak = max(peak, len(q))
        step += 1
    return -1, pushes, peak, order


def bfs_dequeue_mark(adj, start, target):
    """出队时才标记 visited 的那种写法（错的那版）。返回同样的四元组。"""
    seen, q = set(), deque([start])
    pushes, peak, step, order = 1, 1, 0, []
    while q:
        size = len(q)
        for _ in range(size):
            cur = q.popleft()
            order.append(cur)
            if cur == target:
                return step, pushes, peak, order
            seen.add(cur)
            for v in adj[cur]:
                if v not in seen:
                    q.append(v)
                    pushes += 1
        peak = max(peak, len(q))
        step += 1
    return -1, pushes, peak, order


def grid_dist(n, sources):
    """多源 BFS：所有源在第 0 层。返回每个格子的分钟数（-1 表示到不了）。"""
    dist = [[-1] * n for _ in range(n)]
    q = deque()
    for r, c in sources:
        dist[r][c] = 0
        q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and dist[nr][nc] < 0:
                dist[nr][nc] = dist[r][c] + 1
                q.append((nr, nc))
    return dist


def lock_neighbors(cur):
    for i in range(4):
        d = int(cur[i])
        for delta in (1, -1):
            yield cur[:i] + str((d + delta) % 10) + cur[i + 1:]


def lock_single(deadends, target):
    """752 单源 BFS。返回 (最少步数, 出队节点数)。"""
    dead = set(deadends)
    if "0000" in dead or target in dead:
        return -1, 0
    seen, q = {"0000"}, deque(["0000"])
    popped, step = 0, 0
    while q:
        for _ in range(len(q)):
            cur = q.popleft()
            popped += 1
            if cur == target:
                return step, popped
            for nxt in lock_neighbors(cur):
                if nxt not in dead and nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        step += 1
    return -1, popped


def lock_bidirectional(deadends, target, stats=None):
    """752 双向 BFS（每次扩散更小的那一侧）。返回 (最少步数, 出队节点数)。

    `stats` 传一个 dict 进来就能拿到 `swaps`：图里写了「交换过若干次」，
    这个数字必须真的数出来，不能凭印象写。
    """
    dead = set(deadends)
    swaps = 0
    if "0000" in dead or target in dead:
        if stats is not None:
            stats["swaps"] = swaps
        return -1, 0
    if target == "0000":
        if stats is not None:
            stats["swaps"] = swaps
        return 0, 0
    front, back, visited = {"0000"}, {target}, {"0000", target}
    step, popped = 0, 0
    while front and back:
        if len(front) > len(back):
            front, back = back, front
            swaps += 1
        nxt_layer = set()
        # 按字典序迭代:集合本身无序,而 popped 数到「碰头那一刻」为止,
        # 不排序的话同一个用例每次跑出来的数字会差一两个(集合迭代序随哈希种子变)。
        for cur in sorted(front):
            popped += 1
            for nxt in lock_neighbors(cur):
                if nxt in dead:
                    continue
                if nxt in back:
                    if stats is not None:
                        stats["swaps"] = swaps
                    return step + 1, popped
                if nxt not in visited:
                    visited.add(nxt)
                    nxt_layer.add(nxt)
        front = nxt_layer
        step += 1
    if stats is not None:
        stats["swaps"] = swaps
    return -1, popped


def lock_bidirectional_noswap(deadends, target):
    """同一套双向 BFS,但去掉「扩散更小的一侧」那一步:正确答案不变,只是慢。"""
    dead = set(deadends)
    if "0000" in dead or target in dead:
        return -1, 0
    if target == "0000":
        return 0, 0
    front, back, visited = {"0000"}, {target}, {"0000", target}
    step, popped = 0, 0
    while front and back:
        nxt_layer = set()
        for cur in sorted(front):
            popped += 1
            for nxt in lock_neighbors(cur):
                if nxt in dead:
                    continue
                if nxt in back:
                    return step + 1, popped
                if nxt not in visited:
                    visited.add(nxt)
                    nxt_layer.add(nxt)
        front = nxt_layer
        step += 1
    return -1, popped


# ---- 图 1 的数 ----
L1 = bfs_layers(G1, "S")
F1_STEP, F1_PUSH, F1_PEAK, F1_ORDER = bfs_enqueue_mark(G1, "S", "T")

# ---- 图 2 的数：正确版 vs 出队才标记版 ----
L2 = bfs_layers(G2, "S")
OK_STEP, OK_PUSH, OK_PEAK, OK_ORDER = bfs_enqueue_mark(G2, "S", "T")
BAD_STEP, BAD_PUSH, BAD_PEAK, BAD_ORDER = bfs_dequeue_mark(G2, "S", "T")

# ---- 图 3 的数：同一个 5x5 网格，单源 vs 多源 ----
N = 5
SOURCES = [(0, 0), (4, 4)]
D_MULTI = grid_dist(N, SOURCES)
D_SINGLE = grid_dist(N, SOURCES[:1])
MULTI_ANS = max(max(row) for row in D_MULTI)
SINGLE_ANS = max(max(row) for row in D_SINGLE)

# ---- 图 4 的数：752，target=0202，含 5 个 deadends ----
DEADENDS = ["0201", "0101", "0102", "1212", "2002"]
LOCK_TARGET = "0202"
S_STEP, S_POPPED = lock_single(DEADENDS, LOCK_TARGET)
B_STATS = {}
B_STEP, B_POPPED = lock_bidirectional(DEADENDS, LOCK_TARGET, B_STATS)
B_SWAPS = B_STATS["swaps"]
NS_STEP, NS_POPPED = lock_bidirectional_noswap(DEADENDS, LOCK_TARGET)
BRANCH = 8                      # 4 位 x 2 个方向
IDEAL_SINGLE = BRANCH ** 6      # b^d
IDEAL_BIDI = 2 * BRANCH ** 3    # 2 * b^(d/2)

assert S_STEP == B_STEP == 6, "两个版本的步数必须一致"
assert OK_STEP == BAD_STEP == 4 and OK_STEP == len(L2) - 1, "两个变体答案必须一致"
assert B_POPPED < S_POPPED, "双向版出队数必须更少"
assert B_SWAPS > 0, "图里写了「交换过若干次」,那就必须真的交换过"
assert NS_STEP == S_STEP, "不交换那一侧也必须给出同样的步数"
assert NS_POPPED > B_POPPED, "图里说不交换会更慢,那就必须真的更慢"


# ---------------------------------------------------------------------------
# 画图小工具
# ---------------------------------------------------------------------------

def txt(s, c, name, x, y, t, size=13, fill=INK, anchor="middle", weight="400"):
    """Svg.text 和 Check.text 必须传同一个 x，包一层就不会写歪。"""
    s.text(x, y, t, size=size, fill=fill, anchor=anchor, weight=weight)
    c.text(name, x, y, t, size=size, anchor=anchor)
    return t


def head(s, c, name, text, sub=None, w=1240):
    txt(s, c, name + ".title", w // 2, 36, text, size=17, weight="600")
    if sub:
        txt(s, c, name + ".sub", w // 2, 60, sub, size=12, fill=MUTED)


def cellnum(s, c, name, x, y, w, h, t, fill=PAPER, size=14):
    s.cell(x, y, w, h, t, fill=fill, size=size)
    c.text(name, x + w / 2, y + h / 2 + size * 0.36, t, size=size)


def node(s, c, name, x, y, t, r=22, fill=FILL_BLUE):
    s.circle(x, y, r, fill=fill)
    txt(s, c, name, x, y + 5, t, size=14, weight="600")


def edge(s, c, name, p1, p2, r=22, gap=9):
    """两个节点之间画箭头：两端各留 r+gap，避免箭头压到节点里的字。"""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    d = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / d, dy / d
    a = (x1 + ux * (r + gap), y1 + uy * (r + gap))
    b = (x2 - ux * (r + gap), y2 - uy * (r + gap))
    s.arrow(a[0], a[1], b[0], b[1])
    c.arrow(name, a[0], a[1], b[0], b[1])


def save(s, c, name):
    global PROBLEMS
    PROBLEMS += c.run(name)
    s.save(str(OUT / name))


# ---------------------------------------------------------------------------
# 图 1：三种模板，区别只在「什么时候 step++」
# ---------------------------------------------------------------------------
def fig01():
    W, H = 1240, 716
    s, c = Svg(W, H), None
    c = Check(s)
    head(s, c, "f1", "同一张 4 层小图:三种模板的差别只在「什么时候 step++」",
         f"层数、出队顺序、step 的取值都是这张图真跑出来的;从 S 到 T 的最短步数是 {F1_STEP}")

    c.panel("f1.graph", 30, 84, 1180, 300)
    s.panel(30, 84, 1180, 300)
    col = {0: 210, 1: 490, 2: 780, 3: 1050}
    for k, x in col.items():
        txt(s, c, f"f1.layer{k}", x, 120, f"第 {k} 层", size=12, fill=MUTED)
    pos = {"S": (col[0], 220), "A": (col[1], 180), "B": (col[1], 262),
           "C": (col[2], 158), "D": (col[2], 220), "E": (col[2], 282),
           "T": (col[3], 220)}
    for u, vs in G1.items():
        for v in vs:
            edge(s, c, f"f1.e{u}{v}", pos[u], pos[v])
    for name, (x, y) in pos.items():
        node(s, c, f"f1.node{name}", x, y, name,
             fill=FILL_WARM if name in ("S", "T") else FILL_BLUE)
    txt(s, c, "f1.count", W / 2, 352,
        " / ".join(f"第 {i} 层 {len(l)} 个" for i, l in enumerate(L1))
        + f";入队顺序 {' '.join(F1_ORDER)};最短步数 {F1_STEP}",
        size=13)

    rows = [
        (398, "模板一:不分层,visited 在入队时标记 —— 只能判断「能不能到达」",
         f"while q: cur = q.pop();出队顺序 {' '.join(F1_ORDER)},一共出队 {len(F1_ORDER)} 次",
         f"没有「层」的概念:step++ 只能写在出队那一行 → 数出来是 {len(F1_ORDER)}"
         f",而正确答案是 {F1_STEP}"),
        (500, "模板二:size = len(q) 先固化,for 吃掉一整层,while 末尾 step++(本文例题都用它)",
         " → ".join(f"step={i} 处理 {{ {', '.join(l)} }}" for i, l in enumerate(L1))
         + f",处理到 T 时返回 {F1_STEP}",
         f"整个 while 只转 {F1_STEP} 圈,step++ 只发生 {F1_STEP} 次;"
         f"和模板一的 {len(F1_ORDER)} 次出队是两件事"),
        (602, "模板三:把步数存进队列元素里,(节点, 步数)",
         " → ".join(f"{n},{i}" for i, l in enumerate(L1) for n in l)
         + ":出队时就已经知道步数",
         "不需要分层循环,但每个元素多存一个整数;要记录具体路径时也用它"),
    ]
    for y0, t, l1, l2 in rows:
        c.panel(f"f1.row{y0}", 30, y0, 1180, 94)
        s.panel(30, y0, 1180, 94)
        txt(s, c, f"f1.row{y0}.t", 52, y0 + 32, t, size=14, weight="600", anchor="start")
        txt(s, c, f"f1.row{y0}.l1", 52, y0 + 58, l1, size=12.5, anchor="start")
        txt(s, c, f"f1.row{y0}.l2", 52, y0 + 80, l2, size=12.5, anchor="start", fill=MUTED)
    save(s, c, "01-three-templates.svg")


# ---------------------------------------------------------------------------
# 图 2：visited 在入队时标记 vs 在出队时标记
# ---------------------------------------------------------------------------
def fig02():
    W, H = 1240, 750
    s, c = Svg(W, H), None
    c = Check(s)
    head(s, c, "f2", "visited 在入队时标记 vs 在出队时标记:答案一样,队列差一倍",
         "同一张图、同一个起点和终点;两个变体的入队次数与队列峰值都是这段代码真跑出来的")

    c.panel("f2.graph", 30, 84, 1180, 250)
    s.panel(30, 84, 1180, 250)
    pos = {"S": (170, 230), "A": (430, 160), "B": (430, 286),
           "C": (690, 160), "D": (690, 286), "E": (920, 230), "T": (1140, 230)}
    for u, vs in G2.items():
        for v in vs:
            edge(s, c, f"f2.e{u}{v}", pos[u], pos[v])
    for name, (x, y) in pos.items():
        node(s, c, f"f2.node{name}", x, y, name,
             fill=FILL_WARM if name in ("S", "T") else FILL_BLUE)
    txt(s, c, "f2.layers", W / 2, 328,
        f"层:S | {' | '.join(' '.join(l) for l in L2[1:])};"
        f"最短步数 {OK_STEP}(S → A → C → E → T)", size=13)

    left = [
        f"每轮开头的队列快照:{' → '.join('[' + ', '.join(l) + ']' for l in L2[:4])}",
        "C 和 D 各有 2 个父亲,但入队时就已经标记了,第二个父亲看不见它们",
        f"每个节点恰好入队 1 次:总入队 {OK_PUSH} 次(节点共 {len(pos)} 个)",
        f"队列峰值 {OK_PEAK} 个(展开 S 之后,A、B 同时在队列里)",
        f"答案 {OK_STEP} 步 —— 正确",
    ]
    right = [
        f"出队序列:{' '.join(BAD_ORDER)}(一共出队 {len(BAD_ORDER)} 次)",
        "C、D、E 都在出队时才被标记,于是被后来的父亲又入队一次",
        f"总入队 {BAD_PUSH} 次,是正确版的 {BAD_PUSH / OK_PUSH:.2f} 倍",
        f"队列峰值 {BAD_PEAK} 个(C、D 各被塞了两份,同时躺在队列里)",
        f"答案仍是 {BAD_STEP} 步 —— 不崩只错,对答案发现不了",
    ]
    for x0, title, lines, fill in ((30, "入队时标记(正确)", left, FILL_TEAL),
                                   (630, "出队时标记(错)", right, FILL_WARM)):
        c.panel(f"f2.p{x0}", x0, 360, 580, 330)
        s.panel(x0, 360, 580, 330)
        s.rect(x0 + 22, 384, 8, 22, fill=fill, rx=2, sw=0)
        txt(s, c, f"f2.t{x0}", x0 + 42, 402, title, size=15, weight="600", anchor="start")
        for i, line in enumerate(lines):
            txt(s, c, f"f2.l{x0}.{i}", x0 + 42, 442 + i * 34, line,
                size=12.5, anchor="start")

    txt(s, c, "f2.note", W / 2, 726,
        f"两个版本的答案都是 {OK_STEP} 步、访问的节点数也一样;"
        f"但总入队 {OK_PUSH} vs {BAD_PUSH}、队列峰值 {OK_PEAK} vs {BAD_PEAK}",
        size=13)
    save(s, c, "02-visited-timing.svg")


# ---------------------------------------------------------------------------
# 图 3：多源 BFS
# ---------------------------------------------------------------------------
def fig03():
    W, H = 1240, 620
    s, c = Svg(W, H), None
    c = Check(s)
    head(s, c, "f3", "多源 BFS:所有源一起放进第 0 层 —— 半径直接减半",
         "两个 5×5 网格(没有遮挡),格子里的数字是「第几分钟腐烂」,都由这段代码真跑出来")

    side = 62
    for x0, title, dist, srcs, ans, note in (
            (30, "只从第一个源出发(单源)", D_SINGLE, [SOURCES[0]], SINGLE_ANS,
             f"答案 {SINGLE_ANS} 分钟:右下角离唯一的源最远"),
            (630, "两个源同时出发(多源)", D_MULTI, SOURCES, MULTI_ANS,
             f"答案 {MULTI_ANS} 分钟:两个源各自扩散,谁也不等谁")):
        c.panel(f"f3.p{x0}", x0, 84, 580, 460)
        s.panel(x0, 84, 580, 460)
        txt(s, c, f"f3.t{x0}", x0 + 290, 122, title, size=15, weight="600")
        gx = x0 + (580 - N * side) / 2
        gy = 150
        for r in range(N):
            for col in range(N):
                fill = FILL_WARM if (r, col) in srcs else PAPER
                cellnum(s, c, f"f3.{x0}.{r}{col}", gx + col * side, gy + r * side,
                        side, side, str(dist[r][col]), fill=fill)
        txt(s, c, f"f3.n{x0}", x0 + 290, gy + N * side + 34, note, size=13)
        txt(s, c, f"f3.leg{x0}", x0 + 290, gy + N * side + 62,
            "橙色 = 初始就腐烂的橘子(第 0 层)" if len(srcs) > 1 else "橙色 = 唯一的源",
            size=11.5, fill=MUTED)

    txt(s, c, "f3.note", W / 2, 566,
        f"同一张网格、同一批橘子,只把两个源都放进第 0 层:答案从 {SINGLE_ANS} 变成 {MULTI_ANS} 分钟;"
        f"多源 BFS 相对单源只改了「入队」那两行", size=13)
    save(s, c, "03-multi-source.svg")


# ---------------------------------------------------------------------------
# 图 4：双向 BFS 的量级收益
# ---------------------------------------------------------------------------
def fig04():
    W, H = 1240, 620
    s, c = Svg(W, H), None
    c = Check(s)
    head(s, c, "f4", "双向 BFS:从 b^d 降到 2·b^(d/2),代价是要能从终点反向走",
         f"以 752 转盘锁为例(target={LOCK_TARGET},含 {len(DEADENDS)} 个 deadends,"
         f"b={BRANCH}、d={S_STEP});两个出队数都是这段代码真跑出来的"
         f"(集合按字典序迭代,数字每次跑都一样)")

    def staircase(x_start, y0, counts, bw=58, gap=6, direction=1, max_h=150):
        """一层一根柱子,高度按「第几层」线性递增 —— 只为看出指数增长的趋势。"""
        for i, cnt in enumerate(counts):
            h = 24 + (max_h - 24) * i / max(1, len(counts) - 1)
            x = x_start + direction * i * (bw + gap)
            if direction < 0:
                x -= bw
            s.rect(x, y0 - h, bw, h, fill=FILL_BLUE if i % 2 == 0 else FILL_GREY, rx=3)
            txt(s, c, f"f4.cnt{i}", x + bw / 2, y0 - h - 8, str(cnt), size=11)

    # 左:单源,一层比一层大,到第 6 层是 b^6
    c.panel("f4.single", 30, 84, 580, 400)
    s.panel(30, 84, 580, 400)
    txt(s, c, "f4.t1", 320, 122, "单源:一层一层往外扩", size=15, weight="600")
    staircase(74, 330, [BRANCH ** k for k in range(7)])
    s.line(60, 330, 560, 330, stroke=LINE, sw=1.6)
    txt(s, c, "f4.s1", 320, 366, f"第 0 层到第 {S_STEP} 层:总量 ≈ b^d = {IDEAL_SINGLE}",
        size=13)
    txt(s, c, "f4.s2", 320, 396, f"真实用例:单源出队 {S_POPPED} 个节点", size=13)
    txt(s, c, "f4.s3", 320, 424,
        f"(理想模型不封顶;真实状态只有 10^4 个,所以不到 {IDEAL_SINGLE})",
        size=11.5, fill=MUTED)
    txt(s, c, "f4.s4", 320, 456, f"每层约 b^k 个:1 → {BRANCH} → {BRANCH ** 2} → "
        f"{BRANCH ** 3} → … → {BRANCH ** 6}", size=12, fill=MUTED)

    # 右:双向,两边各 d/2 层就碰头
    c.panel("f4.bidi", 630, 84, 580, 400)
    s.panel(630, 84, 580, 400)
    txt(s, c, "f4.t2", 920, 122, "双向:两边各扩到 d/2 = 3 层就碰头", size=15, weight="600")
    staircase(660, 330, [BRANCH ** k for k in range(4)], bw=44, gap=5, direction=1)
    staircase(1180, 330, [BRANCH ** k for k in range(4)], bw=44, gap=5, direction=-1)
    s.line(650, 330, 1190, 330, stroke=LINE, sw=1.6)
    s.line(920, 190, 920, 330, stroke=WARM_TXT, sw=1.6, dash="6 5")
    txt(s, c, "f4.b1", 920, 182, "碰头", size=12, fill=WARM_TXT, weight="600")
    txt(s, c, "f4.b2", 920, 366, f"两边各 ≈ b^(d/2) = {BRANCH ** 3},合起来 ≈ {IDEAL_BIDI}",
        size=13)
    txt(s, c, "f4.b3", 920, 396, f"真实用例:双向出队 {B_POPPED} 个节点", size=13)
    txt(s, c, "f4.b4", 920, 424, "起点一侧 + 终点一侧,两边都不必走完整条路",
        size=11.5, fill=MUTED)
    txt(s, c, "f4.b5", 920, 456,
        f"每次扩散更小的那一侧(这个用例真的交换了 {B_SWAPS} 次)", size=12, fill=MUTED)

    txt(s, c, "f4.note", W / 2, 528,
        f"实测:{S_POPPED} / {B_POPPED} ≈ {S_POPPED / B_POPPED:.1f} 倍(同一步数 {S_STEP});"
        f"理想模型里 b^d 与 2·b^(d/2) 是 {IDEAL_SINGLE} / {IDEAL_BIDI}", size=13)
    txt(s, c, "f4.note2", W / 2, 558,
        f"「每次扩散更小的那一侧」不影响正确性,只影响快慢:不交换也能算出 {NS_STEP} 步,"
        f"但出队 {NS_POPPED} 个节点,比交换版多 {NS_POPPED - B_POPPED} 个", size=12, fill=MUTED)
    save(s, c, "04-bidirectional.svg")


def main():
    print(f"figures -> {OUT}")
    fig01()
    fig02()
    fig03()
    fig04()
    # 把图上的数字再打一遍:这份输出就是「数字是真跑出来的」的证据
    print("\n  [numbers baked into the figures]")
    print(f"  fig01 layers={L1} order={F1_ORDER} step={F1_STEP}")
    print(f"  fig02 enq-mark: step={OK_STEP} pushes={OK_PUSH} peak={OK_PEAK}")
    print(f"  fig02 deq-mark: step={BAD_STEP} pushes={BAD_PUSH} peak={BAD_PEAK} "
          f"order={' '.join(BAD_ORDER)}")
    print(f"  fig03 single={SINGLE_ANS} multi={MULTI_ANS} (grid {N}x{N}, "
          f"sources={SOURCES})")
    print(f"  fig04 lock: single=({S_STEP},{S_POPPED}) bidi=({B_STEP},{B_POPPED}) "
          f"swaps={B_SWAPS} no-swap=({NS_STEP},{NS_POPPED}) "
          f"ideal={IDEAL_SINGLE}/{IDEAL_BIDI}")
    print(f"\n  {PROBLEMS} layout problem(s) across 4 figures")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
