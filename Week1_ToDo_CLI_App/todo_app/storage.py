"""
storage.py
----------
Handles reading and writing the task list to disk as JSON.

Design choice:
    Persistence is isolated in its own module so the TaskManager (business
    logic) doesn't need to know *how* or *where* tasks are stored. If a
    future version wanted to swap JSON for SQLite, only this file would
    need to change.

    All file I/O is wrapped in error handling: a missing file is treated
    as "no tasks yet" (not an error), while a corrupted/unreadable file
    raises a clear, specific exception rather than letting a raw
    JSONDecodeError or OSError bubble up to the user.
"""

import json
import os
from typing import List


class StorageError(Exception):
    """Raised when task data cannot be loaded from or saved to disk."""


class JSONStorage:
    """Reads and writes a list of task dicts to a JSON file."""

    def __init__(self, filepath: str = "tasks.json"):
        self.filepath = filepath

    def load(self) -> List[dict]:
        """
        Load tasks from disk.

        Returns an empty list if the file doesn't exist yet (first run).
        Raises StorageError if the file exists but is not valid JSON or
        cannot be read for another reason.
        """
        if not os.path.exists(self.filepath):
            return []

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Task file '{self.filepath}' is corrupted and could not be "
                f"parsed as JSON: {exc}"
            ) from exc
        except OSError as exc:
            raise StorageError(
                f"Could not read task file '{self.filepath}': {exc}"
            ) from exc

        if not isinstance(data, list):
            raise StorageError(
                f"Task file '{self.filepath}' does not contain a JSON list."
            )
        return data

    def save(self, tasks: List[dict]) -> None:
        """
        Write the given list of task dicts to disk atomically.

        A temp file is written first and then renamed over the target
        file, so a crash mid-write can't leave tasks.json half-written
        or empty.
        """
        tmp_path = f"{self.filepath}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
            os.replace(tmp_path, self.filepath)
        except OSError as exc:
            raise StorageError(
                f"Could not save tasks to '{self.filepath}': {exc}"
            ) from exc
