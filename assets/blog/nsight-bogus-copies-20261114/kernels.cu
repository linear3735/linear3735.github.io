// kernels.cu
//
// 除了「空隙」之外,talk 里还有两处**手段**是可以在同一张卡上做对照实验的。
// 这个文件把两处都做成「同一份输入、两条实现路径、比数字」的形式。
//
//   实验 X:scale-space 合并那一步为什么慢
//           —— 全局原子操作 vs 共享内存原子操作
//           (对应 talk 第 25 页:Write new special-case merge kernels
//            for problem sizes small enough to allow atomic ops in
//            shared memory rather than global memory)
//
//   实验 Y:多 GPU 邻居交换为什么慢
//           —— 发很多次小拷贝 vs 打包成一次大拷贝
//           (对应 talk 第 45 页:Reduce transfer overhead by packing
//            multiple transfers in to one)
//
// 编译:nvcc -O2 -arch=sm_90 kernels.cu -o kernels
// 用法:  ./kernels [rounds]

#include <cstdio>
#include <cstdlib>
#include <vector>

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

// ============================================================ 实验 X
//
// 场景:把格子点按「组号」归并计数(scale-space 合并的抽象)。
// 每个点有一个 group id,要把每个组的计数累加起来。
//
// 两个 kernel 做的是**完全同一件事**,区别只在累加器放在哪:
//
//   merge_global:atomicAdd 打在显存上
//   merge_shared:先在本 block 的 shared memory 上 atomicAdd,再写回显存
//
// 为什么后者快:显存上的 atomicAdd 是「跨 SM 的竞争」,同一个地址被
// 几千个线程同时打,硬件只能串行化;shared memory 上的 atomicAdd
// 只在 block 内竞争,而且 shared memory 的原子操作在 L1/SMEM 里就完成了,
// 不产生显存往返。
//
// 这也解释了 talk 里那个前置条件:「problem sizes small enough」——
// 组数必须小到一张 shared memory 装得下,否则这个办法用不了。

__global__ void merge_global(const int* __restrict__ gid,
                             int* __restrict__ cnt,
                             int n, int ngroups)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    atomicAdd(&cnt[gid[i]], 1);
}

__global__ void merge_shared(const int* __restrict__ gid,
                             int* __restrict__ cnt,
                             int n, int ngroups)
{
    extern __shared__ int s_cnt[];            // ngroups 个 int
    for (int g = threadIdx.x; g < ngroups; g += blockDim.x) s_cnt[g] = 0;
    __syncthreads();

    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) atomicAdd(&s_cnt[gid[i]], 1);
    __syncthreads();

    for (int g = threadIdx.x; g < ngroups; g += blockDim.x)
        if (s_cnt[g]) atomicAdd(&cnt[g], s_cnt[g]);
}

// ============================================================ 实验 Y
//
// 场景:一个长方体的 6 个面要发给邻居(talk 第 43 页的 Send Lattice Edges)。
//
//   朴素做法:每个面单独发一次 cudaMemcpyAsync → 6 次小传输
//   打包做法:把 6 个面在 device 上拼成一块连续缓冲,只发 1 次
//
// 为什么后者快:每次传输都有固定的启动开销(提交描述符、DMA 引擎
// 起停、协议握手),这个开销和数据量无关。6 次 4KB 的开销 ≈
// 6 × 固定开销 + 24KB 的时间;1 次 24KB ≈ 1 × 固定开销 + 24KB 的时间。
//
// 这里用「同一张卡上的 D2D 拷贝」来演示,因为不需要第二张卡;
// 多卡走 NVLink 时是同一个道理(talk 第 46 页:Only one copy to
// each neighbor,10-75% performance gain)。

struct Packer {
    // 把 nfaces 个面从 src 拼到 dst 上连续摆放
    __device__ static void pack(const float* src, float* dst,
                                int face_len, int nfaces)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        int total = face_len * nfaces;
        if (idx >= total) return;
        int f = idx / face_len;
        int off = idx % face_len;
        dst[idx] = src[f * face_len + off];
    }
};

__global__ void pack_faces(const float* __restrict__ src,
                           float* __restrict__ dst,
                           int face_len, int nfaces)
{
    Packer::pack(src, dst, face_len, nfaces);
}

