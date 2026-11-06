#!/usr/bin/env python3
"""Verify every (path, line, required substring) claim in the 3FS RDMA post.

Every claim is checked against a real read-only 3FS checkout: the file must
exist, must have that many lines, and the cited line must contain the quoted
text. A wrong line number fails loudly.

Usage:
    python3 verify_citations.py [post.md]   # default: rdma-buffer-reuse-post.md

Env:
    TREE3FS   path to the 3FS checkout (default: ./third_party-src/3fs)

Exit codes: 0 = all verified, 1 = at least one claim failed, 2 = tree missing.
"""
import os
import sys
from pathlib import Path

TREE = Path(os.environ.get("TREE3FS", "third_party-src/3fs")).expanduser()
POST = Path(sys.argv[1] if len(sys.argv) > 1 else "rdma-buffer-reuse-post.md")

# (label, relpath, lineno, required_substring)
CLAIMS = [
    # --- 1. buffer pool really exists (section 1) ---
    ("pool cls",      "src/common/net/ib/RDMABuf.h", 318, "class RDMABufPool"),
    ("pool sem",      "src/common/net/ib/RDMABuf.h", 346, "Semaphore sem_"),
    ("pool freelist", "src/common/net/ib/RDMABuf.h", 348, "freeList_"),
    ("pool dealloc",  "src/common/net/ib/RDMABuf.h", 336, "deallocate"),
    ("remote buf",    "src/common/net/ib/RDMABuf.h",  40, "class RDMARemoteBuf"),

    # --- 2.1 server-initiated RDMA: read path = server RDMA-WRITEs to client ---
    ("rd readpath fn",   "src/storage/aio/BatchReadJob.cc", 74, "BatchReadJob::addBufferToBatch"),
    ("rd readpath add",  "src/storage/aio/BatchReadJob.cc", 81, "batch.add(job.readIO().rdmabuf, localbuf)"),
    ("rd counter def",   "src/storage/aio/BatchReadJob.cc",  9, "rdmaWriteCount"),
    ("rd sole caller",   "src/storage/service/StorageOperator.cc", 187, "addBufferToBatch(writeBatch)"),

    # --- 2.1 write path = server RDMA-READs from client ---
    ("wr toRemoteBuf", "src/storage/service/StorageOperator.cc", 564, "toRemoteBuf()"),
    ("wr bypass flag", "src/storage/service/StorageOperator.cc", 565, "BYPASS_RDMAXMIT"),
    ("wr rdmaReadBatch", "src/storage/service/StorageOperator.cc", 566, "ibSocket->rdmaReadBatch()"),
    ("wr batch add",   "src/storage/service/StorageOperator.cc", 567, "readBatch.add(updateIO.rdmabuf"),
    ("wr post",        "src/storage/service/StorageOperator.cc", 589, "readBatch.post()"),
    ("wr writeTransmission", "src/storage/service/StorageOperator.cc", 186, "ctx.writeTransmission()"),

    # --- 2.1 client only registers + ships descriptors ---
    ("cli createFromUserBuffer", "src/client/storage/StorageClient.cc", 101, "RDMABuf::createFromUserBuffer"),
    ("fuse bufPool",   "src/fuse/FuseClients.cc", 86, "RDMABufPool::create"),

    # --- 2.2 timeout does NOT close at the Waiter layer ---
    ("waiter timeout call", "src/common/net/Waiter.cc", 104, "timeout(task1.uuid)"),
    ("waiter timeout def",  "src/common/net/Waiter.h", 105, "void timeout(size_t uuid)"),
    ("waiter error body",   "src/common/net/Waiter.h",  91, "static void error(Item *item, Status status)"),

    # --- 2.2 the close happens one layer up, in the RPC caller ---
    ("cc timeout cond", "src/common/serde/ClientContext.h", 89, "RPCCode::kTimeout"),
    ("cc closeIB call", "src/common/serde/ClientContext.h", 92, "item.transport->closeIB()"),
    ("cc checkConns",   "src/common/serde/ClientContext.h", 96, "checkConnections(destAddr_"),

    # --- 2.2 the unique chain to IBSocket::close ---
    ("closeIB def",     "src/common/net/Transport.cc", 135, "Transport::closeIB()"),
    ("closeIB await",   "src/common/net/Transport.cc", 139, "lastReadAndWriteFinished_"),
    ("closeIB sole",    "src/common/net/Transport.cc", 141, "->close()"),
    ("ibsocket close",  "src/common/net/ib/IBSocket.cc", 708, "CoTask<void> IBSocket::close()"),
    ("closed flag",     "src/common/net/ib/IBSocket.cc", 712, "closed_ = true"),
    ("close 200ms",     "src/common/net/ib/IBSocket.cc", 722, "kTimeout = 200_ms"),
    ("qp to err",       "src/common/net/ib/IBSocket.cc", 735, "ibv_modify_qp"),
    ("graceful start",  "src/common/net/ib/IBSocket.cc", 799, "closeGracefully"),
    ("close as write",  "src/common/net/ib/IBSocket.cc", 814, "post close msg"),
    ("close wr_id",     "src/common/net/ib/IBSocket.cc", 818, "WRId::close()"),
    ("close opcode",    "src/common/net/ib/IBSocket.cc", 822, "IBV_WR_RDMA_WRITE_WITH_IMM"),
    ("close num_sge",   "src/common/net/ib/IBSocket.cc", 821, "num_sge = 0"),
    ("close imm_data",  "src/common/net/ib/IBSocket.cc", 824, "ImmData::close()"),
    ("peer sees close", "src/common/net/ib/IBSocket.cc", 1178, "ImmData(wc.imm_data) == ImmData::close()"),

    # --- 2.2 collateral: all pending requests on the transport die together ---
    ("wakeup fn",    "src/common/net/Transport.cc", 375, "wakeUpAfterLastReadAndWriteFinished"),
    ("wakeup clear", "src/common/net/Transport.cc", 378, "clearPendingRequestsOnTransportFailure"),
    ("waiter clear", "src/common/net/Waiter.h", 108, "clearPendingRequestsOnTransportFailure"),

    # --- 3. reconnect machinery ---
    ("ibconnect svc", "src/common/net/ib/IBConnectService.h", 23, "class IBConnectService"),
    ("ibmanager",     "src/common/net/ib/IBDevice.h", 206, "class IBManager"),

    # --- 6.1 the reverse RPC service ---
    ("ctrl req uuid", "src/common/net/RDMAControl.h", 11, "SERDE_STRUCT_FIELD(uuid, size_t{})"),
    ("ctrl service",  "src/common/net/RDMAControl.h", 18, "SERDE_SERVICE(RDMAControl, 10)"),

    # --- 6.2 server side: reverse confirm BEFORE post ---
    ("at signature",   "src/common/serde/CallContext.cc", 15, "CallContext::RDMATransmission::applyTransmission"),
    ("at same transp", "src/common/serde/CallContext.cc", 19, "clientCtx(ctx_.transport())"),
    ("at best effort", "src/common/serde/CallContext.cc", 21, "if (UNLIKELY(!applyResult))"),
    ("at counter",     "src/common/serde/CallContext.cc", 23, "applyRDMATransmissionTimeout.addSample(1)"),
    ("gate timeout",   "src/storage/service/StorageOperator.cc", 199, "rdma_transmission_req_timeout()"),
    ("gate bool",      "src/storage/service/StorageOperator.cc", 200, "apply_transmission_before_getting_semaphore"),
    ("gate before",    "src/storage/service/StorageOperator.cc", 201, "controlRDMA()"),
    ("gate apply1",    "src/storage/service/StorageOperator.cc", 202, "applyTransmission(RDMATransmissionReqTimeout)"),
    ("gate semaphore", "src/storage/service/StorageOperator.cc", 208, "guard.coWait()"),
    ("gate apply2",    "src/storage/service/StorageOperator.cc", 212, "applyTransmission(RDMATransmissionReqTimeout)"),
    ("gate post after", "src/storage/service/StorageOperator.cc", 218, "writeBatch.post()"),

    # --- 6.3 client side: register waiter, released on response ---
    ("ctrl apply sig", "src/common/net/RDMAControl.cc", 30, "RDMAControlImpl::apply"),
    ("ctrl co_wait",   "src/common/net/RDMAControl.cc", 32, "limiter_->co_wait()"),
    ("ctrl setlimiter", "src/common/net/RDMAControl.cc", 34, "setTransmissionLimiterPtr"),
    ("ctrl swallow",   "src/common/net/RDMAControl.cc", 35, "if (UNLIKELY(!prepareLatency))"),
    ("ctrl signal0",   "src/common/net/RDMAControl.cc", 36, "limiter_->signal(0_ms)"),
    ("waiter cls",     "src/common/net/Waiter.h", 23, "class Waiter"),
    ("item baton",     "src/common/net/Waiter.h", 30, "folly::coro::Baton baton"),
    ("item limiter",   "src/common/net/Waiter.h", 35, "RDMATransmissionLimiterPtr limiter"),
    ("item transport", "src/common/net/Waiter.h", 34, "TransportPtr transport"),
    ("proc post",      "src/common/net/Processor.h", 154, "Waiter::instance().post(packet"),
    ("waiter post fn", "src/common/net/Waiter.h", 79, "void post(const serde::MessagePacket<> &packet"),
    ("waiter signal",  "src/common/net/Waiter.h", 85, "limiter->signal"),
    ("waiter batonpost", "src/common/net/Waiter.h", 87, "baton.post()"),

    # --- 6.4 defaults: all off ---
    ("cfg enable",     "src/common/net/Client.h", 28, "enable_rdma_control, false"),
    ("req enable",     "src/common/net/RequestOptions.h", 52, "SERDE_STRUCT_FIELD(enableRDMAControl, false)"),
    ("cfg timeout",    "src/storage/service/StorageOperator.h", 42, "rdma_transmission_req_timeout, 0_ms"),
    ("cfg before sem", "src/storage/service/StorageOperator.h", 43, "apply_transmission_before_getting_semaphore, true"),
    ("cfg max reads",  "src/storage/service/StorageOperator.h", 40, "max_concurrent_rdma_reads, 256U"),
    ("cfg max writes", "src/storage/service/StorageOperator.h", 39, "max_concurrent_rdma_writes, 256U"),
    ("cfg max trans",  "src/common/net/RDMAControl.h", 40, "max_concurrent_transmission, 64u"),
    ("only test on",   "tests/lib/UnitTestFabric.cc", 482, "set_enable_rdma_control(true)"),

    # --- 6.5 the timing difference: nothing after completion ---
    ("onRDMAFinished", "src/common/net/ib/IBSocket.cc", 560, "onRDMAFinished"),
    ("finish only",    "src/common/net/ib/IBSocket.cc", 562, "rdmaPostCtx()->finish()"),
    ("finish stamps",  "src/common/net/ib/IBSocket.h", 273, "finish()"),
    ("readpath order", "src/storage/service/StorageOperator.cc", 227, ""),
]


