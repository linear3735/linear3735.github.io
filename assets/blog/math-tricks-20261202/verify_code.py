#!/usr/bin/env python3
"""Run every code block of _posts/2026-12-02-math-tricks.md, for real.

What this script does
---------------------
1. Extracts the ```python and ```cpp blocks *from the post itself* (so the
   post can never drift away from what was tested) and checks the two are
   equally many.
2. Executes the Python blocks in one namespace.
3. Compiles the C++ blocks together with a generated main() using
   `g++ -std=c++17 -Wall -Wextra -Werror` and requires zero warnings.
4. Drives both languages from the *same* case tables and diffs their output
   line by line, so "the C++ case set equals the Python case set" is not a
   promise but a byte comparison.
5. Python-only assertions that C++ cannot do by itself: fast power compared
   against `pow(a, b, m)` (big-integer truth) and against a brute-force
   repeated multiplication over every small case; prime factorisation
   re-multiplied and every factor checked with an independent Miller-Rabin;
   factorial trailing zeros compared with a materialised n!.
6. Statistical checks (chi-square) for the shuffles and the reservoir
   sampler, PLUS the deliberately broken shuffle as a control group.

The statistical part can only falsify, never prove.  The proofs are the
counting/induction arguments in the post.  This script exists to catch
implementation bugs and to show that the control group is actually rejected.

Usage:  /opt/miniconda3/bin/python3 verify_code.py [--post PATH] [--verbose]
"""

import argparse
import itertools
import math
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent
REPO = BLOG.parent.parent
DEFAULT_POST = REPO / "_posts" / "2026-12-02-math-tricks.md"

ALLOWED_LANGS = {"python", "cpp", "text", "bash", "json", "yaml"}
SEED = 20261202
Z_CRIT = 5.0          # ~3e-7 tail; a fixed seed plus a huge margin, so the
                      # result is deterministic and cannot flake.

# --------------------------------------------------------------------------
# Shared case tables: the single source of truth for BOTH languages.
# --------------------------------------------------------------------------

HAMMING = [0, 1, 2, 3, 11, 44, 128, 255, 256, 2147483645, 2 ** 31 - 1,
           2 ** 40, 2 ** 63 - 1]
POW2 = [0, 1, 2, 3, 4, 6, 8, 1024, 2 ** 20, 2 ** 31, 2 ** 62,
        -1, -2, -3, -8, -1024, -2 ** 62]
LOWBIT = [0, 1, 4, 6, 44, 128, 255, 1024, 2 ** 40, 2 ** 63]
BITS_OF = [0, 1, 6, 44, 255, 1024, 2 ** 40 + 1, 2 ** 63]
SINGLE = [[2, 2, 1], [4, 1, 2, 1, 2], [1], [7, 3, 3], [5, 5, 9, 1, 1, 2, 2],
          [0, 0, 3], [-5, -5, 4]]
MISSING = [[3, 0, 1], [0, 1], [9, 6, 4, 2, 3, 5, 7, 0, 1], [0], [1], [1, 0]]
SUBSETS = [0, 1, 5, 13, 255, 1027, 2 ** 20 - 1]
BITMAP_SIZE = 1024
BITMAP_OPS = [("add", 0), ("add", 63), ("add", 64), ("add", 65), ("remove", 64),
              ("add", 130), ("add", 200), ("add", 1000), ("remove", 200),
              ("remove", 999)]
BITMAP_QUERY = [0, 63, 64, 65, 130, 200, 999, 1000, 1001]
WEIGHTS = [1, 3, 2, 0, 4]
WEIGHTS_ZERO_FIRST = [0, 1]
SHUFFLE_N = 5
SHUFFLE_BASE = [1, 2, 3, 4, 5]
PERM_N = 4
PERM_TRIALS = 240000
RESERVOIR_STREAM_N = 10
RESERVOIR_N = 10
RESERVOIR_TRIALS_K1 = 200000
RESERVOIR_SMALL_N = 4
RESERVOIR_K2 = 2
RESERVOIR_TRIALS_K2 = 120000
WEIGHTED_TRIALS = 100000
POW_SMALL_A = list(range(-3, 13))
POW_SMALL_B = list(range(0, 13))
POW_SMALL_M = list(range(1, 14))
BIG_MUL = [(10 ** 18 - 1, 10 ** 18 - 2, 999999999999999989),
           (10 ** 18 - 3, 10 ** 9 + 7, 10 ** 9 + 7),
           (10 ** 9, 10 ** 9, 10 ** 9 + 7),
           (2 ** 40, 2 ** 40, 1000000007),
           (123456789012345678, 987654321098765432, 1000000007)]
INV_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 97, 1000000007]
INV_AS = list(range(-5, 21))
INV_COMPOSITE = [(8, 3), (9, 2), (10, 3), (12, 5), (100, 7)]
FACTORS = [-5, 0, 1, 2, 3, 4, 12, 97, 100, 360, 1024, 999983, 1000003,
           2147483647, 600851475143, 10 ** 12, 999999999989]
GCD_PAIRS = [(12, 18), (0, 5), (5, 0), (0, 0), (-12, 18), (12, -18),
             (-12, -18), (7, 13), (48, 18), (1, 1), (10 ** 9, 5 * 10 ** 8),
             (2 ** 31, 3 * 2 ** 30)]
LCM_PAIRS = [(12, 18), (0, 5), (5, 0), (0, 0), (-12, 18), (7, 13), (48, 18),
             (10 ** 9, 5 * 10 ** 8), (2 ** 31, 3 * 2 ** 30)]
PRIME_CASES = [-5, 0, 1, 2, 3, 4, 9, 25, 49, 97, 100, 1024, 2147483647,
               2147483646, 999983, 1000003, 999999999989]
TRAILING = [-1, 0, 1, 4, 5, 10, 24, 25, 100, 125, 500, 625, 1000, 10 ** 6,
            10 ** 9, 10 ** 12]
RESERVOIR_SHORT = [([1, 2, 3], 5), ([7], 3), ([1, 2], 0), ([], 2), ([4, 4], 2)]


def _big_pow_cases():
    """(a, b, m) triples with m <= 1e9, because the post's pow_mod keeps
    intermediate products in long long (see the post's overflow section)."""
    out = [(2, 0, 1), (0, 0, 1), (0, 5, 7), (1, 10 ** 18, 1000000007),
           (1000000006, 1000000006, 1000000007), (7, 10 ** 18, 999999937)]
    x = 1234567890123456789
    for _ in range(18):
        vals = []
        for _ in range(3):
            x = (x * 6364136223846793005 + 1442695040888963407) % (2 ** 63)
            vals.append(x)
        a = vals[0] % (10 ** 9)
        b = vals[1] % (10 ** 18)
        m = 2 + vals[2] % (10 ** 9 - 1)
        out.append((a, b, m))
    return out


