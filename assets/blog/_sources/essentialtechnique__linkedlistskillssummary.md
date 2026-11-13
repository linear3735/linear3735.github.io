# 双指针技巧秒杀七道链表题目
url: https://labuladong.online/zh/algo/essential-technique/linked-list-skills-summary/
folder: 第零章、核心刷题框架汇总

提到的力扣题号: 19, 21, 23, 86, 142, 160, 876

## 这节的小标题
- 合并两个有序链表
- 单链表的分解
- 合并 k 个有序链表
- 单链表的倒数第 k 个节点
- 单链表的中点
- 判断链表是否包含环
- 两个链表是否相交

## 复杂度结论
- 这个算法是面试常考题，它的时间复杂度是多少呢？
- 优先队列 pq 中的元素个数最多是 kkk，所以一次 poll 或者 add 方法的时间复杂度是 O(logk)O(logk)O(logk)；所有的链表节点都会被加入和弹出 pq，所以算法整体的时间复杂度是 O(Nlogk)O(Nlogk)O(Nlogk)，其中 kkk 是
- 当然，如果用 big O 表示法来计算时间复杂度，无论遍历一次链表和遍历两次链表的时间复杂度都是 O(N)O(N)O(N)，但上述这个算法更有技巧性
- 这样，这道题就解决了，空间复杂度为 O(1)O(1)O(1)，时间复杂度为 O(N)O(N)O(N)
- 虽然代码多一些，但是时间复杂度是还是 O(N)O(N)O(N)，而且会更容易理解一些

## 涉及的关键术语
- ListNode, next, fast, head, slow, while, dummy, GoJavaJavaScriptPython, lists, Solution, headA, headB, val, length, Linked, else
