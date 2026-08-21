#!/usr/bin/env python3
"""
inventory_report.py (ORIGINAL / BUGGY VERSION)

Purpose: Reads a small inventory CSV file, computes the value of stock on
hand, applies a bulk discount to high-quantity items, flags low-stock
items, and writes a summary report to a text file.

NOTE: This is the "provided" script for Week 2's debugging exercise. It
contains several intentional, realistic bugs that are identified and
fixed in debug_log.md, with the corrected version saved as
inventory_report_fixed.py.
"""

import csv


def read_inventory(filepath):
    """Read inventory rows from a CSV file into a list of dicts."""
    rows = []
    f = open(filepath, "r")          # BUG 3: file is never closed (no `with`,
    reader = csv.DictReader(f)       # no try/finally) -- leaks a file handle
    for row in reader:
        rows.append(row)
    return rows


def compute_item_value(item):
    """Return quantity * price for a single inventory item."""
    # BUG 1: values from csv.DictReader are always strings. Multiplying a
    # string by a string raises a TypeError instead of computing a value.
    return item["quantity"] * item["price"]


def apply_bulk_discount(items, threshold=50, discount=0.10, report=[]):
    # BUG 2: mutable default argument `report=[]`. Because default argument
    # objects are created ONCE at function definition time and reused on
    # every call, calling this function more than once in the same program
    # run causes old results to silently accumulate into the new call's
    # "report" list.
    for item in items:
        qty = int(item["quantity"])
        price = float(item["price"])
        value = qty * price
        if qty > threshold:
            value = value - (value * discount)
        report.append((item["name"], value))
    return report


def find_low_stock(items, min_qty=5):
    """Return names of items at or below the low-stock threshold."""
    low = []
    # BUG 4: loop goes to len(items) - 1, skipping the LAST item in the
    # list entirely (an off-by-one error from an unnecessary "- 1").
    for i in range(len(items) - 1):
        item = items[i]
        if int(item["quantity"]) <= min_qty:
            low.append(item["name"])
    return low


def average_price(items):
    """Return the average unit price across all items."""
    total = 0.0
    for item in items:
        total += float(item["price"])
    # BUG 5: no guard against an empty inventory list -- dividing by zero
    # crashes the whole program instead of failing gracefully.
    return total / len(items)


def write_report(filepath, discounted, low_stock, avg_price):
    try:
        with open(filepath, "w") as f:
            f.write("=== Inventory Report ===\n\n")
            f.write(f"Average unit price: ${avg_price:.2f}\n\n")
            f.write("Item values (after any bulk discount):\n")
            for name, value in discounted:
                f.write(f"  {name}: ${value:.2f}\n")
            f.write("\nLow stock items:\n")
            for name in low_stock:
                f.write(f"  {name}\n")
    except:
        # BUG 6: bare `except:` silently swallows every possible error
        # (including permission errors, disk-full errors, even
        # KeyboardInterrupt) and prints nothing useful, making failures
        # invisible to the user.
        pass


def main():
    items = read_inventory("inventory.csv")
    discounted = apply_bulk_discount(items)
    low_stock = find_low_stock(items)
    avg = average_price(items)
    write_report("report.txt", discounted, low_stock, avg)
    print("Report generated: report.txt")


if __name__ == "__main__":
    main()
