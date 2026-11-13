# 链表（链式存储）基本原理
url: https://labuladong.online/zh/algo/data-structure-basic/linkedlist-basic/
folder: 手把手带你实现单/双链表

## 这节的小标题
- 为什么需要链表
- 单链表的基本操作
- 查/改
- 增
- 删
- 双链表的基本操作
- 查/改
- 增
- 删
- 接下来

## 复杂度结论
- 这个操作的最坏时间复杂度是 O(n)O(n)O(n)，其中 nnn 是链表的长度
- 这个操作的时间复杂度是 O(1)O(1)O(1)
- 这个操作的时间复杂度是 O(n)O(n)O(n)，因为需要先遍历到链表尾部
- 这个操作的时间复杂度是 O(n)O(n)O(n)，因为需要先找到插入位置的前驱节点
- 这个操作的时间复杂度是 O(n)O(n)O(n)，因为需要先找到被删除节点的前驱节点
- 这个操作的时间复杂度是 O(n)O(n)O(n)，因为需要先遍历到倒数第二个节点
- 这个操作的最坏时间复杂度是 O(n)O(n)O(n)
- 这个操作的时间复杂度是 O(n)O(n)O(n)，因为需要先遍历到尾节点

## 涉及的关键术语
- head, next, DoublyListNode, ListNode, GoJavaJavaScriptPython, prev, val, tail, createLinkedList, arr, createDoublyLinkedList, newNode, Node, while, newHead, System
