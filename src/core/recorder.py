"""
Action and screenshot recorder for DesktopAgentBench.

Records every agent action, screenshot, chaos event, and evaluation state
into a structured JSONL log with associated screenshot files.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class RecordedStep:
    """A single recorded step in a benchmark run."""
    step_index: int
    timestamp: float
    elapsed_seconds: float
    action_type: str
    action_parameters: dict[str, Any]
    action_reasoning: str | None = None
    screenshot_path: str | None = None
    chaos_events_active: list[str] = field(default_factory=list)
    agent_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ChaosEventRecord:
    """Record of a chaos injection event."""
    timestamp: float
    elapsed_seconds: float
    module_name: str
    event_type: str  # "inject" | "cleanup"
    parameters: dict[str, Any] = field(default_factory=dict)
    affected_window: str | None = None


class Recorder:
    """
    Records all actions, screenshots, and chaos events during a benchmark run.

    Output structure:
        {results_dir}/{run_id}/
            actions.jsonl       — one JSON line per agent step
            chaos_events.jsonl  — one JSON line per chaos event
            screenshots/        — PNG screenshots per step
            metadata.json       — run metadata (timing, config hash)
    """

    def __init__(self, results_dir: Path, run_id: str) -> None:
        self._run_dir = results_dir / run_id
        self._screenshots_dir = self._run_dir / "screenshots"
        self._actions_path = self._run_dir / "actions.jsonl"
        self._chaos_events_path = self._run_dir / "chaos_events.jsonl"
        self._metadata_path = self._run_dir / "metadata.json"

        self._start_time: float = 0.0
        self._step_count: int = 0
        self._actions: list[RecordedStep] = []
        self._chaos_events: list[ChaosEventRecord] = []
        self._is_recording: bool = False

    def start(self, metadata: dict[str, Any] | None = None) -> None:
        """Begin recording a new run."""
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._screenshots_dir.mkdir(exist_ok=True)
        self._start_time = time.time()
        self._step_count = 0
        self._actions = []
        self._chaos_events = []
        self._is_recording = True

        # Write initial metadata
        meta = {
            "run_id": self._run_dir.name,
            "start_time": self._start_time,
            "start_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self._start_time)),
            **(metadata or {}),
        }
        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)

        # Create empty log files
        self._actions_path.touch()
        self._chaos_events_path.touch()

    def log_step(
        self,
        action_type: str,
        action_parameters: dict[str, Any],
        screenshot: Image.Image | None = None,
        action_reasoning: str | None = None,
        chaos_events_active: list[str] | None = None,
        agent_state: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> RecordedStep:
        """Record a single agent step."""
        if not self._is_recording:
            raise RuntimeError("Recorder is not active. Call start() first.")

        now = time.time()
        elapsed = now - self._start_time

        # Save screenshot
        screenshot_path: str | None = None
        if screenshot is not None:
            fname = f"step_{self._step_count:04d}.png"
            spath = self._screenshots_dir / fname
            screenshot.save(str(spath), format="PNG")
            screenshot_path = fname

        step = RecordedStep(
            step_index=self._step_count,
            timestamp=now,
            elapsed_seconds=round(elapsed, 3),
            action_type=action_type,
            action_parameters=action_parameters,
            action_reasoning=action_reasoning,
            screenshot_path=screenshot_path,
            chaos_events_active=chaos_events_active or [],
            agent_state=agent_state or {},
            error=error,
        )

        self._actions.append(step)
        self._step_count += 1

        # Append to JSONL
        with open(self._actions_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(step), default=str) + "\n")

        return step

    def log_chaos_event(
        self,
        module_name: str,
        event_type: str,
        parameters: dict[str, Any] | None = None,
        affected_window: str | None = None,
    ) -> ChaosEventRecord:
        """Record a chaos injection event."""
        now = time.time()
        elapsed = now - self._start_time if self._start_time else 0.0

        event = ChaosEventRecord(
            timestamp=now,
            elapsed_seconds=round(elapsed, 3),
            module_name=module_name,
            event_type=event_type,
            parameters=parameters or {},
            affected_window=affected_window,
        )

        self._chaos_events.append(event)

        with open(self._chaos_events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")

        return event

    def stop(self) -> None:
        """Stop recording and finalize metadata."""
        if not self._is_recording:
            return

        self._is_recording = False
        end_time = time.time()

        # Update metadata with end time
        meta: dict[str, Any] = {}
        if self._metadata_path.exists():
            with open(self._metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

        meta["end_time"] = end_time
        meta["end_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(end_time))
        meta["total_seconds"] = round(end_time - self._start_time, 3)
        meta["total_steps"] = self._step_count
        meta["total_chaos_events"] = len(self._chaos_events)

        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)

    def get_actions(self) -> list[RecordedStep]:
        """Return all recorded steps."""
        return list(self._actions)

    def get_chaos_events(self) -> list[ChaosEventRecord]:
        """Return all recorded chaos events."""
        return list(self._chaos_events)

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def run_dir(self) -> Path:
        return self._run_dir
