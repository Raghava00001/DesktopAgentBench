"""
Split manager for DesktopAgentBench.

Manages the dev/held-out partition of the task corpus using deterministic
hashing so splits are stable across runs.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

from src.tasks.schema import Task


class SplitManager:
    """
    Manages task corpus splits (dev / held_out).

    Tasks in the `tasks/dev/` directory are public; tasks in
    `tasks/held_out/` are private. This manager can also dynamically
    partition a flat list of tasks using deterministic hashing.
    """

    def __init__(self, dev_ratio: float = 0.7, seed: str = "dab_v1") -> None:
        if not 0.0 < dev_ratio < 1.0:
            raise ValueError(f"dev_ratio must be between 0 and 1, got {dev_ratio}")
        self._dev_ratio = dev_ratio
        self._seed = seed

    def filter_by_split(self, tasks: list[Task], split: str) -> list[Task]:
        """
        Filter tasks by their declared split field.

        Args:
            tasks: All loaded tasks.
            split: "dev", "held_out", or "all".

        Returns:
            Filtered list of tasks.
        """
        if split == "all":
            return list(tasks)
        return [t for t in tasks if t.split == split]

    def assign_splits(self, tasks: list[Task]) -> tuple[list[Task], list[Task]]:
        """
        Deterministically partition tasks into dev and held-out splits
        using content-based hashing.

        Returns:
            Tuple of (dev_tasks, held_out_tasks).
        """
        dev: list[Task] = []
        held_out: list[Task] = []

        for task in tasks:
            bucket = self._hash_to_bucket(task.task_id)
            if bucket < self._dev_ratio:
                dev.append(task)
            else:
                held_out.append(task)

        return dev, held_out

    def _hash_to_bucket(self, task_id: str) -> float:
        """
        Hash a task ID to a float in [0, 1) for deterministic splitting.
        """
        h = hashlib.sha256(f"{self._seed}:{task_id}".encode()).hexdigest()
        # Use first 8 hex chars (32 bits) for bucket
        return int(h[:8], 16) / 0xFFFFFFFF

    def get_split_summary(self, tasks: list[Task]) -> dict[str, int]:
        """Return a count of tasks per declared split."""
        summary: dict[str, int] = {}
        for task in tasks:
            summary[task.split] = summary.get(task.split, 0) + 1
        return summary
