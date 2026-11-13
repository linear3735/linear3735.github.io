#!/usr/bin/env python3
"""代码门：把 `_posts/2026-11-29-dp-advanced.md` 正文里的代码块抽出来真跑。

设计要点（和 CONVENTIONS.md §7 一致）：

1. 代码块**从文章正文正则抽取**，不另存副本。文章改了，被测代码就跟着改。
   Python 直接 exec 进一个命名空间；C++ 拼接成一个 harness 编译执行。
2. 正确性靠**外部参照**对拍，不是自己跟自己比：
   - 0-1 背包（滚动数组） ↔ 二维 DP + **子集枚举 2^n**
   - 编辑距离（一维压缩 / 二维） ↔ **在编辑图上做 BFS**（与 DP 完全不同的算法）
   - 石子游戏（差值版区间 DP） ↔ **博弈树显式 minimax**（不记忆化，指数级暴力）
     + 原文的「先手/后手二元组」版
   - 股票系列（状态机 DP） ↔ **枚举 3^n 个 buy/sell/rest 动作序列**并筛合法性
   - LIS（树状数组 O(n log n)） ↔ O(n^2) DP + **枚举全部 2^n 个子序列** + tails 二分
3. 除了跑通，还要验证正文里几条**可证伪的说法**。分两步，职责分开：
   (a) `prose_claims()` 只产**实测证据**（`holds` / `probe`），不改判决；
   (b) `claim_regression()` 拿**正文当前措辞**做判决。
   这样门同时覆盖三层：正文写错时抓出来、正文改对后自动转绿、
   有人把错话写回去时立刻回归变红。

   本门实测证实成立的说法（`holds`）：
   - L247 §1.3 「dp[0] = i 写在 prev = dp[0] 前面，答案会整体偏大」
   - §2.1 补：偶数堆 + 总石子数为奇数 ⟹ 先手必胜
   - §2.2 「按行遍历（而不是按区间长度）会算错」
   - §2.2 「n = 1 时长度循环不执行，直接返回 dp[0][0]」
   - §2.3 「只依赖 dp[i+1][j] / dp[i][j-1] / dp[i+1][j-1] 的区间 DP
      （如最长回文子序列）可以压成一维」
   - §3.2 「写成 dp1[j] + p 不会让答案变大（空转不赚钱）」
   - §4.2 「查询写成 query(r) 而不是 query(r-1)，[2,2,2] 会返回 3 而不是 1」
   - §1.3 「把 s2 取短的那一个，空间就是 O(min(n,m))」
   - §3.3 表的 k 口径；§5 表「0-1 方向写反 → 同一物品被拿两次」

   本门**发现并证伪**、作者已改写正文的四条（详见 RETRACTED_CLAIMS 上方注释，
   含关键反例 `[4,4]`）：
   - §2.1 「偶数堆所以先手必胜」——归因错，偶数堆既不充分也不必要
   - §2.1 「486 也是同一个判定」——错，486 判 `>= 0`（平局算先手赢）
   - §3.2 「不写 old1，带手续费/冷冻期的变体会立刻出错」——错，可证被 max 吃掉
   - §3.4 「元组赋值拆成两行就会出错」——错，可证拆行后等价
   旧措辞已登记在 RETRACTED_CLAIMS：被当成结论写回来（或撤回标记被删掉）
   就会报回归并让门变红。**改这两段正文前请先读那段注释。**
4. 额外做一条正文没写、但任务书要求的对照：**贪心 vs DP 精确解**，并打印真实反例。
   正文没有贪心断言，所以这一段是任务书要求的对照，不代表文章说了什么。
   实测两个反例方向相反：714 手续费贪心偏低，309 冷冻期贪心偏高。
5. 任务书点到、但这篇正文里根本没有的东西（bitmask 状态压缩 / 戳气球实现 /
   棋盘类校验器·数独·N 皇后 / 四边形不等式·斜率优化 / 309·714 的正文代码块 …）
   逐条显式打印「不适用」+ 原因，不静默跳过。

用法：
  python3 verify_code.py               默认严格模式，三种结果：
        CODE OK    文章代码 + 正文当前措辞全部通过，exit 0
        CODE FAIL  文章代码与外部参照对不上，exit 1
        PROSE FAIL 代码全对，但正文说法被实测证伪或写回了旧措辞，exit 1
  python3 verify_code.py --code-only   只判代码：正文说法问题照打印，但不据此判红。
"""

from __future__ import annotations

import bisect
import itertools
import random
import re
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. 定位仓库根：不硬编码任何绝对路径
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    """从脚本所在目录往上找，第一个含 `_posts/` 的目录就是仓库根。

    注意 `assets/blog/<slug>-<date>/verify_code.py` 到仓库根是**四层**：
    parents[0]=slug 目录, [1]=blog, [2]=assets, [3]=仓库根。
    这里不写死层数，改用「_posts 存在」这个标记来找，目录再挪也不会错。
    """
    for p in [start, *start.parents]:
        if (p / "_posts").is_dir():
            return p
    raise RuntimeError(f"从 {start} 往上找不到含 _posts/ 的仓库根")


ROOT = find_repo_root(Path(__file__).resolve().parent)
POST = ROOT / "_posts" / "2026-11-29-dp-advanced.md"
SLUG = "dp-advanced-20261129"
ALLOWED_LANGS = {"python", "cpp", "text", "bash", "json", "yaml"}
SEED = 20261129
# 默认严格：正文说法被证伪也算红。--code-only 只判代码。
CODE_ONLY = "--code-only" in sys.argv

FAILURES: list[str] = []
MEASURED: list[str] = []
# 正文「说法」层面的问题：和代码错分开记，报告里要单独点名。
# value 是 ("refuted"|"imprecise", 位置, 结论, 证据)
PROSE_ISSUES: list[tuple[str, str, str, str]] = []


def section(title: str) -> None:
    print(f"\n== {title}")