BIG_POW = _big_pow_cases()


# --------------------------------------------------------------------------
# helpers mirrored 1:1 in the generated C++ main
# --------------------------------------------------------------------------

def jl(vs):
    return "[" + ",".join(str(v) for v in vs) + "]"


def b01(x):
    return "1" if x else "0"


def pow_brute(a, n, m):
    r = 1 % m
    for _ in range(n):
        r = r * a % m
    return r


def chi2_crit(df, z=Z_CRIT):
    """Wilson-Hilferty approximation, so no chi-square table is needed."""
    d = float(df)
    t = 1.0 - 2.0 / (9.0 * d) + z * math.sqrt(2.0 / (9.0 * d))
    return d * t * t * t


def chi2_stat(counts):
    n = sum(counts)
    e = n / len(counts)
    return sum((c - e) ** 2 / e for c in counts)


def perm_code(a):
    code = 0
    for v in a:
        code = code * len(a) + v
    return code


def all_perm_codes(n):
    return sorted(perm_code(p) for p in itertools.permutations(range(n)))


def naive_index_of(w, u):
    """The plain 'walk the cumulative intervals' implementation."""
    acc = 0
    for i, x in enumerate(w):
        acc += x
        if u < acc:
            return i
    return -1


def is_prime_mr(n):
    """Independent reference (Miller-Rabin), not the post's trial division."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


# --------------------------------------------------------------------------
# 1. extract the code blocks from the post
# --------------------------------------------------------------------------

def extract_blocks(text):
    blocks = []
    lang = None
    buf = []
    for line in text.splitlines():
        if lang is None:
            m = re.match(r"^```([A-Za-z0-9_+-]*)\s*$", line)
            if m:
                lang = m.group(1)
                buf = []
        else:
            if re.match(r"^```\s*$", line):
                blocks.append((lang, "\n".join(buf)))
                lang = None
            else:
                buf.append(line)
    if lang is not None:
        raise SystemExit("FAIL  unbalanced code fence (language %r)" % lang)
    return blocks


# --------------------------------------------------------------------------
# 2. Python side: one namespace, same case tables as the C++
# --------------------------------------------------------------------------

def python_case_lines(ns):
    """Everything both languages can check with their own means."""
    out = []

    def emit(s):
        out.append(s)

    emit("#1 hamming_weight / is_power_of_two")
    for n in HAMMING:
        emit("hamming_weight(%d)=%d" % (n, ns["hamming_weight"](n)))
    for n in POW2:
        emit("is_power_of_two(%d)=%s" % (n, b01(ns["is_power_of_two"](n))))

    emit("#2 lowbit / bits_of")
    for n in LOWBIT:
        emit("lowbit(%d)=%d" % (n, ns["lowbit"](n)))
    for n in BITS_OF:
        emit("bits_of(%d)=%s" % (n, jl(ns["bits_of"](n))))

    emit("#3 xor")
    for v in SINGLE:
        emit("single_number(%s)=%d" % (jl(v), ns["single_number"](list(v))))
    for v in MISSING:
        emit("missing_number(%s)=%d" % (jl(v), ns["missing_number"](list(v))))

    emit("#4 subsets_of_mask")
    for m in SUBSETS:
        emit("subsets_of_mask(%d)=%s" % (m, jl(ns["subsets_of_mask"](m))))

    emit("#5 bitmap")
    bm = ns["Bitmap"](BITMAP_SIZE)
    model = set()
    for op, i in BITMAP_OPS:
        if op == "add":
            bm.add(i)
            model.add(i)
        else:
            bm.remove(i)
            model.discard(i)
    emit("bitmap.ones=%s" % jl(bm.ones()))
    emit("bitmap_vs_set_ok=%s" % b01(bm.ones() == sorted(model)))
    for i in BITMAP_QUERY:
        emit("bitmap.contains(%d)=%s" % (i, b01(bm.contains(i))))

    emit("#6 shuffle / reservoir (deterministic parts)")
    rng = random.Random(SEED)
    ok = True
    moved = False
    for _ in range(200):
        a = list(SHUFFLE_BASE)
        ns["shuffle"](a, rng)
        ok = ok and sorted(a) == sorted(SHUFFLE_BASE)
        moved = moved or a != SHUFFLE_BASE
    emit("shuffle_multiset_ok=%s" % b01(ok))
    emit("shuffle_moves_ok=%s" % b01(moved))
    for stream, k in RESERVOIR_SHORT:
        emit("reservoir_sample(%s,%d)=%s"
             % (jl(stream), k, jl(ns["reservoir_sample"](list(stream), k, rng))))
    emit("reservoir_single_element=%s"
         % jl(ns["reservoir_sample"]([7], 1, rng)))

    emit("#7 weighted picker (exhaustive over u)")
    wp = ns["WeightedPicker"](WEIGHTS)
    counts = [0] * len(WEIGHTS)
    exhaustive_ok = True
    naive_ok = True
    for u in range(wp.total):
        i = wp.index_of(u)
        if i < 0 or i >= len(WEIGHTS):
            exhaustive_ok = False
            continue
        counts[i] += 1
        if i != naive_index_of(WEIGHTS, u):
            naive_ok = False
    emit("weighted_counts=%s" % ",".join(str(c) for c in counts))
    emit("weighted_counts_match_weights=%s" % b01(counts == WEIGHTS))
    emit("weighted_exhaustive_ok=%s" % b01(exhaustive_ok))
    emit("weighted_vs_naive_ok=%s" % b01(naive_ok))
    emit("weighted_zero_weight_never=%s" % b01(counts[3] == 0))
    emit("weighted_index_of_total=%d" % ns["WeightedPicker"](WEIGHTS).index_of(10))
    zp = ns["WeightedPicker"](WEIGHTS_ZERO_FIRST)
    emit("weighted_zero_first_index_of_0=%d" % zp.index_of(0))
    for name, bad in (("empty", []), ("negative", [1, -1]), ("allzero", [0, 0])):
        try:
            ns["WeightedPicker"](bad)
            emit("weighted_reject_%s=0" % name)
        except ValueError:
            emit("weighted_reject_%s=1" % name)

    emit("#8 fast power: small exhaustive cases (self-checked)")
    small_cases = 0
    small_bad = 0
    rec_bad = 0
    mul_bad = 0
    for a in POW_SMALL_A:
        for b in POW_SMALL_B:
            for m in POW_SMALL_M:
                small_cases += 1
                truth = pow_brute(a, b, m)
                if ns["pow_mod"](a, b, m) != truth:
                    small_bad += 1
                if ns["pow_mod_rec"](a, b, m) != truth:
                    rec_bad += 1
                if ns["mul_mod"](a, b, m) != a * b % m:
                    mul_bad += 1
    emit("powmod_small_cases=%d" % small_cases)
    emit("powmod_small_mismatch=%d" % small_bad)
    emit("powmod_rec_small_mismatch=%d" % rec_bad)
    emit("mulmod_small_mismatch=%d" % mul_bad)

    emit("#9 fast power: big exponents (values, checked by the diff)")
    for a, b, m in BIG_POW:
        emit("pow_mod(%d,%d,%d)=%d" % (a, b, m, ns["pow_mod"](a, b, m)))
        emit("pow_mod_rec(%d,%d,%d)=%d" % (a, b, m, ns["pow_mod_rec"](a, b, m)))
    for a, b, m in BIG_MUL:
        emit("mul_mod(%d,%d,%d)=%d" % (a, b, m, ns["mul_mod"](a, b, m)))
        wrapped = ((a * b) % (2 ** 64)) % m
        emit("mul_mod_64bit_wrap(%d,%d,%d)=%d" % (a, b, m, wrapped))
        emit("mul_mod_wrap_differs(%d,%d,%d)=%s"
             % (a, b, m, b01(wrapped != a * b % m)))

    emit("#10 mod inverse (Fermat, prime moduli only)")
    for m in INV_PRIMES:
        for a in INV_AS:
            v = ns["mod_inverse"](a, m)
            emit("mod_inverse(%d,%d)=%d" % (a, m, -1 if v is None else v))
    for m, a in INV_COMPOSITE:
        v = ns["mod_inverse"](a, m)
        emit("mod_inverse(%d,%d)=%d" % (a, m, -1 if v is None else v))

    emit("#11 prime factorisation")
    for n in FACTORS:
        emit("prime_factors(%d)=%s" % (n, jl(ns["prime_factors"](n))))

    emit("#12 gcd / lcm")
    for a, b in GCD_PAIRS:
        emit("gcd_euclid(%d,%d)=%d" % (a, b, ns["gcd_euclid"](a, b)))
    for a, b in LCM_PAIRS:
        emit("lcm_(%d,%d)=%d" % (a, b, ns["lcm_"](a, b)))

    emit("#13 is_prime")
    for n in PRIME_CASES:
        emit("is_prime(%d)=%s" % (n, b01(ns["is_prime"](n))))

    emit("#14 trailing zeros of n!")
    for n in TRAILING:
        emit("trailing_zeros_factorial(%d)=%d"
             % (n, ns["trailing_zeros_factorial"](n)))
    return out


def python_only_assertions(ns, fails):
    """Checks C++ cannot make on its own (needs big integers)."""
    print("== 4. Python 侧独立断言(需要大整数,不参与逐行对拍) ==")
    bad = 0
    for a, b, m in BIG_POW:
        truth = pow(a, b, m)
        for name in ("pow_mod", "pow_mod_rec"):
            got = ns[name](a, b, m)
            if got != truth:
                bad += 1
                print("  !! %s(%d,%d,%d)=%d,真值 %d" % (name, a, b, m, got, truth))
    print("  快速幂 大指数 %d 例,与 Python 内置 pow(a,b,m) 的差异:%d"
          % (len(BIG_POW) * 2, bad))
    assert bad == 0, "fast power disagrees with pow(a,b,m)"

    mul_bad = 0
    for a, b, m in BIG_MUL:
        if ns["mul_mod"](a, b, m) != a * b % m:
            mul_bad += 1
    print("  __int128 版乘法 %d 例,与 Python 大整数乘法的差异:%d"
          % (len(BIG_MUL), mul_bad))
    assert mul_bad == 0

    # brute force interlock: every small case against repeated multiplication
    brute_bad = 0
    for a in POW_SMALL_A:
        for b in POW_SMALL_B:
            for m in POW_SMALL_M:
                if pow_brute(a, b, m) != pow(a, b, m):
                    brute_bad += 1
    print("  暴力连乘 %d 例,与内置 pow 的差异:%d"
          % (len(POW_SMALL_A) * len(POW_SMALL_B) * len(POW_SMALL_M), brute_bad))
    assert brute_bad == 0

    # factorisation: multiply back + independent primality test
    fac_bad = 0
    for n in FACTORS:
        fs = ns["prime_factors"](n)
        if n < 2:
            fac_bad += (fs != [])
            continue
        prod = 1
        for f in fs:
            prod *= f
        if prod != n or sorted(fs) != fs or not all(is_prime_mr(f) for f in fs):
            fac_bad += 1
            print("  !! prime_factors(%d)=%s 复核失败" % (n, fs))
    print("  质因数分解 %d 例:乘回原数 + Miller-Rabin 独立复核,失败 %d"
          % (len(FACTORS), fac_bad))
    assert fac_bad == 0

    # is_prime against Miller-Rabin
    pr_bad = sum(1 for n in PRIME_CASES if ns["is_prime"](n) != is_prime_mr(n))
    print("  is_prime %d 例,与 Miller-Rabin 的差异:%d" % (len(PRIME_CASES), pr_bad))
    assert pr_bad == 0

    # gcd / lcm against math.gcd and the exact integer formula
    gl_bad = 0
    for a, b in GCD_PAIRS:
        if ns["gcd_euclid"](a, b) != math.gcd(a, b):
            gl_bad += 1
    for a, b in LCM_PAIRS:
        want = 0 if (a == 0 or b == 0) else abs(a * b) // math.gcd(a, b)
        if ns["lcm_"](a, b) != want:
            gl_bad += 1
    print("  gcd/lcm %d 例,与 math.gcd / 精确公式的差异:%d"
          % (len(GCD_PAIRS) + len(LCM_PAIRS), gl_bad))
    assert gl_bad == 0

    # trailing zeros against a materialised factorial
    tz_bad = 0
    for n in TRAILING:
        if not 0 <= n <= 500:
            continue
        f = math.factorial(n)
        want = 0
        while f % 10 == 0:
            f //= 10
            want += 1
        if ns["trailing_zeros_factorial"](n) != want:
            tz_bad += 1
    print("  阶乘尾零:0..500 里与真实 n! 逐位对比,差异:%d" % tz_bad)
    assert tz_bad == 0

    # closed form for n = 5^k: exactly (n-1)/4 trailing zeros
    cf_bad = 0
    for k in range(1, 13):
        n = 5 ** k
        if ns["trailing_zeros_factorial"](n) != (n - 1) // 4:
            cf_bad += 1
    print("  n = 5^k (k=1..12) 与闭式 (n-1)/4 对比,差异:%d" % cf_bad)
    assert cf_bad == 0

    # mod inverse: verify a * a^-1 == 1 (mod m) on primes; and show that the
    # same formula is simply WRONG on a composite modulus
    inv_bad = 0
    for m in INV_PRIMES:
        for a in INV_AS:
            v = ns["mod_inverse"](a, m)
            if math.gcd(a % m, m) != 1:
                if v is not None:
                    inv_bad += 1
            elif v is None or (a * v) % m != 1 % m:
                inv_bad += 1
    print("  模逆 %d 例:a·a⁻¹ ≡ 1 (mod m) 全部成立,失败 %d"
          % (len(INV_PRIMES) * len(INV_AS), inv_bad))
    assert inv_bad == 0
    print("  合数模的反例(gcd 都为 1,但 m 不是质数,所以 m-2 这个指数不成立):")
    for m, a, real in ((8, 3, 3), (9, 2, 5), (10, 3, 7), (14, 5, 3)):
        fermat = ns["pow_mod"](a, m - 2, m)
        print("    m=%2d, a=%d 时 a^(m-2) mod m = %d,而真实的逆元是 %d → %s"
              % (m, a, fermat, real,
                 "错了" if fermat != real else "碰巧对"))
        assert (a * real) % m == 1 % m, "the 'real' inverse must really be one"
        assert fermat != real, "counterexample should NOT be a correct inverse"

    # subset enumeration: exhaustive against itertools
    sub_bad = 0
    for mask in SUBSETS:
        want = sorted((s for s in range(mask + 1) if s & mask == s), reverse=True)
        if ns["subsets_of_mask"](mask) != want:
            sub_bad += 1
    print("  二进制枚举子集 %d 例,与按位穷举的集合对比,失败 %d"
          % (len(SUBSETS), sub_bad))
    assert sub_bad == 0

    # bit tricks against naive definitions
    bit_bad = 0
    for n in HAMMING:
        if ns["hamming_weight"](n) != bin(n).count("1"):
            bit_bad += 1
    for n in POW2:
        want = n > 0 and bin(n).count("1") == 1
        if ns["is_power_of_two"](n) != want:
            bit_bad += 1
    for n in SINGLE:
        want = 0
        for v in n:
            want ^= v
        naive = [v for v in set(n) if n.count(v) % 2 == 1]
        if len(naive) == 1 and ns["single_number"](list(n)) != naive[0]:
            bit_bad += 1
    for v in MISSING:
        n = len(v)
        want = (set(range(n + 1)) - set(v)).pop()
        if ns["missing_number"](list(v)) != want:
            bit_bad += 1
    print("  位运算 4 组共 %d 例,与朴素定义(Counter/set/集合差)对比,失败 %d"
          % (len(HAMMING) + len(POW2) + len(SINGLE) + len(MISSING), bit_bad))
    assert bit_bad == 0

    if fails:
        print("  (前面已有 %d 项失败)" % len(fails))


def statistical_checks(ns, cpp):
    """Chi-square checks on BOTH implementations.

    `cpp` holds the raw bucket counts printed by the C++ binary in `stats`
    mode, so the C++ code is tested against the same law, not merely against
    Python's numbers.  A chi-square test can only falsify an implementation,
    and only with high probability - the proofs live in the post.
    """
    print("== 5. 统计检验(卡方;只能证伪,不能证明) ==")
    rng = random.Random(SEED)
    base = list(range(PERM_N))
    codes = all_perm_codes(PERM_N)
    df = len(codes) - 1
    crit = chi2_crit(df)

    py_perm = {c: 0 for c in codes}
    for _ in range(PERM_TRIALS):
        a = base[:]
        ns["shuffle"](a, rng)
        py_perm[perm_code(a)] += 1
    py_buggy = {c: 0 for c in codes}
    for _ in range(PERM_TRIALS):
        a = base[:]
        for i in range(PERM_N):
            j = rng.randrange(PERM_N)
            a[i], a[j] = a[j], a[i]
        py_buggy[perm_code(a)] += 1

    print("  洗牌(n=%d,%d 个排列,每格期望 %d 次,各 %d 轮):"
          % (PERM_N, len(codes), PERM_TRIALS // len(codes), PERM_TRIALS))
    for who, counts in (("Python", [py_perm[c] for c in codes]),
                        ("C++   ", [cpp["shuffle_perm"][c] for c in codes])):
        stat = chi2_stat(counts)
        print("    %s 卡方 = %8.1f(自由度 %d,临界值 %.1f)→ %s"
              % (who, stat, df, crit, "通过" if stat < crit else "被拒绝"))
        assert stat < crit, "%s shuffle rejected by chi-square" % who

    print("  对照组(每轮与任意位置交换的错误写法,必须被拒绝才算检验有效):")
    for who, counts in (("Python", [py_buggy[c] for c in codes]),
                        ("C++   ", [cpp["shuffle_buggy"][c] for c in codes])):
        stat = chi2_stat(counts)
        print("    %s 卡方 = %8.1f(临界值 %.1f)→ %s"
              % (who, stat, crit,
                 "被拒绝(符合预期)" if stat > crit else "没被拒绝(检验无效)"))
        assert stat > crit, "%s control group must be rejected" % who

    r1 = random.Random(SEED + 1)
    py_k1 = [0] * RESERVOIR_N
    for _ in range(RESERVOIR_TRIALS_K1):
        s = ns["reservoir_sample"](list(range(RESERVOIR_N)), 1, r1)
        py_k1[s[0]] += 1
    c1 = chi2_crit(RESERVOIR_N - 1)
    print("  水塘抽样(k=1, n=%d, %d 次,每个下标的真实概率 1/%d = %.3f):"
          % (RESERVOIR_N, RESERVOIR_TRIALS_K1, RESERVOIR_N, 1.0 / RESERVOIR_N))
    for who, counts in (("Python", py_k1), ("C++   ", cpp["reservoir_k1"])):
        stat = chi2_stat(counts)
        print("    %s 卡方 = %8.1f(自由度 %d,临界值 %.1f)→ %s"
              % (who, stat, RESERVOIR_N - 1, c1, "通过" if stat < c1 else "被拒绝"))
        assert stat < c1, "%s reservoir k=1 rejected" % who

    r2 = random.Random(SEED + 2)
    sub_codes = sorted({perm_code(sorted(c)) for c in
                        itertools.combinations(range(RESERVOIR_SMALL_N),
                                               RESERVOIR_K2)})
    py_k2 = {c: 0 for c in sub_codes}
    for _ in range(RESERVOIR_TRIALS_K2):
        s = ns["reservoir_sample"](list(range(RESERVOIR_SMALL_N)), RESERVOIR_K2, r2)
        py_k2[perm_code(sorted(s))] += 1
    c2 = chi2_crit(len(sub_codes) - 1)
    print("  水塘抽样(k=%d, n=%d, %d 次,%d 个 2 元子集,每个子集真实概率 1/%d):"
          % (RESERVOIR_K2, RESERVOIR_SMALL_N, RESERVOIR_TRIALS_K2,
             len(sub_codes), len(sub_codes)))
    for who, counts in (("Python", [py_k2[c] for c in sub_codes]),
                        ("C++   ", [cpp["reservoir_k2"][c] for c in sub_codes])):
        stat = chi2_stat(counts)
        print("    %s 卡方 = %8.1f(自由度 %d,临界值 %.1f)→ %s"
              % (who, stat, len(sub_codes) - 1, c2,
                 "通过" if stat < c2 else "被拒绝"))
        assert stat < c2, "%s reservoir subset uniformity rejected" % who

    wp = ns["WeightedPicker"](WEIGHTS)
    r3 = random.Random(SEED + 3)
    py_w = [0] * len(WEIGHTS)
    for _ in range(WEIGHTED_TRIALS):
        py_w[wp.pick(r3)] += 1
    expect = [WEIGHTED_TRIALS * w / wp.total for w in WEIGHTS]
    live = [i for i in range(len(WEIGHTS)) if WEIGHTS[i] > 0]
    c3 = chi2_crit(len(live) - 1)
    print("  带权随机(%d 次,权重 %s,期望次数 %s):"
          % (WEIGHTED_TRIALS, WEIGHTS, [round(e, 1) for e in expect]))
    for who, counts in (("Python", py_w), ("C++   ", cpp["weighted"])):
        stat = sum((counts[i] - expect[i]) ** 2 / expect[i] for i in live)
        print("    %s 卡方 = %8.1f(自由度 %d,临界值 %.1f)→ %s;权重 0 的下标出现 %d 次"
              % (who, stat, len(live) - 1, c3,
                 "通过" if stat < c3 else "被拒绝", counts[3]))
        assert stat < c3 and counts[3] == 0, "%s weighted picker rejected" % who


# --------------------------------------------------------------------------
# 3. C++ side: post blocks + a generated main driven by the same tables
# --------------------------------------------------------------------------

CPP_MAIN = r"""
// ================= generated harness: same case tables as the Python side
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

