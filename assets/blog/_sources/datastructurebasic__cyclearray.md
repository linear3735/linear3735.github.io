# 环形数组技巧及实现
url: https://labuladong.online/zh/algo/data-structure-basic/cycle-array/
folder: 数组链表的种种变换

## 这节的小标题
- 环形数组原理
- 动手环节
- 代码实现
- 思考题

## 复杂度结论
- // 在数组尾部添加元素，时间复杂度 O(1)
- // 删除数组尾部元素，时间复杂度 O(1)
- // 获取数组头部元素，时间复杂度 O(1)
- // 获取数组尾部元素，时间复杂度 O(1)
- 我们都说，在数组增删头部元素的时间复杂度是 O(N)O(N)O(N)，因为需要搬移元素
- 但是，如果我们使用环形数组，其实是可以实现在 O(1)O(1)O(1) 的时间复杂度内增删头部元素的
- 但是你可以思考一下，难道环形数组实现不了这些方法么？环形数组实现这些方法，时间复杂度相比普通数组，有退化吗？
- 也可以获取指定索引的元素（随机访问），只不过不是直接访问对应索引，而是要通过 start 计算出真实索引，但计算和访问的时间复杂度依然是 O(1)O(1)O(1)；

## 涉及的关键术语
- end, size, arr, start, count, val, resize, isEmpty, addLast, CycleArray, throw, IllegalStateException, Array, empty, GoJavaJavaScriptPython, length
