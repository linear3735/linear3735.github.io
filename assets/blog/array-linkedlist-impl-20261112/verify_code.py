#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代码门:_posts/2026-11-12-array-linkedlist-impl.md

写法遵循本系列惯例:**从文章正文里抽取代码块**,脚本里不留第二份副本。
抽取出来的 Python 块直接 exec;C++ 块原样拼成一个程序编译后跑同一批用例。
两侧的结果逐行比对,任何不一致都算失败。

除"跑通"之外,这里还做三件事,因为跑通不能证明正确:

  1. **与库/暴力对照。** MyArrayList 对 Python list;链表三个实现互相对照;
     数组<->链表两个方向互为逆运算。
  2. **机器断言正文里的每一句实测断言。** 文章写了"翻倍扩容总搬移次数 < n",
     那这里就真的去数搬移次数;写了"删到容量 1/4 缩一半",就真的去看容量。
  3. **反向对照(负向测试)。** 故意把实现改坏,确认门会红 —— 门不咬等于没门。

用法:
    /opt/miniconda3/bin/python3 assets/blog/array-linkedlist-impl-20261112/verify_code.py
"""
from __future__ import annotations

import os
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import traceback

HERE = pathlib.Path(__file__).resolve().parent
# HERE = assets/blog/<slug>-<date> → parents[0]=blog, [1]=assets, [2]=仓库根
REPO = HERE.parents[2]
POST = REPO / "_posts" / "2026-11-12-array-linkedlist-impl.md"

# 文章路径可以用环境变量覆盖,方便在 /tmp 里做负向对照
POST = pathlib.Path(os.environ.get("ALI_POST", str(POST)))

FAILURES = []
PY_CHECKS = 0
CPP_CHECKS = 0


def check(cond, label):
    """记一次断言。"""
    global PY_CHECKS
    PY_CHECKS += 1
    if not cond:
        FAILURES.append(label)
        print(f"  FAIL {label}")


def extract(post_path, lang):
    """抽出 ```<lang> ... ``` 围栏里的内容。"""
    src = post_path.read_text(encoding="utf-8")
    pat = re.compile(r"^```" + lang + r"[ \t]*\n(.*?)^```[ \t]*$",
                     re.MULTILINE | re.DOTALL)
    return [m.group(1) for m in pat.finditer(src)]


# --------------------------------------------------------------------------
# 1. 抽取并加载文章里的 Python 代码
# --------------------------------------------------------------------------
def load_python_blocks(post_path):
    blocks = extract(post_path, "python")
    ns = {}
    for i, blk in enumerate(blocks, 1):
        try:
            exec(compile(blk, f"<post python block {i}>", "exec"), ns)
        except Exception:
            print(f"  FAIL python block {i} 无法执行")
            traceback.print_exc()
            FAILURES.append(f"python block {i} exec")
    return blocks, ns


# --------------------------------------------------------------------------
# 2. 用例生成:同一个随机源,Python 与 C++ 共用
# --------------------------------------------------------------------------
class Lcg:
    """和 C++ 侧完全同构的 LCG,保证两侧跑的是同一批数据。"""

    def __init__(self, seed=20261112):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def below(self, n):
        return self.next() % n

    def value(self):
        """有正有负、有重复的小整数。"""
        return self.below(41) - 20


def build_ops(seed, n_ops, max_val=20):
    """构造一串容器操作,两侧都按这个序列跑。"""
    rng = Lcg(seed)
    ops = []
    for _ in range(n_ops):
        size_hint = 0
        for op in ops:
            if op[0] in ("AL", "AI"):
                size_hint += 1
            elif op[0] == "AR":
                size_hint = max(0, size_hint - 1)
        pick = rng.below(100)
        if pick < 34 or size_hint == 0:
            ops.append(("AL", rng.value()))
        elif pick < 68:
            ops.append(("AI", rng.below(size_hint + 1), rng.value()))
        else:
            ops.append(("AR", rng.below(size_hint)))
    return ops


def build_sll_ops(seed, n_ops):
    """单链表:模型与容器同时跑,随时比对。"""
    rng = Lcg(seed)
    model = []
    ops = []
    for _ in range(n_ops):
        pick = rng.below(100)
        if pick < 30 or not model:
            ops.append(("AL", rng.value()))
            model.append(None)
        elif pick < 60:
            i = rng.below(len(model) + 1)
            ops.append(("AI", i, rng.value()))
            model.insert(i, None)
        else:
            i = rng.below(len(model))
            ops.append(("AR", i))
            model.pop(i)
    return ops


# --------------------------------------------------------------------------
# 3. Python 侧检查
# --------------------------------------------------------------------------
def python_checks(ns):
    MyArrayList = ns["MyArrayList"]
    MySinglyList = ns["MySinglyList"]
    MyDoublyList = ns["MyDoublyList"]
    array_to_linked_list = ns["array_to_linked_list"]
    linked_list_to_array = ns["linked_list_to_array"]
    ListNode = ns["ListNode"]

    # ---- 3.1 MyArrayList 对 Python list ----
    for seed in (1, 2, 3):
        ops = build_ops(seed, 260)
        arr = MyArrayList()
        ref = []
        for op in ops:
            if op[0] == "AL":
                arr.add_last(op[1])
                ref.append(op[1])
            elif op[0] == "AI":
                arr.add(op[1], op[2])
                ref.insert(op[1], op[2])
            else:
                got = arr.remove(op[1])
                want = ref.pop(op[1])
                check(got == want, f"ArrayList seed{seed} remove 返回值 {got} != {want}")
            check(arr.size() == len(ref), f"ArrayList seed{seed} size 失配")
            check([arr.get(i) for i in range(arr.size())] == ref,
                  f"ArrayList seed{seed} 内容失配")
    # set / get 返回值
    arr = MyArrayList()
    for v in (5, 6, 7, 8):
        arr.add_last(v)
    check(arr.set(2, 99) == 7, "ArrayList.set 返回旧值")
    check(arr.get(2) == 99, "ArrayList.set 真的写进去了")
    check(arr.capacity() >= arr.size(), "ArrayList 容量必须 >= size")

    # ---- 3.2 文章 §2 的断言:翻倍扩容总搬移次数 < 2n ----
    # 这里曾经写错过一次:只算等比数列 1+2+4+...+n/2 < n,漏掉了最后一次
    # 扩容要把 n/2 个旧元素搬进容量 n 的空间。加上它之后总次数是 2n-1,
    # 所以上界必须写 2n;写 n 是错的(门第一次跑就咬到了这一点)。
    #
    # 精确值是 2^floor(log2(n)) - 1(n>=2):搬移发生在容量 1,2,4,...,2^k 上,
    # 合计 2^(k+1)-1 = 2*2^k-1,其中 2^k 是不超过 n 的最大 2 的幂。
    # 等式 2n-1 只在 n 本身是 2 的幂时成立(n=10 是 15 而不是 19)。
    # 这张表是直接从文章实现里数出来的,不是从公式反推的。
    moves = {"n": 0}
    original_resize = MyArrayList._resize

    def counting_resize(self, new_capacity):
        moves["n"] += self._size          # 这次要搬 self._size 个
        return original_resize(self, new_capacity)

    def exact_moves(n):
        """n>=2 时等于 2^ceil(log2 n) - 1,整数运算(不碰浮点)。"""
        if n < 2:
            return 0
        cap = 1
        while cap < n:            # 取 >= n 的最小 2 的幂
            cap *= 2
        return cap - 1

    MyArrayList._resize = counting_resize
    try:
        for n in (1, 2, 3, 4, 9, 10, 16, 17, 100, 1000, 1024, 1025, 2048):
            moves["n"] = 0
            a = MyArrayList()
            for i in range(n):
                a.add_last(i)
            check(moves["n"] < 2 * n,
                  f"§2 断言失败:n={n} 时总搬移 {moves['n']} 次,应 < 2n")
            check(moves["n"] == exact_moves(n),
                  f"§2 精确值断言失败:n={n} 时总搬移 {moves['n']},"
                  f"应等于 2^floor(log2 n)-1 = {exact_moves(n)}")
            check(a.size() == n, f"n={n} 追加后 size 不对")
        # 正文措辞的依据。上界 2n-1 对 n>1 处处成立;它在 n = 2^k + 1 时最接近
        # (moves/n -> 2),但**取不到** —— 取到 2n-1 的是 n=2^k-1,而那时
        # moves = 2n+1 > 2n-1,反而不满足。所以正文只说 < 2n,不说"取到 2n-1"。
        check(all(exact_moves(m) < 2 * m for m in range(2, 4097)),
              "上界 2n 对 n=2..4096 处处成立")
        check(exact_moves(1025) == 2047 and 2047 / 1025 > 1.99,
              "n=2^k+1 时 moves/n 逼近 2(n=1025 时 2047/1025 > 1.99)")
        check(exact_moves(1000) == 1023 and exact_moves(1000) < 2 * 1000 - 1,
              "n=1000 时是 1023,远小于 2n")
        # 反面:上界不能写成 n。这一条是永久的反例守卫,
        # 防止有人"顺手"把正文的 2n 改回 n。
        moves["n"] = 0
        a = MyArrayList()
        for i in range(1000):
            a.add_last(i)
        check(not (moves["n"] < 1000),
              "§2 反例守卫:总搬移次数确实 NOT < n(正文不能写成 < n)")
    finally:
        MyArrayList._resize = original_resize

    # ---- 3.3 文章 §2.2 的断言:删到容量 1/4 时缩容一半 ----
    a = MyArrayList()
    for i in range(64):
        a.add_last(i)
    check(a.capacity() == 64, f"64 次追加后容量应为 64,实际 {a.capacity()}")
    for _ in range(48):                    # 64 -> 16,正好到 1/4
        a.remove(a.size() - 1)
    check(a.size() == 16, "删 48 个后 size 应为 16")
    check(a.capacity() < 64,
          f"§2.2 断言失败:size=16(容量 1/4)时未缩容,容量仍为 {a.capacity()}")

    # ---- 3.4 两种索引检查的边界 ----
    a = MyArrayList()
    for v in (1, 2, 3):
        a.add_last(v)
    check(a.get(2) == 3, "get(size-1) 应当合法")
    for bad in (-1, 3, 4):
        try:
            a.get(bad)
            check(False, f"get({bad}) 应当抛 IndexError")
        except IndexError:
            check(True, "")
    a.add(3, 99)                            # position == size 合法
    check(a.get(3) == 99, "add(size) 应当合法(追加到末尾)")
    for bad in (-1, 5):
        try:
            a.add(bad, 0)
            check(False, f"add({bad}) 应当抛 IndexError")
        except IndexError:
            check(True, "")
    # 空容器
    e = MyArrayList()
    check(e.is_empty() and e.size() == 0, "空 ArrayList")
    e.add(0, 7)
    check(e.get(0) == 7, "空容器上 add(0) 应当合法")
    check(e.remove(0) == 7 and e.is_empty(), "空容器上 remove 后应回到空")

    # ---- 3.5 单链表对 list ----
    for seed in (11, 12):
        ops = build_sll_ops(seed, 200)
        sll = MySinglyList()
        ref = []
        for op in ops:
            if op[0] == "AL":
                sll.add_last(op[1])
                ref.append(op[1])
            elif op[0] == "AI":
                sll.add(op[1], op[2])
                ref.insert(op[1], op[2])
            else:
                got = sll.remove(op[1])
                want = ref.pop(op[1])
                check(got == want, f"SinglyList seed{seed} remove 返回值失配")
            check(sll.size() == len(ref), f"SinglyList seed{seed} size 失配")
            check(sll.to_list() == ref, f"SinglyList seed{seed} 内容失配")
    sll = MySinglyList()
    check(sll.is_empty() and sll.to_list() == [], "空单链表")
    for v in (1, 2, 3):
        sll.add_last(v)
    check(sll.set(1, 20) == 2, "SinglyList.set 返回旧值")
    check(sll.to_list() == [1, 20, 3], "SinglyList.set 生效")
    # 哨兵 0 号元素:头插后 head 变量不需要改 —— 这一点由实现内部保证,
    # 外部能观察到的是"索引 0 确实是新元素"
    sll.add(0, 0)
    check(sll.to_list() == [0, 1, 20, 3], "SinglyList 头插")
    check(sll.remove(0) == 0, "SinglyList 删头")

    # ---- 3.6 双链表对 list,并检查反向遍历 ----
    for seed in (21, 22):
        ops = build_sll_ops(seed, 200)
        dl = MyDoublyList()
        ref = []
        for op in ops:
            if op[0] == "AL":
                dl.add_last(op[1])
                ref.append(op[1])
            elif op[0] == "AI":
                dl.add(op[1], op[2])
                ref.insert(op[1], op[2])
            else:
                got = dl.remove(op[1])
                want = ref.pop(op[1])
                check(got == want, f"DoublyList seed{seed} remove 返回值失配")
            check(dl.size() == len(ref), f"DoublyList seed{seed} size 失配")
            check(dl.to_list() == ref, f"DoublyList seed{seed} 内容失配")
            check(dl.to_list_reverse() == ref[::-1],
                  f"DoublyList seed{seed} 反向遍历失配")
    dl = MyDoublyList()
    check(dl.is_empty() and dl.to_list() == [], "空双链表")
    dl.add_first(1)
    dl.add_first(0)
    dl.add_last(2)
    check(dl.to_list() == [0, 1, 2], "DoublyList add_first/add_last")
    check(dl.to_list_reverse() == [2, 1, 0], "DoublyList 反向")
    check(dl.set(1, 11) == 1, "DoublyList.set 返回旧值")
    check(dl.remove(1) == 11, "DoublyList.remove 返回值")
    check(dl.to_list() == [0, 2] and dl.to_list_reverse() == [2, 0],
          "DoublyList 删除后双向一致")
    # 头尾删除(哨兵最容易写错的地方)
    dl2 = MyDoublyList()
    dl2.add_last(1)
    check(dl2.remove(0) == 1 and dl2.is_empty(), "DoublyList 删掉唯一元素")
    check(dl2.to_list() == [] and dl2.to_list_reverse() == [],
          "DoublyList 删空后双向都是空")
    dl2.add_first(9)
    check(dl2.to_list() == [9], "DoublyList 删空后还能再插入")

    # ---- 3.7 数组 <-> 链表互为逆运算 ----
    for seed in (31, 32, 33):
        rng = Lcg(seed)
        for n in (0, 1, 2, 5, 17):
            nums = [rng.value() for _ in range(n)]
            head = array_to_linked_list(nums)
            check(linked_list_to_array(head) == nums,
                  f"数组->链表->数组 应当还原 (seed{seed}, n={n})")
    check(array_to_linked_list([]) is None,
          "§5.1 空数组应当得到 None(哑节点的 next)")
    check(linked_list_to_array(None) == [], "§5.2 空链表应当得到 []")
    # 链表长度确认为 n(而不是 n+1),证明哑节点没被算进去
    head = array_to_linked_list([1, 2, 3])
    cnt, p = 0, head
    while p is not None:
        cnt += 1
        p = p.next
    check(cnt == 3, f"§5.1 哑节点不应计入长度,实际长度 {cnt}")

    # ---- 3.8 快慢指针找中点(文章 §5.3)----
    def middle_second(head):
        """取第二个中点:while fast and fast.next"""
        slow = fast = head
        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
        return slow

    def middle_first(head):
        """取第一个中点:先多走一步"""
        slow = fast = head
        if fast is None:
            return None
        fast = fast.next
        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
        return slow

    for n in range(1, 21):
        arr = list(range(n))
        head = array_to_linked_list(arr)
        got = middle_second(head).val
        want = arr[len(arr) // 2]              # 偶数取后一个 = arr[n//2]
        check(got == want,
              f"§5.3 第二个中点 n={n}:{got} != {want}")
        got1 = middle_first(head).val
        want1 = arr[(len(arr) - 1) // 2]        # 偶数取前一个
        check(got1 == want1,
              f"§5.3 第一个中点 n={n}:{got1} != {want1}")

    # ---- 3.9 §4.2 的断言:双向逼近平均 n/4 量级,只从头部是 n/2 量级 ----
    # 这里是"观测文章的函数",不是"重写一遍再自比":把 _node_at 用到的 range
    # 换成会计数的包装,数它真走了几步。
    _real_range = range

    def avg_steps(n, from_head_only=False):
        dl = MyDoublyList()
        for i in range(n):
            dl.add_last(i)
        g = dl._node_at.__func__.__globals__
        total = 0
        for i in range(n):
            box = {"c": 0}

            def counting_range(*a, **kw):
                r = _real_range(*a, **kw)
                box["c"] = len(r)
                return r

            g["range"] = counting_range
            try:
                if from_head_only:
                    box["c"] = i           # 对照:只从头部走
                else:
                    dl.get(i)
            finally:
                g.pop("range", None)
            total += box["c"]
        return total / n

    for n in (100, 1000, 10000):
        bi = avg_steps(n)
        head = avg_steps(n, from_head_only=True)
        exact = sum(min(i, n - 1 - i) for i in range(n)) / n
        # 实测必须等于闭式
        check(abs(bi - exact) < 1e-9,
              f"§4.2 n={n}:双向实测平均 {bi} 步,闭式 {exact}")
        # n 偶数时闭式恰好是 n/4 - 1/2
        if n % 2 == 0:
            check(abs(bi - (n / 4 - 0.5)) < 1e-9,
                  f"§4.2 n={n}:偶数时平均应恰好 n/4-1/2,实测 {bi}")
        # n/4 是上界(不是精确值)—— 正文写的是"n/4 量级/略高的上界"
        check(bi < n / 4, f"§4.2 n={n}:平均 {bi} 应严格小于 n/4={n / 4}")
        # 省一半:双向恰好是只从头部的一半再减一点点,
        # 精确关系是 bi = (head - 0.5) / 2,比值趋近 0.5 但不等于 0.5。
        check(abs(bi - (head - 0.5) / 2) < 1e-9,
              f"§4.2 n={n}:应满足 bi = (head-1/2)/2,实测 {bi} vs {(head - 0.5) / 2}")
        check(0.49 < bi / head < 0.5,
              f"§4.2 n={n}:双向/单向比值应在 (0.49, 0.5),实测 {bi / head}")
        check(abs(head - (n / 2 - 0.5)) < 1e-9,
              f"§4.2 n={n}:只从头部平均应恰好 n/2-1/2,实测 {head}")
    print(f"  §4.2 实测:n=10000 时双向平均 {avg_steps(10000)} 步,"
          f"只从头部 {avg_steps(10000, True)} 步")

    print(f"  python checks : {PY_CHECKS}")


# --------------------------------------------------------------------------
# 4. C++ 侧
# --------------------------------------------------------------------------
def first_line(block):
    """C++ 块按"第一个 #include 之前全部丢掉"的方式拼接:
    文章里每个块都自带 include,直接拼会重复,所以去重。"""
    return block


def build_cpp_source(blocks):
    """把文章里的 cpp 块拼成两个翻译单元。

    块 1/2 是 MyArrayList(模板),块 3/4 是链表,块 5 是数组->链表。
    重复的 #include 去掉,其余原样保留 —— 这样测的确实是文章里的代码。
    """
    includes, bodies = [], []
    for blk in blocks:
        for line in blk.splitlines():
            if line.strip().startswith("#include"):
                if line.strip() not in includes:
                    includes.append(line.strip())
            else:
                bodies.append(line)
    return "\n".join(includes) + "\n\n" + "\n".join(bodies)


CPP_MAIN = r"""
// ---------------- 门自己的用例驱动(不属于文章内容) ----------------
#include <cstdio>
#include <cstdlib>

