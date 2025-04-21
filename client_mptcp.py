
#!/usr/bin/env python3

import socket
import signal
import time
import random
import numpy as np
import mpsched
import pandas as pd
import sys
import subprocess
import argparse
import matplotlib.pyplot as plt

BUFFER_SIZE = 1024
PERF_RECORD_INTERVAL = 1.0
keep_running = True

def signal_handler(sig, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def create_mptcp_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
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

def set_scheduler(scheduler_name):
    subprocess.run(["sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)

def run_test(server_ip, port, scheduler, duration=10):
    set_scheduler(scheduler)
    time.sleep(1)

    sock = create_mptcp_socket()
    connect_socket(sock, server_ip, port)
    print(f"[{scheduler}] Connected to {server_ip}:{port}")

    total_sent = 0
    total_recv = 0
    start_time = time.time()
    last_record = start_time
    metrics_log = []
    fd = sock.fileno()
    buffer = generate_buffer()

    while keep_running and (time.time() - start_time < duration):
        try:
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
                    "time": time.time() - start_time,
                    "throughput_total": throughput,
                    "latency_max": latency,
                    "segment_loss_rate_weighted": loss_rate
                })
                last_record = time.time()

            time.sleep(0.05)
        except Exception as e:
            print(f"[{scheduler}] Error: {e}")
            break

    sock.close()
    df = pd.DataFrame(metrics_log)
    filename = f"metrics_{scheduler}.csv"
    df.to_csv(filename, index=False)
    print(f"[{scheduler}] Saved to {filename}")
    return filename

def plot_metrics(csv_files):
    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = csv.split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["throughput_total"], label=f"{scheduler} - throughput")
    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (sum of subflows)")
    plt.title("MPTCP Scheduler Comparison - Throughput")
    plt.legend()
    plt.grid()
    plt.savefig("plot_throughput.png")

    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = csv.split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["latency_max"], label=f"{scheduler} - max latency")
    plt.xlabel("Time (s)")
    plt.ylabel("Max Latency (ms)")
    plt.title("MPTCP Scheduler Comparison - Max Latency")
    plt.legend()
    plt.grid()
    plt.savefig("plot_latency.png")

    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = csv.split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["segment_loss_rate_weighted"], label=f"{scheduler} - loss rate")
    plt.xlabel("Time (s)")
    plt.ylabel("Weighted Segment Loss Rate")
    plt.title("MPTCP Scheduler Comparison - Loss Rate")
    plt.legend()
    plt.grid()
    plt.savefig("plot_lossrate.png")

    print("Plots saved: plot_throughput.png, plot_latency.png, plot_lossrate.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="Server IP")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--schedulers", nargs="+", required=True, help="Schedulers to test")
    parser.add_argument("--duration", type=int, default=10, help="Test duration per scheduler (s)")
    args = parser.parse_args()

    csvs = []
    for sched in args.schedulers:
        print(f"🧪 Testing scheduler: {sched}")
        csv_file = run_test(args.ip, args.port, sched, args.duration)
        csvs.append(csv_file)

    plot_metrics(csvs)

if __name__ == "__main__":
    main()
