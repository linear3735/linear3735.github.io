#!/bin/bash
# 在 GPU 节点上跑完这一篇需要的全部实验。
. /etc/profile.d/modules.sh
module load cuda/12.6
cd "$HOME/nsight_bench"

build() {
  echo "=== build $1 ==="
  # nvcc 自己不认 -Wall/-Wextra,要转给 host 编译器就得用 -Xcompiler 包起来。
  # (写 -Wall 会直接 nvcc fatal: Unknown option '-Wall',整个 build 挂掉。)
  nvcc -O2 -arch=sm_90 -Xcompiler -Wall -Xcompiler -Wextra \
       --generate-line-info "$1" -o "${1%.cu}" 2>&1 | head -25
  [ -x "${1%.cu}" ] || { echo "BUILD FAILED: $1"; return 1; }
  echo "  ok"
}

echo "##### 1. bench_bogus:五种模式的墙钟 #####"
build bench_bogus.cu || exit 1
for m in good sync alloc errsync all; do
  ./bench_bogus 200 1048576 "$m" | grep -E "mode=|elapsed_ms"
done

echo
echo "##### 2. nsys:导出逐 kernel 时间线 #####"
for m in good sync errsync; do
  nsys profile -o "prof_$m" -f true --trace=cuda --stats=false \
      ./bench_bogus 50 262144 "$m" > "run_$m.txt" 2>&1
  nsys stats --report cuda_gpu_trace --format csv --force-export=true \
      "prof_$m.nsys-rep" > "trace_$m.csv" 2>/dev/null
  echo "  $m: elapsed=$(grep -o 'elapsed_ms=[0-9.]*' run_$m.txt | head -1)"
done

echo
echo "##### 3. kernels.cu:shared atomics / 打包传输 #####"
build kernels.cu && ./kernels 50

echo
echo "##### 4. cpu_side.cu:spinlock / 零拷贝 #####"
# stdbuf -oL:sbatch 把 stdout 重定向到文件时是**全缓冲**的,程序不退出就
# 一行都看不到 —— 上一轮就是这样误判了两次(以为卡住,其实是没 flush)。
build cpu_side.cu && timeout 400 stdbuf -oL ./cpu_side 200 8 1
echo "  cpu_side exit=$? (124 = 超时被杀)"

echo
echo "##### done #####"
