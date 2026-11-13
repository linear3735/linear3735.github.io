#!/usr/bin/env python3
"""Code gate for the array-two-pointers post.

There are no second copies of the code here: the seven ```python and seven
```cpp blocks are extracted from the post itself, executed, and cross-checked
against brute-force / library oracles on the same set of cases.  The C++ side
is assembled into one harness with the extracted blocks verbatim and compiled
with -std=c++17 -Wall -Wextra -Werror (zero warnings tolerated).

    /opt/miniconda3/bin/python3 assets/blog/array-two-pointers-20261111/verify_code.py

Exit code 0 means every case passed in both languages.
"""
import itertools
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
# ATP_POST lets the negative control below point at a mutated copy in /tmp.
POST = Path(os.environ.get("ATP_POST",
                           REPO / "_posts/2026-11-11-array-two-pointers.md"))
EXPECT_BLOCKS = 23
ORACLE_OPS_SEEN = set()

# ---------------------------------------------------------------- cases
# Every case is one line of the shared input file; both languages read the
# same bytes.  Empty arrays, single elements, all-equal and all-negative
# inputs are all present on purpose.
CASES = [
    # removeDuplicates: empty / single / all-equal / all-negative / sorted
    "D 0",
    "D 1 7",
    "D 5 1 1 1 1 1",
    "D 5 -3 -3 -1 -1 0",
    "D 3 1 2 3",
    "D 2 0 0",
    "D 1 -5",
    "D 8 0 0 1 1 1 2 2 3",
    # deleteDuplicates (linked list)
    "L 0",
    "L 1 7",
    "L 3 1 1 2",
    "L 3 1 1 1",
    "L 5 -2 -2 -1 0 0",
    "L 6 1 1 2 3 3 3",
    # removeElement
    "E 0 3",
    "E 1 5 5",
    "E 1 4 5",
    "E 4 3 3 2 2 3",
    "E 3 2 2 2 2",
    "E 3 -1 -1 -2 -1",
    "E 3 0 0 0 0",
    "E 5 9 1 2 3 4 5",
    # moveZeroes
    "Z 0",
    "Z 1 0",
    "Z 1 1",
    "Z 5 0 1 0 3 12",
    "Z 3 0 0 0",
    "Z 4 -1 0 -2 0",
    "Z 5 1 2 3 4 5",
    # twoSum (LC 1, unordered, 0-based indices) and the nSum family
    "H2 4 9 2 7 11 15",
    "H2 3 6 3 2 4",
    "H2 2 6 3 3",
    "H2 1 5 5",
    "H2 0 0",
    "H2 4 0 -3 4 3 90",
    "H2 5 1 -1 -2 -3 -4 6",
    "3S 0",
    "3S 1 0",
    "3S 1 1",
    "3S 3 0 0 0",
    "3S 6 -1 0 1 2 -1 -4",
    "3S 5 -2 0 0 2 2",
    "3S 4 0 0 0 0",
    "3S 3 1 2 3",
    "3S 6 -4 -2 -2 0 1 2",
    "4S 6 0 1 0 -1 0 -2 2",
    "4S 5 8 2 2 2 2 2",
    "4S 6 2 -3 -1 0 2 4 5",
    "4S 0 0",
    "4S 2 0 1 2",
    "4S 4 0 0 0 0 0",
    "4S 6 0 -1 0 1 2 -1 -4",
    # twoSumSorted: sorted inputs, with and without a solution
    "T 0 5",
    "T 1 5 5",
    "T 4 9 2 7 11 15",
    "T 3 6 2 3 4",
    "T 6 10 1 3 4 6 8 11",
    "T 2 2 1 1",
    "T 3 -8 -5 -3 -1",
    "T 5 100 -4 -1 0 3 10",
    "T 4 -6 -4 -2 -1 5",
    # 80 / 125 / 75 / 88 / 977 / 14
    "DUP2 0",
    "DUP2 1 1",
    "DUP2 2 1 1",
    "DUP2 3 1 1 1",
    "DUP2 6 1 1 1 2 2 3",
    "DUP2 9 0 0 1 1 1 1 2 3 3",
    "DUP2 5 1 1 1 1 1",
    "DUP2 10 -3 -1 -1 -1 0 0 0 0 0 2",
    "DUP2 3 1 2 3",
    "PAL",
    "PAL a",
    "PAL aa",
    "PAL ab",
    "PAL A man, a plan, a canal: Panama",
    "PAL race a car",
    "PAL 0P",
    "PAL .,",
    "PAL ab_a",
    "SORT3 0",
    "SORT3 1 2",
    "SORT3 3 2 0 2",
    "SORT3 3 2 1 0",
    "SORT3 1 0",
    "SORT3 3 1 1 1",
    "SORT3 6 2 2 0 0 1 1",
    "SORT3 8 1 0 2 1 0 2 1 0",
    "MG 0 1 0 5",
    "MG 1 0 1",
    "MG 3 3 4 5 6 0 0 0 1 2 3",
    "MG 3 3 1 2 3 0 0 0 2 5 6",
    "MG 1 1 2 0 1",
    "MG 2 2 2 2 3 0 1 2",
    "SQ 0",
    "SQ 1 0",
    "SQ 5 -4 -1 0 3 10",
    "SQ 5 -7 -3 2 3 11",
    "SQ 3 1 2 3",
    "SQ 3 -5 -4 -3",
    "LCP 0",
    "LCP 1 a",
    "LCP 2 ab a",
    "LCP 3 flower flow flight",
    "LCP 3 dog racecar car",
    "LCP 2 _ b",
    "LCP 3 abc abc abc",
    # 48 / 54 / 59: 2D traversal
    "ROT 1 1 5",
    "ROT 2 2 1 2 3 4",
    "ROT 3 3 1 2 3 4 5 6 7 8 9",
    "ROT 4 4 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16",
    "SPI 0 0",
    "SPI 1 1 7",
    "SPI 1 3 1 2 3",
    "SPI 3 1 1 2 3",
    "SPI 2 2 1 2 3 4",
    "SPI 2 3 1 2 3 4 5 6",
    "SPI 3 4 1 2 3 4 5 6 7 8 9 10 11 12",
    "SPI 3 3 1 2 3 4 5 6 7 8 9",
    "GEN 1", "GEN 2", "GEN 3", "GEN 4", "GEN 5",
    # trapping rain water 42: identical inputs through both frameworks + brute
    "TR 0", "T2 0",
    "TR 1 5", "T2 1 5",
    "TR 2 3 3", "T2 2 3 3",
    "TR 3 0 0 0", "T2 3 0 0 0",
    "TR 6 4 2 0 3 2 5", "T2 6 4 2 0 3 2 5",
    "TR 12 0 1 0 2 1 0 1 3 2 1 2 1", "T2 12 0 1 0 2 1 0 1 3 2 1 2 1",
    "TR 5 5 4 3 2 1", "T2 5 5 4 3 2 1",
    "TR 5 1 2 3 4 5", "T2 5 1 2 3 4 5",
    "TR 3 2 0 2", "T2 3 2 0 2",
    "TR 4 3 3 3 3", "T2 4 3 3 3 3",
    "TR 10 5 5 1 7 1 1 5 2 7 6", "T2 10 5 5 1 7 1 1 5 2 7 6",
    "TR 5 0 7 1 4 6", "T2 5 0 7 1 4 6",
    "TR 2 0 5", "T2 2 0 5",
    # container with most water 11
    "MW 0",
    "MW 1 5",
    "MW 2 1 1",
    "MW 2 2 1",
    "MW 3 1 2 1",
    "MW 5 1 5 6 3 4",
    "MW 9 1 8 6 2 5 4 8 3 7",
    "MW 5 4 3 2 1 4",
    "MW 4 1 1 1 1",
    "MW 3 2 2 2",
    # 151 / 61: strings with spaces are raw lines, list rotation
    "RW",
    "RW a",
    "RW ab",
    "RW the sky is blue",
    "RW   hello world",
    "RW a good   example",
    "RW   Bob    Loves  Alice",
    "ROTK 0 3",
    "ROTK 1 0 7",
    "ROTK 1 5 7",
    "ROTK 2 1 1 2",
    "ROTK 5 0 1 2 3 4 5",
    "ROTK 5 2 1 2 3 4 5",
    "ROTK 5 5 1 2 3 4 5",
    "ROTK 5 7 1 2 3 4 5",
    "ROTK 3 4 1 2 3",
    # reverseString (the empty case is the size_t wrap trap)
    "R 0",
    "R 1 a",
    "R 2 ab",
    "R 3 aba",
    "R 5 abcde",
    "R 2 aa",
    "R 4 aaaa",
    # longestPalindrome: even centre, all-equal, no long palindrome
    "P 0",
    "P 1 a",
    "P 2 bb",
    "P 4 cbbd",
    "P 5 babad",
    "P 4 aaaa",
    "P 5 abcda",
    "P 15 forgeeksskeegfor",
    "P 3 aab",
]

