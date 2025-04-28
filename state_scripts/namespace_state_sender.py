#!/usr/bin/env python3

import socket
import time
import random
import pandas as pd
import argparse
import sys
import struct

# 加载 mpsched 模块
sys.path.append(".")
import mpsched

BUFFER_SIZE = 1024
INTERVAL = 1.0  # 每秒记录一次
MSS = 1460  # Maximum Segment Size
DEFAULT_TIMEOUT = 5  # TCP连接超时时间

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="Server IP")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--duration", type=int, required=True, help="Test duration (s)")
    parser.add_argument("--output", required=True, help="CSV output file")
    args = parser.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    s.settimeout(DEFAULT_TIMEOUT)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)  # MPTCP_ENABLED
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
            timestamp = time.time() - start

            if subs:
                for idx, sub in enumerate(subs):
                    if len(sub) >= 8:
                        metrics.append({
                            'time': timestamp,
                            'subflow': idx,
                            'segs_out': sub[0],
                            'rtt_us': sub[1],
                            'snd_cwnd': sub[2],
                            'unacked': sub[3],
                            'total_retrans': sub[4],
                            'dst_addr': sub[5],
                            'rcv_ooopack': sub[6],
                            'snd_wnd': sub[7],
                        })

            last = time.time()

        time.sleep(0.05)

    s.close()
    df = pd.DataFrame(metrics)
    df.to_csv(args.output, index=False)

if __name__ == "__main__":
    main()
