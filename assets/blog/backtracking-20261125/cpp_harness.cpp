// Test harness for the C++ blocks of _posts/2026-11-25-backtracking.md.
//
// verify_code.py concatenates the post's ```cpp blocks in front of this file
// and compiles the result with `g++ -std=c++17 -Wall -Wextra -O1`.  Nothing
// here re-implements a solution: this file only calls the functions defined in
// the post and compares their output with results worked out independently in
// the Python half of the gate (and with Python's itertools).
//
// Exit code 0 = every case passed.

#include <algorithm>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

static int g_pass = 0;
static int g_fail = 0;

static std::string dump(const std::vector<std::vector<int>>& v) {
    std::string s = "[";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i != 0) s += ", ";
        s += "[";
        for (std::size_t j = 0; j < v[i].size(); ++j) {
            if (j != 0) s += ",";
            s += std::to_string(v[i][j]);
        }
        s += "]";
    }
    return s + "]";
}

// Order-insensitive canonical form: sort inside each row, then sort rows.
static std::vector<std::vector<int>> canon(std::vector<std::vector<int>> v) {
    for (std::vector<int>& row : v) std::sort(row.begin(), row.end());
    std::sort(v.begin(), v.end());
    return v;
}

static void check_set(const std::string& name,
                      const std::vector<std::vector<int>>& got,
                      const std::vector<std::vector<int>>& want) {
    if (canon(got) == canon(want)) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << "\n        got  " << dump(canon(got))
                  << "\n        want " << dump(canon(want)) << "\n";
    }
}

static void check_int(const std::string& name, long long got, long long want) {
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << ": got " << got << " want " << want << "\n";
    }
}

// ---- section 6 helpers -------------------------------------------------
// Row order matters here (row r -> column of the queen), the order of the
// solutions themselves does not, so only the outer collection is sorted.
static void check_seq(const std::string& name,
                      std::vector<std::vector<int>> got,
                      std::vector<std::vector<int>> want) {
    std::sort(got.begin(), got.end());
    std::sort(want.begin(), want.end());
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << "\n        got  " << dump(got)
                  << "\n        want " << dump(want) << "\n";
    }
}

static std::string dump_grid(const std::vector<std::string>& grid) {
    std::string s = "[";
    for (std::size_t i = 0; i < grid.size(); ++i) {
        if (i != 0) s += ", ";
        s += grid[i];
    }
    return s + "]";
}

static void check_grid(const std::string& name,
                       const std::vector<std::string>& got,
                       const std::vector<std::string>& want) {
    if (got == want) {
        ++g_pass;
    } else {
        ++g_fail;
        std::cout << "  FAIL " << name << "\n        got  " << dump_grid(got)
                  << "\n        want " << dump_grid(want) << "\n";
    }
}

