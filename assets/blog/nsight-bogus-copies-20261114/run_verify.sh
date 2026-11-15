#!/bin/bash
# 复跑一遍核心实验,目的是**检查可复现性**而不是产生新结论。
# 正文里的数字全部来自第一次运行(作业 434338);这个脚本只在
# 第二次运行和第一次明显不一致时才有意义 —— 那样说明某条结论
# 是噪声,不该写进文章。

cd "$HOME/nsight_bench"
. /etc/profile.d/modules.sh
module load cuda/12.6

echo "##### 复现性检查(第二次运行)#####"
echo "node: $(hostname)  date: $(date -Is)"

echo
echo "=== bench_bogus 五种模式 ==="
for m in good sync alloc errsync all; do
  ./bench_bogus 200 1048576 $m
  echo "  ^ mode=$m"
done

echo
echo "=== nsys 时间线(重新采) ==="
for m in good sync errsync; do
  nsys profile -o v2_$m -f true --trace=cuda --stats=false \
       ./bench_bogus 50 262144 $m >/dev/null 2>&1
  nsys stats --report cuda_gpu_trace --format csv --force-export=true \
       v2_$m.nsys-rep 2>/dev/null | sed -n '/^Start (ns),/,$p' > vtrace_$m.csv
  echo "  $m: $(wc -l < vtrace_$m.csv) 行"
done

echo
echo "=== kernels.cu ==="
./kernels 50

echo
echo "=== cpu_side.cu ==="
timeout 400 stdbuf -oL ./cpu_side 200 8 1

echo
echo "##### done #####"
