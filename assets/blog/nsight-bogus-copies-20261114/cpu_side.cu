// cpu_side.cu
//
// talk 里有两处优化不涉及 kernel,可以在这台机器上直接对照复现。
//
//   实验 Z1:host 线程同步 —— pthread_cond_broadcast vs CPU spinlock
//     talk 第 44 页:Lattice Microbes 的 host 线程同步
//       "Using System API trace: pthread_cond_broadcast
//        Replaced with CPU spinlock
//        60us faster on average!  ~25% performance gain
//        Analyzed via Python"
//
//     机制是「唤醒成本」:到同步点的时候,broadcast 要把**所有**等着的
//     线程都叫醒(每个睡眠线程一次 futex 系统调用 + 调度器介入),
//     spinlock 是原地重试,不进出内核。
//
//     **同步点的数量决定这个成本重不重要。** 这一点我在这个实验上
//     栽了两次,记在这里:
//
//       第一版:每个任务 broadcast 一次。实测每次惊群约 2.6 ms
//               (dgx-009, 4 线程,383 次 broadcast 用掉约 1 s,
//                probe2 的计数器显示 done 只走到 384/500),
//               20k 个任务直接超时。
//       第二版:每轮一个屏障、主线程和 worker 用 generation 计数对账。
//               有竞态 —— 主线程上一轮 wait 返回时还没释放 mutex,
//               下一轮已经在改本轮计数,和上一轮迟到的 worker 撞上,
//               自己把自己等死(exit 124)。
//
//     现在的结构是「单一任务计数器 + 固定批大小」:线程取到任务后
//     先干满 batch 个活再碰锁。同步点 = 任务数 / batch,数量可控,
//     而且没有多轮对账,不给自己留竞态面。
//
//     所以下面这把参数(任务粒度、线程数)是**实验设定**,不是
//     普遍结论。talk 量的 60us 对应的是粗粒度任务;粒度细到某个
//     程度,cond 会被唤醒成本压死,spinlock 也会把 CPU 空烧掉 ——
//     两个原语各有适用区,这里只演示其中一段。
//
//   实验 Z2:cudaMemcpy vs zero-copy memory
//     talk 第 42 页:Lattice Microbes 把 cudaMemcpy 换成零拷贝内存,
//       "20% performance gain"
//
// 编译:nvcc -O2 -arch=sm_90 -Xcompiler -pthread cpu_side.cu -o cpu_side
// 用法:  ./cpu_side [tasks] [threads] [batch]

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include <cuda_runtime.h>
#include <pthread.h>

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t _e = (call);                                             \
        if (_e != cudaSuccess) {                                             \
            std::fprintf(stderr, "CUDA error %s at %s:%d\n",                 \
                         cudaGetErrorString(_e), __FILE__, __LINE__);        \
            std::exit(1);                                                    \
        }                                                                    \
    } while (0)

using Clock = std::chrono::steady_clock;

