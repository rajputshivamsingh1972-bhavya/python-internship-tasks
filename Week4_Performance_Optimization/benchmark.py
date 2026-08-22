#!/usr/bin/env python3
"""
benchmark.py
------------
Runs baseline.run() and optimized.run() against several dataset sizes
and reports wall-clock time for each, using timeit for repeatable,
overhead-controlled measurement. Results back the before/after table in
Week4_Report.md.
"""

import timeit

import baseline
import optimized

SIZES = [5000, 10000, 20000, 30000]


def bench(module, path, repeats=3):
    timer = timeit.Timer(lambda: module.run(path, "/tmp/_bench_report.txt"))
    times = timer.repeat(repeat=repeats, number=1)
    return min(times)  # best-of-N minimizes noise from system jitter


def main():
    print(f"{'Rows':>8} | {'Baseline (s)':>13} | {'Optimized (s)':>14} | {'Speedup':>9}")
    print("-" * 55)
    for size in SIZES:
        path = f"inv_{size}.csv"
        base_time = bench(baseline, path)
        opt_time = bench(optimized, path)
        speedup = base_time / opt_time if opt_time > 0 else float("inf")
        print(f"{size:>8} | {base_time:>13.4f} | {opt_time:>14.4f} | {speedup:>8.1f}x")


if __name__ == "__main__":
    main()