CPP_PROLOGUE = r"""#include <algorithm>
#include <cctype>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

"""

CPP_MAIN = r"""
static void show(const std::vector<int>& v) {
    for (std::size_t i = 0; i < v.size(); ++i) std::cout << ' ' << v[i];
}

static std::vector<int> read_ints(int n) {
    std::vector<int> v;
    v.reserve(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) {
        int x = 0;
        std::cin >> x;
        v.push_back(x);
    }
    return v;
}

static void print_combos(const std::string& tag,
                         std::vector<std::vector<int>> combos) {
    for (std::size_t i = 0; i < combos.size(); ++i) {
        std::sort(combos[i].begin(), combos[i].end());
    }
    std::sort(combos.begin(), combos.end());
    std::cout << tag;
    for (std::size_t i = 0; i < combos.size(); ++i) {
        for (std::size_t j = 0; j < combos[i].size(); ++j) {
            std::cout << ' ' << combos[i][j];
        }
    }
    std::cout << '\n';
}

static std::vector<std::vector<int>> read_matrix(int rows, int cols) {
    std::vector<std::vector<int>> m;
    for (int i = 0; i < rows; ++i) {
        std::vector<int> row;
        for (int j = 0; j < cols; ++j) {
            int x = 0;
            std::cin >> x;
            row.push_back(x);
        }
        m.push_back(row);
    }
    return m;
}

static void show_matrix(const std::string& tag, const std::vector<std::vector<int>>& m) {
    std::cout << tag;
    for (std::size_t i = 0; i < m.size(); ++i) {
        for (std::size_t j = 0; j < m[i].size(); ++j) std::cout << ' ' << m[i][j];
    }
    std::cout << '\n';
}

static std::string read_word(int n) {
    std::string s;
    if (n > 0) std::cin >> s;
    return s;
}

int main() {
    std::string op;
    while (std::cin >> op) {
        if (op == "RW") {                        // raw line: spaces are data here
            std::string rest;
            std::getline(std::cin, rest);
            if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1);
            std::cout << "RW " << reverseWords(rest) << '\n';
            continue;
        }
        if (op == "PAL") {                       // raw line again: punctuation/spaces
            std::string rest;
            std::getline(std::cin, rest);
            if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1);
            std::cout << "PAL " << (isPalindrome(rest) ? 1 : 0) << '\n';
            continue;
        }
        int n = 0;
        if (!(std::cin >> n)) return 2;
        if (op == "DUP2") {
            std::vector<int> v = read_ints(n);
            int k = removeDuplicatesII(v);
            std::cout << "DUP2 " << k;
            for (int i = 0; i < k; ++i) std::cout << ' ' << v[static_cast<std::size_t>(i)];
            std::cout << '\n';
        } else if (op == "SORT3") {
            std::vector<int> v = read_ints(n);
            sortColors(v);
            std::cout << "SORT3";
            show(v);
            std::cout << '\n';
        } else if (op == "MG") {
            int n2 = 0;
            std::cin >> n2;
            std::vector<int> a = read_ints(n + n2);
            std::vector<int> b = read_ints(n2);
            merge(a, n, b, n2);
            std::cout << "MG";
            show(a);
            std::cout << '\n';
        } else if (op == "SQ") {
            std::vector<int> v = read_ints(n);
            std::cout << "SQ";
            show(sortedSquares(v));
            std::cout << '\n';
        } else if (op == "LCP") {
            std::vector<std::string> strs;
            for (int i = 0; i < n; ++i) {
                std::string w = read_word(1);
                strs.push_back(w == "_" ? std::string() : w);
            }
            std::cout << "LCP " << longestCommonPrefix(strs) << '\n';
        } else if (op == "ROT") {
            int cols = 0;
            std::cin >> cols;
            std::vector<std::vector<int>> m = read_matrix(n, cols);
            rotate(m);
            show_matrix("ROT", m);
        } else if (op == "SPI") {
            int cols = 0;
            std::cin >> cols;
            std::vector<std::vector<int>> m = read_matrix(n, cols);
            std::cout << "SPI";
            show(spiralOrder(m));
            std::cout << '\n';
        } else if (op == "GEN") {
            show_matrix("GEN", generateMatrix(n));
        } else if (op == "ROTK") {
            int k = 0;
            std::cin >> k;
            std::vector<int> v = read_ints(n);
            ListNode* head = nullptr;
            ListNode* tail = nullptr;
            for (int i = 0; i < n; ++i) {
                ListNode* node = new ListNode(v[static_cast<std::size_t>(i)]);
                if (tail == nullptr) {
                    head = node;
                } else {
                    tail->next = node;
                }
                tail = node;
            }
            std::cout << "ROTK";
            for (ListNode* q = rotateRight(head, k); q != nullptr; q = q->next) {
                std::cout << ' ' << q->val;
            }
            std::cout << '\n';
        } else if (op == "TR") {
            std::vector<int> v = read_ints(n);
            std::cout << "TR " << trapStack(v) << '\n';
        } else if (op == "T2") {
            std::vector<int> v = read_ints(n);
            std::cout << "T2 " << trapTwoPointers(v) << '\n';
        } else if (op == "MW") {
            std::vector<int> v = read_ints(n);
            std::cout << "MW " << maxArea(v) << '\n';
        } else if (op == "H2") {
            int target = 0;
            std::cin >> target;
            std::vector<int> v = read_ints(n);
            std::cout << "H2";
            show(twoSum(v, target));
            std::cout << '\n';
        } else if (op == "3S") {
            std::vector<int> v = read_ints(n);
            print_combos("3S", threeSum(v));
        } else if (op == "4S") {
            int target = 0;
            std::cin >> target;
            std::vector<int> v = read_ints(n);
            print_combos("4S", fourSum(v, target));
        } else if (op == "D") {
            std::vector<int> v = read_ints(n);
            int k = removeDuplicates(v);
            std::cout << "D " << k;
            for (int i = 0; i < k; ++i) std::cout << ' ' << v[static_cast<std::size_t>(i)];
            std::cout << '\n';
        } else if (op == "L") {
            std::vector<ListNode*> pool;
            ListNode* head = nullptr;
            ListNode* tail = nullptr;
            for (int i = 0; i < n; ++i) {
                int x = 0;
                std::cin >> x;
                ListNode* node = new ListNode(x);
                pool.push_back(node);
                if (tail == nullptr) head = node; else tail->next = node;
                tail = node;
            }
            std::cout << "L";
            for (ListNode* p = deleteDuplicates(head); p != nullptr; p = p->next) {
                std::cout << ' ' << p->val;
            }
            std::cout << '\n';
            for (std::size_t i = 0; i < pool.size(); ++i) delete pool[i];
        } else if (op == "E") {
            int val = 0;
            std::cin >> val;
            std::vector<int> v = read_ints(n);
            int k = removeElement(v, val);
            std::cout << "E " << k;
            for (int i = 0; i < k; ++i) std::cout << ' ' << v[static_cast<std::size_t>(i)];
            std::cout << '\n';
        } else if (op == "Z") {
            std::vector<int> v = read_ints(n);
            moveZeroes(v);
            std::cout << "Z";
            show(v);
            std::cout << '\n';
        } else if (op == "T") {
            int target = 0;
            std::cin >> target;
            std::vector<int> v = read_ints(n);
            std::vector<int> r = twoSumSorted(v, target);
            std::cout << "T";
            if (r.size() == 2) std::cout << ' ' << r[0] << ' ' << r[1];
            else std::cout << " -1 -1";
            std::cout << '\n';
        } else if (op == "R") {
            std::string w = read_word(n);
            std::vector<char> c(w.begin(), w.end());
            reverseString(c);
            std::cout << "R " << std::string(c.begin(), c.end()) << '\n';
        } else if (op == "P") {
            std::string w = read_word(n);
            std::cout << "P " << longestPalindrome(w) << '\n';
        } else {
            std::cerr << "unknown op " << op << '\n';
            return 2;
        }
    }
    return 0;
}
"""