static double ms_since(Clock::time_point t0)
{
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

struct Job {
    long tasks = 0;
    long next  = 0;
    long done  = 0;
    long sink  = 0;
};

// 单个任务:一小段算术。**同步点和任务粒度分离** ——
// 线程一次锁住取走 batch 个任务号,然后在锁外干完。
static void work_one(long id, long& acc)
{
    for (int k = 0; k < 256; ++k) acc += (id * 131 + k) % 7;
}

// ============================================ Z1 路径 A:cond_broadcast
//
// 取任务的临界区用 mutex + condition variable 保护。没有活的时候
// 线程 pthread_cond_wait 睡下去;干完一批后由干活的那个线程
// pthread_cond_broadcast 把所有同伴叫醒去抢下一批 —— 这就是
// talk 里被换掉的那个写法,也是「惊群」的来源。

struct CondPool {
    pthread_mutex_t m  = PTHREAD_MUTEX_INITIALIZER;
    pthread_cond_t  cv = PTHREAD_COND_INITIALIZER;
    Job* job      = nullptr;
    long batch    = 1;

    static void* worker(void* arg)
    {
        auto* self = static_cast<CondPool*>(arg);
        Job* j = self->job;
        long acc = 0;
        for (;;) {
            pthread_mutex_lock(&self->m);
            if (j->next >= j->tasks) {
                // 没活了。前面可能还有同伴在睡,得把它们叫醒让它们也退。
                pthread_cond_broadcast(&self->cv);
                pthread_mutex_unlock(&self->m);
                return nullptr;
            }
            long lo = j->next;
            long hi = lo + self->batch;
            if (hi > j->tasks) hi = j->tasks;
            j->next = hi;
            pthread_mutex_unlock(&self->m);

            for (long id = lo; id < hi; ++id) work_one(id, acc);

            pthread_mutex_lock(&self->m);
            j->done += hi - lo;
            pthread_mutex_unlock(&self->m);
        }
    }

    double run(int nt, long tasks, long b)
    {
        Job j;
        j.tasks = tasks;
        job = &j;
        batch = b;

        std::vector<pthread_t> th(nt);
        auto t0 = Clock::now();
        for (int i = 0; i < nt; ++i) pthread_create(&th[i], nullptr, worker, this);
        for (int i = 0; i < nt; ++i) pthread_join(th[i], nullptr);
        const double ms = ms_since(t0);

        job->sink = j.done;     // 让结果可校验
        return ms;
    }
};

// ============================================ Z1 路径 B:CPU spinlock
//
// 同样的结构,把「睡 + 唤醒」换成原地 test_and_set。

struct SpinPool {
    std::atomic_flag lock = ATOMIC_FLAG_INIT;
    Job* job   = nullptr;
    long batch = 1;

    void acquire()
    {
        while (lock.test_and_set(std::memory_order_acquire)) {
            #if defined(__x86_64__)
            __builtin_ia32_pause();
            #endif
        }
    }
    void release() { lock.clear(std::memory_order_release); }

    static void* worker(void* arg)
    {
        auto* self = static_cast<SpinPool*>(arg);
        Job* j = self->job;
        long acc = 0;
        for (;;) {
            self->acquire();
            if (j->next >= j->tasks) { self->release(); return nullptr; }
            long lo = j->next;
            long hi = lo + self->batch;
            if (hi > j->tasks) hi = j->tasks;
            j->next = hi;
            self->release();

            for (long id = lo; id < hi; ++id) work_one(id, acc);

            self->acquire();
            j->done += hi - lo;
            self->release();
        }
    }

    double run(int nt, long tasks, long b)
    {
        Job j;
        j.tasks = tasks;
        job = &j;
        batch = b;

        std::vector<pthread_t> th(nt);
        auto t0 = Clock::now();
        for (int i = 0; i < nt; ++i) pthread_create(&th[i], nullptr, worker, this);
        for (int i = 0; i < nt; ++i) pthread_join(th[i], nullptr);
        return ms_since(t0);
    }
};

// ============================================ Z2: 拷贝 vs 零拷贝

__global__ void touch(const float* __restrict__ in,
                      float* __restrict__ out,
                      int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    out[i] = in[i] * 2.0f + 1.0f;
}

int main(int argc, char** argv)
{
    const long tasks   = (argc > 1) ? std::atol(argv[1]) : 400;
    const int  threads = (argc > 2) ? std::atoi(argv[2]) : 8;
    const long batch   = (argc > 3) ? std::atol(argv[3]) : 1;

    std::printf("host threads=%d tasks=%ld batch=%ld\n", threads, tasks, batch);
    std::fflush(stdout);

    cudaDeviceProp prop{};
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    std::printf("device: %s sm_%d%d SMs=%d\n\n", prop.name, prop.major,
                prop.minor, prop.multiProcessorCount);
    std::fflush(stdout);

    auto med = [](std::vector<double> v) {
        std::sort(v.begin(), v.end());
        return v[v.size() / 2];
    };

    // ---------------------------------------------------------- Z1
    {
        std::printf("[Z1] host 线程同步:tasks=%ld threads=%d batch=%ld"
                    "  (同步点=%ld)\n",
                    tasks, threads, batch, tasks / batch);
        std::fflush(stdout);

        // 热身:线程创建、页错误等一次性成本不进统计
        { CondPool p; p.run(threads, tasks, batch); }
        { SpinPool p; p.run(threads, tasks, batch); }

        std::vector<double> cond_ms, spin_ms;
        for (int r = 0; r < 7; ++r) {
            { CondPool p; cond_ms.push_back(p.run(threads, tasks, batch)); }
            { SpinPool p; spin_ms.push_back(p.run(threads, tasks, batch)); }
        }
        const double c = med(cond_ms), s = med(spin_ms);

        std::printf("    cond_broadcast : %9.3f ms  (中位数/7 轮)\n", c);
        std::printf("    spinlock       : %9.3f ms\n", s);
        std::printf("    ratio          : %9.3fx\n", c / s);
        std::printf("    performance gain: %7.1f %%\n", (c / s - 1.0) * 100.0);
        std::fflush(stdout);
    }

    // ---------------------------------------------------------- Z1b
    // 同一组参数下换一个任务粒度,看这个差距怎么随粒度变化。
    // 「spinlock 更快」不是无条件成立的,这一节是为了把条件摆出来。
    //
    // 任务数放大到 tasks*20:第一版只用 tasks*4,结果 batch=4/16/64
    // 三档的 spin 全是 0.143 ms、cond 全是 0.133 ms,一模一样 ——
    // 那是工作量小到被固定开销盖住了,量的是噪声不是差异。
    {
        std::printf("\n[Z1b] 换任务粒度(同步点数量变化)\n");
        std::fflush(stdout);
        const long t2 = tasks * 20;
        for (long b : {1L, 4L, 16L, 64L}) {
            { CondPool p; p.run(threads, t2, b); }
            { SpinPool p; p.run(threads, t2, b); }
            std::vector<double> cm, sm;
            for (int r = 0; r < 5; ++r) {
                { CondPool p; cm.push_back(p.run(threads, t2, b)); }
                { SpinPool p; sm.push_back(p.run(threads, t2, b)); }
            }
            const double cc = med(cm), ss = med(sm);
            std::printf("    batch=%3ld (同步点 %5ld)  cond %8.3f ms  "
                        "spin %8.3f ms   gain %6.1f %%\n",
                        b, t2 / b, cc, ss, (cc / ss - 1.0) * 100.0);
            std::fflush(stdout);
        }
    }

    // ---------------------------------------------------------- Z2
    //
    // 这里要小心别把「零拷贝的好处」和「异步化的好处」混在一起。
    //
    // 第一版只比了两条路径:
    //     A: 同步 cudaMemcpy(H2D) → kernel → 同步 cudaMemcpy(D2H)
    //     B: kernel 直接读写 mapped 主机内存,末尾 sync 一次
    // 量出来 B 快 332%,而 talk 说的是 20%。差距这么大不是零拷贝有多神,
    // 是 A 每一步都在**阻塞 host**:每次拷贝都要等完才能往下走。
    // 那 332% 里绝大部分是「host 阻塞 vs 不阻塞」,不是零拷贝本身。
    //
    // 所以这里补一条 C:pinned host 内存 + cudaMemcpyAsync + stream,
    // host 同样不阻塞,但数据仍然真的走了一趟设备内存。A / C / B 三条
    // 摆在一起,A→C 是异步化拿到的,C→B 才是零拷贝拿到的。
    {
        const int n = 4096;                  // 16 KB,刻意取小
        const size_t bytes = n * sizeof(float);
        const int block = 256;
        const int grid = (n + block - 1) / block;

        std::printf("\n[Z2] host<->device 往返:%zu 字节\n", bytes);
        std::fflush(stdout);

        std::vector<float> h_in(n, 1.0f), h_out(n, 0.0f);

        // --- A:同步拷贝 ---
        float *d_in = nullptr, *d_out = nullptr;
        CUDA_CHECK(cudaMalloc(&d_in, bytes));
        CUDA_CHECK(cudaMalloc(&d_out, bytes));

        // --- C:pinned + async ---
        float *p_in = nullptr, *p_out = nullptr;
        CUDA_CHECK(cudaHostAlloc(&p_in, bytes, cudaHostAllocDefault));
        CUDA_CHECK(cudaHostAlloc(&p_out, bytes, cudaHostAllocDefault));
        for (int i = 0; i < n; ++i) p_in[i] = 1.0f;
        float *d_pin = nullptr, *d_pout = nullptr;
        CUDA_CHECK(cudaMalloc(&d_pin, bytes));
        CUDA_CHECK(cudaMalloc(&d_pout, bytes));
        cudaStream_t st{};
        CUDA_CHECK(cudaStreamCreate(&st));

        // --- B:零拷贝(mapped pinned)---
        float *zc_in = nullptr, *zc_out = nullptr;
        CUDA_CHECK(cudaHostAlloc(&zc_in, bytes, cudaHostAllocMapped));
        CUDA_CHECK(cudaHostAlloc(&zc_out, bytes, cudaHostAllocMapped));
        for (int i = 0; i < n; ++i) zc_in[i] = 1.0f;

        float *d_zc_in = nullptr, *d_zc_out = nullptr;
        CUDA_CHECK(cudaHostGetDevicePointer(&d_zc_in, zc_in, 0));
        CUDA_CHECK(cudaHostGetDevicePointer(&d_zc_out, zc_out, 0));

        const int iters = 500;

        auto time_sync = [&]() {
            CUDA_CHECK(cudaDeviceSynchronize());
            auto t0 = Clock::now();
            for (int i = 0; i < iters; ++i) {
                CUDA_CHECK(cudaMemcpy(d_in, h_in.data(), bytes,
                                      cudaMemcpyHostToDevice));
                touch<<<grid, block>>>(d_in, d_out, n);
                CUDA_CHECK(cudaMemcpy(h_out.data(), d_out, bytes,
                                      cudaMemcpyDeviceToHost));
            }
            CUDA_CHECK(cudaDeviceSynchronize());
            return ms_since(t0) / iters;
        };

        auto time_async_pinned = [&]() {
            CUDA_CHECK(cudaDeviceSynchronize());
            auto t0 = Clock::now();
            for (int i = 0; i < iters; ++i) {
                CUDA_CHECK(cudaMemcpyAsync(d_pin, p_in, bytes,
                                           cudaMemcpyHostToDevice, st));
                touch<<<grid, block, 0, st>>>(d_pin, d_pout, n);
                CUDA_CHECK(cudaMemcpyAsync(p_out, d_pout, bytes,
                                           cudaMemcpyDeviceToHost, st));
            }
            CUDA_CHECK(cudaStreamSynchronize(st));
            return ms_since(t0) / iters;
        };

        auto time_zerocopy = [&]() {
            CUDA_CHECK(cudaDeviceSynchronize());
            auto t0 = Clock::now();
            for (int i = 0; i < iters; ++i)
                touch<<<grid, block>>>(d_zc_in, d_zc_out, n);
            CUDA_CHECK(cudaDeviceSynchronize());
            return ms_since(t0) / iters;
        };

        time_sync();            // 热身
        time_async_pinned();
        time_zerocopy();

        std::vector<double> a_v, c_v, b_v;
        for (int r = 0; r < 5; ++r) {
            a_v.push_back(time_sync());
            c_v.push_back(time_async_pinned());
            b_v.push_back(time_zerocopy());
        }
        const double a = med(a_v), c = med(c_v), b = med(b_v);

        // 三条路径算出来的结果必须一致
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            if (zc_out[i] != h_out[i]) { ok = false; break; }
            if (p_out[i]     != h_out[i]) { ok = false; break; }
        }

        std::printf("    correctness      : 三条路径结果一致 : %s\n",
                    ok ? "OK" : "WRONG");
        std::printf("    A 同步 memcpy x2 : %9.4f ms/iter\n", a);
        std::printf("    C pinned+async   : %9.4f ms/iter\n", c);
        std::printf("    B 零拷贝         : %9.4f ms/iter\n", b);
        std::printf("    A -> C 异步化    : %7.1f %%\n", (a / c - 1.0) * 100.0);
        std::printf("    C -> B 零拷贝    : %7.1f %%\n", (c / b - 1.0) * 100.0);
        std::printf("    A -> B 合计      : %7.1f %%\n", (a / b - 1.0) * 100.0);

        CUDA_CHECK(cudaFree(d_in));
        CUDA_CHECK(cudaFree(d_out));
        CUDA_CHECK(cudaFree(d_pin));
        CUDA_CHECK(cudaFree(d_pout));
        CUDA_CHECK(cudaFreeHost(p_in));
        CUDA_CHECK(cudaFreeHost(p_out));
        CUDA_CHECK(cudaStreamDestroy(st));
        CUDA_CHECK(cudaFreeHost(zc_in));
        CUDA_CHECK(cudaFreeHost(zc_out));
    }

    std::printf("\ndone\n");
    return 0;
}