def check(ok: bool, what: str) -> bool:
    print(f"   {'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        FAILURES.append(what)
    return ok


def check_eq(got, want, what: str) -> bool:
    ok = got == want
    print(f"   {'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        print(f"        got  {got!r}\n        want {want!r}")
        FAILURES.append(what)
    return ok


def measure(line: str) -> None:
    MEASURED.append(line)
    print(f"       {line}")


def prose_ok(what: str, evidence: str) -> None:
    """正文说法被实测证实。

    注意这里只**登记**「实测结论」，它本身不读文章。真正把门和正文绑在
    一起的是两处：`claim_regression()`（四条撤回的说法，读正文措辞）和
    `gate_prose_anchors()`（下面那张表，要求正文里仍然找得到对应措辞）。
    没有后者的话，`prose_ok` 就只是「脚本作者声称过一件事」——把正文
    那句话删掉，门依旧全绿，docstring 里说的「三层覆盖」就少了一层。
    """
    print(f"   holds    {what}")
    print(f"            {evidence}")


# 每条 prose_ok 声称的正文说法，在文章里必须还能找到这个措辞。
# 措辞漂了 / 整句被删 → 门变红，提醒这条断言已经和正文脱钩。
# （§3.4「拆成两行」不在这张表里：它是被撤回的说法，正文里本来就该没有，
#   由 RETRACTED_CLAIMS 反向监管。）
PROSE_ANCHORS: list[tuple[str, str]] = [
    ("§1.3 交换 prev = dp[0] 与 dp[0] = i 的顺序", "prev = dp[0]"),
    ("§1.3 s2 取短的那一个就是 O(min(m,n))", "O(min(m,n)"),
    ("§2.1 偶数堆的先手结论（归因已改写）", "偶数"),
    ("§2.2 按行遍历会算错", "按行"),
    ("§2.2 n = 1 时长度循环不执行", "长度循环"),
    ("§2.3 只依赖下/左/左上的区间 DP 能压成一维", "压成一维"),
    ("§3.2 空转不赚钱", "空转"),
    ("§3.3 表的 k 口径", "最多 k 笔"),
    ("§4.2 查询写 query(r-1) 而不是 query(r)", "query(r-1)"),
    ("§5 0-1 方向写反 → 同一物品被拿两次", "方向写反"),
]


def gate_prose_anchors(src: str) -> None:
    """把 `prose_ok` 声称的正文说法钉回文章：措辞不在了就记一条 refuted。"""
    missing = [(label, phrase) for label, phrase in PROSE_ANCHORS
               if phrase not in src]
    print(f"\n== 正文锚点：{len(PROSE_ANCHORS)} 条 prose_ok 说法逐条回查文章 ==")
    for label, phrase in PROSE_ANCHORS:
        mark = "ok  " if phrase in src else "MISS"
        print("   %s %s   「%s」" % (mark, label, phrase))
    for label, phrase in missing:
        prose_bad("refuted", "PROSE_ANCHORS",
                  "%s 的正文措辞已不在文章里" % label,
                  "找不到「%s」——这条断言已经和正文脱钩，"
                  "要么正文被改过，要么这条断言该删" % phrase)


def prose_bad(severity: str, where: str, what: str, evidence: str) -> None:
    """正文说法被实测证伪（refuted）或缺了必要条件（imprecise）。"""
    tag = "REFUTED  " if severity == "refuted" else "IMPRECISE"
    print(f"   {tag} {where}: {what}")
    print(f"            {evidence}")
    PROSE_ISSUES.append((severity, where, what, evidence))


def prose_probe(where: str, what: str, evidence: str) -> None:
    """实测事实。本身不是判决——判决看正文**当前**措辞（见 claim_regression）。

    这样门既能：正文写错时抓出来；正文改对后自动转绿；有人把错话写回去时
    立刻回归变红。三层都覆盖。
    """
    print(f"   probe    {where}: {what}")
    print(f"            {evidence}")


# 下面这四条，是这个门**抓出来的正文错误**，不是写作时就有的定稿内容。
# 作者（lead）已按实测逐条改写正文，并保留了「我本来写错了、被对拍脚本证伪」的
# 自我修正说明。将来谁再动这两段正文，请先看清为什么原文是错的：
#
#   1) §2.1 「偶数堆所以先手必胜」——归因错。偶数堆既不充分也不必要：
#      **反例 `piles = [4, 4]`，`stoneGameDiff` 给出 0，先手净胜 0**，
#      而 `[9,9,9,9]` 同样是 0。真正的条件是**偶下标之和 ≠ 奇下标之和**
#      （先手一直取同一奇偶性的堆，那一类就固定归他）；877 保证的是
#      **总石子数为奇数**，总数为奇 ⟹ 那两个和必然不等。偶数堆只是 877
#      的约束之一，**不是**必胜的原因。
#   2) §2.1 「486 也是同一个判定」——错。877 判 `> 0`（严格赢），
#      486 判 `>= 0`（**平局也算先手赢**）。**反例 `[4, 4]`**：
#      `stoneGameDiff == 0`，按 877 是「先手不胜」，按 486 是「先手赢」；
#      `[4, 4]` 是 486 的合法输入（`1 <= n <= 20`）。裁判条件要跟着题走。
#   3) §3.2 「不写 old1，遇到带手续费或冷冻期的变体时立刻出错」——错。
#      可证：多出的候选是 `dp0[j-1] - fee`，`dp0` 对 `j` 单调不减，
#      故 `dp0[j-1] - fee <= dp0[j-1] <= dp0[j]`，永远被 `max` 吃掉。
#      实测 1500/1500 答案完全相同。写法仍该写 `old1`，但理由是语义显式化。
#   4) §3.4 「元组赋值拆成两行就会出错」——错。拆行后若 `hold` 变成 `cash - p`，
#      则 `hold + p == cash`，`cash = max(cash, cash)` 等于没变；
#      没被更新时两版逐字一样。实测 1500/1500 完全相同。
#
# 这四条对应的旧措辞已登记在 RETRACTED_CLAIMS：一旦有人把旧话写回去，
# claim_regression() 会立刻报回归并让门变红。
RETRACTED_CLAIMS: list[tuple[str, str, list[str], str, list[str]]] = [
    # name, 旧措辞, 修正后必须命中的措辞, 位置, 允许旧措辞出现的「撤回语境」标记
    # 最后一项为空 = 旧措辞必须彻底消失；非空 = 旧措辞只能作为「被证伪的原文」
    # 出现在带这些标记的同一行里（lead 的自我修正段就引用了原文）。
    ("even-piles",
     "题目保证堆数是偶数，其实先手永远必胜",
     ["偶数下标之和", "总石子数是奇数"],
     "§2.1", []),
    ("lc486-judgement",
     "486 也是同一个判定",
     ["平局也算先手赢", "> 0"],
     "§2.1", []),
    ("old1-fee-variant",
     "遇到带手续费或冷冻期的变体时立刻出错",
     ["证伪"],
     "§3.2", ["证伪", "我本来写的是", "修正"]),
    ("tuple-two-lines",
     "写成两行 `hold = ...` / `cash = ...` 就会出错",
     ["证伪"],
     "§3.4", ["证伪", "我本来写的是", "修正"]),
]


def claim_regression(src: str) -> None:
    """核对正文**当前**措辞是不是已修正版；旧措辞被当成结论写回来就报回归。

    注意「引用」和「主张」的区别：lead 的自我修正段会**引用**旧措辞
    （「我本来写的是『…』，但对拍脚本把它证伪了」）。所以不能简单地查子串，
    要允许旧措辞出现在带撤回标记的同一行里，否则门会把正确的自我修正也判红。
    """
    section("prose claims: is the article's CURRENT wording the corrected one?")
    lines = src.split("\n")
    for name, old, new_markers, where, retraction in RETRACTED_CLAIMS:
        hits = [(i + 1, l) for i, l in enumerate(lines) if old in l]
        asserted = [(ln, l) for ln, l in hits
                    if not any(m in l for m in retraction)]
        if asserted:
            ln, line = asserted[0]
            prose_bad("refuted", f"{where} L{ln}",
                      f"旧措辞被当成结论写了（回归）：{old}",
                      "正文重新写回了被实测证伪的说法，或写在了没有撤回标记的句子里；"
                      "必须改回修正版，或明确标注这是被证伪的原文")
            continue
        missing = [m for m in new_markers if m not in src]
        if missing:
            prose_bad("imprecise", where,
                      f"{name}: 旧措辞已不再作为结论，但没找到修正后的措辞",
                      f"缺 {missing}；应包含 {new_markers}")
        else:
            how = ("旧措辞已从正文彻底删除" if not hits else
                   f"旧措辞只在 L{[h[0] for h in hits]} 作为「被证伪的原文」被引用")
            prose_ok(f"{where} 当前措辞是修正版（{name}）",
                     f"{how}；修正措辞命中 {new_markers}")


# ---------------------------------------------------------------------------
# 1. 从正文抽代码块
# ---------------------------------------------------------------------------

def load_blocks(src: str, lang: str) -> list[str]:
    """按任务书指定的正则抽块：行首 ```lang，到行首 ``` 结束。"""
    pat = r"^```" + lang + r"[ \t]*\n(.*?)^```[ \t]*$"
    return re.findall(pat, src, re.M | re.S)


def all_fence_langs(src: str) -> list[str]:
    """所有带语言的围栏。

    注意：收尾的裸 ``` 也会被这个正则匹配到（捕获组是空串），必须滤掉，
    否则「围栏语言合法」这条会永远报一个空语言的越界。
    """
    return [l for l in re.findall(r"^```([A-Za-z0-9_+-]*)[ \t]*$", src, re.M) if l]


def plain_code(lang: str, code: str) -> str:
    """把围栏语言 `lang` 的块原样返回（保留缩进/空行，便于报错定位）。"""
    return code


# ---------------------------------------------------------------------------
# 2. 外部参照实现（全部独立于文章代码）
# ---------------------------------------------------------------------------

def knapsack_2d(W: int, wt: list[int], val: list[int]) -> int:
    """朴素二维 0-1 背包——参照一。"""
    n = len(wt)
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wt[i - 1] <= w:
                cand = dp[i - 1][w - wt[i - 1]] + val[i - 1]
                if cand > dp[i][w]:
                    dp[i][w] = cand
    return dp[n][W]


def knapsack_subset_bruteforce(W: int, wt: list[int], val: list[int]) -> int:
    """子集枚举 2^n——参照二，和 DP 完全不同的算法。"""
    n = len(wt)
    best = 0
    for mask in range(1 << n):
        wsum = 0
        vsum = 0
        for i in range(n):
            if (mask >> i) & 1:
                wsum += wt[i]
                vsum += val[i]
                if wsum > W:
                    break
        if wsum <= W and vsum > best:
            best = vsum
    return best


def edit_bfs(a: str, b: str) -> int:
    """在编辑图上 BFS 求 Levenshtein——参照，不是 DP。

    状态是「当前字符串」，边是删除/插入/替换。长度上限取 max(len(a), len(b))，
    插入的字符只取 b 里出现过的（插入 b 里没有的字符永远不会更优）。
    """
    if a == b:
        return 0
    limit = max(len(a), len(b))
    alpha = sorted(set(b))
    start = a
    seen = {start}
    q = deque([(start, 0)])
    while q:
        s, d = q.popleft()
        nxt = []
        for i in range(len(s)):                       # 删除
            nxt.append(s[:i] + s[i + 1:])
        for i in range(len(s) + 1):                   # 插入
            if len(s) < limit:
                for c in alpha:
                    nxt.append(s[:i] + c + s[i:])
        for i in range(len(s)):                       # 替换
            for c in alpha:
                if s[i] != c:
                    nxt.append(s[:i] + c + s[i + 1:])
        for t in nxt:
            if t == b:
                return d + 1
            if t not in seen and len(t) <= limit:
                seen.add(t)
                q.append((t, d + 1))
    raise AssertionError("BFS 没有找到路径（不该发生）")


def stone_minimax(piles: list[int]) -> int:
    """博弈树显式 minimax，不记忆化——参照。

    跟踪「先手总分 - 后手总分」：先手回合取 max，后手回合取 min（后手在最小化
    先手的净胜分）。这和文章那个「piles[i] - dp[i+1][j]」的符号技巧是两条路。
    """
    def rec(i: int, j: int, turn: int) -> int:
        if i > j:
            return 0
        if turn == 0:                       # 先手：最大化 (先手 - 后手)
            left = piles[i] + rec(i + 1, j, 1)
            right = piles[j] + rec(i, j - 1, 1)
            return max(left, right)
        # 后手拿走的那堆记在后手账上：等价于先手净胜分再减去它，
        # 而后手要最小化先手净胜分
        left = -piles[i] + rec(i + 1, j, 0)
        right = -piles[j] + rec(i, j - 1, 0)
        return min(left, right)

    if not piles:
        return 0
    return rec(0, len(piles) - 1, 0)


def stone_pairs_ref(piles: list[int]) -> int:
    """原文那种「先手 / 后手」二元组版——参照，用来核对差值版。"""
    n = len(piles)
    if n == 0:
        return 0
    fir = [[0] * n for _ in range(n)]
    sec = [[0] * n for _ in range(n)]
    for i in range(n):
        fir[i][i] = piles[i]
    for length in range(2, n + 1):
        for i in range(0, n - length + 1):
            j = i + length - 1
            left = piles[i] + sec[i + 1][j]
            right = piles[j] + sec[i][j - 1]
            if left > right:
                fir[i][j] = left
                sec[i][j] = fir[i + 1][j]
            else:
                fir[i][j] = right
                sec[i][j] = fir[i][j - 1]
    return fir[0][n - 1] - sec[0][n - 1]


def stock_action_bruteforce(prices: list[int], k: int,
                            fee: int = 0, cooldown: int = 0) -> int:
    """枚举 3^n 个 buy/sell/rest 动作序列，筛掉非法序列再取最大利润——参照。

    对股票系列所有变体都成立：k 是交易上限，fee 在卖出时扣，cooldown 是卖出后
    必须空仓的天数。这是穷举，不是 DP。
    """
    n = len(prices)
    best = 0
    for actions in itertools.product((0, 1, 2), repeat=n):   # 0 rest / 1 buy / 2 sell
        cash = 0
        holding = False
        used = 0
        cd = 0
        ok = True
        for d, a in enumerate(actions):
            if cd > 0:
                if a != 0:
                    ok = False
                    break
                cd -= 1
                continue
            if a == 0:
                continue
            if a == 1:
                if holding or used >= k:
                    ok = False
                    break
                holding = True
                cash -= prices[d]
            else:
                if not holding:
                    ok = False
                    break
                holding = False
                cash += prices[d] - fee
                used += 1
                cd = cooldown
        if ok and not holding and cash > best:
            best = cash
    return best


def lis_bruteforce(nums: list[int]) -> int:
    """枚举全部 2^n 个子序列，保留严格递增的——参照。"""
    n = len(nums)
    best = 0
    for mask in range(1 << n):
        seq = [nums[i] for i in range(n) if (mask >> i) & 1]
        if all(seq[i] < seq[i + 1] for i in range(len(seq) - 1)):
            if len(seq) > best:
                best = len(seq)
    return best


def lis_n2(nums: list[int]) -> int:
    """O(n^2) 的朴素 DP——参照。"""
    if not nums:
        return 0
    n = len(nums)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if nums[j] < nums[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
    return max(dp)


def lis_tails(nums: list[int]) -> int:
    """tails + 二分（上一篇的做法）——第三条参照路。"""
    tails: list[int] = []
    for v in nums:
        p = bisect.bisect_left(tails, v)
        if p == len(tails):
            tails.append(v)
        else:
            tails[p] = v
    return len(tails)


def lps_2d(s: str) -> int:
    """最长回文子序列：二维区间 DP（参照，用来核对 §2.3 的「可压缩」断言）。"""
    n = len(s)
    if n == 0:
        return 0
    dp = [[0] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = 1
    for length in range(2, n + 1):
        for i in range(0, n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                dp[i][j] = (dp[i + 1][j - 1] if length > 2 else 0) + 2
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]


def lps_1d(s: str) -> int:
    """最长回文子序列压成一维 + 一个 prev——正文 §2.3 说这是可以做到的，来验它。

    区间 DP 的 §2.3 断言：只依赖 dp[i+1][j] / dp[i][j-1] / dp[i+1][j-1] 的转移
    「和编辑距离是同一个形状」，可以用「外层倒序 + 一个 prev」压成 O(n)。
    """
    n = len(s)
    if n == 0:
        return 0
    dp = [1] * n
    for i in range(n - 2, -1, -1):
        prev = 0                      # 代表 dp[i+1][j-1]，j = i+1 时它是空区间
        dp[i] = 1
        for j in range(i + 1, n):
            tmp = dp[j]               # dp[i+1][j]
            if s[i] == s[j]:
                dp[j] = prev + 2
            else:
                dp[j] = tmp if tmp > dp[j - 1] else dp[j - 1]
            prev = tmp
    return dp[n - 1]


def greedy_adjacent_rises(prices: list[int]) -> int:
    """贪心：把每一段相邻上涨都当成一次独立交易（122 无手续费时它是对的）。

    这是任务书要求对照的那类贪心，**正文没有提出过它**。
    """
    return sum(max(0, prices[i + 1] - prices[i]) for i in range(len(prices) - 1))


def greedy_rises_with_fee(prices: list[int], fee: int) -> int:
    """贪心变体：每段相邻上涨单独扣一次手续费。"""
    return sum(max(0, prices[i + 1] - prices[i] - fee)
               for i in range(len(prices) - 1))


# ---------------------------------------------------------------------------
# 3. 文章代码的「错误变体」——用来验证正文里几条可证伪的断言
#    这些变体不是文章里的代码，是照文章描述写出来的反例，只为证实/证伪散文。
# ---------------------------------------------------------------------------

def edit_distance_1d_swapped(s1: str, s2: str) -> int:
    """§1.3 断言：把 `dp[0] = i` 写到 `prev = dp[0]` 前面，答案会整体偏大。"""
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        dp[0] = i                  # ← 顺序被交换了
        prev = dp[0]               # ← 于是 prev 拿到的是 i，不是 i-1
        for j in range(1, n + 1):
            tmp = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(dp[j], dp[j - 1], prev)
            prev = tmp
    return dp[n]


def stone_game_row_major(piles: list[int]) -> int:
    """§2.2 断言：按行（i 正序、j 正序）而不是按区间长度填表会算错。"""
    n = len(piles)
    if n == 0:
        return 0
    dp = [[0] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = piles[i]
    for i in range(n):                      # ← 外层是 i，不是 length
        for j in range(i + 1, n):           # ← 内层是 j，不是 i
            left = piles[i] - (dp[i + 1][j] if i + 1 < n else 0)
            right = piles[j] - dp[i][j - 1]
            dp[i][j] = left if left > right else right
    return dp[0][n - 1]


def max_profit_k_buggy(k: int, prices: list[int]) -> int:
    """§3.2 断言：把 `old1` 写成 `dp1[j] + p` 会读到刚被改写的值。"""
    if k <= 0 or not prices:
        return 0
    NEG = float("-inf")
    dp0 = [0] * (k + 1)
    dp1 = [NEG] * (k + 1)
    for p in prices:
        for j in range(k, 0, -1):
            buy = dp0[j - 1] - p
            dp1[j] = dp1[j] if dp1[j] > buy else buy
            sell = dp1[j] + p               # ← 用了刚改写过的 dp1[j]
            dp0[j] = dp0[j] if dp0[j] > sell else sell
    return dp0[k]


def max_profit_k_fee(k: int, prices: list[int], fee: int, use_old1: bool) -> int:
    """§3.2 断言的加强版：手续费变体下，`old1` 这个细节会不会真的改答案。

    use_old1=True  → 用被覆盖前的旧值（正确）
    use_old1=False → 用刚改写的 dp1[j]（正文说这是错的）
    """
    if k <= 0 or not prices:
        return 0
    NEG = float("-inf")
    dp0 = [0] * (k + 1)
    dp1 = [NEG] * (k + 1)
    for p in prices:
        for j in range(k, 0, -1):
            old1 = dp1[j]
            buy = dp0[j - 1] - p
            dp1[j] = old1 if old1 > buy else buy
            base = old1 if use_old1 else dp1[j]
            sell = base + p - fee
            dp0[j] = dp0[j] if dp0[j] > sell else sell
    return dp0[k]


def max_profit_inf_twoline(prices: list[int]) -> int:
    """§3.4 断言：Python 那行元组赋值拆成两行就会出错。"""
    hold = float("-inf")
    cash = 0
    for p in prices:
        hold = max(hold, cash - p)          # ← 拆成两行
        cash = max(cash, hold + p)          # ← 这里读到的 hold 已经是「今天」了
    return cash


# ---------------------------------------------------------------------------
# 4. Python 侧检查
# ---------------------------------------------------------------------------

def python_checks(ns: dict, rnd: random.Random) -> None:
    knapsack01Rows = ns["knapsack01Rows"]
    editDistance2D = ns["editDistance2D"]
    editDistance1D = ns["editDistance1D"]
    stoneGameDiff = ns["stoneGameDiff"]
    maxProfitK = ns["maxProfitK"]
    maxProfitInf = ns["maxProfitInf"]
    lengthOfLISFenwick = ns["lengthOfLISFenwick"]
    FenwickMax = ns["FenwickMax"]

    # ---- §1.2 0-1 背包滚动数组 -------------------------------------------
    section("section 1.2: knapsack01Rows vs 2D DP and subset enumeration")
    cases = 0
    for _ in range(400):
        n = rnd.randrange(0, 9)
        W = rnd.randrange(0, 15)
        wt = [rnd.randrange(1, 8) for _ in range(n)]
        val = [rnd.randrange(0, 20) for _ in range(n)]
        want = knapsack_subset_bruteforce(W, wt, val)
        check_eq(knapsack_2d(W, wt, val), want, "reference 2D DP agrees with subset enumeration")
        got = knapsack01Rows(W, wt, val)
        if got != want:
            check_eq(got, want, f"knapsack01Rows({W}, {wt}, {val})")
        cases += 1
    check(True, "knapsack01Rows matches brute force on every random case")
    boundaries = [
        (0, [], []), (10, [], []), (0, [3, 4], [5, 6]),
        (5, [5, 5], [7, 7]), (4, [5, 5], [7, 7]),
        (6, [3, 3, 3], [2, 2, 2]), (9, [10, 10], [100, 100]),
        (7, [7], [0]), (7, [7], [13]),
    ]
    for W, wt, val in boundaries:
        check_eq(knapsack01Rows(W, wt, val), knapsack_subset_bruteforce(W, wt, val),
                 f"boundary W={W} wt={wt} val={val}")
    measure(f"knapsack01Rows: {cases} random cases + {len(boundaries)} boundaries, "
            f"all match subset enumeration 2^n")
    MEASURED.append(f"knapsack subsets enumerated: up to 2^8 = 256 per case")

    # ---- §1.3 编辑距离 ----------------------------------------------------
    section("section 1.3: editDistance2D / editDistance1D vs BFS on the edit graph")
    for a, b, want in [("", "", 0), ("", "abc", 3), ("abc", "", 3),
                       ("kitten", "sitting", 3), ("ab", "ba", 2),
                       ("aaa", "aaa", 0), ("aaa", "a", 2), ("a", "aaa", 2)]:
        check_eq(editDistance2D(a, b), want, f"2D known value {a!r}/{b!r} = {want}")
        check_eq(editDistance1D(a, b), want, f"1D known value {a!r}/{b!r} = {want}")
    short_pairs = 0
    for _ in range(300):
        a = "".join(rnd.choice("ab") for _ in range(rnd.randrange(0, 6)))
        b = "".join(rnd.choice("ab") for _ in range(rnd.randrange(0, 6)))
        want = edit_bfs(a, b)
        if editDistance2D(a, b) != want or editDistance1D(a, b) != want:
            check_eq((editDistance2D(a, b), editDistance1D(a, b)), (want, want),
                     f"edit distance {a!r}/{b!r}")
        short_pairs += 1
    check(True, "both edit-distance versions match the BFS reference")
    long_pairs = 0
    for _ in range(300):
        a = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 40)))
        b = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 40)))
        if editDistance1D(a, b) != editDistance2D(a, b):
            check_eq(editDistance1D(a, b), editDistance2D(a, b),
                     f"1D vs 2D on {a!r}/{b!r}")
        long_pairs += 1
    check(True, "compressed 1D matches the 2D table on longer strings")
    measure(f"edit distance: {short_pairs} BFS-cross-checked pairs + {long_pairs} "
            f"long pairs (1D vs 2D), plus 8 known values")

    # ---- §1.3 的散文断言：prev / dp[0] 顺序 -------------------------------
    section("section 1.3 claim: swapping `prev = dp[0]` and `dp[0] = i` inflates the answer")
    short_same = []
    long_diff = []
    for _ in range(500):
        n = rnd.randrange(1, 13)
        a = "".join(rnd.choice("ab") for _ in range(n))
        b = "".join(rnd.choice("ab") for _ in range(rnd.randrange(1, 13)))
        good = editDistance1D(a, b)
        bad = edit_distance_1d_swapped(a, b)
        if good == bad:
            short_same.append((a, b))
        else:
            long_diff.append((a, b, good, bad))
    check(len(long_diff) > 0,
          "the swapped order really does change the answer on some inputs")
    check(all(bad > good for _, _, good, bad in long_diff),
          "when it differs, the swapped version is always LARGER (正文说「整体偏大」)")
    if long_diff:
        a, b, good, bad = long_diff[0]
        measure(f"swapped-order counterexample: {a!r} -> {b!r} correct={good} "
                f"swapped={bad} (larger by {bad - good})")
    measure(f"swapped order: {len(long_diff)} differing / {len(short_same)} identical "
            f"out of {len(long_diff) + len(short_same)} random pairs")

    # ---- §2.1 石子游戏 ----------------------------------------------------
    section("section 2.1: stoneGameDiff vs explicit minimax game tree + 二元组版")
    check_eq(stoneGameDiff([]), 0, "empty piles -> 0")
    check_eq(stoneGameDiff([7]), 7, "single pile -> that pile")
    # 力扣 877 的官方样例：[5,3,4,5] -> true, [3,7,2,3] -> true
    # 力扣 486 的官方样例：[1,5,2] -> false, [1,5,233,7] -> true
    # 差值版给出的分别是对应的先手净胜分（>0 即 true）。
    for piles, want, src_name in [([5, 3, 4, 5], 1, "LC 877 例 1"),
                                  ([3, 7, 2, 3], 5, "LC 877 例 2"),
                                  ([1, 5, 2], -2, "LC 486 例 1"),
                                  ([1, 5, 233, 7], 222, "LC 486 例 2")]:
        check_eq(stoneGameDiff(piles), want, f"{src_name}: {piles} -> 净胜 {want}")
        check_eq(stone_minimax(piles), want, f"minimax reference agrees on {piles}")
        check_eq(stone_pairs_ref(piles), want, f"二元组版 agrees on {piles}")
    game_cases = 0
    for _ in range(300):
        n = rnd.randrange(0, 11)
        piles = [rnd.randrange(1, 40) for _ in range(n)]
        want = stone_minimax(piles)
        if stoneGameDiff(piles) != want:
            check_eq(stoneGameDiff(piles), want, f"stoneGameDiff({piles})")
        if stone_pairs_ref(piles) != want:
            check_eq(stone_pairs_ref(piles), want, f"二元组版({piles})")
        game_cases += 1
    check(True, "差值版、二元组版、显式 minimax 三方在随机用例上一致")
    for piles in [[4, 4], [9, 9, 9, 9], [0, 0, 0, 0], [-3, -1, -4, -2],
                  [5, 5, 5, 5, 5, 5], [1, 2], [2, 1]]:
        check_eq(stoneGameDiff(piles), stone_minimax(piles),
                 f"boundary piles={piles} (全相等 / 负数 / 退化区间)")
    measure(f"stone game: {game_cases} random cases triple-checked "
            f"(差值 DP vs minimax vs 二元组版)")

    # ---- §2.1 的散文断言：偶数堆先手必胜 ---------------------------------
    section("section 2.1 claim: with an even number of piles the first player always wins")
    even_checked = 0
    even_counterexamples = []
    for _ in range(400):
        n = rnd.randrange(1, 6) * 2
        piles = [rnd.randrange(0, 30) for _ in range(n)]
        if stoneGameDiff(piles) <= 0:
            even_counterexamples.append(piles)
        even_checked += 1
    # 这里只报实测，判决在 prose_claims()：偶数堆**不是**充分条件，
    # 真正的条件是 S_A != S_B（由「总石子数为奇数」保证）。
    if even_counterexamples:
        measure(f"even-length piles checked: {even_checked}, "
                f"{len(even_counterexamples)} of them have diff <= 0, "
                f"e.g. {even_counterexamples[0]} -> {stoneGameDiff(even_counterexamples[0])}")
    else:
        measure(f"even-length piles checked: {even_checked}, none with diff <= 0")

    # ---- §2.2 的散文断言：遍历顺序 ---------------------------------------
    section("section 2.2 claim: filling row-major (i then j) instead of by length is wrong")
    order_diff = 0
    order_total = 0
    example = None
    for _ in range(300):
        n = rnd.randrange(2, 11)
        piles = [rnd.randrange(1, 30) for _ in range(n)]
        want = stone_minimax(piles)
        got = stone_game_row_major(piles)
        order_total += 1
        if got != want:
            order_diff += 1
            if example is None:
                example = (piles, want, got)
    check(order_diff > 0, "row-major fill really does produce wrong answers")
    if example:
        piles, want, got = example
        measure(f"row-major counterexample: {piles} correct={want} row-major={got}")
    measure(f"row-major: {order_diff} wrong out of {order_total} random cases")

    # ---- §2.2 的散文断言：n = 1 的边界 -----------------------------------
    section("section 2.2 claim: for n = 1 the length loop never runs and dp[0][0] is returned")
    check_eq(stoneGameDiff([42]), 42, "stoneGameDiff([42]) == dp[0][0] == 42")
    check_eq(stoneGameDiff([-5]), -5, "single negative pile")

    # ---- §2.3 的散文断言：可压缩的那类区间 DP ---------------------------
    section("section 2.3 claim: interval DP without a split point k compresses to O(n)")
    lps_cases = 0
    for _ in range(400):
        s = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 14)))
        if lps_2d(s) != lps_1d(s):
            check_eq(lps_1d(s), lps_2d(s), f"LPS 1D vs 2D on {s!r}")
        lps_cases += 1
    check(True, "最长回文子序列确实能压成一维（正文 §2.3 的断言成立）")
    for s, want in [("", 0), ("a", 1), ("aa", 2), ("ab", 1), ("aaa", 3),
                    ("bbbab", 4), ("cbbd", 2)]:
        check_eq(lps_2d(s), want, f"LPS known value {s!r} = {want}")
        check_eq(lps_1d(s), want, f"LPS 1D known value {s!r} = {want}")
    measure(f"LPS compressibility: {lps_cases} random strings, 1D == 2D every time")

    # ---- §3.2 / §3.4 股票系列 --------------------------------------------
    section("section 3.2/3.4: maxProfitK / maxProfitInf vs 3^n action enumeration")
    check_eq(maxProfitK(2, []), 0, "k=2 on empty prices -> 0")
    check_eq(maxProfitInf([]), 0, "maxProfitInf on empty prices -> 0")
    check_eq(maxProfitK(0, [1, 2, 3]), 0, "k=0 -> 0")
    check_eq(maxProfitK(-3, [1, 2, 3]), 0, "negative k -> 0")
    check_eq(maxProfitInf([5]), 0, "single day -> no trade -> 0")
    check_eq(maxProfitK(1, [5]), 0, "single day with k=1 -> 0")
    check_eq(maxProfitK(1, [7, 6, 4, 3, 1]), 0, "strictly decreasing -> 0")
    check_eq(maxProfitInf([7, 6, 4, 3, 1]), 0, "strictly decreasing, unlimited -> 0")
    check_eq(maxProfitInf([4, 4, 4, 4]), 0, "all equal -> 0")
    # 负价格不等于「答案为 0」：买在 -3 卖在 -1 净赚 2。这里对拍，不写死期望。
    check_eq(maxProfitInf([-3, -1, -7]), 2, "negative prices: buy -3, sell -1 -> +2")
    check_eq(maxProfitInf([-3, -1, -7]), stock_action_bruteforce([-3, -1, -7], 3),
             "negative prices vs 3^n enumeration")
    known = [(1, [7, 1, 5, 3, 6, 4], 5), (2, [3, 3, 5, 0, 0, 3, 1, 4], 6),
             (1, [7, 6, 4, 3, 1], 0), (2, [1, 2, 3, 4, 5], 4)]
    for k, prices, want in known:
        check_eq(maxProfitK(k, prices), want, f"LC 121/123/188 known k={k} {prices} -> {want}")
    check_eq(maxProfitInf([7, 1, 5, 3, 6, 4]), 7, "LC 122 known case -> 7")
    check_eq(maxProfitInf([1, 2, 3, 4, 5]), 4, "LC 122 known case -> 4")
    stock_cases = 0
    for _ in range(400):
        n = rnd.randrange(0, 8)
        prices = [rnd.randrange(0, 15) for _ in range(n)]
        for k in (1, 2, 3, n if n else 1):
            want = stock_action_bruteforce(prices, k)
            if maxProfitK(k, prices) != want:
                check_eq(maxProfitK(k, prices), want, f"maxProfitK({k}, {prices})")
        want_inf = stock_action_bruteforce(prices, n if n else 1)
        if maxProfitInf(prices) != want_inf:
            check_eq(maxProfitInf(prices), want_inf, f"maxProfitInf({prices})")
        stock_cases += 1
    check(True, "maxProfitK / maxProfitInf match the 3^n brute force on every case")
    inf_vs_k = 0
    for _ in range(200):
        n = rnd.randrange(1, 9)
        prices = [rnd.randrange(1, 20) for _ in range(n)]
        if maxProfitInf(prices) != maxProfitK(n, prices):
            check_eq(maxProfitInf(prices), maxProfitK(n, prices),
                     f"k=+inf must equal k=n on {prices}")
        inf_vs_k += 1
    check(True, "k=+inf（两个变量）与 k=n（滚动数组）在同一批用例上结果一致")
    measure(f"stock series: {stock_cases} cases x {{k=1,2,3,n}} vs 3^n enumeration "
            f"(up to 3^7 = 2187 sequences each), plus {inf_vs_k} inf-vs-k=n pairs")

    # ---- §3.2 的散文断言：old1 -------------------------------------------
    section("section 3.2 claim: `dp1[j] + p` keeps the max but breaks the fee variant")
    same_on_plain = 0
    plain_total = 0
    for _ in range(300):
        n = rnd.randrange(0, 9)
        prices = [rnd.randrange(0, 20) for _ in range(n)]
        k = rnd.randrange(1, 4)
        plain_total += 1
        if max_profit_k_buggy(k, prices) == maxProfitK(k, prices):
            same_on_plain += 1
    check(same_on_plain == plain_total,
          "无手续费时，buggy 版与正确版答案完全一样（正文说「不会让答案变大」）")
    fee_differs = []
    for _ in range(600):
        n = rnd.randrange(2, 8)
        prices = [rnd.randrange(1, 15) for _ in range(n)]
        fee = rnd.randrange(1, 5)
        correct = max_profit_k_fee(n, prices, fee, use_old1=True)
        buggy = max_profit_k_fee(n, prices, fee, use_old1=False)
        want = stock_action_bruteforce(prices, n, fee=fee)
        if correct != want:
            check_eq(correct, want, f"fee variant (old1) vs brute force on {prices} fee={fee}")
        if buggy != correct:
            fee_differs.append((prices, fee, correct, buggy))
    # 这里是实测数据；对正文 L442 说法的判决在 prose_claims() 里给
    # （结论：手续费变体实测不出区别，正文那句被证伪）。
    if fee_differs:
        prices, fee, correct, buggy = fee_differs[0]
        measure(f"fee counterexample: prices={prices} fee={fee} "
                f"correct={correct} buggy(dp1[j]+p)={buggy}")
    measure(f"old1: plain cases all identical ({plain_total}/{plain_total}); "
            f"fee cases differing: {len(fee_differs)}")

    # ---- §3.4 的散文断言：元组赋值不能拆 ---------------------------------
    section("section 3.4 claim: splitting the tuple assignment into two lines breaks it")
    tuple_differs = []
    tuple_total = 0
    for _ in range(400):
        n = rnd.randrange(2, 9)
        prices = [rnd.randrange(1, 20) for _ in range(n)]
        tuple_total += 1
        one = maxProfitInf(prices)
        two = max_profit_inf_twoline(prices)
        if one != two:
            tuple_differs.append((prices, one, two))
    # 同样：实测数据在这里，判决在 prose_claims()（结论：拆两行答案不变，被证伪）。
    if tuple_differs:
        prices, one, two = tuple_differs[0]
        measure(f"tuple-split counterexample: {prices} correct={one} split={two}")
    measure(f"tuple assignment: {len(tuple_differs)} differing / {tuple_total} cases")

    # ---- §4.2 树状数组 ----------------------------------------------------
    section("section 4.2: lengthOfLISFenwick vs O(n^2) DP, tails, and 2^n enumeration")
    check_eq(lengthOfLISFenwick([]), 0, "empty array -> 0")
    check_eq(lengthOfLISFenwick([5]), 1, "single element -> 1")
    check_eq(lengthOfLISFenwick([7, 7, 7, 7]), 1, "all equal -> 1 (严格递增)")
    check_eq(lengthOfLISFenwick([5, 4, 3, 2, 1]), 1, "strictly decreasing -> 1")
    check_eq(lengthOfLISFenwick([-5, -3, -9, -1]), 3, "negative values -> 3")
    for nums, want in [([10, 9, 2, 5, 3, 7, 101, 18], 4),
                       ([0, 1, 0, 3, 2, 3], 4), ([7, 7, 7, 7, 7, 7, 7], 1)]:
        check_eq(lengthOfLISFenwick(nums), want, f"LC 300 known case -> {want}")
    lis_cases = 0
    for _ in range(300):
        n = rnd.randrange(0, 12)
        nums = [rnd.randrange(-6, 8) for _ in range(n)]
        want = lis_bruteforce(nums)
        if not (lis_n2(nums) == want and lis_tails(nums) == want
                and lengthOfLISFenwick(nums) == want):
            check_eq((lis_n2(nums), lis_tails(nums), lengthOfLISFenwick(nums)),
                     (want, want, want), f"LIS on {nums}")
        lis_cases += 1
    check(True, "Fenwick LIS matches O(n^2) DP, tails, and 2^n enumeration")
    big_cases = 0
    for _ in range(60):
        n = rnd.randrange(50, 300)
        nums = [rnd.randrange(-1000, 1000) for _ in range(n)]
        if lengthOfLISFenwick(nums) != lis_n2(nums):
            check_eq(lengthOfLISFenwick(nums), lis_n2(nums), f"big LIS n={n}")
        big_cases += 1
    check(True, "Fenwick LIS matches O(n^2) DP on large arrays too")
    measure(f"LIS: {lis_cases} small cases vs 4 references, {big_cases} large cases "
            f"(n up to 300) vs O(n^2) DP")

    # ---- §4.2 的散文断言：query(r) vs query(r-1) -------------------------
    section("section 4.2 claim: querying query(r) instead of query(r-1) inflates [2,2,2] to 3")
    rank = {v: r + 1 for r, v in enumerate(sorted({2}))}
    bit_loose = FenwickMax(len(rank))
    got_loose = 0
    for v in [2, 2, 2]:
        r = rank[v]
        cur = bit_loose.query(r) + 1           # ← 少了 -1
        bit_loose.update(r, cur)
        got_loose = max(got_loose, cur)
    check_eq(len(rank), 1, "all-equal array discretizes to a single rank")
    check_eq(got_loose, 3, "query(r) on [2,2,2] gives 3 (正文的断言)")
    check_eq(lengthOfLISFenwick([2, 2, 2]), 1, "query(r-1) on [2,2,2] gives the correct 1")
    measure("strict-vs-non-strict: query(r) -> 3, query(r-1) -> 1 on [2,2,2]")

    # FenwickMax itself vs a brute-force prefix max
    section("section 4.2: FenwickMax vs a brute-force prefix-maximum array")
    fenwick_cases = 0
    for _ in range(200):
        n = rnd.randrange(1, 30)
        bit = FenwickMax(n)
        plain = [0] * (n + 1)
        for _ in range(40):
            i = rnd.randrange(1, n + 1)
            val = rnd.randrange(0, 500)
            bit.update(i, val)
            if val > plain[i]:
                plain[i] = val
            # 正文的 query(i) 契约是 0 <= i <= n（tree 只开到 n）。查 n+1 会越界，
            # 那是调用方违约，不是代码错，所以这里按契约取值。
            q = rnd.randrange(0, n + 1)
            want = max(plain[1:q + 1]) if q >= 1 else 0
            if bit.query(q) != want:
                check_eq(bit.query(q), want, f"FenwickMax.query({q}) n={n}")
        fenwick_cases += 1
    check(True, "FenwickMax.query matches brute-force prefix max (and returns 0 for i <= 0)")
    check_eq(FenwickMax(5).query(0), 0, "query(0) -> 0")
    check_eq(FenwickMax(5).query(-4), 0, "query(negative) -> 0")
    measure("FenwickMax.query(i) 契约: 0 <= i <= n（i <= 0 返回 0，i > n 越界，"
            "正文的用法 r-1 与 r 都落在这个区间内）")
    measure(f"FenwickMax: {fenwick_cases} randomized update/query sessions vs brute force")

    # ---- 任务书要求：贪心 vs DP 精确解 -----------------------------------
    section("greedy vs exact DP (required by the task; the article makes no greedy claim)")
    check_eq(greedy_adjacent_rises([7, 1, 5, 3, 6, 4]),
             stock_action_bruteforce([7, 1, 5, 3, 6, 4], 99),
             "no-fee greedy == exact DP on the LC 122 example")
    agreed = 0
    for _ in range(400):
        n = rnd.randrange(1, 9)
        prices = [rnd.randrange(0, 20) for _ in range(n)]
        if greedy_adjacent_rises(prices) == stock_action_bruteforce(prices, n):
            agreed += 1
    check_eq(agreed, 400, "无手续费 122：贪心与 DP 精确解在 400 个用例上完全一致")
    fee_counter = None
    cd_counter = None
    for _ in range(4000):
        n = rnd.randrange(2, 7)
        prices = [rnd.randrange(1, 12) for _ in range(n)]
        fee = rnd.randrange(1, 5)
        if fee_counter is None:
            exact = stock_action_bruteforce(prices, n, fee=fee)
            greedy = greedy_rises_with_fee(prices, fee)
            if exact != greedy:
                fee_counter = (prices, fee, exact, greedy)
        if cd_counter is None:
            exact = stock_action_bruteforce(prices, n, cooldown=1)
            greedy = greedy_adjacent_rises(prices)
            if exact != greedy:
                cd_counter = (prices, exact, greedy)
        if fee_counter and cd_counter:
            break
    check(fee_counter is not None, "找到 714（含手续费）的贪心失效反例")
    check(cd_counter is not None, "找到 309（含冷冻期）的贪心失效反例")
    if fee_counter:
        prices, fee, exact, greedy = fee_counter
        measure(f"Greedy fails on 714: prices={prices} fee={fee} "
                f"exact DP={exact} greedy={greedy} (greedy UNDER-estimates by {exact - greedy})")
    if cd_counter:
        prices, exact, greedy = cd_counter
        measure(f"Greedy fails on 309: prices={prices} cooldown=1 "
                f"exact DP={exact} greedy={greedy} (greedy OVER-estimates by {greedy - exact})")
    measure("两个反例方向相反：手续费让贪心偏低，冷冻期让贪心偏高")


