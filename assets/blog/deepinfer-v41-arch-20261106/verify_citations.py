#!/usr/bin/env python3
"""Verify every documented claim in the DeepInfer V4.1 Flash architecture post.

Two independent checks:
  A) Q&A quotes  — each cited line of doc/inference_deployment_qa.md must contain
                   the quoted substring.
  B) Code refs   — each cited (path, line) must contain the expected symbol.

Also cross-checks that each cited line number actually appears in the post text.

Usage:
    python3 verify_citations.py [post.md]

Env:
    DEEPINFER   path to the DeepInfer checkout (default: ~/learn-deepinfer/DeepInfer)

Exit: 0 all pass, 1 any fail, 2 tree/post missing.
"""
import os
import re
import sys
from pathlib import Path

DI = Path(os.environ.get("DEEPINFER", "~/learn-deepinfer/DeepInfer")).expanduser()
POST = Path(sys.argv[1] if len(sys.argv) > 1 else "deepinfer-v41-arch-post.md")
QA = "doc/inference_deployment_qa.md"

# --- A) Q&A line quotes: (label, line, required substring) ---
QA_CLAIMS = [
    ("retention goal",   13,  "Retain KV cache for more than 72 hours"),
    ("daily tokens",     17,  "155 trillion tokens per day"),
    ("revenue",          17,  "US$38 per GPU-hour"),
    ("recipe aligned",   19,  "fully aligned with the official DeepSeek API"),
    ("not open sourced", 21,  "not yet fully open-sourced"),
    ("zhihu ref",        21,  "zhuanlan.zhihu.com"),
    ("TTFT/TBT",         31,  "TTFT and TBT can be controlled and optimized independently"),
    ("four balancers",   33,  "Prefill Load Balancer, Decode Load Balancer"),
    ("deploy shape",     43,  "disaggregated E/P/D architecture plus dedicated storage nodes"),
    ("prefill par",      47,  "Prefill: EP2\u20138 / DP2\u20138"),
    ("prefill rule",     47,  "smallest EP/DP that HBM allows"),
    ("decode par",       49,  "Decode: EP64\u2013128 / DP64\u2013128"),
    ("decode rule",      49,  "largest EP/DP that the available GPUs allow"),
    ("no tp/cp",         53,  "TP and CP are not used"),
    ("wide-ep mech",     57,  "reduces per-step memory traffic"),
    ("wide-ep cond",     57,  "with good EPLB support"),
    ("smallest unit",    67,  "64 GPUs of prefill plus 64 GPUs of decode"),
    ("cross-dc",         73,  "severed by construction work"),
    ("cross-dc bw",      73,  "400 Gbps of interconnect bandwidth per 8 GPUs"),
    ("storage srv",      77,  "20 \u00d7 30.73 TB SSDs"),
    ("per gpu",          81,  "about 14.4 TB per GPU"),
    ("3fs ec",           87,  "10+2 erasure coding"),
    ("3fs read",         89,  "any 10 responses are enough"),
    ("gc worker",        91,  "GC Worker"),
    ("eplb prefill",     99,  "4 redundant experts per GPU"),
    ("eplb prefill win", 99,  "100-step statistics window"),
    ("eplb prefill int", 99,  "re-assignment every 1,000 steps"),
    ("eplb prefill lb",  99,  "1.074 (EP4DP4) / 1.045 (EP2DP2)"),
    ("eplb decode",     103,  "1 redundant expert per GPU"),
    ("eplb decode int", 103,  "re-assignment every 10,000 steps"),
    ("eplb decode lb",  103,  "moe_lb` = 1.090"),
    ("no prefix aff",   111,  "there is no prefix-affinity routing"),
    ("4 tiers",         109,  "<16K / 16\u201364K / 64\u2013256K / \u2265256K"),
    ("quota limit",     115,  "compute_quota_limit"),
    ("quadratic",       115,  "fitted quadratic cost model"),
    ("token budget",    115,  "32,768-token budget"),
    ("allreduce min",   115,  "reduced by an all-reduce MIN within the DP group"),
    ("decode lb dual",  119,  "request count"),
    ("decode lb rev",   119,  "short requests to GPUs with low concurrency but large total KV cache length"),
    ("lb level",        127,  "80% of a perfectly balanced offline benchmark"),
    ("paged 3fs",       135,  "Paged block KV cache"),
    ("no app repl",     135,  "No application-level replication"),
    ("no local mem",    141,  "not in local host memory"),
    ("any prefix",      141,  "every prefill machine hit any prefix"),
    ("fail rate",       141,  "more than an order of magnitude higher than storage nodes"),
    ("prefill paged",   145,  "the prefill side also uses a paged KV cache"),
    ("decode no off",   149,  "Decode is not bound by cache capacity"),
    ("ttl",             153,  "3 days for agent traffic and 7 days for chatbot traffic"),
    ("100 pib",         153,  "roughly 100 PiB of SSD storage"),
    ("long tail",       153,  "much heavier long tail of hits"),
    ("ttl cost",        153,  "0.5%\u20131% of KV cache hit rate"),
    ("matching",        157,  "hash-chain prefix match over metadata only"),
    ("cannot hide",     157,  "it cannot be hidden"),
    ("fetching",        157,  "moving the KV cache from 3FS into host shared memory"),
    ("gdr reason",      157,  "CUDA copy engine performs poorly"),
    ("gdr impl",        157,  "swap-in is implemented with GDR"),
    ("gdr sm",          157,  "without consuming SMs"),
    ("swa format",      163,  "stored region: SWA"),
    ("swa 20 layers",   163,  "the stored layers are the first 20"),
    ("swa 128",         165,  "multiples of 128 tokens"),
    ("swa last chunk",  165,  "only the last chunk stores"),
    ("swa overshoot",   165,  "at most 5 tokens"),
    ("swa ring",        165,  "6 extra positions"),
    ("swa size",        169,  "1,415,040 B per sequence"),
    ("swa mxfp8",       169,  "528 B/token is the MXFP8 SWA KV format"),
    ("swa dir",         169,  "physically partitioned by key across the Entrypoint machines"),
    ("swa p2d",         173,  "share the same P-to-D transfer path"),
    ("swa cross",       177,  "400G VLAN pull-back"),
    ("bounded replay",  183,  "recomputes only the most recent 128 tokens"),
    ("replay const",    183,  "reduced to a constant"),
    ("dec replay",      187,  "last 2,560 tokens"),
    ("half prefill",    187,  "nearly halving total prefill computation"),
    ("hit cap",         191,  "at most L \u2212 134"),
    ("ce grace",        199,  "grace period (1 min)"),
    ("scale-in",        203,  "scale-in is forbidden whenever quota utilization is above 0.8"),
    ("ep failover",     211,  "re-determines the EP size from all currently healthy GPUs"),
    ("fp4 main kv",     217,  "per-16, e4m3"),
    ("fp4 indexer",     219,  "per-32, ue8m0, MXFP4"),
    ("mega moe",        231,  "Mega MoE is significantly faster than unfused MoE"),
    ("flashmla",        235,  "5%\u201310% slower"),
    ("e2e close",       237,  "at most 5% apart"),
    ("dspark idea",     243,  "DSpark uses variable-length verification"),
    ("dspark waste",    243,  "fixed-length verification wastes verification compute"),
    ("confidence head", 243,  "Confidence Head"),
    ("dspark prefix",   243,  "prefix subset that maximizes effective throughput"),
    ("dspark result",   247,  "about 30% (5.00 \u2192 3.2\u20134.4)"),
    ("dspark accept",   247,  "3.29 vs. 3.20"),
    ("dspark gain",     247,  "+4\u20137% throughput"),
    ("dspark conc",     247,  "~60 concurrent sequences per rank"),
    ("dspark est",      249,  "estimated throughput"),
    # table rows 249-256
    ("tbl hdr",         249,  "dynamic vs. fixed-5 gain"),
    ("tbl 16",          251,  "\u22121.5%"),
    ("tbl 32",          252,  "+1.6%"),
    ("tbl 48",          253,  "+3.6%"),
    ("tbl 60",          254,  "+5.4%"),
    ("tbl 72",          255,  "+6.7%"),
    ("tbl 96",          256,  "+11.0%"),
    ("dspark async",    264,  "confidence from step N has not been returned yet"),
    ("dspark kernel",   264,  "recomputed on the GPU by a TileLang kernel"),
    ("dspark pinned",   264,  "written back to a pinned buffer"),
    ("async problem",   270,  "the GPU sits idle during"),
    ("async pipeline",  274,  "the CPU concurrently runs"),
    ("async prior art", 274,  "SGLang, NanoFlow"),
    ("so def",          280,  "JSON schema, regular expression, EBNF"),
    ("so decoupled",    284,  "Compilation and inference are decoupled"),
    ("so automaton",    286,  "compiled into a grammar automaton"),
    ("so mask",         288,  "a mask is generated and applied to the sampling logic"),
    ("recipe protos",   294,  "Chat Completions API, the Responses API, and the Messages API"),
    ("recipe rust",     296,  "implemented in Rust"),
    ("inject",          300,  "preventing text from injecting control tokens"),
    ("out parse",       302,  "does not gain the ability to trigger end-of-reasoning"),
    ("segmented",       304,  "encode the segments in parallel"),
    ("stream utf8",     310,  "incomplete UTF-8 character"),
    ("stream kmp",      310,  "incremental KMP matching"),
    ("stream progress", 310,  "the match progress is retained"),
]

