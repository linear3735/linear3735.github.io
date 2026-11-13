# 数据压缩和霍夫曼树
url: https://labuladong.online/zh/algo/data-structure-basic/huffman-tree/
folder: 二叉树结构的种种变换

## 这节的小标题
- 浅谈数据压缩
- 定长编码 vs 变长编码
- 变长编码的难点

## 复杂度结论
- 假设最长的编码长度为 KKK，编码后的数据长度为 NNN，那么解码的时间复杂度为 O(NK)O(NK)O(NK)
- 在实际的编解码场景中 NNN 往往很大，即便 KKK 较小，解码速度慢几倍也是非常糟糕的，所以我们需要保证编解码算法的时间复杂度为 O(N)O(N)O(N)，且压缩率尽可能高

## 涉及的关键术语
- aaabacc, zip, ASCII, UTF, length, encoding, KKK, NNN, hahahahahahaha, fixed, variable, bit, comments, labuladong
