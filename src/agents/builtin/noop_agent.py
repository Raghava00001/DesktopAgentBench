"""
No-op agent — does nothing, used for harness validation.

This agent takes no actions and never signals done. It's useful for
verifying that the benchmark harness, recorder, evaluator, and chaos
engine all function correctly end-to-end.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from src.agents.adapter import AgentAdapter, Action


class NoopAgent(AgentAdapter):
    """Agent that takes no actions — baseline for harness testing."""

    def __init__(self) -> None:
        self._step_count = 0
        self._done = False

    def name(self) -> str:
        return "noop"

    def version(self) -> str:
        return "1.0.0"

    def setup(self, task_instruction: str, app_info: dict[str, Any]) -> None:
        self._step_count = 0
        self._done = False

    def decide(
        self,
        screenshot: Image.Image,
        accessibility_tree: dict[str, Any] | None,
        task_instruction: str,
    ) -> Action:
        self._step_count += 1
        # Signal done after 3 no-op steps
        if self._step_count >= 3:
            self._done = True
            return Action(action_type="done", reasoning="Noop agent — auto-completing after 3 steps")
        return Action(action_type="noop", reasoning="Noop agent — intentionally doing nothing")

    def execute_action(self, action: Action) -> bool:
        return True  # noop always "succeeds"

    def get_screenshot(self) -> Image.Image:
        try:
            from PIL import ImageGrab
            return ImageGrab.grab()
        except Exception:
            return Image.new("RGB", (1920, 1080), color=(0, 0, 0))

    def get_state(self) -> dict[str, Any]:
        return {"step_count": self._step_count, "agent": "noop"}

    def signals_done(self) -> bool:
        return self._done

    def teardown(self) -> None:
        pass
