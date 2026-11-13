# 算法就像搭乐高：手撸 LRU 算法
url: https://labuladong.online/zh/algo/data-structure/lru-cache/
folder: 经典数据结构设计

提到的力扣题号: 146

## 这节的小标题
- 一、LRU 算法描述
- 二、LRU 算法设计
- 三、代码实现

## 复杂度结论
- 注意哦，get 和 put 方法必须都是 O(1)O(1)O(1) 的时间复杂度，我们举个具体例子来看看 LRU 算法怎么工作：
- 分析上面的操作过程，要让 put 和 get 方法的时间复杂度为 O(1)，我们可以总结出 cache 这个数据结构必要的条件：
- 删除一个节点不光要得到该节点本身的指针，也需要操作其前驱节点的指针，而双向链表才能支持直接查找前驱，保证操作的时间复杂度 O(1)

## 涉及的关键术语
- key, cache, Node, val, map, LRU, put, get, next, prev, tail, size, remove, head, LRUCache, cap