def extract_blocks(text):
    """Pull ```python / ```cpp blocks out of the post, in document order."""
    lang, cur, py, cpp, fence = None, [], [], [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            if not fence:
                lang, fence, cur = line[3:].strip(), True, []
            else:
                (py if lang == "python" else cpp if lang == "cpp" else []).append(
                    "\n".join(cur))
                lang, fence, cur = None, False, []
            continue
        if fence:
            cur.append(line)
    return py, cpp


# ---------------------------------------------------------------- oracles
def brute_two_sum(nums, target):
    """All 1-based pairs, so the harness can accept any valid answer."""
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i + 1, j + 1]
    return []


def brute_longest_palindrome(s):
    """Longest palindromic substring by enumerating everything: O(n^3)."""
    best = ""
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            sub = s[i:j]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best


def parse(line):
    return line.split()


def find_block(blocks, needle):
    for b in blocks:
        if needle in b:
            return b
    raise AssertionError(f"no extracted block contains {needle!r}")


def brute_trap(height):
    """Column-by-column O(N^2) reference: the definition, written out plainly."""
    water = 0
    for i, h in enumerate(height):
        lmax = max(height[:i]) if i else 0
        rmax = max(height[i + 1:]) if i + 1 < len(height) else 0
        water += max(0, min(lmax, rmax) - h)
    return water


def brute_area(height):
    """All pairs, for LC 11."""
    best = 0
    for i in range(len(height)):
        for j in range(i + 1, len(height)):
            best = max(best, min(height[i], height[j]) * (j - i))
    return best


def brute_spiral(matrix):
    """Independent spiral order: peel the top row, rotate the rest, repeat."""
    out = []
    m = [row[:] for row in matrix]
    while m:
        out.extend(m.pop(0))
        m = [list(r) for r in zip(*m)][::-1]
    return out


def canon(tag, combos):
    """Canonical form for LC 15/18 answers: any order is accepted by the judge."""
    flat = sorted(sorted(c) for c in combos)
    out = [str(x) for c in flat for x in c]
    return tag + (" " + " ".join(out) if out else "")


def solve_python(ns, line):
    """Run one case through the post's own Python functions."""
    if line.startswith("RW"):                  # raw line: spaces are data here
        raw = line[3:] if len(line) > 3 else ""
        return "RW " + ns["reverseWords"](raw)
    if line.startswith("PAL"):                 # raw line again: punctuation/spaces
        raw = line[3:] if len(line) > 3 else ""
        return "PAL " + ("1" if ns["isPalindrome"](raw) else "0")
    f = parse(line)
    op, n = f[0], int(f[1])
    if op in ("TR", "T2"):
        v = [int(x) for x in f[2:2 + n]]
        fn = ns["trapStack"] if op == "TR" else ns["trapTwoPointers"]
        return f"{op} {fn(v)}"
    if op == "MW":
        v = [int(x) for x in f[2:2 + n]]
        return f"MW {ns['maxArea'](v)}"
    if op == "DUP2":
        v = [int(x) for x in f[2:2 + n]]
        k = ns["removeDuplicatesII"](v)
        return f"DUP2 {k}" + "".join(f" {x}" for x in v[:k])
    if op == "SORT3":
        v = [int(x) for x in f[2:2 + n]]
        ns["sortColors"](v)
        return "SORT3" + "".join(f" {x}" for x in v)
    if op == "MG":
        m, n2 = int(f[1]), int(f[2])
        nums1 = [int(x) for x in f[3:3 + m + n2]]
        nums2 = [int(x) for x in f[3 + m + n2:3 + m + n2 + n2]]
        ns["merge"](nums1, m, nums2, n2)
        return "MG" + "".join(f" {x}" for x in nums1)
    if op == "SQ":
        v = [int(x) for x in f[2:2 + n]]
        return "SQ" + "".join(f" {x}" for x in ns["sortedSquares"](v))
    if op == "LCP":
        strs = [("" if f[2 + i] == "_" else f[2 + i]) for i in range(n)]
        return "LCP " + ns["longestCommonPrefix"](strs)
    if op == "ROT":
        rows, cols = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + rows * cols]]
        m = [vals[i * cols:(i + 1) * cols] for i in range(rows)]
        ns["rotate"](m)                        # in place
        return "ROT" + "".join(f" {x}" for row in m for x in row)
    if op == "SPI":
        rows, cols = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + rows * cols]]
        m = [vals[i * cols:(i + 1) * cols] for i in range(rows)]
        return "SPI" + "".join(f" {x}" for x in ns["spiralOrder"](m))
    if op == "GEN":
        size = int(f[1])
        return "GEN" + "".join(f" {x}" for row in ns["generateMatrix"](size) for x in row)
    if op == "ROTK":
        size, k = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + size]]
        head = None
        for x in reversed(vals):
            head = ns["ListNode"](x, head)
        out = []
        node = ns["rotateRight"](head, k)
        while node is not None:
            out.append(node.val)
            node = node.next
        return "ROTK" + "".join(f" {x}" for x in out)
    if op == "H2":
        target, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        return "H2 " + " ".join(str(x) for x in ns["twoSum"](v, target))
    if op == "3S":
        v = [int(x) for x in f[2:2 + n]]
        return canon("3S", ns["threeSum"](v))
    if op == "4S":
        target, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        return canon("4S", ns["fourSum"](v, target))
    if op == "D":
        v = [int(x) for x in f[2:2 + n]]
        k = ns["removeDuplicates"](v)
        return "D " + " ".join([str(k)] + [str(x) for x in v[:k]])
    if op == "L":
        vals = [int(x) for x in f[2:2 + n]]
        head = None
        for x in reversed(vals):
            head = ns["ListNode"](x, head)
        out, p = [], ns["deleteDuplicates"](head)
        while p is not None:
            out.append(p.val)
            p = p.next
        return "L " + " ".join(str(x) for x in out)
    if op == "E":
        val, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        k = ns["removeElement"](v, val)
        return "E " + " ".join([str(k)] + [str(x) for x in v[:k]])
    if op == "Z":
        v = [int(x) for x in f[2:2 + n]]
        ns["moveZeroes"](v)
        return "Z " + " ".join(str(x) for x in v)
    if op == "T":
        target, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        r = ns["twoSumSorted"](v, target)
        return "T " + (" ".join(str(x) for x in r) if len(r) == 2 else "-1 -1")
    if op == "R":
        chars = list(f[2]) if n > 0 else []
        ns["reverseString"](chars)
        return "R " + "".join(chars)
    if op == "P":
        w = f[2] if n > 0 else ""
        return "P " + ns["longestPalindrome"](w)
    raise AssertionError("unknown op " + op)


