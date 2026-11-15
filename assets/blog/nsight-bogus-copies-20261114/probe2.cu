// probe2.cu
//
// probe_deadlock.cu 证明了「宣布收工的线程没有 broadcast」会让 join 挂死。
// 但修掉那一处之后 cpu_side 仍然挂在 [Z1],说明还有第二个原因。
//
// 这个版本给 cond 池加上计数器,并且**不退出就外部超时**,
// 让挂死的点能自己暴露出来:
//
//   waits      —— 线程进入 pthread_cond_wait 的次数
//   broadcasts —— broadcast 次数
//   tasks_ok   —— 实际取走的任务数
//
// 如果 tasks_ok 停在某个数不动,而 waits 还在涨,就是「主线程在等一个
// 永远追不平的 done」。

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <thread>
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

struct Counters {
    std::atomic<long> waits{0};
    std::atomic<long> broadcasts{0};
    std::atomic<long> tasks_ok{0};
};

struct CondPool {
    pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
    pthread_cond_t  cv = PTHREAD_COND_INITIALIZER;
    SharedWork* w = nullptr;
    bool shutdown = false;
    Counters* c = nullptr;

    std::mutex done_mu;
    std::condition_variable done_cv;

    static void* worker(void* arg)
    {
        auto* self = static_cast<CondPool*>(arg);
        SharedWork* w = self->w;
        for (;;) {
            pthread_mutex_lock(&self->m);
            if (self->shutdown && w->done >= w->tasks) {
                pthread_mutex_unlock(&self->m);
                return nullptr;
            }
            if (w->done >= w->tasks) {
                self->c->waits.fetch_add(1);
                pthread_cond_wait(&self->cv, &self->m);
                pthread_mutex_unlock(&self->m);
                continue;
            }
            long my = w->done++;
            self->c->tasks_ok.fetch_add(1);
            pthread_mutex_unlock(&self->m);

            long acc = 0;
            for (int k = 0; k < 64; ++k) acc += (my * 31 + k) % 7;
            w->sink += acc;

            pthread_mutex_lock(&self->m);
            self->c->broadcasts.fetch_add(1);
            pthread_cond_broadcast(&self->cv);
            pthread_mutex_unlock(&self->m);
        }
    }

    // 主线程就等 done 追平;带进度打印,卡住时能看出追到哪了
    void wait_done(SharedWork& work)
    {
        for (;;) {
            {
                std::unique_lock<std::mutex> lk(done_mu);
                if (work.done >= work.tasks) return;
            }
            std::printf("      [progress] done=%ld/%ld waits=%ld bc=%ld ok=%ld\n",
                        work.done, work.tasks,
                        c->waits.load(), c->broadcasts.load(),
                        c->tasks_ok.load());
            std::fflush(stdout);
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }

    double run(int nt, long tasks)
    {
        SharedWork work;
        work.tasks = tasks;
        Counters counters;
        c = &counters;
        w = &work;
        shutdown = false;

        std::vector<pthread_t> th(nt);
        auto t0 = Clock::now();
        for (int i = 0; i < nt; ++i) pthread_create(&th[i], nullptr, worker, this);

        wait_done(work);

        pthread_mutex_lock(&m);
        shutdown = true;
        counter_broadcasts:;
        counters.broadcasts.fetch_add(1);
        pthread_cond_broadcast(&cv);
        pthread_mutex_unlock(&m);

        for (int i = 0; i < nt; ++i) pthread_join(th[i], nullptr);
        return ms_since(t0);
    }
};

int main(int argc, char** argv)
{
    const long tasks   = (argc > 1) ? std::atol(argv[1]) : 500;
    const int  threads = (argc > 2) ? std::atoi(argv[2]) : 4;

    std::printf("probe2 tasks=%ld threads=%d\n", tasks, threads);
    std::fflush(stdout);

    CondPool p;
    std::printf("  -> %.2f ms\n", p.run(threads, tasks));
    std::printf("probe2 done\n");
    return 0;
}
