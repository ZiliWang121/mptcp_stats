# === namespace_sender.py ===

#!/usr/bin/env python3

import socket
import time
import random
import pandas as pd
import sys

BUFFER_SIZE = 1024
PERF_RECORD_INTERVAL = 1.0

# Simple sender running inside ns-mptcp
def main():
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    duration = int(sys.argv[3])
    output_file = sys.argv[4]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    s.setsockopt(socket.IPPROTO_TCP, 42, 1)
    s.connect((server_ip, server_port))

    start = time.time()
    last_record = start
    metrics = []
    buf = bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])

    while time.time() - start < duration:
        try:
            s.send(buf)
            s.recv(BUFFER_SIZE)
        except Exception:
            pass

        if time.time() - last_record >= PERF_RECORD_INTERVAL:
            metrics.append({
                "time": time.time() - start,
                "throughput_mbps": 0,
                "latency_max": 0,
                "segment_loss_rate_weighted": 0
            })
            last_record = time.time()

        time.sleep(0.05)

    s.close()
    df = pd.DataFrame(metrics)
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()
