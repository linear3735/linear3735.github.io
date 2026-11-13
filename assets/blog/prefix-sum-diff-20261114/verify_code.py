#!/usr/bin/env python3
"""Code gate for `_posts/2026-11-14-prefix-sum-diff.md`.

Extracts every ```python and ```cpp block straight out of the article body (no
mirrored copies that can drift), then:

  * runs every Python implementation against its brute-force twin on random
    inputs, all sub-rectangles of small matrices, and a fixed boundary list
    (空数组、单元素、全相等、全负数、l == r、区间取满全长、空区间 l == r+1)
  * re-runs the article's own Python benchmark block as a subprocess (`--quick`)
    so `main()` is executed for real, not just exec'd
  * compiles all C++ blocks with -Wall -Wextra -Werror (two translation units,
    the second one adds the benchmark and runs it with --quick)
  * re-checks the LeetCode examples the article pastes (370 / 1109 / 1094 / 304)

Run:  /opt/miniconda3/bin/python3 verify_code.py
"""
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
POST = HERE.parent.parent.parent / "_posts" / "2026-11-14-prefix-sum-diff.md"

EXPECTED_PY = 7
EXPECTED_CPP = 7
SEED = 20261114

LC304 = [[3, 0, 1, 4, 2],
         [5, 6, 3, 2, 1],
         [1, 2, 0, 1, 5],
         [4, 1, 0, 1, 7],
         [1, 0, 3, 0, 5]]


def blocks(lang):
    src = POST.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"```" + lang + r"\n(.*?)```", src, re.S):
        body = m.group(1)
        if "def " in body or "#include" in body:
            out.append(body)
    return out


PY_NAMES = ["NumArrayBrute", "NumArray", "NumMatrixBrute", "NumMatrix",
            "build_by_axis", "DifferenceBrute", "Difference",
            "get_modified_array", "corp_flight_bookings", "car_pooling"]

FIXED_1D = [[], [7], [-3], [5, 5, 5, 5], [-1, -2, -3, -4], [0, 0, 0],
            [10 ** 6, -10 ** 6], [2, -2, 2, -2, 2]]


