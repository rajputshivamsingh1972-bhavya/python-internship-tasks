"""
inventory package
------------------
A small, dependency-free module for reading inventory CSV data, computing
stock value with bulk discounts, flagging low-stock items, and writing a
summary report.

This module is the corrected version originally produced for the Week 2
debugging exercise, lightly refactored here to make it easier to unit
test in isolation (see core.py docstrings for what changed and why).
"""

from .core import (
    InventoryError,
    average_price,
    apply_bulk_discount,
    compute_item_value,
    find_low_stock,
    read_inventory,
    run_report,
    write_report,
)

__all__ = [
    "InventoryError",
    "average_price",
    "apply_bulk_discount",
    "compute_item_value",
    "find_low_stock",
    "read_inventory",
    "run_report",
    "write_report",
]
