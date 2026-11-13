#!/usr/bin/env python3
"""代码门:单调栈(2026-11-18-monotonic-stack.md)。

从正文里抽代码块(不另存副本),然后把每道题和暴力 O(n^2) 参考实现对拍:
  * next_greater_element / next_greater_element_backward  -> 暴力下一个更大
  * next_greater_element_i (496)                          -> 暴力查表
  * next_smaller_element                                  -> 暴力下一个更小
  * next_greater_elements (503, 环形)                      -> 暴力环形扫描
  * bar_spans + largest_rectangle_area (84)               -> 暴力枚举行;另外校验
        「最左最矮柱」区间不变量 + 区间个数 (j-L)*(R-j) + 每根柱子恰好结算一次
  * largest_rectangle_area_fast (84 哨兵版)                -> 和上一版逐例一致
  * sum_of_subarray_mins (907)                            -> 暴力逐个区间取最小值求和
  * trap (42)                                             -> 暴力按位置算 min(l_max, r_max)

边界:空数组、单元素、全相等、严格递增、严格递减、全 0、含大量重复值。
C++ 侧用同一套用例,并且 g++ -std=c++17 -Wall -Wextra -Werror 零警告。
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POST = os.path.normpath(os.path.join(HERE, "..", "..", "..", "_posts",
                                     "2026-11-18-monotonic-stack.md"))

EXPECTED_PY = 9
EXPECTED_CPP = 9
SEED = 20261118
MOD = 10 ** 9 + 7


# ---------------------------------------------------------------------------
# 抽取
# ---------------------------------------------------------------------------

def extract(text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def load_blocks():
    with open(POST, encoding="utf-8") as fh:
        text = fh.read()
    py = extract(text, "python")
    cpp = extract(text, "cpp")
    return py, cpp


# ---------------------------------------------------------------------------
# 确定性随机数:Python 与 C++ 用同一套 LCG,保证两边用例完全相同
# ---------------------------------------------------------------------------

class Lcg(object):
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def randint(self, lo, hi):
        return lo + self.next() % (hi - lo + 1)

    def shuffled(self, items):
        out = list(items)
        for i in range(len(out) - 1, 0, -1):
            j = self.randint(0, i)
            out[i], out[j] = out[j], out[i]
        return out


def gen_array(rng, n, lo, hi):
    return [rng.randint(lo, hi) for _ in range(n)]


# ---------------------------------------------------------------------------
# 暴力参考实现
# ---------------------------------------------------------------------------

def brute_nge(a):
    """每个元素右边第一个比它大的值,没有填 -1。"""
    res = []
    for i in range(len(a)):
        got = -1
        for j in range(i + 1, len(a)):
            if a[j] > a[i]:
                got = a[j]
                break
        res.append(got)
    return res


def brute_nse(a):
    res = []
    for i in range(len(a)):
        got = -1
        for j in range(i + 1, len(a)):
            if a[j] < a[i]:
                got = a[j]
                break
        res.append(got)
    return res


def brute_nge_circular(a):
    n = len(a)
    res = []
    for i in range(n):
        got = -1
        for step in range(1, n):
            if a[(i + step) % n] > a[i]:
                got = a[(i + step) % n]
                break
        res.append(got)
    return res


def brute_nge_i(nums1, nums2):
    out = []
    for v in nums1:
        pos = nums2.index(v)
        got = -1
        for j in range(pos + 1, len(nums2)):
            if nums2[j] > v:
                got = nums2[j]
                break
        out.append(got)
    return out


def brute_max_rect(h):
    """枚举所有子区间:面积 = 区间最小值 × 区间长度。O(n^2)。"""
    best = 0
    n = len(h)
    for l in range(n):
        cur = h[l]
        for r in range(l, n):
            cur = min(cur, h[r])
            best = max(best, cur * (r - l + 1))
    return best


def brute_sum_mins(a):
    total = 0
    n = len(a)
    for l in range(n):
        cur = a[l]
        for r in range(l, n):
            cur = min(cur, a[r])
            total += cur
    return total % MOD


def brute_trap(h):
    """按位置算:min(左边最高, 右边最高) - height[i]。"""
    n = len(h)
    total = 0
    for i in range(n):
        lmax = max(h[:i + 1]) if i >= 0 else 0
        rmax = max(h[i:]) if i < n else 0
        total += min(lmax, rmax) - h[i]
    return total


def brute_nge_ge(a):
    """下一个「更大或相等」。"""
    res = []
    for i in range(len(a)):
        got = -1
        for j in range(i + 1, len(a)):
            if a[j] >= a[i]:
                got = a[j]
                break
        res.append(got)
    return res


def brute_nse_le(a):
    """下一个「更小或相等」。"""
    res = []
    for i in range(len(a)):
        got = -1
        for j in range(i + 1, len(a)):
            if a[j] <= a[i]:
                got = a[j]
                break
        res.append(got)
    return res


def count_leftmost_min(h, j):
    """暴力数:有多少个子区间以 h[j] 为「最左的最小值」。"""
    n = len(h)
    cnt = 0
    for l in range(j + 1):
        for r in range(j, n):
            seg = h[l:r + 1]
            m = min(seg)
            if m == h[j] and seg.index(m) == j - l:
                cnt += 1
    return cnt


# ---------------------------------------------------------------------------
# Python 侧
# ---------------------------------------------------------------------------

class Counted(list):
    """list 子类,只统计读取次数:用来给「每个元素只进出一趟」的 O(n) 作证。"""

    def __init__(self, data=()):
        super().__init__(data)
        self.reads = 0

    def __getitem__(self, key):
        self.reads += 1
        return super().__getitem__(key)


def run_python(blocks):
    checks = [0]
    fails = []

    def check(ok, what):
        checks[0] += 1
        if not ok and len(fails) < 25:
            fails.append(what)

    for i, b in enumerate(blocks):
        compile(b, "<post-block-%d>" % (i + 1), "exec")
    ns = {}
    for i, b in enumerate(blocks):
        exec(compile(b, "<post-block-%d>" % (i + 1), "exec"), ns)

    nge = ns["next_greater_element"]
    nge_back = ns["next_greater_element_backward"]
    nge_i = ns["next_greater_element_i"]
    nse = ns["next_smaller_element"]
    nge_circ = ns["next_greater_elements"]
    bar_spans = ns["bar_spans"]
    max_rect = ns["largest_rectangle_area"]
    max_rect_fast = ns["largest_rectangle_area_fast"]
    sum_mins = ns["sum_of_subarray_mins"]
    trap = ns["trap"]

    # ---- 边界用例(手写答案,便于报告里直接引用) --------------------------
    fixed = [
        ([], []),
        ([5], [-1]),
        ([0], [-1]),
        ([1, 3, 2], [3, -1, -1]),
        ([3, 1, 2], [-1, 2, -1]),
        ([2, 2, 2], [-1, -1, -1]),
        ([3, 2, 1], [-1, -1, -1]),
        ([1, 2, 3], [2, 3, -1]),
        ([2, 1, 2, 4, 3], [4, 2, 4, -1, -1]),
        ([5, 4, 3, 2, 1], [-1, -1, -1, -1, -1]),
        ([1, 1, 2, 1], [2, 2, -1, -1]),
        ([0, 0, 0, 1], [1, 1, 1, -1]),
    ]
    for arr, want in fixed:
        check(nge(list(arr)) == want, "next_greater_element(%r) got=%r want=%r"
              % (arr, nge(list(arr)), want))

    # ---- 下一个更大:正着扫 / 倒着扫 / 暴力三方对拍 ----------------------
    cases = [list(a) for a, _ in fixed]
    rng = Lcg(SEED)
    for _ in range(200):
        cases.append(gen_array(rng, rng.randint(0, 30), 0, 4))      # 大量重复值
    for _ in range(100):
        cases.append(gen_array(rng, rng.randint(0, 40), 0, 1000))
    for n in (0, 1, 2, 3, 8, 33):
        cases.append(list(range(n)))                                # 严格递增
        cases.append(list(range(n, 0, -1)))                         # 严格递减
        cases.append([7] * n)                                       # 全相等
    for arr in cases:
        want = brute_nge(arr)
        check(nge(list(arr)) == want, "nge(%r) got=%r want=%r" % (arr, nge(list(arr)), want))
        check(nge_back(list(arr)) == want, "nge_backward(%r) got=%r want=%r"
              % (arr, nge_back(list(arr)), want))

    # ---- 读取次数上界:while 里的比较是常数摊还的 -------------------------
    # 数一遍 nums 的读取:while 条件每次读 2 个元素(栈顶 + 当前),条件判断最多
    # n + 出栈次数 <= 2n 次 -> 4n;每次弹出写答案时再读一次 nums[i] -> <= n。
    # 合计 <= 5n,这就是「每个元素只进出一趟」的 O(n) 的直接证据。
    for n in (1, 2, 7, 50, 200, 501):
        for arr in (list(range(n)), list(range(n, 0, -1)), [3] * n,
                    gen_array(Lcg(SEED + n), n, 0, 5)):
            counted = Counted(arr)
            nge(counted)
            check(counted.reads <= 5 * n,
                  "reads bound n=%d reads=%d > 5n (%r...)" % (n, counted.reads, arr[:6]))

    # ---- 496 ------------------------------------------------------------
    rng = Lcg(SEED + 1)
    check(nge_i([], [1, 2, 3]) == [], "496 empty nums1")
    check(nge_i([2, 4], [1, 2, 3, 4]) == [3, -1], "496 basic")
    for _ in range(150):
        m = rng.randint(1, 20)
        pool = rng.shuffled(range(0, 60))[:m]
        nums2 = list(pool)
        k = rng.randint(0, m)
        nums1 = rng.shuffled(nums2)[:k]
        want = brute_nge_i(list(nums1), list(nums2))
        got = nge_i(list(nums1), list(nums2))
        check(got == want, "496 nums1=%r nums2=%r got=%r want=%r"
              % (nums1, nums2, got, want))
    for n in (1, 5, 30):
        nums2 = list(range(n))
        check(nge_i(list(nums2), list(nums2)) == brute_nge(list(nums2)),
              "496 nums1 == nums2 n=%d" % n)

    # ---- 下一个更小 ------------------------------------------------------
    for arr in ([], [5], [3, 1, 2], [1, 8, 3, 2], [1, 1, 1], [1, 2, 3], [3, 2, 1],
                [4, 2, 0, 3, 2, 5], [2, 1, 2, 4, 3]):
        check(nse(list(arr)) == brute_nse(list(arr)),
              "next_smaller_element(%r) got=%r want=%r"
              % (arr, nse(list(arr)), brute_nse(list(arr))))
    rng = Lcg(SEED + 2)
    for _ in range(150):
        arr = gen_array(rng, rng.randint(0, 30), 0, 5)
        check(nse(list(arr)) == brute_nse(arr),
              "next_smaller_element(%r)" % (arr,))

    # ---- 503 环形 --------------------------------------------------------
    for arr, want in (([], []),
                      ([5], [-1]),
                      ([1, 2, 3], [2, 3, -1]),
                      ([3, 1, 2], [-1, 2, 3]),
                      ([2, 1, 2, 4, 3], [4, 2, 4, -1, 4]),
                      ([1, 1, 1], [-1, -1, -1]),
                      ([5, 4, 3, 2, 1], [-1, 5, 5, 5, 5]),
                      ([0, 0, 1], [1, 1, -1])):
        check(nge_circ(list(arr)) == want, "503(%r) got=%r want=%r"
              % (arr, nge_circ(list(arr)), want))
    rng = Lcg(SEED + 3)
    for _ in range(200):
        arr = gen_array(rng, rng.randint(0, 25), 0, 4)
        check(nge_circ(list(arr)) == brute_nge_circular(arr),
              "503(%r) got=%r want=%r"
              % (arr, nge_circ(list(arr)), brute_nge_circular(arr)))
    for n in (1, 2, 6, 25):
        check(nge_circ(list(range(n))) == brute_nge_circular(list(range(n))),
              "503 increasing n=%d" % n)
        check(nge_circ(list(range(n, 0, -1))) == brute_nge_circular(list(range(n, 0, -1))),
              "503 decreasing n=%d" % n)

    # ---- 84:区间不变量 + 最大矩形 + 哨兵版一致 ---------------------------
    for arr, want in (([], 0), ([1], 1), ([0], 0), ([2, 1, 2], 3), ([2, 2, 2], 6),
                      ([5, 5, 5], 15), ([1, 2, 3], 4), ([3, 2, 1], 4),
                      ([1, 2, 3, 4, 5], 9), ([5, 4, 3, 2, 1], 9),
                      ([2, 1, 5, 6, 2, 3], 10), ([0, 0, 0], 0),
                      ([4, 2, 0, 3, 2, 5], 6)):
        got = max_rect(list(arr))
        check(got == want, "84(%r) got=%r want=%r" % (arr, got, want))
        check(max_rect_fast(list(arr)) == want, "84-fast(%r) got=%r want=%r"
              % (arr, max_rect_fast(list(arr)), want))

    rng = Lcg(SEED + 4)
    rect_cases = [list(a) for a, _ in (([], 0), ([1], 1), ([2, 1, 2], 3), ([2, 2, 2], 6))]
    for _ in range(150):
        rect_cases.append(gen_array(rng, rng.randint(0, 12), 0, 4))
    for _ in range(60):
        rect_cases.append(gen_array(rng, rng.randint(0, 20), 0, 50))
    for n in (1, 2, 9, 40):
        rect_cases.append(list(range(n)))
        rect_cases.append(list(range(n, 0, -1)))
        rect_cases.append([6] * n)
    for arr in rect_cases:
        want = brute_max_rect(arr)
        got = max_rect(list(arr))
        fast = max_rect_fast(list(arr))
        check(got == want, "84(%r) got=%r want=%r" % (arr, got, want))
        check(fast == want, "84-fast(%r) got=%r want=%r" % (arr, fast, want))

    # bar_spans 的三条不变量:区间合法、区间极大、每根柱子恰好一次
    for arr in rect_cases:
        n = len(arr)
        spans = bar_spans(list(arr))
        check(len(spans) == n, "bar_spans(%r) 结算次数 %d != n=%d" % (arr, len(spans), n))
        seen = sorted(j for _, _, j in spans)
        check(seen == list(range(n)), "bar_spans(%r) 下标不是 0..n-1: %r" % (arr, seen))
        for l, r, j in spans:
            ok = all(arr[k] >= arr[j] for k in range(l, r + 1))
            check(ok, "span(%r) [%d,%d] j=%d 区间里有更矮的柱子" % (arr, l, r, j))
            seg = arr[l:r + 1]
            check(seg.index(min(seg)) == j - l,
                  "span(%r) [%d,%d] j=%d 不是最左最矮柱" % (arr, l, r, j))
            check(l == 0 or arr[l - 1] <= arr[j],
                  "span(%r) [%d,%d] j=%d 左边其实还可以延长" % (arr, l, r, j))
            check(r == n - 1 or arr[r + 1] < arr[j],
                  "span(%r) [%d,%d] j=%d 右边其实还可以延长" % (arr, l, r, j))
            count = (j - (l - 1)) * ((r + 1) - j)
            check(count == count_leftmost_min(arr, j),
                  "span(%r) j=%d 区间个数 %d != 暴力 %d"
                  % (arr, j, count, count_leftmost_min(arr, j)))
        total = sum(arr[j] * (j - (l - 1)) * ((r + 1) - j) for l, r, j in spans)
        check(total == brute_sum_mins(arr),
              "区间贡献求和(%r) got=%d want=%d" % (arr, total, brute_sum_mins(arr)))

    # ---- 907:区间贡献计数 -------------------------------------------------
    rng = Lcg(SEED + 5)
    sum_cases = [[], [1], [2, 1, 2], [2, 2, 2], [3, 1, 2], [1, 2, 3], [3, 2, 1],
                 [11, 81, 94, 43, 3], [4, 2, 0, 3, 2, 5]]
    for _ in range(120):
        sum_cases.append(gen_array(rng, rng.randint(0, 14), 0, 6))
    for arr in sum_cases:
        got = sum_mins(list(arr))
        want = brute_sum_mins(arr)
        check(got == want, "907(%r) got=%r want=%r" % (arr, got, want))

    # ---- 42 接雨水 -------------------------------------------------------
    for arr, want in (([], 0), ([1], 0), ([2, 1, 3], 1), ([3, 1, 2], 1),
                      ([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1], 6),
                      ([4, 2, 0, 3, 2, 5], 9), ([5, 5, 5], 0), ([1, 2, 3], 0),
                      ([3, 2, 1], 0), ([2, 0, 2], 2), ([0, 0, 0], 0)):
        check(trap(list(arr)) == want, "42(%r) got=%r want=%r"
              % (arr, trap(list(arr)), want))
    rng = Lcg(SEED + 6)
    for _ in range(200):
        arr = gen_array(rng, rng.randint(0, 22), 0, 5)
        check(trap(list(arr)) == brute_trap(arr),
              "42(%r) got=%r want=%r" % (arr, trap(list(arr)), brute_trap(arr)))
    for n in (1, 2, 10, 41):
        check(trap(list(range(n))) == 0, "42 increasing n=%d" % n)
        check(trap(list(range(n, 0, -1))) == 0, "42 decreasing n=%d" % n)
        check(trap([4] * n) == 0, "42 all-equal n=%d" % n)

    # ---- 图里写死的数字,也逐条机器核对 --------------------------------
    # 02-pop-trace.svg
    check(nge([2, 1, 2, 4, 3]) == [4, 2, 4, -1, -1], "fig02 的 res")
    # 03-directions.svg:nums = [3,1,2,2] 四个方向的答案
    quad = [3, 1, 2, 2]
    check(brute_nge(quad) == [-1, 2, -1, -1], "fig03 下一个更大")
    check(brute_nge_ge(quad) == [-1, 2, 2, -1], "fig03 下一个更大或相等")
    check(brute_nse(quad) == [1, -1, -1, -1], "fig03 下一个更小")
    check(brute_nse_le(quad) == [1, -1, 2, -1], "fig03 下一个更小或相等")
    check(nge(list(quad)) == brute_nge(quad), "fig03 与正文模板一致")
    # 05-histogram.svg:柱子 2 的 L/R 与两笔账
    hs5 = [2, 1, 5, 6, 2, 3]
    spans5 = dict((j, (l, r)) for l, r, j in bar_spans(list(hs5)))
    check(spans5[2] == (2, 3), "fig05 柱子 2 的极大区间 %r" % (spans5[2],))
    left5, right5 = spans5[2][0] - 1, spans5[2][1] + 1
    check((left5, right5) == (1, 4), "fig05 L=%d R=%d" % (left5, right5))
    check(hs5[2] * (right5 - left5 - 1) == 10, "fig05 84 的面积")
    check((2 - left5) * (right5 - 2) == 2, "fig05 907 的区间个数")
    check(max_rect(list(hs5)) == 10 and hs5[3] * 1 == 6, "fig05 最大值与柱子 3")
    # 06-trap.svg:四层水恰好铺满每个位置的水柱
    h42 = [4, 2, 0, 3, 2, 5]
    layers42 = [(0, 2, 2, 2), (2, 3, 1, 2), (2, 3, 4, 4), (3, 4, 1, 4)]
    cover = [0] * len(h42)
    for lo, hi, first, last in layers42:
        for k in range(first, last + 1):
            cover[k] += hi - lo
    for k, v in enumerate(h42):
        want = min(max(h42[:k + 1]), max(h42[k:])) - v
        check(cover[k] == want, "fig06 第 %d 列的水层厚度 %d != %d" % (k, cover[k], want))
    check(sum((last - first + 1) * (hi - lo)
              for lo, hi, first, last in layers42) == 9, "fig06 四层相加")
    check(trap(list(h42)) == 9, "fig06 正文答案")

    return checks[0], fails


# ---------------------------------------------------------------------------
# C++ 侧
# ---------------------------------------------------------------------------

CPP_PRELUDE = r"""
// ---------------------------------------------------------------------------
// test harness generated by verify_code.py -- not part of the post
// ---------------------------------------------------------------------------
#include <algorithm>
#include <cstddef>
#include <iostream>
#include <string>
#include <vector>

