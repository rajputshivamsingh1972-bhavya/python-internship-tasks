# Debugging Log — `inventory_report.py`

## Subject of this exercise

The script under review, `original_buggy_script.py`, reads an inventory
CSV file (`inventory.csv`), computes stock value with bulk discounts,
flags low-stock items, and writes a summary to `report.txt`. It runs
without crashing on a quick, careless test — which is exactly what makes
it a good debugging exercise: several of its bugs are silent, and only
surface with specific inputs or repeated calls.

This log walks through the full process: initial review, bug report,
step-by-step reproduction using pdb-style isolation (calling functions
directly in a Python shell to bisect behavior), the fix for each, and
the code-quality refactor applied afterward.

---

## 1. Initial Code Review

A first read-through flagged five areas as likely trouble spots, matching
the classic risk areas for this kind of task:

- **File I/O** — `read_inventory()` opens a file with no `with` block and
  no error handling around a missing path.
- **Loops** — `find_low_stock()` uses `range(len(items) - 1)`, an
  unusual and suspicious bound.
- **Conditionals / defaults** — `apply_bulk_discount(..., report=[])`
  uses a mutable default argument, a well-known Python footgun.
- **Type handling** — CSV data is read as strings throughout, but
  `compute_item_value()` multiplies two of those string fields directly.
- **Error handling** — `write_report()` has a bare `except: pass`.

Each of these hypotheses was then confirmed or refuted by actually
running the code, rather than assumed from the read-through alone.

---

## 2. Bug Report (as found, before fixes)

### Bug 1 — `TypeError` in `compute_item_value()`
- **Where:** `compute_item_value(item)`
- **Trigger:** calling it on any row read from the CSV.
- **Observed error:**
  ```
  TypeError: can't multiply sequence by non-int of type 'str'
  ```
- **Hypothesis:** `csv.DictReader` returns every field as a `str`.
  `item["quantity"] * item["price"]` is therefore `"120" * "2.50"`,
  which Python interprets as sequence repetition (only valid with an
  int operand), not numeric multiplication.
- **Reproduction:**
  ```python
  >>> import original_buggy_script as m
  >>> items = m.read_inventory('inventory.csv')
  >>> m.compute_item_value(items[0])
  TypeError: can't multiply sequence by non-int of type 'str'
  ```

### Bug 2 — Mutable default argument accumulates stale data
- **Where:** `apply_bulk_discount(items, threshold=50, discount=0.10, report=[])`
- **Trigger:** calling `apply_bulk_discount()` more than once in the same
  process (e.g. in a test suite, or a future version of `main()` that
  regenerates a report more than once).
- **Observed behavior:** second call returns 10 entries instead of 5.
- **Hypothesis:** default argument values in Python are evaluated once,
  at function-definition time, and the same list object is reused as the
  default on every call that doesn't pass its own `report=`. Each call
  appends to the *same* list rather than starting fresh.
- **Reproduction:**
  ```python
  >>> r1 = m.apply_bulk_discount(items)
  >>> len(r1)
  5
  >>> r2 = m.apply_bulk_discount(items)
  >>> len(r2)
  10   # should be 5
  ```

### Bug 3 — Unclosed file handle in `read_inventory()`
- **Where:** `read_inventory(filepath)`
- **Trigger:** every call — the file is opened with `open()` directly and
  never explicitly closed.
- **Observed behavior:** running under `-W error::ResourceWarning`
  produces:
  ```
  ResourceWarning: unclosed file <_io.TextIOWrapper name='inventory.csv' ...>
  ```
- **Hypothesis:** no `with` block or `try/finally` means the file
  object is only closed when garbage collected — not deterministic, and
  a real resource leak under CPython reference counting is avoided only
  by luck of the interpreter's GC timing. On other Python implementations
  (or long-running processes with many calls) this leaks file descriptors.
- **Reproduction:** confirmed via `python3 -W error::ResourceWarning`
  triggering the warning as an exception during `gc.collect()`.

### Bug 4 — Off-by-one skips the last item in `find_low_stock()`
- **Where:** `for i in range(len(items) - 1):`
- **Trigger:** any inventory list — the bug always skips exactly the
  last item regardless of list size.
- **Observed behavior:** with `inventory.csv` (5 items, last item
  "Widget E" has quantity 4, below the `min_qty=5` threshold), the
  generated report's "Low stock items" section only listed "Widget C"
  and omitted "Widget E".
- **Hypothesis:** `range(len(items) - 1)` produces indices
  `0 .. len(items)-2`, one short of covering the full list. This is a
  classic off-by-one, likely introduced by conflating "last valid index"
  (`len(items) - 1`) with "loop bound" (should just be `len(items)`).
- **Reproduction:** compared `report.txt` output against a manual check
  of `inventory.csv` — Widget E (qty 4) was missing from the "Low stock"
  section despite meeting the criterion.

### Bug 5 — `ZeroDivisionError` in `average_price()`
- **Where:** `return total / len(items)`
- **Trigger:** calling `average_price([])` — an empty inventory list
  (e.g. an inventory file with only a header row and no data rows).
- **Observed error:**
  ```
  ZeroDivisionError: float division by zero
  ```
- **Hypothesis:** no guard checks for an empty list before dividing.
- **Reproduction:**
  ```python
  >>> m.average_price([])
  ZeroDivisionError: float division by zero
  ```

### Bug 6 — Silent failure in `write_report()`
- **Where:** `except: pass` in `write_report()`
- **Trigger:** any failure while writing the report — e.g. an invalid
  output path, a read-only filesystem, or a full disk.
