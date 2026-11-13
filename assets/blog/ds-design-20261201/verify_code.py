#!/usr/bin/env python3
"""Code gate for the ds-design post: the code in the post must actually run.

Why this exists: the prose gate cannot tell a correct structure from a
plausible-looking one.  Every claim this post makes about O(1) is a claim about
*behaviour*, so the gate has to execute the code, not read it.

It extracts the ```python and ```cpp blocks straight out of the post body --
no second copy, because a copy drifts -- and then:

  1. execs the Python blocks and diffs all five structures against a naive
     reference implementation that is obviously correct and obviously slow;
  2. proves LFU is really O(1) by *counting container touches per operation*
     and showing the bound does not move when capacity grows (wall-clock timing
     is not evidence: it is noisy, and this box is shared);
  3. compiles the C++ blocks with -Wall -Wextra -Werror (zero warnings) and
     runs the same differential fuzz against C++ references.

Usage: python3 assets/blog/ds-design-20261201/verify_code.py
Exit:  0 all cases pass, 1 otherwise.
"""

import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Derived, never hardcoded: this file is <repo>/assets/blog/<slug>/verify_code.py,
# so parents[3] is the repo root no matter where the repo is checked out.
REPO = Path(__file__).resolve().parents[3]
POST = REPO / "_posts" / "2026-12-01-ds-design.md"

EXPECTED_PY_BLOCKS = 5
EXPECTED_CPP_BLOCKS = 5
GXX = "/usr/bin/g++"


def extract(post_text, lang):
    return re.findall(r"```" + lang + r"\n(.*?)```", post_text, re.S)


# --------------------------------------------------------------------------
# naive references: slow, but there is nothing to get wrong
# --------------------------------------------------------------------------
class RefLRU:
    """A list of (key, val), oldest first.  get() rescans the whole list."""

    def __init__(self, cap):
        self.cap = cap
        self.items = []

    def get(self, key):
        for i, (k, v) in enumerate(self.items):
            if k == key:
                self.items.pop(i)
                self.items.append((k, v))
                return v
        return -1

    def put(self, key, val):
        for i, (k, _) in enumerate(self.items):
            if k == key:
                self.items.pop(i)
                self.items.append((key, val))
                return
        if self.cap <= 0:
            return
        if len(self.items) == self.cap:
            self.items.pop(0)
        self.items.append((key, val))


class RefLFU:
    """Evict = smallest freq, ties broken by the oldest last-access stamp."""

    def __init__(self, cap):
        self.cap = cap
        self.val = {}
        self.freq = {}
        self.stamp = {}
        self.t = 0

    def get(self, key):
        if key not in self.val:
            return -1
        self.freq[key] += 1
        self.t += 1
        self.stamp[key] = self.t
        return self.val[key]

    def put(self, key, val):
        if self.cap <= 0:
            return
        if key in self.val:
            self.val[key] = val
            self.freq[key] += 1
            self.t += 1
            self.stamp[key] = self.t
            return
        if len(self.val) == self.cap:
            victim, best = None, None
            for k in self.val:
                cand = (self.freq[k], self.stamp[k])
                if best is None or cand < best:
                    victim, best = k, cand
            del self.val[victim]
            del self.freq[victim]
            del self.stamp[victim]
        self.val[key] = val
        self.freq[key] = 1
        self.t += 1
        self.stamp[key] = self.t


class RefMinStack:
    def __init__(self):
        self.s = []

    def push(self, val):
        self.s.append(val)

    def pop(self):
        return self.s.pop()

    def top(self):
        return self.s[-1]

    def get_min(self):
        return min(self.s)


class RefTwitter:
    def __init__(self):
        self.t = 0
        self.tw = {}
        self.fo = {}

    def post_tweet(self, uid, tid):
        self.t += 1
        self.tw.setdefault(uid, []).append((self.t, tid))

    def get_news_feed(self, uid):
        src = {uid} | self.fo.get(uid, set())
        allt = []
        for x in src:
            allt.extend(self.tw.get(x, []))
        allt.sort(reverse=True)
        return [tid for _, tid in allt[:10]]

    def follow(self, a, b):
        self.fo.setdefault(a, set()).add(b)

    def unfollow(self, a, b):
        if b in self.fo.get(a, set()):
            self.fo[a].discard(b)


