#!/usr/bin/env python3
"""Code gate for _posts/2026-11-25-backtracking.md.

Nothing here tests a hand-copied solution: every ```python / ```cpp block is
regex-extracted from the post itself, compiled, and then exercised.

What is checked, and against what external reference
  1. extraction: the anchored fence pattern (^```python … ^```$) must find the
     same blocks as the loose one, and the python/cpp block counts must match
  2. permutations / subsets / combinations are compared, as *sets of tuples*,
     with `itertools` — normalised with `sorted(map(tuple, ...))`, which keeps
     the order inside each solution.  (Sorting inside the rows too, as an
     earlier version of this gate did, silently accepts e.g. six copies of
     [1,2,3] as "all permutations of [1,2,3]" — so the strict form is used.)
  3. combination sum gets two independent oracles: a local brute force over
     candidate multisets, and itertools.combinations_with_replacement
  4. every number the prose quotes is re-measured here, so a prose number can
     never drift away from the code that produced it:
       §1.4  permute(n=7) = 13700 calls / 5040 permutations, ratio ≈ 2.7
       §3.4  the four-row dedup cost table (calls for both strategies + solutions)
       §4.2  the five-row pruning table (solutions, naive calls, pruned calls)
             plus the "7.2×" quoted for the last row
       §5.1  the n = 0 / n = 1 boundary table, value by value
       §5.2  the duplicate-input table, all six columns
       §6.1  the ten N-Queens counts (n = 1…10) against a brute force over
             itertools.permutations, the n = 0 boundary, the n = 4 solution set
             as column tuples, the call count at n = 8, and the three broken
             variants whose wrong answers the prose quotes (mixed-up diagonal
             key, abs() on the anti-diagonal, missing undo)
       §6.2  the bitmask variant: same counts for n = 1…10, same call count at
             n = 8, and the same solutions when the boards are compared
       §6.3  sudoku against an independent exact-cover (Algorithm X) solver:
             the classical puzzle, the "hardest" puzzle, the empty grid, an
             unsolvable-but-locally-consistent puzzle, uniqueness, givens kept,
             and the two mutants the prose quotes (wrong box index, and the
             missing `board[r][c] = "."` undo with its 34 conflicts)
       §7.1  力扣 698 / 473: the four-row payoff table is *parsed out of the post*
             and every cell re-measured (post's code / without the same-sum-bucket
             skip / sorted ascending / bitmask-DP reference), plus the two broken
             variants the prose quotes (break instead of continue: 268 of 3000
             random inputs wrong; a missing buckets undo: 16), each with its
             minimal counterexample searched for from scratch
       §7.2  力扣 416: the same treatment for the eight-row table (post's code /
             ascending / without same-layer dedup / boolean-DP reference), plus the
             parity guard (dropped: 1041 of 3000 wrong, minimal counterexample
             [1,1,1]) and break in a descending array (129 wrong, minimal
             counterexample [1,1,2,2]), and the cross-check that 698 with k = 2
             and 416 agree on 1500 random inputs
     The §7 oracles are independent of the post: a bitmask DP and a k^n
     assignment brute force on the partition side, a boolean DP and a 2^n
     enumeration on the subset-sum side; each pair is checked against itself
     before being used as a reference.  Every positive §7 answer is then redone
     by an output-only witness walker that must produce the explicit groups /
     subset (the §6 counterpart of "only the board is validated, not the search").
     Recursion calls are counted from the outside with sys.setprofile, so the
     numbers come from the post's own `backtrack` closures.
  5. C++ side, two translation units, both with -Wall -Wextra -Werror -O1:
       TU-A: the post's blocks + cpp_harness.cpp (solutions, counts, boundaries)
       TU-B: the post's blocks + a driver whose expected solution sets are
             generated *at gate runtime* from Python's itertools, so the C++
             side is cross-checked against an external reference and not just
             against literals written by hand.  The N-Queens counters and the
             sudoku grids are generated the same way (permutation brute force
             and the exact-cover solver below).

  The post does contain board-type problems (N-Queens in §6.1/§6.2, sudoku in
  §6.3), so the "board validator" requirement applies and is enforced in section
  8: every board the post hands back is re-validated from the outside by code
  that never looks at the search (no two queens share a column or a diagonal;
  every sudoku row, column and box is a permutation of 1…9 and the givens are
  untouched).  If those blocks disappear from the post again, section 8 fails —
  it does not print a note and move on.

Usage: /opt/miniconda3/bin/python3 verify_code.py
Exit:  0 all green, 1 otherwise.
"""
import itertools
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]          # <repo>/assets/blog/<slug>-<date> -> <repo>
POST = REPO / "_posts" / "2026-11-25-backtracking.md"
HARNESS = HERE / "cpp_harness.cpp"

EXPECTED_PY_BLOCKS = 12
EXPECTED_CPP_BLOCKS = 12

