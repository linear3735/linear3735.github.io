// bench_bogus.cu
//
// 复现 GTC 2018《Optimizing HPC Simulation and Visualization Code Using
// NVIDIA Nsight Systems》里 VMD 冷冻电镜分割那一段的核心现象:
//
//   时间线上出现「GPU kernel 之间的空隙」,而这些空隙不是算出来的,
//   是被三种「本可以不发生」的操作塞进去的:
//
//     A. 多余的 D2H / H2D 拷贝(而且用的是同步 API)
//     B. 循环里反复 cudaMalloc / cudaFree
//     C. 每次迭代都 cudaDeviceSynchronize 查错
//
// 这个程序把三者各自做成一个可以开关的开关,别的都不动 ——
// 这样 nsys 时间线上多出来的空隙就只可能来自打开的那一个。
//
// 编译:nvcc -O2 -arch=sm_90 --generate-line-info bench_bogus.cu -o bench_bogus
// 用法:  ./bench_bogus [iters] [n] [mode]
//          mode = good | sync | alloc | errorsync | all
//
// 注意:这是为了**把问题显出来**而写的代码,不是「典型写法」。
//       每个坏模式旁边都写了它对应的真实成因。

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include <cuda_runtime.h>

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t _e = (call);                                             \
        if (_e != cudaSuccess) {                                             \
            std::fprintf(stderr, "CUDA error %s at %s:%d\n",                 \
                         cudaGetErrorString(_e), __FILE__, __LINE__);        \
            std::exit(1);                                                    \
        }                                                                    \
    } while (0)

// ---------------------------------------------------------------- 计时
//
// 用 CUDA event 计时,不用 host 的 clock:host 墙钟会把 host 侧的忙等
// 也算进去,而我们要量的是「GPU 侧这一串工作花了多久」。

struct Timer {
    cudaEvent_t a, b;
    Timer()  { CUDA_CHECK(cudaEventCreate(&a)); CUDA_CHECK(cudaEventCreate(&b)); }
    ~Timer() { cudaEventDestroy(a); cudaEventDestroy(b); }
    void start() { CUDA_CHECK(cudaEventRecord(a)); }
    double stop_ms() {
        CUDA_CHECK(cudaEventRecord(b));
        CUDA_CHECK(cudaEventSynchronize(b));
        float ms = 0.f;
        CUDA_CHECK(cudaEventElapsedTime(&ms, a, b));
        return ms;
    }
};

// ---------------------------------------------------------------- kernel
//
// 一个玩具 kernel:每个线程在格子点上做几步扩散。
// 它本身没意义,存在的理由是「足够短」——
// 短到 host 侧那些多余操作塞进来的空隙在时间线上肉眼可见。

__global__ void diffuse(const float* __restrict__ in,
                        float* __restrict__ out,
                        int n, int steps)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;

    float v = in[i];
    #pragma unroll 4
    for (int s = 0; s < steps; ++s) {
        // 一点点算术,让 kernel 不至于短到被 launch 开销淹没
        v = v * 0.999f + 0.001f * __sinf(v + s);
    }
    out[i] = v;
}

__global__ void reduce1(const float* __restrict__ in, float* __restrict__ out, int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    float v = in[i];
    // warp 内规约,够了 —— 要的不是快,是「每次都跑一遍」
    for (int off = 16; off > 0; off >>= 1)
        v += __shfl_down_sync(0xffffffffu, v, off);
    if ((threadIdx.x & 31) == 0) atomicAdd(out, v);
}

// ---------------------------------------------------------------- 模式

struct Mode {
    bool sync_copy   = false;  // A: 多余的同步 D2H/H2D
    bool iter_alloc  = false;  // B: 循环里 malloc/free
    bool err_sync    = false;  // C: 每次迭代 cudaDeviceSynchronize
};

Mode parse_mode(const std::string& s)
{
    Mode m;
    if (s == "good")      { /* 全关 */ }
    else if (s == "sync") { m.sync_copy  = true; }
    else if (s == "alloc"){ m.iter_alloc = true; }
    else if (s == "errsync") { m.err_sync = true; }
    else if (s == "all")  { m.sync_copy = m.iter_alloc = m.err_sync = true; }
    else { std::fprintf(stderr, "unknown mode: %s\n", s.c_str()); std::exit(2); }
    return m;
}