# --------------------------------------------------------------------------
# LFU O(1) evidence: count container touches, do not time anything
# --------------------------------------------------------------------------
class _Counter:
    __slots__ = ("n",)

    def __init__(self):
        self.n = 0


class CountBucket(dict):
    """A freq bucket that counts how many of its keys are actually touched.

    `next(iter(bucket))` costs 1; `min(bucket, key=...)` over a bucket of N
    costs N.  That difference is exactly "O(1) vs O(bucket size)", so counting
    touches here is a real proof and not a proxy for wall-clock noise.
    """

    def __init__(self, counter, *a, **kw):
        dict.__init__(self, *a, **kw)
        self._c = counter

    def __iter__(self):
        for k in dict.__iter__(self):
            self._c.n += 1
            yield k

    def __getitem__(self, k):
        self._c.n += 1
        return dict.__getitem__(self, k)

    def __contains__(self, k):
        self._c.n += 1
        return dict.__contains__(self, k)

    def get(self, k, d=None):
        self._c.n += 1
        return dict.get(self, k, d)

    def pop(self, *a):
        self._c.n += 1
        return dict.pop(self, *a)


class CountFreqMap(dict):
    """Replaces freq_to_keys so every bucket it hands out is instrumented."""

    def __init__(self, counter, *a, **kw):
        dict.__init__(self, *a, **kw)
        self._c = counter

    def setdefault(self, k, default=None):
        if not dict.__contains__(self, k):
            dict.__setitem__(self, k, CountBucket(self._c))
        return dict.__getitem__(self, k)


def lfu_touch_profile(lfu_cls, cap, ops):
    """(worst touches inside one get/put, largest bucket seen).

    The second number is what makes the first one meaningful: a constant bound
    proves nothing if the buckets never grow.  We want "bucket held N keys, and
    an operation still touched a bounded number of them" for large N.
    """
    c = lfu_cls(cap)
    ctr = _Counter()
    c.freq_to_keys = CountFreqMap(ctr)
    worst = 0
    biggest = 0
    for kind, a, b in ops:
        before = ctr.n
        if kind == "get":
            c.get(a)
        else:
            c.put(a, b)
        d = ctr.n - before
        if d > worst:
            worst = d
        for bucket in c.freq_to_keys.values():
            if len(bucket) > biggest:
                biggest = len(bucket)
    return worst, biggest


def fuzz_ops(rng, n, key_hi):
    ops = []
    for _ in range(n):
        k = rng.randint(0, key_hi)
        if rng.random() < 0.5:
            ops.append(("get", k, 0))
        else:
            ops.append(("put", k, rng.randint(-50, 50)))
    return ops


# --------------------------------------------------------------------------
def build_cpp_test(blocks):
    """The blocks, plus a fuzz harness that diffs them against C++ references."""
    return "\n".join(blocks) + "\n" + CPP_MAIN


def run_cpp(cpp_blocks):
    src = build_cpp_test(cpp_blocks)
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "probe.cpp"
        exe = Path(td) / "probe"
        cpp.write_text(src, encoding="utf-8")
        cmd = [GXX, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1",
               str(cpp), "-o", str(exe)]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            return None, cp.stderr.strip()
        rp = subprocess.run([str(exe)], capture_output=True, text=True)
        return (rp.stdout + rp.stderr).strip(), None