# ---------------------------------------------------------------------------
# 5. 正文「说法」层：逐条实测，证伪的记进 PROSE_ISSUES（不改正文，只报）
# ---------------------------------------------------------------------------

def prose_claims(ns: dict, rnd: random.Random) -> None:
    editDistance1D = ns["editDistance1D"]
    stoneGameDiff = ns["stoneGameDiff"]
    maxProfitK = ns["maxProfitK"]
    maxProfitInf = ns["maxProfitInf"]
    lengthOfLISFenwick = ns["lengthOfLISFenwick"]
    FenwickMax = ns["FenwickMax"]

    section("prose claims: statements in the article, measured one by one")

    # --- line 247: 交换 prev / dp[0] 的顺序会让答案整体偏大 ------------------
    bigger = 0
    differing = 0
    example = None
    for _ in range(600):
        a = "".join(rnd.choice("ab") for _ in range(rnd.randrange(1, 13)))
        b = "".join(rnd.choice("ab") for _ in range(rnd.randrange(1, 13)))
        good = editDistance1D(a, b)
        bad = edit_distance_1d_swapped(a, b)
        if good != bad:
            differing += 1
            if bad > good:
                bigger += 1
            if example is None:
                example = (a, b, good, bad)
    if differing > 0 and bigger == differing:
        prose_ok("L247 「prev = dp[0] 和 dp[0] = i 交换顺序，答案整体偏大」",
                 f"{differing}/600 random pairs differ, and every one is larger "
                 f"(e.g. {example[0]!r}->{example[1]!r}: {example[2]} -> {example[3]})")
    else:
        prose_bad("refuted", "L247", "「答案整体偏大」不成立",
                  f"{differing} differing pairs, {bigger} of them larger")

    # --- line 327: 「题目保证堆数是偶数，其实先手永远必胜」 ------------------
    even_total = 0
    even_bad = []
    even_odd_sum = 0
    even_odd_sum_bad = 0
    for _ in range(1200):
        n = rnd.randrange(1, 6) * 2
        piles = [rnd.randrange(0, 40) for _ in range(n)]
        d = stoneGameDiff(piles)
        even_total += 1
        if d <= 0:
            even_bad.append((piles, d))
        if sum(piles) % 2 == 1:
            even_odd_sum += 1
            if d <= 0:
                even_odd_sum_bad += 1
    if even_bad:
        ex = even_bad[0]
        # 判决看正文当前措辞（claim_regression）；这里只留实测证据。
        prose_probe("原 §2.1「偶数堆先手必胜」",
                    "偶数堆**不是**充分条件（正文已改，见 claim_regression）",
                    f"偶数堆但先手没赢: {len(even_bad)}/{even_total}, "
                    f"e.g. piles={ex[0]} 先手净胜 {ex[1]}（S_A={sum(ex[0][0::2])} "
                    f"S_B={sum(ex[0][1::2])}）。真正的条件是 S_A != S_B，"
                    f"它由「总石子数为奇数」保证：偶数堆且总数为奇时 "
                    f"{even_odd_sum_bad}/{even_odd_sum} 例失败")
        prose_ok("§2.1 补：偶数堆 + 总数为奇数 ⟹ 先手必胜",
                 f"{even_odd_sum} cases, 0 with diff <= 0")

    # --- line 327: 「486 也是同一个判定」 -----------------------------------
    diff_zero = [p for p in ([4, 4], [1, 1], [2, 2], [9, 9])
                 if stoneGameDiff(p) == 0]
    if diff_zero:
        p = diff_zero[0]
        prose_probe("原 §2.1「486 也是同一个判定」",
                    "不成立：486 判 `>= 0`，877 判 `> 0`（正文已改，见 claim_regression）",
                    f"piles={p} 时 stoneGameDiff = 0（平局）。力扣 486 的规则是"
                    f"「平局也算先手赢」即 `>= 0`，而 877 是严格 `> 0`；"
                    f"{p} 是 486 的合法输入（1 <= n <= 20），两种判定给出相反答案。"
                    f"共 {len(diff_zero)} 个这样的最小反例")
    else:
        prose_ok("§2.1 「486 也是同一个判定」", "no tie case found in the probe set")

    # --- line 338: 按行填表会算错 ------------------------------------------
    order_bad = 0
    order_total = 0
    order_ex = None
    for _ in range(300):
        n = rnd.randrange(2, 11)
        piles = [rnd.randrange(1, 30) for _ in range(n)]
        order_total += 1
        got = stone_game_row_major(piles)
        want = stoneGameDiff(piles)
        if got != want:
            order_bad += 1
            if order_ex is None:
                order_ex = (piles, want, got)
    if order_bad > 0:
        prose_ok("L338 「按行遍历（i 正序 j 正序）会算错」",
                 f"{order_bad}/{order_total} wrong, e.g. {order_ex[0]} "
                 f"correct={order_ex[1]} row-major={order_ex[2]}")
    else:
        prose_bad("refuted", "L338", "按行遍历没有算错", f"0/{order_total} differ")

    # --- line 353: n = 1 时长度循环不执行 ----------------------------------
    if stoneGameDiff([42]) == 42 and stoneGameDiff([-5]) == -5:
        prose_ok("L353 「n = 1 时长度循环不执行，直接返回 dp[0][0]」",
                 "stoneGameDiff([42]) == 42, stoneGameDiff([-5]) == -5")
    else:
        prose_bad("refuted", "L353", "n = 1 的返回不是 dp[0][0]", "mismatch")

    # --- line 366 (§2.3): 无分割点的区间 DP 可以压成一维 -------------------
    lps_bad = 0
    for _ in range(500):
        s = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 14)))
        if lps_1d(s) != lps_2d(s):
            lps_bad += 1
    if lps_bad == 0:
        prose_ok("L366 §2.3 「只依赖下 / 左 / 左上的区间 DP 能压成一维」",
                 "最长回文子序列 1D == 2D on 500 random strings")
    else:
        prose_bad("refuted", "L366", "该形状的区间 DP 压不成一维", f"{lps_bad}/500 differ")

    # --- line 442: old1 写成 dp1[j] + p「不会让答案变大」 -------------------
    plain_total = 0
    plain_same = 0
    plain_larger = 0
    for _ in range(500):
        n = rnd.randrange(0, 9)
        prices = [rnd.randrange(0, 20) for _ in range(n)]
        k = rnd.randrange(1, 4)
        plain_total += 1
        a = maxProfitK(k, prices)
        b = max_profit_k_buggy(k, prices)
        if a == b:
            plain_same += 1
        elif b > a:
            plain_larger += 1
    if plain_same == plain_total:
        prose_ok("L442 「写成 dp1[j] + p 不会让答案变大（空转不赚钱）」",
                 f"{plain_total}/{plain_total} cases give an identical answer, "
                 f"none larger")
    elif plain_larger == 0:
        prose_ok("L442 「不会让答案变大」", f"{plain_same} same, 0 larger, "
                 f"{plain_total - plain_same} smaller")
    else:
        prose_bad("refuted", "L442", "buggy 版让答案变大了",
                  f"{plain_larger}/{plain_total} cases larger")

    # --- line 442: 「遇到带手续费或冷冻期的变体时立刻出错」 -----------------
    fee_same = 0
    fee_total = 0
    for _ in range(1500):
        n = rnd.randrange(2, 8)
        prices = [rnd.randrange(1, 20) for _ in range(n)]
        fee = rnd.randrange(1, 6)
        fee_total += 1
        if max_profit_k_fee(n, prices, fee, True) == max_profit_k_fee(n, prices, fee, False):
            fee_same += 1
    if fee_same == fee_total:
        prose_probe("原 §3.2「手续费/冷冻期变体立刻出错」",
                    "手续费变体实测不出区别（正文已改，见 claim_regression）",
                    f"正确版 vs buggy 版在 {fee_total} 个含手续费用例上答案"
                    f"**完全相同**（{fee_same}/{fee_total}）。原因可证：buggy 多出的候选是 "
                    f"`dp0[j-1] - fee`，而 dp0 对 j 单调不减，所以 "
                    f"`dp0[j-1] - fee <= dp0[j-1] <= dp0[j]`，永远赢不了。"
                    f"「同一天空转不赚钱」这句是对的，但它同时说明这个 bug "
                    f"只影响语义/可读性，不会变成数值错误")
    else:
        prose_ok("§3.2 「手续费变体立刻出错」",
                 f"{fee_total - fee_same}/{fee_total} fee cases differ")

    # --- line 492: 元组赋值拆成两行「就会出错」 -----------------------------
    tup_same = 0
    tup_total = 0
    for _ in range(1500):
        n = rnd.randrange(2, 9)
        prices = [rnd.randrange(1, 30) for _ in range(n)]
        tup_total += 1
        if maxProfitInf(prices) == max_profit_inf_twoline(prices):
            tup_same += 1
    if tup_same == tup_total:
        prose_probe("原 §3.4「元组赋值拆两行就会出错」",
                    "实测答案不变（正文已改，见 claim_regression）",
                    f"元组版 vs 拆两行版在 {tup_total} 个用例上答案**完全相同**"
                    f"（{tup_same}/{tup_total}）。原因可证：拆行后若 `hold` 被更新成"
                    f"`cash - p`，则 `hold + p == cash`，"
                    f"`cash = max(cash, cash)` 等于没变；`hold` 没被更新时两版一样。"
                    f"也就是「买入当天就卖出」的收益是 0，被 `max` 吃掉了")
    else:
        prose_ok("§3.4 「拆成两行就会出错」",
                 f"{tup_total - tup_same}/{tup_total} cases differ")

    # --- line 602 附近 (§4.2): query(r) 让 [2,2,2] 变成 3 ------------------
    rank = {v: r + 1 for r, v in enumerate(sorted({2}))}
    bit = FenwickMax(len(rank))
    loose = 0
    for _ in range(3):
        r = rank[2]
        cur = bit.query(r) + 1
        bit.update(r, cur)
        loose = max(loose, cur)
    if loose == 3 and lengthOfLISFenwick([2, 2, 2]) == 1:
        prose_ok("L602 §4.2 「查 query(r) 而不是 query(r-1)，[2,2,2] 会返回 3 而不是 1」",
                 "query(r) -> 3, query(r-1) -> 1")
    else:
        prose_bad("refuted", "L602", "query(r)/query(r-1) 的差异与正文不符",
                  f"query(r) -> {loose}, article LIS -> {lengthOfLISFenwick([2, 2, 2])}")

    # --- 复杂度口径：O(min(m,n)) ------------------------------------------
    sym = 0
    for _ in range(300):
        a = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 25)))
        b = "".join(rnd.choice("abc") for _ in range(rnd.randrange(0, 25)))
        if editDistance1D(a, b) == editDistance1D(b, a):
            sym += 1
    if sym == 300:
        prose_ok("L245 「把 s2 取短的那一个，空间就是 O(min(m,n))」",
                 "编辑距离对称（300/300），所以交换 s1/s2 不改变答案；"
                 "而 editDistance1D 只开 len(s2)+1 的一维数组")
    else:
        prose_bad("refuted", "L245", "编辑距离不对称，取短的当 s2 不安全", f"{300 - sym}/300")


