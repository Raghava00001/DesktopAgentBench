"""Tests for the task schema and loader."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.tasks.schema import Task, SuccessCriterion, Difficulty, ChaosType


class TestTaskSchema:
    """Tests for the Task Pydantic model."""

    def test_minimal_valid_task(self):
        """A task with only required fields should validate."""
        task = Task(
            task_id="test_001",
            category="text_editor",
            app="notepad",
            title="Test Task",
            description="A test task.",
            natural_language_instruction="Do something.",
            success_criteria=[
                SuccessCriterion(type="file_exists", path="C:\\test.txt")
            ],
        )
        assert task.task_id == "test_001"
        assert task.difficulty == Difficulty.MEDIUM  # default

    def test_full_task(self):
        """A task with all fields should validate."""
        task = Task(
            task_id="notepad_001",
            version="1.0",
            category="text_editor",
            app="notepad",
            split="dev",
            difficulty="easy",
            title="Create file",
            description="Create a file.",
            natural_language_instruction="Create a file.",
            success_criteria=[
                SuccessCriterion(type="file_exists", path="C:\\test.txt"),
                SuccessCriterion(
                    type="file_content_matches",
                    path="C:\\test.txt",
                    expected="Hello",
                ),
            ],
            chaos_compatibility=["popup", "focus_steal", "delay"],
            max_steps=30,
            timeout_seconds=180,
            tags=["test", "basic"],
        )
        assert task.max_steps == 30
        assert len(task.chaos_compatibility) == 3

    def test_invalid_task_id_uppercase(self):
        """Task IDs with uppercase letters should fail."""
        with pytest.raises(ValidationError, match="task_id"):
            Task(
                task_id="Test_001",
                category="test",
                app="test",
                title="Test",
                description="Test",
                natural_language_instruction="Test",
                success_criteria=[
                    SuccessCriterion(type="file_exists", path="C:\\test.txt")
                ],
            )

    def test_invalid_task_id_spaces(self):
        """Task IDs with spaces should fail."""
        with pytest.raises(ValidationError, match="task_id"):
            Task(
                task_id="test 001",
                category="test",
                app="test",
                title="Test",
                description="Test",
                natural_language_instruction="Test",
                success_criteria=[
                    SuccessCriterion(type="file_exists", path="C:\\test.txt")
                ],
            )

    def test_empty_success_criteria_fails(self):
        """Tasks must have at least one success criterion."""
        with pytest.raises(ValidationError):
            Task(
                task_id="test_001",
                category="test",
                app="test",
                title="Test",
                description="Test",
                natural_language_instruction="Test",
                success_criteria=[],
            )

    def test_max_steps_bounds(self):
        """max_steps must be 1-500."""
        with pytest.raises(ValidationError):
            Task(
                task_id="test_001",
                category="test",
                app="test",
                title="Test",
                description="Test",
                natural_language_instruction="Test",
                success_criteria=[
                    SuccessCriterion(type="file_exists", path="C:\\test.txt")
                ],
                max_steps=0,
            )

    def test_timeout_bounds(self):
        """timeout_seconds must be 10-3600."""
        with pytest.raises(ValidationError):
            Task(
                task_id="test_001",
                category="test",
                app="test",
                title="Test",
                description="Test",
                natural_language_instruction="Test",
                success_criteria=[
                    SuccessCriterion(type="file_exists", path="C:\\test.txt")
                ],
                timeout_seconds=5,
            )


class TestTaskLoader:
    """Tests for loading tasks from JSON files."""

    def test_load_valid_task_file(self, tmp_path: Path):
        """Load a valid task from a JSON file."""
        from src.tasks.loader import TaskLoader

        task_data = {
            "task_id": "test_001",
            "category": "test",
            "app": "notepad",
            "title": "Test",
            "description": "Test task",
            "natural_language_instruction": "Do test.",
            "split": "dev",
            "success_criteria": [
                {"type": "file_exists", "path": "C:\\test.txt"}
            ],
        }

        dev_dir = tmp_path / "dev" / "test"
        dev_dir.mkdir(parents=True)
        (dev_dir / "test_001.json").write_text(json.dumps(task_data))

        loader = TaskLoader(tmp_path)
        tasks = loader.load_all("dev")
        assert len(tasks) == 1
        assert tasks[0].task_id == "test_001"

    def test_skip_invalid_task(self, tmp_path: Path):
        """Invalid task files should be skipped with warnings."""
        from src.tasks.loader import TaskLoader

        dev_dir = tmp_path / "dev" / "test"
        dev_dir.mkdir(parents=True)
        (dev_dir / "bad.json").write_text('{"invalid": "data"}')

        loader = TaskLoader(tmp_path)
        tasks = loader.load_all("dev")
        assert len(tasks) == 0
