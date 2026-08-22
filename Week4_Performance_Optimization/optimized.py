#!/usr/bin/env python3
"""
optimized.py
------------
OPTIMIZED version of the inventory analytics tool. Produces identical
results to baseline.py, but with each profiled bottleneck addressed.
See Week4_Report.md for the full profiling data and before/after
benchmarks behind each change.

Summary of changes:
  1. find_duplicates:        list + `in`           -> set-based single pass
  2. compute_category_totals: re-scan per category  -> single pass with dict accumulation
  3. top_n_by_value:          full sort + recompute -> heapq.nlargest + precomputed values
  4. build_report:            string += in a loop    -> list of parts + ''.join()
"""

import csv
import heapq
import sys
import time
from collections import defaultdict


def load_items(filepath):
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_duplicates(items):
    """
    Return the set of item names that appear more than once.

    FIX: uses a `set` for membership testing instead of a list. Set
    membership (`in`) is O(1) average case (hash lookup) instead of
    O(n) (linear scan), turning the overall function from O(n^2) into
    O(n).
    """
    seen = set()
    duplicates = set()
    for item in items:
        name = item["name"]
        if name in seen:          # O(1) average case
            duplicates.add(name)  # O(1) average case
        else:
            seen.add(name)
    return sorted(duplicates)  # sorted for stable, readable report output


def compute_category_totals(items):
    """
    Return total inventory value per category.

    FIX: single pass over the item list, accumulating into a dict
    keyed by category. O(n) instead of O(C * n).
    """
    totals = defaultdict(float)
    for item in items:
        value = int(item["quantity"]) * float(item["price"])
        totals[item["category"]] += value
    return dict(totals)


def top_n_by_value(items, n=10):
    """
    Return the n most valuable items (by quantity * price).

    FIX: computes each item's value exactly once (not recomputed on
    every sort comparison), and uses heapq.nlargest, which finds the
    top n in O(n log n_small) rather than fully sorting the whole list
    in O(n log n) just to throw away everything past index n. For
    small, fixed n this is a meaningful constant-factor win and avoids
    the wasted comparisons of a full sort.
    """
    valued = [
        (item["name"], int(item["quantity"]) * float(item["price"]))
        for item in items
    ]
    return heapq.nlargest(n, valued, key=lambda pair: pair[1])


def build_report(duplicates, category_totals, top_items):
    """
    Build the report text.

    FIX: accumulates report lines in a list and joins once at the end.
    `str.join()` is guaranteed O(n) regardless of Python implementation
    (it doesn't rely on any implementation-specific in-place resize
    behavior the way repeated `+=` can), and is the standard idiom for
    building large strings incrementally in Python.
    """
    parts = ["=== Inventory Analytics Report ===\n\n"]

    parts.append(f"Duplicate item names found: {len(duplicates)}\n")
    for name in duplicates:
        parts.append(f"  - {name}\n")

    parts.append("\nTotal value by category:\n")
    for category, total in category_totals.items():
        parts.append(f"  {category}: ${total:,.2f}\n")

    parts.append("\nTop 10 most valuable items:\n")
    for name, value in top_items:
        parts.append(f"  {name}: ${value:,.2f}\n")

    return "".join(parts)


def run(input_path, output_path):
    items = load_items(input_path)
    duplicates = find_duplicates(items)
    category_totals = compute_category_totals(items)
    top_items = top_n_by_value(items, n=10)
    report = build_report(duplicates, category_totals, top_items)

    with open(output_path, "w") as f:
        f.write(report)

    return {
        "num_items": len(items),
        "num_duplicates": len(duplicates),
        "category_totals": category_totals,
        "top_items": top_items,
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "large_inventory.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "optimized_report.txt"

    start = time.perf_counter()
    result = run(input_path, output_path)
    elapsed = time.perf_counter() - start

    print(f"Processed {result['num_items']} items in {elapsed:.3f}s")
    print(f"Found {result['num_duplicates']} duplicate names")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
