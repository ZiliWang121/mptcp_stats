#!/usr/bin/env python3

import socket
import signal
import time
import random
import subprocess
import pandas as pd
import sys
import argparse
import os
import matplotlib.pyplot as plt

BUFFER_SIZE = 1024
PERF_RECORD_INTERVAL = 1.0
keep_running = True
NAMESPACE = "ns-mptcp"  # 你的 namespace 名称

def signal_handler(sig, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def set_scheduler(scheduler_name):
    """在主空间切换 scheduler"""
    try:
        subprocess.run(["sudo", "sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)
        print(f"✅ Scheduler set to {scheduler_name} (in root namespace)")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to set scheduler {scheduler_name}, error: {e}")

def run_test_in_namespace(server_ip, port, duration, scheduler):
    """在 mptcp namespace 内实际执行 client 逻辑"""
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "-c", f'''
import socket
import time
import random
import pandas as pd

BUFFER_SIZE = {BUFFER_SIZE}
PERF_RECORD_INTERVAL = {PERF_RECORD_INTERVAL}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
s.setsockopt(socket.IPPROTO_TCP, 42, 1)
s.connect(("{server_ip}", {port}))

start_time = time.time()
last_record = start_time
total_sent = 0
total_recv = 0
metrics = []

data = bytes([random.randint(33, 126) for _ in range(BUFFER_SIZE)])

while time.time() - start_time < {duration}:
    try:
        sent = s.send(data)
        if sent <= 0:
            break
        total_sent += sent

        try:
            recv_data = s.recv(BUFFER_SIZE)
            total_recv += len(recv_data)
        except BlockingIOError:
            pass

        now = time.time()
        if now - last_record >= PERF_RECORD_INTERVAL:
            elapsed = now - last_record
            throughput = (total_sent - total_recv) * 8 / elapsed / 1e6
            metrics.append({{"time": now - start_time, "throughput_mbps": throughput}})
            last_record = now

        time.sleep(0.05)
    except Exception as e:
        print("Error during transfer:", e)
        break

s.close()
df = pd.DataFrame(metrics)
csv_name = "metrics_{scheduler}.csv"
df.to_csv(csv_name, index=False)
print(f"✅ Saved {{csv_name}}")
'''
    ]
    subprocess.run(cmd)

def plot_metrics(csv_files):
    plt.figure(figsize=(12, 6))

    for csv_file in csv_files:
        scheduler = os.path.basename(csv_file).split("_")[1].split(".")[0]
        if not os.path.exists(csv_file):
            print(f"⚠️ Warning: file {csv_file} does not exist, skipping")
            continue
        df = pd.read_csv(csv_file)
        if "throughput_mbps" not in df.columns:
            print(f"⚠️ Warning: file {csv_file} missing throughput_mbps, skipping")
            continue
        plt.plot(df["time"], df["throughput_mbps"], label=f"{scheduler}")

    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (Mbps)")
    plt.title("MPTCP Scheduler Comparison - Throughput")
    plt.legend()
    plt.grid()
    plt.savefig("plot_throughput.png")
    print("✅ Throughput plot saved as plot_throughput.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="Server IP")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--schedulers", nargs="+", required=True, help="Schedulers to test")
    parser.add_argument("--duration", type=int, default=10, help="Test duration per scheduler (s)")
    args = parser.parse_args()

    csvs = []
    for sched in args.schedulers:
        set_scheduler(sched)
        time.sleep(1)
        run_test_in_namespace(args.ip, args.port, args.duration, sched)
        csvs.append(f"metrics_{sched}.csv")

    plot_metrics(csvs)

if __name__ == "__main__":
    main()
