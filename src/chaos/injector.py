"""
Central chaos injector for DesktopAgentBench.

Orchestrates all chaos modules, manages their lifecycle, and provides
a unified interface for the benchmark orchestrator. All injections are
hidden from the agent under test.
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.core.config import ChaosProfileConfig, ChaosModuleName
from src.chaos.scheduler import ChaosScheduler
from src.chaos.registry import get_registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chaos module base class
# ---------------------------------------------------------------------------

@dataclass
class ChaosContext:
    """Context passed to chaos modules during injection."""
    target_window_hwnd: int | None = None
    target_window_title: str = ""
    target_process_name: str = ""
    screen_resolution: tuple[int, int] = (1920, 1080)
    elapsed_seconds: float = 0.0
    injection_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosEvent:
    """Record of a chaos injection that occurred."""
    module_name: str
    event_type: str  # "injected", "cleaned_up", "failed"
    timestamp: float
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    affected_hwnd: int | None = None
    cleanup_required: bool = False


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


# ---------------------------------------------------------------------------
# Central injector
# ---------------------------------------------------------------------------

class ChaosInjector:
    """
    Central chaos injection controller.

    Manages the lifecycle of all chaos modules, schedules randomized
    injections, and records all events for evaluation.

    The injector is hidden from the agent — no agent API exposes
    chaos state or timing information.
    """

    def __init__(self) -> None:
        self._profile: ChaosProfileConfig | None = None
        self._scheduler: ChaosScheduler | None = None
        self._active_modules: dict[str, ChaosModule] = {}
        self._context = ChaosContext()
        self._event_log: list[ChaosEvent] = []
        self._lock = threading.Lock()
        self._running = False
        self._start_time: float = 0.0

    def configure(
        self,
        profile: ChaosProfileConfig,
        target_hwnd: int | None = None,
        target_title: str = "",
        target_process: str = "",
        screen_resolution: tuple[int, int] = (1920, 1080),
    ) -> None:
        """
        Configure the injector with a chaos profile and target info.

        Must be called before start().
        """
        self._profile = profile
        self._context = ChaosContext(
            target_window_hwnd=target_hwnd,
            target_window_title=target_title,
            target_process_name=target_process,
            screen_resolution=screen_resolution,
        )

        # Initialize scheduler
        self._scheduler = ChaosScheduler(
            seed=profile.randomization.seed,
            jitter_pct=profile.randomization.injection_jitter_pct,
        )

        # Load and configure enabled modules
        registry = get_registry()
        registry.discover_builtins()

        self._active_modules.clear()
        for module_name in profile.get_enabled_modules():
            module_class = registry.get(module_name.value)
            if module_class is None:
                logger.warning(f"Chaos module '{module_name.value}' not found in registry")
                continue

            module = module_class()
            if not module.is_safe():
                logger.error(
                    f"Chaos module '{module_name.value}' failed safety check — skipping"
                )
                continue

            module_config = profile.get_module_config(module_name)
            module.configure(module_config.model_dump())
            self._active_modules[module_name.value] = module
            logger.info(f"Loaded chaos module: {module_name.value}")

    def start(self) -> None:
        """
        Start chaos injection.

        All injections happen in background threads, invisible to the agent.
        """
        if not self._profile or not self._scheduler:
            logger.warning("ChaosInjector.start() called without configure()")
            return

        self._running = True
        self._start_time = time.time()
        self._event_log.clear()
        self._scheduler.start()

        # Schedule recurring injections for each active module
        for module_name, module in self._active_modules.items():
            config = self._profile.get_module_config(ChaosModuleName(module_name))

            def make_callback(m: ChaosModule) -> callable:
                def _inject() -> None:
                    self._do_injection(m)
                return _inject

            self._scheduler.schedule_recurring(
                module_name=module_name,
                frequency_range=config.frequency_range,
                callback=make_callback(module),
            )

        enabled_names = list(self._active_modules.keys())
        logger.info(f"Chaos injection started with modules: {enabled_names}")

    def stop(self) -> None:
        """Stop all chaos injections."""
        self._running = False
        if self._scheduler:
            self._scheduler.stop()
        logger.info(f"Chaos injection stopped. {len(self._event_log)} events recorded.")

    def cleanup(self) -> None:
        """Clean up all active chaos modules."""
        for name, module in self._active_modules.items():
            try:
                module.cleanup()
                with self._lock:
                    self._event_log.append(ChaosEvent(
                        module_name=name,
                        event_type="cleaned_up",
                        timestamp=time.time(),
                    ))
            except Exception as e:
                logger.error(f"Cleanup failed for module '{name}': {e}")

        self._active_modules.clear()

    def get_event_log(self) -> list[ChaosEvent]:
        """Return a copy of the chaos event log."""
        with self._lock:
            return list(self._event_log)

    def get_active_module_names(self) -> list[str]:
        """Return names of currently injecting modules."""
        return list(self._active_modules.keys())

    @property
    def is_running(self) -> bool:
        return self._running

    def _do_injection(self, module: ChaosModule) -> None:
        """Execute a single injection (called from scheduler thread)."""
        if not self._running:
            return

        # Update context timing
        self._context.elapsed_seconds = time.time() - self._start_time

        try:
            event = module.inject(self._context)
            with self._lock:
                self._event_log.append(event)
            logger.debug(f"Chaos injected: {event.module_name} -> {event.event_type}")
        except Exception as e:
            logger.error(f"Injection failed for {module.name()}: {e}")
            with self._lock:
                self._event_log.append(ChaosEvent(
                    module_name=module.name(),
                    event_type="failed",
                    timestamp=time.time(),
                    details={"error": str(e)},
                ))
