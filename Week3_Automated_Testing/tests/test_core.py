"""
tests/test_core.py
-------------------
Automated test suite for the `inventory` module.

Organized into:
  - Unit tests for each pure function (compute_item_value, apply_bulk_discount,
    find_low_stock, average_price) -- no file I/O involved.
  - Unit tests for the I/O functions (read_inventory, write_report), using
    pytest's `tmp_path` fixture so tests never touch real files on disk
    outside of a temp directory that pytest cleans up automatically.
  - An integration test for run_report(), which exercises the full
    read -> compute -> write pipeline end to end.

See TESTING.md for the rationale behind each test case and how it maps
to the module's functionality.
"""

import pytest

from inventory import (
    InventoryError,
    average_price,
    apply_bulk_discount,
    compute_item_value,
    find_low_stock,
    read_inventory,
    run_report,
    write_report,
)
from inventory.core import main


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_items():
    """A small, representative inventory: mixes high/low quantity and price."""
    return [
        {"name": "Widget A", "quantity": "120", "price": "2.50"},
        {"name": "Widget B", "quantity": "8", "price": "15.00"},
        {"name": "Widget C", "quantity": "3", "price": "7.25"},
        {"name": "Widget D", "quantity": "60", "price": "1.20"},
        {"name": "Widget E", "quantity": "4", "price": "9.99"},
    ]


def write_csv(path, rows):
    """Helper: write a list of dict rows to a CSV file at `path`."""
    import csv
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "quantity", "price"])
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# compute_item_value
# ---------------------------------------------------------------------------

class TestComputeItemValue:
    def test_basic_multiplication(self):
        item = {"name": "X", "quantity": "10", "price": "2.50"}
        assert compute_item_value(item) == 25.0

    def test_zero_quantity_gives_zero_value(self):
        item = {"name": "X", "quantity": "0", "price": "99.99"}
        assert compute_item_value(item) == 0.0

    def test_decimal_price_is_handled_precisely_enough(self):
        item = {"name": "X", "quantity": "3", "price": "0.1"}
        assert compute_item_value(item) == pytest.approx(0.3)

    def test_string_fields_are_converted_not_concatenated(self):
        # Regression test for the Week 2 bug: "10" * "2.5" used to raise
        # TypeError because both fields stayed as strings.
        item = {"name": "X", "quantity": "10", "price": "2.5"}
        result = compute_item_value(item)
        assert isinstance(result, float)
        assert result == 25.0


# ---------------------------------------------------------------------------
# apply_bulk_discount
# ---------------------------------------------------------------------------

class TestApplyBulkDiscount:
    def test_no_discount_below_threshold(self):
        items = [{"name": "A", "quantity": "10", "price": "5.00"}]
        result = apply_bulk_discount(items, threshold=50, discount=0.10)
        assert result == [("A", 50.0)]

    def test_discount_applied_above_threshold(self):
        items = [{"name": "A", "quantity": "100", "price": "1.00"}]
        result = apply_bulk_discount(items, threshold=50, discount=0.10)
        # 100 * 1.00 = 100, minus 10% = 90.0
        assert result == [("A", 90.0)]

    def test_boundary_quantity_exactly_at_threshold_gets_no_discount(self):
        # threshold uses a strict ">" comparison, so qty == threshold
        # should NOT receive a discount.
        items = [{"name": "A", "quantity": "50", "price": "2.00"}]
        result = apply_bulk_discount(items, threshold=50, discount=0.10)
        assert result == [("A", 100.0)]

    def test_boundary_quantity_one_above_threshold_gets_discount(self):
        items = [{"name": "A", "quantity": "51", "price": "2.00"}]
        result = apply_bulk_discount(items, threshold=50, discount=0.10)
        assert result == [("A", pytest.approx(91.8))]  # 102 - 10%

    def test_empty_items_returns_empty_list(self):
        assert apply_bulk_discount([]) == []

    def test_custom_threshold_and_discount(self):
        items = [{"name": "A", "quantity": "5", "price": "10.00"}]
        result = apply_bulk_discount(items, threshold=1, discount=0.50)
        assert result == [("A", 25.0)]  # 50 - 50%

    def test_repeated_calls_do_not_accumulate_stale_results(self):
        # Regression test for the Week 2 mutable-default-argument bug:
        # apply_bulk_discount(report=[]) used to leak state across calls.
        items = [{"name": "A", "quantity": "10", "price": "1.00"}]
        first_call = apply_bulk_discount(items)
        second_call = apply_bulk_discount(items)
        assert len(first_call) == 1
        assert len(second_call) == 1


# ---------------------------------------------------------------------------
# find_low_stock
# ---------------------------------------------------------------------------

class TestFindLowStock:
    def test_flags_items_below_threshold(self, sample_items):
        result = find_low_stock(sample_items, min_qty=5)
        assert result == ["Widget C", "Widget E"]

    def test_boundary_quantity_exactly_at_min_qty_is_included(self):
        # Comparison is "<=", so an item exactly at min_qty should count
        # as low stock, not be excluded.
        items = [{"name": "A", "quantity": "5", "price": "1.00"}]
        assert find_low_stock(items, min_qty=5) == ["A"]

    def test_no_low_stock_items_returns_empty_list(self):
        items = [{"name": "A", "quantity": "100", "price": "1.00"}]
        assert find_low_stock(items, min_qty=5) == []

    def test_empty_items_list(self):
        assert find_low_stock([]) == []

    def test_last_item_in_list_is_included(self):
        # Regression test for the Week 2 off-by-one bug: the old
        # `range(len(items) - 1)` loop silently skipped the last item.
        items = [
            {"name": "First", "quantity": "1", "price": "1.00"},
            {"name": "Last", "quantity": "1", "price": "1.00"},
        ]
        result = find_low_stock(items, min_qty=5)
        assert "Last" in result


