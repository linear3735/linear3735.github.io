// C++ 侧驱动 for _posts/2026-11-28-knapsack.md
//
// 这个文件**不是**文章的一部分。verify_code.py 会把文章里抽出来的 ```cpp 片段
// 原样拼在本文件前面，再用
//     g++ -std=c++17 -Wall -Wextra -O1 main.cpp -o main
// 编译（要求零警告）。所以这里只写测试和独立参考实现，
// 一篇文章函数都不重复抄；要测的就是文章里那段代码本身。
#include <cstdio>
#include <functional>
#include <random>
#include <string>
#include <vector>
using namespace std;

static int g_checks = 0;
static int g_failures = 0;

static void expect_eq(long long got, long long want, const string& what) {
    g_checks++;
    if (got != want) {
        g_failures++;
        printf("  cpp| FAIL %s: got %lld, want %lld\n", what.c_str(), got, want);
    }
}

static void expect_true(bool cond, const string& what) {
    g_checks++;
    if (!cond) {
        g_failures++;
        printf("  cpp| FAIL %s\n", what.c_str());
    }
}

// ---------- 独立参考实现（只用于对拍） ----------

long long ref_brute_exact(int W, const vector<int>& wt, const vector<int>& val) {
    int n = (int)wt.size();
    long long best = -1;
    for (int mask = 0; mask < (1 << n); mask++) {
        int tw = 0;
        long long tv = 0;
        for (int i = 0; i < n; i++) {
            if ((mask >> i) & 1) { tw += wt[i]; tv += val[i]; }
        }
        if (tw == W && tv > best) best = tv;
    }
    return best;
}

long long ref_unbounded(int W, const vector<int>& wt, const vector<int>& val) {
    int n = (int)wt.size();
    vector<vector<int>> dp(n + 1, vector<int>(W + 1, 0));
    for (int i = 1; i <= n; i++) {
        for (int w = 0; w <= W; w++) {
            dp[i][w] = dp[i - 1][w];
            if (wt[i - 1] <= w) {
                int cand = dp[i][w - wt[i - 1]] + val[i - 1];
                if (cand > dp[i][w]) dp[i][w] = cand;
            }
        }
    }
    return dp[n][W];
}

long long ref_combos(int amount, const vector<int>& coins) {
    // 递归枚举非降序的面额序列
    function<long long(int, int)> go = [&](int rest, int start) -> long long {
        long long total = (rest == 0) ? 1 : 0;
        for (int i = start; i < (int)coins.size(); i++) {
            if (coins[i] <= rest) total += go(rest - coins[i], i);
        }
        return total;
    };
    return go(amount, 0);
}

long long ref_perms(int amount, const vector<int>& coins) {
    // 递归枚举有序的面额序列
    function<long long(int)> go = [&](int rest) -> long long {
        if (rest == 0) return 1;
        long long total = 0;
        for (int c : coins) if (c >= 1 && c <= rest) total += go(rest - c);
        return total;
    };
    return go(amount);
}

bool ref_can_partition(const vector<int>& nums) {
    int n = (int)nums.size();
    int total = 0;
    for (int x : nums) total += x;
    for (int mask = 0; mask < (1 << n); mask++) {
        int s = 0;
        for (int i = 0; i < n; i++) if ((mask >> i) & 1) s += nums[i];
        if (2 * s == total) return true;
    }
    return false;
}

int ref_min_distance(const string& s1, const string& s2) {
    // 自顶向下记忆化：跟文章里的填表版是两种写法
    int m = (int)s1.size(), n = (int)s2.size();
    vector<vector<int>> memo(m + 1, vector<int>(n + 1, -1));
    function<int(int, int)> f = [&](int i, int j) -> int {
        if (i == 0) return j;
        if (j == 0) return i;
        if (memo[i][j] != -1) return memo[i][j];
        int r;
        if (s1[i - 1] == s2[j - 1]) r = f(i - 1, j - 1);
        else r = 1 + min(f(i - 1, j), min(f(i, j - 1), f(i - 1, j - 1)));
        memo[i][j] = r;
        return r;
    };
    return f(m, n);
}

struct Op {
    string kind;   // delete / replace / insert
    int pos;
    char from;     // delete: 被删的字符；replace: 被换掉的字符；insert: 未使用
    char to;       // insert: 插入的字符；replace: 换成什么
};