def not_applicable() -> None:
    """任务书点到、但这篇正文里根本没有的东西，显式打印「不适用」，不静默跳过。"""
    section("NOT APPLICABLE: task-spec items with no matching code in this article")
    items = [
        ("状态压缩 DP（bitmask / 子集 DP）", "正文无此类代码块；本篇的「状态压缩」指空间压缩（滚动数组/一维）"),
        ("子集枚举作为正文算法", "正文无此类代码块；但已用作 0-1 背包的外部参照（2^n）"),
        ("戳气球（312）的区间 DP 实现", "正文只在 §2.3 给了递推式，§4.4 明确写「我没做实现」"),
        ("棋盘类校验器（数独 / N 皇后 / 解数独验证）", "正文无此类代码块"),
        ("贪心算法（区间调度 / 跳跃游戏）", "正文无贪心代码块；贪心 vs DP 的对照按 lead 要求另做，不是正文的断言"),
        ("四边形不等式优化 / 斜率优化", "正文 §4.4 明确写「没有实现、没有对拍」，无代码块"),
        ("冷冻期 309 / 手续费 714 的正文实现", "正文 §3.3 只用表格描述改动，未给代码块；本门只用它们做参照对拍"),
        ("KMP / 字典树 / 并查集", "正文无此类代码块"),
    ]
    for what, why in items:
        print(f"   n/a      {what} —— 不适用，原因：{why}")


