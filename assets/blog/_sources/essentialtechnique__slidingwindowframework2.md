# 滑动窗口算法核心代码模板
url: https://labuladong.online/zh/algo/essential-technique/sliding-window-framework-2/
folder: 手把手刷数组算法

提到的力扣题号: 3, 76, 438, 567

## 这节的小标题
- 滑动窗口框架概览
- 一、最小覆盖子串
- 二、字符串排列
- 三、找所有字母异位词
- 四、最长无重复子串

## 复杂度结论
- 如果用暴力解的话，你需要嵌套 for 循环这样穷举所有子数组，时间复杂度是 O(N2)O(N^2)O(N2)：
- 基于滑动窗口算法框架写出的代码，时间复杂度是 O(N)O(N)O(N)，比嵌套 for 循环的暴力解法效率高
- 减），所以字符串/数组中的每个元素都只会进入窗口一次，然后被移出窗口一次，不会说有某些元素多次进入和离开窗口，所以算法的时间复杂度就和字符串/数组的长度成正比
- 反观嵌套 for 循环的暴力解法，那个 j 会回退，所以某些元素会进入和离开窗口多次，所以时间复杂度就是 O(N2)O(N^2)O(N2) 了
- 我在 算法时空复杂度分析实用指南 有具体教大家如何从理论上估算时间空间复杂度，这里就不展开了

## 涉及的关键术语
- right, left, need, window, length, while, valid, HashMap, get, res, String, Map, char, put, GoJavaJavaScriptPython, size