namespace harness {

int g_checks = 0;
int g_fails = 0;

void check(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) {
        ++g_fails;
        if (g_fails <= 25) {
            std::cout << "FAIL: " << what << "\n";
        }
    }
}

std::string show(const std::vector<int>& v) {
    std::string s = "[";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += std::to_string(v[i]);
    }
    return s + "]";
}

void check_vec(const std::string& what, const std::vector<int>& got,
               const std::vector<int>& want) {
    check(got == want, what + " got=" + show(got) + " want=" + show(want));
}

// 和 Python 侧同一个 LCG,保证两边用例逐元素相同
struct Lcg {
    unsigned int s;
    explicit Lcg(unsigned int seed) : s(seed & 0x7FFFFFFFu) {}
    unsigned int next() {
        s = (s * 1103515245u + 12345u) & 0x7FFFFFFFu;
        return s;
    }
    int randint(int lo, int hi) {
        return lo + static_cast<int>(next() % static_cast<unsigned int>(hi - lo + 1));
    }
};

std::vector<int> gen_array(Lcg& rng, int n, int lo, int hi) {
    std::vector<int> out;
    out.reserve(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) out.push_back(rng.randint(lo, hi));
    return out;
}

std::vector<int> iota_vec(int n) {
    std::vector<int> out;
    out.reserve(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) out.push_back(i);
    return out;
}

