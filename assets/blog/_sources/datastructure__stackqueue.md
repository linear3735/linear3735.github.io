# 队列实现栈以及栈实现队列
url: https://labuladong.online/zh/algo/data-structure/stack-queue/
folder: 经典队列/栈算法

提到的力扣题号: 225, 232

## 这节的小标题
- 一、用栈实现队列
- 二、用队列实现栈

## 复杂度结论
- 值得一提的是，这几个操作的时间复杂度是多少呢？
- 有点意思的是 peek 操作，调用它时可能触发 while 循环，这样的话时间复杂度是 O(N)，但是大部分情况下 while 循环不会被触发，时间复杂度是 O(1)
- 由于 pop 操作调用了 peek，它的时间复杂度和 peek 相同
- 像这种情况，可以说它们的最坏时间复杂度是 O(N)，因为包含 while 循环，可能需要从 s1 往 s2 搬移元素
- 但是它们的均摊时间复杂度是 O(1)，这个要这么理解：对于一个元素，最多只可能被搬运一次，也就是说 peek 操作平均到每个元素的时间复杂度是 O(1)
- 关于时间复杂度的分析方法，详见 时空复杂度实用分析方法
- 很明显，用队列实现栈的话，pop 操作时间复杂度是 O(N)，其他操作都是 O(1)

## 涉及的关键术语
- pop, peek, size, push, top_elem, poll, GoJavaJavaScriptPython, while, offer, isEmpty, API, boolean, empty, MyStack, Stack, top
