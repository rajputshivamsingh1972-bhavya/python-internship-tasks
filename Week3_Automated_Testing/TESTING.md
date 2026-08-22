# Testing Documentation — `inventory` module

## Methodology

Tests were written **after** the module was implemented (the module
itself is the corrected version from the Week 2 debugging exercise),
but this suite was built test-first in the sense that mattered most:
every previously-identified bug from Week 2 got its own **regression
test** before anything else, so a future change can never silently
reintroduce a fixed bug. New tests were then added outward from there —
happy path, then boundaries, then error conditions — which is the same
discipline TDD encourages even when applied after the fact.

The module was structured specifically to make this possible:
- Every computation function (`compute_item_value`, `apply_bulk_discount`,
  `find_low_stock`, `average_price`) is **pure** — same input always
  produces the same output, no file access, no printing, no shared
  state. These are tested with plain input/output assertions.
- The two I/O functions (`read_inventory`, `write_report`) are isolated
  from the computation functions, so file-system behavior is tested
  only where file-system behavior actually happens.
- `run_report()` takes explicit file paths as arguments (rather than
  hardcoding filenames), so the full pipeline can be integration-tested
  against pytest's `tmp_path` fixture without touching real files.

## How to run the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

To see coverage:

```bash
pytest tests/ --cov=inventory --cov-report=term-missing
```

Current result: **31 tests, 100% pass, 99% line coverage** (the only
uncovered line is the `if __name__ == "__main__":` guard, which isn't
meaningfully testable).

## Test case reference

### `TestComputeItemValue`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_basic_multiplication` | Normal case: integer quantity × decimal price | Confirms the core calculation is correct |
| `test_zero_quantity_gives_zero_value` | Edge case: qty = 0 | Ensures no special-casing breaks on zero |
| `test_decimal_price_is_handled_precisely_enough` | Fractional price (`0.1`) | Uses `pytest.approx` to guard against float precision surprises |
| `test_string_fields_are_converted_not_concatenated` | Regression test | Locks in the Week 2 fix for the `TypeError` caused by multiplying two strings |

### `TestApplyBulkDiscount`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_no_discount_below_threshold` | qty < threshold | Confirms the "no discount" path |
| `test_discount_applied_above_threshold` | qty > threshold | Confirms the discount math |
| `test_boundary_quantity_exactly_at_threshold_gets_no_discount` | qty == threshold | The comparison is strict `>`, so this boundary is the exact line between the two behaviors and is the single highest-value test in this class |
| `test_boundary_quantity_one_above_threshold_gets_discount` | qty == threshold + 1 | Confirms the boundary flips correctly one unit past it |
| `test_empty_items_returns_empty_list` | No items | Trivial but guards against an unhandled edge case |
| `test_custom_threshold_and_discount` | Non-default parameters | Confirms the function isn't hardcoded to the default 50/10% |
| `test_repeated_calls_do_not_accumulate_stale_results` | Regression test | Locks in the Week 2 fix for the mutable-default-argument bug |

### `TestFindLowStock`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_flags_items_below_threshold` | Realistic mixed inventory | End-to-end sanity check against `sample_items` |
| `test_boundary_quantity_exactly_at_min_qty_is_included` | qty == min_qty | Comparison is `<=`, so this boundary determines inclusion vs. exclusion |
| `test_no_low_stock_items_returns_empty_list` | All items well-stocked | Confirms the function doesn't over-report |
| `test_empty_items_list` | No items | Trivial edge case |
| `test_last_item_in_list_is_included` | Regression test | Locks in the Week 2 fix for the off-by-one bug that silently dropped the last item |

### `TestAveragePrice`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_average_of_multiple_items` | Normal case | Basic correctness |
| `test_single_item` | One item | Average of one is itself |
| `test_empty_list_returns_zero_not_error` | Regression test | Locks in the Week 2 fix for the `ZeroDivisionError` bug |

### `TestReadInventory`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_reads_valid_csv_into_list_of_dicts` | Happy path | Confirms parsing produces the expected structure (and that values are still strings at this stage, since conversion happens downstream) |
| `test_missing_file_raises_inventory_error` | `FileNotFoundError` -> `InventoryError` | Confirms the specific, user-friendly error path |
| `test_other_os_error_wrapped_as_inventory_error` | Generic `OSError` (simulated permission error) | Confirms the broader I/O error branch is also caught and re-raised clearly, not just the missing-file case |
| `test_header_only_file_raises_inventory_error` | Empty data set | Confirms an "empty inventory" doesn't silently produce a blank report |
| `test_row_missing_expected_column_raises_key_error` | Malformed CSV (missing a column) | Documents a **known, deliberate limitation**: `read_inventory()` doesn't validate columns itself. This test exists so a future change to add that validation is a conscious decision, not an accidental behavior change caught by surprise |

### `TestWriteReport`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_writes_expected_content` | Happy path | Confirms the report format matches spec |
| `test_writes_none_marker_when_no_low_stock` | Empty low-stock list | Confirms the "(none)" placeholder, added during the Week 2 refactor, actually renders |
| `test_invalid_path_raises_inventory_error` | Write to a nonexistent directory | Regression test locking in the Week 2 fix for the silent `except: pass` bug |

### `TestRunReportIntegration`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_end_to_end_pipeline` | Full read -> compute -> write flow, real temp files | The only test that exercises every function together; also re-confirms the off-by-one fix by checking "Widget E" appears in the written file, not just the in-memory list |
| `test_missing_input_file_raises_inventory_error` | Pipeline halts cleanly on bad input | Confirms errors propagate up through the whole pipeline rather than being swallowed partway |

### `TestMainEntryPoint`
| Test | What it covers | Why it matters |
|------|------------------|-----------------|
| `test_main_prints_success_message_on_valid_run` | CLI wrapper, happy path | Confirms the exit code and printed message a real user would see |
| `test_main_prints_error_and_nonzero_exit_on_missing_input` | CLI wrapper, error path | Confirms failures produce a non-zero exit code (important for scripting/CI use) and a message on stderr, not a silent failure or raw traceback |

## Design note: why so many "regression tests"?

Several tests above are explicitly labeled as regression tests for bugs
found during the Week 2 debugging exercise. This is intentional: a test
suite's most valuable job is often not proving new code works, but
proving that a bug, once fixed, **stays** fixed. Each of Week 2's six
bugs has at least one test here that would fail immediately if that
specific bug were ever reintroduced.
