"""
Pydantic models defining the task schema for DesktopAgentBench.

Each task is a JSON file describing a specific Windows desktop operation
the agent must complete, along with success criteria, partial credit,
chaos compatibility, and metadata.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CriterionType(str, Enum):
    FILE_EXISTS = "file_exists"
    FILE_CONTENT_MATCHES = "file_content_matches"
    FILE_CONTENT_REGEX = "file_content_regex"
    APP_LAUNCHED = "app_launched"
    WINDOW_EXISTS = "window_exists"
    CLIPBOARD_CONTENT = "clipboard_content"
    TEXT_TYPED = "text_typed"
    REGISTRY_VALUE = "registry_value"


class ChaosType(str, Enum):
    POPUP = "popup"
    FOCUS_STEAL = "focus_steal"
    DELAY = "delay"
    RESIZE = "resize"
    UAC = "uac"
    NOTIFICATION = "notification"
    SCROLL_HIDE = "scroll_hide"


class SuccessCriterion(BaseModel):
    """A binary success criterion for task completion."""
    type: CriterionType
    path: str | None = None
    expected: str | None = None
    pattern: str | None = None  # for regex matching
    process: str | None = None
    window_title: str | None = None
    registry_key: str | None = None
    registry_value: str | None = None


class PartialCreditCriterion(BaseModel):
    """A weighted partial credit criterion."""
    type: CriterionType
    weight: float = Field(ge=0.0, le=1.0)
    path: str | None = None
    expected: str | None = None
    pattern: str | None = None
    process: str | None = None
    content: str | None = None
    window_title: str | None = None


class Preconditions(BaseModel):
    """Environment preconditions that must be met before task execution."""
    apps_required: list[str] = Field(default_factory=list)
    files_required: list[str] = Field(default_factory=list)
    registry_keys: list[str] = Field(default_factory=list)
    env_setup_script: str | None = None


class TaskMetadata(BaseModel):
    """Authorship and bookkeeping metadata."""
    author: str = "benchmark_team"
    created: str = ""
    notes: str = ""


class Task(BaseModel):
    """
    Complete task definition for a single benchmark scenario.

    Each task describes:
    - What the agent must do (natural language instruction)
    - What constitutes success (success_criteria)
    - Partial credit for intermediate progress
    - Which chaos injections are compatible
    - Execution limits (max steps, timeout)
    """

    task_id: str = Field(min_length=1)
    version: str = "1.0"
    category: str
    app: str
    split: str = "dev"
    difficulty: Difficulty = Difficulty.MEDIUM

    title: str
    description: str
    natural_language_instruction: str

    preconditions: Preconditions = Field(default_factory=Preconditions)

    success_criteria: list[SuccessCriterion] = Field(min_length=1)
    partial_credit_criteria: list[PartialCreditCriterion] = Field(default_factory=list)

    chaos_compatibility: list[ChaosType] = Field(
        default_factory=lambda: list(ChaosType)
    )

    max_steps: int = Field(default=20, ge=1, le=500)
    timeout_seconds: int = Field(default=120, ge=10, le=3600)

    tags: list[str] = Field(default_factory=list)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Task IDs must be lowercase alphanumeric with underscores."""
        import re
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                f"task_id must be lowercase alphanumeric with underscores, got: {v}"
            )
        return v