// 操作格式（和文章里 Python 版一致）：
//   "delete s1[2]='a'"   "replace s1[2]='a'->'b'"   "insert at 1 'b'"
Op parse_op(const string& s) {
    Op o;
    o.pos = -1;
    o.from = 0;
    o.to = 0;
    if (s.rfind("delete ", 0) == 0) {
        o.kind = "delete";
        size_t lb = s.find('['), rb = s.find(']');
        size_t q = s.find('\'', rb);
        o.pos = stoi(s.substr(lb + 1, rb - lb - 1));
        o.from = s[q + 1];
    } else if (s.rfind("replace ", 0) == 0) {
        o.kind = "replace";
        size_t lb = s.find('['), rb = s.find(']');
        size_t q1 = s.find('\'', rb);
        // 操作串的格式是  'c'->'a'：两个字符**各自**带引号，箭头两侧各有一对。
        // 所以第二个引号必须从箭头之后开始找。这里原先写的是 q1 + 2，
        // 那是 '[c]'->[a]' 的偏移，实际落在 'c' 的收尾引号上，
        // q2 + 1 取到的是 '-' 而不是目标字符——于是替换永远校验失败。
        size_t arrow = s.find("->", q1);
        size_t q2 = s.find('\'', arrow);
        o.pos = stoi(s.substr(lb + 1, rb - lb - 1));
        o.from = s[q1 + 1];
        o.to = s[q2 + 1];
    } else {
        o.kind = "insert";
        size_t at = s.find("at ");
        size_t q1 = s.find('\'', at);
        o.pos = stoi(s.substr(at + 3, q1 - at - 3 - 1));
        o.to = s[q1 + 1];
    }
    return o;
}

bool ops_valid(const string& s1, const vector<string>& ops, const string& s2, int expect_len) {
    if ((int)ops.size() != expect_len) return false;
    string out;
    size_t cursor = 0;
    int prev_pos = -1;
    for (const string& s : ops) {
        Op o = parse_op(s);
        if (o.pos < 0 || o.pos < prev_pos) return false;      // 位置必须单调不减
        if ((size_t)o.pos < cursor) return false;             // 也不能倒退
        prev_pos = o.pos;
        out += s1.substr(cursor, (size_t)o.pos - cursor);     // 跨过的字符：匹配上的，原样保留
        cursor = (size_t)o.pos;
        if (o.kind == "insert") {
            out += o.to;
        } else {
            if (cursor >= s1.size() || s1[cursor] != o.from) return false;
            if (o.kind == "replace") out += o.to;
            cursor++;
        }
    }
    out += s1.substr(cursor);
    return out == s2;
}

vector<int> rand_coins(mt19937& rng) {
    vector<int> coins;
    for (int v = 1; v <= 6; v++) {
        if (rng() % 5 < 2) coins.push_back(v);
    }
    return coins;
}

string rand_str(mt19937& rng, int maxlen) {
    string s;
    int len = (int)(rng() % (unsigned)(maxlen + 1));
    for (int i = 0; i < len; i++) s += (char)('a' + rng() % 3);
    return s;
}

