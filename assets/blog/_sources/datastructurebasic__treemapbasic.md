# 二叉搜索树的应用及可视化
url: https://labuladong.online/zh/algo/data-structure-basic/tree-map-basic/
folder: 二叉树结构的种种变换

## 这节的小标题
- 二叉搜索树的优势
- TreeMap/TreeSet 实现原理

## 复杂度结论
- 这里展示的是查找目标元素的场景，可以看到，利用 BST 左小右大的特性，可以迅速定位到目标节点，理想的时间复杂度是树的高度 O(logN)O(logN)O(logN)，而普通的二叉树遍历函数则需要 O(N)O(N)O(N) 的时间遍历所有节点
- 至于其他增、删、改的操作，你首先查到目标节点，才能进行增删改的操作对吧？增删改的操作无非就是改一改指针，所以增删改的时间复杂度也是 O(logN)O(logN)O(logN)

## 涉及的关键术语
- TreeMap, logN, key, TreeNode, TreeSet, BST, value, HashMap, GoJavaJavaScriptPython, left, right, put, get, remove, containsKey, List
