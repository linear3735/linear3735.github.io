# 并发写入规则(多个 writer 同时工作)

这一系列会由多个 writer 并行产出。共享文件冲突过一次就会浪费很多时间，
所以规则写死在这里。

## 每个人独占的路径(随便写)

```
_posts/<你的 slug>.md
assets/img/<你的 slug>-<日期>/          整目录
assets/blog/<你的 slug>-<日期>/         整目录
```

**不要碰别人的这几样。** 尤其不要在别人的 `_posts/*.md` 上跑格式化命令。

## 共享文件(只做追加，且要先读后写)

| 文件 | 规则 |
|---|---|
| `_data/roadmap.json` | 只改**你自己那几条**的 `status` 和 `post`。改之前重读文件；如果 revision 变了就重新基于新内容改 |
| `assets/css/site.css` | **不要改。** 需要新样式就写到 `assets/blog/<你的目录>/post.css`，由 Lead 统一合并 |

`site.css` 是所有页面共用的，一次并发追加就可能把别人的样式截断。所以
writer 一律不动它。

## 判断"我这篇要写什么"

看 `_data/roadmap.json` 里分给你的条目。条目的 `title` 和 `desc` 是选题说明，
不是必须照抄的标题——你可以起更好的名字，但**覆盖范围要对得上**。

## 提交

**不要 `git add` / `git commit` / `git push`。**
所有改动攒在工作区，最后由 Lead 汇总、展示 diff、等用户同意。

## 工作区里已有的外来改动(绝对不要动)

工作区里有**其他会话**正在进行的改动，不属于本任务:

- `_posts/2026-10-23-llm-quantization-five-lineages.md`(已修改)
- `_posts/2026-11-07-recsys-deepfm-onerec.md`(未跟踪)
- `assets/blog/recsys-20261107/`(未跟踪)

这些**不要读进来改、不要格式化、不要 stage**。
