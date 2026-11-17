import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

# 仓库根由脚本自身位置推导:这个文件在 assets/blog/<slug>-<date>/ 下,
# 上溯三层就是仓库根。写死绝对路径的话,换台机器或换个目录就全失效。
ROOT = Path(__file__).resolve().parent.parent.parent.parent
GATE = "assets/blog/fa3-cutlass-mainloop-20261115/fa3_facts.py"
PY = "/opt/miniconda3/bin/python3"

CASES = [
    ("改掉一条引文的数字 (850 -> 999)",
     "assets/blog/fa3-cutlass-mainloop-20261115/fa3_facts.py",
     "BF16 Benchmark: reach up to 850 TFLOPS", "BF16 Benchmark: reach up to 999 TFLOPS"),
    ("删掉一张基准图页的标题 (p24)",
     "assets/blog/fa3-cutlass-mainloop-20261115/data/slides-text.txt",
     "BF16 Decode Benchmark for MQA. Lower is better!", "removed"),
    ("把 p20 的 block_m 从 128 改成 64 (tile 数应翻倍)",
     "assets/blog/fa3-cutlass-mainloop-20261115/fa3_facts.py",
     "seqlen, heads, batch, block_m = 4096, 8, 4, 128",
     "seqlen, heads, batch, block_m = 4096, 8, 4, 64"),
    ("改一个字的 SHA-256 记录",
     "assets/blog/fa3-cutlass-mainloop-20261115/fa3_facts.py",
     '"softmax.h":\n        "4eef1079', '"softmax.h":\n        "0eef1079'),
    ("把上游源文件改一个字节",
     "assets/blog/fa3-cutlass-mainloop-20261115/upstream/named_barrier.hpp", "", ""),
]

def run_gate():
    p = subprocess.run([PY, GATE], cwd=ROOT, capture_output=True, text=True)
    first = [l for l in p.stdout.splitlines() if "FAIL" in l]
    return p.returncode, (first[0].strip() if first else "")

backup = Path(tempfile.mkdtemp())
reds = 0
try:
    for name, rel, old, new in CASES:
        tgt = ROOT / rel
        saved = backup / rel.replace("/", "__")
        shutil.copy2(tgt, saved)
        try:
            if rel.endswith("named_barrier.hpp"):
                b = tgt.read_bytes()
                tgt.write_bytes(b[:-1] + bytes([(b[-1] + 1) % 256]))
            else:
                s = tgt.read_text(encoding="utf-8")
                assert old in s, f"找不到要改的串: {old[:40]}"
                tgt.write_text(s.replace(old, new, 1), encoding="utf-8")
            code, fail = run_gate()
            verdict = "RED  " if code != 0 else "GREEN"
            if code != 0: reds += 1
            print(f"  {verdict} exit={code}  {name}")
            if fail: print(f"          {fail[:110]}")
        finally:
            shutil.copy2(saved, tgt)
    code, _ = run_gate()
    print(f"\n还原后 gate exit={code}  ({'OK' if code==0 else '还原不干净!'})")
finally:
    shutil.rmtree(backup)

print(f"\n{reds}/{len(CASES)} 个负对照变红")
sys.exit(0 if reds == len(CASES) and code == 0 else 1)