# --- A2) README claims: (label, line, required substring) ---
README_CLAIMS = [
    ("readme cp claim",    12, "Attention DP / balanced CP, MoE EP + EPLB"),
    ("readme dspark on",   24, "Set `DEEPINFER_ENABLE_MTP_VARLEN=1`"),
    ("readme draft len",   24, "maximum draft length (default: 5)"),
    ("readme not incl",    38, "not included in this release"),
    ("readme no kv",       40, "A KV cache system"),
    ("readme no disag",    41, "VE/Prefill/Decode disaggregation"),
    ("readme most impl",   41, "most required engine functionality is already implemented"),
    ("readme no lb",       42, "Load balancing across data-parallel replicas"),
    ("readme no gdr",      42, "for both prefill and decode"),
    ("readme tests",       35, "Ascend") if False else ("readme npu", 36, "Huawei Ascend 950 NPUs"),
]

# --- B) Code refs: (label, relpath, line, required substring) ---
CODE_CLAIMS = [
    ("platform enum",   "deepinfer/platform.py", 14, "class PlatformEnum"),
    ("platform gpu npu","deepinfer/platform.py", 15, "GPU = enum.auto()"),
    ("platform npu en", "deepinfer/platform.py", 16, "NPU = enum.auto()"),
    ("platform backend","deepinfer/platform.py", 22, "tilelang_ops_backend"),
    ("gpu backend",     "deepinfer/platform.py", 57, 'tilelang_ops_backend = "cuda"'),
    ("gpu dist",        "deepinfer/platform.py", 58, 'distributed_backend = "nccl"'),
    ("gpu pin",         "deepinfer/platform.py", 68, "cudaHostRegister"),
    ("npu cls",         "deepinfer/platform.py", 86, "class PlatformNPU"),
    ("npu backend",     "deepinfer/platform.py", 88, 'tilelang_ops_backend = "asc"'),
    ("npu dist",        "deepinfer/platform.py", 89, 'distributed_backend = "hccl"'),
    ("npu ascend env",  "deepinfer/platform.py", 93, "ASCEND_RT_VISIBLE_DEVICES"),
    ("npu sf type",     "deepinfer/platform.py", 138, "self.fp8_sf_type = torch.int16"),
    ("platform select", "deepinfer/platform.py", 226, 'PlatformNPU if accelerator_kind() == "ascend"'),
    ("markov head",     "deepinfer/model_executor/models/v4_modules/heads.py", 26, "class MarkovGPTHead"),
    ("markov doc",      "deepinfer/model_executor/models/v4_modules/heads.py", 27, "first-order Markov correction"),
    ("markov rank",     "deepinfer/model_executor/models/v4_modules/heads.py", 31, "dspark_markov_rank"),
    ("accept predictor","deepinfer/model_executor/models/v4_modules/heads.py", 37, "class AcceptRatePredictor"),
    ("accept doc",      "deepinfer/model_executor/models/v4_modules/heads.py", 38, "acceptance-rate prediction head"),
    ("conf head use",   "deepinfer/model_executor/models/v4_modules/heads.py", 105, "self.confidence_head = AcceptRatePredictor"),
    ("dspark block",    "deepinfer/model_executor/models/v4_modules/heads.py", 86, "dspark_block_size"),
    ("eplb rebalance",  "deepinfer/model_executor/eplb/policy.py", 73, "def rebalance_experts_global"),
    ("eplb greedy",     "deepinfer/model_executor/eplb/policy.py", 12, "def _batch_greedy_indices"),
    ("eplb shuffle",    "deepinfer/model_executor/eplb/shuffle.py", 65, "def expert_model_parallel_shuffle_inplace"),
    ("eplb intranode",  "deepinfer/model_executor/eplb/shuffle.py", 150, "def expert_model_parallel_shuffle_inplace_intranode"),
    ("so compiler",     "deepinfer/structure_output/compiler.py", 14, "class XGrammarCompiler"),
    ("so matcher",      "deepinfer/structure_output/matcher.py", 58, "class XGrammarMatcher"),
    ("so future",       "deepinfer/structure_output/matcher.py", 261, "class XGrammarMatcherFuture"),
    ("so kmp",          "deepinfer/structure_output/matcher.py", 24, "def _kmp_failure"),
    ("so mask",         "deepinfer/structure_output/mask.py", 10, "def allocate_vocab_mask"),
    ("so utils",        "deepinfer/structure_output/mask.py", 23, "class XGrammarUtils"),
    ("so builder",      "deepinfer/structure_output/so_matcher_builder.py", 19, "class SOMatcherBuilder"),
    ("tl ops import",   "deepinfer/model_executor/layers/tilelang_ops/random_sampling.py", 7, "from deepinfer import PLATFORM"),
    # -- added after the independent verification pass --
    ("env int sig",     "deepinfer/environ.py", 62, "def int(*, default: int = 0)"),
    ("env extra exp",   "deepinfer/environ.py", 114, "DEEPINFER_OVERRIDE_NUM_EXTRA_EXPERTS = EnvVar.int()"),
    ("env window",      "deepinfer/environ.py", 115, "DEEPINFER_EXPERT_COUNT_WINDOW_SIZE = EnvVar.int(default=100)"),
    ("env interval",    "deepinfer/environ.py", 116, "DEEPINFER_EXPERT_REARRANGEMENT_STEP_INTERVAL = EnvVar.int()"),
    ("eplb early ret",  "deepinfer/model_executor/eplb/__init__.py", 147, "if self._rearrangement_interval == 0:"),
    ("eplb return",     "deepinfer/model_executor/eplb/__init__.py", 148, "return"),
    ("eplb cls",        "deepinfer/model_executor/eplb/__init__.py", 42, "class ExpertLoadBalancer"),
    ("conf head cls",   "deepinfer/model_executor/models/mtp/dflash.py", 46, "class ConfidenceHead(nn.Module)"),
    ("conf head doc",   "deepinfer/model_executor/models/mtp/dflash.py", 47, "Predict the acceptance probability of each draft token"),
    ("conf temp",       "deepinfer/model_executor/models/mtp/dflash.py", 62, "DEEPINFER_DFLASH_CONFIDENCE_HEAD_TEMPERATURE"),
    ("accept proj",     "deepinfer/model_executor/models/v4_modules/heads.py", 42, "ReplicatedLinear(input_dim, 1, bias=False"),
    ("accept cls",      "deepinfer/model_executor/models/v4_modules/heads.py", 40, "def __init__(self, input_dim: int)"),
    ("kvstore fn",      "deepinfer/worker/cache_engine.py", 101, "def get_kvstore_swa_block_size"),
    ("kvstore doc",     "deepinfer/worker/cache_engine.py", 102, "kvstore \u89c6\u89d2\u7684 swa_block_size"),
    ("sched vote",      "csrc/engine/scheduler.hpp", 316, "c10d::ReduceOp::MIN"),
    ("sched vote cmt",  "csrc/engine/scheduler.hpp", 316, "ANY"),
    ("sched want",      "csrc/engine/scheduler.hpp", 313, "_has_prefill_waiting()"),
    ("sched tokbound",  "csrc/engine/scheduler.hpp", 470, "max_num_batched_tokens - num_batched_tokens"),
    ("sched cp_align",  "csrc/engine/scheduler.hpp", 470, "cp_align"),
    ("flops cmt",       "csrc/engine/flops_estimator.hpp", 22, "FP8-equivalent FLOPs"),
    ("ops dispatch",    "deepinfer/model_executor/layers/tilelang_ops/ops.py", 15, "PLATFORM.tilelang_ops_backend"),
    ("cp ranks",        "deepinfer/model_executor/parallel_utils/parallel_state.py", 97, "cp_ranks = rearrange"),
    ("eplb test",       "tests/models/test_eplb_policy.py", 1, "rebalance_experts_global"),
    ("shuffle test",    "tests/distributed/test_expert_shuffle.py", 1, 'import os'),
    ("zos pinned",      "csrc/engine/zos.cpp", 239, "pinned(torch::kInt32)"),
    ("mtp varlen cls",  "csrc/engine/mtp_varlen.hpp", 133, "class MTPVarlen"),
    ("sched mtpvarlen", "deepinfer/model_executor/layers/tilelang_ops/schedule_mtp_varlen.py", 11,
     "def compute_seqlens_q_by_confidence_rates"),
    ("cumprod",         "deepinfer/model_executor/layers/tilelang_ops/schedule_mtp_varlen.py", 68, "torch.cumprod(gathered_rates"),
]


