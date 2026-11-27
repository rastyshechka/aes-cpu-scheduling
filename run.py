import argparse
import csv
import json
from collections import deque
from math import expm1
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

DT, DURATION = 0.01, 120
TIME = np.arange(round(DURATION / DT)) * DT
SCENARIOS = (
    ("steady_load", "Steady load", 25.0),
    ("bursty_spikes", "Bursty spikes", np.where((TIME % 30 >= 5) & (TIME % 30 < 17), 65.0, 9.0)),
    ("sustained_overload", "Sustained overload", 49.0),
)
POLICIES = (("Reactive DVFS", "reactive_dvfs", "#b64916"), ("AES", "endocrine", "#12658a"))
TELEMETRY = (
    "time_s", "temperature_c", "frequency_ghz", "power_w", "utilization", "fatigue",
    "arrivals", "tasks_completed", "tasks_outstanding", "completed_queue_waits_ms",
)

def power(clock, utilization):
    return 12.0 + 45.0 * utilization * (0.28 + 0.18 * clock)**2 * clock

def aes_clock(temp, fatigue):
    weight = -expm1(-4.5 / 6.25)
    budget = (77.0 - (1.0 - weight) * temp - weight * 25.0) / (weight * 0.50)
    if power(4.0, fatigue) <= budget:
        return 4.0
    low, high = 2.0, 4.0
    for _ in range(18):
        trial = (low + high) / 2
        if power(trial, fatigue) <= budget:
            low = trial
        else:
            high = trial
    return low

def workload(rate, seed):
    rng = np.random.default_rng(seed)
    counts = rng.poisson(rate * DT, size=len(TIME))
    return np.split(rng.uniform(0.04, 0.116, size=counts.sum()), counts.cumsum()[:-1])

def simulate(tasks, aes):
    queue = deque()
    temp, fatigue, clock, throttled = 25.0, 0.0, 4.0, False
    temps, clocks, waits, raw = [temp], [], [], []
    thermal_weight, clock_weight = -expm1(-DT / 6.25), -expm1(-DT / 0.20)
    for start, batch in zip(TIME, tasks):
        if aes:
            clock += clock_weight * (aes_clock(temp, fatigue) - clock)
        else:
            if temp >= 95:
                throttled = True
            elif temp < 85:
                throttled = False
            clock = 2.0 if throttled else 4.0

        queue.extend([size, start, None] for size in batch)
        capacity = available = clock * DT
        finished = []
        while queue and available > 0:
            task = queue[0]
            if task[2] is None:
                task[2] = (start - task[1] + (capacity - available) / clock) * 1000
            served = min(available, task[0])
            task[0] -= served
            available -= served
            if task[0] == 0:
                finished.append(queue.popleft()[2])

        utilization = (capacity - available) / capacity
        watts = power(clock, utilization)
        temp += thermal_weight * (25.0 + 0.50 * watts - temp)
        if aes:
            response = 1.50 if utilization > fatigue else 1.80
            fatigue += -expm1(-DT / response) * (utilization - fatigue)
        temps.append(temp)
        clocks.append(clock)
        waits.extend(finished)
        raw.append((start + DT, temp, clock, watts, utilization, fatigue if aes else "",
                    len(batch), len(finished), len(queue), json.dumps(finished)))

    p95, p99 = np.percentile(waits, [95, 99]) if waits else (np.nan, np.nan)
    return temps, clocks, raw, {
        "peak_temp_c": max(temps),
        "time_above_90c_pct": 100 * np.mean(np.asarray(temps[1:]) >= 90),
        "mean_freq_ghz": np.mean(clocks),
        "freq_std_ghz": np.std(clocks),
        "mean_abs_freq_delta_ghz": np.abs(np.diff(clocks)).mean(),
        "mean_queue_latency_ms": np.mean(waits) if waits else np.nan,
        "p95_queue_latency_ms": p95,
        "p99_queue_latency_ms": p99,
        "tasks_completed": len(waits),
        "tasks_arrived": sum(map(len, tasks)),
        "tasks_unfinished": len(queue),
    }

def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def sensitivity():
    for scenario, _, rate in SCENARIOS:
        for seed in (*range(10), 42):
            tasks = workload(rate, seed)
            for policy, suffix, _ in POLICIES:
                _, _, _, stats = simulate(tasks, suffix == "endocrine")
                yield dict(scenario=scenario, seed=seed, scheduler=policy, **stats)

def experiment(results):
    fig, axes = plt.subplots(3, 2, figsize=(10, 6.5), sharex=True, layout="constrained")
    edges, summary = np.append(TIME, DURATION), []
    for (scenario, label, rate), (temp_ax, freq_ax) in zip(SCENARIOS, axes):
        tasks = workload(rate, 42)
        for policy, suffix, color in POLICIES:
            temp, clock, raw, stats = simulate(tasks, suffix == "endocrine")
            write_csv(results / f"raw_{scenario}_{suffix}.csv", TELEMETRY, raw)
            summary.append(dict(scenario=scenario, scheduler=policy, **stats))
            temp_ax.plot(edges, temp, color=color, label=policy)
            freq_ax.stairs(clock, edges, baseline=None, color=color, label=policy)
        temp_ax.axhline(95.0, color="0.4", linestyle="--", label="95°C limit")
        temp_ax.set(title=label, ylabel="Temperature (°C)", ylim=(20, 101))
        freq_ax.set(title=label, ylabel="Frequency (GHz)", ylim=(1.8, 4.2))
        for axis in (temp_ax, freq_ax):
            axis.grid(alpha=0.25)
            axis.set_xlim(0, DURATION)
    for axis in axes[0]:
        axis.legend(loc="lower right", fontsize=8)
    for axis in axes[-1]:
        axis.set_xlabel("Time (s)")
    fig.canvas.manager.set_window_title("CPU scheduling | Reactive DVFS vs AES")
    return fig, summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensitivity", action="store_true", help="Run the 11-seed check.")
    args = parser.parse_args()
    results = Path(__file__).resolve().parent / "results"
    results.mkdir(exist_ok=True)
    if args.sensitivity:
        rows = list(sensitivity())
        write_csv(results / "seed_sensitivity.csv", rows[0].keys(), (row.values() for row in rows))
        return
    fig, rows = experiment(results)
    write_csv(results / "summary_metrics.csv", rows[0].keys(), (row.values() for row in rows))
    for row in rows:
        print(
            f"{row['scenario']:20} {row['scheduler']:14} "
            f"peak {row['peak_temp_c']:6.2f} C | "
            f"mean wait {row['mean_queue_latency_ms']:8.2f} ms | "
            f"completed {row['tasks_completed']}/{row['tasks_arrived']}"
        )
    plt.show()
    plt.close(fig)

if __name__ == "__main__":
    main()
