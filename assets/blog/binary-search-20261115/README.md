# 二分搜索 — 素材与校验

这个目录放这篇文章的校验脚本、C++ harness 和插图生成脚本。

- 文章: [`_posts/2026-11-15-binary-search.md`](../../../_posts/2026-11-15-binary-search.md)
- 图片: `assets/img/binary-search-20261115/`（4 张 SVG，`make_figures.py` 手写生成，非截图）

## 怎么复跑

```bash
cd <repo>

# 结构门:front matter 顺序、代码围栏配对与语言标注、目录锚点可达、图片存在且是真 SVG
python3 assets/blog/_tools/verify_post.py _posts/2026-11-15-binary-search.md

# 插图门:XML 可解析、<svg> 有 viewBox、<text> 非空、不设 font-family、文字不重叠
python3 assets/blog/_tools/verify_svg.py assets/img/binary-search-20261115/*.svg

# 代码门:把文章里的代码块抽出来真跑，Python 3 与 C++17 两版
python3 assets/blog/binary-search-20261115/verify_code.py
```

三个脚本退出码 0 表示全部通过。

重画插图（需要 `sips`，只在 macOS 上用来目视检查，不影响门禁）:

```bash
python3 assets/blog/binary-search-20261115/make_figures.py
```

## verify_code.py 的设计

**它不存任何代码副本，每次运行都从文章正文里重新抽。** 抽法是

```python
re.findall(r"```" + lang + r"\n(.*?)```", post_text, re.S)
```

然后

- 每个 ```` ```python ```` 块 `exec` 进同一个命名空间，再拿文章里定义的函数去跑断言；
- 所有 ```` ```cpp ```` 块按顺序拼在 `cpp_solutions_test.cpp` 前面，末尾接
  `int main() { return run_all_tests(); }`，用 `g++ -std=c++17 -Wall -Wextra -O1` 编译。
  编译产物跑完退出码必须是 0，stdout/stderr 里不允许出现任何诊断。
- 最后核对围栏账目:`len(opens) == len(py)+len(cpp)+len(text)`，且
  `sorted(set(opens)) == ["cpp", "python", "text"]`。文章改了代码却忘了改这里，块数就会对不上。

所以文章和门禁不可能各自漂移：**改文章就是改被测代码**。

### 对拍对象（每段都用独立参照实现逐用例比对，不只跑给定样例）

| 文章小节 | 参照实现 | 规模与边界 |
| --- | --- | --- |
| §2–§3 六种边界函数 | `bisect.bisect_left` / `bisect_right` | `n = 0..20` 各 40 组随机数组 × `target = -8..8`，共 **14,280** 组；顺带核对 `left_bound` 与 `right_bound` 的关系 |
| §2.4 两个手算例子 | 手算答案 | 原文举的那两组数组与目标 |
| §3.2 目标不存在时的性质 | 断言 `left_bound == right_bound + 1` | 3000 组随机数组，含空数组 |
| §4 二分答案三题 | 暴力枚举可行解（`ref_koko` 等） | 各 300 组随机用例，含 `h == len(piles)` 的下界贴边 |
| §4.4 1011 与 410 同构 | 共用同一个判定函数交叉验证 | — |
| §5.1 峰值元素 | `is_peak` 独立校验返回值 | 3000 组随机数组（保证相邻不等），含单元素、单调升/降 |
| §6 带权随机选择 | 40 万次抽样 vs 权重占比；权重为 0 的元素必须永不命中 | 含 `w = [1,3,0,2,4,0,6]` |
| §6.3 `bisect_left` 的坑 | 穷举单位区间，断言 `bisect_left` 版本确实会取到 `-1`、`bisect_right` 版本不会 | 全值域穷举 |

C++ 侧走同一套用例：把文章里所有 ```` ```cpp ```` 块拼上 `cpp_solutions_test.cpp`，加上
`int main()`，用 `g++ -std=c++17 -Wall -Wextra -O1` 编译（要求 0 warning），跑完退出码必须是 0。

Python 版和 C++ 版的题目数与代码块数必须相等——文章少写一版，门禁立刻失败。

## 材料出处

材料来自 labuladong 的算法教程站点，逐篇链接在文章第 0 节。原文用 Java，本文全部代码用
Python 3 和 C++17 重写，原文代码与可视化面板没有复制。
