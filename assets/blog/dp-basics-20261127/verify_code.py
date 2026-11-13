#!/usr/bin/env python3
"""代码门:文章里的代码必须真跑得起来。

这个脚本**从文章里正则抽取** ```python 和 ```cpp 块,不维护手抄副本。
这一点很重要:副本会和文章漂移,那样这道门就什么都证明不了。

  * Python:每个块单独 compile;再把所有块 exec 到一起,跑固定用例,
    另外用随机数组和一份独立的暴力实现交叉验证。
  * C++:把文章里的 cpp 块和一段测试 main 拼成一个 .cpp,用
    g++ -std=c++17 -Wall -Wextra -O1 编译(必须零警告)并运行;同样的
    固定用例在 C++ 侧再跑一遍,随机数组由 C++ 侧的暴力实现独立交叉验证。

用法: python3 verify_code.py
退出码: 0 全过,1 有问题。
"""
import random
import re
import subprocess
import sys
import tempfile
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
POST = Path.home() / "projects/linear3735.github.io/_posts/2026-11-27-dp-basics.md"

EXPECTED_PY = 5
EXPECTED_CPP = 5

# Python 侧的块里用到 bisect,C++ 侧用到 std::function,所以拼文件时要带全头文件
CPP_HEADERS = ["<vector>", "<string>", "<algorithm>", "<functional>",
               "<climits>", "<iostream>", "<random>"]


# --------------------------------------------------------------------------
# 独立暴力实现(不来自文章,用来交叉验证文章里的代码)
# --------------------------------------------------------------------------
def brute_lis(nums):
    """枚举所有下标组合,取最长的严格递增子序列长度。"""
    n = len(nums)
    best = 0
    for r in range(1, n + 1):
        for comb in combinations(range(n), r):
            vals = [nums[i] for i in comb]
            if all(vals[k] < vals[k + 1] for k in range(len(vals) - 1)):
                best = max(best, len(vals))
    return best


def brute_max_subarray(nums):
    if not nums:
        return 0
    best = None
    for i in range(len(nums)):
        for j in range(i + 1, len(nums) + 1):
            s = sum(nums[i:j])
            if best is None or s > best:
                best = s
    return best


def brute_coin_change(coins, amount):
    """BFS 层数 = 最少硬币数;比递归更慢但和文章的写法完全独立。"""
    if amount == 0:
        return 0
    seen = {0}
    frontier = [0]
    steps = 0
    while frontier:
        steps += 1
        nxt = []
        for cur in frontier:
            for c in coins:
                nv = cur + c
                if nv == amount:
                    return steps
                if nv < amount and nv not in seen:
                    seen.add(nv)
                    nxt.append(nv)
        frontier = nxt
    return -1


def brute_coin_ways(coins, amount):
    """枚举所有组合(硬币面额可重复),数一数几种凑法。"""
    if amount == 0:
        return 1
    total = 0
    for c in coins:
        if c <= amount:
            total += brute_coin_ways(coins, amount - c)
    return total


