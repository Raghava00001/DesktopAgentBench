"""
Chaos module base and context interfaces for DesktopAgentBench.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.chaos.injector import ChaosEvent


@dataclass
class ChaosContext:
    """Context passed to chaos modules during injection."""
    target_window_hwnd: int | None = None
    target_window_title: str = ""
    target_process_name: str = ""
    screen_resolution: tuple[int, int] = (1920, 1080)
    elapsed_seconds: float = 0.0
    injection_params: dict[str, Any] = field(default_factory=dict)


class ChaosModule(ABC):
    """
    Abstract base class for all chaos injection modules.

    Safety contract:
    - Modules must NOT modify system state permanently
    - All created windows/resources must be cleaned up
    - Modules must NOT escalate privileges or access protected resources
    - The is_safe() method must return True for the module to be usable
    """

    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this chaos module."""
        ...

    @abstractmethod
    def inject(self, context: ChaosContext) -> ChaosEvent:
        """
        Perform a single chaos injection.

        Args:
            context: Current state of the benchmark environment.

        Returns:
            ChaosEvent describing what happened.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up all resources created by this module.

        Must be idempotent — safe to call multiple times.
        """
        ...

    @abstractmethod
    def is_safe(self) -> bool:
        """
        Verify this module's operations are safe.

        Must return True for the module to be loaded.
        """
        ...

    def configure(self, params: dict[str, Any]) -> None:
        """Optional: configure the module with parameters from the chaos profile."""
        pass