# ---------------------------------------------------------------------------
# average_price
# ---------------------------------------------------------------------------

class TestAveragePrice:
    def test_average_of_multiple_items(self):
        items = [
            {"name": "A", "quantity": "1", "price": "10.00"},
            {"name": "B", "quantity": "1", "price": "20.00"},
        ]
        assert average_price(items) == 15.0

    def test_single_item(self):
        items = [{"name": "A", "quantity": "1", "price": "7.50"}]
        assert average_price(items) == 7.5

    def test_empty_list_returns_zero_not_error(self):
        # Regression test for the Week 2 ZeroDivisionError bug.
        assert average_price([]) == 0.0


# ---------------------------------------------------------------------------
# read_inventory (file I/O)
# ---------------------------------------------------------------------------

class TestReadInventory:
    def test_reads_valid_csv_into_list_of_dicts(self, tmp_path, sample_items):
        csv_path = tmp_path / "inventory.csv"
        write_csv(csv_path, sample_items)

        result = read_inventory(str(csv_path))

        assert len(result) == 5
        assert result[0]["name"] == "Widget A"
        assert result[0]["quantity"] == "120"  # still a string at this stage

    def test_missing_file_raises_inventory_error(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.csv"
        with pytest.raises(InventoryError, match="not found"):
            read_inventory(str(missing_path))

    def test_other_os_error_wrapped_as_inventory_error(self, tmp_path, monkeypatch):
        # Simulates a permission-denied style failure that isn't a plain
        # FileNotFoundError, to exercise the generic OSError branch.
        csv_path = tmp_path / "inventory.csv"
        csv_path.write_text("name,quantity,price\nA,1,1.0\n")

        real_open = open

        def failing_open(path, *args, **kwargs):
            if str(path) == str(csv_path):
                raise PermissionError("simulated permission denied")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", failing_open)

        with pytest.raises(InventoryError, match="Could not read inventory file"):
            read_inventory(str(csv_path))

    def test_header_only_file_raises_inventory_error(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        write_csv(csv_path, [])  # header row only, no data rows

        with pytest.raises(InventoryError, match="no data rows"):
            read_inventory(str(csv_path))

    def test_row_missing_expected_column_raises_key_error(self, tmp_path):
        # Documents current behavior: read_inventory() does not validate
        # column presence itself; a missing column surfaces as a KeyError
        # downstream (e.g. in compute_item_value) rather than being caught
        # here. This test locks in that known, documented limitation so
        # a future change to add column validation is a deliberate choice,
        # not an accidental regression.
        csv_path = tmp_path / "bad_columns.csv"
        csv_path.write_text("name,quantity\nWidget X,10\n")  # no "price" column

        rows = read_inventory(str(csv_path))
        with pytest.raises(KeyError):
            compute_item_value(rows[0])


# ---------------------------------------------------------------------------
# write_report (file I/O)
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_writes_expected_content(self, tmp_path):
        report_path = tmp_path / "report.txt"
        write_report(
            str(report_path),
            discounted=[("Widget A", 270.0)],
            low_stock=["Widget C"],
            avg_price=7.19,
        )

        content = report_path.read_text()
        assert "Average unit price: $7.19" in content
        assert "Widget A: $270.00" in content
        assert "Widget C" in content

    def test_writes_none_marker_when_no_low_stock(self, tmp_path):
        report_path = tmp_path / "report.txt"
        write_report(str(report_path), discounted=[], low_stock=[], avg_price=0.0)

        content = report_path.read_text()
        assert "(none)" in content

    def test_invalid_path_raises_inventory_error(self, tmp_path):
        bad_path = tmp_path / "no_such_dir" / "report.txt"
        with pytest.raises(InventoryError, match="Could not write report"):
            write_report(str(bad_path), discounted=[], low_stock=[], avg_price=0.0)


# ---------------------------------------------------------------------------
# run_report (integration test: full pipeline)
# ---------------------------------------------------------------------------

class TestRunReportIntegration:
    def test_end_to_end_pipeline(self, tmp_path, sample_items):
        csv_path = tmp_path / "inventory.csv"
        report_path = tmp_path / "report.txt"
        write_csv(csv_path, sample_items)

        result = run_report(str(csv_path), str(report_path))

        # Return value reflects the computed data...
        assert result["low_stock"] == ["Widget C", "Widget E"]
        assert result["average_price"] == pytest.approx(7.188, abs=0.01)
        names = [name for name, _ in result["discounted"]]
        assert names == ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"]

        # ...and the report file on disk matches it.
        assert report_path.exists()
        content = report_path.read_text()
        assert "Widget E" in content  # confirms Bug 4 (off-by-one) stays fixed

    def test_missing_input_file_raises_inventory_error(self, tmp_path):
        with pytest.raises(InventoryError):
            run_report(str(tmp_path / "missing.csv"), str(tmp_path / "report.txt"))


# ---------------------------------------------------------------------------
# main() CLI entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    def test_main_prints_success_message_on_valid_run(
        self, tmp_path, monkeypatch, capsys, sample_items
    ):
        monkeypatch.chdir(tmp_path)
        write_csv(tmp_path / "inventory.csv", sample_items)

        exit_code = main()

        assert exit_code == 0
        assert "Report generated: report.txt" in capsys.readouterr().out
        assert (tmp_path / "report.txt").exists()

    def test_main_prints_error_and_nonzero_exit_on_missing_input(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)  # no inventory.csv created here

        exit_code = main()

        assert exit_code == 1
        assert "Error:" in capsys.readouterr().err
