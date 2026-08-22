"""
inventory/core.py
------------------
Core logic for the inventory reporting module.

Testability changes from the Week 2 version (inventory_report_fixed.py):

1. `main()` has been replaced with `run_report(input_path, output_path)`,
   which takes its file paths as arguments instead of hardcoding
   "inventory.csv" / "report.txt". This means tests can point it at a
   temporary file (via pytest's `tmp_path` fixture) instead of having to
   fake or monkeypatch the current working directory.
2. `apply_bulk_discount()` and `find_low_stock()` accept their thresholds
   as parameters (already true in the Week 2 fix) so boundary conditions
   can be tested directly without needing to construct inventories of
   specific sizes.
3. Every function still does exactly one thing and returns a plain value
   (no printing, no global state), so each can be tested completely in
   isolation with plain input -> output assertions.
"""

import csv
import sys


class InventoryError(Exception):
    """Raised for problems reading, processing, or writing inventory data."""


def read_inventory(filepath):
    """Read inventory rows from a CSV file into a list of dicts."""
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
    """Return quantity * price for a single inventory item (dict of strings)."""
    quantity = int(item["quantity"])
    price = float(item["price"])
    return quantity * price


def apply_bulk_discount(items, threshold=50, discount=0.10):
    """
    Return a list of (name, value) tuples, applying `discount` to any
    item whose quantity is strictly greater than `threshold`.
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
    """Return names of items whose quantity is <= min_qty."""
    return [item["name"] for item in items if int(item["quantity"]) <= min_qty]


def average_price(items):
    """Return the average unit price across all items, or 0.0 if empty."""
    if not items:
        return 0.0
    total = sum(float(item["price"]) for item in items)
    return total / len(items)


def write_report(filepath, discounted, low_stock, avg_price):
    """Write the summary report to disk."""
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


def run_report(input_path="inventory.csv", output_path="report.txt"):
    """
    Run the full pipeline: read inventory, compute values, write report.

    Returns the report's underlying data (discounted values, low stock
    list, average price) so callers -- including tests -- can make
    assertions without needing to re-parse the written report file.
    """
    items = read_inventory(input_path)
    discounted = apply_bulk_discount(items)
    low_stock = find_low_stock(items)
    avg = average_price(items)
    write_report(output_path, discounted, low_stock, avg)
    return {"discounted": discounted, "low_stock": low_stock, "average_price": avg}


def main():
    """CLI entry point."""
    try:
        run_report("inventory.csv", "report.txt")
    except InventoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Report generated: report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
