#!/usr/bin/env python3

import socket
import time
import random
import pandas as pd
import argparse
import mpsched
import signal

BUFFER_SIZE = 1024
PERF_RECORD_INTERVAL = 1.0
keep_running = True

# Handle Ctrl+C
def signal_handler(sig, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def create_mptcp_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()

    sock = create_mptcp_socket()
    sock.connect((args.ip, args.port))
    fd = sock.fileno()
    buffer = bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])

    start_time = time.time()
    last_record = start_time
    metrics_log = []

    while keep_running and (time.time() - start_time < args.duration):
        try:
            sock.send(buffer)
            try:
                sock.recv(BUFFER_SIZE)
            except BlockingIOError:
                pass

            if time.time() - last_record >= PERF_RECORD_INTERVAL:
                subs = mpsched.get_sub_info(fd)

                throughput_sum = 0
                rtts = []
                loss_weighted = []

                for sub in subs:
                    segs_out = sub[0]
                    rtt = sub[1]
                    cwnd = sub[2]
                    unacked = sub[3]
                    retrans = sub[4]
                    # 注意：这里进行throughput算法
                    throughput = segs_out / (PERF_RECORD_INTERVAL * 125000)  # Mbps

                    throughput_sum += throughput
                    rtts.append(rtt)
                    loss = retrans / segs_out if segs_out > 0 else 0
                    loss_weighted.append((throughput, loss))

                max_latency = max(rtts) if rtts else 0
                weighted_loss = sum(tp * loss for tp, loss in loss_weighted) / throughput_sum if throughput_sum > 0 else 0

                metrics_log.append({
                    "time": time.time() - start_time,
                    "throughput_mbps": throughput_sum,
                    "latency_max": max_latency,
                    "segment_loss_rate_weighted": weighted_loss
                })

                last_record = time.time()

            time.sleep(0.05)

        except Exception as e:
            print(f"Error: {e}")
            break

    sock.close()
    df = pd.DataFrame(metrics_log)
    df.to_csv(args.csv, index=False)
    print(f"✅ Metrics saved to {args.csv}")

if __name__ == "__main__":
    main()
