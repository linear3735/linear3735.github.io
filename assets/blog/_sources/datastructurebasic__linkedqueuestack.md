# 用链表实现队列/栈
url: https://labuladong.online/zh/algo/data-structure-basic/linked-queue-stack/
folder: 手把手带你实现队列/栈

## 这节的小标题
- 用链表实现栈
- 用链表实现队列

## 复杂度结论
- // 向栈顶加入元素，时间复杂度 O(1)
- // 从栈顶弹出元素，时间复杂度 O(1)
- // 查看栈顶元素，时间复杂度 O(1)
- // 返回栈中的元素个数，时间复杂度 O(1)
- 提示上面这段代码相当于是把双链表的尾部作为栈顶，在双链表尾部增删元素的时间复杂度都是 O(1)，符合要求
- 当然，你也可以把双链表的头部作为栈顶，因为双链表头部增删元素的时间复杂度也是 O(1)，所以这样实现也是一样的
- // 向队尾插入元素，时间复杂度 O(1)
- // 从队头删除元素，时间复杂度 O(1)

## 涉及的关键术语
- list, push, queue, stack, System, out, println, LinkedList, peek, pop, size, API, MyLinkedStack, addLast, MyLinkedQueue, GoJavaJavaScriptPython