def check(claims, root, kind):
    ok = bad = 0
    fails = []
    for item in claims:
        if kind == "QA":
            label, lineno, needle = item
            rel = QA
        elif kind == "README":
            label, lineno, needle = item
            rel = "README.md"
        else:
            label, rel, lineno, needle = item
        p = root / rel
        if not p.is_file():
            fails.append((label, rel, lineno, "FILE MISSING"))
            bad += 1
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if lineno > len(lines):
            fails.append((label, rel, lineno, f"ONLY {len(lines)} LINES"))
            bad += 1
            continue
        actual = lines[lineno - 1]
        if needle not in actual:
            fails.append((label, rel, lineno, f"GOT: {actual.strip()[:120]}"))
            bad += 1
            continue
        ok += 1
    return ok, bad, fails


def main() -> int:
    if not DI.is_dir():
        print(f"ERROR: DeepInfer tree not found at {DI}")
        return 2
    if not POST.is_file():
        print(f"ERROR: post not found at {POST}")
        return 2

    post = POST.read_text(encoding="utf-8")
    total_bad = 0

    print(f"tree : {DI}")
    print(f"post : {POST}  ({len(post):,} chars)")
    print()

    ok_a, bad_a, fails_a = check(QA_CLAIMS, DI, "QA")
    print(f"[A] Q&A doc quotes   : {ok_a}/{len(QA_CLAIMS)} verified, {bad_a} failed")
    ok_b, bad_b, fails_b = check(CODE_CLAIMS, DI, "CODE")
    print(f"[B] code references  : {ok_b}/{len(CODE_CLAIMS)} verified, {bad_b} failed")
    ok_c, bad_c, fails_c = check(README_CLAIMS, DI, "README")
    print(f"[C] README claims    : {ok_c}/{len(README_CLAIMS)} verified, {bad_c} failed")
    total_bad = bad_a + bad_b + bad_c

    for label, rel, lineno, why in fails_a + fails_b + fails_c:
        print(f"\nFAIL [{label}] {rel}:{lineno}\n      {why}")

    # [C] every NNN line number cited for the Q&A should exist in the doc
    cited = set()
    for m in re.finditer(r"`:(\d{1,3})(?:-(\d{1,3}))?`", post):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        cited.update(range(a, b + 1))
    qa_lines = len((DI / QA).read_text(encoding="utf-8").splitlines())
    oob = sorted(n for n in cited if n > qa_lines)
    print(f"\n[D] Q&A line refs in post: {len(cited)} distinct, "
          f"{'all within 1..' + str(qa_lines) if not oob else 'OUT OF RANGE: ' + str(oob)}")
    total_bad += len(oob)

    print()
    if total_bad:
        print(f"RESULT: {total_bad} problem(s)")
        return 1
    print("ALL CITATIONS VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
