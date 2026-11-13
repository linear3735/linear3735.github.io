# 二叉堆结构的运用：堆排序
url: https://labuladong.online/zh/algo/data-structure-basic/heap-sort/
folder: 十大排序算法原理及可视化

## 复杂度结论
- 3、优先级队列插入元素时，首先把元素追加到二叉堆底部，然后调用 swim 方法把该元素上浮到合适的位置，时间复杂度是 O(log⁡N)O(\log N)O(logN)
- 元素时，首先把堆底的最后一个元素交换到堆顶作为新的堆顶元素，然后调用 sink 方法把这个新的堆顶元素下沉到合适的位置，时间复杂度是 O(log⁡N)O(\log N)O(logN)
- // push 操作会自动构建二叉堆，时间复杂度为 O(logN)
- 因为优先级队列的 push, pop 方法的复杂度都是 O(log⁡N)O(\log N)O(logN)，所以整个排序的时间复杂度是 O(Nlog⁡N)O(N \log N)O(NlogN)，其中 N 是输入数组的长度
- 这个思路可以得到正确的排序结果，但空间复杂度是 O(N)O(N)O(N)，因为我们创建的这个优先级队列是一个额外的数据结构，它的底层使用了一个数组来存储元素

## 涉及的关键术语
- log, swim, sink, logN, Sort, Nlog, NlogN, SimpleMinPQ, nums, push, Heapify, Heap, num, Array912, heap, GoJavaJavaScriptPython
