# 数组（顺序存储）基本原理
url: https://labuladong.online/zh/algo/data-structure-basic/array-basic/
folder: 手把手带你实现动态数组

## 这节的小标题
- 静态数组
- 增删查改
- 增
- 删
- 总结
- 动态数组

## 复杂度结论
- 计算机的内存寻址时间可以认为是 O(1)O(1)O(1)，所以数组的随机访问时间复杂度是 O(1)O(1)O(1)
- 可以看到，由于只是对索引赋值，所以在数组末尾追加元素的时间复杂度是 O(1)O(1)O(1)
- 综上，在数组中间插入元素的时间复杂度是 O(N)O(N)O(N)，因为涉及到数据搬移，给新元素腾地方
- 综上，数组的扩容操作会涉及到新数组的开辟和数据的复制，时间复杂度是 O(N)O(N)O(N)
- 带大家具体实现动态数组的时候，会有更完善的方法删除数组元素，这里只是为了说明删除数组尾部元素的本质就是进行一次随机访问，时间复杂度是 O(1)O(1)O(1)
- 综上，在数组中间删除元素的时间复杂度是 O(N)O(N)O(N)，因为涉及到数据搬移
- 综上，静态数组的增删查改操作的时间复杂度是：
- - 查：给定指定索引，查询索引对应的元素的值，时间复杂度 O(1)O(1)O(1)

## 涉及的关键术语
- arr, GoJavaJavaScriptPython, API, sizeof, insert, Java, Golang, memset, ArrayList, push, remove, Python, JavaScript, bit, append, comments