PY_RE = re.compile(r"^```python[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
CPP_RE = re.compile(r"^```cpp[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
LOOSE_PY_RE = re.compile(r"```python[ \t]*\n(.*?)```", re.S)
LOOSE_CPP_RE = re.compile(r"```cpp[ \t]*\n(.*?)```", re.S)

CXX = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1"]


def extract(pattern, text):
    return [m.group(1) for m in pattern.finditer(text)]


def norm(rows):
    """The Lead's normalisation: sort the collection, keep each solution intact."""
    return sorted(map(tuple, rows))


def norm_unique(rows):
    return sorted({tuple(row) for row in rows})


class CallCounter:
    """Counts calls into the post's `backtrack` closures from the outside.

    Profiling hooks see every call event, so the counts below are produced by the
    post's own code instead of by an instrumented copy of it.
    """

    def __init__(self):
        self.n = 0

    def __call__(self, frame, event, arg):
        if event == "call" and frame.f_code.co_name == "backtrack":
            self.n += 1

    def count(self, fn, *args, **kwargs):
        self.n = 0
        sys.setprofile(self)
        try:
            out = fn(*args, **kwargs)
        finally:
            sys.setprofile(None)
        return out, self.n


# ------------------------------------------------------------------ C++ glue
CPP_ORACLE_PRELUDE = r"""
// ---- generated by verify_code.py: expectations come from Python's itertools ----
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

static int g_pass = 0;
static int g_fail = 0;

// Only the outer collection is sorted: the order inside a solution is part of
// the answer, so it must match exactly.
static std::vector<std::vector<int>> canon(std::vector<std::vector<int>> v) {
    std::sort(v.begin(), v.end());
    return v;
}

static void checkSet(const std::string& name,
                     const std::vector<std::vector<int>>& got,
                     const std::vector<std::vector<int>>& want) {
    if (canon(got) == canon(want)) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << " (got " << got.size()
                  << " rows, want " << want.size() << ")\n";
    }
}

static void checkInt(const std::string& name, long long got, long long want) {
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << " (got " << got << ", want " << want << ")\n";
    }
}

// Order inside each row matters (row r -> column of the queen), the order of
// the solutions themselves does not.
static void checkSeqSorted(const std::string& name,
                           std::vector<std::vector<int>> got,
                           std::vector<std::vector<int>> want) {
    std::sort(got.begin(), got.end());
    std::sort(want.begin(), want.end());
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << " (got " << got.size()
                  << " rows, want " << want.size() << ")\n";
    }
}

// Nothing is normalised here: a sudoku grid is compared cell by cell.
static void checkExact(const std::string& name,
                       const std::vector<std::vector<int>>& got,
                       const std::vector<std::vector<int>>& want) {
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << " (grid differs from the reference)\n";
    }
}

// (row -> column of the queen) for a returned board collection
static std::vector<std::vector<int>> boardCols(
        const std::vector<std::vector<std::string>>& boards) {
    std::vector<std::vector<int>> out;
    for (const std::vector<std::string>& board : boards) {
        std::vector<int> cols;
        for (const std::string& row : board) {
            int at = -1;
            for (std::size_t j = 0; j < row.size(); ++j) {
                if (row[j] == 'Q') { at = static_cast<int>(j); break; }
            }
            cols.push_back(at);
        }
        out.push_back(cols);
    }
    return out;
}

// Independent validator: two queens must not share a column or a diagonal.
static bool validQueens(const std::vector<std::vector<std::string>>& boards) {
    for (const std::vector<std::string>& board : boards) {
        const int n = static_cast<int>(board.size());
        std::vector<int> cols;
        for (const std::string& row : board) {
            if (static_cast<int>(row.size()) != n) return false;
            int queens = 0, at = -1;
            for (int j = 0; j < n; ++j) {
                if (row[j] == 'Q') { ++queens; at = j; }
            }
            if (queens != 1) return false;
            cols.push_back(at);
        }
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                if (cols[i] == cols[j]) return false;
                if (std::abs(cols[i] - cols[j]) == j - i) return false;
            }
        }
    }
    return true;
}

// Independent validator: every row, column and 3x3 box holds 1..9 exactly once.
static bool validSudoku(const std::vector<std::string>& grid) {
    if (grid.size() != 9) return false;
    for (const std::string& row : grid) {
        if (row.size() != 9) return false;
    }
    for (int i = 0; i < 9; ++i) {
        bool rowSeen[10] = {}, colSeen[10] = {}, boxSeen[10] = {};
        for (int j = 0; j < 9; ++j) {
            const int rv = grid[i][j] - '0';
            const int cv = grid[j][i] - '0';
            const int bv = grid[(i / 3) * 3 + j / 3][(i % 3) * 3 + j % 3] - '0';
            if (rv < 1 || rv > 9 || cv < 1 || cv > 9 || bv < 1 || bv > 9) return false;
            if (rowSeen[rv] || colSeen[cv] || boxSeen[bv]) return false;
            rowSeen[rv] = colSeen[cv] = boxSeen[bv] = true;
        }
    }
    return true;
}

// solveSudoku() works in place: fold the verdict and the grid into one row list
static std::vector<std::vector<int>> sudokuCase(std::vector<std::string> board) {
    const bool ok = solveSudoku(board);
    std::vector<std::vector<int>> out;
    out.push_back({ok ? 1 : 0});
    for (const std::string& row : board) {
        std::vector<int> digits;
        for (char ch : row) digits.push_back(ch == '.' ? 0 : ch - '0');
        out.push_back(digits);
    }
    return out;
}

// the same, but only "is the returned board valid" (for the many-solution case)
static long long sudokuValid(std::vector<std::string> board) {
    const bool ok = solveSudoku(board);
    return (ok && validSudoku(board)) ? 1 : 0;
}
"""

CPP_ORACLE_MAIN_HEAD = """
int main() {
"""

CPP_ORACLE_MAIN_TAIL = """
    std::cout << "  cpp oracle    : " << g_pass << "/" << (g_pass + g_fail)
              << " pass\\n";
    return g_fail == 0 ? 0 : 1;
}
"""


def cpp_rows(rows):
    """[[1,2],[2]] -> '{{1, 2}, {2}}' (empty collection -> '{}')."""
    return "{" + ", ".join(
        "{" + ", ".join(str(x) for x in row) + "}" for row in rows) + "}"


def cpp_call(name, ints):
    return f"{name}({{{', '.join(str(i) for i in ints)}}})"


def oracle_cases():
    """(label, C++ call expression, expected rows) with expectations from itertools."""
    cases = []

    # permute: n = 0 … 5, the whole solution set
    for n in range(6):
        nums = list(range(1, n + 1))
        cases.append((f"permute({nums})", cpp_call("permute", nums),
                      [list(p) for p in itertools.permutations(nums)]))

    # subsets: every node is an answer, so k runs over 0 … n
    for n in range(6):
        nums = list(range(1, n + 1))
        want = [list(c) for k in range(n + 1)
                for c in itertools.combinations(nums, k)]
        cases.append((f"subsets({nums})", cpp_call("subsets", nums), want))

    # combine: k = 0, k = n, and k > n (unsolvable)
    for n in range(6):
        for k in range(n + 3):
            want = [list(c) for c in itertools.combinations(range(1, n + 1), k)]
            cases.append((f"combine({n},{k})", f"combine({n}, {k})", want))

    # duplicate inputs (LeetCode 47 / 90)
    dup_inputs = ([1], [1, 1], [1, 1, 2], [1, 1, 1, 2],
                  [1, 2, 2, 3, 3], [1, 1, 2, 2, 3, 3])
    for nums in dup_inputs:
        cases.append((f"permuteUnique({nums})", cpp_call("permuteUnique", nums),
                      [list(p) for p in set(itertools.permutations(nums))]))
        # subsetsWithDup must return *distinct* subsets, so the expectation is the
        # set of combinations — plain combinations() enumerates positionally
        # distinct copies of the same subset when the input repeats
        distinct = sorted({c for k in range(len(nums) + 1)
                           for c in itertools.combinations(sorted(nums), k)})
        cases.append((f"subsetsWithDup({nums})", cpp_call("subsetsWithDup", nums),
                      [list(c) for c in distinct]))

    # combination sum, section 4.2 table + unsolvable / empty-target edges
    cand_cases = [([2, 3, 6, 7], 7), ([2, 3, 5], 8), ([3, 4, 7, 8], 11),
                  ([2, 3, 5, 7, 11, 13], 30), ([1, 2, 3, 4, 5, 6, 7, 8], 20),
                  ([2, 3], 1), ([2, 3], 0)]
    for cand, target in cand_cases:
        want = [list(c) for k in range(target // min(cand) + 1)
                for c in itertools.combinations_with_replacement(cand, k)
                if sum(c) == target]
        args = f"{{{', '.join(str(c) for c in cand)}}}, {target}"
        cases.append((f"combinationSumPruned({cand},{target})",
                      f"combinationSumPruned({args}).first", want))
        if len(want) <= 5:
            cases.append((f"combinationSumNaive({cand},{target})",
                          f"combinationSumNaive({args}).first", want))
    return cases


def cpp_board(puzzle):
    """['53..7....', ...] -> a C++ initializer list of std::string."""
    return "{" + ", ".join(json.dumps(row) for row in puzzle) + "}"


def oracle_board_lines():
    """C++ statements for §6 whose expectations come from the Python references.

    Nothing here is a hand-written constant: the N-Queens counters come from the
    permutation brute force, the sudoku grids from the exact-cover solver, and
    the boards are re-validated inside C++ by validQueens/validSudoku, which
    never look at the search.
    """
    lines = []
    for n in range(1, 11):
        want = len(n_queens_reference(n))
        lines.append(f'    checkInt("totalNQueens({n})", totalNQueens({n}), {want});\n')
        lines.append(f'    checkInt("totalNQueensBitmask({n})", '
                     f'totalNQueensBitmask({n}), {want});\n')
    lines.append('    checkSeqSorted("solveNQueens(4)", boardCols(solveNQueens(4)), '
                 + cpp_rows([list(p) for p in n_queens_reference(4)]) + ');\n')
    lines.append('    checkSeqSorted("solveNQueens(0)", boardCols(solveNQueens(0)), '
                 '{{}});\n')
    lines.append('    checkInt("validQueens(solveNQueens(8))", '
                 'validQueens(solveNQueens(8)) ? 1 : 0, 1);\n')
    for name, puzzle in (("经典题", CLASSIC), ("最难数独", HARDEST)):
        ref = exact_cover_solutions(puzzle, limit=2)
        want = [[1]] + [[0 if ch == "." else int(ch) for ch in row] for row in ref[0]]
        lines.append(f'    checkExact("solveSudoku({name})", '
                     f'sudokuCase({cpp_board(puzzle)}), {cpp_rows(want)});\n')
    lines.append('    checkInt("solveSudoku(全空盘) 解出的盘合法", '
                 f'sudokuValid({cpp_board(EMPTY_GRID)}), 1);\n')
    unsolvable = with_cell(CLASSIC, 0, 2, "1")
    want = [[0]] + [[0 if ch == "." else int(ch) for ch in row] for row in unsolvable]
    lines.append('    checkExact("solveSudoku(无解盘)", '
                 f'sudokuCase({cpp_board(unsolvable)}), {cpp_rows(want)});\n')
    return lines


def oracle_partition_lines(post):
    """C++ statements for §7 whose expectations come from the DP references.

    The rows are read out of the post's own tables, so a drifted table cell makes
    the C++ side fail too; the numbers handed to checkInt are never literals from
    the prose but the output of dp_partition_k / dp_subset_sum at gate runtime.
    """
    lines = []
    cases = []
    for nums, k, _ans, _cells in table_rows_parsed(post, "去掉同和桶去重", with_k=True):
        cases.append((nums, k, dp_partition_k(nums, k)[0]))
    for nums, k in (([1, 2, 3, 4], 3), ([1, 1, 2, 2, 2], 4), ([3, 3, 3, 3, 4], 4),
                    ([1, 1], 2), ([2, 2, 2, 2, 3, 3], 2)):
        cases.append((nums, k, dp_partition_k(nums, k)[0]))
    for nums, k, want in cases:
        lines.append(f'    checkInt("canPartitionKSubsets({nums}, {k})", '
                     f'{cpp_call("canPartitionKSubsets", nums)[:-1]}, {k})'
                     f' ? 1 : 0, {1 if want else 0});\n')
    want = dp_subset_sum([1, 5, 11, 5])[0]
    lines.append('    checkInt("canPartition({1, 5, 11, 5})", '
                 f'{cpp_call("canPartition", [1, 5, 11, 5])}, {1 if want else 0});\n')
    for nums, _k, _ans, _cells in table_rows_parsed(post, "去掉同层去重", with_k=False):
        want = dp_subset_sum(nums)[0]
        lines.append(f'    checkInt("canPartition({nums})", '
                     f'{cpp_call("canPartition", nums)}, {1 if want else 0});\n')
    return lines


def python_oracle_cases():
    """(label, callable, expected rows) — the same ladder, against the post's python."""
    cases = []
    for n in range(6):
        nums = list(range(1, n + 1))
        cases.append((f"permute({nums})", lambda ns, v=nums: ns["permute"](list(v)),
                      [list(p) for p in itertools.permutations(nums)]))
    for n in range(6):
        nums = list(range(1, n + 1))
        cases.append((f"subsets({nums})", lambda ns, v=nums: ns["subsets"](list(v)),
                      [list(c) for k in range(n + 1)
                       for c in itertools.combinations(nums, k)]))
    for n in range(6):
        for k in range(n + 3):
            cases.append((f"combine({n},{k})",
                          lambda ns, a=n, b=k: ns["combine"](a, b),
                          [list(c) for c in itertools.combinations(range(1, n + 1), k)]))
    for nums in ([1], [1, 1], [1, 1, 2], [1, 1, 1, 2], [1, 2, 2, 3, 3],
                 [1, 1, 2, 2, 3, 3], [-1, -1, 0]):
        cases.append((f"permute_unique({nums})",
                      lambda ns, v=nums: ns["permute_unique"](list(v)),
                      [list(p) for p in set(itertools.permutations(nums))]))
        distinct = sorted({c for k in range(len(nums) + 1)
                           for c in itertools.combinations(sorted(nums), k)})
        cases.append((f"subsets_with_dup({nums})",
                      lambda ns, v=nums: ns["subsets_with_dup"](list(v)),
                      [list(c) for c in distinct]))
    return cases


# ------------------------------------------- §6 board references (independent)
N_QUEENS_REF = {}
TEXT_RE = re.compile(r"^```text[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)

CLASSIC = ["53..7....", "6..195...", ".98....6.", "8...6...3", "4..8.3..1",
           "7...2...6", ".6....28.", "...419..5", "....8..79"]
HARDEST = ["8........", "..36.....", ".7..9.2..", ".5...7...", "....457..",
           "...1...3.", "..1....68", "..85...1.", ".9....4.."]
EMPTY_GRID = ["." * 9 for _ in range(9)]


def with_cell(puzzle, r, c, value):
    """A copy of the puzzle with one cell overwritten (row-wise, not column-wise!)."""
    return [row[:c] + value + row[c + 1:] if i == r else row
            for i, row in enumerate(puzzle)]


def locally_consistent(puzzle):
    """Every row / column / box has no repeated digit (partial grids included)."""
    units = []
    units += [[(r, c) for c in range(9)] for r in range(9)]
    units += [[(r, c) for r in range(9)] for c in range(9)]
    units += [[(br * 3 + dr, bc * 3 + dc) for dr in range(3) for dc in range(3)]
              for br in range(3) for bc in range(3)]
    for unit in units:
        values = [puzzle[r][c] for r, c in unit if puzzle[r][c] != "."]
        if len(values) != len(set(values)):
            return False
    return True


def n_queens_reference(n):
    """Every permutation of column numbers, checked pairwise with abs().

    Independent of the post twice over: no recursion and no pruning at all, and
    the diagonal predicate is `abs(c1 - c2) == r2 - r` instead of two invariant
    sets.  n = 10 costs about 1.3 s, so the whole ladder n = 0…10 is cheap; the
    results are cached because the C++ oracle generator wants them too.
    """
    if n not in N_QUEENS_REF:
        solutions = []
        for perm in itertools.permutations(range(n)):
            if all(abs(perm[r] - perm[r2]) != r2 - r
                   for r in range(n) for r2 in range(r + 1, n)):
                solutions.append(tuple(perm))
        N_QUEENS_REF[n] = solutions
    return N_QUEENS_REF[n]


def render_board(perm):
    """(1, 3, 0, 2) -> ['.Q..', '...Q', 'Q...', '..Q.']"""
    return ["." * c + "Q" + "." * (len(perm) - 1 - c) for c in perm]


def board_to_columns(board):
    """Read a returned ASCII board back into (row -> column) form."""
    cols = []
    for row in board:
        if row.count("Q") != 1:
            raise AssertionError(f"row does not hold exactly one queen: {row!r}")
        cols.append(row.index("Q"))
    return tuple(cols)


def queens_violations(board):
    """External validator for one board: lists the constraints it breaks."""
    cols = board_to_columns(board)          # raises if a row holds != 1 queen
    n = len(board)
    bad = []
    if any(len(row) != n for row in board):
        bad.append(f"board is not {n}x{n}")
    if len(set(cols)) != n:
        bad.append("two queens share a column")
    if len({r + c for r, c in enumerate(cols)}) != n:
        bad.append('two queens share a "\\" diagonal')
    if len({r - c for r, c in enumerate(cols)}) != n:
        bad.append('two queens share a "/" diagonal')
    return bad


SUDOKU_UNITS = ([("cell", r, c) for r in range(9) for c in range(9)]
                + [("row", r, v) for r in range(9) for v in range(1, 10)]
                + [("col", c, v) for c in range(9) for v in range(1, 10)]
                + [("box", b, v) for b in range(9) for v in range(1, 10)])


def sudoku_units_of(r, c, v):
    return (("cell", r, c), ("row", r, v), ("col", c, v),
            ("box", (r // 3) * 3 + c // 3, v))


def exact_cover_solutions(puzzle, limit=2):
    """Algorithm X with an MRV column choice — independent of the post's scan.

    Only the intersection structure of "one digit per cell" plus "each digit
    once per row / column / box" is used; the post's first-empty-cell scan and
    its three sets play no part.  A validator can prove that a returned grid is
    *a* solution, but only a solver like this can answer the two questions the
    prose quotes: how many solutions a puzzle has (uniqueness), and whether an
    unsolvable-looking puzzle really has none.
    """
    candidates = [(r, c, v) for r in range(9) for c in range(9)
                  for v in ([int(puzzle[r][c])] if puzzle[r][c] != "."
                            else range(1, 10))]
    remaining = {u: set() for u in SUDOKU_UNITS}
    for cand in candidates:
        for u in sudoku_units_of(*cand):
            remaining[u].add(cand)
    solutions, chosen = [], []

    def backtrack(rem):
        if len(solutions) >= limit:
            return
        if not rem:
            grid = [["."] * 9 for _ in range(9)]
            for r, c, v in chosen:
                grid[r][c] = str(v)
            solutions.append(["".join(row) for row in grid])
            return
        unit = min(rem, key=lambda u: len(rem[u]))
        if not rem[unit]:
            return
        for cand in sorted(rem[unit]):
            nxt = {u: set(s) for u, s in rem.items()}
            ok = True
            for u in sudoku_units_of(*cand):
                if u not in nxt:
                    ok = False
                    break
                for other in list(nxt[u]):
                    for y in sudoku_units_of(*other):
                        if y in nxt and y != u:
                            nxt[y].discard(other)
                del nxt[u]
            if not ok:
                continue
            chosen.append(cand)
            backtrack(nxt)
            chosen.pop()
            if len(solutions) >= limit:
                return

    backtrack(remaining)
    return solutions


def sudoku_conflicts(grid):
    """Duplicate digit occurrences over the 27 units: 2nd/3rd copies count."""
    units = []
    units += [[(r, c) for c in range(9)] for r in range(9)]
    units += [[(r, c) for r in range(9)] for c in range(9)]
    units += [[(br * 3 + dr, bc * 3 + dc) for dr in range(3) for dc in range(3)]
              for br in range(3) for bc in range(3)]
    extra = 0
    for unit in units:
        values = [grid[r][c] for r, c in unit]
        for v in set(values):
            if v != ".":
                extra += max(0, values.count(v) - 1)
    return extra


def conflict_cells(grid):
    """Distinct cells that share their digit with another cell in some unit."""
    units = []
    units += [[(r, c) for c in range(9)] for r in range(9)]
    units += [[(r, c) for r in range(9)] for c in range(9)]
    units += [[(br * 3 + dr, bc * 3 + dc) for dr in range(3) for dc in range(3)]
              for br in range(3) for bc in range(3)]
    cells = set()
    for unit in units:
        where = {}
        for cell in unit:
            where.setdefault(grid[cell[0]][cell[1]], []).append(cell)
        for value, spots in where.items():
            if value != "." and len(spots) > 1:
                cells.update(spots)
    return len(cells)


def sudoku_violations(puzzle, grid):
    """External validator: 27 units are permutations of 1…9, givens untouched."""
    bad = []
    if len(grid) != 9 or any(len(row) != 9 for row in grid):
        return [f"board is not 9x9: {len(grid)} rows"]
    for i in range(9):
        if sorted(grid[i]) != [str(d) for d in range(1, 10)]:
            bad.append(f"row {i} is not a permutation of 1..9: {grid[i]}")
    for c in range(9):
        col = [grid[r][c] for r in range(9)]
        if sorted(col) != [str(d) for d in range(1, 10)]:
            bad.append(f"column {c} is not a permutation of 1..9: {''.join(col)}")
    for br in range(3):
        for bc in range(3):
            box = [grid[br * 3 + dr][bc * 3 + dc]
                   for dr in range(3) for dc in range(3)]
            if sorted(box) != [str(d) for d in range(1, 10)]:
                bad.append(f"box ({br},{bc}) is not a permutation of 1..9: {''.join(box)}")
    for r in range(9):
        for c in range(9):
            if puzzle[r][c] != "." and grid[r][c] != puzzle[r][c]:
                bad.append(f"given ({r},{c}) changed: {puzzle[r][c]} -> {grid[r][c]}")
    return bad


# ------------------------- §7 partition / subset-sum references (independent)
def dp_partition_k(nums, k):
    """Exact bitmask-DP reference for 698 / 473 — no search at all.

    `reach[mask]` is the running sum (mod target) of the group being filled; an
    element may be appended only while the group stays within `target`, and the
    full mask is a partition exactly when its running sum comes back to 0.
    Returns (answer, inner-loop steps), the step count being the number the
    fourth column of the §7.1 table quotes.
    """
    total = sum(nums)
    if k <= 0:
        return False, 0
    if k == 1:
        return True, 0
    if total % k:
        return False, 0
    target = total // k
    n = len(nums)
    if n == 0:
        return True, 0
    reach = [-1] * (1 << n)
    reach[0] = 0
    steps = 0
    for mask in range(1 << n):
        cur = reach[mask]
        if cur < 0:
            continue
        for i in range(n):
            steps += 1
            if mask & (1 << i) or cur + nums[i] > target:
                continue
            nxt = mask | (1 << i)
            if reach[nxt] < 0:
                reach[nxt] = (cur + nums[i]) % target
    return reach[(1 << n) - 1] == 0, steps


def brute_partition_k(nums, k):
    """Exhaustive k^n assignment brute force — slow, but impossible to get wrong."""
    if k <= 0:
        return False
    if k == 1:
        return True
    total = sum(nums)
    if total % k:
        return False
    target = total // k
    for assign in itertools.product(range(k), repeat=len(nums)):
        sums = [0] * k
        for v, b in zip(nums, assign):
            sums[b] += v
        if all(s == target for s in sums):
            return True
    return False


def dp_subset_sum(nums):
    """Boolean-DP reference for 416 (no search): (answer, inner-loop steps)."""
    total = sum(nums)
    if total % 2:
        return False, 0
    half = total // 2
    dp = [False] * (half + 1)
    dp[0] = True
    steps = 0
    for v in nums:
        for s in range(half, v - 1, -1):
            steps += 1
            if dp[s - v]:
                dp[s] = True
    return dp[half], steps


def brute_subset_sum(nums):
    """2^n enumeration of every subset — the slow, obviously-correct oracle."""
    n = len(nums)
    total = sum(nums)
    return any(sum(nums[i] for i in range(n) if mask >> i & 1) * 2 == total
               for mask in range(1 << n))


def table_rows(md, header):
    """Rows (cell lists) of the first markdown table whose header contains `header`."""
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if header in line and line.strip().startswith("|"):
            rows = []
            for line2 in lines[i + 2:]:
                if not line2.strip().startswith("|"):
                    break
                rows.append([c.strip() for c in line2.strip().strip("|").split("|")])
            return rows
    raise AssertionError(f"markdown table not found: {header!r}")


def table_rows_parsed(md, header, with_k):
    """[(nums, k or None, expected answer or None, [cells…]), …] for a §7 table."""
    out = []
    for cells in table_rows(md, header):
        label = cells[0]
        m = re.search(r"\[([\d,\s]+)\]", label)
        if m is None:
            raise AssertionError(f"§7 table row without a number list: {label!r}")
        nums = [int(x) for x in m.group(1).split(",") if x.strip() != ""]
        k = None
        mk = re.search(r"k\s*=\s*(\d+)", label)
        if mk:
            k = int(mk.group(1))
        elif with_k:
            raise AssertionError(f"§7 table row without k: {label!r}")
        answer = None
        ma = re.search(r"(True|False)", label)
        if ma:
            answer = ma.group(1) == "True"
        out.append((nums, k, answer, [int(c) for c in cells[1:]]))
    return out


def minimal_counterexample(fn, ref, ks=(2, 3, 4), max_n=9, values=range(1, 8)):
    """Smallest (nums, k) where fn disagrees with ref — searched from scratch."""
    for n in range(1, max_n + 1):
        for nums in itertools.combinations_with_replacement(values, n):
            for k in ks:
                if k > n:
                    continue
                if fn(list(nums), k) != ref(list(nums), k):
                    return list(nums), k
    return None, None


def minimal_subset_counterexample(fn, ref, max_n=9, values=range(1, 8)):
    """Smallest nums where the 416 variant fn disagrees with ref."""
    for n in range(1, max_n + 1):
        for nums in itertools.combinations_with_replacement(values, n):
            if fn(list(nums)) != ref(list(nums)):
                return list(nums)
    return None


def partition_witness(nums, k):
    """Re-derive an explicit k-way split from the DP table — output-only check.

    Returns the sorted list of bucket sums when a split exists and None when it
    does not, so a positive answer can be validated without looking at the
    search at all (the same spirit as the board validators of §6).
    """
    total = sum(nums)
    if k <= 0 or total % k:
        return None
    target = total // k
    n = len(nums)
    if n == 0:
        return [0] * k if k == 1 else None
    reach = [False] * (1 << n)
    reach[0] = True
    order = [0] * (1 << n)
    for mask in range(1 << n):
        if not reach[mask]:
            continue
        cur = sum(nums[i] for i in range(n) if mask >> i & 1) % target
        for i in range(n):
            if mask >> i & 1 or cur + nums[i] > target:
                continue
            nxt = mask | (1 << i)
            if not reach[nxt]:
                reach[nxt] = True
                order[nxt] = i
    if not reach[(1 << n) - 1]:
        return None
    sums = []
    mask = (1 << n) - 1
    running = 0
    while mask:
        i = order[mask]
        running += nums[i]
        mask ^= 1 << i
        if running == target:
            sums.append(running)
            running = 0
    if running != 0 or len(sums) != k:
        raise AssertionError(f"witness walk failed for {nums} k={k}: {sums}")
    return sorted(sums)


def subset_witness(nums):
    """An explicit subset with sum == half, from a 2-D boolean table — output-only."""
    total = sum(nums)
    if total % 2:
        return None
    half = total // 2
    n = len(nums)
    dp = [[False] * (half + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(n):
        for s in range(half + 1):
            dp[i + 1][s] = dp[i][s] or (s >= nums[i] and dp[i][s - nums[i]])
    if not dp[n][half]:
        return None
    chosen, s = [], half
    for i in range(n - 1, -1, -1):
        if not dp[i][s]:
            chosen.append(nums[i])
            s -= nums[i]
    if s != 0:
        raise AssertionError(f"witness walk failed for {nums}: {chosen}")
    return chosen


def mutant_namespace(py_blocks, index, patches):
    """Compile one post block with literal text patches applied.

    The mutant is built from the post's own source text, so it cannot drift
    away from the block that the prose describes; each anchor must appear
    exactly the expected number of times or the gate fails loudly.
    """
    src = py_blocks[index]
    for old, new, times in patches:
        found = src.count(old)
        if found != times:
            raise AssertionError(
                f"mutant anchor appears {found}x, expected {times}x: {old!r}")
        src = src.replace(old, new)
    ns = {"__name__": f"post_code_mutant_{index}"}
    exec(compile(src, f"<mutant block {index + 1}>", "exec"), ns)
    return ns


def main() -> int:
    if not POST.exists():
        print(f"  post not found: {POST}")
        return 1
    post = POST.read_text(encoding="utf-8")
    py = extract(PY_RE, post)
    cpp = extract(CPP_RE, post)

    problems = []
    print(f"  post          : {POST.name} ({len(post):,} chars)")
    print(f"  python blocks : {len(py)}   cpp blocks: {len(cpp)}")

    if len(py) != EXPECTED_PY_BLOCKS or len(cpp) != EXPECTED_CPP_BLOCKS:
        problems.append(f"expected {EXPECTED_PY_BLOCKS} python / {EXPECTED_CPP_BLOCKS} "
                        f"cpp blocks, found {len(py)} / {len(cpp)}")
    if len(py) != len(cpp):
        problems.append(f"python and cpp block counts differ: {len(py)} vs {len(cpp)}")
    if len(extract(LOOSE_PY_RE, post)) != len(py) or \
       len(extract(LOOSE_CPP_RE, post)) != len(cpp):
        problems.append("anchored fence pattern finds fewer blocks than the loose one "
                        "(a fence is probably not at the start of a line)")
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        return 1

    for i, block in enumerate(py, 1):
        try:
            compile(block, f"<py block {i}>", "exec")
        except SyntaxError as e:
            problems.append(f"python block {i} does not compile: line {e.lineno}: {e.msg}")
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        return 1

    ns = {"__name__": "post_code"}
    exec(compile("\n".join(py), str(POST), "exec"), ns)

    fails = []
    n_cases = 0

    def brief(value, limit=240):
        text = repr(value)
        return text if len(text) <= limit else text[:limit] + f" … (+{len(text) - limit} chars)"

    def check(name, got, want):
        nonlocal n_cases
        n_cases += 1
        if got != want:
            fails.append(name)
            print(f"  FAIL  {name}:\n          got  {brief(got)}\n          want {brief(want)}")

    counter = CallCounter()

    # ---- 1. the whole solution-set ladder vs itertools (strict normalisation) --
    ladder = python_oracle_cases()
    for label, call, want in ladder:
        check(f"{label} vs itertools (strict set comparison)",
              norm(call(ns)), norm(want))
    print(f"  ok  [py] {len(ladder)} 个解集与 itertools 严格对拍"
          f"（sorted(map(tuple, ...))，保留解内顺序；n=0…5 全枚举）")

    # ---- 2. section 1.4: the n = 7 anchor ----------------------------------
    got7, calls7 = counter.count(ns["permute"], list(range(7)))
    check("permute(n=7) solution count (post: 5040)", len(got7), 5040)
    check("permute(n=7) recursion calls (post: 13700)", calls7, 13700)
    check("permute(n=7) calls/solutions ratio (post: ≈2.7)",
          round(calls7 / len(got7), 1), 2.7)
    check("permute(n=7) vs itertools", norm(got7),
          norm([list(p) for p in itertools.permutations(range(7))]))
    check("counter really counted something", calls7 > 0, True)
    print(f"  ok  [py] §1.4 锚点：permute(n=7) {calls7} 次递归调用 / {len(got7)} 个解"
          f"，比值 {calls7 / len(got7):.2f}")

    # ---- 3. section 3.4: the dedup cost table ------------------------------
    dup_table = [  # input, naive calls, same-layer-dedup calls, distinct solutions
        ((1, 1, 2), 16, 9, 3),
        ((1, 1, 1, 2), 65, 14, 4),
        ((1, 2, 2, 3, 3), 326, 90, 30),
        ((1, 1, 2, 2, 3, 3), 1957, 271, 90),
    ]
    for nums, naive_calls, dedup_calls, n_sol in dup_table:
        nums = list(nums)
        raw, c_raw = counter.count(ns["permute"], nums)
        uniq, c_uniq = counter.count(ns["permute_unique"], nums)
        check(f"§3.4 permute{tuple(nums)} calls (post {naive_calls})", c_raw, naive_calls)
        check(f"§3.4 permute_unique{tuple(nums)} calls (post {dedup_calls})",
              c_uniq, dedup_calls)
        check(f"§3.4 permute_unique{tuple(nums)} solutions (post {n_sol})",
              len(uniq), n_sol)
        check(f"permute_unique{tuple(nums)} vs set(itertools.permutations)",
              norm(uniq), norm([list(p) for p in set(itertools.permutations(nums))]))
        check(f"permute{tuple(nums)} really enumerates repeated solutions",
              len(raw) > len(set(itertools.permutations(nums))), True)
        check(f"permute_unique{tuple(nums)} has no internal repeats",
              len(uniq), len(norm_unique(uniq)))
    check("§3.4 last row is '7.2×' (1957 / 271)", round(1957 / 271, 1), 7.2)
    print("  ok  [py] §3.4 去重代价表 4 行 12 个数字 + 「7.2 倍」全部实测复核")

    # ---- 4. section 4.2: pruning, measured --------------------------------
    prune_table = [  # candidates, target, solutions, naive calls, pruned calls
        ([2, 3, 6, 7], 7, 2, 28, 10),
        ([2, 3, 5], 8, 3, 23, 13),
        ([3, 4, 7, 8], 11, 3, 34, 14),
        ([2, 3, 5, 7, 11, 13], 30, 80, 1831, 672),
        ([1, 2, 3, 4, 5, 6, 7, 8], 20, 434, 6360, 2099),
    ]
    for cand, target, n_sol, naive_calls, pruned_calls in prune_table:
        r_naive, c_naive = ns["combination_sum_naive"](cand, target)
        r_pruned, c_pruned = ns["combination_sum_pruned"](cand, target)
        tag = f"{cand}/{target}"
        check(f"§4.2 {tag} naive vs pruned answer sets", norm(r_naive), norm(r_pruned))
        check(f"§4.2 {tag} solution count (post {n_sol})", len(r_pruned), n_sol)
        check(f"§4.2 {tag} naive calls (post {naive_calls})", c_naive, naive_calls)
        check(f"§4.2 {tag} pruned calls (post {pruned_calls})", c_pruned, pruned_calls)
        check(f"§4.2 {tag} pruning really reduces calls", c_pruned < c_naive, True)
        # two independent oracles: local brute force, and itertools
        brute = []

        def grow(start, remain, acc):
            if remain == 0:
                brute.append(list(acc))
                return
            for i in range(start, len(cand)):
                if cand[i] > remain:
                    continue
                acc.append(cand[i])
                grow(i, remain - cand[i], acc)
                acc.pop()

        grow(0, target, [])
        check(f"§4.2 {tag} vs local brute force", norm(r_pruned), norm(brute))
        via_itertools = [list(c) for k in range(target // min(cand) + 1)
                         for c in itertools.combinations_with_replacement(cand, k)
                         if sum(c) == target]
        check(f"§4.2 {tag} vs itertools.combinations_with_replacement",
              norm(r_pruned), norm(via_itertools))
    check("§4.2 no-solution case [2,3]/1",
          norm(ns["combination_sum_pruned"]([2, 3], 1)[0]), [])
    check("§4.2 empty target [2,3]/0 is exactly the empty combination",
          norm(ns["combination_sum_pruned"]([2, 3], 0)[0]), [()])
    print("  ok  [py] §4.2 剪枝表 5 行 15 个数字全部实测复核"
          "（两套独立参照 + 无解/空目标边界）")

    # ---- 5. sections 5.1 / 5.2: the tables, cell by cell -------------------
    check("§5.1 permute([]) is [[]]", ns["permute"]([]), [[]])
    check("§5.1 permute([1]) is [[1]]", ns["permute"]([1]), [[1]])
    check("§5.1 permute([1,2]) is [[1,2],[2,1]]",
          norm(ns["permute"]([1, 2])), norm([[1, 2], [2, 1]]))
    check("§5.1 subsets([]) is [[]]", ns["subsets"]([]), [[]])
    check("§5.1 subsets([1]) is [[], [1]]", norm(ns["subsets"]([1])), norm([[], [1]]))
    check("§5.1 subsets([1,2]) is [[], [1], [1,2], [2]]",
          norm(ns["subsets"]([1, 2])), norm([[], [1], [1, 2], [2]]))
    check("§5.1 combine(0,0) is [[]]", ns["combine"](0, 0), [[]])
    check("§5.1 combine(1,1) is [[1]]", ns["combine"](1, 1), [[1]])
    check("§5.1 combine(2,1) is [[1],[2]]", norm(ns["combine"](2, 1)), norm([[1], [2]]))
    check("§5.1 combine(3,2) is [[1,2],[1,3],[2,3]]",
          norm(ns["combine"](3, 2)), norm([[1, 2], [1, 3], [2, 3]]))
    check("§5.1 combine(k>n) is []", ns["combine"](3, 5), [])
    check("§5.1 n=3 counts: permute 6", len(ns["permute"]([1, 2, 3])), 6)
    check("§5.1 n=3 counts: subsets 8", len(ns["subsets"]([1, 2, 3])), 8)

    # input, permute, permute_unique, set(itertools), subsets, subsets_with_dup,
    # distinct subsets, "同一批解被重复枚举了几倍" (720 / 90 = 8× in the prose)
    dup_5_2 = [
        ((1, 1, 2), 6, 3, 3, 8, 6, 6, 2),
        ((1, 1, 1, 2), 24, 4, 4, 16, 8, 8, 6),
        ((1, 2, 2, 3, 3), 120, 30, 30, 32, 18, 18, 4),
        ((1, 1, 2, 2, 3, 3), 720, 90, 90, 64, 27, 27, 8),
    ]
    for (nums, n_perm, n_uniq, n_set, n_sub, n_sub_dup, n_sub_set,
         n_repeat) in dup_5_2:
        nums = list(nums)
        check(f"§5.2 permute{tuple(nums)} count (post {n_perm})",
              len(ns["permute"](nums)), n_perm)
        check(f"§5.2 permute_unique{tuple(nums)} count (post {n_uniq})",
              len(ns["permute_unique"](nums)), n_uniq)
        check(f"§5.2 set(itertools.permutations{tuple(nums)}) count (post {n_set})",
              len(set(itertools.permutations(nums))), n_set)
        check(f"§5.2 subsets{tuple(nums)} count (post {n_sub})",
              len(ns["subsets"](nums)), n_sub)
        check(f"§5.2 subsets_with_dup{tuple(nums)} count (post {n_sub_dup})",
              len(ns["subsets_with_dup"](nums)), n_sub_dup)
        distinct_subs = {c for k in range(len(nums) + 1)
                         for c in itertools.combinations(sorted(nums), k)}
        check(f"§5.2 distinct subsets of {tuple(nums)} (post {n_sub_set})",
              len(distinct_subs), n_sub_set)
        check(f"§5.2 permute/permute_unique ratio for {tuple(nums)} "
              f"(raw enumerations per distinct solution)",
              n_perm // n_set, n_repeat)
        check(f"§5.2 set(itertools.permutations) agrees with permute_unique "
              f"for {tuple(nums)}", n_set, n_uniq)
    print("  ok  [py] §5.1 / §5.2 两张表逐格复核（12 + 24 个数字）")

    # ---- 5b. §6.1 / §6.2: N-Queens against the permutation brute force -----
    queens_ref = {n: n_queens_reference(n) for n in range(11)}
    check("§6.1 table (n = 0…10): solution counts vs the permutation brute force",
          [len(ns["solve_n_queens"](n)) for n in range(11)],
          [len(queens_ref[n]) for n in range(11)])
    check("§6.1 table: the ten printed numbers, pinned as printed",
          [len(queens_ref[n]) for n in range(1, 11)],
          [1, 0, 0, 2, 10, 4, 40, 92, 352, 724])
    check("§6.1 total_n_queens agrees with solve_n_queens for n = 1…10",
          [ns["total_n_queens"](n) for n in range(1, 11)],
          [len(ns["solve_n_queens"](n)) for n in range(1, 11)])
    check("§6.1 solution sets for every n = 1…8 vs the brute force",
          {n: sorted(board_to_columns(b) for b in ns["solve_n_queens"](n))
           for n in range(1, 9)},
          {n: sorted(queens_ref[n]) for n in range(1, 9)})
    check("§6.1 n=0: the empty board is one solution (same convention as §5.1)",
          ns["solve_n_queens"](0), [[]])
    check("§6.1 the two n=4 solutions the prose prints, as column tuples",
          sorted(board_to_columns(b) for b in ns["solve_n_queens"](4)),
          [(1, 3, 0, 2), (2, 0, 3, 1)])
    text_blocks = extract(TEXT_RE, post)
    n4_block = next((b for b in text_blocks if "n=4" in b), None)
    if n4_block is None:
        problems.append("§6.1 text block with the two n=4 boards disappeared")
    else:
        rows = [re.findall(r"[.Q]{4}", ln) for ln in n4_block.splitlines()]
        board_rows = [r for r in rows if len(r) == 2]
        check("§6.1 text block prints two 4x4 boards side by side", len(board_rows), 4)
        printed = [[r[0] for r in board_rows], [r[1] for r in board_rows]]
        check("§6.1 text block: the printed boards are the two real solutions",
              sorted(printed),
              sorted([render_board(p) for p in sorted(queens_ref[4])]))
        tuples_in_text = [tuple(int(d) for d in t)
                          for t in re.findall(r"\((\d), (\d), (\d), (\d)\)", n4_block)]
        check("§6.1 text block: the column tuples printed next to the boards",
              sorted(tuples_in_text), [(1, 3, 0, 2), (2, 0, 3, 1)])
        check("§6.1 text block: each board really is the tuple printed beside it",
              dict(zip(tuples_in_text, [board_to_columns(b) for b in printed])),
              {(1, 3, 0, 2): (1, 3, 0, 2), (2, 0, 3, 1): (2, 0, 3, 1)})
    calls_per_n = [counter.count(ns["total_n_queens"], n)[1] for n in range(1, 11)]
    check("§6.1 call-count row of the table (n = 1…10)",
          calls_per_n, [2, 3, 6, 17, 54, 153, 552, 2057, 8394, 35539])
    check("§6.1 the prose ratio 8! / 2057 ≈ 19.6",
          round(40320 / calls_per_n[7], 1), 19.6)

    # the three broken variants the prose quotes, patched into the post's source
    diagonal_patches = [
        ("row - col in diag2", "abs(row - col) in diag2", 2),
        ("diag2.add(row - col)", "diag2.add(abs(row - col))", 2),
        ("diag2.discard(row - col)", "diag2.discard(abs(row - col))", 2),
    ]
    same_key_patches = [
        ("row - col in diag2", "row + col in diag2", 2),
        ("diag2.add(row - col)", "diag2.add(row + col)", 2),
        ("diag2.discard(row - col)", "diag2.discard(row + col)", 2),
    ]
    undo_patches = [
        ("cols.discard(col); diag1.discard(row + col); diag2.discard(row - col)",
         "pass  # mutant: 忘记撤销", 2),
    ]
    mutants = [
        ("§6.1 abs(row-col): under-constrained, loses solutions",
         diagonal_patches, {4: 0, 5: 4, 6: 0}),
        ("§6.1 both diagonals keyed on row+col: over-counts",
         same_key_patches, {2: 1, 4: 7, 8: 2113}),
        ("§6.1 sets never undone: every count collapses to 0",
         undo_patches, {4: 0, 6: 0, 8: 0}),
    ]
    for label, patches, expected in mutants:
        ns_mut = mutant_namespace(py, 7, patches)
        check(f"{label} (prose numbers)",
              {n: ns_mut["total_n_queens"](n) for n in expected}, expected)
        print(f"  ok  [py] {label.split(':')[0]}: "
              f"{', '.join(f'n={n}→{v}' for n, v in expected.items())}")
    check("§6.1 the good variant is not affected by the mutant patches",
          ns["total_n_queens"](4), 2)

    check("§6.2 bitmask counts equal §6.1 counts for n = 0…10",
          [ns["total_n_queens_bitmask"](n) for n in range(11)],
          [len(queens_ref[n]) for n in range(11)])
    bitmask_calls = counter.count(ns["total_n_queens_bitmask"], 8)[1]
    check("§6.2 both versions take 2057 calls at n = 8 (the prose claim)",
          (bitmask_calls, calls_per_n[7]), (2057, 2057))
    print(f"  ok  [py] §6.1 / §6.2：N 皇后 n=0…10 与全排列暴力逐项一致，"
          f"位运算版 n=8 同为 {bitmask_calls} 次调用，三个错版本的数字全部复现")

    # ---- 5c. §6.3: sudoku against the exact-cover reference ----------------
    unsolvable = with_cell(CLASSIC, 0, 2, "1")
    check("§6.3 the unsolvable probe is locally consistent",
          locally_consistent(unsolvable), True)
    check("§6.3 the unsolvable probe is really unsolvable (exact cover)",
          exact_cover_solutions(unsolvable, limit=2), [])
    sudoku_calls = {}
    for name, puzzle, want_solutions, want_calls in (
            ("经典题", CLASSIC, 1, 4209),
            ("最难数独", HARDEST, 1, 49559),
            ("全空盘", EMPTY_GRID, 2, 392)):
        ref = exact_cover_solutions(puzzle, limit=2)
        check(f"§6.3 {name}: exact-cover solution count (limit 2)", len(ref), want_solutions)
        grid = [list(row) for row in puzzle]
        ok, calls = counter.count(ns["solve_sudoku"], grid)
        solved = ["".join(row) for row in grid]
        sudoku_calls[name] = calls
        check(f"§6.3 {name}: the post's solver returns True", ok, True)
        check(f"§6.3 {name}: no blank left", sum(r.count(".") for r in solved), 0)
        check(f"§6.3 {name}: recursion calls (prose number)", calls, want_calls)
        if want_solutions == 1:
            check(f"§6.3 {name}: the grid equals the exact-cover solution", solved, ref[0])
        else:
            check(f"§6.3 {name}: the grid is a valid solution (external validator)",
                  sudoku_violations(puzzle, solved), [])
            check(f"§6.3 {name}: the post's grid differs from the reference's first "
                  f"solution (it is its own first hit)", solved == ref[0], False)
    grid = [list(row) for row in EMPTY_GRID]
    ns["solve_sudoku"](grid)
    check("§6.3 全空盘：前三行逐格复核（prose 里引的那三行）",
          ["".join(row) for row in grid][:3],
          ["123456789", "456789123", "789123456"])
    grid = [list(row) for row in unsolvable]
    ok, _ = counter.count(ns["solve_sudoku"], grid)
    check("§6.3 无解盘: the post's solver returns False", ok, False)
    check("§6.3 无解盘: the board is left untouched", ["".join(r) for r in grid], unsolvable)
    print(f"  ok  [py] §6.3：数独三例 vs 精确覆盖参照（解数/调用次数/棋盘），"
          f"经典题 {sudoku_calls['经典题']} 次、最难 {sudoku_calls['最难数独']} 次、"
          f"空盘 {sudoku_calls['全空盘']} 次")

    box_mutant = mutant_namespace(
        py, 9, [("b = (r // 3) * 3 + c // 3", "b = (r % 3) * 3 + c % 3", 1)])
    grid = [list(row) for row in CLASSIC]
    ok = box_mutant["solve_sudoku"](grid)
    check("§6.3 wrong box index: cannot even solve the classic puzzle", ok, False)
    check("§6.3 wrong box index: blanks left (prose: 51)",
          sum(r.count(".") for r in grid), 51)
    undo_mutant = mutant_namespace(
        py, 9, [('board[r][c] = "."    # 撤销:格子和三个集合都要还原',
                 'pass  # mutant: 格子值不还原', 1)])
    grid = [list(row) for row in CLASSIC]
    ok = undo_mutant["solve_sudoku"](grid)
    mutant_grid = ["".join(row) for row in grid]
    check("§6.3 missing grid undo: still claims success", ok, True)
    check("§6.3 missing grid undo: no blank left", sum(r.count(".") for r in mutant_grid), 0)
    check("§6.3 missing grid undo: the 34 duplicated cells the prose quotes",
          sudoku_conflicts(mutant_grid), 34)
    check("§6.3 missing grid undo: 34 duplicates land on 33 distinct cells",
          conflict_cells(mutant_grid), 33)
    check("§6.3 missing grid undo: the validator rejects the board",
          len(sudoku_violations(CLASSIC, mutant_grid)) > 0, True)
    print("  ok  [py] §6.3 两个错版本：宫号写错连经典题都解不出来（51 个空格没填）；"
          "漏掉格子撤销则返回 True、棋盘 34 处重复落在 33 个格子上")

    # ---- 5d. sections 7.1 / 7.2: partition & subset-sum -------------------
    part = ns["can_partition_k_subsets"]
    subset = ns["can_partition"]

    # two references per problem: the fast oracle is only trusted after it has
    # been matched against the slow, obviously-correct one.
    random.seed(4242)
    ref_bad = 0
    for _ in range(300):
        nums = [random.randint(1, 7) for _ in range(random.randint(1, 7))]
        k = random.randint(1, 3)
        if dp_partition_k(nums, k)[0] != brute_partition_k(nums, k):
            ref_bad += 1
    check("§7.1 位掩码 DP 参照 vs k^n 分配暴力（300 组）", ref_bad, 0)
    random.seed(4243)
    ref_bad = 0
    for _ in range(300):
        nums = [random.randint(1, 9) for _ in range(random.randint(1, 10))]
        if dp_subset_sum(nums)[0] != brute_subset_sum(nums):
            ref_bad += 1
    check("§7.2 布尔 DP 参照 vs 2^n 子集枚举（300 组）", ref_bad, 0)

    # the slow-but-correct variants the tables quote (built from the post source)
    k_asc = mutant_namespace(py, 10, [
        ("nums = sorted(nums, reverse=True)        # 大数先放:小数留着填缝",
         "nums = sorted(nums)", 1)])
    k_noskip = mutant_namespace(py, 10, [
        ("""            if buckets[j] in tried:
                continue                     # 同和的桶等价:已经试过,跳过
            tried.add(buckets[j])
""", "", 1)])
    k_nofix = mutant_namespace(py, 10, [
        ("    buckets[0] = nums[0]                     # 桶可互换:最大的数固定进 0 号桶\n",
         "", 1),
        ("    return backtrack(1)", "    return backtrack(0)", 1)])
    k_break = mutant_namespace(py, 10, [
        ("""            if buckets[j] + nums[i] > target:
                continue                     # 只能 continue:桶没排序,后面的桶还装得下""",
         """            if buckets[j] + nums[i] > target:
                break""", 1)])
    k_noundo = mutant_namespace(py, 10, [
        ("            buckets[j] -= nums[i]            # 撤销:把数从桶里拿出来\n", "", 1)])
    k_variants = [("去掉同和桶去重", k_noskip["can_partition_k_subsets"]),
                  ("改成升序排列", k_asc["can_partition_k_subsets"]),
                  ("不固定最大数", k_nofix["can_partition_k_subsets"])]

    rows71 = table_rows_parsed(post, "去掉同和桶去重", with_k=True)
    check("§7.1 收益表有 4 行", len(rows71), 4)
    for nums, k, _ans, cells in rows71:
        label = f"{nums} k={k}"
        want, steps = dp_partition_k(nums, k)
        got, calls = counter.count(part, list(nums), k)
        check(f"§7.1 {label}: 本文写法答案 vs 位掩码 DP", got, want)
        check(f"§7.1 {label}: 本文写法调用次数（表 {cells[0]}）", calls, cells[0])
        check(f"§7.1 {label}: 去掉同和桶去重的调用次数（表 {cells[1]}）",
              counter.count(k_noskip["can_partition_k_subsets"], list(nums), k)[1], cells[1])
        check(f"§7.1 {label}: 升序排列的调用次数（表 {cells[2]}）",
              counter.count(k_asc["can_partition_k_subsets"], list(nums), k)[1], cells[2])
        check(f"§7.1 {label}: 位掩码 DP 格子更新次数（表 {cells[3]}）", steps, cells[3])
        for name, fn in k_variants:
            check(f"§7.1 {label}: 「{name}」答案仍然正确", fn(list(nums), k), want)
        check(f"§7.1 {label}: 去重省下了调用次数",
              counter.count(k_noskip["can_partition_k_subsets"], list(nums), k)[1] >= calls, True)
        # output-only validation: a positive answer must come with an explicit split
        witness = partition_witness(nums, k)
        if want:
            check(f"§7.1 {label}: True 时给出显式分组，每桶和都等于 target",
                  witness, [sum(nums) // k] * k)
        else:
            check(f"§7.1 {label}: False 时确实切不出 k 个等和组", witness, None)
    calls71 = {tuple(r[0]): counter.count(part, list(r[0]), r[1])[1] for r in rows71}
    nofix71 = {tuple(r[0]): counter.count(k_nofix["can_partition_k_subsets"],
                                          list(r[0]), r[1])[1] for r in rows71}
    check("§7.1 固定最大数只值 1 次调用：[2,2,2,2,3,3,4,6,7,7,7,7,8,8] 255 → 256",
          (calls71[(2, 2, 2, 2, 3, 3, 4, 6, 7, 7, 7, 7, 8, 8)],
           nofix71[(2, 2, 2, 2, 3, 3, 4, 6, 7, 7, 7, 7, 8, 8)]), (255, 256))
    check("§7.1 固定最大数只值 1 次调用：[2,2,3,4,4,5,5,5,5,6,7,7,8,9] 620 → 621",
          (calls71[(2, 2, 3, 4, 4, 5, 5, 5, 5, 6, 7, 7, 8, 9)],
           nofix71[(2, 2, 3, 4, 4, 5, 5, 5, 5, 6, 7, 7, 8, 9)]), (620, 621))
    print(f"  ok  [py] §7.1 收益表 4 行 16 个数字逐格复核（本文 / 去掉同和桶去重 / 升序 /"
          f" 位掩码 DP 参照），三个慢版本答案仍然正确")

    # 力扣 698 / 473 的示例
    for nums, k, want in (([4, 3, 2, 3, 5, 2, 1], 4, True), ([1, 2, 3, 4], 3, False)):
        check(f"§7.1 力扣 698 示例 {nums} k={k}", counter.count(part, list(nums), k)[0], want)
        check(f"§7.1 力扣 698 示例 {nums} k={k} vs 位掩码 DP",
              counter.count(part, list(nums), k)[0], dp_partition_k(nums, k)[0])
    check("§7.1 力扣 698 示例 1 的调用次数（散文：7）",
          counter.count(part, [4, 3, 2, 3, 5, 2, 1], 4)[1], 7)
    check("§7.1 力扣 698 示例 2（10 % 3 != 0）是 0 次调用",
          counter.count(part, [1, 2, 3, 4], 3)[1], 0)
    check("§7.3 力扣 473 示例 [1,1,2,2,2] k=4 → True（散文：5 次调用）",
          counter.count(part, [1, 1, 2, 2, 2], 4), (True, 5))
    check("§7.3 力扣 473 示例 [3,3,3,3,4] k=4 → False（散文：4 次调用）",
          counter.count(part, [3, 3, 3, 3, 4], 4), (False, 4))

    # the 3000-input wrongness sample the prose quotes
    random.seed(20261125)
    wrong = {"本文写法": 0, "break": 0, "漏撤销": 0}
    for _ in range(3000):
        n = random.randint(1, 8)
        k = random.randint(1, 4)
        nums = [random.randint(1, 7) for _ in range(n)]
        want = dp_partition_k(nums, k)[0]
        if part(list(nums), k) != want:
            wrong["本文写法"] += 1
        if k_break["can_partition_k_subsets"](list(nums), k) != want:
            wrong["break"] += 1
        if k_noundo["can_partition_k_subsets"](list(nums), k) != want:
            wrong["漏撤销"] += 1
    check("§7.1 3000 组随机输入：本文写法错的组数", wrong["本文写法"], 0)
    check("§7.1 3000 组随机输入：break 版错的组数（散文：268）", wrong["break"], 268)
    check("§7.1 3000 组随机输入：漏撤销版错的组数（散文：16）", wrong["漏撤销"], 16)

    # minimal counterexamples, re-searched here rather than copied
    ref_k = lambda a, k: dp_partition_k(a, k)[0]          # noqa: E731
    mn, mk = minimal_counterexample(k_break["can_partition_k_subsets"], ref_k)
    check("§7.1 break 版最小反例（散文：[1,1] k=2）", (mn, mk), ([1, 1], 2))
    check("§7.1 最小反例上 break 版确实答错（正确 True）",
          (ref_k(mn, mk), k_break["can_partition_k_subsets"](list(mn), mk)), (True, False))
    mn, mk = minimal_counterexample(k_noundo["can_partition_k_subsets"], ref_k)
    check("§7.1 漏撤销版最小反例（散文：[2,2,2,2,3,3] k=2）", (mn, mk),
          ([2, 2, 2, 2, 3, 3], 2))
    check("§7.1 最小反例上漏撤销版确实答错（正确 True）",
          (ref_k(mn, mk), k_noundo["can_partition_k_subsets"](list(mn), mk)), (True, False))
    print(f"  ok  [py] §7.1 两个错版本：3000 组随机输入里 break 错 {wrong['break']} 组、"
          f"漏撤销错 {wrong['漏撤销']} 组；最小反例现场搜出 [1,1] k=2 与 "
          f"[2,2,2,2,3,3] k=2")

    # ---- 7.2 -------------------------------------------------------------
    s_asc = mutant_namespace(py, 11, [
        ("nums = sorted(nums, reverse=True)        # 大数先试:失败得快",
         "nums = sorted(nums)", 1)])
    s_nodedup = mutant_namespace(py, 11, [
        ("""            if i > start and nums[i] == nums[i - 1]:
                continue                     # 同层去重:和上一个候选同值,选哪个都一样
""", "", 1)])
    s_break = mutant_namespace(py, 11, [
        ("""            if nums[i] > remain:
                continue                     # 降序数组:装不下的是前面几个,后面的更小""",
         """            if nums[i] > remain:
                break""", 1)])
    s_nopar = mutant_namespace(py, 11, [
        ("    if total % 2:\n        return False                         # 总和是奇数:一半根本不存在\n",
         "", 1)])

    rows72 = table_rows_parsed(post, "去掉同层去重", with_k=False)
    check("§7.2 对照表有 8 行", len(rows72), 8)
    for nums, _k, answer, cells in rows72:
        want, steps = dp_subset_sum(nums)
        label = f"{nums}"
        check(f"§7.2 {label}: 表里写的 {answer} 就是正确答案", answer, want)
        check(f"§7.2 {label}: 本文写法答案 vs 布尔 DP", subset(list(nums)), want)
        check(f"§7.2 {label}: 本文写法调用次数（表 {cells[0]}）",
              counter.count(subset, list(nums))[1], cells[0])
        check(f"§7.2 {label}: 升序排列的调用次数（表 {cells[1]}）",
              counter.count(s_asc["can_partition"], list(nums))[1], cells[1])
        check(f"§7.2 {label}: 去掉同层去重的调用次数（表 {cells[2]}）",
              counter.count(s_nodedup["can_partition"], list(nums))[1], cells[2])
        check(f"§7.2 {label}: 布尔 DP 格子更新次数（表 {cells[3]}）", steps, cells[3])
        check(f"§7.2 {label}: 升序版本答案仍然正确",
              s_asc["can_partition"](list(nums)), want)
        check(f"§7.2 {label}: 去掉同层去重的版本答案仍然正确",
              s_nodedup["can_partition"](list(nums)), want)
        # output-only validation: True must come with an explicit subset
        witness = subset_witness(nums)
        if want:
            check(f"§7.2 {label}: True 时挑出的子集和正好是 half",
                  sum(witness) if witness else None, sum(nums) // 2)
        else:
            check(f"§7.2 {label}: False 时确实挑不出和为 half 的子集", witness, None)
    print(f"  ok  [py] §7.2 对照表 8 行 32 个数字逐格复核（本文 / 升序 / 去掉同层去重 /"
          f" 布尔 DP 参照），两个慢版本答案仍然正确")
    print("  ok  [witness] §7 的每个正例都由外部见证程序重做一遍（只看答案，不看搜索）："
          "698/473 每行给出显式分组、每桶和等于 target，416 每行给出和为 half 的子集")

    for nums, want in (([1, 5, 11, 5], True), ([1, 2, 3, 5], False)):
        check(f"§7.2 力扣 416 示例 {nums}", counter.count(subset, list(nums))[0], want)
        check(f"§7.2 力扣 416 示例 {nums} vs 布尔 DP",
              counter.count(subset, list(nums))[0], dp_subset_sum(nums)[0])
    check("§7.2 力扣 416 示例 1 的调用次数（散文：2）",
          counter.count(subset, [1, 5, 11, 5])[1], 2)
    check("§7.2 示例 2 / [1,1,1] 都是 0 次调用（奇数和）",
          (counter.count(subset, [1, 2, 3, 5])[1], counter.count(subset, [1, 1, 1])[1]),
          (0, 0))
    check("§7.2 17 个偶数的探针：回溯 65536 次 / DP 2312 步",
          (counter.count(subset, list(range(2, 35, 2)))[1], dp_subset_sum(list(range(2, 35, 2)))[1]),
          (65536, 2312))
    check("§7.2 20 个 1：回溯 11 次 / DP 200 步",
          (counter.count(subset, [1] * 20)[1], dp_subset_sum([1] * 20)[1]), (11, 200))

    random.seed(20261125)
    wrong = {"本文写法": 0, "去掉 parity": 0, "break": 0}
    for _ in range(3000):
        nums = [random.randint(1, 9) for _ in range(random.randint(1, 10))]
        want = dp_subset_sum(nums)[0]
        if subset(list(nums)) != want:
            wrong["本文写法"] += 1
        if s_nopar["can_partition"](list(nums)) != want:
            wrong["去掉 parity"] += 1
        if s_break["can_partition"](list(nums)) != want:
            wrong["break"] += 1
    check("§7.2 3000 组随机输入：本文写法错的组数", wrong["本文写法"], 0)
    check("§7.2 3000 组随机输入：去掉 parity 错的组数（散文：1041）",
          wrong["去掉 parity"], 1041)
    check("§7.2 3000 组随机输入：break 错的组数（散文：129）", wrong["break"], 129)
    ref_s = lambda a: dp_subset_sum(a)[0]                 # noqa: E731
    mn = minimal_subset_counterexample(s_nopar["can_partition"], ref_s)
    check("§7.2 去掉 parity 的最小反例（散文：[1,1,1]）", mn, [1, 1, 1])
    check("§7.2 最小反例上去掉 parity 确实答错（正确 False）",
          (ref_s(mn), s_nopar["can_partition"](list(mn))), (False, True))
    mn = minimal_subset_counterexample(s_break["can_partition"], ref_s)
    check("§7.2 降序 break 的最小反例（散文：[1,1,2,2]）", mn, [1, 1, 2, 2])
    check("§7.2 最小反例上 break 确实答错（正确 True）",
          (ref_s(mn), s_break["can_partition"](list(mn))), (True, False))
    print(f"  ok  [py] §7.2 两个错版本：3000 组随机输入里去掉 parity 错 "
          f"{wrong['去掉 parity']} 组、break 错 {wrong['break']} 组；最小反例现场搜出 "
          f"[1,1,1] 与 [1,1,2,2]")

    # 7.3: k = 2 的 698 与 416 是同一道题
    random.seed(20261126)
    disagree = 0
    for _ in range(1500):
        nums = [random.randint(1, 9) for _ in range(random.randint(0, 9))]
        if part(list(nums), 2) != subset(list(nums)):
            disagree += 1
    check("§7.3 k=2 的 698 与 416 在 1500 组随机输入上逐组一致（散文：0 处）",
          disagree, 0)
    check("§7.3 k=2 的 698 与 416 在 416 的两个示例上也一致",
          [(part(list(n), 2), subset(list(n))) for n in ([1, 5, 11, 5], [1, 2, 3, 5])],
          [(True, True), (False, False)])
    print("  ok  [py] §7.3 k=2 的 698 与 416 逐组一致（1500 组随机 + 两个示例）")

    print(f"  python cases  : {n_cases - len(fails)}/{n_cases} pass")
    if fails:
        problems.extend(fails)

    # ---- 6. C++ TU-A: the post's blocks + the checked-in harness -----------
    if not HARNESS.exists():
        problems.append("cpp_harness.cpp missing — C++ unverified")
    else:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "post_and_harness.cpp"
            src.write_text("\n".join(cpp) + "\n" + HARNESS.read_text(encoding="utf-8"),
                           encoding="utf-8")
            exe = Path(td) / "harness"
            cp = subprocess.run([*CXX, str(src), "-o", str(exe)],
                                capture_output=True, text=True)
            if cp.returncode != 0:
                problems.append("g++ failed on the post's C++ + harness:\n"
                                + (cp.stderr or "")[:2000])
                print("  FAIL  g++ did not compile the post's C++ + harness")
            else:
                run = subprocess.run([str(exe)], capture_output=True, text=True)
                out = (run.stdout or "").strip()
                print(f"  cpp TU-A      : {' '.join(CXX[1:])}, zero warnings")
                for line in out.splitlines()[-2:]:
                    print(f"  {line.strip()}")
                if run.returncode != 0:
                    problems.append(f"cpp harness exited {run.returncode}")
                    print(out)

    # ---- 7. C++ TU-B: expectations generated from itertools at gate runtime -
    cases = oracle_cases()
    board_lines = oracle_board_lines()
    part_lines = oracle_partition_lines(post)
    body = "".join(f'    checkSet({json.dumps(label)}, {call}, {cpp_rows(want)});\n'
                   for label, call, want in cases) \
        + "".join(board_lines) + "".join(part_lines)
    if not cases or not board_lines or not part_lines:
        problems.append("no generated C++ oracle cases — nothing cross-checked")
    else:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "post_and_oracle.cpp"
            src.write_text("\n".join(cpp) + CPP_ORACLE_PRELUDE
                           + CPP_ORACLE_MAIN_HEAD + body + CPP_ORACLE_MAIN_TAIL,
                           encoding="utf-8")
            exe = Path(td) / "oracle"
            cp = subprocess.run([*CXX, str(src), "-o", str(exe)],
                                capture_output=True, text=True)
            if cp.returncode != 0:
                problems.append("g++ failed on the generated oracle TU:\n"
                                + (cp.stderr or "")[:2000])
                print("  FAIL  g++ did not compile the generated C++ oracle TU")
            else:
                run = subprocess.run([str(exe)], capture_output=True, text=True)
                out = (run.stdout or "").strip()
                print(f"  cpp TU-B      : {' '.join(CXX[1:])}, zero warnings")
                for line in out.splitlines()[-6:]:
                    print(f"  {line.strip()}")
                if run.returncode != 0:
                    problems.append(f"generated cpp oracle exited {run.returncode}")
                    print(out)
                else:
                    print(f"  ok  [cpp] {len(cases)} 个解集的期望值由 itertools 现场生成，"
                          f"另有 {len(board_lines)} 条 §6 断言（N 皇后计数/棋盘、数独棋盘）"
                          f"与 {len(part_lines)} 条 §7 断言（划分 / 子集和，期望值由位掩码 DP "
                          f"与布尔 DP 现场算出，表里的行直接读自正文）")

    # ---- 8. the board-validator requirement, which now applies ------------
    needs = {
        "§6.1 N 皇后（solve_n_queens / total_n_queens）":
            "solve_n_queens" in ns and "total_n_queens" in ns,
        "§6.2 位运算版（total_n_queens_bitmask）": "total_n_queens_bitmask" in ns,
        "§6.3 解数独（solve_sudoku）": "solve_sudoku" in ns,
        "§7.1 划分（can_partition_k_subsets）": "can_partition_k_subsets" in ns,
        "§7.2 子集和（can_partition）": "can_partition" in ns,
    }
    missing = [name for name, present in needs.items() if not present]
    if missing:
        problems.append("棋盘类 / 划分类代码块缺失，校验器要求失去对象：" + "、".join(missing))
        print(f"  FAIL  正文缺少棋盘类 / 划分类代码块：{'、'.join(missing)}")
    else:
        bad = []
        for n in range(1, 11):
            for board in ns["solve_n_queens"](n):
                bad += [f"n={n}: {v}" for v in queens_violations(board)]
        check("§6 every N-Queens board n = 1…10 passes the external validator",
              bad, [])
        check("§6 the bitmask variant produces the same count row",
              [ns["total_n_queens_bitmask"](n) for n in range(1, 11)],
              [len(queens_ref[n]) for n in range(1, 11)])
        for name, puzzle in (("经典题", CLASSIC), ("最难数独", HARDEST),
                             ("全空盘", EMPTY_GRID)):
            grid = [list(row) for row in puzzle]
            ok = ns["solve_sudoku"](grid)
            check(f"§6 {name}: the returned board passes the external validator",
                  sudoku_violations(puzzle, ["".join(r) for r in grid]) if ok
                  else [f"{name}: solve_sudoku returned False"], [])
        grid = [list(row) for row in unsolvable]
        ok = ns["solve_sudoku"](grid)
        check("§6 无解盘: False and an untouched board (givens preserved)",
              (ok, ["".join(r) for r in grid]), (False, unsolvable))
        print("  ok  [board] 棋盘类小节存在：N 皇后 n=1…10 的每一块棋盘、数独三例的解，"
              "全部由外部校验器逐块复核（只看棋盘，不看搜索）；无解盘保持原样")

    print()
    if problems:
        print(f"  RESULT: {len(problems)} problem(s)")
        for p in problems[:12]:
            print(f"    - {p.splitlines()[0][:160]}")
        return 1
    print("  CODE OK — 正文的 Python 与 C++ 代码块都被执行过：解集与 itertools 严格对拍，"
          "六张表的散文数字全部实测复核，棋盘类的每个数字都由全排列暴力与精确覆盖求解器"
          "算出，划分与子集和的每个数字都由位掩码 DP / k^n 暴力、布尔 DP / 2^n 枚举这两组"
          "互相独立的参照算出，两个 C++ 编译单元 -Werror 零警告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
