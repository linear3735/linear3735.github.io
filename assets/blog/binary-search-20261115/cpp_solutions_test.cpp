// Test harness for _posts/2026-11-15-binary-search.md
//
// This file is NOT shown in the post. verify_code.py concatenates every
// ```cpp block from the post with this file, compiles the result with
//
//   g++ -std=c++17 -Wall -Wextra -O1 -o <tmp>
//
// and requires: zero warnings, exit code 0.
//
// There is deliberately no main() here; verify_code.py appends one that
// calls run_all_tests().  Every parameter is used, because -Wextra is on.

#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

static int g_checks = 0;
static int g_failures = 0;

static void expectTrue(const std::string& what, bool ok) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        std::cout << "  FAIL " << what << "\n";
    }
}

template <typename T>
static void expectEq(const std::string& what, T got, T want) {
    ++g_checks;
    if (!(got == want)) {
        ++g_failures;
        std::cout << "  FAIL " << what << ": got " << got
                  << " want " << want << "\n";
    }
}

// LeetCode 162 guarantees nums[i] != nums[i+1]; enforce it so that a peak
// is guaranteed to exist for every generated array.
static void make_adjacent_distinct(std::vector<int>& v) {
    for (std::size_t i = 1; i < v.size(); ++i) {
        while (v[i] == v[i - 1]) ++v[i];
    }
}

static std::vector<int> random_sorted(std::mt19937& rng, int n, int lo,
                                      int hi) {
    std::uniform_int_distribution<int> d(lo, hi);
    std::vector<int> v(static_cast<std::size_t>(n));
    for (int& x : v) x = d(rng);
    std::sort(v.begin(), v.end());
    return v;
}

// ---------------------------------------------------------------- sections 2-3
// Both boundary conventions must agree with the standard library, and with
// each other, on every input.
static void test_search_conventions() {
    std::mt19937 rng(20261115);
    int cases = 0;
    for (int n = 0; n <= 20; ++n) {
        for (int rep = 0; rep < 40; ++rep) {
            std::vector<int> nums = random_sorted(rng, n, -6, 6);
            for (int target = -8; target <= 8; ++target) {
                ++cases;
                const auto b = nums.begin(), e = nums.end();
                const int lb = static_cast<int>(std::lower_bound(b, e, target) - b);
                const int ub = static_cast<int>(std::upper_bound(b, e, target) - b);
                const bool present = lb < ub;

                expectEq("leftBound(closed)", leftBound(nums, target), lb);
                expectEq("rightBound(closed)", rightBound(nums, target), ub - 1);
                expectEq("leftBoundOpen(open)", leftBoundOpen(nums, target), lb);
                expectEq("rightBoundOpen(open)", rightBoundOpen(nums, target),
                         ub - 1);

                // The article's claim: two conventions, identical semantics.
                expectEq("closed==open left", leftBound(nums, target),
                         leftBoundOpen(nums, target));
                expectEq("closed==open right", rightBound(nums, target),
                         rightBoundOpen(nums, target));

                // left_bound > right_bound  <=>  target absent.
                expectTrue("existence iff lb>rb",
                           (lb > ub - 1) == !present);

                // The occurrence count formula from section 2.4.
                expectEq("occurrences", ub - lb,
                         static_cast<int>(std::count(b, e, target)));

                const int got_closed = binarySearch(nums, target);
                const int got_open = binarySearchOpen(nums, target);
                expectTrue("binarySearch found flag", (got_closed >= 0) == present);
                expectTrue("binarySearchOpen found flag", (got_open >= 0) == present);
                if (got_closed >= 0) {
                    expectEq("binarySearch value",
                             nums[static_cast<std::size_t>(got_closed)], target);
                }
                if (got_open >= 0) {
                    expectEq("binarySearchOpen value",
                             nums[static_cast<std::size_t>(got_open)], target);
                }
            }
        }
    }
    std::cout << "  sections 2-3: " << cases << " (array, target) pairs checked\n";
}

// ---------------------------------------------------------------- section 4.2
static int koko_reference(const std::vector<int>& piles, int h) {
    const int hi = *std::max_element(piles.begin(), piles.end());
    for (int k = 1; k <= hi; ++k) {
        long long hours = 0;
        for (int p : piles) hours += (p + k - 1) / k;
        if (hours <= h) return k;
    }
    return -1;
}

static void test_koko() {
    std::mt19937 rng(875);
    for (int rep = 0; rep < 300; ++rep) {
        std::uniform_int_distribution<int> dn(1, 8), dp(1, 30);
        const int n = dn(rng);
        std::vector<int> piles(static_cast<std::size_t>(n));
        for (int& p : piles) p = dp(rng);
        const long long total = std::accumulate(piles.begin(), piles.end(), 0LL);
        // h >= n is the LeetCode constraint; it also guarantees that k =
        // max(piles) is feasible, so the brute-force reference always finds a k.
        std::uniform_int_distribution<int> dh(n, static_cast<int>(total));
        const int h = dh(rng);
        expectEq("minEatingSpeed", minEatingSpeed(piles, h),
                 koko_reference(piles, h));
    }
    // The article's worked example: piles = [3,6,7,11], h = 8  ->  4
    expectEq("koko example", minEatingSpeed({3, 6, 7, 11}, 8), 4);
    std::cout << "  section 4.2: 301 koko cases checked\n";
}

// ---------------------------------------------------------------- section 4.3
static int ship_reference(const std::vector<int>& weights, int days) {
    const int lo = *std::max_element(weights.begin(), weights.end());
    const int hi = static_cast<int>(
        std::accumulate(weights.begin(), weights.end(), 0LL));
    for (int c = lo; c <= hi; ++c) {
        int used = 1, load = 0;
        for (int w : weights) {
            if (load + w > c) { ++used; load = 0; }
            load += w;
        }
        if (used <= days) return c;
    }
    return -1;
}

