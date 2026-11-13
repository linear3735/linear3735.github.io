# 动态数组代码实现
url: https://labuladong.online/zh/algo/data-structure-basic/array-implement/
folder: 手把手带你实现动态数组

提到的力扣题号: 707

## 这节的小标题
- 几个关键点
- 关键点一、自动扩缩容
- 关键点二、索引越界的检查
- 关键点三、删除元素谨防内存泄漏
- 其他细节优化
- 动态数组代码实现

## 复杂度结论
- 不过它再怎么优化，本质上也是要搬移数据，时间复杂度都是 O(n)O(n)O(n)
- 本文的重点在于让你理解数组增删查改 API 的基本实现思路以及时间复杂度，如果对这些细节感兴趣，可以找到编程语言标准库的源码深入研究

## 涉及的关键术语
- size, data, index, cap, checkPositionIndex, deletedVal, MyArrayList, length, resize, checkElementIndex, nums, Java, import, java, util, removeLast
