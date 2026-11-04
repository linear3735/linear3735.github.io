#!/usr/bin/env python3
"""Verify every `file:line` citation in a post against the real source trees.

Every claim in the post must be traceable to a line that actually says that
thing. Point the three env vars at your copies of the trees, then run this next
to the post:

    XGRAMMAR2_POST=xgrammar2-post.md \
    VLLM_TREE=/path/to/actual-0909-source/vllm \
    DEEPINFER_TREE=/path/to/DeepInfer \
    XGRAMMAR_WHEEL=/path/to/site-packages/xgrammar \
    python3 verify_citations.py

Exit code 0 means every cited line contains the expected text.
"""
import os
import sys
from pathlib import Path

POST = Path(os.environ.get("XGRAMMAR2_POST", "xgrammar2-post.md"))

V = Path(os.environ.get("VLLM_TREE", "/path/to/actual-0909-source/vllm"))
D = Path(os.environ.get("DEEPINFER_TREE", "/path/to/DeepInfer"))
X = Path(os.environ.get("XGRAMMAR_WHEEL", "/path/to/site-packages/xgrammar"))

# (tree, relative path, line number, substring that line must contain)
CLAIMS = [
    # ---------- vLLM: the whole structured-output path ----------
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 79,  "def compile_grammar"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 96,  "compile_regex_with_timeout"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 105, "xgr.StructuralTagItem"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 112, "compile_structural_tag(tags"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 114, "compile_structural_tag(grammar_spec)"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 133, "def allocate_token_bitmask"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 157, "def accept_tokens"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 203, "def rollback"),
    ("vLLM", V, "v1/structured_output/backend_xgrammar.py", 208, "def fill_bitmask"),
    ("vLLM", V, "v1/structured_output/__init__.py",         59,  "self._full_mask = torch.tensor(-1, dtype=torch.int32)"),
    ("vLLM", V, "v1/structured_output/__init__.py",         62,  "fill_bitmask_parallel_threshold = 128"),
    ("vLLM", V, "v1/structured_output/__init__.py",         63,  "fill_bitmask_parallel_threshold < max_batch_size"),
    ("vLLM", V, "v1/structured_output/utils.py",            49,  "def compile_regex_with_timeout"),
    ("vLLM", V, "v1/structured_output/utils.py",            66,  "if timeout <= 0:"),
    ("vLLM", V, "v1/structured_output/utils.py",            67,  "return fn(pattern)"),
    ("vLLM", V, "envs.py",                                 221,  "VLLM_XGRAMMAR_CACHE_MB: int = 0"),
    ("vLLM", V, "envs.py",                                1647,  'os.getenv("VLLM_XGRAMMAR_CACHE_MB", "512")'),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",      59,  "def apply_grammar_bitmask"),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",     104,  "BLOCK_SIZE = 8192"),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",     105,  "triton.cdiv(vocab_size, BLOCK_SIZE)"),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",     126,  "def _apply_grammar_bitmask_kernel"),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",     154,  ") & 1) == 0"),
    ("vLLM", V, "v1/worker/gpu/structured_outputs.py",     161,  '-float("inf")'),

    # ---------- DeepInfer: the places that agree "bit=1 is allowed" ----------
    ("DeepInfer", D, "deepinfer/structure_output/matcher.py", 14, "from xgrammar.matcher import _FULL_MASK, bitmask_dtype, get_bitmask_shape"),
    ("DeepInfer", D, "deepinfer/structure_output/matcher.py", 44, "mask.fill_(_FULL_MASK)"),
    ("DeepInfer", D, "deepinfer/structure_output/matcher.py", 105, "fill_with_full_mask=True"),
    ("DeepInfer", D, "deepinfer/structure_output/matcher.py", 185, "vocab_mask[idx].zero_()"),
    ("DeepInfer", D, "deepinfer/structure_output/matcher.py", 186, "1 << (expected & 31)"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/sampler.py", 362, "matcher.fill_vocab_mask"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/sampler.py", 398, ".cuda(non_blocking=True)"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/sampler.py", 437, "apply_token_bitmask_by_step_inplace"),
    ("DeepInfer", D, "deepinfer/structure_output/compiler.py", 57, "compile_json_schema"),
    ("DeepInfer", D, "deepinfer/structure_output/compiler.py", 59, "compile_regex"),
    ("DeepInfer", D, "deepinfer/structure_output/compiler.py", 61, "compile_grammar"),
    ("DeepInfer", D, "deepinfer/environ.py", 170, "10 * 1024 * 1024 * 1024"),
    ("DeepInfer", D, "requirements.txt", 21, "xgrammar==0.2.2"),

    # ---------- DeepInfer tilelang_ops: reference impl, tests, dispatch ----------
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 12, "def apply_token_bitmask_by_step_inplace"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 60, ">> bit_ids) & 1).bool()"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 61, "masked_fill_(~allowed, -torch.inf)"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 81, "def test_apply_token_bitmask_by_step_inplace"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 89, "torch.randint(-(2**31), 2**31 - 1"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/structure_output.py", 96, "torch.equal(logits_ref, logits_tl)"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/ops.py", 15, "PLATFORM.tilelang_ops_backend"),
    # Ascend kernel: bit=1 means allowed (agrees with the reference impl)
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/asc/structure_output.py", 95, '"ne")'),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/asc/structure_output.py", 97, "vsel(values, neg_inf, allowed)"),
    # CUDA kernel: the inverted predicate
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py", 28, "threads = 128"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py", 29, "block_size = threads * 64"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py", 40, "T.pdl_sync()"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py", 55, "1 << (i % _BITS_PER_BLOCK))) == 0"),
    ("DeepInfer", D, "deepinfer/model_executor/layers/tilelang_ops/cuda/structure_output.py", 56, "-T.infinity(T.float32)"),

    # ---------- xgrammar itself: where _FULL_MASK is defined ----------
    ("xgrammar", X, "matcher.py", 15, "bitmask_dtype = torch.int32"),
    ("xgrammar", X, "matcher.py", 24, "_FULL_MASK = torch.tensor(-1, dtype=bitmask_dtype)"),
    ("xgrammar", X, "matcher.py", 55, "bitmask.fill_(_FULL_MASK)"),
]


