"""
Random agent — takes random actions, used as a baseline for metrics.

This agent randomly clicks, types, and uses hotkeys. It provides a
performance floor: any real agent should significantly outperform
random actions.
"""

from __future__ import annotations

import random
import string
import time
from typing import Any

from PIL import Image

from src.agents.adapter import AgentAdapter, Action


class RandomAgent(AgentAdapter):
    """Agent that takes random actions — performance floor baseline."""

    def __init__(self, seed: int | None = None, max_steps: int = 3) -> None:
        self._rng = random.Random(seed)
        self._max_steps = max_steps
        self._step_count = 0
        self._screen_size = (1920, 1080)

    def name(self) -> str:
        return "random"

    def version(self) -> str:
        return "1.0.0"

    def setup(self, task_instruction: str, app_info: dict[str, Any]) -> None:
        self._step_count = 0

    def decide(
        self,
        screenshot: Image.Image,
        accessibility_tree: dict[str, Any] | None,
        task_instruction: str,
    ) -> Action:
        self._step_count += 1
        self._screen_size = screenshot.size if screenshot else (1920, 1080)

        if self._step_count >= self._max_steps:
            return Action(
                action_type="done",
                reasoning="Random agent — max steps reached",
            )

        # Weighted random action selection
        action_type = self._rng.choices(
            ["click", "type", "hotkey", "scroll", "wait"],
            weights=[40, 25, 15, 10, 10],
            k=1,
        )[0]

        if action_type == "click":
            return Action(
                action_type="click",
                parameters={
                    "x": self._rng.randint(50, self._screen_size[0] - 50),
                    "y": self._rng.randint(50, self._screen_size[1] - 50),
                    "button": "left",
                },
                reasoning="Random click",
            )

        elif action_type == "type":
            length = self._rng.randint(1, 10)
            text = "".join(self._rng.choices(string.ascii_lowercase + " ", k=length))
            return Action(
                action_type="type",
                parameters={"text": text},
                reasoning=f"Random typing: '{text}'",
            )

        elif action_type == "hotkey":
            hotkeys = [
                ["ctrl", "s"],
                ["ctrl", "a"],
                ["ctrl", "c"],
                ["ctrl", "v"],
                ["ctrl", "z"],
                ["tab"],
                ["enter"],
                ["escape"],
            ]
            return Action(
                action_type="hotkey",
                parameters={"keys": self._rng.choice(hotkeys)},
                reasoning="Random hotkey",
            )

        elif action_type == "scroll":
            return Action(
                action_type="scroll",
                parameters={
                    "x": self._screen_size[0] // 2,
                    "y": self._screen_size[1] // 2,
                    "delta": self._rng.choice([-3, -1, 1, 3]),
                },
                reasoning="Random scroll",
            )

        else:  # wait
            return Action(
                action_type="wait",
                parameters={"seconds": self._rng.uniform(0.5, 2.0)},
                reasoning="Random wait",
            )

    def execute_action(self, action: Action) -> bool:
        """Execute action — random agent doesn't actually interact with the desktop."""
        # if action.action_type == "wait":
        #     time.sleep(action.parameters.get("seconds", 1.0))
        # In a real benchmark, this would use pyautogui or similar
        return True

    def get_state(self) -> dict[str, Any]:
        return {
            "step_count": self._step_count,
            "agent": "random",
            "max_steps": self._max_steps,
        }

    def signals_done(self) -> bool:
        return self._step_count >= self._max_steps

    def teardown(self) -> None:
        pass