def check_oracles(ns, line):
    """Independent library / brute-force checks on the same case."""
    if line.startswith("RW"):
        raw = line[3:] if len(line) > 3 else ""
        got = ns["reverseWords"](raw)
        want = " ".join(raw.split()[::-1])
        assert got == want, f"reverseWords: {got!r} != {want!r}"
        ORACLE_OPS_SEEN.add("RW")
        return True
    if line.startswith("PAL"):
        raw = line[3:] if len(line) > 3 else ""
        cleaned = "".join(ch for ch in raw.lower() if ch.isalnum())
        got = ns["isPalindrome"](raw)
        want = cleaned == cleaned[::-1]
        assert got == want, f"isPalindrome({raw!r}): {got} != {want} (cleaned {cleaned!r})"
        ORACLE_OPS_SEEN.add("PAL")
        return True
    f = parse(line)
    op, n = f[0], int(f[1])
    ORACLE_OPS_SEEN.add(op)
    if op == "D":
        v = [int(x) for x in f[2:2 + n]]
        k = ns["removeDuplicates"](v)          # in place: v is this case's copy
        assert k == len(set(v)), f"k={k} unique={len(set(v))} for {v}"
        assert v[:k] == sorted(set(v)), f"prefix {v[:k]} != {sorted(set(v))}"
        assert ns["removeDuplicates"]([]) == 0, "empty array must give 0"
    elif op == "L":
        vals = [int(x) for x in f[2:2 + n]]
        head = None
        for x in reversed(vals):
            head = ns["ListNode"](x, head)
        out, p = [], ns["deleteDuplicates"](head)
        while p is not None:
            out.append(p.val)
            p = p.next
        assert out == list(dict.fromkeys(vals)), f"{out} != {list(dict.fromkeys(vals))}"
    elif op == "E":
        val, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        want = [x for x in v if x != val]     # before the in-place call
        k = ns["removeElement"](v, val)
        assert k == len(want) and v[:k] == want, f"k={k} {v[:k]} != {want}"
    elif op == "Z":
        v = [int(x) for x in f[2:2 + n]]
        want = [x for x in v if x != 0] + [0] * v.count(0)
        ns["moveZeroes"](v)                    # in place: v is this case's copy
        assert v == want, f"{v} != {want}"
    elif op == "T":
        target, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        got = ns["twoSumSorted"](list(v), target)
        want = brute_two_sum(v, target)
        if want:
            i, j = got
            assert 1 <= i < j <= len(v), f"bad indices {got} for {v}"
            assert v[i - 1] + v[j - 1] == target, f"{got} sums to {v[i-1]+v[j-1]}"
            assert i != j, "the same element must not be used twice"
        else:
            assert got == [], f"expected no answer for {v}/{target}, got {got}"
    elif op == "R":
        chars = list(f[2]) if n > 0 else []
        ns["reverseString"](chars)
        assert chars == list(f[2])[::-1] if n > 0 else chars == []
    elif op == "P":
        w = f[2] if n > 0 else ""
        got = ns["longestPalindrome"](w)
        assert got == got[::-1] and got in w, f"{got!r} is not a palindrome of {w!r}"
        assert len(got) == len(brute_longest_palindrome(w)), \
            f"{got!r} (len {len(got)}) is not longest in {w!r}"
    elif op == "DUP2":
        vals = [int(x) for x in f[2:2 + n]]
        want = []
        run_val, run_len = None, 0
        for x in vals:
            if x == run_val:
                run_len += 1
            else:
                run_val, run_len = x, 1
            if run_len <= 2:
                want.append(x)
        v = list(vals)
        k = ns["removeDuplicatesII"](v)
        assert k == len(want), f"DUP2: k={k} != {len(want)} for {vals}"
        assert v[:k] == want, f"DUP2: prefix {v[:k]} != {want} for {vals}"
    elif op == "SORT3":
        v = [int(x) for x in f[2:2 + n]]
        ns["sortColors"](v)
        assert v == sorted(v), f"SORT3: {v} is not sorted"
    elif op == "MG":
        m, n2 = int(f[1]), int(f[2])
        nums1 = [int(x) for x in f[3:3 + m + n2]]
        nums2 = [int(x) for x in f[3 + m + n2:3 + m + n2 + n2]]
        arr = list(nums1)
        ns["merge"](arr, m, list(nums2), n2)
        want = sorted(nums1[:m] + nums2)
        assert arr == want, f"MG: {arr} != {want}"
    elif op == "SQ":
        v = [int(x) for x in f[2:2 + n]]
        got = ns["sortedSquares"](list(v))
        want = sorted(x * x for x in v)
        assert got == want, f"SQ: {got} != {want} for {v}"
    elif op == "LCP":
        strs = [("" if f[2 + i] == "_" else f[2 + i]) for i in range(n)]
        got = ns["longestCommonPrefix"](list(strs))
        want = ""
        if strs:
            for chars in zip(*strs):
                if len(set(chars)) != 1:
                    break
                want += chars[0]
        assert got == want, f"LCP: {got!r} != {want!r} for {strs}"
    elif op in ("TR", "T2"):
        v = [int(x) for x in f[2:2 + n]]
        got = ns["trapStack"](list(v)) if op == "TR" else ns["trapTwoPointers"](list(v))
        assert got == brute_trap(v), f"{op}: {got} != column-wise {brute_trap(v)} on {v}"
    elif op == "MW":
        v = [int(x) for x in f[2:2 + n]]
        got = ns["maxArea"](list(v))
        assert got == brute_area(v), f"MW: {got} != brute {brute_area(v)} on {v}"
    elif op == "H2":
        target, v = int(f[2]), [int(x) for x in f[3:3 + n]]
        got = ns["twoSum"](list(v), target)
        pairs = [(i, j) for i in range(len(v)) for j in range(i + 1, len(v))
                 if v[i] + v[j] == target]
        if pairs:
            assert len(got) == 2 and 0 <= got[0] < got[1] < len(v), f"bad {got}"
            assert v[got[0]] + v[got[1]] == target, f"{got} does not sum to {target}"
        else:
            assert got == [], f"expected no pair for {v}/{target}, got {got}"
    elif op in ("3S", "4S"):
        size = 3 if op == "3S" else 4
        target = 0 if op == "3S" else int(f[2])
        v = [int(x) for x in f[2 + (size - 3):2 + (size - 3) + n]]
        got = ns["threeSum"](list(v)) if op == "3S" else ns["fourSum"](list(v), target)
        want = sorted({tuple(sorted(c)) for c in itertools.combinations(v, size)
                       if sum(c) == target})
        assert sorted(tuple(sorted(c)) for c in got) == want, \
            f"{sorted(got)} != {[list(t) for t in want]}"
        assert len(got) == len({tuple(sorted(c)) for c in got}), \
            f"duplicate combinations returned: {got}"
        assert all(list(c) == sorted(c) for c in got), \
            f"each combination should be ascending: {got}"
    elif op == "ROT":
        rows, cols = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + rows * cols]]
        m = [vals[i * cols:(i + 1) * cols] for i in range(rows)]
        got = [row[:] for row in m]
        ns["rotate"](got)
        want = [list(r) for r in zip(*m[::-1])]        # library clockwise 90 degrees
        assert got == want, f"rotate: {got} != {want}"
    elif op == "SPI":
        rows, cols = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + rows * cols]]
        m = [vals[i * cols:(i + 1) * cols] for i in range(rows)]
        got = ns["spiralOrder"]([row[:] for row in m])
        want = brute_spiral(m)
        assert got == want, f"spiralOrder: {got} != peel-and-rotate {want}"
    elif op == "GEN":
        size = int(f[1])
        m = ns["generateMatrix"](size)
        flat = [x for row in m for x in row]
        assert sorted(flat) == list(range(1, size * size + 1)), f"not a permutation: {flat}"
        assert brute_spiral(m) == list(range(1, size * size + 1)), \
            "the fill order is not the spiral order"
    elif op == "ROTK":
        size, k = int(f[1]), int(f[2])
        vals = [int(x) for x in f[3:3 + size]]
        head = None
        for x in reversed(vals):
            head = ns["ListNode"](x, head)
        out = []
        node = ns["rotateRight"](head, k)
        guard = 0
        while node is not None and guard <= size:
            out.append(node.val)
            node = node.next
            guard += 1
        assert guard <= size, "the returned list still has a cycle (never terminates)"
        shift = k % size if size else 0
        want = (vals[size - shift:] + vals[:size - shift]) if shift else list(vals)
        assert out == want, f"rotateRight: {out} != {want}"
    else:
        raise AssertionError(f"no oracle branch for op {op!r} - refusing to pass silently")
    return True


