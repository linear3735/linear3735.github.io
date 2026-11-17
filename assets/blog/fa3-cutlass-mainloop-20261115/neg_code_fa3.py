import shutil, subprocess, sys, tempfile
from pathlib import Path

# 仓库根由脚本自身位置推导:这个文件在 assets/blog/<slug>-<date>/ 下,
# 上溯三层就是仓库根。写死绝对路径的话,换台机器或换个目录就全失效。
REPO = Path(__file__).resolve().parent.parent.parent.parent
GATE = "assets/blog/fa3-cutlass-mainloop-20261115/verify_code.py"
POST = "_posts/2026-11-15-fa3-cutlass-mainloop.md"
PY = "/opt/miniconda3/bin/python3"

CASES = [
    ("把正文 text 里的 74.8% 改成 75.8%",
     POST, "=  74.8%", "=  75.8%"),
    ("把 python 块里的峰值 989.4e12 改成 999.4e12",
     POST, "PEAK_FP16 = 989.4e12", "PEAK_FP16 = 999.4e12"),
    ("把 text 里的 1717 行改成 1707",
     POST, "  行数                          1306      1717", "  行数                          1306      1707"),
    ("把 text 块里的 sha256 前缀改一位",
     POST, "sha256  d8f7bef97156  ->", "sha256  d8f7bef97157  ->"),
    ("删掉一个 python 块(数量与登记不符)",
     POST, "OUTPUT_MARKER 无关", "OUTPUT_MARKER 无关"),
    # 注意:变异对象必须是代码门**真的会读**的文件。第一版选了
    # named_barrier.hpp,它只被事实门(fa3_facts.py)核对,代码门不查它,
    # 所以门没红 —— 那次没红是对的,错的是我的负对照。
    ("改掉被核对的上游快照一个字节(行数/SHA-256/锚点数应全变)",
     "assets/blog/fa3-cutlass-mainloop-20261115/upstream/mainloop_fwd_sm90_tma_gmma_ws.hpp", "", ""),
]

def run():
    p = subprocess.run([PY, GATE], cwd=REPO, capture_output=True, text=True)
    first = [l for l in p.stdout.splitlines() if "FAIL" in l]
    return p.returncode, (first[0].strip() if first else "")

backup = Path(tempfile.mkdtemp())
reds = 0
try:
    for name, rel, old, new in CASES:
        tgt = REPO / rel
        saved = backup / rel.replace("/", "__")
        shutil.copy2(tgt, saved)
        try:
            if rel.endswith("mainloop_fwd_sm90_tma_gmma_ws.hpp"):
                b = tgt.read_bytes()
                tgt.write_bytes(b[:-1] + bytes([(b[-1] + 1) % 256]))
            elif name.startswith("删掉一个 python 块"):
                s = tgt.read_text(encoding="utf-8")
                i = s.index("```python")
                j = s.index("```", i + 9) + 4      # 连整块带围栏删掉
                tgt.write_text(s[:i] + s[j:], encoding="utf-8")
            else:
                s = tgt.read_text(encoding="utf-8")
                assert old in s, f"找不到要改的串: {old[:40]}"
                tgt.write_text(s.replace(old, new, 1), encoding="utf-8")
            code, fail = run()
            if code != 0: reds += 1
            print(f"  {'RED  ' if code else 'GREEN'} exit={code}  {name}")
            if fail: print(f"          {fail[:100]}")
        finally:
            shutil.copy2(saved, tgt)
    code, _ = run()
    print(f"\n还原后 gate exit={code}  ({'OK' if code==0 else '还原不干净!'})")
finally:
    shutil.rmtree(backup)

print(f"\n{reds}/{len(CASES)} 个负对照变红")
sys.exit(0 if reds == len(CASES) and code == 0 else 1)