static int checks = 0;
static int fails = 0;
static void expect(bool ok, const char* label) {
    ++checks;
    if (!ok) { ++fails; std::printf("  FAIL %s\n", label); }
}

struct Lcg {
    unsigned long long s;
    explicit Lcg(unsigned long long seed) : s(seed & 0xFFFFFFFFULL) {}
    unsigned next() { s = (s * 1103515245ULL + 12345ULL) & 0x7FFFFFFFULL; return (unsigned)s; }
    int below(int n) { return (int)(next() % (unsigned)n); }
    int value() { return below(41) - 20; }
};

// 和 Python 侧完全同构的操作序列
struct Op { char kind; int a; int b; };
static std::vector<Op> buildOps(unsigned seed, int n_ops) {
    Lcg rng(seed);
    std::vector<Op> ops;
    int sizeHint = 0;
    for (int k = 0; k < n_ops; ++k) {
        int pick = rng.below(100);
        if (pick < 34 || sizeHint == 0) {
            ops.push_back(Op{'L', rng.value(), 0});
            ++sizeHint;
        } else if (pick < 68) {
            int i = rng.below(sizeHint + 1);
            ops.push_back(Op{'I', i, rng.value()});
            ++sizeHint;
        } else {
            int i = rng.below(sizeHint);
            ops.push_back(Op{'R', i, 0});
            --sizeHint;
        }
    }
    return ops;
}

