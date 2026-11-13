#!/usr/bin/env python3
"""The Python in the post, verified.  Extracts every ```python block from the
post, execs it, and runs the cases below.  Run: python3 py_solutions_test.py"""
import heapq, re, sys
from pathlib import Path

POST = Path.home() / "projects/linear3735.github.io/_posts/2026-11-08-interview-algo-speedrun.md"
post = POST.read_text(encoding="utf-8")
blocks = re.findall(r"```python\n(.*?)```", post, re.S)
assert blocks, "no python blocks found in post"
ns = {}
exec(compile("\n".join(blocks), str(POST), "exec"), ns)
ListNode = ns["ListNode"]

def L(*vals):
    d = ListNode(-1); p = d
    for v in vals:
        p.next = ListNode(v); p = p.next
    return d.next

def show(h, cap=40):
    out, seen = [], set()
    while h and len(out) < cap:
        if id(h) in seen:
            out.append("...CYCLE"); break
        seen.add(id(h)); out.append(h.val); h = h.next
    return out

fails = []
def check(name, got, want):
    ok = got == want
    print(f"  {'OK  ' if ok else 'FAIL'} {name}: got {got} want {want}")
    if not ok:
        fails.append(name)

# 21
check("21 both empty", show(ns["mergeTwoLists"](None, None)), [])
check("21 one empty", show(ns["mergeTwoLists"](L(1,2,3), None)), [1,2,3])
check("21 [1,2,4]+[1,3,4]", show(ns["mergeTwoLists"](L(1,2,4), L(1,3,4))), [1,1,2,3,4,4])
# 86
check("86 x=3", show(ns["partition"](L(1,4,3,2,5,2), 3)), [1,2,2,4,3,5])
check("86 empty", show(ns["partition"](None, 3)), [])
# 23
check("23 3 lists", show(ns["mergeKLists"]([L(1,4,5), L(1,3,4), L(2,6)])), [1,1,2,3,4,4,5,6])
check("23 ties stress", show(ns["mergeKLists"]([L(1,1), L(1,1), L(1,1)])), [1]*6)
check("23 no lists", show(ns["mergeKLists"]([])), [])
# 19
check("19 k=2", ns["findFromEnd"](L(1,2,3,4,5), 2).val, 4)
check("19 k=1", ns["findFromEnd"](L(1,2,3), 1).val, 3)
# 876
check("876 odd", show(ns["middleNode"](L(1,2,3,4,5))), [3,4,5])
check("876 even -> LATER middle", ns["middleNode"](L(1,2,3,4)).val, 3)
# 141
check("141 no cycle", ns["hasCycle"](L(1,2,3)), False)
c = L(3,2,0,-4); t = c
while t.next: t = t.next
t.next = c.next
check("141 cycle", ns["hasCycle"](c), True)
# 142
check("142 no cycle", ns["detectCycle"](L(1,2,3)), None)
c2 = L(3,2,0,-4); t2 = c2
while t2.next: t2 = t2.next
t2.next = c2
check("142 cycle at head", ns["detectCycle"](c2).val, 3)
# 160
sh = L(8,4,5); A = L(4,1); B = L(5,6,1)
pa = A
while pa.next: pa = pa.next
pa.next = sh
pb = B
while pb.next: pb = pb.next
pb.next = sh
check("160 intersect at 8", ns["getIntersectionNode"](A, B).val, 8)
check("160 no intersect", ns["getIntersectionNode"](L(2,6,4), L(1,5)), None)

print(f"RESULT: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURES'}")
sys.exit(1 if fails else 0)
