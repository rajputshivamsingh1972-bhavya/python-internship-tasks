#!/usr/bin/env python3
"""
inventory_report.py (CORRECTED VERSION)

Reads a small inventory CSV file, computes the value of stock on hand,
applies a bulk discount to high-quantity items, flags low-stock items,
and writes a summary report to a text file.

See debug_log.md for the full list of bugs found in the original version
of this script, how each was reproduced, and why each fix works.
"""

import csv
import sys


class InventoryError(Exception):
    """Raised for problems reading or processing inventory data."""


def read_inventory(filepath):
    """
    Read inventory rows from a CSV file into a list of dicts.

    Fix: uses a `with` block so the file handle is always closed, even if
    reading raises an exception partway through. Also wraps the file-not-
    found case in a clear, specific InventoryError instead of letting a
    raw FileNotFoundError propagate with a less helpful message.
    """
    try:
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        raise InventoryError(f"Inventory file not found: '{filepath}'")
    except OSError as exc:
        raise InventoryError(f"Could not read inventory file '{filepath}': {exc}")

    if not rows:
        raise InventoryError(f"Inventory file '{filepath}' contains no data rows.")
    return rows


def compute_item_value(item):
    """
    Return quantity * price for a single inventory item.

    Fix: explicitly converts the CSV string fields to numeric types before
    multiplying. csv.DictReader always returns strings, so `"120" * "2.50"`
    is invalid; `int("120") * float("2.50")` is what was intended.
    """
    quantity = int(item["quantity"])
    price = float(item["price"])
    return quantity * price


def apply_bulk_discount(items, threshold=50, discount=0.10):
    """
    Return a list of (name, value) tuples, applying a bulk discount to
    items whose quantity exceeds `threshold`.

    Fix: removed the mutable default argument (`report=[]`). A fresh list
    is created inside the function body on every call instead, so
    repeated calls in the same program run no longer accumulate stale
    results from previous calls.
    """
    report = []
    for item in items:
        value = compute_item_value(item)
        qty = int(item["quantity"])
        if qty > threshold:
            value -= value * discount
        report.append((item["name"], value))
    return report


def find_low_stock(items, min_qty=5):
    """
    Return names of items at or below the low-stock threshold.

    Fix: loop now runs over range(len(items)), not range(len(items) - 1),
    so the last item in the inventory is no longer silently skipped.
    (Rewritten as a plain `for item in items` loop, which is both clearer
    and immune to this class of off-by-one error entirely.)
    """
    return [item["name"] for item in items if int(item["quantity"]) <= min_qty]


def average_price(items):
    """
    Return the average unit price across all items.

    Fix: guards against an empty item list. read_inventory() already
    raises InventoryError on an empty file, so in practice `items` is
    never empty by the time this runs -- but this function is kept
    defensive so it behaves correctly even if called independently
    (e.g. from a unit test) with an empty list.
    """
    if not items:
        return 0.0
    total = sum(float(item["price"]) for item in items)
    return total / len(items)


def write_report(filepath, discounted, low_stock, avg_price):
    """
    Write the summary report to disk.

    Fix: replaced the bare `except: pass` with a specific `except OSError`
    that re-raises as InventoryError with a clear message, so failures
    (permission denied, disk full, bad path) are visible to the caller
    instead of being silently discarded.
    """
    try:
        with open(filepath, "w") as f:
            f.write("=== Inventory Report ===\n\n")
            f.write(f"Average unit price: ${avg_price:.2f}\n\n")
            f.write("Item values (after any bulk discount):\n")
            for name, value in discounted:
                f.write(f"  {name}: ${value:.2f}\n")
            f.write("\nLow stock items:\n")
            if low_stock:
                for name in low_stock:
                    f.write(f"  {name}\n")
            else:
                f.write("  (none)\n")
    except OSError as exc:
        raise InventoryError(f"Could not write report to '{filepath}': {exc}")


def main():
    try:
        items = read_inventory("inventory.csv")
        discounted = apply_bulk_discount(items)
        low_stock = find_low_stock(items)
        avg = average_price(items)
        write_report("report.txt", discounted, low_stock, avg)
    except InventoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Report generated: report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
