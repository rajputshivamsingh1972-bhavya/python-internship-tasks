#!/usr/bin/env python3
"""
baseline.py
-----------
BASELINE (unoptimized) version of an inventory analytics tool.

Given a large inventory CSV, this computes:
  1. Duplicate item names (same name appearing more than once)
  2. Total value per category
  3. The top 10 most valuable items
  4. A formatted text report of all of the above

This version is written the way a first draft often is -- correct, but
with several performance anti-patterns left in. Week4_Report.md documents
each bottleneck, how it was found via profiling, and how it was fixed in
optimized.py.
"""

import csv
import sys
import time


def load_items(filepath):
    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_duplicates(items):
    """
    Return the set of item names that appear more than once.

    BOTTLENECK 1: uses a plain list (`seen`) and checks membership with
    `in`, which is an O(n) scan on a list. Doing this once per item
    makes the whole function O(n^2) -- on 20,000 rows that's ~400
    million comparisons in the worst case.
    """
    seen = []
    duplicates = []
    for item in items:
        name = item["name"]
        if name in seen:                 # O(n) list scan, called n times
            if name not in duplicates:    # another O(n) list scan
                duplicates.append(name)
        else:
            seen.append(name)
    return duplicates


def compute_category_totals(items):
    """
    Return total inventory value per category.

    BOTTLENECK 2: for every category, this re-scans the ENTIRE item
    list from scratch to sum up that category's value. With C
    categories and n items, that's O(C * n) work instead of a single
    O(n) pass.
    """
    categories = set(item["category"] for item in items)
    totals = {}
    for category in categories:
        total = 0.0
        for item in items:                # full re-scan per category
            if item["category"] == category:
                total += int(item["quantity"]) * float(item["price"])
        totals[category] = total
    return totals


def top_n_by_value(items, n=10):
    """
    Return the n most valuable items (by quantity * price).

    BOTTLENECK 3: computes each item's value freshly every time it's
    compared (recomputed inside the sort key function on every
    comparison Timsort makes), and sorts the ENTIRE list just to get
    the top 10 -- an O(n log n) full sort when an O(n) partial
    selection (heapq.nlargest) would do.
    """
    def value_of(item):
        # Recomputed on every comparison during sort -- redundant work.
        return int(item["quantity"]) * float(item["price"])

    sorted_items = sorted(items, key=value_of, reverse=True)
    return [(item["name"], value_of(item)) for item in sorted_items[:n]]


def build_report(duplicates, category_totals, top_items):
    """
    Build the report text.

    BOTTLENECK 4: builds the report with repeated string concatenation
    (`report += ...`) inside loops. Because strings are immutable in
    Python, each `+=` allocates an entirely new string and copies
    everything built so far into it -- making this loop O(n^2) in the
    total report length instead of O(n).
    """
    report = "=== Inventory Analytics Report ===\n\n"

    report += f"Duplicate item names found: {len(duplicates)}\n"
    for name in duplicates:                   # string += in a loop
        report += f"  - {name}\n"

    report += "\nTotal value by category:\n"
    for category, total in category_totals.items():
        report += f"  {category}: ${total:,.2f}\n"   # string += in a loop

    report += "\nTop 10 most valuable items:\n"
    for name, value in top_items:
        report += f"  {name}: ${value:,.2f}\n"        # string += in a loop

    return report


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
    output_path = sys.argv[2] if len(sys.argv) > 2 else "baseline_report.txt"

    start = time.perf_counter()
    result = run(input_path, output_path)
    elapsed = time.perf_counter() - start

    print(f"Processed {result['num_items']} items in {elapsed:.3f}s")
    print(f"Found {result['num_duplicates']} duplicate names")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
