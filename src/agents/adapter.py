"""
Agent adapter abstract base class for DesktopAgentBench.

Any desktop agent that wants to be benchmarked must implement this
interface. The adapter provides a clean boundary between the benchmark
harness and the agent's internal logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PIL import Image


@dataclass
class Action:
    """
    Represents a single agent action on the desktop.

    Supported action_types:
    - "click":    parameters = {"x": int, "y": int, "button": "left"|"right"}
    - "type":     parameters = {"text": str}
    - "hotkey":   parameters = {"keys": list[str]}  e.g. ["ctrl", "s"]
    - "scroll":   parameters = {"x": int, "y": int, "delta": int}
    - "drag":     parameters = {"start_x": int, "start_y": int, "end_x": int, "end_y": int}
    - "wait":     parameters = {"seconds": float}
    - "done":     parameters = {}  — agent signals task completion
    - "noop":     parameters = {}  — agent chooses to do nothing this step
    """
    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    reasoning: str | None = None  # optional: agent's chain-of-thought


class AgentAdapter(ABC):
    """
    Abstract base class for integrating any desktop agent with DesktopAgentBench.

    To benchmark a new agent:
    1. Create a subclass in agents/{your_agent}/adapter.py
    2. Implement all abstract methods below
    3. Either:
       a. Place the module in the agents/ directory (auto-discovered), or
       b. Register via entry_points in pyproject.toml, or
       c. Specify via CLI: --agent path.to.module:ClassName

    The benchmark harness will call methods in this order:
        setup() → [decide() → execute_action()]* → teardown()
    """

    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this agent.

        Used in reports and result filenames.
        """
        ...

    @abstractmethod
    def version(self) -> str:
        """Agent version string for tracking across benchmark runs."""
        ...

    @abstractmethod
    def setup(self, task_instruction: str, app_info: dict[str, Any]) -> None:
        """
        Initialize the agent for a specific task.

        Called once before the evaluation loop begins.

        Args:
            task_instruction: Natural language description of what to do.
            app_info: Dict with keys like "app", "category", "preconditions".
        """
        ...

    @abstractmethod
    def decide(
        self,
        screenshot: Image.Image,
        accessibility_tree: dict[str, Any] | None,
        task_instruction: str,
    ) -> Action:
        """
        Given the current observation, return the next action.

        This is the core agent intelligence method.

        Args:
            screenshot: Current screen capture (PIL Image).
            accessibility_tree: Optional UI automation tree of visible elements.
            task_instruction: The task the agent is trying to complete.

        Returns:
            Action to perform on the desktop.
        """
        ...

    @abstractmethod
    def execute_action(self, action: Action) -> bool:
        """
        Execute the decided action on the desktop.

        Args:
            action: The action to perform.

        Returns:
            True if the action was successfully performed.
        """
        ...

    @abstractmethod
    def get_screenshot(self) -> Image.Image:
        """
        Capture the current screen state.

        The agent is responsible for its own screenshot mechanism.
        This allows agents to use different capture methods (GDI, DXGI, etc.)
        """
        ...

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """
        Return the agent's current internal state for logging.

        May include: step count, confidence scores, memory state,
        plan state, error state, etc.
        """
        ...

    @abstractmethod
    def signals_done(self) -> bool:
        """
        Return True if the agent believes the task is complete.

        The harness checks this after each action. If True, the
        evaluation loop ends and success criteria are checked.
        """
        ...

    @abstractmethod
    def teardown(self) -> None:
        """
        Clean up agent resources after task completion.

        Called once after the evaluation loop ends, regardless of
        success or failure.
        """
        ...

    def supports_accessibility_tree(self) -> bool:
        """
        Override to return True if the agent can use accessibility trees.

        Default is False — only screenshots are provided.
        """
        return False

    def get_metadata(self) -> dict[str, Any]:
        """
        Optional: return additional metadata about the agent.

        Included in benchmark reports for context.
        """
        return {
            "name": self.name(),
            "version": self.version(),
            "supports_a11y": self.supports_accessibility_tree(),
        }