std::vector<int> rev_iota_vec(int n) {
    std::vector<int> out;
    out.reserve(static_cast<std::size_t>(n));
    for (int i = n; i > 0; --i) out.push_back(i);
    return out;
}

std::vector<int> filled(int n, int v) {
    return std::vector<int>(static_cast<std::size_t>(n), v);
}

// ---- 暴力参考 ----
std::vector<int> brute_nge(const std::vector<int>& a) {
    int n = static_cast<int>(a.size());
    std::vector<int> res(static_cast<std::size_t>(n), -1);
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (a[j] > a[i]) { res[i] = a[j]; break; }
        }
    }
    return res;
}

std::vector<int> brute_nse(const std::vector<int>& a) {
    int n = static_cast<int>(a.size());
    std::vector<int> res(static_cast<std::size_t>(n), -1);
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (a[j] < a[i]) { res[i] = a[j]; break; }
        }
    }
    return res;
}

std::vector<int> brute_nge_circular(const std::vector<int>& a) {
    int n = static_cast<int>(a.size());
    std::vector<int> res(static_cast<std::size_t>(n), -1);
    for (int i = 0; i < n; ++i) {
        for (int step = 1; step < n; ++step) {
            int k = (i + step) % n;
            if (a[k] > a[i]) { res[i] = a[k]; break; }
        }
    }
    return res;
}

