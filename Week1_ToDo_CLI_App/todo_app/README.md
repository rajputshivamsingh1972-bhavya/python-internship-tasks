# To-Do List Manager (CLI)

A simple, dependency-free command-line To-Do List Manager written in
Python. Tasks persist between runs in a local `tasks.json` file.

## 1. Architecture

The application is split into three modules with clearly separated
responsibilities, following a simple layered design:

```
main.py     -> Presentation layer: CLI menu, input prompts, input validation
manager.py  -> Business logic layer: TaskManager (add/remove/list/complete)
models.py   -> Domain layer: the Task class
storage.py  -> Persistence layer: JSONStorage (load/save tasks.json)
```

**Why this split?**
- `main.py` only knows how to talk to a human (print menus, read input,
  show errors). It never touches JSON or task-list internals directly.
- `manager.py` contains all the *rules* (an empty description is invalid,
  you can't complete a task twice, etc.) and is fully testable without
  any `input()`/`print()` calls.
- `models.py` defines what a `Task` *is* and how it serializes, so that
  knowledge lives in one place.
- `storage.py` knows only about *how* data is saved/loaded (JSON files).
  If a future version swapped in SQLite or a remote API, this is the
  only file that would need to change.

This mirrors a small-scale version of the standard
"presentation / business logic / data access" layering used in larger
applications, sized appropriately for a CLI tool.

### Flow diagram (pseudocode)

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

## 2. Design Decisions

- **Menu loop over argparse subcommands.** The app is meant to be used
  across a whole session (add a few tasks, check them off, add more).
  A persistent menu avoids re-typing `python main.py add "..."` for
  every single action and makes manual testing (see Section 5) easy
  for anyone without prior knowledge of the tool.
- **OOP for both the domain object (`Task`) and the logic layer
  (`TaskManager`).** A class-based `Task` keeps validation and
  serialization next to the data. `TaskManager` holds state (the task
  list, the next available id) so it can be instantiated fresh in tests
  without needing to fake global variables.
- **JSON persistence with atomic writes.** `storage.py` writes to a
  temporary file and uses `os.replace()` to swap it into place, so a
  crash mid-save cannot corrupt `tasks.json` by leaving it half-written.
- **Errors are raised as exceptions from the logic layer
  (`TaskManagerError`, `StorageError`) and caught at the CLI boundary.**
  This means the same `TaskManager` could back a future GUI or web API
  and just needs its own error-display logic, without duplicating
  validation rules.
- **IDs are auto-incrementing integers, never reused.** Even after a
  task is removed, its ID is not recycled. This avoids confusion if a
  user refers to an ID from a previous "View" that has since changed.

## 3. Installation

No external dependencies are required — only the Python standard
library is used (`json`, `os`, `datetime`, `typing`, `sys`).

Requires **Python 3.8+**.

## 4. How to Run

```bash
cd todo_app
python3 main.py
```

You'll see a menu:

```
==================== TO-DO LIST MANAGER ====================
1. Add a task
2. View all tasks
3. View pending tasks only
4. Mark a task as complete
5. Remove a task
6. Quit
==============================================================
```

Type the number of the option you want and press Enter. Tasks are
automatically saved to `tasks.json` in the same directory after every
add/remove/complete action, so your list will still be there next time
you run the program.

To start fresh, simply delete `tasks.json`.

## 5. Manual Test Scenarios

Run `python3 main.py` and try the following. Expected results are noted
next to each step — deleting `tasks.json` first gives a clean slate.

| # | Action | Expected Result |
|---|--------|------------------|
| 1 | Choose `1`, enter "Buy groceries" | `Added task #1: Buy groceries` |
| 2 | Choose `1`, enter "" (just press Enter) | `Error: Task description cannot be empty.` — no task added |
| 3 | Choose `2` (View all) | Shows `[ ] #1: Buy groceries` |
| 4 | Choose `4`, enter `1` | `Marked task #1 as complete.` |
| 5 | Choose `4`, enter `1` again | `Error: Task #1 is already marked complete.` |
| 6 | Choose `4`, enter `abc` | `Error: 'abc' is not a valid integer task ID.` |
| 7 | Choose `4`, enter `999` | `Error: No task found with id 999.` |
| 8 | Choose `3` (View pending only) after step 4 | `(no tasks to show)` since the only task is complete |
| 9 | Choose `5`, enter `1` | `Removed task #1: Buy groceries` |
| 10 | Choose `9` (invalid menu number) | `Error: '9' is not a valid option. Please choose 1-6.` |
| 11 | Choose `6` | Prints `Goodbye!` and exits |
| 12 | Re-run `python3 main.py` after adding tasks | Previously added/uncompleted tasks are still present (confirms persistence) |
| 13 | Manually edit `tasks.json` to invalid JSON (e.g. delete a bracket), then run | `Fatal error loading tasks: Task file 'tasks.json' is corrupted...` and the program exits instead of crashing |

These scenarios cover the four core features (add/view/complete/remove),
input validation (empty text, non-numeric IDs, out-of-range IDs, invalid
menu choices), state transitions (double-completing a task), persistence
across runs, and corrupted-file recovery.