TRAP_DEMO = r"""#include <cstddef>
#include <iostream>
#include <vector>

int main() {
    std::vector<char> s;                    // empty input
    std::size_t bad = s.size() - 1;         // the trap: unsigned wrap
    int good = static_cast<int>(s.size()) - 1;
    std::cout << bad << "\n";
    std::cout << (0 < bad ? "runs" : "skips") << "\n";
    std::cout << (0 < good ? "runs" : "skips") << "\n";
    return 0;
}
"""


def trap_demo(tmp):
    """Prove the section 3.2 C++ claim: s.size() - 1 on an empty vector wraps."""
    src = tmp / "trap.cpp"
    src.write_text(TRAP_DEMO, encoding="utf-8")
    exe = tmp / "trap"
    cc = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                         str(src), "-o", str(exe)], capture_output=True, text=True)
    if cc.returncode != 0:
        return [f"trap demo did not compile: {cc.stderr.strip()}"]
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    out = run.stdout.split()
    problems = []
    if len(out) != 3:
        return [f"trap demo printed {out!r}"]
    if int(out[0]) != 2 ** 64 - 1:
        problems.append(f"size_t wrap gave {out[0]}, expected {2 ** 64 - 1}")
    if out[1] != "runs":
        problems.append("the unsigned version was expected to enter the loop")
    if out[2] != "skips":
        problems.append("the int version was expected to skip the loop")
    print(f"  trap demo   : s.size() - 1 on an empty vector = {out[0]} "
          f"-> unsigned {out[1]} / int-cast {out[2]} (post 3.2 claim verified)")
    return problems


def dedup_control(py_blocks):
    """Reverse control: prove the two section 5.3 counter-examples are real.

    The two de-dup guards are deleted from the post's own nSum block; if the
    prose is right, each mutant must start emitting duplicate combinations.
    """
    src = find_block(py_blocks, "def nSum(")
    problems = []

    def run(mutant_src, case):
        scope = {}
        exec(compile(mutant_src, "<mutant nSum block>", "exec"), scope)  # noqa: S102
        res = scope["threeSum"](list(case))
        seen = [tuple(sorted(c)) for c in res]
        return seen, len(seen) - len(set(seen))

    # 1) drop the recursion-level guard  -> [-1,0,1,2,-1,-4] yields [-1,0,1] twice
    no_first = re.sub(r"[ ]*if i > start and nums\[i\] == nums\[i - 1\]:\n[ ]*continue[^\n]*\n",
                      "", src, count=1)
    if no_first == src:
        problems.append("could not find the recursion-level de-dup guard in block 9")
    else:
        seen, dup = run(no_first, [-1, 0, 1, 2, -1, -4])
        print(f"  counter-ex : drop `i > start` guard -> {seen}, {dup} duplicate(s)")
        if dup == 0:
            problems.append("prose claims a duplicate [-1,0,1] appears, but it did not")

    # 2) drop the two-pointer skips     -> [-2,0,0,2,2] yields [-2,0,2] twice
    no_second = re.sub(r"[ ]*while left < right and nums\[left\] == nums\[left \+ 1\]:\n"
                       r"[ ]*left \+= 1[^\n]*\n[ ]*while left < right and nums\[right\] == "
                       r"nums\[right - 1\]:\n[ ]*right -= 1[^\n]*\n",
                       "", src, count=1)
    if no_second == src:
        problems.append("could not find the two-pointer de-dup guards in block 9")
    else:
        seen, dup = run(no_second, [-2, 0, 0, 2, 2])
        print(f"  counter-ex : drop two-pointer skips -> {seen}, {dup} duplicate(s)")
        if dup == 0:
            problems.append("prose claims a duplicate [-2,0,2] appears, but it did not")

    # the untouched block must stay clean on both cases
    scope = {}
    exec(compile(src, "<post nSum block>", "exec"), scope)  # noqa: S102
    for case in ([-1, 0, 1, 2, -1, -4], [0, 0, 0, 0], [-2, 0, 0, 2, 2], [0] * 5):
        seen = [tuple(sorted(c)) for c in scope["threeSum"](list(case))]
        if len(seen) != len(set(seen)):
            problems.append(f"the shipped nSum block duplicates on {case}: {seen}")
    return problems