def main() -> int:
    if not TREE.is_dir():
        print(f"ERROR: 3FS tree not found at {TREE}")
        print("       set TREE3FS=/path/to/3fs")
        return 2
    if not POST.is_file():
        print(f"ERROR: post not found at {POST}")
        return 2

    post_text = POST.read_text(encoding="utf-8")
    verified = failed = 0
    failures = []

    for label, rel, lineno, needle in CLAIMS:
        path = TREE / rel
        if not path.is_file():
            failures.append((label, rel, lineno, "FILE MISSING"))
            failed += 1
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if lineno > len(lines):
            failures.append((label, rel, lineno, f"ONLY {len(lines)} LINES"))
            failed += 1
            continue
        actual = lines[lineno - 1].strip()
        if needle and needle not in actual:
            failures.append((label, rel, lineno, f"GOT: {actual[:110]}"))
            failed += 1
            continue
        verified += 1

    # independent check: is each cited "file:line" pair actually present in the post?
    print(f"tree  : {TREE}")
    print(f"post  : {POST}  ({len(post_text):,} chars)")
    print(f"claims: {len(CLAIMS)}   verified: {verified}   failed: {failed}")
    print()
    if failures:
        for label, rel, lineno, why in failures:
            print(f"FAIL [{label}] {rel}:{lineno}")
            print(f"      {why}")
        return 1
    print("ALL CITATIONS VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