std::vector<int> brute_nge_or_eq(const std::vector<int>& a) {
    int n = static_cast<int>(a.size());
    std::vector<int> res(static_cast<std::size_t>(n), -1);
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (a[j] >= a[i]) { res[i] = a[j]; break; }
        }
    }
    return res;
}

std::vector<int> brute_nse_or_eq(const std::vector<int>& a) {
    int n = static_cast<int>(a.size());
    std::vector<int> res(static_cast<std::size_t>(n), -1);
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (a[j] <= a[i]) { res[i] = a[j]; break; }
        }
    }
    return res;
}

int brute_max_rect(const std::vector<int>& h) {
    int best = 0;
    int n = static_cast<int>(h.size());
    for (int l = 0; l < n; ++l) {
        int cur = h[l];
        for (int r = l; r < n; ++r) {
            cur = std::min(cur, h[r]);
            best = std::max(best, cur * (r - l + 1));
        }
    }
    return best;
}

int brute_sum_mins(const std::vector<int>& a) {
    const long long mod = 1000000007LL;
    long long total = 0;
    int n = static_cast<int>(a.size());
    for (int l = 0; l < n; ++l) {
        int cur = a[l];
        for (int r = l; r < n; ++r) {
            cur = std::min(cur, a[r]);
            total += cur;
        }
    }
    return static_cast<int>(total % mod);
}