- **Observed behavior:** calling `write_report()` with a path in a
  nonexistent directory produced **no error, no output file, and no
  indication anything went wrong** — `main()` printed
  `"Report generated: report.txt"` even though nothing was generated.
- **Hypothesis:** a bare `except:` catches every exception (including
  ones that should never be silenced, like `KeyboardInterrupt` or
  `MemoryError`) and discards it with `pass`, hiding real failures from
  the user.
- **Reproduction:**
  ```python
  >>> m.write_report('/nonexistent_dir/report.txt', discounted, low, avg)
  >>> # no exception, no file written, no error message
  ```

---

## 3. Step-by-Step Debugging & Fix Rationale

Debugging was done by isolating each function in a Python shell (the
same technique `pdb` step-execution would give you, applied at function
granularity since each bug was cleanly reproducible without needing to
step through intermediate state) — importing the buggy module directly
and calling each function with controlled inputs, which let each bug be
confirmed independently of the others before touching any code.

| Bug | Before | After | Why the fix works |
|-----|--------|-------|--------------------|
| 1 | `item["quantity"] * item["price"]` | `int(item["quantity"]) * float(item["price"])` | Converts CSV strings to actual numeric types before arithmetic. |
| 2 | `def apply_bulk_discount(items, ..., report=[]):` | `def apply_bulk_discount(items, ...):` with `report = []` created inside the function body | A fresh list is created on every call; nothing persists between calls. |
| 3 | `f = open(filepath, "r")` (never closed) | `with open(filepath, "r", newline="") as f:` | Guarantees the file is closed as soon as the block exits, even on exception. |
| 4 | `for i in range(len(items) - 1):` | `for item in items:` (list comprehension) | Iterates over every item; removes the off-by-one bound entirely by not indexing manually. |
| 5 | `return total / len(items)` | `if not items: return 0.0` guard before the division | Avoids dividing by zero on an empty list; returns a sensible default instead. |
| 6 | `except: pass` | `except OSError as exc: raise InventoryError(...)` | Catches only I/O-related failures (not everything), and surfaces them to the caller instead of hiding them. |

Two additional, related improvements were made while fixing Bug 3 and
Bug 5:
- `read_inventory()` now raises a clear `InventoryError` for a missing
  file or an empty CSV, instead of letting a raw `FileNotFoundError`
  propagate or silently producing an empty report.
- `main()` now wraps the whole pipeline in a `try/except InventoryError`
  and prints a clean, actionable error message to `stderr` with a
  non-zero exit code, instead of letting any of the above bugs crash
  with a raw traceback or fail silently.

---

## 4. Code Optimization / Refactoring

Beyond the direct bug fixes, the following readability and structure
improvements were made without changing intended behavior:

- Introduced a single `InventoryError` exception type so all
  inventory-related failures (bad file, empty file, write failure) are
  handled consistently in `main()`, rather than mixing bare
  `FileNotFoundError`, `OSError`, and silent failures.
- `apply_bulk_discount()` now calls `compute_item_value()` internally
  instead of duplicating the `qty * price` calculation — removing
  repeated logic that existed in two places in the original script.
- `find_low_stock()` was rewritten from an index-based loop
  (`for i in range(...)`) to a direct list comprehension over the
  items themselves. This isn't just a style preference: it structurally
  eliminates the entire class of off-by-one bugs that caused Bug 4,
  since there's no index arithmetic left to get wrong.
- `write_report()` now writes `(none)` under "Low stock items" when the
  list is empty, instead of leaving that section blank with no
  indication whether the check ran.

---

## 5. Final Verification

All six bugs were re-tested against `inventory_report_fixed.py` after
the fixes:

```
$ python3 inventory_report_fixed.py
Report generated: report.txt
```

`report.txt` now correctly includes **both** low-stock items (Widget C
*and* Widget E, confirming Bug 4 is fixed):

```
=== Inventory Report ===

Average unit price: $7.19

Item values (after any bulk discount):
  Widget A: $270.00
  Widget B: $120.00
  Widget C: $21.75
  Widget D: $64.80
  Widget E: $39.96

Low stock items:
  Widget C
  Widget E
```

Additional targeted checks, run directly against the fixed module:

```python
>>> import inventory_report_fixed as m
>>> m.compute_item_value({'name': 'X', 'quantity': '10', 'price': '2.5'})
25.0                                    # Bug 1: fixed, no TypeError

>>> items = m.read_inventory('inventory.csv')
>>> len(m.apply_bulk_discount(items))
5
>>> len(m.apply_bulk_discount(items))   # called again
5                                        # Bug 2: fixed, no accumulation

>>> m.average_price([])
0.0                                      # Bug 5: fixed, no ZeroDivisionError

>>> m.read_inventory('missing.csv')
InventoryError: Inventory file not found: 'missing.csv'   # Bug 3-related: clear error

>>> m.write_report('/nonexistent_dir/report.txt', [], [], 1.0)
InventoryError: Could not write report to '/nonexistent_dir/report.txt': ...
                                          # Bug 6: fixed, failure is now visible
```

A `ResourceWarning`-as-error run (`python3 -W error::ResourceWarning`)
around `read_inventory()` produced no warning, confirming Bug 3's file
handle is now properly closed via the `with` block.

All fixes preserve the script's original intended behavior (same report
format, same discount/low-stock logic) while eliminating every
previously reproducible failure and silent-failure mode.
