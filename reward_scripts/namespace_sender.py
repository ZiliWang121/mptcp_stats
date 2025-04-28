#!/usr/bin/env python3

import socket
import time
import random
import pandas as pd
import argparse
import struct
import sys
sys.path.append(".")
import mpsched

BUFFER_SIZE = 1024
MSS = 1460
INTERVAL = 1.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)
    s.connect((args.ip, args.port))
    fd = s.fileno()
    buf = bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])

    start = time.time()
    last = start
    metrics = []
    last_subs = None

    while time.time() - start < args.duration:
        s.send(buf)
        try:
            s.recv(BUFFER_SIZE)
        except:
            pass

        if time.time() - last >= INTERVAL:
            subs = mpsched.get_sub_info(fd)
            if last_subs is not None and len(subs) == len(last_subs):
                throughput = 0
                weighted_rtt = 0
                weighted_loss = 0
                total_seg = 0
                for i in range(len(subs)):
                    seg_diff = subs[i][0] - last_subs[i][0]
                    throughput += seg_diff * MSS * 8 / 1e6
                    total_seg += subs[i][0]
                for i in range(len(subs)):
                    if subs[i][0] > 0:
                        weighted_rtt += (subs[i][0] / total_seg) * subs[i][1]
                        loss = subs[i][4] / subs[i][0] if subs[i][0] > 0 else 0
                        weighted_loss += (subs[i][0] / total_seg) * loss
                metrics.append({
                    "time": time.time() - start,
                    "throughput_mbps": throughput,
                    "latency_max": weighted_rtt,
                    "segment_loss_rate_weighted": weighted_loss
                })
            last_subs = subs
            last = time.time()

        time.sleep(0.05)

    s.close()
    pd.DataFrame(metrics).to_csv(args.output, index=False)

if __name__ == "__main__":
    main()
