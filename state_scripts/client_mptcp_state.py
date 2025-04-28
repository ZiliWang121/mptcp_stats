#!/usr/bin/env python3

import subprocess
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

NAMESPACE = "ns-mptcp"

def set_scheduler(scheduler_name):
    subprocess.run(["sudo", "sysctl", f"net.mptcp.mptcp_scheduler={scheduler_name}"], check=True)
    print(f"✅ Scheduler set to {scheduler_name}")

def run_in_namespace(server_ip, port, duration, csv_output):
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "namespace_state_sender.py",
        "--ip", server_ip,
        "--port", str(port),
        "--duration", str(duration),
        "--output", csv_output
    ]
    subprocess.run(cmd, check=True)

def plot_metrics(csv_files):
    plt.figure(figsize=(12, 6))
    for csv in csv_files:
        scheduler = os.path.basename(csv).split("_")[1].split(".")[0]
        df = pd.read_csv(csv)
        if "avg_rtt" in df.columns:
            plt.plot(df["time"], df["avg_rtt"], label=f"{scheduler}")
    plt.xlabel("Time (s)")
    plt.ylabel("Average RTT (ms)")
    plt.title("Average RTT per Scheduler")
    plt.legend()
    plt.grid()
    plt.savefig("plot_avg_rtt.png")
    print("✅ Plots saved: plot_avg_rtt.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--schedulers", nargs="+", required=True)
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()

    csvs = []
    for sched in args.schedulers:
        print(f"\n🧪 Testing scheduler: {sched}")
        set_scheduler(sched)
        csv_file = f"state_{sched}.csv"
        run_in_namespace(args.ip, args.port, args.duration, csv_file)
        csvs.append(csv_file)

    plot_metrics(csvs)

if __name__ == "__main__":
    main()