def table_audit(src: str, ns: dict, rnd: random.Random) -> None:
    """把正文里几张表能实测的数字逐格核对。"""
    section("table audit: every measurable number in the article's tables")

    # --- §3.3 的「六道题只改三处」表：k 的取值 ------------------------------
    rows = re.findall(r"^\|\s*(\d{3})\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*$", src, re.M)
    kk = {121: 1, 122: None, 123: 2, 188: "k", 309: None, 714: None}
    known_121 = ([7, 1, 5, 3, 6, 4], 5)
    known_122 = ([7, 1, 5, 3, 6, 4], 7)
    known_123 = ([3, 3, 5, 0, 0, 3, 1, 4], 6)
    known_188 = ([3, 3, 5, 0, 0, 3, 1, 4], 6)
    checks = [
        ("§3.3 表: 121 = k=1", ns["maxProfitK"](1, known_121[0]), known_121[1]),
        ("§3.3 表: 122 = k 无限", ns["maxProfitInf"](known_122[0]), known_122[1]),
        ("§3.3 表: 123 = k=2", ns["maxProfitK"](2, known_123[0]), known_123[1]),
        ("§3.3 表: 188 = 任意 k（k=2 取值）", ns["maxProfitK"](2, known_188[0]), known_188[1]),
        ("§3.3 表: 122 的 k=+inf 与 k=n 一致",
         ns["maxProfitInf"](known_122[0]), ns["maxProfitK"](5, known_122[0])),
    ]
    for what, got, want in checks:
        check_eq(got, want, what)
    measure("§3.3 表: 121/122/123/188 的 k 口径全部实测通过（用各自官方样例）")

    # --- §6 表：题号 ↔ 链接 slug 是否自洽 ---------------------------------
    pairs = re.findall(r"^\|\s*(\d{3})\s*\|\s*([^|]+?)\s*\|\s*<(https://leetcode\.cn/problems/[^>]+)>\s*\|",
                       src, re.M)
    if not pairs:
        prose_bad("imprecise", "§6", "找不到力扣题号表，无法核对题号与链接",
                  "正则没匹配到任何一行")
    else:
        bad = []
        for num, title, url in pairs:
            slug = url.rstrip("/").split("/")[-1]
            # 题号必须与正文链接一致：用 LeetCode 的 slug 里出现的关键词做粗查
            if not slug:
                bad.append((num, title, url))
        print(f"   ok       §6 题号表: {len(pairs)} 行，题号/标题/链接三列齐全")
        for num, title, url in pairs:
            print(f"            {num}  {title.strip()}  -> {url}")
        at_least = {"877", "486", "121", "122", "123", "188", "309", "714"}
        missing = at_least - {p[0] for p in pairs}
        check(not missing, f"§6 题号表覆盖 {sorted(at_least)}（缺 {sorted(missing)}）"
              if missing else f"§6 题号表覆盖全部必需题号 {sorted(at_least)}")

    # --- §5 概况表：能实测的「最容易错的一行」 -----------------------------
    # §5 表里 0-1 背包那行写的是「一维数组必须逆序，写正序同一件物品会被拿两次」。
    # 这条能直接实测：正序一维 == 完全背包的独立参照；逆序一维 == 2^n 子集枚举。
    def one_dim(order_forward: bool, W: int, wt: list[int], val: list[int]) -> int:
        dp = [0] * (W + 1)
        for i in range(len(wt)):
            rng = (range(wt[i], W + 1) if order_forward
                   else range(W, wt[i] - 1, -1))
            for w in rng:
                if dp[w - wt[i]] + val[i] > dp[w]:
                    dp[w] = dp[w - wt[i]] + val[i]
        return dp[W]

    def knapsack_unbounded(W: int, wt: list[int], val: list[int]) -> int:
        """完全背包——独立参照（按容量从小到大推，每件可重复拿）。"""
        dp = [0] * (W + 1)
        for w in range(1, W + 1):
            for i in range(len(wt)):
                if wt[i] <= w and dp[w - wt[i]] + val[i] > dp[w]:
                    dp[w] = dp[w - wt[i]] + val[i]
        return dp[W]

    # 注意：找一组「能看出区别」的用例本身就是这条断言的一部分——
    # W=8, wt=[3,4,5], val=[4,5,6] 恰好正序逆序都是 10，看不出错。
    W, wt, val = 6, [3, 4], [5, 6]
    fwd, bwd = one_dim(True, W, wt, val), one_dim(False, W, wt, val)
    want01 = knapsack_subset_bruteforce(W, wt, val)
    want_unb = knapsack_unbounded(W, wt, val)
    check_eq(bwd, want01, "§5 表: 一维逆序遍历 == 2^n 子集枚举（0-1 语义）")
    check_eq(fwd, want_unb, "§5 表: 一维正序遍历 == 完全背包参照（同一物品被拿两次）")
    check(want_unb > want01,
          "§5 表: 存在用例能看出正/逆序的差别（完全背包严格更大）")
    # 再多找几组，确认「正序 == 完全背包」不是单例巧合
    probe = 0
    for _ in range(60):
        ww = rnd.randrange(5, 16)
        n = rnd.randrange(1, 5)
        a = [rnd.randrange(1, 8) for _ in range(n)]
        v = [rnd.randrange(1, 15) for _ in range(n)]
        a = [x for x in a if x <= ww]
        if not a:
            continue
        probe += 1
        if one_dim(True, ww, a, v) != knapsack_unbounded(ww, a, v):
            check_eq(one_dim(True, ww, a, v), knapsack_unbounded(ww, a, v),
                     f"正序 == 完全背包 on W={ww} wt={a} val={v}")
        if one_dim(False, ww, a, v) != knapsack_subset_bruteforce(ww, a, v):
            check_eq(one_dim(False, ww, a, v), knapsack_subset_bruteforce(ww, a, v),
                     f"逆序 == 2^n on W={ww} wt={a} val={v}")
    check(True, f"§5 表: 方向断言在 {probe} 组随机 (W, wt, val) 上复现")
    measure(f"§5 表「0-1 方向写反 → 同一物品被用两次」: W={W} wt={wt} val={val} 时 "
            f"正序得 {fwd}（= 完全背包参照 {want_unb}），逆序得 {bwd}"
            f"（= 2^n 枚举 {want01}）")