# ---------------------------------------------------------------- python side
def run_python(py_blocks):
    fails, checks = [], 0
    ns = {"__name__": "article_code"}
    for b in py_blocks:
        try:
            exec(compile(b, "<article>", "exec"), ns)
        except Exception as e:                       # noqa: BLE001
            fails.append(f"exec of a python block failed: {type(e).__name__}: {e}")
            return fails, checks

    def check(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(msg)

    for name in PY_NAMES:
        check(name in ns, f"{name} not defined by any python block")
    if fails:
        return fails, checks

    rng = random.Random(SEED)

    # ---- 一维:暴力 vs 前缀和,逐个区间 ----------------------------------
    cases = list(FIXED_1D) + [[rng.randint(-30, 30) for _ in range(rng.randint(1, 40))]
                              for _ in range(200)]
    bad = None
    for nums in cases:
        fb, ff = ns["NumArrayBrute"](nums), ns["NumArray"](nums)
        n = len(nums)
        probes = [(l, r) for l in range(n) for r in range(l, n)]
        probes += [(l, l - 1) for l in range(n + 1)]          # 空区间
        for l, r in probes:
            want = sum(nums[l:r + 1])
            got_b, got_f = fb.sum_range(l, r), ff.sum_range(l, r)
            if got_b != want:
                bad = f"NumArrayBrute{ nums[:6] }[{l},{r}] = {got_b}, want {want}"
            elif got_f != want:
                bad = f"NumArray{ nums[:6] }[{l},{r}] = {got_f}, want {want}"
            if bad:
                break
        if bad:
            break
    check(bad is None, bad or "")
    print(f"  ok  [py] 一维:{len(cases)} 组数组（含空数组/单元素/全相等/全负数）"
          f"的每个区间都与暴力解一致")

    # ---- 二维:暴力 vs 容斥 vs 逐维,逐个子矩形 --------------------------
    shapes = [(1, 1), (1, 5), (5, 1), (2, 3), (4, 4), (3, 6)]
    shapes += [(rng.randint(1, 5), rng.randint(1, 5)) for _ in range(30)]
    bad, rects = None, 0
    for m, n in shapes:
        matrix = [[rng.randint(-20, 20) for _ in range(n)] for _ in range(m)]
        nb, nm = ns["NumMatrixBrute"](matrix), ns["NumMatrix"](matrix)
        if ns["build_by_axis"](matrix) != nm.preSum:
            bad = f"build_by_axis != preSum for a {m}x{n} matrix"
            break
        for r1 in range(m):
            for r2 in range(r1, m):
                for c1 in range(n):
                    for c2 in range(c1, n):
                        rects += 1
                        want = sum(matrix[i][j]
                                   for i in range(r1, r2 + 1)
                                   for j in range(c1, c2 + 1))
                        if nb.sum_region(r1, c1, r2, c2) != want:
                            bad = f"NumMatrixBrute[{r1},{c1},{r2},{c2}] mismatch"
                        elif nm.sum_region(r1, c1, r2, c2) != want:
                            bad = f"NumMatrix[{r1},{c1},{r2},{c2}] mismatch"
                        if bad:
                            break
                    if bad:
                        break
                if bad:
                    break
            if bad:
                break
        if bad:
            break
    check(bad is None, bad or "")
    print(f"  ok  [py] 二维:{len(shapes)} 种形状（含 1x1、1xN、Nx1）共 {rects} 个子矩形，"
          f"容斥版与逐维版都对得上暴力解")

    # ---- 差分:暴力 vs 差分数组 ------------------------------------------
    bad, trials = None, 0
    for _ in range(300):
        n = rng.randint(1, 40)
        nums = [rng.randint(-30, 30) for _ in range(n)]
        db, df = ns["DifferenceBrute"](nums), ns["Difference"](nums)
        for _ in range(rng.randint(1, 12)):
            i = rng.randrange(n)
            j = rng.randrange(i, n)
            val = rng.randint(-15, 15)
            db.increment(i, j, val)
            df.increment(i, j, val)
        trials += 1
        if db.result() != df.result():
            bad = f"Difference disagrees with DifferenceBrute on {nums[:6]}..."
            break
    check(bad is None, bad or "")

    # 语义直查:全 0 数组上给 [i, j] 加 v,结果必须恰好是 [i, j] 段为 v
    bad = None
    for n in (1, 2, 7):
        for i in range(n):
            for j in range(i, n):
                df = ns["Difference"]([0] * n)
                df.increment(i, j, 5)
                want = [5 if i <= k <= j else 0 for k in range(n)]
                if df.result() != want:
                    bad = f"Difference[{n}] increment({i},{j},5) = {df.result()}, want {want}"
    check(bad is None, bad or "")

    # 边界:i == j == n-1 时不该出现任何 -val;空数组两种实现都要能构造
    df = ns["Difference"]([1, 2, 3])
    df.increment(2, 2, 4)
    check(df.result() == [1, 2, 7], f"increment(2,2,4) on [1,2,3] = {df.result()}")
    check(df.diff == [1, 1, 5], f"increment(2,2,4) touched diff = {df.diff}")
    check(ns["Difference"]([]).result() == [], "Difference([]).result() != []")
    check(ns["DifferenceBrute"]([]).result() == [], "DifferenceBrute([]).result() != []")
    check(ns["get_modified_array"](0, []) == [], "get_modified_array(0, []) != []")
    print(f"  ok  [py] 差分:{trials} 组随机用例 + 全区间/单点/末元素/空数组边界都对上了")

    # ---- 力扣原题 --------------------------------------------------------
    check(ns["get_modified_array"](5, [[1, 3, 2], [2, 4, 3], [0, 2, -2]])
          == [-2, 0, 3, 5, 3], "LC 370 example mismatch")
    check(ns["corp_flight_bookings"]([[1, 2, 10], [2, 3, 20], [2, 5, 25]], 5)
          == [10, 55, 45, 25, 25], "LC 1109 example mismatch")
    check(ns["car_pooling"]([[2, 1, 5], [3, 3, 7]], 4) is False, "LC 1094 #1")
    check(ns["car_pooling"]([[2, 1, 5], [3, 3, 7]], 5) is True, "LC 1094 #2")
    check(ns["car_pooling"]([[2, 1, 5], [3, 5, 7]], 3) is True, "LC 1094 #3")
    nm = ns["NumMatrix"](LC304)
    check(nm.sum_region(2, 1, 4, 3) == 8, "LC 304 sumRegion(2,1,4,3) != 8")
    check(nm.sum_region(1, 1, 2, 2) == 11, "LC 304 sumRegion(1,1,2,2) != 11")
    check(nm.sum_region(1, 2, 2, 4) == 12, "LC 304 sumRegion(1,2,2,4) != 12")
    check(nm.preSum[5][4] == 38 and nm.preSum[2][4] == 24
          and nm.preSum[5][1] == 14 and nm.preSum[2][1] == 8,
          "文章里 304 那张四项表的数字对不上")
    print("  ok  [py] 力扣 370 / 1109 / 1094 / 304 的示例值逐个复现")

    # ---- 文章自己的实测脚本,真的跑一遍 ----------------------------------
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "bench_from_article.py"
        script.write_text("\n\n".join(py_blocks), encoding="utf-8")
        for label, extra in (("--quick", ["--quick"]), ("全量", [])):
            cp = subprocess.run([sys.executable, str(script), *extra],
                                capture_output=True, text=True)
            if cp.returncode != 0:
                fails.append(f"article python bench ({label}) exited "
                             f"{cp.returncode}: {cp.stderr.strip()[:600]}")
                continue
            hits = cp.stdout.count("对拍一致")
            if hits != 3:
                fails.append(f"python bench ({label}) printed {hits} "
                             f"'对拍一致' lines, want 3")
            else:
                print(f"  ok  [py] 第 5 节的实测脚本以 {label} 模式真跑了一遍:"
                      f"3 个格子全部「对拍一致」")
    return fails, checks


# ---------------------------------------------------------------- cpp side
CPP_HEAD = """#include <chrono>
#include <cstddef>
#include <iostream>
#include <random>
#include <string>
#include <vector>
"""

CPP_MAIN = r"""
static int failures = 0;
static int checks = 0;

static void expect(bool cond, const std::string& what) {
    checks++;
    if (!cond) { failures++; std::cout << "  FAIL " << what << "\n"; }
}

static std::vector<std::vector<int>> lc304() {
    return {{3, 0, 1, 4, 2}, {5, 6, 3, 2, 1}, {1, 2, 0, 1, 5},
            {4, 1, 0, 1, 7}, {1, 0, 3, 0, 5}};
}

static void check_1d() {
    std::vector<std::vector<int>> cases = {
        {}, {7}, {-3}, {5, 5, 5, 5}, {-1, -2, -3, -4}, {0, 0, 0},
        {1000000, -1000000}, {2, -2, 2, -2, 2},
    };
    std::mt19937 rng(20261114u);
    std::uniform_int_distribution<int> pick(-30, 30);
    for (int t = 0; t < 60; t++) {
        std::vector<int> v(static_cast<std::size_t>(rng() % 30 + 1));
        for (int& x : v) x = pick(rng);
        cases.push_back(v);
    }
    int probes = 0;
    for (const std::vector<int>& nums : cases) {
        NumArrayBrute nb(nums);
        NumArray nf(nums);
        const int n = static_cast<int>(nums.size());
        for (int l = 0; l < n; l++) {
            for (int r = l; r < n; r++) {
                int want = 0;
                for (int k = l; k <= r; k++) want += nums[static_cast<std::size_t>(k)];
                probes++;
                if (nb.sumRange(l, r) != want || nf.sumRange(l, r) != want) {
                    expect(false, "1-D mismatch at [" + std::to_string(l) + "," +
                                  std::to_string(r) + "]");
                    return;
                }
            }
        }
        // 空区间 l == r+1:两种实现都必须给 0
        for (int l = 0; l <= n; l++) {
            probes++;
            if (nb.sumRange(l, l - 1) != 0 || nf.sumRange(l, l - 1) != 0) {
                expect(false, "empty range at " + std::to_string(l));
                return;
            }
        }
    }
    expect(true, "1-D ok");
    std::cout << "  ok  [cpp] 一维:" << cases.size() << " 组数组 / " << probes
              << " 个区间（含空区间）与暴力解一致\n";
}

static void check_2d() {
    std::mt19937 rng(20261114u);
    std::uniform_int_distribution<int> pick(-20, 20);
    std::vector<std::pair<int, int>> shapes = {{1, 1}, {1, 5}, {5, 1}, {2, 3}, {4, 4}};
    for (int t = 0; t < 10; t++) {
        shapes.push_back({static_cast<int>(rng() % 5 + 1),
                          static_cast<int>(rng() % 5 + 1)});
    }
    int rects = 0;
    for (const auto& sh : shapes) {
        std::vector<std::vector<int>> m(static_cast<std::size_t>(sh.first),
                                        std::vector<int>(static_cast<std::size_t>(sh.second)));
        for (auto& row : m) for (int& x : row) x = pick(rng);
        NumMatrixBrute nb(m);
        NumMatrix nm(m);
        // preSum_ 是私有的,测试不该去掏私有成员:直接把 buildByAxis 的返回值当
        // preSum 表用,套同一套容斥公式,和暴力解比。
        const std::vector<std::vector<int>> by_axis = buildByAxis(m);
        for (int r1 = 0; r1 < sh.first; r1++) {
            for (int r2 = r1; r2 < sh.first; r2++) {
                for (int c1 = 0; c1 < sh.second; c1++) {
                    for (int c2 = c1; c2 < sh.second; c2++) {
                        int want = 0;
                        for (int i = r1; i <= r2; i++)
                            for (int j = c1; j <= c2; j++)
                                want += m[static_cast<std::size_t>(i)][static_cast<std::size_t>(j)];
                        const std::size_t a = static_cast<std::size_t>(r1);
                        const std::size_t b = static_cast<std::size_t>(c1);
                        const std::size_t c = static_cast<std::size_t>(r2);
                        const std::size_t d = static_cast<std::size_t>(c2);
                        const int via_axis = by_axis[c + 1][d + 1] - by_axis[a][d + 1] -
                                             by_axis[c + 1][b] + by_axis[a][b];
                        rects++;
                        if (nb.sumRegion(r1, c1, r2, c2) != want ||
                            nm.sumRegion(r1, c1, r2, c2) != want ||
                            via_axis != want) {
                            expect(false, "2-D mismatch");
                            return;
                        }
                    }
                }
            }
        }
    }
    expect(true, "2-D ok");
    std::cout << "  ok  [cpp] 二维:" << shapes.size() << " 种形状（含 1x1、1xN、Nx1）共 "
              << rects << " 个子矩形，容斥/逐维/暴力三者一致\n";

    NumMatrix nm(lc304());
    expect(nm.sumRegion(2, 1, 4, 3) == 8, "LC 304 (2,1,4,3) != 8");
    expect(nm.sumRegion(1, 1, 2, 2) == 11, "LC 304 (1,1,2,2) != 11");
    expect(nm.sumRegion(1, 2, 2, 4) == 12, "LC 304 (1,2,2,4) != 12");
    // 文章里 304 那张四项表的数字:拿 buildByAxis 返回的表(和私有 preSum_ 同构)查
    const std::vector<std::vector<int>> ps = buildByAxis(lc304());
    expect(ps[5][4] == 38 && ps[2][4] == 24 && ps[5][1] == 14 && ps[2][1] == 8,
           "LC 304 four-term table mismatch");
}

static void check_difference() {
    std::mt19937 rng(20261114u);
    std::uniform_int_distribution<int> pick(-30, 30);
    for (int t = 0; t < 200; t++) {
        const int n = static_cast<int>(rng() % 30 + 1);
        std::vector<int> nums(static_cast<std::size_t>(n));
        for (int& x : nums) x = pick(rng);
        DifferenceBrute db(nums);
        Difference df(nums);
        for (int u = 0; u < 8; u++) {
            const int i = static_cast<int>(rng() % static_cast<unsigned>(n));
            const int j = i + static_cast<int>(rng() % static_cast<unsigned>(n - i));
            const int val = pick(rng);
            db.increment(i, j, val);
            df.increment(i, j, val);
        }
        if (db.result() != df.result()) {
            expect(false, "Difference disagrees with DifferenceBrute");
            return;
        }
    }
    // i == j == n-1:不该出现任何 -val
    {
        Difference df({1, 2, 3});
        df.increment(2, 2, 4);
        // 只加最后一个元素:结果必须只有最后一格变了;diff_ 是私有的,不去掏
        expect(df.result() == std::vector<int>({1, 2, 7}), "last-element increment");
        DifferenceBrute db({1, 2, 3});
        db.increment(2, 2, 4);
        expect(db.result() == df.result(), "last-element: difference vs brute");
    }
    // 空数组
    {
        const std::vector<int> empty;          // 写成 Difference df(std::vector<int>()) 会被当成函数声明
        Difference df(empty);
        expect(df.result().empty(), "Difference({}) result");
    }
    // 全 0 数组:一次 [i, j] 加 v 必须只在 [i, j] 段出现 v
    for (int n = 1; n <= 6; n++) {
        for (int i = 0; i < n; i++) {
            for (int j = i; j < n; j++) {
                Difference df(std::vector<int>(static_cast<std::size_t>(n), 0));
                df.increment(i, j, 5);
                std::vector<int> want(static_cast<std::size_t>(n), 0);
                for (int k = i; k <= j; k++) want[static_cast<std::size_t>(k)] = 5;
                if (df.result() != want) {
                    expect(false, "increment semantics");
                    return;
                }
            }
        }
    }
    expect(true, "difference ok");
    std::cout << "  ok  [cpp] 差分:200 组随机用例 + 末元素/空数组/区间语义边界全过\n";

    expect(getModifiedArray(5, {{1, 3, 2}, {2, 4, 3}, {0, 2, -2}}) ==
           std::vector<int>({-2, 0, 3, 5, 3}), "LC 370 example");
    expect(getModifiedArray(0, {}) == std::vector<int>(), "LC 370 empty");
    expect(corpFlightBookings({{1, 2, 10}, {2, 3, 20}, {2, 5, 25}}, 5) ==
           std::vector<int>({10, 55, 45, 25, 25}), "LC 1109 example");
    expect(carPooling({{2, 1, 5}, {3, 3, 7}}, 4) == false, "LC 1094 #1");
    expect(carPooling({{2, 1, 5}, {3, 3, 7}}, 5) == true, "LC 1094 #2");
    expect(carPooling({{2, 1, 5}, {3, 5, 7}}, 3) == true, "LC 1094 #3");
    std::cout << "  ok  [cpp] 力扣 370 / 1109 / 1094 / 304 的示例值逐个复现\n";
}

int main() {
    check_1d();
    check_2d();
    check_difference();
    std::cout << "\n  [cpp] " << (checks - failures) << "/" << checks
              << " assertions passed\n";
    return failures == 0 ? 0 : 1;
}
"""


def compile_and_run(src, name, flags, arg_sets=([],)):
    """编译一次,按 arg_sets 跑若干次;返回 (runs, problems, warnings)。"""
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / f"{name}.cpp"
        exe = Path(td) / name
        cpp.write_text(src, encoding="utf-8")
        cp = subprocess.run(["g++", "-std=c++17", *flags, "-o", str(exe), str(cpp)],
                            capture_output=True, text=True)
        if cp.returncode != 0:
            return None, ["g++ failed:\n" + (cp.stderr or "")[:3000]], None
        warns = [l for l in cp.stderr.splitlines() if "warning:" in l]
        problems = [f"g++ warning: {w}" for w in warns]
        runs = []
        for args in arg_sets:
            r = subprocess.run([str(exe), *args], capture_output=True, text=True)
            if r.returncode != 0:
                problems.append(f"{name} {' '.join(args)} exited {r.returncode}")
            runs.append(r)
        return runs, problems, warns


def run_cpp(cpp_blocks):
    fails = []
    body = "\n".join(b for b in cpp_blocks if "int main(" not in b)
    bench = [b for b in cpp_blocks if "int main(" in b]
    if len(bench) != 1:
        fails.append(f"expected exactly one cpp block with main(), got {len(bench)}")
        return fails

    # TU1:文章所有实现 + 对拍驱动
    runs, f, warns = compile_and_run(CPP_HEAD + "\n" + body + "\n" + CPP_MAIN,
                                     "psd_test",
                                     ["-Wall", "-Wextra", "-Werror", "-O1"])
    if runs is None:
        return fails + f
    r = runs[0]
    print(f"  cpp compile   : {'clean' if not warns else str(len(warns)) + ' warnings'}"
          "  (g++ -std=c++17 -Wall -Wextra -Werror -O1)")
    print("  [cpp] start")
    print("\n".join("  " + l for l in r.stdout.strip().splitlines()))
    fails += f
    if r.stderr.strip():
        fails.append("cpp stderr: " + r.stderr.strip()[:800])

    # TU2:文章所有实现 + 第 5 节的实测脚本(--quick)
    runs2, f2, warns2 = compile_and_run(CPP_HEAD + "\n" + body + "\n" + bench[0],
                                       "psd_bench",
                                       ["-Wall", "-Wextra", "-Werror", "-O2"],
                                       arg_sets=(["--quick"], []))
    if runs2 is None:
        return fails + f2
    print(f"  cpp bench     : {'clean' if not warns2 else str(len(warns2)) + ' warnings'}"
          "  (g++ -std=c++17 -Wall -Wextra -Werror -O2, --quick 与全量各跑一次)")
    for label, r2 in zip(("--quick", "全量"), runs2):
        print(f"  [cpp bench {label}]")
        print("\n".join("  " + l for l in r2.stdout.strip().splitlines()))
        hits = r2.stdout.count("对拍一致")
        if hits != 3:
            fails.append(f"cpp bench ({label}) printed {hits} '对拍一致', want 3")
        if "结果不一致" in r2.stdout:
            fails.append(f"cpp bench ({label}) reported 结果不一致")
    fails += f2
    return fails


def main():
    if not POST.exists():
        print(f"  post not found: {POST}")
        return 1
    print(f"  post          : {POST.name}")
    py, cpp = blocks("python"), blocks("cpp")
    print(f"  blocks        : {len(py)} python / {len(cpp)} cpp")
    problems = []
    if len(py) != EXPECTED_PY or len(cpp) != EXPECTED_CPP:
        problems.append(f"expected {EXPECTED_PY} python and {EXPECTED_CPP} cpp blocks, "
                        f"got {len(py)} and {len(cpp)}")
    if len(py) != len(cpp):
        problems.append(f"python/cpp blocks unequal: {len(py)} vs {len(cpp)}")
    pf, checks = run_python(py)
    problems += pf
    problems += run_cpp(cpp)
    print()
    if problems:
        print(f"  RESULT: {len(problems)} problem(s)")
        for p in problems[:20]:
            print(f"    - {p.splitlines()[0][:160]}")
        return 1
    print(f"  CODE OK — 前缀和/二维容斥/差分三个实现都与暴力解对拍通过，"
          f"文章自己的实测脚本在 Python 与 C++ 两侧都真跑过（python {checks} 项断言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
