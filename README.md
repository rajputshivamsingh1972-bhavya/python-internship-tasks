# Python Internship Tasks

This repository contains my Python internship assignments. Full project
files for each week live in their own folder (linked below); this README
also inlines the key required deliverables directly — architecture, flow
diagram/pseudocode, representative code, and test scenarios — for Weeks
1 and 2, so everything can be reviewed without opening subfolders.

---

## Week 1 — Python CLI Application Design and Implementation

**Folder:** [`Week1_ToDo_CLI_App/todo_app/`](./Week1_ToDo_CLI_App/todo_app/)
**Files:** `main.py`, `manager.py`, `models.py`, `storage.py`, `README.md`

A modular command-line To-Do List Manager with add/view/complete/remove,
JSON persistence, input validation, and error handling.

### Architecture

```
main.py     -> Presentation layer: CLI menu, input prompts, input validation
manager.py  -> Business logic layer: TaskManager (add/remove/list/complete)
models.py   -> Domain layer: the Task class
storage.py  -> Persistence layer: JSONStorage (load/save tasks.json)
```

`main.py` only talks to the human (menus, input, errors) and never
touches JSON directly. `manager.py` holds all business rules (empty
description is invalid, can't complete a task twice) and is fully
testable without any `input()`/`print()` calls. `storage.py` isolates
*how* data is persisted, so swapping JSON for a database later would
only touch this one file.

### Flow diagram / pseudocode

```
START
  load tasks.json into TaskManager (empty list if file doesn't exist)
  LOOP forever:
    print menu (Add / View All / View Pending / Complete / Remove / Quit)
    read user choice

    IF choice == Add:
        read description
        IF description is blank -> show error, continue loop
        create Task, assign next id, append, save to disk

    ELIF choice == View All / View Pending:
        print each task as "[x] #id: description" or "[ ] #id: description"

    ELIF choice == Complete:
        read task id
        IF id is not an integer -> show error, continue loop
        IF no task with that id -> show error, continue loop
        IF task already completed -> show error, continue loop
        mark task completed, stamp completed_at, save to disk

    ELIF choice == Remove:
        read task id
        IF id is not an integer -> show error, continue loop
        IF no task with that id -> show error, continue loop
        remove task from list, save to disk

    ELIF choice == Quit:
        print goodbye, EXIT loop

    ELSE:
        show "invalid option" error, continue loop
END
```

### Representative code

`models.py` — the `Task` domain object:

```python
class Task:
    """Represents a single to-do item."""

    def __init__(self, task_id, description, completed=False,
                 created_at=None, completed_at=None):
        self.task_id = task_id
        self.description = description
        self.completed = completed
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")
        self.completed_at = completed_at

    def mark_complete(self):
        self.completed = True
        self.completed_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
```

`manager.py` — core business rule example (rejecting an empty task,
preventing a double-complete):

```python
def add_task(self, description: str) -> Task:
    description = description.strip()
    if not description:
        raise TaskManagerError("Task description cannot be empty.")
    task = Task(task_id=self._next_id, description=description)
    self.tasks.append(task)
    self._next_id += 1
    self._save()
    return task

def mark_complete(self, task_id: int) -> Task:
    task = self._find(task_id)
    if task.completed:
        raise TaskManagerError(f"Task #{task_id} is already marked complete.")
    task.mark_complete()
    self._save()
    return task
```

`main.py` — input validation at the CLI boundary:

```python
def prompt_task_id(tasks_manager, action):
    raw = input(f"Enter the task ID to {action}: ").strip()
    if not raw:
        raise ValueError("Task ID cannot be empty.")
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"'{raw}' is not a valid integer task ID.")
```

### How to run

```bash
cd Week1_ToDo_CLI_App/todo_app
python3 main.py
```

No external dependencies — Python 3.8+ standard library only.

### Manual test scenarios

| # | Action | Expected Result |
|---|--------|------------------|
| 1 | Choose `1`, enter "Buy groceries" | `Added task #1: Buy groceries` |
| 2 | Choose `1`, enter "" (blank) | `Error: Task description cannot be empty.` — no task added |
| 3 | Choose `2` (View all) | Shows `[ ] #1: Buy groceries` |
| 4 | Choose `4`, enter `1` | `Marked task #1 as complete.` |
| 5 | Choose `4`, enter `1` again | `Error: Task #1 is already marked complete.` |
| 6 | Choose `4`, enter `abc` | `Error: 'abc' is not a valid integer task ID.` |
| 7 | Choose `4`, enter `999` | `Error: No task found with id 999.` |
| 8 | Choose `3` (pending only) after step 4 | `(no tasks to show)` — the only task is complete |
| 9 | Choose `5`, enter `1` | `Removed task #1: Buy groceries` |
| 10 | Choose `9` (invalid menu number) | `Error: '9' is not a valid option. Please choose 1-6.` |
| 11 | Choose `6` | Prints `Goodbye!` and exits |
| 12 | Re-run after adding tasks | Previously added tasks persist (confirms JSON persistence) |
| 13 | Manually corrupt `tasks.json`, then run | `Fatal error loading tasks: ...corrupted...` — fails gracefully, no crash |

These 13 scenarios cover all four core features, input validation
(blank text, non-numeric IDs, out-of-range IDs, invalid menu choices),
state transitions (double-completing a task), persistence across runs,
and corrupted-file recovery. Full detail in
[`Week1_ToDo_CLI_App/todo_app/README.md`](./Week1_ToDo_CLI_App/todo_app/README.md).

---

## Week 2 — Debugging and Troubleshooting Python Applications

**Folder:** [`Week2_Debugging_ToDo/`](./Week2_Debugging_ToDo/)
**Files:** `original_buggy_script.py`, `inventory_report_fixed.py`,
`debug_log.md`, `inventory.csv`

An inventory-reporting script was reviewed, six bugs were reproduced
with real tracebacks, fixed, and verified. Full narrative in
[`Week2_Debugging_ToDo/debug_log.md`](./Week2_Debugging_ToDo/debug_log.md).

### Bugs found, with before/after code

**Bug 1 — `TypeError` multiplying CSV string fields directly**
```python
# Before (crashes: "can't multiply sequence by non-int of type 'str'")
def compute_item_value(item):
    return item["quantity"] * item["price"]

# After
def compute_item_value(item):
    quantity = int(item["quantity"])
    price = float(item["price"])
    return quantity * price
```

**Bug 2 — Mutable default argument silently accumulates across calls**
```python
# Before (report=[] is created ONCE, shared across every call)
def apply_bulk_discount(items, threshold=50, discount=0.10, report=[]):
    ...
    report.append((item["name"], value))
    return report

# After
def apply_bulk_discount(items, threshold=50, discount=0.10):
    report = []   # fresh list every call
    ...
    return report
```

**Bug 3 — Unclosed file handle (resource leak)**
```python
# Before
f = open(filepath, "r")
reader = csv.DictReader(f)
# f is never closed

# After
with open(filepath, "r", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
```

**Bug 4 — Off-by-one skips the last inventory item**
```python
# Before (range(len(items) - 1) misses the final index)
for i in range(len(items) - 1):
    item = items[i]
    if int(item["quantity"]) <= min_qty:
        low.append(item["name"])

# After
return [item["name"] for item in items if int(item["quantity"]) <= min_qty]
```
Reproduced with `inventory.csv`: "Widget E" (qty 4, below the low-stock
threshold of 5) was silently missing from the report before the fix.

**Bug 5 — `ZeroDivisionError` on an empty inventory**
```python
# Before
return total / len(items)

# After
if not items:
    return 0.0
return total / len(items)
```

**Bug 6 — Bare `except: pass` silently swallows write failures**
```python
# Before
except:
    pass

# After
except OSError as exc:
    raise InventoryError(f"Could not write report to '{filepath}': {exc}")
```

### How to run / verify

```bash
cd Week2_Debugging_ToDo
python3 inventory_report_fixed.py   # generates report.txt
```

Each bug above was reproduced with an actual traceback before being
fixed, and re-tested afterward to confirm the fix (full transcripts of
both in `debug_log.md`). For example, Bug 4's fix was confirmed by
checking that "Widget E" now appears in the generated `report.txt`
under "Low stock items," where it was previously missing.

---

## Technologies

- Python 3.8+
- Python Standard Library only (`json`, `csv`, `os`, `datetime`, `typing`, `sys`)

## Purpose

These projects demonstrate modular design, object-oriented programming,
input validation and error handling, systematic debugging with
reproducible before/after evidence, and refactoring for code quality.
