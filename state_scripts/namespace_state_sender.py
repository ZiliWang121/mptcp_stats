#!/usr/bin/env python3

import socket
import time
import random
import pandas as pd
import argparse
import sys
import os

# 加载 mpsched 动态库
sys.path.append(".")
import mpsched

BUFFER_SIZE = 1024
MSS = 1460
PERF_RECORD_INTERVAL = 1.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)
    s.connect((args.ip, args.port))
    fd = s.fileno()

    buf = bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])
    start = time.time()
    last_record = start

    records = []

    while time.time() - start < args.duration:
        try:
            s.send(buf)
            s.recv(BUFFER_SIZE)
        except Exception:
            pass

        now = time.time()
        if now - last_record >= PERF_RECORD_INTERVAL:
            subs = mpsched.get_sub_info(fd)
            total_throughput = 0
            total_rtt = 0
            total_cwnd = 0
            total_unacked = 0
            total_retrans = 0
            valid_flows = 0

            for sub in subs:
                if len(sub) >= 8:
                    data_segs_out = sub[0]
                    rtt_us = sub[1]
                    cwnd = sub[2]
                    unacked = sub[3]
                    total_retrans = sub[4]
                    # dst_addr = sub[5] （忽略）
                    # rcv_ooopack = sub[6]（暂不使用）
                    # snd_wnd = sub[7]（暂不使用）

                    total_throughput += data_segs_out
                    total_rtt += rtt_us
                    total_cwnd += cwnd
                    total_unacked += unacked
                    valid_flows += 1

            if valid_flows > 0:
                avg_rtt = total_rtt / valid_flows / 1000  # 转成 ms
                avg_cwnd = total_cwnd / valid_flows
                avg_unacked = total_unacked / valid_flows
            else:
                avg_rtt = 0
                avg_cwnd = 0
                avg_unacked = 0

            records.append({
                "time": now - start,
                "total_data_segs_out": total_throughput,
                "avg_rtt": avg_rtt,
                "avg_cwnd": avg_cwnd,
                "avg_unacked": avg_unacked,
                "total_retrans": total_retrans
            })

            last_record = now

        time.sleep(0.05)

    s.close()
    df = pd.DataFrame(records)
    df.to_csv(args.output, index=False)
    print(f"✅ Saved metrics to {args.output}")

if __name__ == "__main__":
    main()