int main(int argc, char** argv)
{
    const int iters = (argc > 1) ? std::atoi(argv[1]) : 200;
    const int n     = (argc > 2) ? std::atoi(argv[2]) : (1 << 20);
    const std::string mode_s = (argc > 3) ? argv[3] : "good";
    const Mode mode = parse_mode(mode_s);

    const int block = 256;
    const int grid  = (n + block - 1) / block;

    std::printf("mode=%s iters=%d n=%d grid=%d block=%d\n",
                mode_s.c_str(), iters, n, grid, block);

    // ---- host 侧缓冲 ----
    //
    // probe 很小(4KB),它的作用是:每次拷这么一点点东西,
    // 却要占掉一次完整的同步往返。这正是「bogus copies」难看的地方 ——
    // 时间上的代价和搬运的数据量完全不成比例。
    const int probe_n = 1024;
    float* h_probe = nullptr;
    CUDA_CHECK(cudaMallocHost(&h_probe, probe_n * sizeof(float)));  // pinned
    for (int i = 0; i < probe_n; ++i) h_probe[i] = 1.0f;

    float* h_out = nullptr;
    CUDA_CHECK(cudaMallocHost(&h_out, probe_n * sizeof(float)));

    // ---- device 侧 ----
    float *d_in = nullptr, *d_out = nullptr, *d_red = nullptr;

    if (!mode.iter_alloc) {
        // 好写法:工作缓冲只分配一次,循环里复用
        CUDA_CHECK(cudaMalloc(&d_in,  n * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&d_out, n * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&d_red, sizeof(float)));
    } else {
        // 坏写法:每次迭代都重新分配
        // 真实成因很多,比如「每个 kernel 自己管自己的临时缓冲」,
        // 或者一个 C++ 临时对象在循环体里构造/析构
        CUDA_CHECK(cudaMalloc(&d_in,  n * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&d_out, n * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&d_red, sizeof(float)));
    }

    CUDA_CHECK(cudaMemset(d_in, 0, n * sizeof(float)));
    CUDA_CHECK(cudaMemset(d_out, 0, n * sizeof(float)));
    CUDA_CHECK(cudaMemset(d_red, 0, sizeof(float)));

    Timer timer;
    timer.start();

    for (int it = 0; it < iters; ++it) {
        // ---- B: 分配/释放 ----
        float *bin = d_in, *bout = d_out, *bred = d_red;
        if (mode.iter_alloc) {
            CUDA_CHECK(cudaFree(d_in));
            CUDA_CHECK(cudaFree(d_out));
            CUDA_CHECK(cudaFree(d_red));
            CUDA_CHECK(cudaMalloc(&bin,  n * sizeof(float)));
            CUDA_CHECK(cudaMalloc(&bout, n * sizeof(float)));
            CUDA_CHECK(cudaMalloc(&bred, sizeof(float)));
            CUDA_CHECK(cudaMemset(bin,  0, n * sizeof(float)));
            d_in = bin; d_out = bout; d_red = bred;
        }

        // 每轮都把累加器清零。**这一步必须在每一轮里都做**,否则
        // iter_alloc 模式每轮拿到的是新分配(零)内存,而别的模式一直在
        // 往同一个累加器上加 —— 两边算出来的 checksum 就不是一个东西,
        // 加速比也就失去可比性。(第一版就踩了这个坑:alloc 的 checksum
        // 是 -174.5,good 是 -34927。)
        CUDA_CHECK(cudaMemset(bred, 0, sizeof(float)));

        // ---- 真正的工作 ----
        diffuse<<<grid, block>>>(bin, bout, n, 32);

        // ---- C: 每次迭代同步查错 ----
        if (mode.err_sync) {
            // 这就是 talk 里说的「Many calls to cudaDeviceSynchronize(),
            // checking error status」。它把 host 和 device 强行对齐,
            // 于是本来能重叠的 launch 排队变成「发一个、等一个」。
            CUDA_CHECK(cudaDeviceSynchronize());
            CUDA_CHECK(cudaGetLastError());
        }

        reduce1<<<grid, block>>>(bout, bred, n);

        // ---- A: 多余的同步拷贝 ----
        if (mode.sync_copy) {
            float total = 0.f;
            // 同步 D2H:host 必须等到 kernel 也做完才拿到数
            CUDA_CHECK(cudaMemcpy(&total, bred, sizeof(float),
                                  cudaMemcpyDeviceToHost));
            // 写完立刻同步 H2D 送回,哪怕下一个 kernel 根本不读它
            CUDA_CHECK(cudaMemcpy(bred, &total, sizeof(float),
                                  cudaMemcpyHostToDevice));
            h_out[it % probe_n] = total;
            // 再拷一小块没用的东西,模拟「顺手把状态刷回 host」
            CUDA_CHECK(cudaMemcpy(h_probe, bin, probe_n * sizeof(float),
                                  cudaMemcpyDeviceToHost));
        }
    }

    const double ms = timer.stop_ms();

    // 结果校验:让编译器没法把整段循环优化掉
    float check = 0.f;
    CUDA_CHECK(cudaMemcpy(&check, d_red, sizeof(float), cudaMemcpyDeviceToHost));

    std::printf("elapsed_ms=%.3f  per_iter_us=%.3f  checksum=%.6g\n",
                ms, ms * 1000.0 / iters, check);

    CUDA_CHECK(cudaFree(d_in));
    CUDA_CHECK(cudaFree(d_out));
    CUDA_CHECK(cudaFree(d_red));
    CUDA_CHECK(cudaFreeHost(h_probe));
    CUDA_CHECK(cudaFreeHost(h_out));
    return 0;
}
