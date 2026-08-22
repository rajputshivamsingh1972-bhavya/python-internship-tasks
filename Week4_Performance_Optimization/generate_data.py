#!/usr/bin/env python3
"""
generate_data.py
----------------
Generates a synthetic inventory CSV large enough to expose real
performance differences between the baseline and optimized
implementations. Includes deliberate duplicate rows (by name) so the
duplicate-detection bottleneck can be exercised meaningfully.

Usage:
    python3 generate_data.py [num_rows] [output_path]
"""

import csv
import random
import sys

CATEGORIES = [f"Category-{i:03d}" for i in range(60)]


def generate(num_rows: int, output_path: str, duplicate_rate: float = 0.15) -> None:
    random.seed(42)  # reproducible dataset across runs
    rows = []
    names_used = []

    for i in range(num_rows):
        # Occasionally re-emit a previously used name to create a real
        # duplicate (by name) -- this is what the duplicate-detection
        # bottleneck actually has to find.
        if names_used and random.random() < duplicate_rate:
            name = random.choice(names_used)
        else:
            name = f"Item-{i:07d}"
            names_used.append(name)

        rows.append(
            {
                "name": name,
                "category": random.choice(CATEGORIES),
                "quantity": random.randint(0, 500),
                "price": round(random.uniform(0.5, 500.0), 2),
            }
        )

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "category", "quantity", "price"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {num_rows} rows -> {output_path}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    out = sys.argv[2] if len(sys.argv) > 2 else "large_inventory.csv"
    generate(n, out)
