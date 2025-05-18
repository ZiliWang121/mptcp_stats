#!/usr/bin/env python3

import argparse
import subprocess
import os
import pandas as pd
import matplotlib.pyplot as plt

NAMESPACE = "ns-mptcp"

def set_scheduler(scheduler_name):
    subprocess.run(["sudo", "sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)
    print(f"Scheduler set to {scheduler_name}")

def run_in_namespace(server_ip, port, duration, output_csv):
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "namespace_sender.py",
        "--ip", server_ip,
        "--port", str(port),
        "--duration", str(duration),
        "--output", output_csv
    ]
    subprocess.run(cmd, check=True)

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
    plt.ylabel("Weighted RTT (ms)")
    plt.title("MPTCP Scheduler Comparison - RTT")
    plt.legend()
    plt.grid()
    plt.savefig("plot_latency.png")

    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = os.path.basename(csv).split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        plt.plot(df["time"], df["segment_loss_rate_weighted"], label=f"{scheduler}")
    plt.xlabel("Time (s)")
    plt.ylabel("Weighted Loss Rate")
    plt.title("MPTCP Scheduler Comparison - Loss Rate")
    plt.legend()
    plt.grid()
    plt.savefig("plot_lossrate.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--schedulers", nargs="+", required=True)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    csvs = []
    for sched in args.schedulers:
        print(f"\nTesting scheduler: {sched}")
        set_scheduler(sched)
        csv_file = f"metrics_{sched}.csv"
        run_in_namespace(args.ip, args.port, args.duration, csv_file)
        csvs.append(csv_file)

    plot_metrics(csvs)

if __name__ == "__main__":
    main()
