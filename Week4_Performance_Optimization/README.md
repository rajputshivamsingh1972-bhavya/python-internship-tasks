# Week 4 — Performance Optimization in Python Applications

## What this is

An inventory analytics tool (duplicate detection, category totals,
top-10 valuable items, text report) built in two versions:

- `baseline.py` — a correct but deliberately unoptimized first draft
- `optimized.py` — the same functionality, with every profiled
  bottleneck fixed

Full profiling data, before/after code for each bottleneck, and
benchmark results are in **`Week4_Report.md`** — start there.

## Files

```
generate_data.py     - generates a synthetic inventory CSV (reproducible, seeded)
baseline.py           - unoptimized version
optimized.py           - optimized version
benchmark.py           - timeit-based before/after benchmark across dataset sizes
Week4_Report.md        - full profiling analysis and results (the main report)
```

## How to reproduce

```bash
# Generate a test dataset (30,000 rows)
python3 generate_data.py 30000 large_inventory.csv

# Run either version
python3 baseline.py large_inventory.csv baseline_report.txt
python3 optimized.py large_inventory.csv optimized_report.txt

# Profile either version
python3 -m cProfile -s cumulative baseline.py large_inventory.csv baseline_report.txt

# Run the full before/after benchmark across multiple sizes
# (regenerate inv_5000.csv / inv_10000.csv / inv_20000.csv / inv_30000.csv first,
#  or edit benchmark.py's SIZES list to match whatever CSVs you have)
python3 benchmark.py
```

## Result

**~57x faster** on a 30,000-row dataset (3.38s → 0.06s), with identical
output verified between both versions. See `Week4_Report.md` Section 5
for the full scaling table — the speedup grows with dataset size
because the core fix was algorithmic (O(n²) → O(n)), not just a
constant-factor tweak.