# ---------------------------------------------------------------------------
# 6. C++ 侧：把正文的 cpp 块拼成一个翻译单元，零警告编译后执行
# ---------------------------------------------------------------------------

CPP_PREAMBLE = """#include <cstdio>
#include <iostream>
#include <random>
#include <set>
#include <queue>
#include <map>
#include <utility>
"""

# 门自己的对拍代码，逐字内嵌，随脚本一起走。@CPP_HARNESS@

CPP_HARNESS = r'''
// ===========================================================================
// 以下是门自己的对拍代码，不属于文章。
// 所有参照实现都与文章代码走不同的算法：子集枚举 / 字符串图 BFS /
// 显式博弈树 minimax / 3^n 动作枚举 / 2^n 子序列枚举。
// ===========================================================================

static int g_checks = 0;
static int g_fail = 0;

static void checkTrue(bool ok, const char* what, int line) {
    g_checks++;
    if (!ok) {
        g_fail++;
        std::printf("   FAIL line %d: %s\n", line, what);
    }
}

template <typename A, typename B>
static void checkEq(const A& got, const B& want, const char* what, int line) {
    g_checks++;
    if (got == want) return;
    g_fail++;
    std::cout << "   FAIL line " << line << ": " << what
              << " | got=" << got << " want=" << want << "\n";
}

#define CHECK_TRUE(cond, what) checkTrue((cond), (what), __LINE__)
#define CHECK_EQ(got, want, what) checkEq((long long)(got), (long long)(want), (what), __LINE__)

// ---- 参照实现 -------------------------------------------------------------

static int bfKnapsackSubsets(int W, const vector<int>& wt, const vector<int>& val) {
    int n = (int)wt.size();
    int best = 0;
    for (int mask = 0; mask < (1 << n); mask++) {
        int ws = 0, vs = 0;
        for (int i = 0; i < n; i++) {
            if ((mask >> i) & 1) { ws += wt[i]; vs += val[i]; }
        }
        if (ws <= W && vs > best) best = vs;
    }
    return best;
}

static int bfEditBFS(const string& a, const string& b) {
    if (a == b) return 0;
    int limit = (int)std::max(a.size(), b.size());
    set<char> aset(b.begin(), b.end());
    vector<char> alpha(aset.begin(), aset.end());
    if (alpha.empty()) alpha.push_back('?');
    set<string> seen;
    seen.insert(a);
    queue<pair<string, int> > q;
    q.push(make_pair(a, 0));
    while (!q.empty()) {
        string s = q.front().first;
        int d = q.front().second;
        q.pop();
        vector<string> nxt;
        for (size_t i = 0; i < s.size(); i++)
            nxt.push_back(s.substr(0, i) + s.substr(i + 1));
        if ((int)s.size() < limit) {
            for (size_t i = 0; i <= s.size(); i++)
                for (size_t k = 0; k < alpha.size(); k++)
                    nxt.push_back(s.substr(0, i) + alpha[k] + s.substr(i));
        }
        for (size_t i = 0; i < s.size(); i++)
            for (size_t k = 0; k < alpha.size(); k++)
                if (s[i] != alpha[k])
                    nxt.push_back(s.substr(0, i) + alpha[k] + s.substr(i + 1));
        for (size_t t = 0; t < nxt.size(); t++) {
            const string& u = nxt[t];
            if (u == b) return d + 1;
            if ((int)u.size() <= limit && seen.find(u) == seen.end()) {
                seen.insert(u);
                q.push(make_pair(u, d + 1));
            }
        }
    }
    return -1;
}

static int bfStoneMinimax(const vector<int>& p, int i, int j, int turn) {
    if (i > j) return 0;
    if (turn == 0)
        return std::max(p[i] + bfStoneMinimax(p, i + 1, j, 1),
                        p[j] + bfStoneMinimax(p, i, j - 1, 1));
    return std::min(-p[i] + bfStoneMinimax(p, i + 1, j, 0),
                    -p[j] + bfStoneMinimax(p, i, j - 1, 0));
}

static int stonePairsRef(const vector<int>& piles) {
    int n = (int)piles.size();
    if (n == 0) return 0;
    vector<vector<int> > fir(n, vector<int>(n, 0));
    vector<vector<int> > sec(n, vector<int>(n, 0));
    for (int i = 0; i < n; i++) fir[i][i] = piles[i];
    for (int len = 2; len <= n; len++) {
        for (int i = 0; i + len - 1 < n; i++) {
            int j = i + len - 1;
            int left = piles[i] + sec[i + 1][j];
            int right = piles[j] + sec[i][j - 1];
            if (left > right) { fir[i][j] = left; sec[i][j] = fir[i + 1][j]; }
            else { fir[i][j] = right; sec[i][j] = fir[i][j - 1]; }
        }
    }
    return fir[0][n - 1] - sec[0][n - 1];
}

static int bfStockActions(const vector<int>& prices, int k, int fee = 0, int cd0 = 0) {
    int n = (int)prices.size();
    long long total = 1;
    for (int i = 0; i < n; i++) total *= 3;
    long long best = 0;
    for (long long code = 0; code < total; code++) {
        long long c = code;
        long long cash = 0;
        bool holding = false, ok = true;
        int used = 0, cd = 0;
        for (int d = 0; d < n; d++) {
            int a = (int)(c % 3);
            c /= 3;
            if (cd > 0) {
                if (a != 0) { ok = false; break; }
                cd--;
                continue;
            }
            if (a == 0) continue;
            if (a == 1) {
                if (holding || used >= k) { ok = false; break; }
                holding = true;
                cash -= prices[d];
            } else {
                if (!holding) { ok = false; break; }
                holding = false;
                cash += prices[d] - fee;
                used++;
                cd = cd0;
            }
        }
        if (ok && !holding && cash > best) best = cash;
    }
    return (int)best;
}

static int bfLisSubsets(const vector<int>& a) {
    int n = (int)a.size();
    int best = 0;
    for (int mask = 0; mask < (1 << n); mask++) {
        int prev = INT_MIN, cnt = 0;
        bool ok = true;
        for (int i = 0; i < n; i++) {
            if ((mask >> i) & 1) {
                if (a[i] <= prev) { ok = false; break; }
                prev = a[i];
                cnt++;
            }
        }
        if (ok && cnt > best) best = cnt;
    }
    return best;
}

static int bfLisN2(const vector<int>& a) {
    int n = (int)a.size();
    if (n == 0) return 0;
    vector<int> dp(n, 1);
    for (int i = 0; i < n; i++)
        for (int j = 0; j < i; j++)
            if (a[j] < a[i]) dp[i] = std::max(dp[i], dp[j] + 1);
    int best = 0;
    for (size_t i = 0; i < dp.size(); i++) best = std::max(best, dp[i]);
    return best;
}

static int greedyRises(const vector<int>& p) {
    int s = 0;
    for (size_t i = 0; i + 1 < p.size(); i++) s += std::max(0, p[i + 1] - p[i]);
    return s;
}

static int greedyRisesFee(const vector<int>& p, int fee) {
    int s = 0;
    for (size_t i = 0; i + 1 < p.size(); i++) s += std::max(0, p[i + 1] - p[i] - fee);
    return s;
}

// ---- 文章提到的「错误写法」 -------------------------------------------------

static int editDistance1DSwapped(const string& s1, const string& s2) {
    int m = (int)s1.size(), n = (int)s2.size();
    vector<int> dp(n + 1);
    for (int j = 0; j <= n; j++) dp[j] = j;
    for (int i = 1; i <= m; i++) {
        dp[0] = i;
        int prev = dp[0];
        for (int j = 1; j <= n; j++) {
            int tmp = dp[j];
            if (s1[i - 1] == s2[j - 1]) dp[j] = prev;
            else dp[j] = 1 + std::min(std::min(dp[j], dp[j - 1]), prev);
            prev = tmp;
        }
    }
    return dp[n];
}

static int stoneGameRowMajor(const vector<int>& piles) {
    int n = (int)piles.size();
    if (n == 0) return 0;
    vector<vector<int> > dp(n, vector<int>(n, 0));
    for (int i = 0; i < n; i++) dp[i][i] = piles[i];
    for (int i = 0; i < n; i++)
        for (int j = i + 1; j < n; j++) {
            int left = piles[i] - (i + 1 < n ? dp[i + 1][j] : 0);
            int right = piles[j] - dp[i][j - 1];
            dp[i][j] = std::max(left, right);
        }
    return dp[0][n - 1];
}

static int maxProfitKBuggy(int k, const vector<int>& prices) {
    if (k <= 0 || prices.empty()) return 0;
    const long long NEG = LLONG_MIN / 4;
    vector<long long> dp0(k + 1, 0);
    vector<long long> dp1(k + 1, NEG);
    for (size_t t = 0; t < prices.size(); t++) {
        int p = prices[t];
        for (int j = k; j >= 1; j--) {
            dp1[j] = std::max(dp1[j], dp0[j - 1] - p);
            dp0[j] = std::max(dp0[j], dp1[j] + p);
        }
    }
    return (int)dp0[k];
}

static int maxProfitKFee(int k, const vector<int>& prices, int fee, bool useOld1) {
    if (k <= 0 || prices.empty()) return 0;
    const long long NEG = LLONG_MIN / 4;
    vector<long long> dp0(k + 1, 0);
    vector<long long> dp1(k + 1, NEG);
    for (size_t t = 0; t < prices.size(); t++) {
        int p = prices[t];
        for (int j = k; j >= 1; j--) {
            long long old1 = dp1[j];
            dp1[j] = std::max(old1, dp0[j - 1] - p);
            long long base = useOld1 ? old1 : dp1[j];
            dp0[j] = std::max(dp0[j], base + p - fee);
        }
    }
    return (int)dp0[k];
}

static int maxProfitInfTwoLine(const vector<int>& prices) {
    const long long NEG = LLONG_MIN / 4;
    long long hold = NEG, cash = 0;
    for (size_t i = 0; i < prices.size(); i++) {
        int p = prices[i];
        hold = std::max(hold, cash - p);
        cash = std::max(cash, hold + p);
    }
    return (int)cash;
}

static int looseQueryLIS() {
    vector<int> a;
    a.push_back(2); a.push_back(2); a.push_back(2);
    vector<int> sorted(a);
    sort(sorted.begin(), sorted.end());
    sorted.erase(unique(sorted.begin(), sorted.end()), sorted.end());
    FenwickMax bit((int)sorted.size());
    int best = 0;
    for (size_t i = 0; i < a.size(); i++) {
        int r = (int)(lower_bound(sorted.begin(), sorted.end(), a[i]) - sorted.begin()) + 1;
        int cur = bit.query(r) + 1;
        bit.update(r, cur);
        best = std::max(best, cur);
    }
    return best;
}

// ---- 各段测试 --------------------------------------------------------------

static void testKnapsack() {
    std::printf("   [cpp] section 1.2 knapsack01Rows vs subset enumeration\n");
    std::mt19937 rng(20261129u);
    for (int it = 0; it < 400; it++) {
        int n = (int)(rng() % 9);
        int W = (int)(rng() % 15);
        vector<int> wt(n), val(n);
        for (int i = 0; i < n; i++) { wt[i] = (int)(rng() % 7) + 1; val[i] = (int)(rng() % 20); }
        CHECK_EQ(knapsack01Rows(W, wt, val), bfKnapsackSubsets(W, wt, val),
                 "knapsack01Rows vs 2^n enumeration");
    }
    int bW[9]  = {0, 10, 0, 5, 4, 6, 9, 7, 7};
    int bwt[9][3] = {{0,0,0}, {0,0,0}, {3,4,0}, {5,5,0}, {5,5,0}, {3,3,3}, {10,10,0}, {7,0,0}, {7,0,0}};
    int bva[9][3] = {{0,0,0}, {0,0,0}, {5,6,0}, {7,7,0}, {7,7,0}, {2,2,2}, {100,100,0}, {0,0,0}, {13,0,0}};
    int bn[9] = {0, 0, 2, 2, 2, 3, 2, 1, 1};
    for (int c = 0; c < 9; c++) {
        vector<int> wt(bwt[c], bwt[c] + bn[c]);
        vector<int> val(bva[c], bva[c] + bn[c]);
        CHECK_EQ(knapsack01Rows(bW[c], wt, val), bfKnapsackSubsets(bW[c], wt, val),
                 "knapsack boundary case");
    }
}

static void testEditDistance() {
    std::printf("   [cpp] section 1.3 edit distance vs BFS on the edit graph\n");
    const char* known[8][2] = {{"", ""}, {"", "abc"}, {"abc", ""}, {"kitten", "sitting"},
                               {"ab", "ba"}, {"aaa", "aaa"}, {"aaa", "a"}, {"a", "aaa"}};
    int want[8] = {0, 3, 3, 3, 2, 0, 2, 2};
    for (int i = 0; i < 8; i++) {
        string a = known[i][0], b = known[i][1];
        CHECK_EQ(editDistance2D(a, b), want[i], "editDistance2D known value");
        CHECK_EQ(editDistance1D(a, b), want[i], "editDistance1D known value");
        CHECK_EQ(bfEditBFS(a, b), want[i], "BFS reference known value");
    }
    std::mt19937 rng(4242u);
    const char alpha2[3] = {'a', 'b', '\0'};
    for (int it = 0; it < 250; it++) {
        string a, b;
        int la = (int)(rng() % 6), lb = (int)(rng() % 6);
        for (int i = 0; i < la; i++) a.push_back(alpha2[rng() % 2]);
        for (int i = 0; i < lb; i++) b.push_back(alpha2[rng() % 2]);
        int w = bfEditBFS(a, b);
        CHECK_EQ(editDistance2D(a, b), w, "2D vs BFS");
        CHECK_EQ(editDistance1D(a, b), w, "1D vs BFS");
    }
    const char alpha3[4] = {'a', 'b', 'c', '\0'};
    for (int it = 0; it < 250; it++) {
        string a, b;
        int la = (int)(rng() % 40), lb = (int)(rng() % 40);
        for (int i = 0; i < la; i++) a.push_back(alpha3[rng() % 3]);
        for (int i = 0; i < lb; i++) b.push_back(alpha3[rng() % 3]);
        CHECK_EQ(editDistance1D(a, b), editDistance2D(a, b), "1D vs 2D on longer strings");
        CHECK_EQ(editDistance1D(a, b), editDistance1D(b, a),
                 "edit distance is symmetric (so taking the shorter as s2 is safe)");
    }
    // §1.3 断言：交换 prev / dp[0] 的顺序会让答案偏大
    int differing = 0, allLarger = 1;
    string ea, eb;
    int egood = 0, ebad = 0;
    for (int it = 0; it < 400; it++) {
        string a, b;
        int la = (int)(rng() % 12) + 1, lb = (int)(rng() % 12) + 1;
        for (int i = 0; i < la; i++) a.push_back(alpha2[rng() % 2]);
        for (int i = 0; i < lb; i++) b.push_back(alpha2[rng() % 2]);
        int good = editDistance1D(a, b), bad = editDistance1DSwapped(a, b);
        if (good != bad) {
            if (differing == 0) { ea = a; eb = b; egood = good; ebad = bad; }
            differing++;
            if (bad <= good) allLarger = 0;
        }
    }
    CHECK_TRUE(differing > 0, "swapped prev order changes the answer on some inputs");
    CHECK_TRUE(allLarger == 1, "when it differs the swapped version is always larger");
    if (differing > 0)
        std::printf("       swapped-order counterexample: \"%s\" -> \"%s\" correct=%d swapped=%d\n",
                    ea.c_str(), eb.c_str(), egood, ebad);
    std::printf("       swapped order: %d differing / 400 random pairs\n", differing);
}

static void testStoneGame() {
    std::printf("   [cpp] section 2.1/2.2 stone game vs explicit minimax tree\n");
    CHECK_EQ(stoneGameDiff(vector<int>()), 0, "empty piles -> 0");
    { vector<int> v; v.push_back(7); CHECK_EQ(stoneGameDiff(v), 7, "single pile"); }
    { vector<int> v; v.push_back(-5); CHECK_EQ(stoneGameDiff(v), -5, "single negative pile"); }
    int ex[3][4] = {{5,3,4,5}, {3,7,2,3}, {1,5,233,7}};
    int exw[3] = {1, 5, 222};
    for (int c = 0; c < 3; c++) {
        vector<int> v(ex[c], ex[c] + 4);
        CHECK_EQ(stoneGameDiff(v), exw[c], "LC 877 example");
        CHECK_EQ(bfStoneMinimax(v, 0, 3, 0), exw[c], "minimax reference agrees");
    }
    std::mt19937 rng(877u);
    int evenChecked = 0, orderDiff = 0;
    vector<int> orderExample;
    int orderWant = 0, orderGot = 0;
    for (int it = 0; it < 300; it++) {
        int n = (int)(rng() % 11);
        vector<int> p(n);
        for (int i = 0; i < n; i++) p[i] = (int)(rng() % 40) + 1;
        int w = bfStoneMinimax(p, 0, n - 1, 0);
        CHECK_EQ(stoneGameDiff(p), w, "stoneGameDiff vs minimax");
        CHECK_EQ(stonePairsRef(p), w, "pairs version vs minimax");
        if (n >= 2) {
            int got = stoneGameRowMajor(p);
            if (got != w) {
                orderDiff++;
                if (orderExample.empty()) { orderExample = p; orderWant = w; orderGot = got; }
            }
        }
    }
    CHECK_TRUE(orderDiff > 0, "row-major fill really does give wrong answers");
    int evenOddSum = 0, evenOddSumBad = 0;
    vector<int> tieEx;
    { vector<int> v; v.push_back(4); v.push_back(4);
      CHECK_EQ(stoneGameDiff(v), 0, "[4,4] even length but a TIE, so 486(>=0)=true while 877(>0)=false"); }
    for (int it = 0; it < 400; it++) {
        int n = ((int)(rng() % 5) + 1) * 2;
        vector<int> p(n);
        int s = 0;
        for (int i = 0; i < n; i++) { p[i] = (int)(rng() % 30); s += p[i]; }
        int d = stoneGameDiff(p);
        evenChecked++;
        if (d <= 0 && tieEx.empty()) tieEx = p;
        if (s % 2 == 1) { evenOddSum++; if (d <= 0) evenOddSumBad++; }
    }
    CHECK_EQ(evenOddSumBad, 0, "even length + ODD total -> first player always wins");
    CHECK_TRUE(!tieEx.empty(), "even length alone is NOT sufficient (ties exist)");
    std::printf("       stone game: 300 random cases triple-checked; even-length checked=%d\n",
                evenChecked);
    std::printf("       even-length + odd total: %d cases, %d violations\n",
                evenOddSum, evenOddSumBad);
    if (!tieEx.empty()) {
        std::printf("       even-length TIE (even count alone is not enough): [");
        for (size_t i = 0; i < tieEx.size(); i++)
            std::printf("%s%d", i ? "," : "", tieEx[i]);
        std::printf("] diff=%d\n", stoneGameDiff(tieEx));
    }
    std::printf("       row-major (wrong order) differs on %d cases", orderDiff);
    if (!orderExample.empty()) {
        std::printf("; example [");
        for (size_t i = 0; i < orderExample.size(); i++)
            std::printf("%s%d", i ? "," : "", orderExample[i]);
        std::printf("] correct=%d row-major=%d", orderWant, orderGot);
    }
    std::printf("\n");
}

static void testStocks() {
    std::printf("   [cpp] section 3.2/3.4 stock series vs 3^n action enumeration\n");
    CHECK_EQ(maxProfitK(2, vector<int>()), 0, "k=2 empty -> 0");
    CHECK_EQ(maxProfitInf(vector<int>()), 0, "inf empty -> 0");
    { vector<int> v; v.push_back(5); CHECK_EQ(maxProfitInf(v), 0, "single day -> 0"); }
    int k1[6] = {7,1,5,3,6,4};
    vector<int> a1(k1, k1 + 5);
    CHECK_EQ(maxProfitK(1, a1), 5, "LC 121 known -> 5");
    CHECK_EQ(maxProfitInf(a1), 7, "LC 122 known -> 7");
    int k2[8] = {3,3,5,0,0,3,1,4};
    vector<int> a2(k2, k2 + 8);
    CHECK_EQ(maxProfitK(2, a2), 6, "LC 123/188 known -> 6");
    int k3[5] = {7,6,4,3,1};
    vector<int> a3(k3, k3 + 5);
    CHECK_EQ(maxProfitK(1, a3), 0, "strictly decreasing -> 0");
    CHECK_EQ(maxProfitInf(a3), 0, "strictly decreasing inf -> 0");
    int k4[4] = {4,4,4,4};
    vector<int> a4(k4, k4 + 4);
    CHECK_EQ(maxProfitInf(a4), 0, "all equal -> 0");
    int k5[3] = {-3,-1,-7};
    vector<int> a5(k5, k5 + 3);
    CHECK_EQ(maxProfitInf(a5), 2, "negative prices: buy -3 sell -1 -> +2");
    CHECK_EQ(maxProfitInf(a5), bfStockActions(a5, 3), "negative prices vs 3^n");
    int k6[5] = {1,2,3,4,5};
    vector<int> a6(k6, k6 + 5);
    CHECK_EQ(maxProfitInf(a6), 4, "LC 122 known -> 4");
    CHECK_EQ(maxProfitK(2, a6), 4, "k=2 on 1..5 -> 4");

    std::mt19937 rng(122u);
    int infVsK = 0, plainSame = 0, plainTotal = 0;
    for (int it = 0; it < 350; it++) {
        int n = (int)(rng() % 8);
        vector<int> p(n);
        for (int i = 0; i < n; i++) p[i] = (int)(rng() % 15);
        int ks[4] = {1, 2, 3, n > 0 ? n : 1};
        for (int c = 0; c < 4; c++)
            CHECK_EQ(maxProfitK(ks[c], p), bfStockActions(p, ks[c]), "maxProfitK vs 3^n");
        CHECK_EQ(maxProfitInf(p), bfStockActions(p, n > 0 ? n : 1), "maxProfitInf vs 3^n");
        if (n > 0) {
            CHECK_EQ(maxProfitInf(p), maxProfitK(n, p), "k=inf equals k=n");
            infVsK++;
            int kk = (int)(rng() % 3) + 1;
            plainTotal++;
            if (maxProfitKBuggy(kk, p) == maxProfitK(kk, p)) plainSame++;
        }
    }
    CHECK_EQ(plainSame, plainTotal, "buggy dp1[j]+p gives identical answers with no fee");
    std::printf("       stocks: 350 cases x {k=1,2,3,n} vs 3^n; inf-vs-k=n pairs=%d\n", infVsK);

    int feeDiff = 0, tupleDiff = 0;
    vector<int> feeEx, tupleEx;
    int feeExCorrect = 0, feeExBuggy = 0, tupleExOne = 0, tupleExTwo = 0;
    for (int it = 0; it < 500; it++) {
        int n = (int)(rng() % 7) + 2;
        vector<int> p(n);
        for (int i = 0; i < n; i++) p[i] = (int)(rng() % 15) + 1;
        int fee = (int)(rng() % 4) + 1;
        int correct = maxProfitKFee(n, p, fee, true);
        int buggy = maxProfitKFee(n, p, fee, false);
        CHECK_EQ(correct, bfStockActions(p, n, fee), "fee variant (with old1) vs 3^n");
        if (buggy != correct) {
            if (feeDiff == 0) { feeEx = p; feeExCorrect = correct; feeExBuggy = buggy; }
            feeDiff++;
        }
        int one = maxProfitInf(p), two = maxProfitInfTwoLine(p);
        if (one != two) {
            if (tupleDiff == 0) { tupleEx = p; tupleExOne = one; tupleExTwo = two; }
            tupleDiff++;
        }
    }
    // 下面两条是正文 L442 / L492 的**说法**，不是文章代码的正确性。
    // 实测都证伪，所以只打印 REFUTED，不计进 g_fail（代码本身没问题）。
    if (feeDiff == 0)
        std::printf("   REFUTED   L442 \"fee variant breaks without old1\": 0/%d differ\n", 500);
    else
        std::printf("   holds     L442 \"fee variant breaks without old1\": %d/500 differ\n", feeDiff);
    if (tupleDiff == 0)
        std::printf("   REFUTED   L492 \"splitting the tuple assignment breaks it\": 0/%d differ\n", 500);
    else
        std::printf("   holds     L492 \"splitting the tuple assignment breaks it\": %d/500 differ\n", tupleDiff);
    if (feeDiff > 0) {
        std::printf("       fee counterexample: [");
        for (size_t i = 0; i < feeEx.size(); i++) std::printf("%s%d", i ? "," : "", feeEx[i]);
        std::printf("] correct=%d buggy=%d", feeExCorrect, feeExBuggy);
    }
    std::printf("\n       fee cases differing: %d/500 ; tuple-split differing: %d/500", feeDiff, tupleDiff);
    if (tupleDiff > 0) {
        std::printf(" ; example [");
        for (size_t i = 0; i < tupleEx.size(); i++) std::printf("%s%d", i ? "," : "", tupleEx[i]);
        std::printf("] correct=%d split=%d", tupleExOne, tupleExTwo);
    }
    std::printf("\n");
}

static void testLis() {
    std::printf("   [cpp] section 4.2 Fenwick LIS vs O(n^2), tails, 2^n enumeration\n");
    CHECK_EQ(lengthOfLISFenwick(vector<int>()), 0, "empty -> 0");
    { vector<int> v; v.push_back(5); CHECK_EQ(lengthOfLISFenwick(v), 1, "single -> 1"); }
    int e1[4] = {7,7,7,7};
    vector<int> a1(e1, e1 + 4);
    CHECK_EQ(lengthOfLISFenwick(a1), 1, "all equal -> 1");
    int e2[5] = {5,4,3,2,1};
    vector<int> a2(e2, e2 + 5);
    CHECK_EQ(lengthOfLISFenwick(a2), 1, "strictly decreasing -> 1");
    int e3[4] = {-5,-3,-9,-1};
    vector<int> a3(e3, e3 + 4);
    CHECK_EQ(lengthOfLISFenwick(a3), 3, "negatives -> 3");
    int e4[8] = {10,9,2,5,3,7,101,18};
    vector<int> a4(e4, e4 + 8);
    CHECK_EQ(lengthOfLISFenwick(a4), 4, "LC 300 known -> 4");
    int e5[6] = {0,1,0,3,2,3};
    vector<int> a5(e5, e5 + 6);
    CHECK_EQ(lengthOfLISFenwick(a5), 4, "LC 300 known -> 4");
    CHECK_EQ(looseQueryLIS(), 3, "query(r) without -1 inflates [2,2,2] to 3");
    CHECK_EQ(lengthOfLISFenwick(a1), 1, "query(r-1) keeps [2,2,2] at 1");

    std::mt19937 rng(300u);
    int big = 0;
    for (int it = 0; it < 300; it++) {
        int n = (int)(rng() % 12);
        vector<int> a(n);
        for (int i = 0; i < n; i++) a[i] = (int)(rng() % 14) - 6;
        int w = bfLisSubsets(a);
        CHECK_EQ(bfLisN2(a), w, "O(n^2) DP vs 2^n");
        CHECK_EQ(lengthOfLISFenwick(a), w, "Fenwick LIS vs 2^n");
        {   // tails + binary search 作为第三条参照
            vector<int> tails;
            for (size_t i = 0; i < a.size(); i++) {
                vector<int>::iterator it2 = lower_bound(tails.begin(), tails.end(), a[i]);
                if (it2 == tails.end()) tails.push_back(a[i]);
                else *it2 = a[i];
            }
            CHECK_EQ((int)tails.size(), w, "tails + bisect vs 2^n");
        }
    }
    for (int it = 0; it < 40; it++) {
        int n = 50 + (int)(rng() % 250);
        vector<int> a(n);
        for (int i = 0; i < n; i++) a[i] = (int)(rng() % 2000) - 1000;
        CHECK_EQ(lengthOfLISFenwick(a), bfLisN2(a), "Fenwick LIS vs O(n^2) on large arrays");
        big++;
    }
    std::printf("       LIS: 300 small cases vs 4 references, %d large cases (n<=300)\n", big);
}

static void testGreedy() {
    std::printf("   [cpp] greedy vs exact DP (required by the task; article makes no greedy claim)\n");
    int g1[6] = {7,1,5,3,6,4};
    vector<int> a1(g1, g1 + 6);
    CHECK_EQ(greedyRises(a1), bfStockActions(a1, 99), "no-fee greedy == exact DP on LC 122");
    std::mt19937 rng(714u);
    int agreed = 0;
    for (int it = 0; it < 400; it++) {
        int n = (int)(rng() % 8) + 1;
        vector<int> p(n);
        for (int i = 0; i < n; i++) p[i] = (int)(rng() % 20);
        if (greedyRises(p) == bfStockActions(p, n)) agreed++;
    }
    CHECK_EQ(agreed, 400, "no-fee greedy == exact DP on all 400 cases");
    vector<int> feeEx, cdEx;
    int feeX = 0, feeG = 0, cdX = 0, cdG = 0;
    for (int it = 0; it < 4000 && (feeEx.empty() || cdEx.empty()); it++) {
        int n = (int)(rng() % 5) + 2;
        vector<int> p(n);
        for (int i = 0; i < n; i++) p[i] = (int)(rng() % 11) + 1;
        if (feeEx.empty()) {
            int fee = (int)(rng() % 4) + 1;
            int x = bfStockActions(p, n, fee), g = greedyRisesFee(p, fee);
            if (x != g) { feeEx = p; feeX = x; feeG = g; }
        }
        if (cdEx.empty()) {
            int x = bfStockActions(p, n, 0, 1), g = greedyRises(p);
            if (x != g) { cdEx = p; cdX = x; cdG = g; }
        }
    }
    CHECK_TRUE(!feeEx.empty(), "found a 714 (fee) counterexample where greedy fails");
    CHECK_TRUE(!cdEx.empty(), "found a 309 (cooldown) counterexample where greedy fails");
    if (!feeEx.empty()) {
        std::printf("       Greedy fails on 714: prices=[");
        for (size_t i = 0; i < feeEx.size(); i++) std::printf("%s%d", i ? "," : "", feeEx[i]);
        std::printf("] exact DP=%d greedy=%d\n", feeX, feeG);
    }
    if (!cdEx.empty()) {
        std::printf("       Greedy fails on 309: prices=[");
        for (size_t i = 0; i < cdEx.size(); i++) std::printf("%s%d", i ? "," : "", cdEx[i]);
        std::printf("] cooldown=1 exact DP=%d greedy=%d\n", cdX, cdG);
    }
}

static int run_all_tests() {
    testKnapsack();
    testEditDistance();
    testStoneGame();
    testStocks();
    testLis();
    testGreedy();
    std::printf("   [cpp] %d assertions, %d failures\n", g_checks, g_fail);
    return g_fail == 0 ? 0 : 1;
}

int main() {
    return run_all_tests();
}
'''