static void test_ship() {
    std::mt19937 rng(1011);
    for (int rep = 0; rep < 300; ++rep) {
        std::uniform_int_distribution<int> dn(1, 8), dw(1, 20);
        const int n = dn(rng);
        std::vector<int> weights(static_cast<std::size_t>(n));
        for (int& w : weights) w = dw(rng);
        std::uniform_int_distribution<int> dd(1, n + 3);
        const int days = dd(rng);
        expectEq("shipWithinDays", shipWithinDays(weights, days),
                 ship_reference(weights, days));
    }
    expectEq("ship example", shipWithinDays({1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, 5),
             15);
    std::cout << "  section 4.3: 301 ship cases checked\n";
}

// ---------------------------------------------------------------- section 4.4
static int split_reference(const std::vector<int>& nums, int m) {
    const int n = static_cast<int>(nums.size());
    int best = -1;
    // enumerate every way to place m-1 cut points among n-1 gaps
    const int gaps = n - 1;
    for (int mask = 0; mask < (1 << gaps); ++mask) {
        int cuts = 0;
        for (int i = 0; i < gaps; ++i)
            if (mask & (1 << i)) ++cuts;
        if (cuts != m - 1) continue;
        int worst = 0, run = 0;
        for (int i = 0; i < n; ++i) {
            run += nums[static_cast<std::size_t>(i)];
            const bool cut_here = (i == n - 1) || (mask & (1 << i));
            if (cut_here) { worst = std::max(worst, run); run = 0; }
        }
        if (best < 0 || worst < best) best = worst;
    }
    return best;
}

static void test_split() {
    std::mt19937 rng(410);
    for (int rep = 0; rep < 400; ++rep) {
        std::uniform_int_distribution<int> dn(1, 8), dv(0, 15);
        const int n = dn(rng);
        std::vector<int> nums(static_cast<std::size_t>(n));
        for (int& x : nums) x = dv(rng);
        std::uniform_int_distribution<int> dm(1, n);
        const int m = dm(rng);
        expectEq("splitArray", splitArray(nums, m), split_reference(nums, m));
    }
    expectEq("split example", splitArray({7, 2, 5, 10, 8}, 2), 18);
    std::cout << "  section 4.4: 401 split cases checked\n";
}

// ---------------------------------------------------------------- section 5.1
static bool is_peak(const std::vector<int>& nums, int i) {
    const int n = static_cast<int>(nums.size());
    if (i < 0 || i >= n) return false;
    const bool left_ok = (i == 0) ||
                         (nums[static_cast<std::size_t>(i)] >
                          nums[static_cast<std::size_t>(i - 1)]);
    const bool right_ok = (i == n - 1) ||
                          (nums[static_cast<std::size_t>(i)] >
                           nums[static_cast<std::size_t>(i + 1)]);
    return left_ok && right_ok;
}

static void test_peak() {
    std::mt19937 rng(162);
    for (int rep = 0; rep < 2000; ++rep) {
        std::uniform_int_distribution<int> dn(1, 25), dv(-50, 50);
        const int n = dn(rng);
        std::vector<int> nums(static_cast<std::size_t>(n));
        for (int& x : nums) x = dv(rng);
        make_adjacent_distinct(nums);
        const int got = findPeakElement(nums);
        expectTrue("findPeakElement returns a real peak", is_peak(nums, got));
    }
    expectEq("peak of increasing", findPeakElement({1, 2, 3, 4}), 3);
    expectEq("peak of decreasing", findPeakElement({4, 3, 2, 1}), 0);
    expectEq("peak single", findPeakElement({7}), 0);
    std::cout << "  section 5.1: 2003 peak cases checked\n";
}

// ---------------------------------------------------------------- section 6
static void test_weighted_picker() {
    // Deterministic RNG is *inside* the article's class, so this measures the
    // real implementation, not a copy.
    const std::vector<int> w = {1, 3, 0, 2, 4, 0, 6};
    WeightedPicker picker(w);
    long long total = std::accumulate(w.begin(), w.end(), 0LL);
    const long long trials = 400000;
    std::vector<long long> hits(w.size(), 0);
    for (long long i = 0; i < trials; ++i) {
        const int idx = picker.pickIndex();
        expectTrue("pickIndex in range", idx >= 0 &&
                   idx < static_cast<int>(w.size()));
        if (idx < 0 || idx >= static_cast<int>(w.size())) return;
        ++hits[static_cast<std::size_t>(idx)];
    }
    for (std::size_t i = 0; i < w.size(); ++i) {
        const double want = static_cast<double>(w[i]) /
                            static_cast<double>(total);
        const double got = static_cast<double>(hits[i]) /
                           static_cast<double>(trials);
        if (w[i] == 0) {
            expectEq("zero weight never picked", hits[i], 0LL);
        } else {
            // 4 sigma on a binomial with n = 400000; sigma <= 0.0008
            expectTrue("frequency within 4 sigma of w[i]/sum(w)",
                       std::abs(got - want) < 0.004);
        }
    }
    std::cout << "  section 6: " << trials << " samples over "
              << w.size() << " weights checked\n";
}

int run_all_tests() {
    std::cout << "C++ checks\n";
    test_search_conventions();
    test_koko();
    test_ship();
    test_split();
    test_peak();
    test_weighted_picker();
    std::cout << "  " << g_checks << " assertions, " << g_failures
              << " failures\n";
    return g_failures == 0 ? 0 : 1;
}