int main() {
    mt19937 rng(20261128);

    // ---------- 固定用例 ----------
    {
        vector<int> wt{2, 1, 3}, val{4, 2, 3};
        expect_eq(knapsackBrute(4, wt, val), 6, "brute W=4");
        expect_eq(knapsack01(4, wt, val), 6, "01 二维 W=4");
        expect_eq(knapsack01Rolling(4, wt, val), 6, "01 一维 W=4");
        expect_eq(knapsack01(0, wt, val), 0, "01 容量 0");
        expect_eq(knapsack01Rolling(0, wt, val), 0, "01 一维 容量 0");
        vector<int> none;
        expect_eq(knapsack01(4, none, none), 0, "01 空物品");
        vector<int> w5{5}, v9{9};
        expect_eq(knapsack01(1, w5, v9), 0, "01 单件装不下");
        expect_eq(knapsack01(5, w5, v9), 9, "01 单件刚好装下");

        // 恰好装满和「至多装」不同：W=4 只有 {1,3} 能填满（值 5），W=3 是 {2,1}（值 6）
        expect_eq(knapsack01Exact(4, wt, val), 5, "恰好装满 W=4");
        expect_eq(knapsack01Exact(3, wt, val), 6, "恰好装满 W=3");
        vector<int> w22{2, 2}, v33{3, 3};
        expect_eq(knapsack01Exact(3, w22, v33), -1, "恰好装满 装不满");
        expect_eq(knapsack01Exact(4, w22, v33), 6, "恰好装满 刚好");
        expect_eq(knapsack01Exact(0, wt, val), 0, "恰好装满 W=0");
        vector<int> w24{2, 4}, v59{5, 9};
        expect_eq(knapsack01Exact(7, w24, v59), -1, "恰好装满 无解");

        vector<int> w2{2}, v3{3};
        expect_eq(unboundedKnapsack(4, w2, v3), 6, "完全背包 装两次");
        expect_eq(unboundedKnapsack(0, w2, v3), 0, "完全背包 容量 0");
        expect_eq(unboundedKnapsack(4, none, none), 0, "完全背包 空物品");

        vector<int> c125{1, 2, 5};
        expect_eq(changeCombinations(5, c125), 4, "组合数 518 样例");
        expect_eq(changePermutations(5, c125), 9, "排列数 同样例");
        vector<int> c12{1, 2};
        expect_eq(changeCombinations(0, c12), 1, "组合数 amount=0");
        expect_eq(changeCombinations(3, none), 0, "组合数 无面额");
        expect_eq(changePermutations(0, none), 1, "排列数 amount=0 无面额");

        vector<int> n15115{1, 5, 11, 5};
        expect_eq(canPartition(n15115), 1, "416 样例 true");
        vector<int> n1235{1, 2, 3, 5};
        expect_eq(canPartition(n1235), 0, "416 样例 false");
        vector<int> n12{1, 2};
        expect_eq(canPartition(n12), 0, "416 奇数和");
        vector<int> n2{2};
        expect_eq(canPartition(n2), 0, "416 单元素 {2} vs {} 不是平分");
        expect_eq(canPartition(none), 1, "416 空数组");

        vector<int> five{1, 1, 1, 1, 1};
        expect_eq(findTargetSumWaysBrute(five, 3), 5, "494 暴力样例");
        expect_eq(findTargetSumWays(five, 3), 5, "494 样例");
        vector<int> one{1};
        expect_eq(findTargetSumWays(one, 1), 1, "494 单元素");
        expect_eq(findTargetSumWays(one, 2), 0, "494 无解");
        vector<int> z1{0}, z2{0, 0};
        expect_eq(findTargetSumWays(z1, 0), 2, "494 零元素");
        expect_eq(findTargetSumWays(z2, 0), 4, "494 两个零");

        expect_eq(minDistance("horse", "ros"), 3, "72 horse/ros");
        expect_eq(minDistance("intention", "execution"), 5, "72 intention");
        expect_eq(minDistance("", ""), 0, "72 两个空串");
        expect_eq(minDistance("abc", ""), 3, "72 只能删");
        expect_eq(minDistance("", "abc"), 3, "72 只能插");
        expect_eq(minDistance("abc", "abc"), 0, "72 完全相同");
    }

    // ---------- 随机对拍 ----------
    for (int t = 0; t < 200; t++) {
        int n = (int)(rng() % 10);
        int W = (int)(rng() % 15);
        vector<int> wt(n), val(n);
        for (int i = 0; i < n; i++) {
            wt[i] = (int)(rng() % 9);
            val[i] = (int)(rng() % 21);
        }
        long long b = knapsackBrute(W, wt, val);
        expect_eq(knapsack01(W, wt, val), b, "随机 01 二维 vs 暴力");
        expect_eq(knapsack01Rolling(W, wt, val), b, "随机 01 一维 vs 暴力");
        expect_eq(knapsack01Exact(W, wt, val), ref_brute_exact(W, wt, val), "随机恰好装满");
        expect_eq(unboundedKnapsack(W, wt, val), ref_unbounded(W, wt, val), "随机完全背包");
    }
    for (int t = 0; t < 120; t++) {
        int amount = (int)(rng() % 12);
        vector<int> coins = rand_coins(rng);
        expect_eq(changeCombinations(amount, coins), ref_combos(amount, coins), "随机组合数");
        expect_eq(changePermutations(amount, coins), ref_perms(amount, coins), "随机排列数");
    }
    for (int t = 0; t < 120; t++) {
        int n = (int)(rng() % 9);
        vector<int> nums(n);
        for (int i = 0; i < n; i++) nums[i] = (int)(rng() % 9) + 1;
        int target = (int)(rng() % 13) - 6;
        expect_true(canPartition(nums) == ref_can_partition(nums), "随机 416");
        expect_eq(findTargetSumWays(nums, target), findTargetSumWaysBrute(nums, target),
                  "随机 494 vs 暴力");
    }
    for (int t = 0; t < 120; t++) {
        string s1 = rand_str(rng, 7), s2 = rand_str(rng, 7);
        int d = minDistance(s1, s2);
        expect_eq(d, ref_min_distance(s1, s2), "随机 72 vs 记忆化");
        vector<string> ops = minDistanceOps(s1, s2);
        expect_eq((long long)ops.size(), d, "随机 72 操作数");
        expect_true(ops_valid(s1, ops, s2, d), "随机 72 操作序列能还原 s2");
    }

    printf("  cpp| cases: %d, failures: %d\n", g_checks, g_failures);
    if (g_failures == 0) printf("  cpp| ALL CPP CASES PASS\n");
    return g_failures == 0 ? 0 : 1;
}
