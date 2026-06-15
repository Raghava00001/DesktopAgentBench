"""
Randomized chaos injection scheduler for DesktopAgentBench.

Uses a Poisson-process-inspired model with configurable jitter
to produce realistic, unpredictable disruption timing.
"""

from __future__ import annotations

import random
import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledEvent:
    """A scheduled chaos injection event."""
    fire_time: float  # absolute time
    module_name: str
    callback: Callable[[], None]
    event_id: str = ""


class ChaosScheduler:
    """
    Schedules chaos injection events with randomized timing.

    Each enabled module gets its own independent timer based on the
    module's frequency_range setting, with added jitter.
    """

    def __init__(self, seed: int | None = None, jitter_pct: float = 20.0) -> None:
        self._rng = random.Random(seed)
        self._jitter_pct = jitter_pct
        self._timers: list[threading.Timer] = []
        self._events: list[ScheduledEvent] = []
        self._lock = threading.Lock()
        self._running = False
        self._start_time: float = 0.0
        self._event_counter = 0

    @property
    def actual_seed(self) -> int | None:
        """Return the seed used for reproducibility logging."""
        return getattr(self._rng, "_seed", None)

    def schedule_recurring(
        self,
        module_name: str,
        frequency_range: tuple[float, float],
        callback: Callable[[], None],
    ) -> None:
        """
        Schedule a recurring chaos event for a module.

        The first event fires after a random delay within frequency_range.
        Subsequent events re-schedule themselves with fresh randomness.
        """
        if not self._running:
            return

        delay = self._random_delay(frequency_range)

        event_id = f"{module_name}_{self._event_counter}"
        self._event_counter += 1

        def _fire() -> None:
            if not self._running:
                return
            try:
                callback()
            except Exception as e:
                logger.error(f"Chaos event {module_name} failed: {e}")

            with self._lock:
                self._events.append(ScheduledEvent(
                    fire_time=time.time(),
                    module_name=module_name,
                    callback=callback,
                    event_id=event_id,
                ))

            # Re-schedule
            if self._running:
                self.schedule_recurring(module_name, frequency_range, callback)

        timer = threading.Timer(delay, _fire)
        timer.daemon = True
        timer.name = f"chaos-{module_name}"

        with self._lock:
            self._timers.append(timer)

        timer.start()

    def schedule_once(
        self,
        module_name: str,
        delay: float,
        callback: Callable[[], None],
    ) -> None:
        """Schedule a single chaos event after a fixed delay."""
        if not self._running:
            return

        event_id = f"{module_name}_once_{self._event_counter}"
        self._event_counter += 1

        def _fire() -> None:
            if not self._running:
                return
            try:
                callback()
            except Exception as e:
                logger.error(f"Chaos event {module_name} failed: {e}")
            with self._lock:
                self._events.append(ScheduledEvent(
                    fire_time=time.time(),
                    module_name=module_name,
                    callback=callback,
                    event_id=event_id,
                ))

        timer = threading.Timer(delay, _fire)
        timer.daemon = True
        timer.name = f"chaos-{module_name}-once"

        with self._lock:
            self._timers.append(timer)

        timer.start()

    def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        self._start_time = time.time()

    def stop(self) -> None:
        """Stop all scheduled events."""
        self._running = False
        with self._lock:
            for timer in self._timers:
                timer.cancel()
            self._timers.clear()

    def get_fired_events(self) -> list[ScheduledEvent]:
        """Return all events that have fired."""
        with self._lock:
            return list(self._events)

    def _random_delay(self, frequency_range: tuple[float, float]) -> float:
        """
        Generate a random delay within frequency_range, plus jitter.
        """
        base = self._rng.uniform(frequency_range[0], frequency_range[1])
        jitter = base * (self._jitter_pct / 100.0)
        return max(0.1, base + self._rng.uniform(-jitter, jitter))
