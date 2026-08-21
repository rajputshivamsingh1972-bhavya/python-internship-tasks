"""
models.py
---------
Defines the core data structure for the To-Do List Manager: the Task class.

Design choice:
    A Task is modeled as a small, self-contained class rather than a plain
    dict. This keeps validation logic (e.g. what counts as a valid task)
    next to the data itself, and makes it trivial to add new fields later
    (due dates, priority, tags, etc.) without touching unrelated code.

    to_dict()/from_dict() are provided so the TaskManager can serialize a
    list of Task objects to JSON for persistence without the storage layer
    needing to know anything about the Task class internals.
"""

from datetime import datetime
from typing import Optional


class Task:
    """Represents a single to-do item."""

    def __init__(
        self,
        task_id: int,
        description: str,
        completed: bool = False,
        created_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ):
        self.task_id = task_id
        self.description = description
        self.completed = completed
        # Stored as ISO-8601 strings so they serialize cleanly to JSON.
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")
        self.completed_at = completed_at

    def mark_complete(self) -> None:
        """Mark this task as completed and stamp the completion time."""
        self.completed = True
        self.completed_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        """Convert this Task into a plain dict suitable for JSON storage."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Rebuild a Task instance from a dict loaded from JSON."""
        return cls(
            task_id=data["task_id"],
            description=data["description"],
            completed=data.get("completed", False),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
        )

    def __str__(self) -> str:
        status = "[x]" if self.completed else "[ ]"
        return f"{status} #{self.task_id}: {self.description}"
