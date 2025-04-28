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

def run_in_namespace(server_ip, port, duration, output_csv):
    cmd = [
        "sudo", "ip", "netns", "exec", NAMESPACE,
        "python3", "namespace_state_sender.py",
        "--ip", server_ip,
        "--port", str(port),
        "--duration", str(duration),
        "--output", output_csv,
    ]
    subprocess.run(cmd, check=True)

def plot_avg_rtt(csv_files):
    plt.figure(figsize=(12,6))
    for csv_file in csv_files:
        scheduler = os.path.basename(csv_file).split("_")[1].split(".")[0]
        df = pd.read_csv(csv_file)
        if 'rtt_us' in df.columns:
            df['rtt_ms'] = df['rtt_us'] / 1000
            avg_rtt = df.groupby('time')['rtt_ms'].mean()
            plt.plot(avg_rtt.index, avg_rtt.values, label=scheduler)

    plt.xlabel("Time (s)")
    plt.ylabel("Average RTT (ms)")
    plt.title("Average RTT per Scheduler")
    plt.legend()
    plt.grid()
    plt.savefig("plot_avg_rtt.png")
    print("Plot saved: plot_avg_rtt.png")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--schedulers", nargs="+", required=True)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    csv_files = []

    for scheduler in args.schedulers:
        print(f"\n🧪 Testing scheduler: {scheduler}")
        set_scheduler(scheduler)
        csv_name = f"state_{scheduler}.csv"
        run_in_namespace(args.ip, args.port, args.duration, csv_name)
        csv_files.append(csv_name)

    plot_avg_rtt(csv_files)

if __name__ == "__main__":
    main()
