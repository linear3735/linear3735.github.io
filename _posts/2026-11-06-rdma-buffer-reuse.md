---
layout: post
title: "RDMA Buffer 的安全复用:核对 3FS 的两条现状,和一处关键时机差异"
display_title: "RDMA Buffer 安全复用"
subtitle: 远端还能悄悄改你的内存吗：核对 3FS 的两条现状，和一处关键时机差异
description: 以 SF-Zhou《一种安全的 RDMA Buffer 复用策略》为出发点，用 DeepSeek 3FS 修订 22fca04 的真实源码核对"Server 发起 RDMA"与"超时断连"两条现状，再拆解"禁用 RDMA Write + 向远端确认"这套方案为什么成立，以及生产代码里已经存在的那套反向确认零件。
excerpt: RDMA Write 能让远端在不通知你的情况下改你的内存，超时回收 Buffer 就是在这里出事的。3FS 用"超时断连"挡住它；而它内部还有一套反向确认零件，默认关着，且时机与提案并不相同。
date: 2026-11-06 00:00:00 +0800
categories: llm inference rdma
tags: [RDMA, 3FS, DeepSeek, 缓冲区复用, 存储系统]
---

> 这篇的出发点是 SF-Zhou 的[《一种安全的 RDMA Buffer 复用策略》](https://sf-zhou.github.io/rdma/rdma_buffer_safe_reuse.html)(2025-11-19):一篇很短的笔记,提出"禁用 RDMA Write、向远端确认 Buffer 未被复用"来解决超时回收 Buffer 的危险。
> 本文不是它的转载或翻译,而是**我自己的一次精读与核对**:把它的两条现状判断拿到 [DeepSeek 3FS](https://github.com/deepseek-ai/3FS) 的真实源码里逐条验证,再把它的方案拆成"为什么成立"和"生产代码里已经有哪些零件"。
> 所有源码结论都落到 `文件:行号`,对应 3FS 修订 `22fca04`(2026-05-07),MIT 许可,可以直接打开核对。
>
> 方法承诺同「量化解剖」系列:数字给出处,推断标注为推断。这次手上只有只读源码副本、**没有 RDMA 硬件也没有运行环境**,所以凡是要跑一次才能定的结论一律写成"待验证",不和已核实的事实混排。
>
> 本次核对最值钱的两条结论,先放在前面:**原文"超时即断连"这条判断在 3FS 里能找到完整调用链**(第 2.2 节);**3FS 内部确实有一套反向确认机制,但它默认关闭,而且时机是"传输前"而不是提案说的"传输后"**——这两者不等价(第 6 节)。

## 目录

- [0 先说清楚这一篇的立场](#0-先说清楚这一篇的立场)
- [1 问题:两种 RDMA 操作,风险不对称](#1-问题两种-rdma-操作风险不对称)
- [2 核对现状:Server 发起与超时断连](#2-核对现状server-发起与超时断连)
- [3 断连的代价,比原文说的还大一点](#3-断连的代价比原文说的还大一点)
- [4 提案:禁用 Write,向远端确认](#4-提案禁用-write向远端确认)
- [5 为什么这样就安全了](#5-为什么这样就安全了)
- [6 3FS 里其实已经有这套零件](#6-3fs-里其实已经有这套零件)
- [7 两者摆在一起比](#7-两者摆在一起比)
- [8 生产上真正会咬人的几个细节](#8-生产上真正会咬人的几个细节)
- [9 局限:我没回答的问题](#9-局限我没回答的问题)
- [10 一页总表](#10-一页总表)

## 0 先说清楚这一篇的立场

先把边界划死,再说技术。

- **原文的价值在"问题定义"。** 它指出的是一个真实且容易被忽略的窗口:RDMA Buffer 从池子里取出来复用之后,远端可能还在操作它。这个窗口不是 3FS 特有的,任何"注册一批 Buffer 反复用"的 RDMA 程序都有。
- **我核对的是"3FS 是否真的这么做"。** 原文对 3FS 的描述是两条断言,我没打算直接信,而是去源码里找。结论是**两条都能找到落点**,但都有需要精确化的地方(第 2 节)。
- **最意外的发现在第 6 节。** 3FS 内部已经有一套"Server 反向调用 Client"的确认机制,和原文的提案结构高度相似,但**默认关闭、且时机不同**。
- **我没有 RDMA 硬件。** 全部结论都是源码文本层面的。任何"这样会更快/更安全"的性能断言,本文一律不写——原文也没有给数字,这点它很克制。
- **引用的许可证**:原文站点声明内容以 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可(署名 + 同许可证分发),3FS 是 MIT。本文正文是我的分析与文字,**观点与方案归原作者**;凡是直接沿用的论证思路,第 1、4 节都注明了来源。

## 1 问题:两种 RDMA 操作,风险不对称

用 RDMA Read/Write 之前,双方要先交换**已经注册过的 Buffer 地址**(在这个地址上,网卡可以绕过 CPU 直接读写本机内存)。为了性能,没人会每次现注册,而是一开始注册一批放进池子,用完还回去。3FS 里这个池子是实打实存在的:`src/common/net/ib/RDMABuf.h:318` 的 `class RDMABufPool` 内部是一个 `folly::fibers::Semaphore sem_`(`:346`)配一条 `std::deque<RDMABuf::Inner *> freeList_`(`:348`),靠 `deallocate`(`:336`)把 Buffer 还回空闲链表。

现在关键的分叉来了——**同一块本地 Buffer,在两个方向上的风险完全不对称**:

| 操作 | 谁动谁的内存 | 本地 Buffer 的角色 | 出事的条件 |
|---|---|---|---|
| RDMA Write | 远端把数据写进**本地** Buffer | 被远端写入 | 本地复用了它,远端却还在往里写 |
| RDMA Read | 远端从**本地** Buffer 读走数据 | 被远端读取 | 本地复用了它(内容已变),远端读到的是错的 |

两条都能出事,但**性质不同**:

- **RDMA Write 的风险是"你的内存被悄悄改了"。** 远端不通知你,你也不知道。反注册 Buffer、或者断掉连接,都是在用"让远端写不进来"来挡住它。
- **RDMA Read 的风险是"远端读到脏数据"。** 麻烦的是**远端不知道**这件事——它以为读到的还是它要的那份。换句话说,Read 的风险本质是**信息差**,而信息差可以靠"告诉它一声"来消除。

这个区分是原文最核心的一步,也是它整个方案成立的支点:**Read 不需要阻止,只需要通知;Write 才需要阻止。**

## 2 核对现状:Server 发起与超时断连

原文对 3FS 有两条断言。我逐条去源码里找,结果如下。

### 2.1 断言一:所有 RDMA 操作都由 Server 端发起 —— 成立

而且方向是"反"的,值得写清楚。**读 chunk**(Server → Client 推数据):Server 用 **RDMA Write** 把数据写进 Client 的 Buffer。

- `src/storage/aio/BatchReadJob.cc:74-94` 是路径本体:`BatchReadJob::addBufferToBatch` 对每个 job 调 `batch.add(job.readIO().rdmabuf, localbuf)`(`:81`),这里的 `rdmabuf` 是**客户端的** Buffer、`localbuf` 是 Server 自己的;同时累加三个监控量(`rdmaWriteCount` / `rdmaWriteFails` / `rdmaWriteBytes`,定义在 `:9-11`)。
- 这个函数唯一的调用点是 `src/storage/service/StorageOperator.cc:187`。

**写 chunk**(Client → Server 送数据):Server 用 **RDMA Read** 从 Client 的 Buffer 拉数据。

- `src/storage/service/StorageOperator.cc:563-572`(在 `doUpdate` 里)是先 `remoteBuf = allocateResult->toRemoteBuf()`(`:564`)拿到 Server 侧 Buffer,再 `auto readBatch = ibSocket->rdmaReadBatch();`(`:566`)、`readBatch.add(updateIO.rdmabuf, std::move(*allocateResult))`(`:567`),最后在 `:589` `readBatch.post()`。
- 注意 `:565` 的 `if (!BITFLAGS_CONTAIN(featureFlags, FeatureFlags::BYPASS_RDMAXMIT))`——RDMA 这段可以被 feature flag 跳过,跳过后走普通传输。

我把"谁发起"做了全树验证:除了 `IBSocket.h` 自身的定义,生产代码里 `rdmaRead/rdmaWrite/rdmaReadBatch/rdmaWriteBatch/readTransmission/writeTransmission` 只出现在两处——`StorageOperator.cc:186` 和 `:566`,**都在 storage server**;其余命中全在测试里(`tests/common/net/ib/TestIBSocket.cc`、`tests/common/net/ib/TestRDMA.cc`)。而 `src/fuse/` 与 `src/client/` 下这些符号**零命中**:客户端只负责注册内存并交出描述符,例如 `src/client/storage/StorageClient.cc:101` 的 `RDMABuf::createFromUserBuffer(buf, len)`、`src/fuse/FuseClients.cc:86` 的 `RDMABufPool::create(...)`。

**所以"Server 发起"是真的,但有个前提不能省**:客户端仍然必须**预先注册并 pin 住**自己的 Buffer、把地址和 rkey 交给 Server。这是一份**联合契约**——发起权在 Server,可用性靠 Client。原文说"所有 RDMA 操作都是由 Server 端发起"没错,只是这句话容易被读成"客户端在这条链路上没有责任"。

顺带解释一个直觉上很别扭的事实:**"客户端读文件"这个动作,在 RDMA 层面是一个 Write 操作**——因为数据要从 Server 进 Client 的内存,只有 Write 能做到"我写进你的内存"。而危险的那一半(远端写你的内存)恰好就落在客户端身上。

### 2.2 断言二:Client 超时后关闭连接,从而让 Buffer 安全 —— 成立,但要加两个限定

**我原本以为这条找不到。** 第一遍只读 `Waiter` 的超时路径时,我看到的是超时"什么都不关":定时线程调 `Waiter::instance().timeout(task1.uuid)`(`src/common/net/Waiter.cc:104`),而它只是 `error(find(uuid), Status(RPCCode::kTimeout))`(`src/common/net/Waiter.h:105`,实现 `:91-99`)——设状态、放信号量、post baton,没有任何拆除动作。

**但关连接的动作在上一层,在 RPC 调用者那里。** `src/common/serde/ClientContext.h:89-98`:

```cpp
if (item.status.code() == RPCCode::kTimeout && std::holds_alternative<net::IOWorker *>(connectionSource_)) {
  if (item.transport) {
    XLOGF(INFO, "req timeout and close transport {}", fmt::ptr(item.transport.get()));
    co_await item.transport->closeIB();
  } else {
    XLOGF(INFO, "req timeout but no transport");
  }
  std::get<net::IOWorker *>(connectionSource_)->checkConnections(destAddr_, Duration::zero());
}
```

调用链完整且唯一:`ClientContext.h:92` → `Transport::closeIB()`(`src/common/net/Transport.cc:135-143`)→ `co_await dynamic_cast<IBSocket *>(socket_.get())->close();`(`Transport.cc:141`)→ `IBSocket::close()`(`src/common/net/ib/IBSocket.cc:708`)。`closeIB()` 是全树**唯一**调用 `IBSocket::close()` 的地方。

**第一个限定:不是"立即"。** `closeIB()` 里先 `invalidate()`,然后 `co_await lastReadAndWriteFinished_`——**要等在途的读写收尾**;`Transport.cc:379` 的 `wakeUpAfterLastReadAndWriteFinished` 才会把 `lastReadAndWriteFinished_` post 出去。所以从超时到连接真正拆掉之间,存在一段等待在途 I/O 的时间。

**第二个限定:作用域是整条 Transport。** `closeIB()` 拆的是**共享的那条 Transport**,不只是这一次请求——同一条连接上多路复用的其他在途请求会一起受影响。这一点比原文的表述更重,第 3 节展开。

`IBSocket::close()` 本身的实现也值得看一眼,因为它解释了"为什么断连能保护 Buffer",而且藏着一个自洽性问题(第 8 节):

- 先 `closed_ = true`(`:712`)标记;
- 然后 `closeGracefully()` 尝试优雅关闭,**最多等 200ms**(`static constexpr auto kTimeout = 200_ms`,`:722`,循环每 50ms 查一次状态);
- 优雅关闭的动作不是直接拆连接,而是**发一个空的 RDMA write,带 `ImmData::close()` 作为立即数**(`IBSocket.cc:814-825`,在 `closeGracefully()` 内,`:799` 起):`opcode = IBV_WR_RDMA_WRITE_WITH_IMM`、`.num_sge = 0`、`.imm_data = ImmData::close()`;
- 对端靠这个立即数识别"这是关闭信号",见 `IBSocket.cc:1178`:`wr.type() == WRType::RECV && (wc.wc_flags & IBV_WC_WITH_IMM) && ImmData(wc.imm_data) == ImmData::close();`
- 优雅关闭走不通时,`close()` 在 `:734-735` 用 `ibv_modify_qp(..., IBV_QPS_ERR)` 把 QP 打到错误态。

**为什么"断连"能保护 Buffer?** 因为它把这条连接上**后续所有**的远端 RDMA 操作都掐掉了。远端再也发不出 Write,本地 Buffer 自然就不怕被悄悄改。原文这条判断是对的。

**还有一个必须先说的护栏:** `Transport.cc:375-381` 的 `wakeUpAfterLastReadAndWriteFinished` 里,当最后一条读写都完成时,会调 `Waiter::instance().clearPendingRequestsOnTransportFailure(this)`,把这条 transport 上**所有**还挂着的请求统一按 `kTimeout` 失败掉(`Waiter.h:108-120`)。也就是说连接一旦废掉,上面的请求不是"接着等",而是**一起判死**。

## 3 断连的代价,比原文说的还大一点

原文对代价的描述很直接,我把它展开成因果链,因为这条链比结论本身更有用:

1. 某个请求超时;
2. 这条 **Transport 被拆掉**(不只是这一次请求);
3. 下一轮请求不能再用这条连接,只能**换一条,或者新建一条**;
4. 新建连接要重新握手、重新协商 Buffer 信息(3FS 的这套流程在 `IBConnectService`,`src/common/net/ib/IBConnectService.h:23`;设备级管理在 `class IBManager`,`src/common/net/ib/IBDevice.h:206`);
5. 在系统已经"忙到开始超时"的时刻,额外付出这些成本,**更容易触发下一轮超时**。

这是一个**正反馈**结构:超时 → 断连 → 更多开销 → 更容易超时。原文那句"更容易触发下一轮的超时"说的就是这个。

**我要在原文基础上再加一条它的代价**:因为 `closeIB()` 拆的是整条共享 Transport,而 `clearPendingRequestsOnTransportFailure` 会把上面所有在途请求一起按超时判死——**一个请求超时会连坐同一条连接上的其他请求**。这比"下一轮更容易超时"更直接:不是未来更容易超时,而是**当下就有无辜请求被牺牲**。

**注意这是定性判断,没有数字**:原文没给重连耗时、没给超时率上升曲线,本文也不编。

## 4 提案:禁用 Write,向远端确认

回到第 1 节的两条风险,分开处理:

- **Write 的风险**用"不用 Write"消掉。数据只能靠 Read 搬,而 Read 不改本地内存,所以"被远端悄悄改"这一类风险从根上没有了。**注意这是一次架构级取舍,不是优化**:它要求把所有 Write 语义的传输重写成 Read 语义。
- **Read 的风险**用"让远端知道"消掉。既然远端是唯一在意"缓冲区内容是否还是它要的那份"的一方,那就在 Read 前后向远端确认一次:**这块 Buffer 还没被复用**。

于是流程变成:**RDMA Read 之前,先发一个反向的消息,远端确认后,才允许这次 Read 发生。**

原文给的两张图(本地读远端 / 本地写远端)是 Mermaid 图,静态抓取取不到内容,所以本文不复述图的时序细节,只保留它的骨架:**确认与数据传输绑定在同一次请求上**。想看准确时序请看原文。

## 5 为什么这样就安全了

把"告诉远端一声"翻译成并发语言,它其实是一个**租约(lease)**:

- 远端的 Read 只有在**持有确认**的条件下才允许发出;
- 本地只有在**确认已经完成、且这次 Read 已完成或已作废**之后,才允许把这块 Buffer 还给池子复用。

只要这两条同时成立,就不存在"远端在读、本地已经改"的窗口。

**这套方案真正的代价在哪,必须说清楚:**它把安全性从"连接级"降到了"Buffer 级"——本来断连一次能保护一整条连接上的所有 Buffer,现在要为**每一次传输**维护一个确认状态。这换来了:

- 好处:超时不再需要毁掉连接,只作废**这一次**传输和**这一块** Buffer,不再连坐;
- 代价:每次传输多一个往返(RTT),以及本地必须跟踪"这块 Buffer 上还有没有未完成的确认"。

**所以它是拿延迟换可用性。** 原文没有给这个往返的量化代价,本文也不编——但这个方向的成本是确定的,在高吞吐场景下它未必划算,**这一点原文没有展开,我把它列进第 9 节的局限**。

## 6 3FS 里其实已经有这套零件

这是本次核对最意外的部分:**和原文提案结构高度相似的反向确认,3FS 里已经实现了,而且默认是关的。**

### 6.1 反向 RPC:`RDMAControl.apply`

`src/common/net/RDMAControl.h` 定义了一个 serde 服务,只有一个方法:

```cpp
struct RDMATransmissionReq {
  SERDE_STRUCT_FIELD(uuid, size_t{});
};
struct RDMATransmissionRsp {
  SERDE_STRUCT_FIELD(dummy, Void{});
};
SERDE_SERVICE(RDMAControl, 10) { SERDE_SERVICE_METHOD(apply, 1, RDMATransmissionReq, RDMATransmissionRsp); };
```

请求里只带一个 `uuid`(`RDMAControl.h:10-12`),作用是把这次请求和 Client 侧的等待者绑定。这就是"Server 反向调用 Client"的那条通道。

### 6.2 发起侧:Server 在 post RDMA 之前先反向确认

`src/common/serde/CallContext.cc:15-26` 的 `CallContext::RDMATransmission::applyTransmission` 是发起端:

```cpp
net::UserRequestOptions options{timeout};
net::RDMATransmissionReq req{ctx_.packet().uuid};
serde::ClientContext clientCtx(ctx_.transport());
auto applyResult = co_await net::RDMAControl<>::apply(clientCtx, req, &options);
if (UNLIKELY(!applyResult)) {
  XLOGF(DBG, "apply transmission error: {}", applyResult.error());
  applyRDMATransmissionTimeout.addSample(1);
}
```

注意两点:请求用的是**同一条 transport**(`clientCtx(ctx_.transport())`);而失败只是**记一个计数器**,不中断流程——**这个确认是尽力而为的**。

调用的位置在 `src/storage/service/StorageOperator.cc:199-213`,是一个明确的开关门:

```cpp
auto RDMATransmissionReqTimeout = config_.rdma_transmission_req_timeout();
bool applyTransmissionBeforeGettingSemaphore = config_.apply_transmission_before_getting_semaphore();
if (ctx.packet().controlRDMA() && RDMATransmissionReqTimeout != 0_ms && applyTransmissionBeforeGettingSemaphore) {
  co_await writeBatch.applyTransmission(RDMATransmissionReqTimeout);
}
// ... 拿并发信号量:SemaphoreGuard guard(...); co_await guard.coWait(); ...
if (ctx.packet().controlRDMA() && RDMATransmissionReqTimeout != 0_ms && !applyTransmissionBeforeGettingSemaphore) {
  co_await writeBatch.applyTransmission(RDMATransmissionReqTimeout);
}
// ... 之后才 co_await writeBatch.post();
```

**三个条件同时成立才启用**:请求方要带 `controlRDMA`、`rdma_transmission_req_timeout` 不能是 0、以及那个 `apply_transmission_before_getting_semaphore` 决定它排在信号量前还是后。**但两个分支都在 `writeBatch.post()`(`:218`)之前**——那个开关只调整它和 Server 侧 RDMA 信号量的先后,不改"传输前"这个性质。

### 6.3 接收侧:Client 登记等待者,完成事件才放行

Client 侧 `RDMAControlImpl::apply`(`src/common/net/RDMAControl.cc:30-41`)收到反向 RPC 后:

```cpp
co_await limiter_->co_wait();
transmissionWaitLatency.addSample(RelativeTime::now() - startTime);
auto prepareLatency = Waiter::instance().setTransmissionLimiterPtr(req.uuid, limiter_, startTime);
if (UNLIKELY(!prepareLatency)) {
  limiter_->signal(0_ms);
} else {
  transmissionPrepareLatency.addSample(*prepareLatency);
}
```

它把一个**限流器**按 `uuid` 登记进全局 `Waiter`(`src/common/net/Waiter.h:23`,`Item` 结构里有 `baton`(`:30`)、`limiter`(`:35`)、`transport`(`:34`)等成员)。等真正的传输完成时,`src/common/net/Processor.h:154` 在"收到的是响应"这条分支上调 `Waiter::instance().post(packet, std::move(buf))`,找到对应 `Item`、`limiter->signal(...)` 之后再 `baton.post()` 唤醒调用者(`Waiter.h:79-89`)。

换句话说,**这个配额从"反向确认"一直占到"整个请求收到响应"才释放**——它是背压与并发控制,不是缓冲区有效性校验。

### 6.4 默认是关的,而且关得很彻底

| 开关 | 位置 | 默认值 |
|---|---|---|
| `enable_rdma_control` | `src/common/net/Client.h:28` | **`false`** |
| `enableRDMAControl`(请求级) | `src/common/net/RequestOptions.h:52` | **`false`** |
| `rdma_transmission_req_timeout` | `src/storage/service/StorageOperator.h:42` | **`0_ms`** |
| `apply_transmission_before_getting_semaphore` | `src/storage/service/StorageOperator.h:43` | `true` |
| `max_concurrent_transmission` | `src/common/net/RDMAControl.h:40` | `64u` |
| `max_concurrent_rdma_reads` / `_writes` | `src/storage/service/StorageOperator.h:39-40` | 各 `256U` |

两个默认值(`Client.h:28` 的配置项、`RequestOptions.h:52` 的请求字段)都是 `false`,而 `StorageOperator.h:42` 的超时是 `0_ms`——`0_ms` 会让 `:201` 和 `:211` 两个 `!= 0_ms` 判断直接短路。

**更值得注意的是它在配置里的实际状态**:仓库随附的 `configs/*.toml` 里 `enable_rdma_control` **全是 false**,全树唯一把它打开的地方是测试:`tests/lib/UnitTestFabric.cc:482` 的 `clientConfig_.net_client().set_enable_rdma_control(true);`。

**一个特性默认关掉、配置里从不开、只有测试打开**——这通常说明它要么还不够成熟,要么代价还没被接受。这是**推断,不是事实**(第 9 节)。

### 6.5 和原文方案的差别:确认在"传输前",不是"传输后"

必须精确,不能含糊。我把整个时序核了一遍:

`StorageOperator::batchRead` 的顺序是 `ctx.writeTransmission()`(`:186`)→ `batch.addBufferToBatch(writeBatch)`(`:187`)→ `applyTransmission(...)`(`:202` 或 `:212`)→ `co_await guard.coWait()`(`:208`)→ **`co_await writeBatch.post()`(`:218`)** → 等 AIO(`:227`)→ 返回。

- 3FS 这个反向 RPC 是**传输前**的确认:它在 `post()` 之前完成,作用是**为这次传输预留并发配额**并让 Client 侧登记等待者。
- 原文说的是**确认 Buffer 在传输期间未被复用**(其表述是 Read 成功后向远端确认)。

**传输完成后有没有再确认一次?没有。** `IBSocket::onRDMAFinished`(`IBSocket.cc:560-563`)只做 `wr.rdmaPostCtx()->finish()`,而 `finish()`(`IBSocket.h:273-276`)只是盖一个 `postEnd` 时间戳并 post baton。**没有第二次往返、没有标志位、没有校验和、没有 rkey 复检。**

**所以两者不等价。** 传输前确认解决的是"这次传输是否被允许发生、并发多大";传输后确认解决的是"这次读到的数据是否还有效"。3FS 的这套零件**可以直接改造成原文的方案**(通道、uuid 绑定、等待者登记都是现成的),但**不能声称 3FS 已经实现了原文的方案**。

**还有一个方向的差别,更容易被忽略:写路径根本没有这套确认。** `doUpdate`(客户端写 chunk、Server 拉数据那条路,`:521-614`)从头到尾**没有调用 `applyTransmission`**,Server 只是在 `:566-589` 直接 RDMA-Read 客户端 Buffer,唯一的闸门是 Server 侧本地的 `concurrentRdmaReadSemaphore_`。也就是说:**读路径有(传输前的)反向确认,写路径连传输前的都没有。** 这一条是我这次核对里最值得写下来的不对称。

## 7 两者摆在一起比

| 维度 | 现状:超时断连 | 提案:禁 Write + 向远端确认 |
|---|---|---|
| 挡住远端 Write 的方式 | 断连接,让远端写不进来 | 根本不用 Write |
| Read 的脏数据风险 | 靠断连顺带挡住 | 靠向远端确认消除信息差 |
| 失效的作用域 | **整条共享 Transport** | **单次传输 / 单块 Buffer** |
| 对同连接其他请求 | 一起判超时(`clearPendingRequestsOnTransportFailure`) | 不受影响 |
| 超时的代价 | 换连接或新建连接,易连锁 | 作废这一次传输 |
| 额外开销 | 重连握手 | 每次传输一个往返 RTT |
| 3FS 实现状态 | 在用,调用链已核实(`ClientContext.h:92`) | 有零件(`RDMAControl`),默认关 |
| 确认时机 | — | 3FS 零件是**传输前**;提案要的是**传输后** |

## 8 生产上真正会咬人的几个细节

这几条是读源码时觉得"如果我要动这块,一定会踩"的地方,原文没提:

1. **"立即断连"其实要先等在途 I/O。** `closeIB()`(`Transport.cc:135-143`)会 `co_await lastReadAndWriteFinished_`,而且 `IBSocket::close()` 自身还有最多 200ms 的优雅期(`IBSocket.cc:722`)。**在这段等待里,远端理论上仍有能力发 Write。** 这个窗口值不值得担心,取决于上层在这期间还会不会复用 Buffer——**这一条我没有核实到结论,标记为待验证。**
2. **关闭本身是一次 RDMA write。** `IBSocket.cc:814-825` 用空 write 加 `ImmData::close()` 通知对端。也就是说**"断连"这个保护动作自身走的就是 Write 通道**——如果按原文方案彻底禁掉 Write,这条通知机制需要换实现。这是个容易被忽略的自洽性问题。
3. **反向确认是尽力而为,失败不拦。** `applyTransmission` 失败只 `addSample(1)` 记数(`CallContext.cc:23-25`),协程照样正常返回;`setTransmissionLimiterPtr` 绑不上时也只是 `limiter_->signal(0_ms)`(`RDMAControl.cc:34-36`)。那么"确认失败时这次传输到底发不发"就是语义问题——**这在生产里是安全边界所在,必须明确定义**,而当前代码的答案是"照发"。
4. **反向确认也要限流,说明它是真实压力点。** `max_concurrent_transmission` 默认 `64`(`RDMAControl.h:40`),而 `RDMAControlImpl::apply` 第一件事就是 `co_await limiter_->co_wait()`(`RDMAControl.cc:32`)。作者已经预见到"反向 RPC 会把 Client 打爆"。
5. **配额的释放点在响应侧,不在 RDMA 完成点。** 限流器是在 `Waiter::post`(收到响应,`Waiter.h:85`)或 `Waiter::error`(`:95`)里才 `signal` 的。所以这个配额比一次 RDMA 长得多——**它是"整个请求"的配额,不是"这次传输"的配额**,容量规划时不能按 RDMA 时长算。

## 9 局限:我没回答的问题

1. **没有性能数字。** 原文没有,我也没有硬件。RTT 代价和断连代价谁大,本文不判断。
2. **3FS 为什么把 `controlRDMA` 默认关掉,没有定论。** 我只能从"默认关 + 配置里从不开 + 只有测试打开"推断它不成熟或代价未被接受,**这是推断,不是事实**。可能有我没读到的历史原因。
3. **禁用 RDMA Write 在 3FS 架构下是否可行,没有评估。** 读 chunk 路径(`BatchReadJob.cc`)依赖 Write 把数据推进客户端内存,改成 Read 意味着客户端要主动拉——那是另一个架构问题,远超原文和本文的范围。
4. **200ms 优雅期窗口内复用 Buffer 是否真的危险,没有结论**(第 8 节第 1 条)。
5. **原文的两张图我没有复现。** Mermaid 源码在静态抓取里取不到,本文只保留了它的结构骨架,时序细节请看原文。
6. **没有跑任何测试、没有编过 3FS。** 全部结论来自静态阅读。本文所有 `文件:行号` 都逐行打印核对过,但静态阅读看不到编译期开关组合出来的真实行为。

## 10 一页总表

**三句话:**

1. **RDMA Write 和 Read 的风险不对称**:Write 是"别人悄悄改你的内存",Read 是"别人读到脏数据"——后者只是信息差,通知即可消除。
2. **原文对 3FS 的两条判断都成立,而且第二条比它说的更重**:超时确实会断连(调用链 `ClientContext.h:92` → `Transport.cc:141` → `IBSocket.cc:708`),但拆的是整条共享 Transport,还会把同连接上的其他在途请求一起判超时;代价不止"下一轮更容易超时",还有当下的连坐。
3. **原文的提案方向清晰,代价是拿每次传输一个 RTT 换可用性**,原文没给量化代价;而 3FS 内部那套反向确认零件**默认关闭、只在测试里打开、且时机是传输前而非传输后**——结构相似,不等价。

**核实纪律(建议照抄):**

1. 源码引用对应具体修订(3FS `22fca04`),写到 `文件:行号`。
2. 区分"能力已核实"和"调用链待验证"——**具备某个能力 ≠ 在那条路径上真的调了**。这次第一遍我就差点把"超时断连"写成待验证,因为只看了 `Waiter` 那一层;真正的调用点在上层的 `ClientContext`。
3. "结构相同"不等于"等价":3FS 的反向 RPC 与原文方案结构相似、**时机不同**(传输前 vs 传输后),不能混为一谈。
4. 同一个机制在两条路径上可能不对称:**读路径有传输前确认,写路径连传输前都没有**。看一条路径不能推全貌。
5. 别人的方案与观点标明出处与许可证;自己没跑过的结论不写成实测。

---

**材料与出处**

- 出发点:SF-Zhou[《一种安全的 RDMA Buffer 复用策略》](https://sf-zhou.github.io/rdma/rdma_buffer_safe_reuse.html),2025-11-19。**观点与方案归原作者**,该站点声明内容以 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可。本文为精读与源码核对,非转载或翻译。
- 3FS 源码:[deepseek-ai/3FS](https://github.com/deepseek-ai/3FS),修订 `22fca04564c7cc230fd8b9523b8b92864e1dad47`(2026-05-07),MIT 许可。本文全部 `文件:行号` 对应此修订。
- 本博客相邻:[拆解 DeepSeek V4.1 Flash 推理架构](/deepinfer-v41-arch/) · [XGrammar-2 精读](/xgrammar2-source-reading/) · [AI Infra:从一条推理命令到硬件](/aiinfra-command-to-hardware/)