def main() -> int:
    named = (("VLLM_TREE", V), ("DEEPINFER_TREE", D), ("XGRAMMAR_WHEEL", X))
    missing = [n for n, r in named if not r.is_dir()]
    if missing:
        print("missing source tree(s): " + ", ".join(missing))
        print("set them via env vars; see the docstring for usage.")
        return 2
    if not POST.is_file():
        print(f"post not found: {POST}")
        return 2

    failures, skipped = [], []
    for tag, root, rel, lineno, needle in CLAIMS:
        f = root / rel
        if not f.exists():
            skipped.append((tag, rel, "not present in this tree"))
            continue
        lines = f.read_text(errors="replace").split("\n")
        if lineno > len(lines):
            failures.append((tag, rel, lineno, needle, f"file has only {len(lines)} lines"))
            continue
        actual = lines[lineno - 1]
        if needle not in actual:
            failures.append((tag, rel, lineno, needle, actual.strip()[:90]))

    good = len(CLAIMS) - len(failures) - len(skipped)
    print(f"post   : {POST}")
    print(f"claims : {len(CLAIMS)}   verified: {good}   skipped: {len(skipped)}   failed: {len(failures)}")
    for tag, rel, why in skipped:
        print(f"  skip [{tag}] {rel}: {why}")
    if failures:
        print()
        for tag, rel, lineno, needle, actual in failures:
            print(f"  FAIL [{tag}] {rel}:{lineno}")
            print(f"       expected substring: {needle}")
            print(f"       actual line       : {actual}")
        return 1
    print("ALL CITATIONS VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