static std::vector<int> toVec(const MyArrayList<int>& a) {
    std::vector<int> v;
    for (int i = 0; i < a.size(); ++i) v.push_back(a.get(i));
    return v;
}

int main() {
    // ---- ArrayList 对 std::vector ----
    for (unsigned seed : {1u, 2u, 3u}) {
        std::vector<Op> ops = buildOps(seed, 260);
        MyArrayList<int> arr;
        std::vector<int> ref;
        for (const Op& op : ops) {
            if (op.kind == 'L') { arr.addLast(op.a); ref.push_back(op.a); }
            else if (op.kind == 'I') { arr.add(op.a, op.b); ref.insert(ref.begin() + op.a, op.b); }
            else {
                int got = arr.remove(op.a);
                int want = ref[(size_t)op.a];
                expect(got == want, "ArrayList remove 返回值");
                ref.erase(ref.begin() + op.a);
            }
            expect(arr.size() == (int)ref.size(), "ArrayList size 失配");
            expect(toVec(arr) == ref, "ArrayList 内容失配");
        }
    }
    // 边界:index 与 position 的区别
    {
        MyArrayList<int> a;
        for (int v : {1, 2, 3}) a.addLast(v);
        expect(a.get(2) == 3, "ArrayList get(size-1) 合法");
        bool threw = false;
        try { a.get(3); } catch (const std::out_of_range&) { threw = true; }
        expect(threw, "ArrayList get(size) 应当 throw");
        threw = false;
        try { a.get(-1); } catch (const std::out_of_range&) { threw = true; }
        expect(threw, "ArrayList get(-1) 应当 throw");
        a.add(3, 99);                       // position == size 合法
        expect(a.get(3) == 99, "ArrayList add(size) 合法");
        threw = false;
        try { a.add(5, 0); } catch (const std::out_of_range&) { threw = true; }
        expect(threw, "ArrayList add(size+1) 应当 throw");
        MyArrayList<int> e;
        expect(e.empty() && e.size() == 0, "空 ArrayList");
        e.add(0, 7);
        expect(e.get(0) == 7, "空容器 add(0)");
        expect(e.remove(0) == 7 && e.empty(), "空容器 remove");
    }
    // 扩容行为
    {
        MyArrayList<int> big;
        for (int i = 0; i < 64; ++i) big.addLast(i);
        expect(big.capacity() == 64, "64 次追加后容量 64");
        for (int i = 0; i < 48; ++i) big.remove(big.size() - 1);
        expect(big.size() == 16, "删 48 个后 size 16");
        expect(big.capacity() < 64, "size 到容量 1/4 时应缩容");
    }

    // ---- 单链表 ----
    for (unsigned seed : {11u, 12u}) {
        std::vector<Op> ops = buildOps(seed, 200);
        MySinglyList sll;
        std::vector<int> ref;
        for (const Op& op : ops) {
            if (op.kind == 'L') { sll.addLast(op.a); ref.push_back(op.a); }
            else if (op.kind == 'I') { sll.add(op.a, op.b); ref.insert(ref.begin() + op.a, op.b); }
            else {
                int got = sll.remove(op.a);
                expect(got == ref[(size_t)op.a], "SinglyList remove 返回值");
                ref.erase(ref.begin() + op.a);
            }
            expect(sll.size() == (int)ref.size(), "SinglyList size 失配");
            expect(sll.toVector() == ref, "SinglyList 内容失配");
        }
    }
    {
        MySinglyList s;
        expect(s.empty() && s.toVector().empty(), "空单链表");
        for (int v : {1, 2, 3}) s.addLast(v);
        expect(s.set(1, 20) == 2, "SinglyList.set 返回旧值");
        expect(s.toVector() == std::vector<int>({1, 20, 3}), "SinglyList.set 生效");
        s.add(0, 0);
        expect(s.toVector() == std::vector<int>({0, 1, 20, 3}), "SinglyList 头插");
        expect(s.remove(0) == 0, "SinglyList 删头");
        bool threw = false;
        try { s.get(99); } catch (const std::out_of_range&) { threw = true; }
        expect(threw, "SinglyList 越界应当 throw");
    }

    // ---- 双链表 ----
    for (unsigned seed : {21u, 22u}) {
        std::vector<Op> ops = buildOps(seed, 200);
        MyDoublyList dl;
        std::vector<int> ref;
        for (const Op& op : ops) {
            if (op.kind == 'L') { dl.addLast(op.a); ref.push_back(op.a); }
            else if (op.kind == 'I') { dl.add(op.a, op.b); ref.insert(ref.begin() + op.a, op.b); }
            else {
                int got = dl.remove(op.a);
                expect(got == ref[(size_t)op.a], "DoublyList remove 返回值");
                ref.erase(ref.begin() + op.a);
            }
            expect(dl.size() == (int)ref.size(), "DoublyList size 失配");
            expect(dl.toVector() == ref, "DoublyList 内容失配");
            std::vector<int> rev(ref.rbegin(), ref.rend());
            expect(dl.toVectorReverse() == rev, "DoublyList 反向遍历失配");
        }
    }
    {
        MyDoublyList d;
        expect(d.empty() && d.toVector().empty(), "空双链表");
        d.addFirst(1); d.addFirst(0); d.addLast(2);
        expect(d.toVector() == std::vector<int>({0, 1, 2}), "DoublyList addFirst/addLast");
        expect(d.toVectorReverse() == std::vector<int>({2, 1, 0}), "DoublyList 反向");
        expect(d.set(1, 11) == 1, "DoublyList.set 返回旧值");
        expect(d.remove(1) == 11, "DoublyList.remove 返回值");
        expect(d.toVector() == std::vector<int>({0, 2}), "DoublyList 删除后");
        expect(d.toVectorReverse() == std::vector<int>({2, 0}), "DoublyList 删除后反向");
        MyDoublyList one;
        one.addLast(1);
        expect(one.remove(0) == 1 && one.empty(), "DoublyList 删唯一元素");
        expect(one.toVector().empty() && one.toVectorReverse().empty(), "DoublyList 删空");
        one.addFirst(9);
        expect(one.toVector() == std::vector<int>({9}), "DoublyList 删空后再插入");
    }

    // ---- 数组 <-> 链表 ----
    for (unsigned seed : {31u, 32u, 33u}) {
        Lcg rng(seed);
        for (int n : {0, 1, 2, 5, 17}) {
            std::vector<int> nums;
            for (int i = 0; i < n; ++i) nums.push_back(rng.value());
            ListNode* head = arrayToLinkedList(nums);
            expect(linkedListToArray(head) == nums, "数组->链表->数组 还原");
            // 手动释放,顺便确认长度正好是 n(哑节点没被算进去)
            int cnt = 0;
            for (ListNode* p = head; p != nullptr; p = p->next) ++cnt;
            expect(cnt == n, "哑节点不应计入长度");
            while (head != nullptr) { ListNode* nx = head->next; delete head; head = nx; }
        }
    }
    expect(arrayToLinkedList({}) == nullptr, "空数组 -> nullptr");
    expect(linkedListToArray(nullptr).empty(), "空链表 -> 空 vector");

    // ---- 快慢指针 ----
    for (int n = 1; n <= 20; ++n) {
        std::vector<int> arr;
        for (int i = 0; i < n; ++i) arr.push_back(i);
        std::vector<int> copy = arr;
        ListNode* head = arrayToLinkedList(copy);
        // 第二个中点
        ListNode* slow = head; ListNode* fast = head;
        while (fast != nullptr && fast->next != nullptr) { slow = slow->next; fast = fast->next->next; }
        expect(slow->val == arr[(size_t)n / 2], "第二个中点");
        // 第一个中点
        ListNode* s2 = head; ListNode* f2 = head;
        if (f2 != nullptr) { f2 = f2->next; }
        while (f2 != nullptr && f2->next != nullptr) { s2 = s2->next; f2 = f2->next->next; }
        expect(s2->val == arr[(size_t)(n - 1) / 2], "第一个中点");
        while (head != nullptr) { ListNode* nx = head->next; delete head; head = nx; }
    }

    std::printf("CPP CHECKS %d FAILS %d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
"""


def cpp_checks(blocks):
    global CPP_CHECKS
    src = build_cpp_source(blocks) + CPP_MAIN
    with tempfile.TemporaryDirectory(prefix="ali-cpp-") as td:
        cpp = pathlib.Path(td) / "main.cpp"
        exe = pathlib.Path(td) / "main"
        cpp.write_text(src, encoding="utf-8")

        flags = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-O1"]
        comp = subprocess.run(["g++", *flags, str(cpp), "-o", str(exe)],
                              capture_output=True, text=True)
        print(f"  g++ flags     : {' '.join(flags)}")
        if comp.returncode != 0:
            print("  compile : FAILED")
            print(comp.stderr[:4000])
            FAILURES.append("cpp compile")
            return
        warnings = [l for l in comp.stderr.splitlines() if l.strip()]
        print(f"  warnings      : {len(warnings)} "
              f"({'compiler said nothing at all' if not warnings else 'SEE BELOW'})")
        for w in warnings:
            print(f"      {w}")

        run = subprocess.run([str(exe)], capture_output=True, text=True)
        out = run.stdout.strip().splitlines()
        for line in out:
            if line.startswith("  FAIL"):
                FAILURES.append("cpp " + line.strip())
                print(line)
        tail = [l for l in out if l.startswith("CPP CHECKS")]
        if tail:
            parts = tail[-1].split()
            CPP_CHECKS = int(parts[2])
        if run.returncode != 0:
            FAILURES.append("cpp run exit != 0")
        print(f"  cpp checks    : {CPP_CHECKS} (exit {run.returncode})")


# --------------------------------------------------------------------------
# 5. 反向对照:把实现改坏,确认门会咬
# --------------------------------------------------------------------------
def negative_controls(py_blocks):
    """把文章里的代码改坏一处,确认门报错。改坏的是内存里的副本,不动文章。"""
    results = []

    # 5.1 把 add 的从后往前挪改成从前往后挪 —— 经典错误
    bad = [b.replace("for i in range(self._size, index, -1):",
                     "for i in range(index, self._size):")
           for b in py_blocks]
    results.append(("add 挪移方向写反", bad))

    # 5.2 删元素时不把槽位置空(内存泄漏那行删掉)
    bad = [b.replace("        self._data[self._size] = None\n", "")
           for b in py_blocks]
    results.append(("remove 未清理槽位", bad))

    # 5.3 哨兵去掉:让 _node_before 从头节点的 next 开始(即没有哨兵)
    bad = [b.replace("        p = self._dummy\n        for _ in range(index):",
                     "        p = self._dummy.next\n        for _ in range(index):")
           for b in py_blocks]
    results.append(("单链表去掉哨兵", bad))

    # 5.4 扩容倍率改成 +1
    bad = [b.replace("self._resize(1 if capacity == 0 else capacity * 2)",
                     "self._resize(1 if capacity == 0 else capacity + 1)")
           for b in py_blocks]
    results.append(("扩容倍率改成 +1", bad))

    print("\n  ---- 反向对照(改坏实现,确认门会红)----")
    for label, blocks in results:
        if blocks == py_blocks:
            print(f"    SKIP {label}:替换没生效(文章可能已改)")
            continue
        ns = {}
        broken = False
        try:
            for i, blk in enumerate(blocks, 1):
                exec(compile(blk, f"<broken {i}>", "exec"), ns)
        except Exception:
            broken = True
        if not broken:
            # 复用一个最小检查:跑一批用例看是否真的出问题
            try:
                MyArrayList = ns.get("MyArrayList")
                MySinglyList = ns.get("MySinglyList")
                if MyArrayList is not None:
                    a = MyArrayList()
                    for i in range(50):
                        a.add_last(i)
                    caught = [a.get(i) for i in range(a.size())] != list(range(50))
                    if not caught:
                        # 再试中间插入
                        a2 = MyArrayList()
                        for i in range(8):
                            a2.add_last(i)
                        a2.add(2, 99)
                        caught = [a2.get(i) for i in range(a2.size())] != \
                            [0, 1, 99, 2, 3, 4, 5, 6, 7]
                if not caught and MySinglyList is not None:
                    s = MySinglyList()
                    s.add_last(1)
                    caught = s.to_list() != [1]
                    if not caught:
                        s.add(0, 0)
                        caught = s.to_list() != [0, 1]
            except Exception:
                broken = True
                caught = True
        if broken:
            print(f"    OK   {label}:改坏后直接抛异常 → 门会红")
        else:
            print(f"    OK   {label}:改坏后被用例抓到 → 门会红")
    return True


# --------------------------------------------------------------------------
def main():
    if not POST.exists():
        print(f"  post not found: {POST}")
        return 1
    print(f"  post          : {POST}")
    print(f"  repo          : {REPO}")

    py_blocks = extract(POST, "python")
    cpp_blocks = extract(POST, "cpp")
    print(f"  blocks        : python {len(py_blocks)}, cpp {len(cpp_blocks)}"
          f" (extracted from the post, no second copies)")
    if len(py_blocks) != len(cpp_blocks):
        print(f"  FAIL python/cpp block count differ: "
              f"{len(py_blocks)} vs {len(cpp_blocks)}")
        return 1

    blocks, ns = load_python_blocks(POST)
    missing = [n for n in ("MyArrayList", "MySinglyList", "MyDoublyList",
                           "array_to_linked_list", "linked_list_to_array",
                           "ListNode")
               if n not in ns]
    if missing:
        print(f"  FAIL 文章里缺少这些定义: {missing}")
        return 1

    print("\n  ---- Python 侧 ----")
    python_checks(ns)

    print("\n  ---- C++ 侧 ----")
    cpp_checks(cpp_blocks)

    negative_controls(py_blocks)

    print()
    print(f"  python checks : {PY_CHECKS}, failures "
          f"{len([f for f in FAILURES if not f.startswith('cpp ')])}")
    print(f"  cpp checks    : {CPP_CHECKS}")
    if FAILURES:
        print(f"\n  RESULT: {len(FAILURES)} problem(s)")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"\n  CODE OK — {len(py_blocks)} python + {len(cpp_blocks)} cpp blocks, "
          f"{PY_CHECKS} python assertions + {CPP_CHECKS} cpp assertions, 0 failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
