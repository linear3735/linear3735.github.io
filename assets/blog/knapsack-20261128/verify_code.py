#!/usr/bin/env python3
"""代码门 for _posts/2026-11-28-knapsack.md

从文章里正则抽出所有 ```python 和 ```cpp 片段，然后：

  1) Python：逐块 compile()（语法检查），再按文中顺序 exec 进同一个命名空间，
     跑固定用例 + 与暴力解随机对拍。
  2) C++  ：把抽出来的片段**原样**拼进一个 .cpp，接上本目录 cpp_tests.cpp 里的驱动，
     用 g++ -std=c++17 -Wall -Wextra -O1 编译（要求零警告）并运行同一批用例。

两个关键点：
  * 文章里的函数体一个字都不复制，C++ 侧也是从 markdown 抽出来再编译的，
    所以「文章里的 C++ 能编译、能跑对」是真的被验证过的，不是靠另抄一份。
  * 随机对拍的另一方（ref_*）写在本文件里，是独立实现，不是文章函数的改写。

用法：python3 verify_code.py [--repo /path/to/site] [--seed N]
退出码：0 全绿，1 有问题。
"""
import argparse
import pathlib
import random
import re
import subprocess
import sys
import tempfile

EXPECTED_PY_BLOCKS = 12
EXPECTED_CPP_BLOCKS = 12
CPP_STD = "-std=c++17"
CPP_WARN = ["-Wall", "-Wextra", "-O1"]


def extract(text: str, lang: str):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


# --------------------------------------------------------------------------
# 独立参考实现（只用于对拍，不出现在文章里）
# --------------------------------------------------------------------------
def ref_brute_exact(W, wt, val):
    """恰好装满的暴力解：枚举子集，只认总重 == W 的。"""
    best = None
    for mask in range(1 << len(wt)):
        tw = sum(wt[i] for i in range(len(wt)) if (mask >> i) & 1)
        tv = sum(val[i] for i in range(len(wt)) if (mask >> i) & 1)
        if tw == W and (best is None or tv > best):
            best = tv
    return -1 if best is None else best


def ref_unbounded(W, wt, val):
    """完全背包的二维参考实现（和文章里的一维写法不同形）。"""
    n = len(wt)
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wt[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i][w - wt[i - 1]] + val[i - 1])
    return dp[n][W]


def ref_combos(amount, coins):
    """枚举非降序的面额序列：{1,2} 和 {2,1} 只算一次。"""
    def go(rest, start):
        total = 1 if rest == 0 else 0
        for i in range(start, len(coins)):
            if coins[i] <= rest:
                total += go(rest - coins[i], i)
        return total
    return go(amount, 0)


def ref_perms(amount, coins):
    """枚举有序的面额序列：{1,2} 和 {2,1} 算两次。"""
    def go(rest):
        if rest == 0:
            return 1
        return sum(go(rest - c) for c in coins if 1 <= c <= rest)
    return go(amount)


def ref_can_partition(nums):
    total = sum(nums)
    for mask in range(1 << len(nums)):
        s = sum(nums[i] for i in range(len(nums)) if (mask >> i) & 1)
        if 2 * s == total:
            return True
    return False


def ref_min_distance(s1, s2):
    """记忆化递归版（文章里是填表版），独立的第二实现。"""
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def f(i, j):
        if i == 0:
            return j
        if j == 0:
            return i
        if s1[i - 1] == s2[j - 1]:
            return f(i - 1, j - 1)
        return 1 + min(f(i - 1, j), f(i, j - 1), f(i - 1, j - 1))

    return f(len(s1), len(s2))


OPS_RE = re.compile(
    r"^delete s1\[(?P<dpos>\d+)\]='(?P<dch>.)'$"
    r"|^replace s1\[(?P<rpos>\d+)\]='(?P<rfrom>.)'->'(?P<rto>.)'$"
    r"|^insert at (?P<ipos>\d+) '(?P<ich>.)'$"
)


