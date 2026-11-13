# 用数组实现队列/栈
url: https://labuladong.online/zh/algo/data-structure-basic/array-queue-stack/
folder: 手把手带你实现队列/栈

## 这节的小标题
- 用数组实现栈
- 用数组实现队列

## 复杂度结论
- 因为数组尾部增删元素的时间复杂度都是 O(1)O(1)O(1)，符合栈的要求
- // 向栈顶加入元素，时间复杂度 O(1)
- // 从栈顶弹出元素，时间复杂度 O(1)
- // 查看栈顶元素，时间复杂度 O(1)
- // 返回栈中的元素个数，时间复杂度 O(1)
- 因为数组头部增删元素的时间复杂度都是 O(n)O(n)O(n)，不符合要求
- 但是我们可以改用前文 环形数组技巧 中实现的 CycleArray 类，这个数据结构在头部增删元素的时间复杂度是 O(1)O(1)O(1)，符合栈的要求

## 涉及的关键术语
- arr, size, CycleArray, API, MyArrayList, GoJavaJavaScriptPython, ArrayList, push, pop, peek, removeFirst, MyArrayQueue, MyArrayStack, add, remove, get