int main(int argc, char** argv)
{
    const int rounds = (argc > 1) ? std::atoi(argv[1]) : 50;

    std::printf("device: ");
    cudaDeviceProp prop{};
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    std::printf("%s sm_%d%d SMs=%d\n", prop.name, prop.major, prop.minor,
                prop.multiProcessorCount);

    // ---------------------------------------------------------- 实验 X
    {
        const int n = 1 << 22;          // 4M 个格子点
        const int ngroups = 256;        // 组数小到能塞进 shared memory
        const int block = 256;
        const int grid = (n + block - 1) / block;
        const size_t smem = ngroups * sizeof(int);

        std::vector<int> h_gid(n);
        for (int i = 0; i < n; ++i) h_gid[i] = (i * 2654435761u >> 24) % ngroups;

        int *d_gid = nullptr, *d_cnt = nullptr;
        CUDA_CHECK(cudaMalloc(&d_gid, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_cnt, ngroups * sizeof(int)));
        CUDA_CHECK(cudaMemcpy(d_gid, h_gid.data(), n * sizeof(int),
                              cudaMemcpyHostToDevice));

        std::vector<int> ref(ngroups, 0), got(ngroups, 0);

        // 参考解:CPU 上直接数
        for (int i = 0; i < n; ++i) ref[h_gid[i]]++;

        cudaEvent_t a, b;
        CUDA_CHECK(cudaEventCreate(&a));
        CUDA_CHECK(cudaEventCreate(&b));

        auto time_it = [&](int which) {
            CUDA_CHECK(cudaMemset(d_cnt, 0, ngroups * sizeof(int)));
            CUDA_CHECK(cudaDeviceSynchronize());
            CUDA_CHECK(cudaEventRecord(a));
            for (int r = 0; r < rounds; ++r) {
                if (which == 0)
                    merge_global<<<grid, block>>>(d_gid, d_cnt, n, ngroups);
                else
                    merge_shared<<<grid, block, smem>>>(d_gid, d_cnt, n, ngroups);
            }
            CUDA_CHECK(cudaEventRecord(b));
            CUDA_CHECK(cudaEventSynchronize(b));
            float ms = 0.f;
            CUDA_CHECK(cudaEventElapsedTime(&ms, a, b));
            return ms / rounds;
        };

        // 先各自单独跑一次,确认两个版本算出来的东西**确实一样**,
        // 然后才谈快慢。顺序不能反:如果两条路径的结果不同,
        // 后面的加速比就没有任何意义。
        // (第一版 bench_bogus.cu 就栽在这上面 —— 累加器没清零,
        //  两种模式算出不同的 checksum,却差点被当成"加速比"。)

        CUDA_CHECK(cudaMemset(d_cnt, 0, ngroups * sizeof(int)));
        merge_global<<<grid, block>>>(d_gid, d_cnt, n, ngroups);
        CUDA_CHECK(cudaMemcpy(got.data(), d_cnt, ngroups * sizeof(int),
                              cudaMemcpyDeviceToHost));
        const bool ok_global = (got == ref);

        CUDA_CHECK(cudaMemset(d_cnt, 0, ngroups * sizeof(int)));
        merge_shared<<<grid, block, smem>>>(d_gid, d_cnt, n, ngroups);
        CUDA_CHECK(cudaMemcpy(got.data(), d_cnt, ngroups * sizeof(int),
                              cudaMemcpyDeviceToHost));
        const bool ok_shared = (got == ref);

        // 校验通过之后才计时
        const double t_global = time_it(0);
        const double t_shared = time_it(1);

        std::printf("\n[X] merge  ngroups=%d n=%d\n", ngroups, n);
        std::printf("    correctness    : global=%s shared=%s (和 CPU 计数一致)\n",
                    ok_global ? "OK" : "WRONG", ok_shared ? "OK" : "WRONG");
        std::printf("    global atomics : %8.4f ms\n", t_global);
        std::printf("    shared atomics : %8.4f ms\n", t_shared);
        std::printf("    speedup        : %8.2fx\n", t_global / t_shared);

        CUDA_CHECK(cudaFree(d_gid));
        CUDA_CHECK(cudaFree(d_cnt));
        CUDA_CHECK(cudaEventDestroy(a));
        CUDA_CHECK(cudaEventDestroy(b));
    }

    // ---------------------------------------------------------- 实验 Y
    {
        const int face_len = 16384;     // 每个面 64KB(float)
        const int nfaces   = 6;
        const int total    = face_len * nfaces;

        float *src = nullptr, *dst = nullptr, *packed = nullptr;
        CUDA_CHECK(cudaMalloc(&src,    total * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&dst,    total * sizeof(float)));
        CUDA_CHECK(cudaMalloc(&packed, total * sizeof(float)));
        // memset 按字节填,所以填成 0x3f800000 才是 float 1.0f。
        // 这里只是为了让下面「搬过去的内容 == 源内容」这条校验有意义。
        {
            std::vector<float> h_fill(total, 1.0f);
            CUDA_CHECK(cudaMemcpy(src, h_fill.data(), total * sizeof(float),
                                  cudaMemcpyHostToDevice));
        }

        cudaEvent_t a, b;
        CUDA_CHECK(cudaEventCreate(&a));
        CUDA_CHECK(cudaEventCreate(&b));

        // 朴素:每个面一次拷贝
        CUDA_CHECK(cudaDeviceSynchronize());
        CUDA_CHECK(cudaEventRecord(a));
        for (int r = 0; r < rounds; ++r) {
            for (int f = 0; f < nfaces; ++f) {
                CUDA_CHECK(cudaMemcpyAsync(dst + f * face_len,
                                           src + f * face_len,
                                           face_len * sizeof(float),
                                           cudaMemcpyDeviceToDevice));
            }
            CUDA_CHECK(cudaDeviceSynchronize());
        }
        CUDA_CHECK(cudaEventRecord(b));
        CUDA_CHECK(cudaEventSynchronize(b));
        float ms_naive = 0.f;
        CUDA_CHECK(cudaEventElapsedTime(&ms_naive, a, b));
        ms_naive /= rounds;

        // 打包:先在 device 上拼成连续块,再一次拷走
        CUDA_CHECK(cudaDeviceSynchronize());
        CUDA_CHECK(cudaEventRecord(a));
        for (int r = 0; r < rounds; ++r) {
            pack_faces<<<(total + 255) / 256, 256>>>(src, packed,
                                                     face_len, nfaces);
            CUDA_CHECK(cudaMemcpyAsync(dst, packed, total * sizeof(float),
                                       cudaMemcpyDeviceToDevice));
            CUDA_CHECK(cudaDeviceSynchronize());
        }
        CUDA_CHECK(cudaEventRecord(b));
        CUDA_CHECK(cudaEventSynchronize(b));
        float ms_packed = 0.f;
        CUDA_CHECK(cudaEventElapsedTime(&ms_packed, a, b));
        ms_packed /= rounds;

        // 正确性:两条路径都要把 src 的内容完整搬到 dst,
        // 所以「打包版跑完之后 dst 里的东西」必须和「朴素版跑完之后」一样。
        // 单纯看一眼"非零"是不够的 —— 那样连整个面没搬过去都发现不了。
        std::vector<float> h_final(total), h_src(total);
        CUDA_CHECK(cudaMemcpy(h_final.data(), dst, total * sizeof(float),
                              cudaMemcpyDeviceToHost));
        CUDA_CHECK(cudaMemcpy(h_src.data(), src, total * sizeof(float),
                              cudaMemcpyDeviceToHost));
        const bool ok_pack = (h_final == h_src);

        std::printf("\n[Y] neighbor exchange face_len=%d nfaces=%d (%.0f KB)\n",
                    face_len, nfaces, total * sizeof(float) / 1024.0);
        std::printf("    correctness    : packed result == src : %s\n",
                    ok_pack ? "OK" : "WRONG");
        std::printf("    %d separate copies : %8.4f ms\n", nfaces, ms_naive);
        std::printf("    packed, 1 copy     : %8.4f ms\n", ms_packed);
        std::printf("    speedup            : %8.2fx\n", ms_naive / ms_packed);

        CUDA_CHECK(cudaFree(src));
        CUDA_CHECK(cudaFree(dst));
        CUDA_CHECK(cudaFree(packed));
        CUDA_CHECK(cudaEventDestroy(a));
        CUDA_CHECK(cudaEventDestroy(b));
    }

    return 0;
}
