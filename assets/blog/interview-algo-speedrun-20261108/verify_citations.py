#!/usr/bin/env python3
"""Claim gate for the post '面试算法题速刷'.

Every claim this post makes about the source tutorial is asserted here against
the archived source text, so a reader can re-run it and check that nothing was
invented.  Each entry is:

    (label, file, line, required-substring)

`line` is 1-based in the archived file.  If the substring is not on that exact
line the check fails, which catches both "wrong fact" and "right fact, wrong
place" (e.g. attributing a repo default to an operator setting).

Usage: python3 verify_citations.py [POST.md]
Exit: 0 all claims verified, 1 any claim failed.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T2 = "t2-linked-list-skills-summary.txt"

# ---------------------------------------------------------------------------
# Claims that come from the tutorial text. (label, file, line, substring)
# ---------------------------------------------------------------------------
CLAIMS = [
    # --- what the tutorial covers -----------------------------------------
    ("tutorial title", T2, 1, "双指针技巧秒杀七道链表题目"),
    ("problem 86 is 分隔链表", T2, 12, "86. 分隔链表"),
    ("problem 23 is 合并 K 个升序链表", T2, 16, "23. 合并 K 个升序链表"),
    ("problem 19 is 删除链表的倒数第 N 个结点", T2, 20,
     "19. 删除链表的倒数第 N 个结点"),
    ("merged list is 力扣第 21 题", T2, 76, "力扣第 21 题"),
    ("partition is 力扣第 86 题", T2, 185, "力扣第 86 题"),
    ("merge-k source is 力扣 23", T2, 346, "力扣 23. 合并 K 个升序链表"),

    # --- technique 1: merge two sorted lists ------------------------------
    ("zip / 拉拉链 analogy", T2, 168, "拉拉链"),
    ("dummy is 虚拟头结点", T2, 176, "虚拟头结点"),
    ("when to use dummy", T2, 180, "当你需要创造一条新链表的时候"),

    # --- technique 2: partition -------------------------------------------
    ("must disconnect next", T2, 251, "断开原链表中的每个节点的 next 指针"),
    ("disconnect rule of thumb", T2, 286, "就把原链表的节点断开"),

    # --- technique 3: merge k -------------------------------------------------
    ("merge-k skips empty heads", T2, 373, "if (head != null)"),
    ("merge-k re-adds node.next", T2, 382, "pq.add(node.next)"),
    ("merge-k total complexity O(Nlogk)", T2, 400, "O(Nlogk)"),
    ("merge-k per-op cost O(logk)", T2, 400, "O(logk)"),
    ("merge-k has a divide-and-conquer alternative", T2, 406, "分治算法核心框架"),

    # --- technique 4: kth from end ----------------------------------------
    ("two scans is the naive way", T2, 416, "需要遍历两次链表"),
    ("one scan is what the interviewer wants", T2, 418, "只遍历一次链表"),
    ("LC19 asks for one pass", T2, 504, "一趟扫描"),
    ("LC19 uses dummy", T2, 514, "虚拟头结点"),
    ("delete needs the n+1-th from end", T2, 517, "倒数第 n + 1 个节点"),

    # --- technique 5: middle ----------------------------------------------
    ("LC876 is the middle-node problem", T2, 544, "力扣第 876 题"),
    ("loop condition guards fast.next", T2, 563, "fast != null && fast.next != null"),
    ("even length returns the later middle", T2, 580,
     "我们这个解法返回的节点是靠后的那个节点"),
    ("middle code adapts to cycle detection", T2, 582, "稍加修改"),

    # --- technique 6: cycle -------------------------------------------------
    ("LC142 is cycle II", T2, 622, "力扣第 142 题"),
    ("break is followed by a null check", T2, 643,
     "if (fast == null || fast.next == null)"),
    ("detectCycle conclusion", T2, 667, "再次相遇时所在的节点位置就是环开始的位置"),
    ("fast walked 2k", T2, 671, "快指针 fast 一定走了 2k 步"),
    ("k is a multiple of cycle length", T2, 673, "k 的值就是环长度的「整数倍」"),
    ("meeting point to cycle start is m", T2, 675, "相遇点距环的起点的距离为 m"),
    ("head to cycle start is k - m", T2, 675, "环的起点距头结点 head 的距离为 k - m"),

    # --- technique 7: intersection ----------------------------------------
    ("LC160 is the intersection problem", T2, 683, "力扣第 160 题"),
    ("HashSet is the extra-space approach", T2, 700, "用 HashSet 记录一个链表的所有节点"),
    ("logical splice idea", T2, 710, "「逻辑上」两条链表接在了一起"),
    ("no-intersection means c1 is null", T2, 716, "相当于 c1 节点是 null 空指针"),
    ("intersection is O(1) space", T2, 745, "空间复杂度为 O(1)"),
    ("intersection is O(N) time", T2, 745, "时间复杂度为 O(N)"),
    ("2022/1/24 update exists", T2, 749, "2022/1/24 更新"),
    ("alternative: precompute lengths", T2, 757, "预先计算两条链表的长度"),
    ("length-based variant is also O(N)", T2, 794, "时间复杂度是还是 O(N)"),
]

# ---------------------------------------------------------------------------
# Claims that are MINE, not the tutorial's.  Asserted so that the post cannot
# silently grow a claim here without this file being updated too.
# ---------------------------------------------------------------------------
OWN_CLAIMS = [
    ("the x = (n-1)(y+z) + z derivation is my reformulation",
     "我的推导用的是 x/y/z 记法"),
    ("section 1 was written without the tutorial body",
     "第一节的讲解是从这个标题和摘要出发"),
    ("the 8 diagrams are mine",
     "8 张示意图都是我自己用 SVG 画的"),
]


def check(post_path=None):
    problems, checked = [], 0
    cache = {}

    def lines_of(fn):
        if fn not in cache:
            p = HERE / fn
            cache[fn] = p.read_text(encoding="utf-8").splitlines()
        return cache[fn]

    for label, fn, lineno, needle in CLAIMS:
        checked += 1
        ls = lines_of(fn)
        if lineno > len(ls):
            problems.append(f"[{label}] {fn} has only {len(ls)} lines, "
                            f"asked for {lineno}")
            continue
        actual = ls[lineno - 1]
        if needle not in actual:
            problems.append(f"[{label}] {fn}:{lineno} does not contain "
                            f"{needle!r}\n        actual: {actual.strip()[:110]}")

    print(f"  source claims  : {checked - len(problems)}/{checked} verified")

    if post_path:
        post = Path(post_path).read_text(encoding="utf-8")
        own_ok = 0
        for label, needle in OWN_CLAIMS:
            if needle in post:
                own_ok += 1
            else:
                problems.append(f"[own-claim missing from post] {label}")
        print(f"  own-claim flags: {own_ok}/{len(OWN_CLAIMS)} present in the post")

    return problems


if __name__ == "__main__":
    post = sys.argv[1] if len(sys.argv) > 1 else None
    probs = check(post)
    if probs:
        print(f"\n  {len(probs)} PROBLEM(S):")
        for p in probs:
            print(f"    - {p}")
        sys.exit(1)
    print("  all claims verified against the archived source")