def ns_trap_three_way(py_blocks, height):
    """stack == two-pointer == column-wise brute, on one input."""
    scope = {}
    for needle in ("def trapStack(", "def trapTwoPointers("):
        exec(compile(find_block(py_blocks, needle), "<post trap block>", "exec"), scope)  # noqa: S102
    a = scope["trapStack"](list(height))
    b = scope["trapTwoPointers"](list(height))
    c = brute_trap(height)
    return a == b == c


def trap_controls(py_blocks):
    """Reverse controls + randomized equivalence checks for section 6."""
    problems = []
    stack_src = find_block(py_blocks, "def trapStack(")
    two_src = find_block(py_blocks, "def trapTwoPointers(")

    # 1) drop `if not stack: break` -> IndexError on both official samples
    mutant = re.sub(r"[ ]*if not stack:\n[ ]*break[^\n]*\n", "", stack_src, count=1)
    if mutant == stack_src:
        problems.append("could not find the empty-stack guard in the trapStack block")
    else:
        for case in ([4, 2, 0, 3, 2, 5], [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]):
            scope = {}
            exec(compile(mutant, "<mutant trapStack>", "exec"), scope)  # noqa: S102
            try:
                got = scope["trapStack"](list(case))
                problems.append(f"dropping the guard did not crash on {case}: {got}")
            except IndexError:
                pass
        print("  counter-ex : drop `if not stack: break` -> IndexError on both samples")

    # 2) move the lmax/rmax updates to the end of the loop -> -1 and 5
    mutant = re.sub(r"[ ]*lmax = max\(lmax, height\[left\]\)[^\n]*\n"
                    r"[ ]*rmax = max\(rmax, height\[right\]\)[^\n]*\n", "", two_src, count=1)
    if mutant == two_src:
        problems.append("could not find the lmax/rmax updates in trapTwoPointers")
    else:
        mutant = mutant.replace(
            "    return water",
            "        lmax = max(lmax, height[left])\n"
            "        rmax = max(rmax, height[right])\n    return water", 1)
        scope = {}
        exec(compile(mutant, "<mutant trapTwoPointers>", "exec"), scope)  # noqa: S102
        observed = [scope["trapTwoPointers"](list(c))
                    for c in ([4, 2, 0, 3, 2, 5],
                              [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1])]
        print(f"  counter-ex : updates moved to loop end -> {observed} "
              f"(prose claims [-1, 5]; answers are 9 and 6)")
        if observed != [-1, 5]:
            problems.append(f"prose says the delayed update gives [-1, 5], it gave {observed}")

    # 3) randomized equivalence of the two variants the prose calls equivalent
    rng = random.Random(20261111)
    trap_alt_bad = area_tie_bad = 0
    for _ in range(400):
        h = [rng.randint(0, 9) for _ in range(rng.randint(0, 12))]
        l, r, lm, rm, w = 0, len(h) - 1, 0, 0, 0
        while l < r:                       # branch on current heights instead of maxima
            lm = max(lm, h[l])
            rm = max(rm, h[r])
            if h[l] < h[r]:
                w += lm - h[l]
                l += 1
            else:
                w += rm - h[r]
                r -= 1
        if w != brute_trap(h):
            trap_alt_bad += 1
        bl, br, best = 0, len(h) - 1, 0
        while bl < br:                     # ties move the left pointer instead
            best = max(best, min(h[bl], h[br]) * (br - bl))
            if h[bl] <= h[br]:
                bl += 1
            else:
                br -= 1
        if best != brute_area(h):
            area_tie_bad += 1
    trap_inputs = [[int(x) for x in ln.split()[2:]] for ln in CASES if ln.startswith("TR ")]
    agree = sum(1 for v in trap_inputs
                if ns_trap_three_way(py_blocks, v))
    print(f"  three-way  : TR == T2 == column-wise brute on {agree}/{len(trap_inputs)} inputs")
    if agree != len(trap_inputs):
        problems.append("stack / two-pointer / brute disagree on some input")
    print(f"  equivalent : height-based branch {400 - trap_alt_bad}/400 match brute, "
          f"tie-moves-left {400 - area_tie_bad}/400 match brute")
    if trap_alt_bad or area_tie_bad:
        problems.append("prose calls those variants equivalent, but they are not")
    return problems


ARITY = {
    "D": lambda f: 2 + int(f[1]),
    "L": lambda f: 2 + int(f[1]),
    "E": lambda f: 3 + int(f[1]),
    "Z": lambda f: 2 + int(f[1]),
    "T": lambda f: 3 + int(f[1]),
    "R": lambda f: 2 if int(f[1]) == 0 else 3,   # word is one token, not n
    "P": lambda f: 2 if int(f[1]) == 0 else 3,
    "H2": lambda f: 3 + int(f[1]),
    "3S": lambda f: 2 + int(f[1]),
    "4S": lambda f: 3 + int(f[1]),
    "TR": lambda f: 2 + int(f[1]),
    "T2": lambda f: 2 + int(f[1]),
    "MW": lambda f: 2 + int(f[1]),
    "DUP2": lambda f: 2 + int(f[1]),
    "SORT3": lambda f: 2 + int(f[1]),
    "SQ": lambda f: 2 + int(f[1]),
    "LCP": lambda f: 2 + int(f[1]),
    "ROT": lambda f: 3 + int(f[1]) * int(f[2]),
    "SPI": lambda f: 3 + int(f[1]) * int(f[2]),
    "GEN": lambda f: 2,
    "ROTK": lambda f: 3 + int(f[1]),
    "MG": lambda f: 3 + int(f[1]) + 2 * int(f[2]),
}


def check_case_arity():
    """A case line with the wrong token count silently under-tests (and desyncs C++)."""
    bad = []
    for line in CASES:
        if line.startswith(("RW", "PAL")):   # raw lines: spaces are data
            continue
        f = parse(line)
        op = f[0]
        if op not in ARITY:
            bad.append(f"{line}  ->  op {op!r} has no declared arity")
            continue
        want = ARITY[op](f)
        if len(f) != want:
            bad.append(f"{line}  ->  {len(f)} tokens, op {op} consumes {want}")
    return bad


