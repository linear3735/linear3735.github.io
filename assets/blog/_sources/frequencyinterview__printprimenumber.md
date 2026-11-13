# 如何高效寻找素数
url: https://labuladong.online/zh/algo/frequency-interview/print-prime-number/
folder: 第四章、数学运算技巧

提到的力扣题号: 204

## 这节的小标题
- 高效实现 countPrimes

## 复杂度结论
- 这样写的话时间复杂度 O(n^2)，问题很大
- 现在，isPrime 函数的时间复杂度降为 O(sqrt(N))O(sqrt(N))O(sqrt(N))，但是我们实现 countPrimes 函数其实并不需要这个函数，以上只是希望读者明白 sqrt(n) 的含义，因
- 该算法的时间复杂度比较难算，显然时间跟这两个嵌套的 for 循环有关，其操作数应该是：
- 最终结果是 O(N∗loglogN)O(N * loglogN)O(N∗loglogN)，有兴趣的读者可以查一下该算法的时间复杂度证明

## 涉及的关键术语
- sqrt, isPrime, countPrimes, boolean, GoJavaJavaScriptPython, loglogN, Solution, Arrays, fill, Count, Primes204, count, nnn, Wikipedia, GIF, comments
