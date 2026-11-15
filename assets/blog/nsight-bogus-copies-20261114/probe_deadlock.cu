// probe_deadlock.cu
//
// cpu_side.cu 里的两个池子在 dgx-009 上会挂住(ps 显示 0.0% CPU,
// 说明是阻塞而不是空转)。这个程序把两段拆开、每步打一行,用来定位
// 到底是哪一段、哪一步挂的。缩到最小参数,挂也挂得快。
//
// 编译:nvcc -O2 -pthread probe_deadlock.cu -o probe_deadlock
// 用法:  stdbuf -oL ./probe_deadlock [tasks] [threads]

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include <pthread.h>

using Clock = std::chrono::steady_clock;

static double ms_since(Clock::time_point t0)
{
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

struct SharedWork {
    long tasks = 0;
    long done  = 0;
    long sink  = 0;
};

// ---------------------------------------------------------------- cond pool
struct CondPool {
    pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
    pthread_cond_t  cv = PTHREAD_COND_INITIALIZER;
    SharedWork* w = nullptr;

    static void* worker(void* arg)
    {
        auto* self = static_cast<CondPool*>(arg);
        SharedWork* w = self->w;
        for (;;) {
            pthread_mutex_lock(&self->m);
            while (w->done >= w->tasks) {
                if (w->done > w->tasks) {          // 收工信号
                    pthread_mutex_unlock(&self->m);
                    return nullptr;
                }
                pthread_cond_wait(&self->cv, &self->m);
            }
            long my = w->done++;
            pthread_mutex_unlock(&self->m);

            long acc = 0;
            for (int k = 0; k < 64; ++k) acc += (my * 31 + k) % 7;
            w->sink += acc;

            pthread_mutex_lock(&self->m);
            pthread_cond_broadcast(&self->cv);
            pthread_mutex_unlock(&self->m);
        }
    }

    double run(int nt, long tasks)
    {
        SharedWork work;
        work.tasks = tasks;
        w = &work;
        std::vector<pthread_t> th(nt);
        auto t0 = Clock::now();
        for (int i = 0; i < nt; ++i) {
            int rc = pthread_create(&th[i], nullptr, worker, this);
            if (rc != 0) std::printf("    !! pthread_create[%d] rc=%d\n", i, rc);
        }
        std::printf("    created %d threads\n", nt); std::fflush(stdout);
        for (int i = 0; i < nt; ++i) {
            pthread_join(th[i], nullptr);
            std::printf("    joined %d/%d\n", i + 1, nt); std::fflush(stdout);
        }
        return ms_since(t0);
    }
};

// ---------------------------------------------------------------- spin pool
struct SpinPool {
    std::atomic_flag lock = ATOMIC_FLAG_INIT;
    SharedWork* w = nullptr;

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
        SharedWork* w = self->w;
        for (;;) {
            self->acquire();
            if (w->done >= w->tasks) { self->release(); return nullptr; }
            long my = w->done++;
            self->release();

            long acc = 0;
            for (int k = 0; k < 64; ++k) acc += (my * 31 + k) % 7;
            w->sink += acc;
        }
    }

    double run(int nt, long tasks)
    {
        SharedWork work;
        work.tasks = tasks;
        w = &work;
        std::vector<pthread_t> th(nt);
        auto t0 = Clock::now();
        for (int i = 0; i < nt; ++i) pthread_create(&th[i], nullptr, worker, this);
        std::printf("    created %d threads\n", nt); std::fflush(stdout);
        for (int i = 0; i < nt; ++i) {
            pthread_join(th[i], nullptr);
            std::printf("    joined %d/%d\n", i + 1, nt); std::fflush(stdout);
        }
        return ms_since(t0);
    }
};

int main(int argc, char** argv)
{
    const long tasks   = (argc > 1) ? std::atol(argv[1]) : 1000;
    const int  threads = (argc > 2) ? std::atoi(argv[2]) : 4;

    std::printf("probe: tasks=%ld threads=%d\n", tasks, threads);
    std::fflush(stdout);

    std::printf("[A] cond pool, tasks=%ld\n", tasks); std::fflush(stdout);
    { CondPool p; std::printf("    -> %.2f ms\n", p.run(threads, tasks)); }
    std::fflush(stdout);

    std::printf("[B] cond pool again, tasks=%ld\n", tasks / 5); std::fflush(stdout);
    { CondPool p; std::printf("    -> %.2f ms\n", p.run(threads, tasks / 5)); }
    std::fflush(stdout);

    std::printf("[C] spin pool, tasks=%ld\n", tasks); std::fflush(stdout);
    { SpinPool p; std::printf("    -> %.2f ms\n", p.run(threads, tasks)); }
    std::fflush(stdout);

    std::printf("[D] spin pool again, tasks=%ld\n", tasks / 5); std::fflush(stdout);
    { SpinPool p; std::printf("    -> %.2f ms\n", p.run(threads, tasks / 5)); }
    std::fflush(stdout);

    std::printf("probe done\n");
    return 0;
}
