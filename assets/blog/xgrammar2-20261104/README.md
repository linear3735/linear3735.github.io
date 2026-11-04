# XGrammar-2 精读:引用核验脚本

这篇笔记(《XGrammar-2 精读:五个机制,两份生产代码,和一处把 bit 极性写反的内核》)里的每一个 `文件:行号`
都是从真实源码树里逐行核对过的。这个目录放的就是做核验用的脚本,你可以自己复现。

## 需要准备的三份源码

| 环境变量 | 指向 | 说明 |
|---|---|---|
| `VLLM_TREE` | vLLM actual-0909 源码树 | 仓库根目录直接就是 `vllm/` 包的内容,所以路径形如 `v1/structured_output/backend_xgrammar.py` |
| `DEEPINFER_TREE` | DeepInfer 仓库根 | 修订 `774ce244b87cc0eb8d4b94ab9f5de2ab22049f01`(2026-10-20),`deepinfer/` 包在仓库根下 |
| `XGRAMMAR_WHEEL` | 已安装的 xgrammar 0.2.3 包目录 | 里面要有 `matcher.py`;只用它核验 `_FULL_MASK` 的定义与位宽 |

## 两个脚本

```bash
export XGRAMMAR2_POST=xgrammar2-post.md
export VLLM_TREE=/path/to/actual-0909-source/vllm
export DEEPINFER_TREE=/path/to/DeepInfer
export XGRAMMAR_WHEEL=/path/to/site-packages/xgrammar

# 1) 内容核验:53 条断言,每一条都要求「那一行确实包含那段文本」
python3 verify_citations.py

# 2) 引用可解析性:文中 40 处 `文件:行号` 都能落到真实文件、且行号存在
python3 audit_refs.py
```

两个脚本都是**只读**的,不会改动任何源码。退出码 0 表示全部通过。

`verify_citations.py` 是逐行断言而不是模糊匹配:把任意一条的行号改错一位,它会失败并打印出
期望的子串和那一行实际的内容。核验 `audit_refs.py` 时也做了同样的反例测试。

## 关于第 7 节那个结论

第 7 节指出 DeepInfer 的 TileLang CUDA 掩码内核把 `bit=1` 的含义写反了。**这是源码文本层面的
结论,不是实测结论** —— 这两个脚本能证明的是"源码里确实这么写",不能证明"跑起来真的错了"。

要判定它,只需要一次运行:在 `774ce24` 上跑 `test_apply_token_bitmask_by_step_inplace`
(`deepinfer/model_executor/layers/tilelang_ops/structure_output.py:81`),在 CUDA 后端上看它是红是绿。
注意该测试用随机 int32 填满 bitmask(`:89`),所以它不是"可能碰巧通过",而是只要极性不一致就必然失败。