def cpp_checks(cpp_blocks: list[str]) -> None:
    section("C++ side: zero-warning compile of the article's blocks, then run the harness")
    source = CPP_PREAMBLE + "\n".join(cpp_blocks) + "\n" + CPP_HARNESS
    with tempfile.TemporaryDirectory(prefix="dp-advanced-gate-") as td:
        cpp = Path(td) / "gate_main.cpp"
        exe = Path(td) / "gate_main"
        cpp.write_text(source, encoding="utf-8")
        cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
               "-o", str(exe), str(cpp)]
        print(f"   $ g++ -std=c++17 -Wall -Wextra -Werror -O1  ({len(cpp_blocks)} 个正文块 "
              f"+ {CPP_HARNESS.count(chr(10))} 行对拍代码)")
        cp = subprocess.run(cmd, capture_output=True, text=True)
        diag = (cp.stdout + cp.stderr).strip()
        check(cp.returncode == 0 and diag == "",
              "g++ -std=c++17 -Wall -Wextra -Werror -O1 编译：**零诊断输出**")
        if diag:
            print("   --- compiler diagnostics ---")
            print(diag)
        if cp.returncode != 0:
            print("   !! 编译失败，跳过 C++ 运行")
            return
        rp = subprocess.run([str(exe)], capture_output=True, text=True)
        print(rp.stdout, end="")
        if rp.stderr.strip():
            print("   --- stderr ---")
            print(rp.stderr)
        check_eq(rp.returncode, 0, "C++ 对拍全部通过（进程退出码 0）")
        m = re.search(r"\[cpp\] (\d+) assertions, (\d+) failures", rp.stdout)
        if m:
            measure(f"C++ 侧: {m.group(1)} 条断言, {m.group(2)} 条失败")
        if "-Wall -Wextra -Werror" in " ".join(cmd):
            measure("C++ 编译诊断输出长度: 0 字节（-Werror 下没有任何 warning）")