static std::string jl_ll(const std::vector<long long>& v) {
    std::string s = "[";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += std::to_string(v[i]);
    }
    return s + "]";
}
static std::string jl_int(const std::vector<int>& v) {
    std::string s = "[";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += std::to_string(v[i]);
    }
    return s + "]";
}
static std::string jl_ull(const std::vector<unsigned long long>& v) {
    std::string s = "[";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i) s += ",";
        s += std::to_string(v[i]);
    }
    return s + "]";
}
static std::string b01(bool b) { return b ? "1" : "0"; }

static long long pow_brute(long long a, long long n, long long m) {
    long long r = 1 % m;
    for (long long i = 0; i < n; ++i) r = ((r * a % m) + m) % m;
    return r;
}
static int perm_code(const std::vector<int>& a) {
    int code = 0;
    for (int v : a) code = code * static_cast<int>(a.size()) + v;
    return code;
}
static void print_counts(const char* name, const std::vector<long long>& v) {
    std::cout << "#S " << name << "=";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << v[i];
    }
    std::cout << "\n";
}
static int naive_index_of(const std::vector<long long>& w, long long u) {
    long long acc = 0;
    for (std::size_t i = 0; i < w.size(); ++i) {
        acc += w[i];
        if (u < acc) return static_cast<int>(i);
    }
    return -1;
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "stats") {
        // Counting mode: emit raw bucket counts so the Python side can run the
        // chi-square test on THIS implementation too (different RNG, same law).
        const int n = @PERM_N@;
        std::vector<int> base(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i) base[static_cast<std::size_t>(i)] = i;
        std::mt19937_64 rng(@SEED@ULL);
        std::vector<long long> good(@PERM_CELLS@, 0), bad(@PERM_CELLS@, 0);
        for (long long t = 0; t < @PERM_TRIALS@; ++t) {
            std::vector<int> a = base;
            shuffle(a, rng);
            good[static_cast<std::size_t>(perm_code(a))] += 1;
            std::vector<int> b = base;
            for (int i = 0; i < n; ++i) {
                std::uniform_int_distribution<int> d(0, n - 1);
                int j = d(rng);
                std::swap(b[static_cast<std::size_t>(i)],
                          b[static_cast<std::size_t>(j)]);
            }
            bad[static_cast<std::size_t>(perm_code(b))] += 1;
        }
        print_counts("shuffle_perm", good);
        print_counts("shuffle_buggy", bad);
        std::vector<long long> k1(@RESERVOIR_N@, 0);
        for (long long t = 0; t < @RESERVOIR_TRIALS_K1@; ++t) {
            std::vector<int> stream(@RESERVOIR_N@);
            for (int i = 0; i < @RESERVOIR_N@; ++i) stream[static_cast<std::size_t>(i)] = i;
            std::vector<int> s = reservoir_sample(stream, 1, rng);
            k1[static_cast<std::size_t>(s[0])] += 1;
        }
        print_counts("reservoir_k1", k1);
        std::vector<long long> k2(@RESERVOIR_SMALL_N@ * @RESERVOIR_SMALL_N@ + 1, 0);
        for (long long t = 0; t < @RESERVOIR_TRIALS_K2@; ++t) {
            std::vector<int> stream(@RESERVOIR_SMALL_N@);
            for (int i = 0; i < @RESERVOIR_SMALL_N@; ++i) stream[static_cast<std::size_t>(i)] = i;
            std::vector<int> s = reservoir_sample(stream, @RESERVOIR_K2@, rng);
            std::sort(s.begin(), s.end());
            k2[static_cast<std::size_t>(perm_code(s))] += 1;
        }
        print_counts("reservoir_k2", k2);
        WeightedPicker wp(std::vector<long long>{@WEIGHTS@});
        std::vector<long long> wf(@WEIGHTS_LEN@, 0);
        for (long long t = 0; t < @WEIGHTED_TRIALS@; ++t)
            wf[static_cast<std::size_t>(wp.pick(rng))] += 1;
        print_counts("weighted", wf);
        return 0;
    }
    std::cout << "#1 hamming_weight / is_power_of_two\n";
    {
        const unsigned long long cases[] = {@HAMMING@};
        for (unsigned long long n : cases)
            std::cout << "hamming_weight(" << n << ")=" << hamming_weight(n) << "\n";
    }
    {
        const long long cases[] = {@POW2@};
        for (long long n : cases)
            std::cout << "is_power_of_two(" << n << ")=" << b01(is_power_of_two(n))
                      << "\n";
    }
    std::cout << "#2 lowbit / bits_of\n";
    {
        const unsigned long long cases[] = {@LOWBIT@};
        for (unsigned long long n : cases)
            std::cout << "lowbit(" << n << ")=" << lowbit(n) << "\n";
    }
    {
        const unsigned long long cases[] = {@BITS_OF@};
        for (unsigned long long n : cases)
            std::cout << "bits_of(" << n << ")=" << jl_int(bits_of(n)) << "\n";
    }
    std::cout << "#3 xor\n";
    {
        const std::vector<std::vector<int>> cases = {@SINGLE@};
        for (const std::vector<int>& v : cases)
            std::cout << "single_number(" << jl_int(v) << ")=" << single_number(v)
                      << "\n";
    }
    {
        const std::vector<std::vector<int>> cases = {@MISSING@};
        for (const std::vector<int>& v : cases)
            std::cout << "missing_number(" << jl_int(v) << ")=" << missing_number(v)
                      << "\n";
    }
    std::cout << "#4 subsets_of_mask\n";
    {
        const unsigned long long cases[] = {@SUBSETS@};
        for (unsigned long long m : cases)
            std::cout << "subsets_of_mask(" << m << ")=" << jl_ull(subsets_of_mask(m))
                      << "\n";
    }
    std::cout << "#5 bitmap\n";
    {
        Bitmap bm(@BITMAP_SIZE@);
        std::set<int> model;
        @BITMAP_OPS@
        std::cout << "bitmap.ones=" << jl_int(bm.ones()) << "\n";
        std::vector<int> want(model.begin(), model.end());
        std::cout << "bitmap_vs_set_ok=" << b01(bm.ones() == want) << "\n";
        const int queries[] = {@BITMAP_QUERY@};
        for (int i : queries)
            std::cout << "bitmap.contains(" << i << ")=" << b01(bm.contains(i))
                      << "\n";
    }
    std::cout << "#6 shuffle / reservoir (deterministic parts)\n";
    {
        std::mt19937_64 rng(@SEED@ULL);
        bool ok = true, moved = false;
        const std::vector<int> base = @SHUFFLE_BASE@;
        for (int round = 0; round < 200; ++round) {
            std::vector<int> a = base;
            shuffle(a, rng);
            std::vector<int> s = a;
            std::sort(s.begin(), s.end());
            ok = ok && (s == base);
            moved = moved || (a != base);
        }
        std::cout << "shuffle_multiset_ok=" << b01(ok) << "\n";
        std::cout << "shuffle_moves_ok=" << b01(moved) << "\n";
        @RESERVOIR_SHORT@
        std::cout << "reservoir_single_element="
                  << jl_int(reservoir_sample(std::vector<int>{7}, 1, rng)) << "\n";
    }
    std::cout << "#7 weighted picker (exhaustive over u)\n";
    {
        const std::vector<long long> w = @WEIGHTS@;
        WeightedPicker wp(w);
        std::vector<long long> counts(w.size(), 0);
        bool exhaustive_ok = true, naive_ok = true;
        for (long long u = 0; u < wp.total(); ++u) {
            int i = wp.index_of(u);
            if (i < 0 || i >= static_cast<int>(w.size())) { exhaustive_ok = false; continue; }
            counts[static_cast<std::size_t>(i)] += 1;
            if (i != naive_index_of(w, u)) naive_ok = false;
        }
        std::cout << "weighted_counts=";
        for (std::size_t i = 0; i < counts.size(); ++i) {
            if (i) std::cout << ",";
            std::cout << counts[i];
        }
        std::cout << "\n";
        std::cout << "weighted_counts_match_weights=" << b01(counts == w) << "\n";
        std::cout << "weighted_exhaustive_ok=" << b01(exhaustive_ok) << "\n";
        std::cout << "weighted_vs_naive_ok=" << b01(naive_ok) << "\n";
        std::cout << "weighted_zero_weight_never=" << b01(counts[3] == 0) << "\n";
        std::cout << "weighted_index_of_total=" << wp.index_of(10) << "\n";
        WeightedPicker zp(std::vector<long long>{0, 1});
        std::cout << "weighted_zero_first_index_of_0=" << zp.index_of(0) << "\n";
        const std::vector<std::vector<long long>> bads = {{}, {1, -1}, {0, 0}};
        const char* names[] = {"empty", "negative", "allzero"};
        for (std::size_t k = 0; k < bads.size(); ++k) {
            bool rejected = false;
            try { WeightedPicker bad(bads[k]); }
            catch (const std::invalid_argument&) { rejected = true; }
            std::cout << "weighted_reject_" << names[k] << "=" << b01(rejected)
                      << "\n";
        }
    }
    std::cout << "#8 fast power: small exhaustive cases (self-checked)\n";
    {
        long long cases = 0, small_bad = 0, rec_bad = 0, mul_bad = 0;
        const long long as[] = {@POW_SMALL_A@};
        const long long bs[] = {@POW_SMALL_B@};
        const long long ms[] = {@POW_SMALL_M@};
        for (long long a : as)
            for (long long b : bs)
                for (long long m : ms) {
                    ++cases;
                    long long truth = pow_brute(a, b, m);
                    if (pow_mod(a, b, m) != truth) ++small_bad;
                    if (pow_mod_rec(a, b, m) != truth) ++rec_bad;
                    if (mul_mod(a, b, m) != ((a % m + m) % m) * ((b % m + m) % m) % m)
                        ++mul_bad;
                }
        std::cout << "powmod_small_cases=" << cases << "\n";
        std::cout << "powmod_small_mismatch=" << small_bad << "\n";
        std::cout << "powmod_rec_small_mismatch=" << rec_bad << "\n";
        std::cout << "mulmod_small_mismatch=" << mul_bad << "\n";
    }
    std::cout << "#9 fast power: big exponents (values, checked by the diff)\n";
    {
        const long long triples[][3] = {@BIG_POW@};
        for (const auto& t : triples) {
            std::cout << "pow_mod(" << t[0] << "," << t[1] << "," << t[2] << ")="
                      << pow_mod(t[0], t[1], t[2]) << "\n";
            std::cout << "pow_mod_rec(" << t[0] << "," << t[1] << "," << t[2] << ")="
                      << pow_mod_rec(t[0], t[1], t[2]) << "\n";
        }
        const long long triples2[][3] = {@BIG_MUL@};
        for (const auto& t : triples2) {
            long long a = t[0], b = t[1], m = t[2];
            long long wrapped = static_cast<long long>(
                (static_cast<unsigned long long>(a) *
                 static_cast<unsigned long long>(b)) %
                static_cast<unsigned long long>(m));
            std::cout << "mul_mod(" << a << "," << b << "," << m << ")="
                      << mul_mod(a, b, m) << "\n";
            std::cout << "mul_mod_64bit_wrap(" << a << "," << b << "," << m << ")="
                      << wrapped << "\n";
            std::cout << "mul_mod_wrap_differs(" << a << "," << b << "," << m << ")="
                      << b01(wrapped != mul_mod(a, b, m)) << "\n";
        }
    }
    std::cout << "#10 mod inverse (Fermat, prime moduli only)\n";
    {
        const long long primes[] = {@INV_PRIMES@};
        const long long as[] = {@INV_AS@};
        for (long long m : primes)
            for (long long a : as)
                std::cout << "mod_inverse(" << a << "," << m << ")="
                          << mod_inverse(a, m) << "\n";
        const long long comp[][2] = {@INV_COMPOSITE@};
        for (const auto& c : comp)
            std::cout << "mod_inverse(" << c[1] << "," << c[0] << ")="
                      << mod_inverse(c[1], c[0]) << "\n";
    }
    std::cout << "#11 prime factorisation\n";
    {
        const long long cases[] = {@FACTORS@};
        for (long long n : cases)
            std::cout << "prime_factors(" << n << ")=" << jl_ll(prime_factors(n))
                      << "\n";
    }
    std::cout << "#12 gcd / lcm\n";
    {
        const long long pairs[][2] = {@GCD_PAIRS@};
        for (const auto& p : pairs)
            std::cout << "gcd_euclid(" << p[0] << "," << p[1] << ")="
                      << gcd_euclid(p[0], p[1]) << "\n";
        const long long lpairs[][2] = {@LCM_PAIRS@};
        for (const auto& p : lpairs)
            std::cout << "lcm_(" << p[0] << "," << p[1] << ")="
                      << lcm_(p[0], p[1]) << "\n";
    }
    std::cout << "#13 is_prime\n";
    {
        const long long cases[] = {@PRIME_CASES@};
        for (long long n : cases)
            std::cout << "is_prime(" << n << ")=" << b01(is_prime(n)) << "\n";
    }
    std::cout << "#14 trailing zeros of n!\n";
    {
        const long long cases[] = {@TRAILING@};
        for (long long n : cases)
            std::cout << "trailing_zeros_factorial(" << n << ")="
                      << trailing_zeros_factorial(n) << "\n";
    }
    return 0;
}
"""


def cpp_literal_list(xs):
    return ", ".join(str(x) for x in xs)


def cpp_literal_ull(xs):
    return ", ".join("%dULL" % x for x in xs)


def cpp_literal_pairs(pairs):
    return ", ".join("{%d, %d}" % (a, b) for a, b in pairs)


def cpp_literal_vecs(vecs):
    return ", ".join("{" + ",".join(str(v) for v in vec) + "}" for vec in vecs)


def cpp_literal_triples(triples):
    return ", ".join("{%d, %d, %d}" % t for t in triples)


def cpp_bitmap_ops():
    lines = []
    for op, i in BITMAP_OPS:
        if op == "add":
            lines.append("bm.add(%d); model.insert(%d);" % (i, i))
        else:
            lines.append("bm.remove(%d); model.erase(%d);" % (i, i))
    return "\n        ".join(lines)


def cpp_reservoir_short():
    lines = []
    for stream, k in RESERVOIR_SHORT:
        lit = "std::vector<int>{%s}" % ",".join(str(v) for v in stream)
        lines.append('std::cout << "reservoir_sample(%s,%d)=" << jl_int('
                     'reservoir_sample(%s, %d, rng)) << "\\n";' % (jl(stream), k, lit, k))
    return "\n        ".join(lines)


def build_cpp(ns_free_cpp_blocks):
    src = "\n\n".join(ns_free_cpp_blocks) + "\n" + CPP_MAIN
    subs = {
        "@HAMMING@": cpp_literal_ull(HAMMING),
        "@POW2@": cpp_literal_list(POW2),
        "@LOWBIT@": cpp_literal_ull(LOWBIT),
        "@BITS_OF@": cpp_literal_ull(BITS_OF),
        "@SINGLE@": cpp_literal_vecs(SINGLE),
        "@MISSING@": cpp_literal_vecs(MISSING),
        "@SUBSETS@": cpp_literal_ull(SUBSETS),
        "@BITMAP_SIZE@": str(BITMAP_SIZE),
        "@BITMAP_OPS@": cpp_bitmap_ops(),
        "@BITMAP_QUERY@": cpp_literal_list(BITMAP_QUERY),
        "@SEED@": str(SEED),
        "@SHUFFLE_BASE@": "std::vector<int>{%s}" % ",".join(str(v) for v in SHUFFLE_BASE),
        "@RESERVOIR_SHORT@": cpp_reservoir_short(),
        "@WEIGHTS@": "std::vector<long long>{%s}" % ",".join(str(v) for v in WEIGHTS),
        "@POW_SMALL_A@": cpp_literal_list(POW_SMALL_A),
        "@POW_SMALL_B@": cpp_literal_list(POW_SMALL_B),
        "@POW_SMALL_M@": cpp_literal_list(POW_SMALL_M),
        "@BIG_POW@": cpp_literal_triples(BIG_POW),
        "@BIG_MUL@": cpp_literal_triples(BIG_MUL),
        "@INV_PRIMES@": cpp_literal_list(INV_PRIMES),
        "@INV_AS@": cpp_literal_list(INV_AS),
        "@INV_COMPOSITE@": cpp_literal_pairs(INV_COMPOSITE),
        "@FACTORS@": cpp_literal_list(FACTORS),
        "@GCD_PAIRS@": cpp_literal_pairs(GCD_PAIRS),
        "@LCM_PAIRS@": cpp_literal_pairs(LCM_PAIRS),
        "@PRIME_CASES@": cpp_literal_list(PRIME_CASES),
        "@TRAILING@": cpp_literal_list(TRAILING),
        "@PERM_N@": str(PERM_N),
        "@PERM_CELLS@": str(PERM_N ** PERM_N),
        "@PERM_TRIALS@": str(PERM_TRIALS),
        "@RESERVOIR_N@": str(RESERVOIR_N),
        "@RESERVOIR_SMALL_N@": str(RESERVOIR_SMALL_N),
        "@RESERVOIR_K2@": str(RESERVOIR_K2),
        "@RESERVOIR_TRIALS_K1@": str(RESERVOIR_TRIALS_K1),
        "@RESERVOIR_TRIALS_K2@": str(RESERVOIR_TRIALS_K2),
        "@WEIGHTS_LEN@": str(len(WEIGHTS)),
        "@WEIGHTED_TRIALS@": str(WEIGHTED_TRIALS),
    }
    for k, v in subs.items():
        src = src.replace(k, v)
    left = sorted(set(re.findall(r"@[A-Z_]+@", src)))
    if left:
        raise SystemExit("FAIL  unsubstituted C++ placeholders: %s" % left)
    return src


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", default=str(DEFAULT_POST))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    post = Path(args.post)
    fails = []
    print("== 0. 目标 ==")
    print("  post : %s" % post)
    if not post.exists():
        raise SystemExit("FAIL  post not found: %s" % post)
    text = post.read_text(encoding="utf-8")

    print("== 1. 从文章里抽取代码块 ==")
    blocks = extract_blocks(text)
    langs = {}
    for lang, _ in blocks:
        langs[lang] = langs.get(lang, 0) + 1
    print("  共 %d 个代码块:%s"
          % (len(blocks), ", ".join("%s %d" % (k, v) for k, v in sorted(langs.items()))))
    bad_lang = [k for k in langs if k not in ALLOWED_LANGS]
    if bad_lang:
        fails.append("语言围栏不合规:%s" % bad_lang)
    py_blocks = [c for lang, c in blocks if lang == "python"]
    cpp_blocks = [c for lang, c in blocks if lang == "cpp"]
    print("  python %d 块,cpp %d 块 → %s"
          % (len(py_blocks), len(cpp_blocks),
             "数量相等" if len(py_blocks) == len(cpp_blocks) else "数量不等(FAIL)"))
    if len(py_blocks) != len(cpp_blocks):
        fails.append("python/cpp 块数不等: %d vs %d" % (len(py_blocks), len(cpp_blocks)))

    print("== 2. 执行 Python 块 ==")
    ns = {"__name__": "post_blocks"}
    for idx, code in enumerate(py_blocks, 1):
        try:
            exec(compile(code, "<post python block %d>" % idx, "exec"), ns)
        except Exception as exc:                       # noqa: BLE001
            fails.append("python 块 %d 执行失败: %r" % (idx, exc))
            print("  !! 块 %d 执行失败:%r" % (idx, exc))
    needed = ["hamming_weight", "is_power_of_two", "lowbit", "bits_of",
              "single_number", "missing_number", "subsets_of_mask", "Bitmap",
              "shuffle", "reservoir_sample", "WeightedPicker", "pow_mod",
              "pow_mod_rec", "mul_mod", "mod_inverse", "prime_factors",
              "gcd_euclid", "lcm_", "is_prime", "trailing_zeros_factorial"]
    missing = [n for n in needed if n not in ns]
    if missing:
        fails.append("Python 侧缺少定义: %s" % missing)
    print("  %d 个块执行完成,定义的必需名字 %d/%d"
          % (len(py_blocks), len(needed) - len(missing), len(needed)))

    print("== 3. 编译并运行 C++ 块 ==")
    src = build_cpp(cpp_blocks)
    tmp = Path(tempfile.mkdtemp(prefix="mt-verify-"))
    cpp_path, bin_path = tmp / "harness.cpp", tmp / "harness"
    cpp_path.write_text(src, encoding="utf-8")
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
           str(cpp_path), "-o", str(bin_path)]
    print("  $ %s" % " ".join(cmd))
    comp = subprocess.run(cmd, capture_output=True, text=True)
    warn_lines = [ln for ln in comp.stderr.splitlines() if ln.strip()]
    print("  编译退出码 = %d,stderr 非空行 = %d(-Wall -Wextra -Werror)"
          % (comp.returncode, len(warn_lines)))
    for ln in warn_lines[:20]:
        print("    | %s" % ln)
    if comp.returncode != 0:
        fails.append("C++ 编译失败(%d)" % comp.returncode)
        print("\nRESULT: FAIL")
        return 1
    run = subprocess.run([str(bin_path)], capture_output=True, text=True)
    cpp_lines = run.stdout.splitlines()
    print("  C++ 程序退出码 = %d,输出 %d 行" % (run.returncode, len(cpp_lines)))
    if run.returncode != 0:
        fails.append("C++ 程序退出码 %d" % run.returncode)
    if run.stderr.strip():
        print("    stderr: %s" % run.stderr.strip()[:400])

    py_lines = python_case_lines(ns)
    print("  Python 侧用例行数 = %d,C++ 侧 = %d" % (len(py_lines), len(cpp_lines)))
    diff = [(i, a, b) for i, (a, b) in enumerate(itertools.zip_longest(py_lines, cpp_lines), 1)
            if a != b]
    if diff:
        fails.append("逐行对拍有 %d 处不同" % len(diff))
        for i, a, b in diff[:20]:
            print("  !! 第 %d 行不同:\n     py : %s\n     cpp: %s" % (i, a, b))
    else:
        print("  ✅ 逐行对拍:%d 行全部一致(Python 与 C++ 用例集等价)" % len(py_lines))
    if args.verbose:
        for ln in py_lines:
            print("    | %s" % ln)
    else:
        print("  用例样例(前 6 行):")
        for ln in py_lines[:6]:
            print("    | %s" % ln)

    python_only_assertions(ns, fails)

    print("  再以 stats 模式跑一次 C++ 程序(只输出分桶计数,交给 Python 做卡方):")
    srun = subprocess.run([str(bin_path), "stats"], capture_output=True, text=True)
    cpp_stats = {}
    for ln in srun.stdout.splitlines():
        if ln.startswith("#S "):
            name, _, body = ln[3:].partition("=")
            cpp_stats[name] = [int(v) for v in body.split(",") if v != ""]
    print("    退出码 = %d,拿到 %d 组计数:%s"
          % (srun.returncode, len(cpp_stats),
             ", ".join("%s(%d 桶)" % (k, len(v)) for k, v in cpp_stats.items())))
    if len(cpp_stats) != 5:
        fails.append("stats 模式输出不完整: %s" % sorted(cpp_stats))

    try:
        if cpp_stats:
            statistical_checks(ns, cpp_stats)
        else:
            print("== 5. 统计检验 ==")
            print("  跳过:C++ stats 模式没有输出任何计数")
    except AssertionError as exc:
        fails.append("统计检验失败: %s" % exc)
        print("  !! %s" % exc)

    print("== 6. 结论 ==")
    if fails:
        print("  RESULT: FAIL")
        for f in fails:
            print("   - %s" % f)
        return 1
    print("  代码块   : python %d / cpp %d,全部执行/编译通过且零警告"
          % (len(py_blocks), len(cpp_blocks)))
    print("  对拍     : %d 行 Python == C++" % len(py_lines))
    print("  暴力连乘 : 小指数 %d 例逐项比对 + 大指数 %d 例对大整数真值"
          % (len(POW_SMALL_A) * len(POW_SMALL_B) * len(POW_SMALL_M),
             len(BIG_POW) * 2))
    print("  统计检验 : 洗牌(排列级)+ 对照组 + 水塘抽样(k=1 与子集级)+ 带权随机")
    print("  RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
