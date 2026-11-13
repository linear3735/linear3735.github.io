# 用数组加强哈希表（ArrayHashMap）
url: https://labuladong.online/zh/algo/data-structure-basic/hashtable-with-array/
folder: 哈希表结构的种种变换

## 这节的小标题
- 添加 randomKey() API

## 复杂度结论
- 让你基于标准哈希表的 API 之上，再添加一个新的 randomKey() API，可以在 O(1)O(1)O(1) 的时间复杂度返回一个随机键：
- // 获取 key 对应的 value，时间复杂度 O(1)
- // 添加/修改 key-value 对，时间复杂度 O(1)
- // 删除 key-value 对，时间复杂度 O(1)
- // 是否包含 key，时间复杂度 O(1)
- // 返回所有 key，时间复杂度 O(N)
- // 新增 API：随机返回一个 key，要求时间复杂度 O(1)
- 1、有个循环，最坏时间复杂度上升到了 O(N)O(N)O(N)，不符合 O(1)O(1)O(1) 的要求

## 涉及的关键术语
- arr, key, length, API, Random, randomKey, value, nextInt, table, randomElement, LinkedHashMap, keys, while, ArrayHashMap, interface, Map