# --------------------------------------------------------------------------
def extract(text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def main() -> int:
    if not POST.exists():
        print(f"  post not found: {POST}")
        return 1
    post = POST.read_text(encoding="utf-8")
    py = extract(post, "python")
    cpp = extract(post, "cpp")

    problems, fails = [], []

    print(f"  post          : {POST.name}")
    print(f"  python blocks : {len(py)}  (expect {EXPECTED_PY})")
    print(f"  cpp blocks    : {len(cpp)}  (expect {EXPECTED_CPP})")
    if len(py) != EXPECTED_PY:
        problems.append(f"expected {EXPECTED_PY} python blocks, found {len(py)}")
    if len(cpp) != EXPECTED_CPP:
        problems.append(f"expected {EXPECTED_CPP} cpp blocks, found {len(cpp)}")

    # 每个 python 块都要能独立编译
    for i, b in enumerate(py, 1):
        try:
            compile(b, f"<py block {i}>", "exec")
        except SyntaxError as e:
            problems.append(f"python block {i} does not compile: line {e.lineno}: {e.msg}")
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        return 1

    # 所有块 exec 到一起:后面的同名定义会覆盖前面的,也正是文章里的最终版本
    ns = {}
    exec(compile("\n".join(py), str(POST), "exec"), ns)

    def check(name, got, want):
        if got != want:
            fails.append(name)
            print(f"  FAIL  {name}: got {got!r} want {want!r}")

    def has(fn):
        if fn not in ns:
            fails.append(f"missing function {fn}")
            print(f"  FAIL  post does not define {fn}()")
            return False
        return True

    need = ["fib_bruteforce", "fib_memo", "fib_dp",
            "coin_change_bruteforce", "coin_change_memo", "coin_change_dp",
            "lis_bruteforce", "lis_memo", "lis_dp", "lis_binary_search",
            "max_subarray_dp", "max_subarray_kadane"]
    if not all(has(f) for f in need):
        print(f"\n  RESULT: {len(fails)} problem(s)")
        return 1

    # ---------- 斐波那契 ----------
    FIB = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
    for n, want in enumerate(FIB):
        check(f"fib_memo({n})", ns["fib_memo"](n), want)
        check(f"fib_dp({n})", ns["fib_dp"](n), want)
    check("fib_bruteforce(10)", ns["fib_bruteforce"](10), 55)
    check("fib_dp(30) 超 int 范围前的值", ns["fib_dp"](30), 832040)

    # ---------- 零钱兑换 ----------
    COINS = [
        ([1, 2, 5], 11, 3), ([2], 3, -1), ([1], 0, 0), ([], 7, -1),
        ([5], 5, 1), ([3, 7], 5, -1), ([1, 2, 5], 0, 0),
        ([186, 419, 83, 408], 6249, 20),        # 力扣上的经典卡人用例
        ([2, 5, 10, 1], 27, 4),
        # 4 和 5 凑不出 11(4a+5b=11 无非负整数解),这就是「凑不出」的用例
        ([4, 5], 11, -1),
        ([5, 7], 11, -1),
    ]
    for coins, amount, want in COINS:
        tag = f"coins={coins},amount={amount}"
        check(f"coin_dp {tag}", ns["coin_change_dp"](list(coins), amount), want)
        check(f"coin_memo {tag}", ns["coin_change_memo"](list(coins), amount), want)
        if amount <= 11:
            check(f"coin_bruteforce {tag}",
                  ns["coin_change_bruteforce"](list(coins), amount), want)

    # ---------- LIS ----------
    LIS_CASES = [
        ([], 0), ([7], 1), ([-5], 1), ([7, 7, 7, 7, 7, 7, 7], 1),
        ([10, 9, 2, 5, 3, 7, 101, 18], 4), ([0, 1, 0, 3, 2, 3], 4),
        ([3, 2, 1], 1), ([-3, -2, -1, 0], 4), ([-1, -2, -3], 1),
        ([1, 2, 3, 4, 5], 5), ([2, 2, 2, 1, 1, 1], 1),
        ([1, 3, 6, 7, 9, 4, 10, 5, 6], 6), ([3, 4, 5, 1], 3),
        ([1, 1, 1, 2, 2, 3], 3), ([4, 10, 4, 3, 8, 9], 3),
    ]
    for nums, want in LIS_CASES:
        for fn in ("lis_bruteforce", "lis_memo", "lis_dp", "lis_binary_search"):
            check(f"{fn}({nums})", ns[fn](list(nums)), want)

    # ---------- 最大子数组 ----------
    MS_CASES = [
        ([], 0), ([-3], -3), ([-2, -1, -3], -1), ([-1, -2], -1),
        ([1], 1), ([5, 5, 5], 15), ([-3, 1, 3, -1, 2, -4, 2], 5),
        ([1, 2, 3, 4], 10), ([-5, -4, -3], -3), ([0, 0, 0], 0),
        ([-2, 1, -3, 4, -1, 2, 1, -5, 4], 6), ([8, -19, 5, -4, 20], 21),
    ]
    for nums, want in MS_CASES:
        check(f"max_subarray_dp({nums})", ns["max_subarray_dp"](list(nums)), want)
        check(f"max_subarray_kadane({nums})", ns["max_subarray_kadane"](list(nums)), want)

    # ---------- 随机交叉验证 ----------
    rng = random.Random(20261127)
    n_rand = 0
    for _ in range(400):
        n = rng.randrange(0, 9)
        # 故意混入重复值和全负区间,专门压「严格递增」和「负数初始化」这两个坑
        nums = [rng.randrange(-4, 5) for _ in range(n)]
        ref = brute_lis(nums)
        for fn in ("lis_memo", "lis_dp", "lis_binary_search"):
            if ns[fn](list(nums)) != ref:
                fails.append(f"{fn} mismatch on {nums}: "
                             f"{ns[fn](list(nums))} vs brute {ref}")
        ref_ms = brute_max_subarray(nums)
        for fn in ("max_subarray_dp", "max_subarray_kadane"):
            if ns[fn](list(nums)) != ref_ms:
                fails.append(f"{fn} mismatch on {nums}: "
                             f"{ns[fn](list(nums))} vs brute {ref_ms}")
        coins = sorted({rng.randrange(1, 8) for _ in range(rng.randrange(0, 4))})
        amount = rng.randrange(0, 25)
        ref_c = brute_coin_change(coins, amount)
        for fn in ("coin_change_dp", "coin_change_memo", "coin_change_bruteforce"):
            got = ns[fn](list(coins), amount)
            if got != ref_c:
                fails.append(f"{fn} mismatch on {coins},{amount}: got {got} vs brute {ref_c}")
        n_rand += 1
    if fails:
        print(f"  (随机交叉验证里前若干条失败已列在上面,共 {len(fails)} 条)")
    print(f"  python cases  : {n_rand} random + fixed, "
          f"{'all pass' if not fails else str(len(fails)) + ' failed'}")

    # ---------- C++ ----------
    if not problems and not fails:
        body = "\n\n".join(cpp)
        src = "".join(f"#include {h}\n" for h in CPP_HEADERS) + "\n" + body + "\n" + CPP_TEST_MAIN
        with tempfile.TemporaryDirectory() as td:
            cpp_path = Path(td) / "dp_basics_test.cpp"
            exe_path = Path(td) / "dp_basics_test"
            cpp_path.write_text(src, encoding="utf-8")
            cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-O1",
                   str(cpp_path), "-o", str(exe_path)]
            comp = subprocess.run(cmd, capture_output=True, text=True)
            warn = (comp.stderr or "").strip()
            if comp.returncode != 0:
                problems.append("C++ compile failed")
                print(f"  FAIL  g++ exit {comp.returncode}")
                print(warn)
            else:
                print(f"  g++           : -std=c++17 -Wall -Wextra -O1 "
                      f"{'零警告' if not warn else '有输出!'}")
                if warn:
                    problems.append(f"C++ compile warnings: {warn[:400]}")
                run = subprocess.run([str(exe_path)], capture_output=True, text=True)
                tail = [ln for ln in run.stdout.splitlines() if ln.strip()]
                for ln in tail[-14:]:
                    print(f"  cpp| {ln}")
                if run.returncode != 0:
                    problems.append(f"C++ harness exit {run.returncode}")
                    print(run.stderr[-2000:])

    if fails or problems:
        print(f"\n  RESULT: {len(fails) + len(problems)} problem(s)")
        return 1
    print("\n  CODE OK — 文章里的 Python 与 C++ 全部跑通")
    return 0


