# 双端队列（Deque）原理及实现
url: https://labuladong.online/zh/algo/data-structure-basic/deque-implement/
folder: 手把手带你实现队列/栈

## 这节的小标题
- 基本原理
- 用链表实现双端队列
- 用数组实现双端队列

## 复杂度结论
- // 从队头插入元素，时间复杂度 O(1)
- // 从队尾插入元素，时间复杂度 O(1)
- // 从队头删除元素，时间复杂度 O(1)
- // 从队尾删除元素，时间复杂度 O(1)
- // 查看队头元素，时间复杂度 O(1)
- // 查看队尾元素，时间复杂度 O(1)
- 因为双链表本就支持 O(1)O(1)O(1) 时间复杂度在链表的头尾增删元素：

## 涉及的关键术语
- deque, addFirst, addLast, list, arr, removeFirst, removeLast, peekFirst, peekLast, System, out, println, GoJavaJavaScriptPython, LinkedList, MyListDeque, CycleArray
