#!/usr/bin/env python3

import os
import subprocess
import argparse
import time
import matplotlib.pyplot as plt
import pandas as pd

NAMESPACE = "ns-mptcp"

# 切换 scheduler (root namespace)
def set_scheduler(scheduler_name):
    try:
        subprocess.run(["sudo", "sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)
        print(f"✅ Scheduler set to {scheduler_name}")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to set scheduler {scheduler_name}")
        exit(1)

# 在 namespace 运行 namespace_sender.py
def run_namespace_sender(server_ip, port, duration, csv_file):
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "namespace_sender.py",
        "--ip", server_ip,
        "--port", str(port),
        "--duration", str(duration),
        "--csv", csv_file
    ]
    subprocess.run(cmd, check=True)

# 作图
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

    print("✅ Plots saved: plot_throughput.png, plot_latency.png, plot_lossrate.png")

# main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="Server IP")
    parser.add_argument("--port", type=int, required=True, help="Server port")
    parser.add_argument("--schedulers", nargs="+", required=True, help="Schedulers to test")
    parser.add_argument("--duration", type=int, default=10, help="Test duration per scheduler (s)")
    args = parser.parse_args()

    csv_files = []
    for sched in args.schedulers:
        print(f"\n🧪 Testing scheduler: {sched}")
        set_scheduler(sched)
        csv_file = f"metrics_{sched}.csv"
        run_namespace_sender(args.ip, args.port, args.duration, csv_file)
        csv_files.append(csv_file)

    plot_metrics(csv_files)

if __name__ == "__main__":
    main()