def apply_ops(s1, ops):
    """把 minDistanceOps 给出的序列真的作用到 s1 上，同时检查位置合法性。

    位置必须从左到右单调不减；两次操作之间被「跨过」的字符是 s1 里被匹配、
    不需要动的部分，原样保留。
    """
    out = []
    cursor = 0
    prev_pos = -1
    for op in ops:
        m = OPS_RE.match(op)
        assert m, f"操作格式不认识: {op!r}"
        if m.group("dpos") is not None:
            pos, kind, ch, new = int(m.group("dpos")), "delete", m.group("dch"), None
        elif m.group("rpos") is not None:
            pos, kind, ch, new = int(m.group("rpos")), "replace", m.group("rfrom"), m.group("rto")
        else:
            pos, kind, ch, new = int(m.group("ipos")), "insert", None, m.group("ich")
        assert pos >= prev_pos, f"位置没有单调不减: {op!r} (prev={prev_pos})"
        assert pos >= cursor, f"位置倒退: {op!r} (cursor={cursor})"
        prev_pos = pos
        out.append(s1[cursor:pos])            # 被跳过的字符：本来就是匹配上的
        if kind == "insert":
            out.append(new)
            cursor = pos
        else:
            assert pos < len(s1) and s1[pos] == ch, \
                f"字符对不上: {op!r} 但 s1[{pos}]={s1[pos]!r}"
            if kind == "replace":
                out.append(new)
            cursor = pos + 1
    out.append(s1[cursor:])
    return "".join(out)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    # __file__ = <repo>/assets/blog/knapsack-20261128/verify_code.py
    ap.add_argument("--repo", default=str(pathlib.Path(__file__).resolve().parents[3]))
    ap.add_argument("--seed", type=int, default=20261128)
    args = ap.parse_args()
    repo = pathlib.Path(args.repo).expanduser().resolve()
    post = repo / "_posts/2026-11-28-knapsack.md"
    here = pathlib.Path(__file__).resolve().parent

    problems = []
    if not post.exists():
        print(f"  FAIL  missing {post}")
        return 1
    text = post.read_text(encoding="utf-8")

    py_blocks = extract(text, "python")
    cpp_blocks = extract(text, "cpp")
    print(f"  post          : {post.name}")
    print(f"  python blocks : {len(py_blocks)}  (expect {EXPECTED_PY_BLOCKS})")
    print(f"  cpp blocks    : {len(cpp_blocks)}  (expect {EXPECTED_CPP_BLOCKS})")
    if len(py_blocks) != EXPECTED_PY_BLOCKS:
        problems.append(f"python block count {len(py_blocks)} != {EXPECTED_PY_BLOCKS}")
    if len(cpp_blocks) != EXPECTED_CPP_BLOCKS:
        problems.append(f"cpp block count {len(cpp_blocks)} != {EXPECTED_CPP_BLOCKS}")
    if len(py_blocks) != len(cpp_blocks):
        problems.append("python / cpp block counts differ (每个问题两版必须成对)")

    # ---------------- Python ----------------
    ns = {}
    for idx, src in enumerate(py_blocks, 1):
        try:
            compile(src, f"<py block {idx}>", "exec")
        except SyntaxError as e:
            problems.append(f"python block {idx} syntax: {e}")
    if not problems:
        for idx, src in enumerate(py_blocks, 1):
            exec(compile(src, f"<py block {idx}>", "exec"), ns)

    rng = random.Random(args.seed)
    py_cases = 0

    def check(got, want, what):
        nonlocal py_cases
        py_cases += 1
        if got != want:
            problems.append(f"{what}: got {got!r}, want {want!r}")

    if not problems:
        k01 = ns["knapsack01"]
        k01r = ns["knapsack01Rolling"]
        kbrute = ns["knapsackBrute"]
        kexact = ns["knapsack01Exact"]
        kunb = ns["unboundedKnapsack"]
        combos = ns["changeCombinations"]
        perms = ns["changePermutations"]
        parts = ns["canPartition"]
        tbrute = ns["findTargetSumWaysBrute"]
        tsum = ns["findTargetSumWays"]
        edit = ns["minDistance"]
        editops = ns["minDistanceOps"]

        # --- 固定用例（含题目要求的边界）---
        wt, val = [2, 1, 3], [4, 2, 3]
        for name, fn in (("brute", kbrute), ("01", k01), ("rolling", k01r)):
            check(fn(4, wt, val), 6, f"knapsack {name} W=4")
            check(fn(0, wt, val), 0, f"knapsack {name} 容量 0")
            check(fn(4, [], []), 0, f"knapsack {name} 空物品")
            check(fn(1, [5], [9]), 0, f"knapsack {name} 单件装不下")
            check(fn(5, [5], [9]), 9, f"knapsack {name} 单件刚好装下")
        # 恰好装满和「至多装」不是一回事：W=4 时只有 {1,3} 能正好填满，价值 5；
        # W=3 时 {2,1} 正好填满，价值 6（这才是文章里那个 6）
        check(kexact(4, wt, val), 5, "恰好装满 W=4")
        check(kexact(3, wt, val), 6, "恰好装满 W=3")
        check(kexact(3, [2, 2], [3, 3]), -1, "恰好装满 装不满")
        check(kexact(4, [2, 2], [3, 3]), 6, "恰好装满 刚好")
        check(kexact(0, wt, val), 0, "恰好装满 W=0")
        check(kexact(7, [2, 4], [5, 9]), -1, "恰好装满 无解")
        check(kunb(4, [2], [3]), 6, "完全背包 同一物品装两次")
        check(kunb(0, [2], [3]), 0, "完全背包 容量 0")
        check(kunb(4, [], []), 0, "完全背包 空物品")
        check(combos(5, [1, 2, 5]), 4, "组合数 518 样例")
        check(perms(5, [1, 2, 5]), 9, "排列数 同样例")
        check(combos(0, [1, 2]), 1, "组合数 amount=0")
        check(combos(3, []), 0, "组合数 无面额")
        check(perms(0, []), 1, "排列数 amount=0 无面额")
        check(parts([1, 5, 11, 5]), True, "416 样例 true")
        check(parts([1, 2, 3, 5]), False, "416 样例 false")
        check(parts([1, 2]), False, "416 奇数和")
        check(parts([2]), False, "416 单元素：{2} vs {} 不是平分")
        check(parts([]), True, "416 空数组（我们自己的约定）")
        check(tbrute([1, 1, 1, 1, 1], 3), 5, "494 暴力样例")
        check(tsum([1, 1, 1, 1, 1], 3), 5, "494 样例")
        check(tsum([1], 1), 1, "494 单元素")
        check(tsum([1], 2), 0, "494 无解")
        check(tsum([0], 0), 2, "494 零元素 +0/-0 两种")
        check(tsum([0, 0], 0), 4, "494 两个零 四种")
        check(edit("horse", "ros"), 3, "72 样例 horse/ros")
        check(edit("intention", "execution"), 5, "72 样例 intention")
        check(edit("", ""), 0, "72 两个空串")
        check(edit("abc", ""), 3, "72 只能删")
        check(edit("", "abc"), 3, "72 只能插")
        check(edit("abc", "abc"), 0, "72 完全相同")

        # --- 随机对拍 ---
        for _ in range(200):
            n = rng.randint(0, 9)
            W = rng.randint(0, 14)
            wt = [rng.randint(0, 8) for _ in range(n)]
            val = [rng.randint(0, 20) for _ in range(n)]
            check(k01(W, wt, val), kbrute(W, wt, val), f"随机 0-1 二维 vs 暴力 W={W}")
            check(k01r(W, wt, val), kbrute(W, wt, val), f"随机 0-1 一维 vs 暴力 W={W}")
            check(kexact(W, wt, val), ref_brute_exact(W, wt, val), f"随机恰好装满 W={W}")
            check(kunb(W, wt, val), ref_unbounded(W, wt, val), f"随机完全背包 W={W}")
        for _ in range(120):
            amount = rng.randint(0, 11)
            coins = rng.sample([1, 2, 3, 4, 5, 6], rng.randint(0, 4))
            check(combos(amount, coins), ref_combos(amount, coins),
                  f"随机组合数 amount={amount} coins={coins}")
            check(perms(amount, coins), ref_perms(amount, coins),
                  f"随机排列数 amount={amount} coins={coins}")
        for _ in range(120):
            nums = [rng.randint(1, 9) for _ in range(rng.randint(0, 8))]
            check(parts(nums), ref_can_partition(nums), f"随机 416 nums={nums}")
            target = rng.randint(-6, 6)
            check(tsum(nums, target), tbrute(nums, target),
                  f"随机 494 nums={nums} target={target}")
        for _ in range(120):
            s1 = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
            s2 = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
            d = edit(s1, s2)
            check(d, ref_min_distance(s1, s2), f"随机 72 {s1!r}->{s2!r}")
            ops = editops(s1, s2)
            check(len(ops), d, f"随机 72 操作数 {s1!r}->{s2!r}")
            check(apply_ops(s1, ops), s2, f"随机 72 操作序列 {s1!r}->{s2!r}")

        print(f"  python cases  : {py_cases} fixed + random, "
              f"{'all pass' if not problems else 'FAILED'}")

    # ---------------- C++ ----------------
    cpp_runs = 0
    if not problems:
        driver = here / "cpp_tests.cpp"
        if not driver.exists():
            problems.append(f"missing {driver}")
        else:
            with tempfile.TemporaryDirectory() as td:
                src = pathlib.Path(td) / "main.cpp"
                src.write_text("\n".join(cpp_blocks) + "\n" + driver.read_text(encoding="utf-8"),
                               encoding="utf-8")
                exe = pathlib.Path(td) / "main"
                cmd = ["g++", CPP_STD, *CPP_WARN, str(src), "-o", str(exe)]
                cp = subprocess.run(cmd, capture_output=True, text=True)
                if cp.returncode != 0:
                    problems.append("g++ 编译失败:\n" + cp.stderr.strip())
                    print("  g++           : COMPILE FAILED")
                elif cp.stderr.strip():
                    problems.append("g++ 有警告（要求零警告）:\n" + cp.stderr.strip())
                    print("  g++           : WARNINGS")
                else:
                    print(f"  g++           : {CPP_STD} {' '.join(CPP_WARN)} 零警告")
                    rp = subprocess.run([str(exe)], capture_output=True, text=True)
                    sys.stdout.write(rp.stdout)
                    if rp.returncode != 0:
                        problems.append(f"C++ 测试失败 (exit {rp.returncode})")
                    else:
                        cpp_runs = 1

    print()
    if problems:
        for p in problems[:40]:
            print(f"  FAIL  {p}")
        print(f"\n  RESULT: {len(problems)} problem(s)")
        return 1
    print(f"  CODE OK — 文章里的 Python 与 C++ 全部跑通"
          f"{'，C++ 是真编译真运行' if cpp_runs else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
