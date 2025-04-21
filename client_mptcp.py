
#!/usr/bin/env python3

import socket
import signal
import time
import random
import numpy as np
import mpsched  # 需要你预先在系统中安装此模块
import pandas as pd
import sys

BUFFER_SIZE = 1024
keep_running = True
PERF_RECORD_INTERVAL = 1.0  # seconds

def signal_handler(sig, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def create_mptcp_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    # Enable MPTCP (42 is SOL_MPTCP in many kernels)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)
    return s

def connect_socket(sock, server_ip, port):
    sock.connect((server_ip, port))

def generate_buffer():
    return bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])

def get_subflow_metrics(fd):
    subs = mpsched.get_sub_info(fd)
    throughput_sum = 0
    rtts = []
    loss_weighted = []

    for sub in subs:
        # sub[idx] 显示具体字段含义因 mpsched 实现而异
        # 假设：sub[3]=rtt, sub[4]=throughput, sub[5]=segments_out, sub[6]=retrans
        rtt = sub[3]
        tp = sub[4]
        segs_out = sub[5]
        retrans = sub[6]
        loss = retrans / segs_out if segs_out > 0 else 0

        throughput_sum += tp
        rtts.append(rtt)
        loss_weighted.append((tp, loss))

    max_latency = max(rtts) if rtts else 0
    weighted_loss = sum(tp * loss for tp, loss in loss_weighted) / throughput_sum if throughput_sum > 0 else 0

    return throughput_sum, max_latency, weighted_loss

def main(server_ip, port):
    sock = create_mptcp_socket()
    connect_socket(sock, server_ip, port)
    print(f"Connected to {server_ip}:{port}, press Ctrl+C to stop.")

    total_sent = 0
    total_recv = 0
    last_record = time.time()
    metrics_log = []

    buffer = generate_buffer()
    fd = sock.fileno()

    while keep_running:
        sent = sock.send(buffer)
        if sent <= 0:
            break
        total_sent += sent

        try:
            recv_data = sock.recv(BUFFER_SIZE)
            total_recv += len(recv_data)
        except BlockingIOError:
            pass

        if time.time() - last_record >= PERF_RECORD_INTERVAL:
            throughput, latency, loss_rate = get_subflow_metrics(fd)
            metrics_log.append({
                "time": time.time(),
                "throughput_total": throughput,
                "latency_max": latency,
                "segment_loss_rate_weighted": loss_rate
            })
            last_record = time.time()

        time.sleep(0.05)

    print(f"Finished. Sent: {total_sent // 1024} KB, Echo received: {total_recv // 1024} KB")
    sock.close()

    df = pd.DataFrame(metrics_log)
    df.to_csv("mptcp_metrics.csv", index=False)
    print("Saved metrics to mptcp_metrics.csv")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <port>")
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))
