"""
Task corpus loader for DesktopAgentBench.

Recursively loads and validates task JSON files from the tasks directory,
organized by split (dev / held_out) and category.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.tasks.schema import Task

logger = logging.getLogger(__name__)


class TaskLoader:
    """Loads and validates tasks from the filesystem."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir

    def load_all(self, split: str | None = None) -> list[Task]:
        """
        Load all tasks, optionally filtered by split.

        Args:
            split: "dev", "held_out", or None for all.

        Returns:
            List of validated Task objects.
        """
        tasks: list[Task] = []
        errors: list[str] = []

        if split:
            search_dirs = [self._tasks_dir / split]
        else:
            search_dirs = [
                d for d in self._tasks_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                logger.warning(f"Tasks directory does not exist: {search_dir}")
                continue

            for json_path in sorted(search_dir.rglob("*.json")):
                try:
                    task = self._load_task_file(json_path)
                    tasks.append(task)
                except (ValidationError, json.JSONDecodeError, KeyError) as e:
                    msg = f"Failed to load {json_path}: {e}"
                    errors.append(msg)
                    logger.warning(msg)

        if errors:
            logger.warning(f"Skipped {len(errors)} invalid task files")

        logger.info(f"Loaded {len(tasks)} tasks from {self._tasks_dir}")
        return tasks

    def load_by_ids(self, task_ids: list[str], split: str | None = None) -> list[Task]:
        """Load specific tasks by their IDs."""
        all_tasks = self.load_all(split)
        id_set = set(task_ids)
        found = [t for t in all_tasks if t.task_id in id_set]

        missing = id_set - {t.task_id for t in found}
        if missing:
            logger.warning(f"Tasks not found: {missing}")

        return found

    def load_by_category(self, category: str, split: str | None = None) -> list[Task]:
        """Load all tasks in a specific category."""
        all_tasks = self.load_all(split)
        return [t for t in all_tasks if t.category == category]

    def validate_all(self) -> tuple[int, list[str]]:
        """
        Validate all task files without loading them for execution.

        Returns:
            Tuple of (valid_count, list of error messages).
        """
        valid = 0
        errors: list[str] = []

        for json_path in sorted(self._tasks_dir.rglob("*.json")):
            try:
                self._load_task_file(json_path)
                valid += 1
            except Exception as e:
                errors.append(f"{json_path.name}: {e}")

        return valid, errors

    def _load_task_file(self, path: Path) -> Task:
        """Load and validate a single task JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Task(**data)