// (row -> column) for every returned board
static std::vector<std::vector<int>> board_cols(
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

// Independent validator: no two queens share a column or a diagonal.  It only
// reads the returned boards, never the search that produced them.
static bool valid_queens(const std::vector<std::vector<std::string>>& boards) {
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
static bool valid_sudoku(const std::vector<std::string>& grid) {
    if (grid.size() != 9) return false;
    for (const std::string& row : grid) {
        if (row.size() != 9) return false;
    }
    for (int i = 0; i < 9; ++i) {
        bool row_seen[10] = {}, col_seen[10] = {}, box_seen[10] = {};
        for (int j = 0; j < 9; ++j) {
            const int rv = grid[i][j] - '0';
            const int cv = grid[j][i] - '0';
            const int bv = grid[(i / 3) * 3 + j / 3][(i % 3) * 3 + j % 3] - '0';
            if (rv < 1 || rv > 9 || cv < 1 || cv > 9 || bv < 1 || bv > 9) return false;
            if (row_seen[rv] || col_seen[cv] || box_seen[bv]) return false;
            row_seen[rv] = col_seen[cv] = box_seen[bv] = true;
        }
    }
    return true;
}

// ---- section 7 helper: a vector<int> label for the partition cases ------
static std::string dump_int(const std::vector<int>& v) {
    std::string s = "{";
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (i != 0) s += ",";
        s += std::to_string(v[i]);
    }
    return s + "}";
}

int main() {
    // ---- permute: n = 0, n = 1, and the 3! case ---------------------------
    check_set("permute([])", permute({}), {{}});
    check_set("permute([7])", permute({7}), {{7}});
    check_set("permute([1,2,3])", permute({1, 2, 3}),
              {{1, 2, 3}, {1, 3, 2}, {2, 1, 3}, {2, 3, 1}, {3, 1, 2}, {3, 2, 1}});
    check_int("permute([1,2,3,4]) count", static_cast<long long>(permute({1, 2, 3, 4}).size()), 24);

    // ---- subsets: the answer sits on every node ---------------------------
    check_set("subsets([])", subsets({}), {{}});
    check_set("subsets([1])", subsets({1}), {{}, {1}});
    check_set("subsets([1,2,3])", subsets({1, 2, 3}),
              {{}, {1}, {2}, {3}, {1, 2}, {1, 3}, {2, 3}, {1, 2, 3}});

    // ---- combine: k = 0, k > n, n = 0 -------------------------------------
    check_set("combine(0,0)", combine(0, 0), {{}});
    check_set("combine(4,0)", combine(4, 0), {{}});
    check_set("combine(3,5)", combine(3, 5), {});
    check_set("combine(4,2)", combine(4, 2),
              {{1, 2}, {1, 3}, {1, 4}, {2, 3}, {2, 4}, {3, 4}});
    check_int("combine(5,3) count", static_cast<long long>(combine(5, 3).size()), 10);

    // ---- duplicate handling ----------------------------------------------
    check_set("permuteUnique([1,1,2])", permuteUnique({1, 1, 2}),
              {{1, 1, 2}, {1, 2, 1}, {2, 1, 1}});
    check_int("permuteUnique([1,1,1,2]) count",
              static_cast<long long>(permuteUnique({1, 1, 1, 2}).size()), 4);
    check_int("permuteUnique([1,2,2,3,3]) count",
              static_cast<long long>(permuteUnique({1, 2, 2, 3, 3}).size()), 30);
    check_int("permuteUnique([1,1,2,2,3,3]) count",
              static_cast<long long>(permuteUnique({1, 1, 2, 2, 3, 3}).size()), 90);
    check_set("subsetsWithDup([1,1,2])", subsetsWithDup({1, 1, 2}),
              {{}, {1}, {2}, {1, 1}, {1, 2}, {1, 1, 2}});
    check_int("subsetsWithDup([1,1,2,2,3,3]) count",
              static_cast<long long>(subsetsWithDup({1, 1, 2, 2, 3, 3}).size()), 27);

    // ---- combination sum: same answers, measured pruning payoff ----------
    // The call counts must match the table in section 4.2 of the post.
    struct Case {
        std::vector<int> cand;
        int target;
        long long solutions;
        long long naive_calls;
        long long pruned_calls;
    };
    const std::vector<Case> cases = {
        {{2, 3, 6, 7}, 7, 2, 28, 10},
        {{2, 3, 5}, 8, 3, 23, 13},
        {{3, 4, 7, 8}, 11, 3, 34, 14},
        {{2, 3, 5, 7, 11, 13}, 30, 80, 1831, 672},
        {{1, 2, 3, 4, 5, 6, 7, 8}, 20, 434, 6360, 2099},
    };
    for (const Case& c : cases) {
        const std::string tag = dump({c.cand}) + "/" + std::to_string(c.target);
        std::pair<std::vector<std::vector<int>>, long long> naive =
            combinationSumNaive(c.cand, c.target);
        std::pair<std::vector<std::vector<int>>, long long> pruned =
            combinationSumPruned(c.cand, c.target);
        check_set(tag + " naive == pruned", naive.first, pruned.first);
        check_int(tag + " solutions", static_cast<long long>(pruned.first.size()), c.solutions);
        check_int(tag + " naive calls", naive.second, c.naive_calls);
        check_int(tag + " pruned calls", pruned.second, c.pruned_calls);
        if (pruned.second >= naive.second) {
            ++g_fail;
            std::cout << "  FAIL " << tag << ": pruning did not reduce calls\n";
        } else {
            ++g_pass;
        }
    }
    check_set("combinationSumPruned([2,3],1)", combinationSumPruned({2, 3}, 1).first, {});
    check_set("combinationSumPruned([2,3],0)", combinationSumPruned({2, 3}, 0).first, {{}});

    // ---- §6.1 / §6.2 N 皇后: the table in the post, row by row -------------
    // The same ten numbers are re-derived in the Python half of the gate from
    // an unpruned enumeration of itertools.permutations(range(n)).
    const long long queens_counts[11] = {1, 1, 0, 0, 2, 10, 4, 40, 92, 352, 724};
    for (int n = 0; n <= 10; ++n) {
        const std::string tag = std::to_string(n);
        check_int("totalNQueens(" + tag + ")", totalNQueens(n), queens_counts[n]);
        check_int("totalNQueensBitmask(" + tag + ")", totalNQueensBitmask(n), queens_counts[n]);
        check_int("solveNQueens(" + tag + ").size()",
                  static_cast<long long>(solveNQueens(n).size()), queens_counts[n]);
        check_int("valid_queens(solveNQueens(" + tag + "))",
                  valid_queens(solveNQueens(n)) ? 1 : 0, 1);
    }
    check_seq("solveNQueens(4)", board_cols(solveNQueens(4)), {{1, 3, 0, 2}, {2, 0, 3, 1}});
    check_seq("solveNQueens(0)", board_cols(solveNQueens(0)), {{}});
    check_int("solveNQueens(6) has 4 boards",
              static_cast<long long>(solveNQueens(6).size()), 4);

    // ---- §6.3 解数独: 经典题 / 最难数独 / 全空盘 / 无解盘 -------------------
    const std::vector<std::string> classic = {
        "53..7....", "6..195...", ".98....6.", "8...6...3", "4..8.3..1",
        "7...2...6", ".6....28.", "...419..5", "....8..79"};
    const std::vector<std::string> hardest = {
        "8........", "..36.....", ".7..9.2..", ".5...7...", "....457..",
        "...1...3.", "..1....68", "..85...1.", ".9....4.."};
    const std::vector<std::string> empty_grid(9, std::string(9, '.'));
    // The same grid the Python half gets from its exact-cover solver.
    const std::vector<std::string> classic_solution = {
        "534678912", "672195348", "198342567", "859761423", "426853791",
        "713924856", "961537284", "287419635", "345286179"};
    {
        std::vector<std::string> board = classic;
        check_int("solveSudoku(经典题) returns true", solveSudoku(board) ? 1 : 0, 1);
        check_grid("solveSudoku(经典题) grid", board, classic_solution);
        check_int("valid_sudoku(经典题 解)", valid_sudoku(board) ? 1 : 0, 1);
    }
    {
        std::vector<std::string> board = hardest;
        check_int("solveSudoku(最难数独) returns true", solveSudoku(board) ? 1 : 0, 1);
        check_int("valid_sudoku(最难数独 解)", valid_sudoku(board) ? 1 : 0, 1);
    }
    {
        std::vector<std::string> board = empty_grid;
        check_int("solveSudoku(全空盘) returns true", solveSudoku(board) ? 1 : 0, 1);
        check_int("valid_sudoku(全空盘 解)", valid_sudoku(board) ? 1 : 0, 1);
    }
    {
        // locally consistent (no row/column/box repeats) but unsolvable
        std::vector<std::string> puzzle = classic;
        puzzle[0][2] = '1';
        std::vector<std::string> board = puzzle;
        check_int("solveSudoku(无解盘) returns false", solveSudoku(board) ? 1 : 0, 0);
        check_int("solveSudoku(无解盘) leaves the board untouched",
                  board == puzzle ? 1 : 0, 1);
    }

    // ---- §7.1 / §7.2 划分与子集和: the post's examples and table rows ------
    // The expectations here are the ones the prose states (力扣's own examples,
    // and the rows of the two tables); TU-B re-derives every one of them from
    // the Python DP references instead of trusting these literals.
    {
        const std::vector<std::vector<int>> yes = {
            {4, 3, 2, 3, 5, 2, 1},                     // 698 示例 1
            {2, 2, 3, 4, 4, 5, 5, 5, 5, 6, 7, 7, 8, 9},
            {2, 2, 2, 2, 3, 3, 4, 6, 7, 7, 7, 7, 8, 8},
            {1, 1, 2, 2, 2},                           // 473 示例 1
            {1, 1},                                    // break 版的最小反例
            {2, 2, 2, 2, 3, 3},                        // 漏撤销版的最小反例
        };
        const std::vector<int> yes_k = {4, 4, 4, 4, 2, 2};
        for (std::size_t i = 0; i < yes.size(); ++i) {
            check_int("canPartitionKSubsets(" + dump_int(yes[i]) + ", "
                          + std::to_string(yes_k[i]) + ")",
                      canPartitionKSubsets(yes[i], yes_k[i]) ? 1 : 0, 1);
        }
        check_int("canPartitionKSubsets({9,8,7,6,5,4,3,2,1}, 3)",
                  canPartitionKSubsets({9, 8, 7, 6, 5, 4, 3, 2, 1}, 3) ? 1 : 0, 1);
        const std::vector<std::vector<int>> no = {
            {1, 2, 3, 4},                              // 698 示例 2: 10 % 3 != 0
            {3, 3, 3, 3, 4},                           // 473 示例 2
            {9, 8, 7, 6, 5, 4, 3, 2, 1},               // 45 % 4 != 0
            {1, 1, 1, 1, 1, 1, 1},                     // 7 个数分 3 组: 凑不出 7/3
        };
        const std::vector<int> no_k = {3, 4, 4, 3};
        for (std::size_t i = 0; i < no.size(); ++i) {
            check_int("canPartitionKSubsets(" + dump_int(no[i]) + ", "
                          + std::to_string(no_k[i]) + ")",
                      canPartitionKSubsets(no[i], no_k[i]) ? 1 : 0, 0);
        }
        check_int("canPartition({1,5,11,5})", canPartition({1, 5, 11, 5}) ? 1 : 0, 1);
        check_int("canPartition({1,2,3,5})", canPartition({1, 2, 3, 5}) ? 1 : 0, 0);
        check_int("canPartition({1,1,1})", canPartition({1, 1, 1}) ? 1 : 0, 0);
        check_int("canPartition({1,1,2,2})", canPartition({1, 1, 2, 2}) ? 1 : 0, 1);
        check_int("canPartition(17 个偶数)", canPartition({2, 4, 6, 8, 10, 12, 14, 16, 18,
                                                           20, 22, 24, 26, 28, 30, 32, 34})
                      ? 1 : 0, 0);
        check_int("canPartition(20 个 1)", canPartition({1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                                         1, 1, 1, 1, 1, 1, 1, 1, 1, 1})
                      ? 1 : 0, 1);
        check_int("canPartition({3,3,3,4,5})", canPartition({3, 3, 3, 4, 5}) ? 1 : 0, 1);
        check_int("canPartition({2,2,3,5})", canPartition({2, 2, 3, 5}) ? 1 : 0, 0);
        check_int("canPartition({1,5,5,5,5,6,7,7,7,7,9})",
                  canPartition({1, 5, 5, 5, 5, 6, 7, 7, 7, 7, 9}) ? 1 : 0, 1);
        // k = 2 的 698 与 416 是同一道题
        check_int("canPartitionKSubsets({1,5,11,5}, 2)",
                  canPartitionKSubsets({1, 5, 11, 5}, 2) ? 1 : 0, 1);
        check_int("canPartitionKSubsets({1,2,3,5}, 2)",
                  canPartitionKSubsets({1, 2, 3, 5}, 2) ? 1 : 0, 0);
    }

    std::cout << "  cpp cases     : " << g_pass << "/" << (g_pass + g_fail) << " pass\n";
    if (g_fail != 0) {
        std::cout << "  CPP FAILED\n";
        return 1;
    }
    return 0;
}
