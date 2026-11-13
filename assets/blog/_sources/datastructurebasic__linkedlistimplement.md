# 链表代码实现
url: https://labuladong.online/zh/algo/data-structure-basic/linkedlist-implement/
folder: 手把手带你实现单/双链表

提到的力扣题号: 707

## 这节的小标题
- 几个关键点
- 关键点一、同时持有头尾节点的引用
- 关键点二、虚拟头尾节点
- 关键点三、内存泄露？
- 双链表代码实现
- 单链表代码实现

## 复杂度结论
- 因为在软件开发中，在容器尾部添加元素是个非常高频的操作，双链表持有尾部节点的引用，就可以在 O(1)O(1)O(1) 的时间复杂度内完成尾部添加元素的操作
- 比如你要在单链表尾部添加元素，如果没有尾部节点的引用，你就需要遍历整个链表找到尾部节点，时间复杂度是 O(n)O(n)O(n)；如果有尾部节点的引用，就可以在 O(1)O(1)O(1) 的时间复杂度内完成尾部添加元素的操作

## 涉及的关键术语
- next, Node, prev, index, head, val, size, tail, temp, list, newNode, addLast, System, out, element, getNode
