# 单调队列结构解决滑动窗口问题
url: https://labuladong.online/zh/algo/data-structure/monotonic-queue/
folder: 经典队列/栈算法

提到的力扣题号: 239

## 这节的小标题
- 一、搭建解题框架
- 二、实现单调队列数据结构
- 拓展延伸

## 复杂度结论
- 但本文开头说的那个判断一个窗口中最值的例子，你无法单凭移出窗口的那个元素更新窗口的最值，除非重新遍历所有元素，但这样的话时间复杂度就上来了，这是我们不希望看到的
- 当然，单调队列这几个 API 的实现方法肯定跟一般的 Queue 不一样，不过我们暂且不管，而且认为这几个操作的时间复杂度都是 O(1)O(1)O(1)，先把这道「滑动窗口」问题的解答框架搭出来：
- 关于单调队列 API 的时间复杂度，读者可能有疑惑：push 操作中含有 while 循环，最坏情况下的时间复杂度应该 O(N)O(N)O(N) 呀，再加上一层 for 循环，本算法的时间复杂度应该是 O(N2)O(N^2)O(N2) 才对吧？
- 单独看 push 操作，最坏时间复杂度确实是 O(N)O(N)O(N)，但是平均时间复杂度是 O(1)O(1)O(1)
- 我们一般用平均复杂度而不是最坏时间复杂度来衡量 API 接口，所以这个算法整体的时间复杂度是 O(N)O(N)O(N)，而不是 O(N2)O(N^2)O(N2)
- 是把 nums 中的每个元素加入和移出 window 至多一次，不可能把同一个元素多次移入移出 window，所以整体的时间复杂度是 O(N)O(N)O(N)
- 空间复杂度很容易分析，就是窗口的大小 O(k)O(k)O(k)

## 涉及的关键术语
- API, MonotonicQueue, push, maxq, window, GoJavaJavaScriptPython, pop, nums, max, LinkedList, res, ArrayList, while, getFirst, maxSlidingWindow, Queue