def section7_controls(py_blocks):
    """Reverse controls for every trap line in section 7."""
    problems = []

    def run(src, needles=()):
        scope = {}
        for needle in needles:
            exec(compile(find_block(py_blocks, needle), "<post block>", "exec"), scope)  # noqa: S102
        exec(compile(src, "<mutant>", "exec"), scope)  # noqa: S102
        return scope

    # 48: transposing over range(n) undoes the transpose -> a left-right mirror
    src = find_block(py_blocks, "def rotate(")
    mut = src.replace("for j in range(i + 1, n):", "for j in range(n):", 1)
    if mut == src:
        problems.append("could not find the upper-triangle loop in rotate")
    else:
        scope = run(mut)
        m = [[1, 2], [3, 4]]
        scope["rotate"](m)
        print(f"  counter-ex : transpose over range(n) -> {m} (prose says [[2, 1], [4, 3]])")
        if m != [[2, 1], [4, 3]]:
            problems.append(f"prose says range(n) gives [[2,1],[4,3]], got {m}")

    # 54: without the bottom-edge guard a single row duplicates its middle
    src = find_block(py_blocks, "def spiralOrder(")
    mut = src.replace("if top <= bottom:", "if True:", 1)
    if mut == src:
        problems.append("could not find the `if top <= bottom:` guard in spiralOrder")
    else:
        scope = run(mut)
        row = scope["spiralOrder"]([[1, 2, 3]])
        col = scope["spiralOrder"]([[1], [2], [3]])
        print(f"  counter-ex : drop bottom guard -> row {row}, column {col} "
              f"(prose says [1, 2, 3, 2, 1] and [1, 2, 3])")
        if row != [1, 2, 3, 2, 1] or col != [1, 2, 3]:
            problems.append(f"prose says {[1, 2, 3, 2, 1]} / {[1, 2, 3]}, got {row} / {col}")

    # 59: `while left < right` loses the centre of odd squares
    src = find_block(py_blocks, "def generateMatrix(")
    mut = src.replace("while left <= right and top <= bottom:", "while left < right:", 1)
    if mut == src:
        problems.append("could not find the generateMatrix loop condition")
    else:
        scope = run(mut)
        missing = {}
        for size in (1, 3, 5):
            flat = [x for r in scope["generateMatrix"](size) for x in r]
            missing[size] = sorted(set(range(1, size * size + 1)) - set(flat))
        print(f"  counter-ex : `while left < right` -> odd squares miss {missing} "
              f"(prose says 1/9/25)")
        if missing != {1: [1], 3: [9], 5: [25]}:
            problems.append(f"prose says odd squares miss 1/9/25, got {missing}")

    # 61: n-k steps instead of n-k-1 shifts every node by one
    src = find_block(py_blocks, "def rotateRight(")
    mut = src.replace("range(n - k - 1)", "range(n - k)", 1)
    if mut == src:
        problems.append("could not find `range(n - k - 1)` in rotateRight")
    else:
        scope = run(mut, ("class ListNode:",))
        head = None
        for x in (5, 4, 3, 2, 1):
            head = scope["ListNode"](x, head)
        out = []
        node = scope["rotateRight"](head, 2)
        while node is not None and len(out) <= 5:
            out.append(node.val)
            node = node.next
        print(f"  counter-ex : `n - k` instead of `n - k - 1` -> {out} (prose says [5, 1, 2, 3, 4])")
        if out != [5, 1, 2, 3, 4]:
            problems.append(f"prose says [5,1,2,3,4], got {out}")
    return problems


def section8_controls(py_blocks):
    """Reverse controls for every trap line in section 8."""
    problems = []

    def run(src, needles=()):
        scope = {}
        for needle in needles:
            exec(compile(find_block(py_blocks, needle), "<post block>", "exec"), scope)  # noqa: S102
        exec(compile(src, "<mutant>", "exec"), scope)  # noqa: S102
        return scope

    # 80: without `slow < 2` a negative index silently wipes short arrays
    src = find_block(py_blocks, "def removeDuplicatesII(")
    mut = src.replace("if slow < 2 or nums[slow - 2] != nums[fast]:",
                      "if nums[slow - 2] != nums[fast]:", 1)
    if mut == src:
        problems.append("could not find the `slow < 2` guard in removeDuplicatesII")
    else:
        scope = run(mut)
        k2 = scope["removeDuplicatesII"]([1, 1])
        k3 = scope["removeDuplicatesII"]([1, 1, 1])
        print(f"  counter-ex : drop `slow < 2` -> k([1, 1]) = {k2}, k([1, 1, 1]) = {k3} "
              f"(prose says 0 and 0)")
        if (k2, k3) != (0, 0):
            problems.append(f"prose says [1,1] and [1,1,1] both give 0, got {k2} and {k3}")

    # 125: the inner skip loops need their own bound
    src = find_block(py_blocks, "def isPalindrome(")
    mut = src.replace("while left < right and not s[left].isalnum():",
                      "while not s[left].isalnum():", 1)
    mut = mut.replace("while left < right and not s[right].isalnum():",
                      "while not s[right].isalnum():", 1)
    if mut == src:
        problems.append("could not find the inner skip bounds in isPalindrome")
    else:
        scope = run(mut)
        try:
            scope["isPalindrome"](".,")
            problems.append("prose says dropping the inner bound raises IndexError on '.,'")
        except IndexError:
            print("  counter-ex : drop the inner `left < right` -> IndexError on '.,' "
                  "(prose says so)")

    # 75: both mutations, on the same 500 random arrays the prose quotes
    src = find_block(py_blocks, "def sortColors(")
    lines = src.splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines) if ln.strip().startswith("p2 -= 1")]
    if len(hits) != 1:
        problems.append(f"could not find exactly one `p2 -= 1` step in sortColors ({len(hits)})")
    else:
        step = hits[0]
        lines.insert(step + 1, "            i += 1\n")
        scope_a = run("".join(lines))
        scope_c = run(src.replace("    while i <= p2:", "    while i < p2:", 1))
        rng = random.Random(7)
        arrays = [[rng.randint(0, 2) for _ in range(rng.randint(0, 9))] for _ in range(500)]
        def sort_with(scope, arr):            # sortColors works in place, no return
            v = list(arr)
            scope["sortColors"](v)
            return v

        bad_a = sum(1 for a in arrays if sort_with(scope_a, a) != sorted(a))
        bad_c = sum(1 for a in arrays if sort_with(scope_c, a) != sorted(a))
        ex = [0, 1, 2, 0, 2, 0, 0, 0]
        got = sort_with(scope_a, ex)
        good = sort_with(run(src), ex)
        print(f"  counter-ex : `i += 1` after a 2 -> {bad_a}/500 wrong (prose says 125), "
              f"e.g. {ex} -> {got} (prose says {got})")
        print(f"  counter-ex : `while i < p2` -> {bad_c}/500 wrong (prose says 109)")
        if (bad_a, bad_c) != (125, 109):
            problems.append(f"prose says 125 and 109 wrong out of 500, got {bad_a} and {bad_c}")
        if got != [0, 0, 0, 1, 0, 0, 2, 2] or good != [0, 0, 0, 0, 0, 1, 2, 2]:
            problems.append(f"prose says {ex} -> {[0, 0, 0, 0, 0, 1, 2, 2]} vs "
                            f"{[0, 0, 0, 1, 0, 0, 2, 2]}, got {good} vs {got}")

    # 88: front-to-back overwrites the elements it has not read yet
    def merge_front(nums1, m, nums2):
        i = j = write = 0
        while i < m and j < len(nums2):
            if nums1[i] <= nums2[j]:
                nums1[write] = nums1[i]
                i += 1
            else:
                nums1[write] = nums2[j]
                j += 1
            write += 1
        while j < len(nums2):
            nums1[write] = nums2[j]
            j += 1
            write += 1
        return nums1

    scope = run(find_block(py_blocks, "def merge("))
    arr = [4, 5, 6, 0, 0, 0]
    scope["merge"](arr, 3, [1, 2, 3], 3)          # in place: no return value
    shipped = arr
    front = merge_front([4, 5, 6, 0, 0, 0], 3, [1, 2, 3])
    print(f"  counter-ex : front-to-back merge -> {front} (prose says {front}; "
          f"shipped gives {shipped})")
    if shipped != [1, 2, 3, 4, 5, 6] or front != [1, 1, 1, 1, 2, 3]:
        problems.append(f"prose says [1,2,3,4,5,6] vs [1,1,1,1,2,3], got {shipped} vs {front}")

    # 977: comparing the values instead of the absolute values
    src = find_block(py_blocks, "def sortedSquares(")
    mut = src.replace("if abs(nums[left]) > abs(nums[right]):",
                      "if nums[left] > nums[right]:", 1)
    if mut == src:
        problems.append("could not find the abs comparison in sortedSquares")
    else:
        scope = run(mut)
        got = scope["sortedSquares"]([-4, -1, 0, 3, 10])
        print(f"  counter-ex : compare raw values -> {got} (prose says [16, 1, 0, 9, 100])")
        if got != [16, 1, 0, 9, 100]:
            problems.append(f"prose says [16,1,0,9,100], got {got}")

    # 14: the column bound must come first
    src = find_block(py_blocks, "def longestCommonPrefix(")
    mut = src.replace("if col >= len(s) or s[col] != ch:",
                      "if s[col] != ch:", 1)
    if mut == src:
        problems.append("could not find the column bound in longestCommonPrefix")
    else:
        scope = run(mut)
        try:
            scope["longestCommonPrefix"](["ab", "a"])
            problems.append("prose says dropping `col >= len(s)` raises IndexError on ['ab','a']")
        except IndexError:
            print("  counter-ex : drop `col >= len(s)` -> IndexError on ['ab', 'a'] "
                  "(prose says so)")
    return problems


