"""
manager.py
----------
Contains TaskManager, the class responsible for all task business logic:
adding, removing, listing, and completing tasks. It sits between the CLI
(main.py) and the persistence layer (storage.py).

Design choice:
    Keeping this logic in its own class (rather than inline in main.py)
    means the same logic could be reused by a future GUI or web front end
    without duplicating code. It also makes the logic unit-testable in
    isolation from any input()/print() calls.
"""

from typing import List, Optional

from models import Task
from storage import JSONStorage, StorageError


class TaskManagerError(Exception):
    """Raised for invalid operations on the task list (bad id, etc.)."""


class TaskManager:
    def __init__(self, storage: Optional[JSONStorage] = None):
        self.storage = storage or JSONStorage()
        self.tasks: List[Task] = []
        self._next_id = 1
        self._load()

    # ---------- persistence helpers ----------

    def _load(self) -> None:
        """Load tasks from storage and compute the next available id."""
        raw = self.storage.load()
        self.tasks = [Task.from_dict(item) for item in raw]
        if self.tasks:
            self._next_id = max(t.task_id for t in self.tasks) + 1
        else:
            self._next_id = 1

    def _save(self) -> None:
        self.storage.save([t.to_dict() for t in self.tasks])

    # ---------- core operations ----------

    def add_task(self, description: str) -> Task:
        """
        Add a new task with the given description.

        Raises TaskManagerError if the description is empty/whitespace,
        since a blank task is never useful and is almost always a sign
        of accidental input (e.g. pressing Enter with nothing typed).
        """
        description = description.strip()
        if not description:
            raise TaskManagerError("Task description cannot be empty.")

        task = Task(task_id=self._next_id, description=description)
        self.tasks.append(task)
        self._next_id += 1
        self._save()
        return task

    def remove_task(self, task_id: int) -> Task:
        """Remove and return the task with the given id, or raise if not found."""
        task = self._find(task_id)
        self.tasks.remove(task)
        self._save()
        return task

    def mark_complete(self, task_id: int) -> Task:
        """Mark the task with the given id as completed."""
        task = self._find(task_id)
        if task.completed:
            raise TaskManagerError(f"Task #{task_id} is already marked complete.")
        task.mark_complete()
        self._save()
        return task

    def list_tasks(self, show_completed: bool = True) -> List[Task]:
        """
        Return tasks in id order.

        If show_completed is False, only pending tasks are returned; this
        backs an optional "view active tasks only" mode in the CLI.
        """
        tasks = sorted(self.tasks, key=lambda t: t.task_id)
        if not show_completed:
            tasks = [t for t in tasks if not t.completed]
        return tasks

    # ---------- internal helpers ----------

    def _find(self, task_id: int) -> Task:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise TaskManagerError(f"No task found with id {task_id}.")