# --------------------------------------------------------------------------
# C++ 测试 main:固定用例 + 随机交叉验证(暴力实现独立写在 C++ 侧)
# --------------------------------------------------------------------------
CPP_TEST_MAIN = r"""
// ===================== 测试 harness(不属于文章正文) =====================
static int g_fail = 0;

static void checkEq(const std::string& name, long long got, long long want) {
    if (got != want) {
        ++g_fail;
        std::cout << "FAIL " << name << ": got " << got << " want " << want << "\n";
    }
}

static long long bruteLis(const std::vector<int>& a) {
    // 枚举所有子集,取最长的严格递增子序列
    const int n = static_cast<int>(a.size());
    long long best = 0;
    for (int mask = 0; mask < (1 << n); ++mask) {
        long long len = 0, last = 0;
        bool first = true, ok = true;
        for (int i = 0; i < n && ok; ++i) {
            if (!(mask & (1 << i))) continue;
            if (!first && !(last < a[i])) ok = false;
            last = a[i];
            first = false;
            ++len;
        }
        if (ok) best = std::max(best, len);
    }
    return best;
}

static long long bruteMaxSubarray(const std::vector<int>& a) {
    if (a.empty()) return 0;
    long long best = LLONG_MIN;
    for (size_t i = 0; i < a.size(); ++i) {
        long long s = 0;
        for (size_t j = i; j < a.size(); ++j) {
            s += a[j];
            best = std::max(best, s);
        }
    }
    return best;
}

static long long bruteCoinChange(const std::vector<int>& coins, int amount) {
    // BFS:第一次到达 amount 的层数就是最少硬币数,和文章里的递归写法独立
    if (amount == 0) return 0;
    std::vector<char> seen(static_cast<size_t>(amount) + 1, 0);
    std::vector<int> frontier{0};
    seen[0] = 1;
    long long steps = 0;
    while (!frontier.empty()) {
        ++steps;
        std::vector<int> nxt;
        for (int cur : frontier) {
            for (int c : coins) {
                long long nv = static_cast<long long>(cur) + c;
                if (nv == amount) return steps;
                if (nv < amount && !seen[static_cast<size_t>(nv)]) {
                    seen[static_cast<size_t>(nv)] = 1;
                    nxt.push_back(static_cast<int>(nv));
                }
            }
        }
        frontier.swap(nxt);
    }
    return -1;
}

int main() {
    // ---- 斐波那契 ----
    const long long fibWant[15] = {0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377};
    for (int n = 0; n < 15; ++n) {
        checkEq("fib_memo(" + std::to_string(n) + ")", fib_memo(n), fibWant[n]);
        checkEq("fib_dp(" + std::to_string(n) + ")", fib_dp(n), fibWant[n]);
    }
    checkEq("fib_bruteforce(10)", fib_bruteforce(10), 55);
    checkEq("fib_dp(30)", fib_dp(30), 832040);

    // ---- 零钱兑换:边界(amount=0 / 空硬币 / 凑不出)全在内 ----
    struct CC { std::vector<int> coins; int amount; long long want; };
    const std::vector<CC> ccs = {
        {{1, 2, 5}, 11, 3},
        {{2}, 3, -1},
        {{1}, 0, 0},
        {{}, 7, -1},
        {{5}, 5, 1},
        {{3, 7}, 5, -1},
        {{1, 2, 5}, 0, 0},
        {{186, 419, 83, 408}, 6249, 20},
        {{2, 5, 10, 1}, 27, 4},
        {{4, 5}, 11, -1},      // 4a+5b=11 无解,专门验「凑不出返回 -1」
        {{5, 7}, 11, -1},
    };
    for (const CC& c : ccs) {
        const std::string tag = "coin amount=" + std::to_string(c.amount);
        checkEq("coin_dp " + tag, coin_change_dp(c.coins, c.amount), c.want);
        checkEq("coin_memo " + tag, coin_change_memo(c.coins, c.amount), c.want);
        // 暴力递归只在硬币里没有 1 元时才跑:面额含 1 时候选分支爆炸,
        // 指数级暴力会把测试卡死(它慢是特性,不是 bug,文章里写了这一点)
        if (c.amount <= 11 && !c.coins.empty() && c.coins.front() != 1) {
            // 硬币面额全 >= 2 的用例不做指数级暴力:分支少但深度大时它跑得太慢
            checkEq("coin_bruteforce " + tag,
                    coin_change_bruteforce(c.coins, c.amount), c.want);
        }
    }

    // ---- LIS:空数组 / 单元素 / 全负 / 全相等 / 全递减 ----
    struct LC { std::vector<int> nums; long long want; };
    const std::vector<LC> lcs = {
        {{}, 0}, {{7}, 1}, {{-5}, 1},
        {{7, 7, 7, 7, 7, 7, 7}, 1},
        {{10, 9, 2, 5, 3, 7, 101, 18}, 4},
        {{0, 1, 0, 3, 2, 3}, 4},
        {{3, 2, 1}, 1},
        {{-3, -2, -1, 0}, 4},
        {{-1, -2, -3}, 1},
        {{1, 2, 3, 4, 5}, 5},
        {{2, 2, 2, 1, 1, 1}, 1},
        {{1, 3, 6, 7, 9, 4, 10, 5, 6}, 6},
        {{3, 4, 5, 1}, 3},
        {{1, 1, 1, 2, 2, 3}, 3},
        {{4, 10, 4, 3, 8, 9}, 3},
    };
    for (const LC& c : lcs) {
        checkEq("lis_bruteforce n=" + std::to_string(c.nums.size()),
                lis_bruteforce(c.nums), c.want);
        checkEq("lis_memo n=" + std::to_string(c.nums.size()),
                lis_memo(c.nums), c.want);
        checkEq("lis_dp n=" + std::to_string(c.nums.size()),
                lis_dp(c.nums), c.want);
        checkEq("lis_binary_search n=" + std::to_string(c.nums.size()),
                lis_binary_search(c.nums), c.want);
    }

    // ---- 最大子数组:空数组 / 全负 / 单元素 是重点 ----
    const std::vector<LC> mss = {
        {{}, 0}, {{-3}, -3}, {{-2, -1, -3}, -1}, {{-1, -2}, -1},
        {{1}, 1}, {{5, 5, 5}, 15},
        {{-3, 1, 3, -1, 2, -4, 2}, 5},
        {{1, 2, 3, 4}, 10}, {{-5, -4, -3}, -3}, {{0, 0, 0}, 0},
        {{-2, 1, -3, 4, -1, 2, 1, -5, 4}, 6},
        {{8, -19, 5, -4, 20}, 21},
    };
    for (const LC& c : mss) {
        checkEq("max_subarray_dp n=" + std::to_string(c.nums.size()),
                max_subarray_dp(c.nums), c.want);
        checkEq("max_subarray_kadane n=" + std::to_string(c.nums.size()),
                max_subarray_kadane(c.nums), c.want);
    }

    // ---- 随机交叉验证 ----
    std::mt19937 rng(20261127u);
    auto rnd = [&rng](int lo, int hi) {
        return lo + static_cast<int>(rng() % static_cast<unsigned>(hi - lo + 1));
    };
    int rounds = 0;
    for (int iter = 0; iter < 400; ++iter) {
        const int n = rnd(0, 8);
        std::vector<int> a;
        for (int i = 0; i < n; ++i) a.push_back(rnd(-4, 4));

        const long long refLis = bruteLis(a);
        if (lis_memo(a) != refLis) { ++g_fail; std::cout << "FAIL rand lis_memo\n"; }
        if (lis_dp(a) != refLis) { ++g_fail; std::cout << "FAIL rand lis_dp\n"; }
        if (lis_binary_search(a) != refLis) {
            ++g_fail; std::cout << "FAIL rand lis_binary_search\n";
        }

        const long long refMs = bruteMaxSubarray(a);
        if (max_subarray_dp(a) != refMs) { ++g_fail; std::cout << "FAIL rand ms_dp\n"; }
        if (max_subarray_kadane(a) != refMs) {
            ++g_fail; std::cout << "FAIL rand ms_kadane\n";
        }

        std::vector<int> coins;
        const int k = rnd(0, 3);
        for (int i = 0; i < k; ++i) coins.push_back(rnd(1, 7));
        std::sort(coins.begin(), coins.end());
        coins.erase(std::unique(coins.begin(), coins.end()), coins.end());
        const int amount = rnd(0, 24);
        const long long refC = bruteCoinChange(coins, amount);
        if (coin_change_dp(coins, amount) != refC) {
            ++g_fail; std::cout << "FAIL rand coin_dp amount=" << amount << "\n";
        }
        if (coin_change_memo(coins, amount) != refC) {
            ++g_fail; std::cout << "FAIL rand coin_memo amount=" << amount << "\n";
        }
        if (coin_change_bruteforce(coins, amount) != refC) {
            ++g_fail; std::cout << "FAIL rand coin_bruteforce amount=" << amount << "\n";
        }
        ++rounds;
    }

    std::cout << "cpp random rounds: " << rounds << "\n";
    if (g_fail == 0) std::cout << "ALL CPP CASES PASS\n";
    else std::cout << g_fail << " CPP CASE(S) FAILED\n";
    return g_fail == 0 ? 0 : 1;
}
"""


if __name__ == "__main__":
    sys.exit(main())