def main():
    if not POST.exists():
        print("  post not found: %s" % POST)
        return 1
    post = POST.read_text(encoding="utf-8")
    py = extract(post, "python")
    cpp = extract(post, "cpp")

    problems = []
    print("  repo root     : %s" % REPO)
    print("  post          : %s" % POST.name)
    print("  python blocks : %d (expect %d)" % (len(py), EXPECTED_PY_BLOCKS))
    print("  cpp blocks    : %d (expect %d)" % (len(cpp), EXPECTED_CPP_BLOCKS))
    if len(py) != EXPECTED_PY_BLOCKS:
        problems.append("expected %d python blocks, found %d"
                        % (EXPECTED_PY_BLOCKS, len(py)))
    if len(cpp) != EXPECTED_CPP_BLOCKS:
        problems.append("expected %d cpp blocks, found %d"
                        % (EXPECTED_CPP_BLOCKS, len(cpp)))
    if len(py) != len(cpp):
        problems.append("python/cpp block counts differ (%d vs %d)"
                        % (len(py), len(cpp)))

    for i, b in enumerate(py, 1):
        try:
            compile(b, "<py block %d>" % i, "exec")
        except SyntaxError as e:
            problems.append("python block %d does not compile: line %s: %s"
                            % (i, e.lineno, e.msg))
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        return 1

    ns = {}
    exec(compile("\n".join(py), str(POST), "exec"), ns)
    LRU, LFU = ns["LRUCache"], ns["LFUCache"]
    MS2, MSD = ns["MinStackTwoStacks"], ns["MinStackDiff"]
    RS, TW = ns["RandomizedSet"], ns["Twitter"]

    # ---------- 1. differential fuzz, all five structures ----------
    rng = random.Random(20261201)
    bad = 0

    for cap in (0, 1, 2, 3, 5, 16):
        for _ in range(8):
            a, b = LRU(cap), RefLRU(cap)
            for kind, k, v in fuzz_ops(rng, 300, 12):
                if kind == "get":
                    if a.get(k) != b.get(k):
                        bad += 1
                else:
                    a.put(k, v)
                    b.put(k, v)
    print("  LRU   fuzz (cap 0/1/2/3/5/16): %s" % ("OK" if not bad else "BAD"))

    lfu_bad = 0
    for cap in (0, 1, 2, 3, 5, 16):
        for _ in range(8):
            a, b = LFU(cap), RefLFU(cap)
            for kind, k, v in fuzz_ops(rng, 300, 12):
                if kind == "get":
                    if a.get(k) != b.get(k):
                        lfu_bad += 1
                else:
                    a.put(k, v)
                    b.put(k, v)
    bad += lfu_bad
    print("  LFU   fuzz (cap 0/1/2/3/5/16): %s" % ("OK" if not lfu_bad else "BAD"))

    ms_bad = 0
    for _ in range(20):
        a, b, r = MS2(), MSD(), RefMinStack()
        pool = []
        for _ in range(200):
            if not pool or rng.random() < 0.6:
                v = rng.choice([0, -1, 1, 2147483647, -2147483648,
                                rng.randint(-1000, 1000)])
                a.push(v)
                b.push(v)
                r.push(v)
                pool.append(v)
            else:
                expect = r.pop()        # 只弹一次:pop 是有副作用的
                if a.pop() != expect:
                    ms_bad += 1
                if b.pop() != expect:
                    ms_bad += 1
                pool.pop()
            if pool:
                if a.top() != r.top() or b.top() != r.top():
                    ms_bad += 1
                if a.get_min() != r.get_min() or b.get_min() != r.get_min():
                    ms_bad += 1
    bad += ms_bad
    print("  MinStack 双栈/差值 vs 重算最小值: %s"
          % ("OK" if not ms_bad else "BAD"))

    rs_bad = 0
    for _ in range(20):
        a, s = RS(), set()
        for _ in range(400):
            v = rng.randint(-5, 30)
            if rng.random() < 0.5:
                if a.insert(v) != (v not in s):
                    rs_bad += 1
                s.add(v)
            else:
                if a.remove(v) != (v in s):
                    rs_bad += 1
                s.discard(v)
            if set(a.vals) != s or len(a.vals) != len(s):
                rs_bad += 1        # 稠密不变量:无空洞、无重复
            for j, vv in enumerate(a.vals):
                if a.idx[vv] != j:
                    rs_bad += 1
    bad += rs_bad
    print("  RandomizedSet fuzz + 稠密不变量: %s"
          % ("OK" if not rs_bad else "BAD"))

    tw_bad = 0
    for _ in range(20):
        a, b = TW(), RefTwitter()
        nid = 0
        for _ in range(300):
            r = rng.random()
            u = rng.randint(1, 4)
            if r < 0.4:
                nid += 1
                a.post_tweet(u, nid)
                b.post_tweet(u, nid)
            elif r < 0.6:
                v = rng.randint(1, 4)
                a.follow(u, v)
                b.follow(u, v)
            elif r < 0.7:
                v = rng.randint(1, 4)
                a.unfollow(u, v)
                b.unfollow(u, v)
            elif a.get_news_feed(u) != b.get_news_feed(u):
                tw_bad += 1
    bad += tw_bad
    print("  Twitter fuzz (post/follow/unfollow/feed): %s"
          % ("OK" if not tw_bad else "BAD"))

    # ---------- 2. LFU: 同频按 LRU 淘汰,专门用例 ----------
    # (a) 两个 key 同为最小频率时,淘汰更久没被访问的那个
    c = LFU(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(3, 3)                     # freq 1 桶里 1 比 2 旧 -> 淘汰 1
    got = (c.get(1), c.get(2), c.get(3))
    same_freq_ok = got == (-1, 2, 3)
    print("  LFU 同频淘汰(最小的桶里最旧): get(1),get(2),get(3) = %s  %s"
          % (got, "OK" if same_freq_ok else "BAD"))
    if not same_freq_ok:
        problems.append("LFU same-freq eviction wrong: %s" % (got,))

    # (b) 频率被抬高之后,同频淘汰必须按「最近一次访问」而不是「插入时间」
    c = LFU(2)
    c.put(1, 1)
    c.put(2, 2)
    c.get(1)                        # 1 -> freq 2
    c.get(2)                        # 2 -> freq 2,1 先到 freq 2 -> 1 更旧
    c.put(3, 3)                     # 同频 2 的桶里淘汰 1
    got = (c.get(1), c.get(2), c.get(3))
    touch_ok = got == (-1, 2, 3)
    print("  LFU 同频淘汰(按最近访问而非插入): get(1),get(2),get(3) = %s  %s"
          % (got, "OK" if touch_ok else "BAD"))
    if not touch_ok:
        problems.append("LFU same-freq refresh order wrong: %s" % (got,))

    # (c) cap == 元素数 时不淘汰;重复 put 只更新值且加频率
    c = LFU(2)
    c.put(7, 70)
    c.put(8, 80)
    c.put(8, 88)                    # 命中已有 key:更新 + freq -> 2
    got = (c.get(7), c.get(8))
    dup_ok = got == (70, 88)
    print("  LFU 重复 put / cap == 元素数: get(7),get(8) = %s  %s"
          % (got, "OK" if dup_ok else "BAD"))
    if not dup_ok:
        problems.append("LFU duplicate-put wrong: %s" % (got,))

    # ---------- 3. LFU: O(1) 是数出来的,不是掐表掐出来的 ----------
    ctr = _Counter()
    small = CountBucket(ctr, dict((i, None) for i in range(1)))
    next(iter(small))
    one = ctr.n
    ctr2 = _Counter()
    big = CountBucket(ctr2, dict((i, None) for i in range(4096)))
    min(big, key=lambda k: k)
    many = ctr2.n
    print("  计数器本身可分辨 O(1) 与 O(桶): next(iter)=%d 次触碰, "
          "扫 4096 个 =%d 次" % (one, many))
    if not (one == 1 and many == 4096):
        problems.append("touch counter does not discriminate (1 vs 4096)")

    # 同一条操作流,只改容量:桶会随容量变大,而单次操作的触碰数不该跟着涨
    ops = fuzz_ops(rng, 4000, 256)
    prof = {}
    for cap in (8, 64, 512):
        prof[cap] = lfu_touch_profile(LFU, cap, ops)
    print("  LFU 单次操作最多触碰的容器元素数: " + ", ".join(
        "cap %d -> %d 次(该容量下最大桶 %d 个 key)"
        % (c, prof[c][0], prof[c][1]) for c in (8, 64, 512)))
    worst_all = max(p[0] for p in prof.values())
    if worst_all > 8:
        problems.append("LFU touches per op not a small constant: %s" % (prof,))

    # 上面那条流 get 很多,key 会被不断加频率,桶长不大。再补一条 put 为主的流,
    # 专门把 freq 1 的桶养到几百个 key —— 桶越大,「取桶头是 O(1)」才越有说服力。
    big_ops = []
    for i in range(3000):
        if i % 40 == 0:
            big_ops.append(("get", rng.randint(0, 700), 0))
        else:
            big_ops.append(("put", rng.randint(0, 700), i))
    bw, bb = lfu_touch_profile(LFU, 512, big_ops)
    print("  LFU 大桶压力(cap 512,put 为主): 最大桶 %d 个 key,"
          "单次操作最多触碰 %d 个" % (bb, bw))
    if bb < 100:
        problems.append("LFU buckets never grew large, so the O(1) claim was "
                        "never exercised: biggest bucket %d keys" % bb)
    if bw > 8:
        problems.append("LFU touched %d elements in one op over a %d-key "
                        "bucket" % (bw, bb))

    # ---------- 4. cpp ----------
    print("  compiling %d cpp blocks with %s -std=c++17 -Wall -Wextra -Werror"
          % (len(cpp), GXX))
    out, err = run_cpp(cpp)
    if err is not None:
        problems.append("cpp blocks failed to compile:\n%s" % err)
        print("  FAIL  cpp compile:\n%s" % err)
    else:
        for line in out.splitlines():
            print("  cpp | %s" % line)
        m = re.search(r"CPP MISMATCHES:\s*(\d+)", out)
        if not m:
            problems.append("cpp harness produced no MISMATCHES line")
        elif m.group(1) != "0":
            problems.append("cpp differential mismatches: %s" % m.group(1))
        if "CPP SAMEFREQ OK" not in out:
            problems.append("cpp same-freq LRU eviction case failed")

    # ---------- report ----------
    if bad:
        problems.append("python differential mismatches: %d" % bad)
    print("  ------------------------------------------------------------")
    print("  python differential mismatches : %d" % bad)
    if problems:
        for p in problems:
            print("  FAIL  %s" % p)
        print("\n  CODE GATE FAILED (%d problem(s))" % len(problems))
        return 1
    print("  CODE GATE OK")
    return 0


# --------------------------------------------------------------------------
# C++ counterpart: same differential fuzz, plus the same-freq LFU case.
# --------------------------------------------------------------------------
CPP_MAIN = r"""
#include <algorithm>
#include <cstdio>
#include <random>
#include <set>
#include <utility>
#include <vector>

namespace ref {

struct LRU {
    int cap;
    std::vector<std::pair<int, int> > items;
    explicit LRU(int c) : cap(c) {}
    int get(int key) {
        for (std::size_t i = 0; i < items.size(); ++i)
            if (items[i].first == key) {
                std::pair<int, int> p = items[i];
                items.erase(items.begin() + static_cast<long>(i));
                items.push_back(p);
                return p.second;
            }
        return -1;
    }
    void put(int key, int val) {
        for (std::size_t i = 0; i < items.size(); ++i)
            if (items[i].first == key) {
                items.erase(items.begin() + static_cast<long>(i));
                items.push_back(std::make_pair(key, val));
                return;
            }
        if (cap <= 0) return;
        if (static_cast<int>(items.size()) == cap)
            items.erase(items.begin());
        items.push_back(std::make_pair(key, val));
    }
};

struct LFU {
    int cap;
    int t;
    std::vector<int> keys, val, freq, stamp;
    explicit LFU(int c) : cap(c), t(0) {}
    int slot(int k) const {
        for (std::size_t i = 0; i < keys.size(); ++i)
            if (keys[i] == k) return static_cast<int>(i);
        return -1;
    }
    int get(int k) {
        int i = slot(k);
        if (i < 0) return -1;
        freq[i] += 1;
        stamp[i] = ++t;
        return val[i];
    }
    void put(int k, int v) {
        if (cap <= 0) return;
        int i = slot(k);
        if (i >= 0) { val[i] = v; freq[i] += 1; stamp[i] = ++t; return; }
        if (static_cast<int>(keys.size()) == cap) {
            int victim = 0;
            for (std::size_t j = 1; j < keys.size(); ++j)
                if (freq[j] < freq[victim] ||
                    (freq[j] == freq[victim] && stamp[j] < stamp[victim]))
                    victim = static_cast<int>(j);
            keys.erase(keys.begin() + victim);
            val.erase(val.begin() + victim);
            freq.erase(freq.begin() + victim);
            stamp.erase(stamp.begin() + victim);
        }
        keys.push_back(k);
        val.push_back(v);
        freq.push_back(1);
        stamp.push_back(++t);
    }
};

}  // namespace ref

int main() {
    std::mt19937 rng(20261201u);
    int bad = 0;
    int caps[] = {0, 1, 2, 3, 5, 16};

    for (int ci = 0; ci < 6; ++ci) {
        for (int trial = 0; trial < 8; ++trial) {
            LRUCache a(caps[ci]);
            ref::LRU b(caps[ci]);
            LFUCache c(caps[ci]);
            ref::LFU d(caps[ci]);
            for (int s = 0; s < 300; ++s) {
                int k = static_cast<int>(rng() % 13u);
                if (rng() % 2u == 0u) {
                    if (a.get(k) != b.get(k)) ++bad;
                    if (c.get(k) != d.get(k)) ++bad;
                } else {
                    int v = static_cast<int>(rng() % 101u) - 50;
                    a.put(k, v); b.put(k, v);
                    c.put(k, v); d.put(k, v);
                }
            }
        }
    }

    // MinStack: both encodings vs recomputing the min from scratch
    for (int trial = 0; trial < 20; ++trial) {
        MinStackTwoStacks a; MinStackDiff b;
        std::vector<int> raw;
        for (int s = 0; s < 200; ++s) {
            if (raw.empty() || rng() % 10u < 6u) {
                int v = static_cast<int>(rng() % 2001u) - 1000;
                a.push(v); b.push(v); raw.push_back(v);
            } else {
                int expect = raw.back(); raw.pop_back();
                if (a.pop() != expect || b.pop() != expect) ++bad;
            }
            if (!raw.empty()) {
                int mn = *std::min_element(raw.begin(), raw.end());
                if (a.getMin() != mn || b.getMin() != mn) ++bad;
                if (a.top() != raw.back() || b.top() != raw.back()) ++bad;
            }
        }
    }

    // RandomizedSet vs std::set
    for (int trial = 0; trial < 20; ++trial) {
        RandomizedSet a; std::set<int> s;
        for (int q = 0; q < 400; ++q) {
            int v = static_cast<int>(rng() % 36u) - 5;
            if (rng() % 2u == 0u) {
                if (a.insert(v) != (s.count(v) == 0)) ++bad;
                s.insert(v);
            } else {
                if (a.remove(v) != (s.count(v) != 0)) ++bad;
                s.erase(v);
            }
        }
        if (!s.empty()) {
            int r = a.getRandom();
            if (s.count(r) != 1) ++bad;
        }
    }

    // Twitter vs collect-and-sort
    for (int trial = 0; trial < 20; ++trial) {
        Twitter a;
        std::vector<std::pair<int, int> > all;   // (time, tweetId)
        std::vector<std::vector<int> > mine(5);
        std::vector<std::set<int> > fo(5);
        int clock = 0, nid = 0;
        for (int q = 0; q < 300; ++q) {
            unsigned r = rng() % 10u;
            int u = static_cast<int>(rng() % 4u) + 1;
            if (r < 4u) {
                ++nid; ++clock;
                a.postTweet(u, nid);
                mine[u].push_back(nid);
                all.push_back(std::make_pair(clock, nid));
            } else if (r < 6u) {
                int v = static_cast<int>(rng() % 4u) + 1;
                a.follow(u, v); fo[u].insert(v);
            } else if (r < 7u) {
                int v = static_cast<int>(rng() % 4u) + 1;
                a.unfollow(u, v); fo[u].erase(v);
            } else {
                std::set<int> src = fo[u]; src.insert(u);
                std::vector<std::pair<int, int> > pool;
                // rebuild by user: walk `all` and keep tweets whose author is in src
                pool.clear();
                for (std::size_t ui = 1; ui < mine.size(); ++ui) {
                    if (!src.count(static_cast<int>(ui))) continue;
                    for (std::size_t j = 0; j < mine[ui].size(); ++j) {
                        // recover the timestamp of tweet mine[ui][j]
                        for (std::size_t z = 0; z < all.size(); ++z)
                            if (all[z].second == mine[ui][j]) {
                                pool.push_back(all[z]);
                                break;
                            }
                    }
                }
                std::sort(pool.begin(), pool.end());
                std::vector<int> want;
                for (std::size_t j = pool.size(); j-- > 0 && want.size() < 10;)
                    want.push_back(pool[j].second);
                if (a.getNewsFeed(u) != want) ++bad;
            }
        }
    }

    // same-freq LFU eviction, both shapes
    {
        LFUCache c(2);
        c.put(1, 1); c.put(2, 2); c.put(3, 3);
        if (!(c.get(1) == -1 && c.get(2) == 2 && c.get(3) == 3)) ++bad;
        LFUCache d(2);
        d.put(1, 1); d.put(2, 2);
        d.get(1); d.get(2);
        d.put(3, 3);
        if (!(d.get(1) == -1 && d.get(2) == 2 && d.get(3) == 3)) ++bad;
    }

    std::printf("CPP MISMATCHES: %d\n", bad);
    std::printf("CPP SAMEFREQ %s\n", bad == 0 ? "OK" : "BAD");
    return bad == 0 ? 0 : 1;
}
"""

if __name__ == "__main__":
    sys.exit(main())