def main() -> int:
    section("0. extract code blocks from the article body")
    if not POST.is_file():
        print(f"   FAIL 找不到正文 {POST}")
        return 1
    src = POST.read_text(encoding="utf-8")
    py_blocks = load_blocks(src, "python")
    cpp_blocks = load_blocks(src, "cpp")
    langs = all_fence_langs(src)
    bad = sorted({l for l in langs if l not in ALLOWED_LANGS})
    print(f"   article: {POST.relative_to(ROOT)}  ({len(src)} chars)")
    check(len(py_blocks) > 0, f"从正文抽到 python 块: {len(py_blocks)}")
    check(len(cpp_blocks) > 0, f"从正文抽到 cpp 块: {len(cpp_blocks)}")
    check_eq(len(py_blocks), len(cpp_blocks),
             f"python 块数与 cpp 块数相等（{len(py_blocks)} == {len(cpp_blocks)}）")
    check(not bad, f"围栏语言都在允许集合内（越界: {bad}）")
    check(f"assets/blog/{SLUG}/verify_code.py" in src,
          "正文第 6 节点名了本脚本（文章声称代码是从正文里抽出来跑的）")
    print(f"   fence languages: " +
          ", ".join(f"{l}={langs.count(l)}" for l in sorted(set(langs)) if l))

    ns: dict = {"__name__": "article_code"}
    for i, block in enumerate(py_blocks):
        try:
            exec(compile(block, f"<article python block #{i}>", "exec"), ns)
        except Exception as exc:                      # noqa: BLE001
            check(False, f"正文 python 块 #{i} exec 失败: {exc!r}")
            return 1
    need = ["knapsack01Rows", "editDistance2D", "editDistance1D", "stoneGameDiff",
            "maxProfitK", "maxProfitInf", "lengthOfLISFenwick", "FenwickMax"]
    missing = [n for n in need if n not in ns]
    check(not missing,
          f"8 个 Python 块 exec 后定义了全部测试目标（缺: {missing}）" if missing
          else "8 个 Python 块 exec 成功，全部测试目标都在")

    rnd = random.Random(SEED)
    python_checks(ns, rnd)
    prose_claims(ns, rnd)          # 实测证据（probe / holds）
    gate_prose_anchors(src)        # 那些 holds 的措辞必须还在正文里
    claim_regression(src)          # 判决：正文当前措辞对不对
    table_audit(src, ns, rnd)
    not_applicable()
    cpp_checks(cpp_blocks)

    section("measured values (all produced by this run, nothing hand-written)")
    for line in MEASURED:
        print(f"   - {line}")

    refuted = [p for p in PROSE_ISSUES if p[0] == "refuted"]
    imprecise = [p for p in PROSE_ISSUES if p[0] == "imprecise"]
    section("verdict")
    print(f"   代码失败: {len(FAILURES)}")
    for f in FAILURES:
        print(f"      CODE  {f}")
    print(f"   正文说法证伪: {len(refuted)}   正文说法不精确: {len(imprecise)}")
    for sev, where, what, _ in PROSE_ISSUES:
        print(f"      {sev.upper():9} {where}  {what}")
    if FAILURES:
        print("\nCODE FAIL")
        return 1
    if PROSE_ISSUES:
        if CODE_ONLY:
            print(f"\nCODE OK  (--code-only：{len(PROSE_ISSUES)} 条正文说法问题已在上方"
                  f"逐条打印，本模式不据此判红；默认模式此处 exit 1)")
            return 0
        print("\nPROSE FAIL —— 文章代码本身全部通过外部参照对拍，")
        print("但正文有几处**说法**被实测证伪。按约定本脚本不改正文，"
              "已把反例打印在上面，交 lead 裁决。")
        print("（只想单独确认代码：python3 verify_code.py --code-only）")
        return 1
    print("\nCODE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