int brute_trap(const std::vector<int>& h) {
    int n = static_cast<int>(h.size());
    int total = 0;
    for (int i = 0; i < n; ++i) {
        int lmax = 0;
        int rmax = 0;
        for (int k = 0; k <= i; ++k) lmax = std::max(lmax, h[k]);
        for (int k = i; k < n; ++k) rmax = std::max(rmax, h[k]);
        total += std::min(lmax, rmax) - h[i];
    }
    return total;
}

int count_leftmost_min(const std::vector<int>& h, int j) {
    int n = static_cast<int>(h.size());
    int cnt = 0;
    for (int l = 0; l <= j; ++l) {
        for (int r = j; r < n; ++r) {
            int m = h[l];
            for (int k = l; k <= r; ++k) m = std::min(m, h[k]);
            if (m != h[j]) continue;
            int first = -1;
            for (int k = l; k <= r; ++k) {
                if (h[k] == m) { first = k; break; }
            }
            if (first == j) ++cnt;
        }
    }
    return cnt;
}

}  // namespace harness
"""

CPP_MAIN = r"""
int main() {
    using harness::check;
    using harness::check_vec;
    using harness::Lcg;
    using harness::gen_array;
    using harness::iota_vec;
    using harness::rev_iota_vec;
    using harness::filled;
    using harness::brute_nge;
    using harness::brute_nge_or_eq;
    using harness::brute_nse;
    using harness::brute_nse_or_eq;
    using harness::brute_nge_circular;
    using harness::brute_max_rect;
    using harness::brute_sum_mins;
    using harness::brute_trap;
    using harness::count_leftmost_min;
    using harness::show;

    const unsigned int seed = 20261118u;

    // ---- 边界用例 ----
    {
        struct Case { std::vector<int> arr; std::vector<int> want; };
        std::vector<Case> fixed;
        fixed.push_back(Case{std::vector<int>{}, std::vector<int>{}});
        fixed.push_back(Case{std::vector<int>{5}, std::vector<int>{-1}});
        fixed.push_back(Case{std::vector<int>{0}, std::vector<int>{-1}});
        fixed.push_back(Case{std::vector<int>{1, 3, 2}, std::vector<int>{3, -1, -1}});
        fixed.push_back(Case{std::vector<int>{3, 1, 2}, std::vector<int>{-1, 2, -1}});
        fixed.push_back(Case{std::vector<int>{2, 2, 2}, std::vector<int>{-1, -1, -1}});
        fixed.push_back(Case{std::vector<int>{3, 2, 1}, std::vector<int>{-1, -1, -1}});
        fixed.push_back(Case{std::vector<int>{1, 2, 3}, std::vector<int>{2, 3, -1}});
        fixed.push_back(Case{std::vector<int>{2, 1, 2, 4, 3}, std::vector<int>{4, 2, 4, -1, -1}});
        fixed.push_back(Case{std::vector<int>{5, 4, 3, 2, 1}, std::vector<int>{-1, -1, -1, -1, -1}});
        fixed.push_back(Case{std::vector<int>{1, 1, 2, 1}, std::vector<int>{2, 2, -1, -1}});
        fixed.push_back(Case{std::vector<int>{0, 0, 0, 1}, std::vector<int>{1, 1, 1, -1}});
        for (std::size_t i = 0; i < fixed.size(); ++i) {
            check_vec("next_greater_element(fixed)", next_greater_element(fixed[i].arr),
                      fixed[i].want);
        }
    }

    // ---- 下一个更大:正着扫 / 倒着扫 / 暴力 ----
    {
        std::vector<std::vector<int>> cases;
        cases.push_back(std::vector<int>{});
        cases.push_back(std::vector<int>{2, 1, 2, 4, 3});
        cases.push_back(std::vector<int>{1, 1, 2, 1});
        Lcg rng(seed);
        for (int t = 0; t < 200; ++t) {
            cases.push_back(gen_array(rng, rng.randint(0, 30), 0, 4));
        }
        for (int t = 0; t < 100; ++t) {
            cases.push_back(gen_array(rng, rng.randint(0, 40), 0, 1000));
        }
        const int sizes[] = {0, 1, 2, 3, 8, 33};
        for (std::size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
            cases.push_back(iota_vec(sizes[i]));
            cases.push_back(rev_iota_vec(sizes[i]));
            cases.push_back(filled(sizes[i], 7));
        }
        for (std::size_t i = 0; i < cases.size(); ++i) {
            std::vector<int> want = brute_nge(cases[i]);
            check_vec("nge", next_greater_element(cases[i]), want);
            check_vec("nge_backward", next_greater_element_backward(cases[i]), want);
        }

        // 03-directions.svg 图里写死的四个答案
        std::vector<int> quad;
        quad.push_back(3);
        quad.push_back(1);
        quad.push_back(2);
        quad.push_back(2);
        check_vec("fig03 nge", brute_nge(quad),
                  std::vector<int>{-1, 2, -1, -1});
        check_vec("fig03 nge_or_eq", brute_nge_or_eq(quad),
                  std::vector<int>{-1, 2, 2, -1});
        check_vec("fig03 nse", brute_nse(quad),
                  std::vector<int>{1, -1, -1, -1});
        check_vec("fig03 nse_or_eq", brute_nse_or_eq(quad),
                  std::vector<int>{1, -1, 2, -1});
        check_vec("fig03 正文模板", next_greater_element(quad), brute_nge(quad));
    }

    // ---- 496 ----
    {
        check_vec("496 empty nums1", next_greater_element_i(std::vector<int>{},
                                                            std::vector<int>{1, 2, 3}),
                  std::vector<int>{});
        check_vec("496 basic", next_greater_element_i(std::vector<int>{2, 4},
                                                      std::vector<int>{1, 2, 3, 4}),
                  std::vector<int>{3, -1});
        Lcg rng(seed + 1u);
        for (int t = 0; t < 150; ++t) {
            int m = rng.randint(1, 20);
            std::vector<int> nums2;
            std::vector<bool> used(64, false);
            while (static_cast<int>(nums2.size()) < m) {
                int v = rng.randint(0, 59);
                if (used[static_cast<std::size_t>(v)]) continue;
                used[static_cast<std::size_t>(v)] = true;
                nums2.push_back(v);
            }
            int k = rng.randint(0, m);
            std::vector<int> nums1;
            for (int i = 0; i < k; ++i) nums1.push_back(nums2[static_cast<std::size_t>(i)]);
            std::vector<int> want;
            for (std::size_t i = 0; i < nums1.size(); ++i) {
                int pos = 0;
                while (nums2[static_cast<std::size_t>(pos)] != nums1[i]) ++pos;
                int got = -1;
                for (std::size_t j = static_cast<std::size_t>(pos) + 1; j < nums2.size(); ++j) {
                    if (nums2[j] > nums1[i]) { got = nums2[j]; break; }
                }
                want.push_back(got);
            }
            check_vec("496", next_greater_element_i(nums1, nums2), want);
        }
    }

    // ---- 下一个更小 ----
    {
        std::vector<std::vector<int>> cases;
        cases.push_back(std::vector<int>{});
        cases.push_back(std::vector<int>{5});
        cases.push_back(std::vector<int>{3, 1, 2});
        cases.push_back(std::vector<int>{1, 8, 3, 2});
        cases.push_back(std::vector<int>{1, 1, 1});
        cases.push_back(std::vector<int>{1, 2, 3});
        cases.push_back(std::vector<int>{3, 2, 1});
        cases.push_back(std::vector<int>{4, 2, 0, 3, 2, 5});
        cases.push_back(std::vector<int>{2, 1, 2, 4, 3});
        Lcg rng(seed + 2u);
        for (int t = 0; t < 150; ++t) cases.push_back(gen_array(rng, rng.randint(0, 30), 0, 5));
        for (std::size_t i = 0; i < cases.size(); ++i) {
            check_vec("next_smaller_element", next_smaller_element(cases[i]),
                      brute_nse(cases[i]));
        }
    }

    // ---- 503 环形 ----
    {
        struct Case { std::vector<int> arr; std::vector<int> want; };
        std::vector<Case> fixed;
        fixed.push_back(Case{std::vector<int>{}, std::vector<int>{}});
        fixed.push_back(Case{std::vector<int>{5}, std::vector<int>{-1}});
        fixed.push_back(Case{std::vector<int>{1, 2, 3}, std::vector<int>{2, 3, -1}});
        fixed.push_back(Case{std::vector<int>{3, 1, 2}, std::vector<int>{-1, 2, 3}});
        fixed.push_back(Case{std::vector<int>{2, 1, 2, 4, 3}, std::vector<int>{4, 2, 4, -1, 4}});
        fixed.push_back(Case{std::vector<int>{1, 1, 1}, std::vector<int>{-1, -1, -1}});
        fixed.push_back(Case{std::vector<int>{5, 4, 3, 2, 1}, std::vector<int>{-1, 5, 5, 5, 5}});
        fixed.push_back(Case{std::vector<int>{0, 0, 1}, std::vector<int>{1, 1, -1}});
        for (std::size_t i = 0; i < fixed.size(); ++i) {
            check_vec("503(fixed)", next_greater_elements(fixed[i].arr), fixed[i].want);
        }
        Lcg rng(seed + 3u);
        for (int t = 0; t < 200; ++t) {
            std::vector<int> arr = gen_array(rng, rng.randint(0, 25), 0, 4);
            check_vec("503", next_greater_elements(arr), brute_nge_circular(arr));
        }
        const int sizes[] = {1, 2, 6, 25};
        for (std::size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
            std::vector<int> inc = iota_vec(sizes[i]);
            std::vector<int> dec = rev_iota_vec(sizes[i]);
            check_vec("503 increasing", next_greater_elements(inc), brute_nge_circular(inc));
            check_vec("503 decreasing", next_greater_elements(dec), brute_nge_circular(dec));
        }
    }

    // ---- 84 ----
    {
        struct Case { std::vector<int> arr; int want; };
        std::vector<Case> fixed;
        fixed.push_back(Case{std::vector<int>{}, 0});
        fixed.push_back(Case{std::vector<int>{1}, 1});
        fixed.push_back(Case{std::vector<int>{0}, 0});
        fixed.push_back(Case{std::vector<int>{2, 1, 2}, 3});
        fixed.push_back(Case{std::vector<int>{2, 2, 2}, 6});
        fixed.push_back(Case{std::vector<int>{5, 5, 5}, 15});
        fixed.push_back(Case{std::vector<int>{1, 2, 3}, 4});
        fixed.push_back(Case{std::vector<int>{3, 2, 1}, 4});
        fixed.push_back(Case{std::vector<int>{1, 2, 3, 4, 5}, 9});
        fixed.push_back(Case{std::vector<int>{5, 4, 3, 2, 1}, 9});
        fixed.push_back(Case{std::vector<int>{2, 1, 5, 6, 2, 3}, 10});
        fixed.push_back(Case{std::vector<int>{0, 0, 0}, 0});
        fixed.push_back(Case{std::vector<int>{4, 2, 0, 3, 2, 5}, 6});
        for (std::size_t i = 0; i < fixed.size(); ++i) {
            check(largest_rectangle_area(fixed[i].arr) == fixed[i].want,
                  "84(fixed) got=" + std::to_string(largest_rectangle_area(fixed[i].arr)) +
                  " want=" + std::to_string(fixed[i].want));
            check(largest_rectangle_area_fast(fixed[i].arr) == fixed[i].want,
                  "84-fast(fixed) got=" +
                  std::to_string(largest_rectangle_area_fast(fixed[i].arr)) +
                  " want=" + std::to_string(fixed[i].want));
        }

        std::vector<std::vector<int>> cases;
        cases.push_back(std::vector<int>{});
        cases.push_back(std::vector<int>{1});
        cases.push_back(std::vector<int>{2, 1, 2});
        cases.push_back(std::vector<int>{2, 2, 2});
        Lcg rng(seed + 4u);
        for (int t = 0; t < 150; ++t) cases.push_back(gen_array(rng, rng.randint(0, 12), 0, 4));
        for (int t = 0; t < 60; ++t) cases.push_back(gen_array(rng, rng.randint(0, 20), 0, 50));
        const int sizes[] = {1, 2, 9, 40};
        for (std::size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
            cases.push_back(iota_vec(sizes[i]));
            cases.push_back(rev_iota_vec(sizes[i]));
            cases.push_back(filled(sizes[i], 6));
        }
        for (std::size_t i = 0; i < cases.size(); ++i) {
            const std::vector<int>& arr = cases[i];
            int want = brute_max_rect(arr);
            check(largest_rectangle_area(arr) == want,
                  "84(" + show(arr) + ") got=" + std::to_string(largest_rectangle_area(arr)) +
                  " want=" + std::to_string(want));
            check(largest_rectangle_area_fast(arr) == want,
                  "84-fast(" + show(arr) + ") got=" +
                  std::to_string(largest_rectangle_area_fast(arr)) +
                  " want=" + std::to_string(want));

            int n = static_cast<int>(arr.size());
            std::vector<Span> spans = bar_spans(arr);
            check(static_cast<int>(spans.size()) == n,
                  "bar_spans(" + show(arr) + ") 结算次数 " +
                  std::to_string(spans.size()) + " != n=" + std::to_string(n));
            long long total = 0;
            for (std::size_t k = 0; k < spans.size(); ++k) {
                int l = spans[k].left;
                int r = spans[k].right;
                int j = spans[k].index;
                bool ok = true;
                for (int p = l; p <= r; ++p) {
                    if (arr[static_cast<std::size_t>(p)] < arr[static_cast<std::size_t>(j)]) {
                        ok = false;
                    }
                }
                check(ok, "span(" + show(arr) + ") [" + std::to_string(l) + "," +
                          std::to_string(r) + "] j=" + std::to_string(j) +
                          " 区间里有更矮的柱子");
                int first = -1;
                int mn = arr[static_cast<std::size_t>(l)];
                for (int p = l; p <= r; ++p) mn = std::min(mn, arr[static_cast<std::size_t>(p)]);
                for (int p = l; p <= r; ++p) {
                    if (arr[static_cast<std::size_t>(p)] == mn) { first = p; break; }
                }
                check(first == j, "span(" + show(arr) + ") [" + std::to_string(l) + "," +
                                  std::to_string(r) + "] j=" + std::to_string(j) +
                                  " 不是最左最矮柱");
                check(l == 0 || arr[static_cast<std::size_t>(l - 1)] <= arr[static_cast<std::size_t>(j)],
                      "span left 其实还可以延长");
                check(r == n - 1 || arr[static_cast<std::size_t>(r + 1)] < arr[static_cast<std::size_t>(j)],
                      "span right 其实还可以延长");
                long long count = static_cast<long long>(j - (l - 1)) * ((r + 1) - j);
                check(static_cast<int>(count) == count_leftmost_min(arr, j),
                      "span(" + show(arr) + ") j=" + std::to_string(j) + " 区间个数 " +
                      std::to_string(count) + " != 暴力 " +
                      std::to_string(count_leftmost_min(arr, j)));
                total += static_cast<long long>(arr[static_cast<std::size_t>(j)]) * count;
            }
            check(static_cast<int>(total % 1000000007LL) == brute_sum_mins(arr),
                  "区间贡献求和(" + show(arr) + ") got=" + std::to_string(total) +
                  " want=" + std::to_string(brute_sum_mins(arr)));
        }
    }

    // ---- 907 ----
    {
        std::vector<std::vector<int>> cases;
        cases.push_back(std::vector<int>{});
        cases.push_back(std::vector<int>{1});
        cases.push_back(std::vector<int>{2, 1, 2});
        cases.push_back(std::vector<int>{2, 2, 2});
        cases.push_back(std::vector<int>{3, 1, 2});
        cases.push_back(std::vector<int>{1, 2, 3});
        cases.push_back(std::vector<int>{3, 2, 1});
        cases.push_back(std::vector<int>{11, 81, 94, 43, 3});
        cases.push_back(std::vector<int>{4, 2, 0, 3, 2, 5});
        Lcg rng(seed + 5u);
        for (int t = 0; t < 120; ++t) cases.push_back(gen_array(rng, rng.randint(0, 14), 0, 6));
        for (std::size_t i = 0; i < cases.size(); ++i) {
            int got = sum_of_subarray_mins(cases[i]);
            int want = brute_sum_mins(cases[i]);
            check(got == want, "907(" + show(cases[i]) + ") got=" + std::to_string(got) +
                               " want=" + std::to_string(want));
        }
    }

    // ---- 42 接雨水 ----
    {
        struct Case { std::vector<int> arr; int want; };
        std::vector<Case> fixed;
        fixed.push_back(Case{std::vector<int>{}, 0});
        fixed.push_back(Case{std::vector<int>{1}, 0});
        fixed.push_back(Case{std::vector<int>{2, 1, 3}, 1});
        fixed.push_back(Case{std::vector<int>{3, 1, 2}, 1});
        fixed.push_back(Case{std::vector<int>{0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1}, 6});
        fixed.push_back(Case{std::vector<int>{4, 2, 0, 3, 2, 5}, 9});
        fixed.push_back(Case{std::vector<int>{5, 5, 5}, 0});
        fixed.push_back(Case{std::vector<int>{1, 2, 3}, 0});
        fixed.push_back(Case{std::vector<int>{3, 2, 1}, 0});
        fixed.push_back(Case{std::vector<int>{2, 0, 2}, 2});
        fixed.push_back(Case{std::vector<int>{0, 0, 0}, 0});
        for (std::size_t i = 0; i < fixed.size(); ++i) {
            int got = trap(fixed[i].arr);
            check(got == fixed[i].want, "42(fixed) got=" + std::to_string(got) +
                                        " want=" + std::to_string(fixed[i].want));
        }
        Lcg rng(seed + 6u);
        for (int t = 0; t < 200; ++t) {
            std::vector<int> arr = gen_array(rng, rng.randint(0, 22), 0, 5);
            int got = trap(arr);
            int want = brute_trap(arr);
            check(got == want, "42(" + show(arr) + ") got=" + std::to_string(got) +
                               " want=" + std::to_string(want));
        }
        const int sizes[] = {1, 2, 10, 41};
        for (std::size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
            check(trap(iota_vec(sizes[i])) == 0, "42 increasing");
            check(trap(rev_iota_vec(sizes[i])) == 0, "42 decreasing");
            check(trap(filled(sizes[i], 4)) == 0, "42 all-equal");
        }
    }

    std::cout << "CPP CHECKS " << harness::g_checks << " FAILS " << harness::g_fails << "\n";
    return harness::g_fails == 0 ? 0 : 1;
}
"""


def run_cpp(blocks):
    build = os.path.join(HERE, "build")
    if not os.path.isdir(build):
        os.makedirs(build)
    src = os.path.join(build, "cpp_test.cpp")
    exe = os.path.join(build, "cpp_test")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(CPP_PRELUDE)
        fh.write("\n// ---------- post code blocks, in post order ----------\n")
        fh.write("\n".join(blocks))
        fh.write(CPP_MAIN)
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1", src, "-o", exe]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = proc.stderr.decode("utf-8", "replace")
    if proc.returncode != 0 or "warning:" in err:
        return None, "g++ failed (rc=%d)\n%s" % (proc.returncode, err)
    if err.strip():
        return None, "g++ stderr not empty:\n%s" % err
    run = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = run.stdout.decode("utf-8", "replace")
    if run.returncode != 0:
        return None, "C++ harness failed (rc=%d)\n%s" % (run.returncode, out)
    return out, err


def main():
    py, cpp = load_blocks()
    print("post            : %s" % os.path.relpath(POST, os.path.join(HERE, "..", "..", "..")))
    print("python blocks   : %d (expected %d)" % (len(py), EXPECTED_PY))
    print("cpp blocks      : %d (expected %d)" % (len(cpp), EXPECTED_CPP))
    if len(py) != EXPECTED_PY or len(cpp) != EXPECTED_CPP:
        print("BLOCK COUNT MISMATCH")
        return 1

    checks, fails = run_python(py)
    print("python checks   : %d, failures %d" % (checks, len(fails)))
    for f in fails:
        print("  FAIL %s" % f)

    out, err = run_cpp(cpp)
    if out is None:
        print("C++ COMPILE/RUN FAILED")
        print(err)
        return 1
    print("g++ flags       : -std=c++17 -Wall -Wextra -Werror -O1  (stderr empty, 0 warnings)")
    tail = out.strip().splitlines()[-1]
    print("cpp harness     : %s" % tail)
    for line in out.strip().splitlines()[:-1]:
        print("  %s" % line)

    if fails or "FAILS 0" not in tail:
        print("CODE FAILED")
        return 1
    print("CODE OK — %d python + %d cpp blocks, %d python assertions + %s cpp assertions, 0 failures"
          % (len(py), len(cpp), checks, tail.split()[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