def main():
    text = POST.read_text(encoding="utf-8")
    py_blocks, cpp_blocks = extract_blocks(text)
    shown = POST.relative_to(REPO) if POST.is_relative_to(REPO) else POST
    print(f"  post        : {shown}")
    print(f"  blocks      : python {len(py_blocks)}, cpp {len(cpp_blocks)}"
          f" (extracted from the post, no second copies)")
    assert len(py_blocks) == len(cpp_blocks), \
        f"python {len(py_blocks)} != cpp {len(cpp_blocks)}"
    assert len(py_blocks) == EXPECT_BLOCKS, \
        f"expected {EXPECT_BLOCKS} python blocks, found {len(py_blocks)}"

    # The prose quotes these three counts; a stale sentence must fail the gate.
    m = re.search(r"文中 (\d+) 段 Python 和 (\d+) 段 C\+\+", text)
    assert m, "the post no longer states its python/cpp block counts"
    assert (int(m.group(1)), int(m.group(2))) == (len(py_blocks), len(cpp_blocks)), \
        f"post says {m.group(1)}/{m.group(2)} blocks, gate extracted " \
        f"{len(py_blocks)}/{len(cpp_blocks)}"
    m = re.search(r"同一批 (\d+) 个用例", text)
    assert m, "the post no longer states its case count"
    assert int(m.group(1)) == len(CASES), \
        f"post says {m.group(1)} cases, gate runs {len(CASES)}"

    ns = {}
    for i, block in enumerate(py_blocks, 1):
        exec(compile(block, f"<post python block {i}>", "exec"), ns)  # noqa: S102

    py_out, oracle_fail = [], []
    arity_bad = check_case_arity()
    print(f"  arity       : {len(CASES)} case line(s), "
          + ("every token count matches its op" if not arity_bad
             else f"{len(arity_bad)} MALFORMED"))
    for line in arity_bad:
        print(f"  FAIL arity   {line}")
    if arity_bad:
        return 1
    for line in CASES:
        try:
            check_oracles(ns, line)
        except AssertionError as exc:
            oracle_fail.append(f"{line}  ->  {exc}")
        py_out.append(solve_python(ns, line).rstrip())
    print(f"  python      : {len(CASES)} cases, {len(oracle_fail)} oracle failure(s)")

    tmp = Path(tempfile.mkdtemp(prefix="atp-verify-"))
    try:
        src = tmp / "harness.cpp"
        src.write_text(CPP_PROLOGUE + "\n\n".join(cpp_blocks) + "\n" + CPP_MAIN,
                       encoding="utf-8")
        exe = tmp / "harness"
        cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
               str(src), "-o", str(exe)]
        print(f"  compile     : {' '.join(cmd[:5])} ... -Werror")
        cc = subprocess.run(cmd, capture_output=True, text=True)
        if cc.returncode != 0:
            print("  FAIL compile with -Werror:\n" + (cc.stderr or cc.stdout))
            return 1
        warn = [ln for ln in (cc.stderr or "").splitlines() if ln.strip()]
        print(f"  warnings    : {len(warn)} (compiler said nothing at all)")

        cases_file = tmp / "cases.txt"
        cases_file.write_text("\n".join(CASES) + "\n", encoding="utf-8")
        with cases_file.open() as fh:
            run = subprocess.run([str(exe)], stdin=fh, capture_output=True,
                                 text=True)
        if run.returncode != 0:
            print(f"  FAIL harness exited {run.returncode}\n{run.stderr}")
            return 1
        cpp_out = [ln.rstrip() for ln in run.stdout.splitlines() if ln.strip()]
        print(f"  cpp         : {len(cpp_out)} result lines")
        trap_fail = trap_demo(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if len(cpp_out) != len(CASES):
        print(f"  FAIL cpp produced {len(cpp_out)} lines for {len(CASES)} cases")
        return 1

    diff = [(c, p, q) for c, p, q in zip(CASES, py_out, cpp_out) if p != q]
    print(f"  agreements  : {len(CASES) - len(diff)}/{len(CASES)} cases identical")
    oracle_fail += trap_fail
    oracle_fail += dedup_control(py_blocks)
    oracle_fail += trap_controls(py_blocks)
    oracle_fail += section7_controls(py_blocks)
    oracle_fail += section8_controls(py_blocks)
    if oracle_fail or diff:
        print()
        for x in oracle_fail:
            print(f"  FAIL oracle {x}")
        for c, p, q in diff:
            print(f"  FAIL case   {c}\n         python: {p}\n         cpp   : {q}")
        print(f"\n  RESULT: {len(oracle_fail) + len(diff)} problem(s)")
        return 1

    ops = {}
    for line in CASES:
        ops[line.split()[0]] = ops.get(line.split()[0], 0) + 1
    case_ops = sorted({ln.split()[0] for ln in CASES})
    no_oracle = [o for o in case_ops if o not in ORACLE_OPS_SEEN]
    print("  coverage    : " + ", ".join(f"{k} x{v}" for k, v in sorted(ops.items())))
    print(f"  oracles     : {len(ORACLE_OPS_SEEN)} op(s) have a real oracle, "
          f"{len(case_ops)} case op(s): " + ("all covered" if not no_oracle
                                             else f"MISSING {no_oracle}"))
    if no_oracle:
        print(f"\n  FAIL       : no oracle branch for {no_oracle} - the case would pass "
              f"on python/cpp agreement alone")
        return 1
    print("\n  CODE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
