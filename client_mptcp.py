# === client_mptcp.py ===

#!/usr/bin/env python3

import socket
import signal
import time
import random
import numpy as np
import pandas as pd
import sys
import subprocess
import argparse
import matplotlib.pyplot as plt
import os

BUFFER_SIZE = 1024
PERF_RECORD_INTERVAL = 1.0
keep_running = True
NAMESPACE = "ns-mptcp"

# Handle Ctrl+C
def signal_handler(sig, frame):
    global keep_running
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

# Run sysctl in root namespace
def set_scheduler(scheduler_name):
    try:
        subprocess.run(["sudo", "sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)
        print(f"\n✅ Scheduler set to {scheduler_name} (in root namespace)")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to set scheduler {scheduler_name}")
        sys.exit(1)

# Actual traffic generation inside ns-mptcp
def run_in_namespace(server_ip, port, duration, csv_output):
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "namespace_sender.py", server_ip, str(port), str(duration), csv_output
    ]
    subprocess.run(cmd, check=True)

# Plot the metrics
def plot_metrics(csv_files):
    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = os.path.basename(csv).split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["throughput_mbps"], label=f"{scheduler}")
    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (Mbps)")
    plt.title("MPTCP Scheduler Comparison - Throughput")
    plt.legend()
    plt.grid()
    plt.savefig("plot_throughput.png")

    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = os.path.basename(csv).split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["latency_max"], label=f"{scheduler}")
    plt.xlabel("Time (s)")
    plt.ylabel("Max Latency (ms)")
    plt.title("MPTCP Scheduler Comparison - Max Latency")
    plt.legend()
    plt.grid()
    plt.savefig("plot_latency.png")

    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = os.path.basename(csv).split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["segment_loss_rate_weighted"], label=f"{scheduler}")
    plt.xlabel("Time (s)")
    plt.ylabel("Weighted Segment Loss Rate")
    plt.title("MPTCP Scheduler Comparison - Loss Rate")
    plt.legend()
    plt.grid()
    plt.savefig("plot_lossrate.png")

    print("\n✅ Plots saved: plot_throughput.png, plot_latency.png, plot_lossrate.png")

# Main function
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="Server IP")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--schedulers", nargs="+", required=True, help="Schedulers to test")
    parser.add_argument("--duration", type=int, default=10, help="Test duration per scheduler (s)")
    args = parser.parse_args()

    csvs = []
    for sched in args.schedulers:
        print(f"\n🧪 Testing scheduler: {sched}")
        set_scheduler(sched)
        csv_file = f"metrics_{sched}.csv"
        run_in_namespace(args.ip, args.port, args.duration, csv_file)
        csvs.append(csv_file)

    plot_metrics(csvs)

if __name__ == "__main__":
    main()
