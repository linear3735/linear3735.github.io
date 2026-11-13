#!/usr/bin/env python3
"""Gate for _posts/2026-11-19-monotonic-queue.md.

It does three things:

1. pulls the python/cpp blocks *out of the post itself* (no second copy of the
   code lives here, so the post cannot drift away from what was tested);
2. runs every python block for real against O(n^2) brute-force references, plus
   edge cases (empty, single, k = 1, k = n, all equal, monotone, all negative)
   and the exact numbers that the five SVG figures draw;
3. compiles every cpp block together with a harness under
   -std=c++17 -Wall -Wextra -Werror and runs the same kind of checks there.

The amortised-O(1) claim in the post is not taken on faith: the python side
swaps `deque` for a counting subclass *after* the blocks are loaded, so the
extracted code keeps using its own `deque(...)` calls while we can read off how
many times each element entered and left the queue.

Run:  python3 verify_code.py
"""
import argparse
import collections
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
POST = REPO / "_posts" / "2026-11-19-monotonic-queue.md"
EXPECTED_PY = 6
EXPECTED_CPP = 6
SEED = 20261119


def code_blocks(text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


class Lcg:
    """The same generator on both sides, so the two languages test on the
    same shapes (each language also cross-checks against its own brute force)."""

    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def randint(self, lo, hi):
        return lo + self.next() % (hi - lo + 1)


class Counted(list):
    """Counts [] reads, so `while nums[q[-1]] <= x` can be bounded."""

    def __init__(self, items=()):
        list.__init__(self, items)
        self.reads = 0

    def __getitem__(self, k):
        self.reads += 1
        return list.__getitem__(self, k)


class CountedDeque(collections.deque):
    """Counts the queue operations an element goes through."""

    made = []

    def __init__(self, *a, **kw):
        collections.deque.__init__(self, *a, **kw)
        self.entered = 0     # append / appendleft
        self.crushed = 0     # pop()      —— 从队尾弹出(压扁)
        self.retired = 0     # popleft()  —— 从队头弹出(过期 / 结算)
        CountedDeque.made.append(self)

    def append(self, x):
        self.entered += 1
        return collections.deque.append(self, x)

    def appendleft(self, x):
        self.entered += 1
        return collections.deque.appendleft(self, x)

    def pop(self):
        self.crushed += 1
        return collections.deque.pop(self)

    def popleft(self):
        self.retired += 1
        return collections.deque.popleft(self)

    @classmethod
    def totals(cls):
        e = sum(d.entered for d in cls.made)
        c = sum(d.crushed for d in cls.made)
        r = sum(d.retired for d in cls.made)
        cls.made = []
        return e, c, r


PY_HARNESS = """# ---------------- 暴力参考 ----------------
def brute_window_max(nums, k):
    return [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]


def brute_longest(nums, limit):
    best = 0
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            seg = nums[i:j + 1]
            if max(seg) - min(seg) <= limit:
                best = max(best, j - i + 1)
    return best


def brute_shortest(nums, k):
    n = len(nums)
    best = n + 1
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += nums[j]
            if s >= k:
                best = min(best, j - i + 1)
                break
    return best if best <= n else -1


def brute_circular(nums):
    n = len(nums)
    if n == 0:
        return 0
    best = nums[0]
    for i in range(n):
        s = 0
        for length in range(1, n + 1):
            s += nums[(i + length - 1) % n]
            best = max(best, s)
    return best


def brute_max_result(nums, k):
    n = len(nums)
    if n == 0:
        return 0
    dp = [None] * n
    dp[0] = nums[0]
    for i in range(1, n):
        dp[i] = max(dp[j] for j in range(max(0, i - k), i)) + nums[i]
    return dp[-1]


def kadane_circular(nums):
    \"\"\"独立参考:不跨越接缝 / 跨越接缝(总和 - 最小子数组)两种取最大。\"\"\"
    n = len(nums)
    if n == 0:
        return 0
    best_end = nums[0]
    best = nums[0]
    for x in nums[1:]:
        best_end = max(x, best_end + x)
        best = max(best, best_end)
    worst_end = nums[0]
    worst = nums[0]
    for x in nums[1:]:
        worst_end = min(x, worst_end + x)
        worst = min(worst, worst_end)
    total = sum(nums)
    if worst == total:            # 全是负数:整个数组就是最小子数组,不能再拿 total - worst
        return best
    return max(best, total - worst)


class Lcg:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def randint(self, lo, hi):
        return lo + self.next() % (hi - lo + 1)


def gen_array(rng, n, lo, hi):
    return [rng.randint(lo, hi) for _ in range(n)]


def main():
    fails = 0
    checks = 0

    def check(ok, name):
        nonlocal fails, checks
        checks += 1
        if not ok:
            fails += 1
            print("FAIL", name)

    # 239
    for nums, k, want in (([1, 3, -1, -3, 5, 3, 6, 7], 3, [3, 3, 5, 5, 6, 7]),
                          ([1], 1, [1]),
                          ([7, 2, 4], 3, [7]),
                          ([5, 5, 5, 5], 2, [5, 5, 5]),
                          ([-1, -3, -1], 1, [-1, -3, -1])):
        check(max_sliding_window(nums, k) == want, "239 fixed")
        check(brute_window_max(nums, k) == want, "239 brute fixed")
    rng = Lcg(20261119)
    for _ in range(300):
        n = rng.randint(1, 30)
        k = rng.randint(1, n)
        nums = gen_array(rng, n, -5, 5)
        got = max_sliding_window(nums, k)
        check(got == brute_window_max(nums, k), "239 random %r k=%d" % (nums, k))
    for _ in range(60):
        n = rng.randint(1, 40)
        k = rng.randint(1, n)
        nums = gen_array(rng, n, -1000, 1000)
        check(max_sliding_window(nums, k) == brute_window_max(nums, k), "239 random big")

    # 通用类:对拍朴素模型
    for _ in range(200):
        q = MonotonicQueue()
        model = []
        for _ in range(rng.randint(1, 40)):
            if model and rng.randint(0, 2) == 0:
                want = model.pop(0)
                check(q.pop() == want, "mq pop")
            else:
                x = rng.randint(-9, 9)
                model.append(x)
                q.push(x)
            check(q.size() == len(model), "mq size")
            if model:
                check(q.max() == max(model), "mq max")
                check(q.min() == min(model), "mq min")
    q = MonotonicQueue()
    q.push(3)
    q.push(1)
    check(q.max() == 3 and q.min() == 1 and q.size() == 2, "mq basic")
    check(q.pop() == 3 and q.max() == 1 and q.size() == 1, "mq after pop")
    check(q.pop() == 1 and q.size() == 0, "mq empty")

    # 1438
    for nums, limit, want in (([8, 2, 4, 7], 4, 2), ([10, 1, 2, 4, 7, 2], 5, 4),
                              ([4, 2, 2, 2, 4, 4, 2, 2], 0, 3),
                              ([1, 5, 6, 7, 8, 10, 6, 5, 6], 4, 5), ([3], 0, 1)):
        check(longest_subarray(nums, limit) == want, "1438 fixed %r" % (nums,))
        check(brute_longest(nums, limit) == want, "1438 brute fixed %r" % (nums,))
    for _ in range(200):
        n = rng.randint(1, 20)
        nums = gen_array(rng, n, 0, 6)
        limit = rng.randint(0, 6)
        check(longest_subarray(nums, limit) == brute_longest(nums, limit),
              "1438 random %r limit=%d" % (nums, limit))

    # 862
    for nums, k, want in (([1], 1, 1), ([1, 2], 4, -1), ([2, -1, 2], 3, 3),
                          ([1, 2, 3, 4], 6, 2), ([77, 19, 35, 10, -14], 19, 1)):
        check(shortest_subarray(nums, k) == want, "862 fixed %r" % (nums,))
        check(brute_shortest(nums, k) == want, "862 brute fixed %r" % (nums,))
    for _ in range(200):
        n = rng.randint(1, 18)
        nums = gen_array(rng, n, -5, 10)
        k = rng.randint(1, 20)
        check(shortest_subarray(nums, k) == brute_shortest(nums, k),
              "862 random %r k=%d" % (nums, k))

    # 918
    check(max_subarray_sum_circular([]) == 0, "918 empty")
    for nums, want in (([1, -2, 3, -2], 3), ([5, -3, 5], 10), ([-3, -2, -3], -2),
                       ([1], 1), ([0, 0, 0], 0), ([2, -1, 2], 4)):
        check(max_subarray_sum_circular(nums) == want, "918 fixed %r" % (nums,))
        check(brute_circular(nums) == want, "918 brute fixed %r" % (nums,))
        check(kadane_circular(nums) == want, "918 kadane fixed %r" % (nums,))
    for _ in range(300):
        n = rng.randint(1, 14)
        nums = gen_array(rng, n, -6, 6)
        got = max_subarray_sum_circular(nums)
        check(got == brute_circular(nums), "918 random %r" % (nums,))
        check(got == kadane_circular(nums), "918 kadane %r" % (nums,))

    # 1696
    check(max_result([], 1) == 0, "1696 empty")
    for nums, k, want in (([1, -1, -2, 4, -7, 3], 2, 7),
                          ([10, -5, -2, 4, 0, 3], 3, 17),
                          ([1, -5, -20, 4, -1, 3, -6, -3], 2, 0), ([1], 5, 1)):
        check(max_result(nums, k) == want, "1696 fixed %r" % (nums,))
        check(brute_max_result(nums, k) == want, "1696 brute fixed %r" % (nums,))
    for _ in range(200):
        n = rng.randint(1, 16)
        nums = gen_array(rng, n, -10, 10)
        k = rng.randint(1, n)
        check(max_result(nums, k) == brute_max_result(nums, k),
              "1696 random %r k=%d" % (nums, k))

    return checks, fails


if __name__ == "__main__":
    main()
"""

CPP_PRELUDE = """static void extra_cpp_checks();

#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <deque>
#include <string>
#include <utility>
#include <vector>
"""

CPP_TAIL = """// ---------------- 暴力参考 ----------------
static std::vector<int> brute_window_max(const std::vector<int>& nums, int k) {
    std::vector<int> res;
    int n = static_cast<int>(nums.size());
    for (int i = 0; i + k <= n; ++i) {
        int best = nums[static_cast<std::size_t>(i)];
        for (int j = i; j < i + k; ++j) {
            best = std::max(best, nums[static_cast<std::size_t>(j)]);
        }
        res.push_back(best);
    }
    return res;
}

static int brute_longest(const std::vector<int>& nums, int limit) {
    int n = static_cast<int>(nums.size());
    int best = 0;
    for (int i = 0; i < n; ++i) {
        int lo = nums[static_cast<std::size_t>(i)];
        int hi = lo;
        for (int j = i; j < n; ++j) {
            lo = std::min(lo, nums[static_cast<std::size_t>(j)]);
            hi = std::max(hi, nums[static_cast<std::size_t>(j)]);
            if (hi - lo <= limit) {
                best = std::max(best, j - i + 1);
            }
        }
    }
    return best;
}

static int brute_shortest(const std::vector<int>& nums, int k) {
    int n = static_cast<int>(nums.size());
    int best = n + 1;
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int j = i; j < n; ++j) {
            s += nums[static_cast<std::size_t>(j)];
            if (s >= k) {
                best = std::min(best, j - i + 1);
                break;
            }
        }
    }
    return best <= n ? best : -1;
}

static long long brute_circular(const std::vector<int>& nums) {
    int n = static_cast<int>(nums.size());
    if (n == 0) {
        return 0;
    }
    long long best = nums[0];
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int len = 1; len <= n; ++len) {
            s += nums[static_cast<std::size_t>((i + len - 1) % n)];
            best = std::max(best, s);
        }
    }
    return best;
}

static long long kadane_circular(const std::vector<int>& nums) {
    int n = static_cast<int>(nums.size());
    if (n == 0) {
        return 0;
    }
    long long best_end = nums[0];
    long long best = nums[0];
    long long worst_end = nums[0];
    long long worst = nums[0];
    long long total = nums[0];
    for (int i = 1; i < n; ++i) {
        long long x = nums[static_cast<std::size_t>(i)];
        total += x;
        best_end = std::max(x, best_end + x);
        best = std::max(best, best_end);
        worst_end = std::min(x, worst_end + x);
        worst = std::min(worst, worst_end);
    }
    if (worst == total) {
        return best;
    }
    return std::max(best, total - worst);
}

static long long brute_max_result(const std::vector<int>& nums, int k) {
    int n = static_cast<int>(nums.size());
    if (n == 0) {
        return 0;
    }
    std::vector<long long> dp(static_cast<std::size_t>(n), 0);
    dp[0] = nums[0];
    for (int i = 1; i < n; ++i) {
        long long best = dp[static_cast<std::size_t>(i - 1)];
        for (int j = std::max(0, i - k); j < i; ++j) {
            best = std::max(best, dp[static_cast<std::size_t>(j)]);
        }
        dp[static_cast<std::size_t>(i)] = best + nums[static_cast<std::size_t>(i)];
    }
    return dp[static_cast<std::size_t>(n - 1)];
}

// ---------------- 小工具 ----------------
struct Lcg {
    unsigned long long s;
    explicit Lcg(unsigned long long seed) : s(seed & 0x7FFFFFFFull) {}
    long long next() {
        s = (s * 1103515245ull + 12345ull) & 0x7FFFFFFFull;
        return static_cast<long long>(s);
    }
    int randint(int lo, int hi) {
        return lo + static_cast<int>(next() % (hi - lo + 1));
    }
};

static int fails = 0;
static int checks = 0;

static void check(bool ok, const std::string& name) {
    checks++;
    if (!ok) {
        fails++;
        std::printf("FAIL %s\\n", name.c_str());
    }
}

static void check_vec(const std::string& name, const std::vector<int>& got,
                      const std::vector<int>& want) {
    bool ok = got.size() == want.size();
    for (std::size_t i = 0; ok && i < got.size(); ++i) {
        ok = got[i] == want[i];
    }
    if (!ok) {
        std::printf("FAIL %s got=[", name.c_str());
        for (std::size_t i = 0; i < got.size(); ++i) {
            std::printf("%s%d", i ? "," : "", got[i]);
        }
        std::printf("] want=[");
        for (std::size_t i = 0; i < want.size(); ++i) {
            std::printf("%s%d", i ? "," : "", want[i]);
        }
        std::printf("]\\n");
    }
    checks++;
    if (!ok) {
        fails++;
    }
}

static std::vector<int> gen_array(Lcg& rng, int n, int lo, int hi) {
    std::vector<int> a;
    for (int i = 0; i < n; ++i) {
        a.push_back(rng.randint(lo, hi));
    }
    return a;
}

static std::vector<int> iota_vec(int n) {
    std::vector<int> a;
    for (int i = 0; i < n; ++i) {
        a.push_back(i);
    }
    return a;
}

static std::vector<int> rev_iota_vec(int n) {
    std::vector<int> a;
    for (int i = n; i > 0; --i) {
        a.push_back(i);
    }
    return a;
}

static std::vector<int> filled(int n, int v) {
    return std::vector<int>(static_cast<std::size_t>(n), v);
}

int main() {
    // ---- 239 ----
    {
        std::vector<int> a;
        a.push_back(1); a.push_back(3); a.push_back(-1); a.push_back(-3);
        a.push_back(5); a.push_back(3); a.push_back(6); a.push_back(7);
        std::vector<int> want;
        want.push_back(3); want.push_back(3); want.push_back(5);
        want.push_back(5); want.push_back(6); want.push_back(7);
        check_vec("239 sample", max_sliding_window(a, 3), want);
        check_vec("239 sample brute", brute_window_max(a, 3), want);
        check_vec("239 k=1", max_sliding_window(std::vector<int>{1}, 1),
                  std::vector<int>{1});
        check_vec("239 k=n", max_sliding_window(a, 8), std::vector<int>{7});
        check_vec("239 all equal", max_sliding_window(filled(5, 5), 2),
                  filled(4, 5));
        check_vec("239 increasing", max_sliding_window(iota_vec(6), 1), iota_vec(6));
        check_vec("239 decreasing k=3", max_sliding_window(rev_iota_vec(5), 3),
                  std::vector<int>{5, 4, 3});
        check_vec("239 negatives", max_sliding_window(std::vector<int>{-1, -3, -1}, 1),
                  std::vector<int>{-1, -3, -1});
        Lcg rng(20261119ull);
        for (int t = 0; t < 300; ++t) {
            int n = rng.randint(1, 30);
            int k = rng.randint(1, n);
            std::vector<int> arr = gen_array(rng, n, -5, 5);
            check_vec("239 random", max_sliding_window(arr, k), brute_window_max(arr, k));
        }
        for (int t = 0; t < 60; ++t) {
            int n = rng.randint(1, 40);
            int k = rng.randint(1, n);
            std::vector<int> arr = gen_array(rng, n, -1000, 1000);
            check_vec("239 random big", max_sliding_window(arr, k), brute_window_max(arr, k));
        }
        for (int n = 1; n <= 8; ++n) {
            for (int k = 1; k <= n; ++k) {
                check_vec("239 increasing all k", max_sliding_window(iota_vec(n), k),
                          brute_window_max(iota_vec(n), k));
                check_vec("239 equal all k", max_sliding_window(filled(n, 3), k),
                          brute_window_max(filled(n, 3), k));
            }
        }
    }

    // ---- 通用类:对拍朴素模型 ----
    {
        Lcg rng(20261119ull + 7ull);
        for (int t = 0; t < 400; ++t) {
            MonotonicQueue<int> q;
            std::vector<int> model;
            int ops = rng.randint(1, 40);
            for (int o = 0; o < ops; ++o) {
                if (!model.empty() && rng.randint(0, 2) == 0) {
                    int want = model.front();
                    model.erase(model.begin());
                    check(q.pop() == want, "mq pop");
                } else {
                    int x = rng.randint(-9, 9);
                    model.push_back(x);
                    q.push(x);
                }
                if (q.size() != model.size()) {
                    check(false, "mq size");
                } else {
                    check(true, "mq size");
                }
                if (!model.empty()) {
                    int hi = model[0];
                    int lo = model[0];
                    for (std::size_t i = 1; i < model.size(); ++i) {
                        hi = std::max(hi, model[i]);
                        lo = std::min(lo, model[i]);
                    }
                    check(q.max() == hi, "mq max");
                    check(q.min() == lo, "mq min");
                }
            }
        }
        MonotonicQueue<int> q;
        q.push(3);
        q.push(1);
        check(q.max() == 3 && q.min() == 1 && q.size() == 2, "mq basic");
        check(q.pop() == 3 && q.max() == 1 && q.size() == 1, "mq after pop");
        check(q.pop() == 1 && q.size() == 0, "mq empty");
        MonotonicQueue<int> q2;
        for (int i = 0; i < 1000; ++i) {
            q2.push(i % 7);
        }
        check(q2.size() == 1000 && q2.max() == 6 && q2.min() == 0, "mq big");
        while (q2.size() > 1) {
            q2.pop();
        }
        check(q2.size() == 1 && q2.pop() == 5, "mq drain");  // 最后压进去的是 999 % 7 = 5
    }

    // ---- 1438 ----
    {
        check(longest_subarray(std::vector<int>{8, 2, 4, 7}, 4) == 2, "1438 fixed 1");
        check(longest_subarray(std::vector<int>{10, 1, 2, 4, 7, 2}, 5) == 4, "1438 fixed 2");
        check(longest_subarray(std::vector<int>{4, 2, 2, 2, 4, 4, 2, 2}, 0) == 3,
              "1438 fixed 3");
        check(longest_subarray(std::vector<int>{1, 5, 6, 7, 8, 10, 6, 5, 6}, 4) == 5,
              "1438 fixed 4");
        check(longest_subarray(std::vector<int>{3}, 0) == 1, "1438 single");
        check(longest_subarray(filled(9, 2), 0) == 9, "1438 all equal");
        check(brute_longest(filled(9, 2), 0) == 9, "1438 all equal brute");
        check(longest_subarray(iota_vec(7), 0) == 1, "1438 increasing");
        Lcg rng(20261119ull + 11ull);
        for (int t = 0; t < 300; ++t) {
            int n = rng.randint(1, 20);
            std::vector<int> arr = gen_array(rng, n, 0, 6);
            int limit = rng.randint(0, 6);
            check(longest_subarray(arr, limit) == brute_longest(arr, limit), "1438 random");
        }
    }

    // ---- 862 ----
    {
        check(shortest_subarray(std::vector<int>{1}, 1) == 1, "862 fixed 1");
        check(shortest_subarray(std::vector<int>{1, 2}, 4) == -1, "862 fixed 2");
        check(shortest_subarray(std::vector<int>{2, -1, 2}, 3) == 3, "862 fixed 3");
        check(shortest_subarray(std::vector<int>{1, 2, 3, 4}, 6) == 2, "862 fixed 4");
        check(shortest_subarray(std::vector<int>{77, 19, 35, 10, -14}, 19) == 1,
              "862 fixed 5");
        check(shortest_subarray(iota_vec(5), 1000) == -1, "862 impossible");
        check(shortest_subarray(filled(6, 1), 3) == 3, "862 all equal");
        check(brute_shortest(filled(6, 1), 3) == 3, "862 all equal brute");
        Lcg rng(20261119ull + 13ull);
        for (int t = 0; t < 300; ++t) {
            int n = rng.randint(1, 18);
            std::vector<int> arr = gen_array(rng, n, -5, 10);
            int k = rng.randint(1, 20);
            check(shortest_subarray(arr, k) == brute_shortest(arr, k), "862 random");
        }
    }

    // ---- 918 ----
    {
        check(max_subarray_sum_circular(std::vector<int>{}) == 0, "918 empty");
        check(max_subarray_sum_circular(std::vector<int>{1, -2, 3, -2}) == 3, "918 fixed 1");
        check(max_subarray_sum_circular(std::vector<int>{5, -3, 5}) == 10, "918 fixed 2");
        check(max_subarray_sum_circular(std::vector<int>{-3, -2, -3}) == -2, "918 fixed 3");
        check(max_subarray_sum_circular(std::vector<int>{1}) == 1, "918 single");
        check(max_subarray_sum_circular(std::vector<int>{0, 0, 0}) == 0, "918 zeros");
        check(max_subarray_sum_circular(std::vector<int>{2, -1, 2}) == 4, "918 fixed 4");
        check(brute_circular(std::vector<int>{2, -1, 2}) == 4, "918 brute fixed 4");
        check(kadane_circular(std::vector<int>{2, -1, 2}) == 4, "918 kadane fixed 4");
        check(max_subarray_sum_circular(filled(6, -4)) == -4, "918 all negative equal");
        check(brute_circular(filled(6, -4)) == -4, "918 all negative equal brute");
        Lcg rng(20261119ull + 17ull);
        for (int t = 0; t < 400; ++t) {
            int n = rng.randint(1, 14);
            std::vector<int> arr = gen_array(rng, n, -6, 6);
            long long got = max_subarray_sum_circular(arr);
            check(got == brute_circular(arr), "918 random brute");
            check(got == kadane_circular(arr), "918 random kadane");
        }
    }

    // ---- 1696 ----
    {
        check(max_result(std::vector<int>{}, 1) == 0, "1696 empty");
        check(max_result(std::vector<int>{1, -1, -2, 4, -7, 3}, 2) == 7, "1696 fixed 1");
        check(max_result(std::vector<int>{10, -5, -2, 4, 0, 3}, 3) == 17, "1696 fixed 2");
        check(max_result(std::vector<int>{1, -5, -20, 4, -1, 3, -6, -3}, 2) == 0,
              "1696 fixed 3");
        check(max_result(std::vector<int>{1}, 5) == 1, "1696 single");
        check(max_result(filled(5, 3), 2) == 15, "1696 all equal");
        check(brute_max_result(filled(5, 3), 2) == 15, "1696 all equal brute");
        check(max_result(iota_vec(6), 1) == 15, "1696 k=1");
        check(brute_max_result(iota_vec(6), 1) == 15, "1696 k=1 brute");
        Lcg rng(20261119ull + 19ull);
        for (int t = 0; t < 300; ++t) {
            int n = rng.randint(1, 16);
            std::vector<int> arr = gen_array(rng, n, -10, 10);
            int k = rng.randint(1, n);
            check(max_result(arr, k) == brute_max_result(arr, k), "1696 random");
        }
        for (int n = 1; n <= 8; ++n) {
            for (int k = 1; k <= n; ++k) {
                check(max_result(iota_vec(n), k) == brute_max_result(iota_vec(n), k),
                      "1696 increasing all k");
                check(max_result(filled(n, 2), k) == brute_max_result(filled(n, 2), k),
                      "1696 equal all k");
            }
        }
    }

    extra_cpp_checks();
    std::printf("CPP CHECKS %d FAILS %d\\n", checks, fails);
    return fails == 0 ? 0 : 1;
}

// ---------------- 图里的数字与边界(与 python 侧一一对应) ----------------
static void extra_cpp_checks() {
    std::vector<int> nums8{1, 3, -1, -3, 5, 3, 6, 7};
    check_vec("fig02 sample", max_sliding_window(nums8, 3),
              std::vector<int>{3, 3, 5, 5, 6, 7});
    check_vec("fig02 sample == brute", max_sliding_window(nums8, 3),
              brute_window_max(nums8, 3));
    check_vec("239 expiry fires", max_sliding_window(std::vector<int>{3, 1, 2}, 2),
              std::vector<int>{3, 2});
    check_vec("fig03 index version",
              max_sliding_window(std::vector<int>{5, 5, 3}, 2),
              brute_window_max(std::vector<int>{5, 5, 3}, 2));

    MonotonicQueue<int> q4;
    q4.push(3);
    q4.push(1);
    q4.push(4);
    check(q4.size() == 3 && q4.max() == 4 && q4.min() == 1, "fig04 after push");
    check(q4.pop() == 3, "fig04 pop returns the oldest");
    check(q4.size() == 2 && q4.max() == 4 && q4.min() == 1, "fig04 after pop");

    std::vector<int> nums3{2, -1, 2};
    std::vector<long long> pre(4, 0);
    for (int i = 0; i < 3; ++i) {
        pre[static_cast<std::size_t>(i) + 1] =
            pre[static_cast<std::size_t>(i)] + nums3[static_cast<std::size_t>(i)];
    }
    check(shortest_subarray(nums3, 3) == 3, "fig05 answer is 3");
    check(pre[3] - pre[0] == 3 && pre[1] >= pre[2], "fig05 prefix numbers");

    check(max_sliding_window(std::vector<int>{}, 1).empty(), "239 empty");
    check_vec("239 single k=1", max_sliding_window(std::vector<int>{9}, 1),
              std::vector<int>{9});
    check(max_sliding_window(std::vector<int>{1, 2, 3, 4, 5}, 5) ==
              std::vector<int>{5}, "239 k=n");
    check(max_sliding_window(std::vector<int>{5, 5, 5, 5, 5}, 3) ==
              std::vector<int>({5, 5, 5}), "239 all equal");
    check(longest_subarray(std::vector<int>{}, 3) == 0, "1438 empty");
    check(longest_subarray(std::vector<int>{2, 2, 2, 2, 2, 2}, 0) == 6,
          "1438 all equal limit=0");
    check(shortest_subarray(std::vector<int>{}, 1) == -1, "862 empty");
    check(shortest_subarray(std::vector<int>{-1, -2, -3}, 1) == -1,
          "862 all negative");
    check(max_subarray_sum_circular(std::vector<int>{}) == 0, "918 empty");
    check(max_subarray_sum_circular(std::vector<int>{-3, -2, -3}) == -2,
          "918 all negative");
    check(max_result(std::vector<int>{}, 1) == 0, "1696 empty");
    check(max_result(std::vector<int>{1, 2, 3, 4}, 4) == 10, "1696 k=n");
}
"""


def load_python(text):
    """Exec the post's python blocks, then swap in the counting deque."""
    ns = {"__name__": "post_blocks"}
    for block in code_blocks(text, "python"):
        exec(compile(block, "<post:python>", "exec"), ns)
    for name in ("max_sliding_window", "MonotonicQueue", "longest_subarray",
                 "shortest_subarray", "max_subarray_sum_circular", "max_result"):
        assert name in ns, "post is missing the python block defining %s" % name
    ns["deque"] = CountedDeque          # 正文里的 deque(...) 之后就走计数版
    return ns


def value_queue_demo(nums, k):
    """第 3.1 节那个存值版本:pop 只知道值,不知道位置。"""
    q = []
    out = []
    for i, x in enumerate(nums):
        while q and q[-1] <= x:
            q.pop()
        q.append(x)
        if i >= k and q and q[0] == nums[i - k]:
            q.pop(0)
        if i >= k - 1:
            out.append(q[0])
    return out


def extra_python_checks(ns):
    """Edge cases, the numbers drawn in the figures, and the O(n) witness."""
    checks = 0
    fails = 0
    notes = []

    def check(ok, name):
        nonlocal checks, fails
        checks += 1
        if not ok:
            fails += 1
            print("FAIL %s" % name)

    msw = ns["max_sliding_window"]
    mq = ns["MonotonicQueue"]
    longest = ns["longest_subarray"]
    shortest = ns["shortest_subarray"]
    circular = ns["max_subarray_sum_circular"]
    jump = ns["max_result"]
    brute_window_max = ns["brute_window_max"]
    brute_shortest = ns["brute_shortest"]
    gen_array = ns["gen_array"]

    # ---------- 边界 ----------
    check(msw([], 1) == [], "239 empty")
    check(msw([9], 1) == [9], "239 single k=1")
    check(msw([3, 1, 2], 2) == [3, 2], "239 过期那次真的发生了")
    check(msw([1, 2, 3, 4, 5], 5) == [5], "239 k=n")
    check(msw([5, 5, 5, 5, 5], 3) == [5, 5, 5], "239 all equal")
    check(msw([1, 2, 3, 4, 5], 1) == [1, 2, 3, 4, 5], "239 increasing k=1")
    check(msw([5, 4, 3, 2, 1], 3) == [5, 4, 3], "239 strictly decreasing")
    check(longest([], 3) == 0, "1438 empty")
    check(longest([7], 0) == 1, "1438 single")
    check(longest([2, 2, 2, 2, 2, 2], 0) == 6, "1438 all equal limit=0")
    check(longest([1, 2, 3, 4, 5], 0) == 1, "1438 increasing limit=0")
    check(shortest([], 1) == -1, "862 empty")
    check(shortest([3], 3) == 1, "862 single")
    check(shortest([1, 1, 1, 1], 4) == 4, "862 k=n 边界")
    check(shortest([-1, -2, -3], 1) == -1, "862 all negative")
    check(shortest([4, 4, 4], 4) == 1, "862 all equal")
    check(circular([]) == 0, "918 empty")
    check(circular([-5]) == -5, "918 single negative")
    check(circular([-3, -2, -3]) == -2, "918 all negative")
    check(circular([7, 7, 7]) == 21, "918 all equal")
    check(jump([], 1) == 0, "1696 empty")
    check(jump([4], 3) == 4, "1696 single")
    check(jump([1, 2, 3, 4], 4) == 10, "1696 k=n")
    check(jump([5, 5, 5, 5], 2) == 20, "1696 all equal")

    # ---------- 图 02:样例走表 ----------
    nums8 = [1, 3, -1, -3, 5, 3, 6, 7]
    rows = []
    q = collections.deque()
    for i, x in enumerate(nums8):
        crushed = []
        while q and nums8[q[-1]] <= x:
            crushed.append(q.pop())
        q.append(i)
        if q[0] <= i - 3:
            q.popleft()
        rows.append((i, crushed, [(j, nums8[j]) for j in q]))
    want_rows = [
        (0, [], [(0, 1)]),
        (1, [0], [(1, 3)]),
        (2, [], [(1, 3), (2, -1)]),
        (3, [], [(1, 3), (2, -1), (3, -3)]),
        (4, [3, 2, 1], [(4, 5)]),
        (5, [], [(4, 5), (5, 3)]),
        (6, [5, 4], [(6, 6)]),
        (7, [6], [(7, 7)]),
    ]
    check(rows == want_rows, "fig02 走表与图里的 8 行一致")
    check(msw(Counted(nums8), 3) == [3, 3, 5, 5, 6, 7], "fig02 样例输出")
    check(brute_window_max(nums8, 3) == [3, 3, 5, 5, 6, 7], "fig02 样例暴力")

    # ---------- 图 03:存值会认错人 ----------
    check(value_queue_demo([5, 5, 3], 2) == [5, 3], "fig03 存值版本算错")
    check(msw([5, 5, 3], 2) == [5, 5], "fig03 存下标版本算对")
    check(brute_window_max([5, 5, 3], 2) == [5, 5], "fig03 暴力对照")

    # ---------- 图 04:通用类的状态 ----------
    q4 = mq()
    q4.push(3)
    q4.push(1)
    q4.push(4)
    check(q4.size() == 3 and q4.max() == 4 and q4.min() == 1, "fig04 push 之后")
    check(list(q4._data) == [(0, 3), (1, 1), (2, 4)], "fig04 _data 三格")
    check(list(q4._max) == [(2, 4)], "fig04 _max 一格")
    check(list(q4._min) == [(1, 1), (2, 4)], "fig04 _min 两格")
    check(q4.pop() == 3, "fig04 pop 返回最早进来的 3")
    check(q4.size() == 2 and q4.max() == 4 and q4.min() == 1, "fig04 pop 之后")
    check(list(q4._max) == [(2, 4)] and list(q4._min) == [(1, 1), (2, 4)],
          "fig04 被 pop 的不在最值队头,两副队列不动")

    # ---------- 图 05:862 的数字 ----------
    nums3, K = [2, -1, 2], 3
    pre = [0]
    for x in nums3:
        pre.append(pre[-1] + x)
    check(pre == [0, 2, 1, 3], "fig05 前缀和是 [0, 2, 1, 3]")
    check(pre[3] - pre[0] == 3 >= K, "fig05 pre[3] - pre[0] = 3 >= K")
    check(pre[1] >= pre[2], "fig05 下标 1 被压扁(pre[1] >= pre[2])")
    check(shortest(nums3, K) == 3, "fig05 答案是 3")
    check(brute_shortest(nums3, K) == 3, "fig05 暴力也是 3")

    # ---------- O(n) 的账 ----------
    rng = Lcg(SEED + 5)
    worst_reads = 0.0
    for _ in range(200):
        n = rng.randint(1, 40)
        nums = Counted(gen_array(rng, n, -6, 6))
        k = rng.randint(1, n)

        CountedDeque.made = []
        msw(nums, k)
        entered, crushed, retired = CountedDeque.totals()
        check(entered == n, "239 每个元素恰好入队一次")
        check(crushed <= n and retired <= n, "239 弹出次数不超过 n")
        check(nums.reads <= 5 * n, "239 数组读取 <= 5n")
        worst_reads = max(worst_reads, nums.reads / float(n))

        CountedDeque.made = []
        shortest(nums, rng.randint(-20, 20))
        entered, crushed, retired = CountedDeque.totals()
        check(entered <= n + 1, "862 入队 <= n + 1")
        check(crushed <= entered and retired <= entered, "862 弹出 <= 入队")

        CountedDeque.made = []
        circular(nums)
        entered, crushed, retired = CountedDeque.totals()
        check(entered <= 2 * n + 1, "918 入队 <= 2n + 1")
        check(crushed <= entered and retired <= entered, "918 弹出 <= 入队")

        CountedDeque.made = []
        jump(nums, k)
        entered, crushed, retired = CountedDeque.totals()
        check(entered == n - 1, "1696 构造函数放进下标 0,其余 n-1 次入队")
        check(crushed <= n and retired <= n, "1696 弹出次数不超过 n")

        limit = rng.randint(0, 6)
        CountedDeque.made = []
        longest(nums, limit)
        entered, crushed, retired = CountedDeque.totals()
        check(entered == 3 * n, "1438 每次 push 让三副队列各入队一次")
        check(crushed <= 2 * n, "1438 被压扁的次数 <= 2n(max/min 各一副)")
        check(retired <= 3 * n, "1438 队头弹出 <= 3n")

        # 用类自己走一遍 1438 的调用序列,验证队列的账目能对上
        CountedDeque.made = []
        qq = mq()
        popped = 0
        for x in nums:
            qq.push(x)
            while qq.max() - qq.min() > limit:
                qq.pop()
                popped += 1
            check(qq.max() - qq.min() <= limit, "1438 窗口此刻一定合法")
        entered, crushed, retired = CountedDeque.totals()
        check(popped + qq.size() == n, "1438 总账:pop 掉的 + 还在队列里的 = n")
        check(entered == 3 * n and crushed <= 2 * n, "1438 计数不变量")
        check(len(qq._data) == qq.size() and len(qq._max) <= qq.size()
              and len(qq._min) <= qq.size(), "1438 三副队列的长度关系")

    notes.append("op witness      : 239 数组读取 <= 5n(实测最大 %.2fn);239 入队 = n "
                 "且弹出 <= n;1696 入队 = n-1(下标 0 由构造函数放进队列);"
                 "918 入队 <= 2n+1" % worst_reads)
    return checks, fails, notes


def run_cpp(blocks):
    exe_dir = HERE / "build"
    exe_dir.mkdir(exist_ok=True)
    src = exe_dir / "cpp_test.cpp"
    exe = exe_dir / "cpp_test"
    src.write_text(CPP_PRELUDE + "\n" + "\n".join(blocks) + "\n" + CPP_TAIL,
                   encoding="utf-8")
    flags = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1"]
    cp = subprocess.run(["g++"] + flags + [str(src), "-o", str(exe)],
                        capture_output=True, text=True)
    if cp.returncode != 0:
        print(cp.stdout)
        print(cp.stderr)
        raise SystemExit("g++ failed (rc=%d)" % cp.returncode)
    stderr = cp.stderr.strip()
    warnings = stderr.count("warning:")
    if stderr or warnings:
        print(stderr)
        raise SystemExit("g++ was not silent (%d warnings)" % warnings)
    rp = subprocess.run([str(exe)], capture_output=True, text=True)
    lines = [ln for ln in rp.stdout.strip().splitlines() if ln.strip()]
    summary = lines[-1] if lines else ""
    bad = [ln for ln in lines[:-1] if ln.startswith("FAIL")]
    if bad:
        print("\n".join(bad[:20]))
    return flags, stderr, summary, rp.returncode, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", default=str(POST))
    args = ap.parse_args()
    post = Path(args.post)
    text = post.read_text(encoding="utf-8")

    py_blocks = code_blocks(text, "python")
    cpp_blocks = code_blocks(text, "cpp")
    print("post            : %s" % post.relative_to(REPO))
    print("python blocks   : %d (expected %d)" % (len(py_blocks), EXPECTED_PY))
    print("cpp blocks      : %d (expected %d)" % (len(cpp_blocks), EXPECTED_CPP))
    if len(py_blocks) != EXPECTED_PY or len(cpp_blocks) != EXPECTED_CPP:
        raise SystemExit("block count changed — update EXPECTED_PY/CPP")

    ns = load_python(text)
    exec(compile(PY_HARNESS, "<harness:python>", "exec"), ns)
    h_checks, h_fails = ns["main"]()

    e_checks, e_fails, notes = extra_python_checks(ns)
    py_checks = h_checks + e_checks
    py_fails = h_fails + e_fails
    print("python checks   : %d, failures %d" % (py_checks, py_fails))
    for n in notes:
        print(n)

    if shutil.which("g++") is None:
        print("g++ not found — cpp side skipped")
        return 1 if py_fails else 0
    flags, stderr, summary, rc, bad = run_cpp(cpp_blocks)
    print("g++ flags       : %s  (stderr %s, %d warnings)"
          % (" ".join(flags), "empty" if not stderr else repr(stderr),
             stderr.count("warning:")))
    print("cpp harness     : %s" % summary)
    m = re.match(r"CPP CHECKS (\d+) FAILS (\d+)$", summary)
    cpp_checks, cpp_fails = (int(m.group(1)), int(m.group(2))) if m else (0, 1)

    total_fails = py_fails + cpp_fails
    if total_fails or bad or rc != 0:
        print("\nCODE FAILED — %d python + %d cpp failures" % (py_fails, cpp_fails))
        return 1
    print("\nCODE OK — %d python + %d cpp blocks, %d python assertions + "
          "%d cpp assertions, 0 failures"
          % (len(py_blocks), len(cpp_blocks), py_checks, cpp_checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
