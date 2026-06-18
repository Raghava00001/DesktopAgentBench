"""
UI delay chaos module.

Injects artificial delays before UI elements become interactive,
simulating slow-loading applications, laggy rendering, and
unresponsive controls.
"""

from __future__ import annotations

import ctypes
import logging
import random
import threading
import time
from typing import Any

from src.chaos.interface import ChaosModule, ChaosContext
from src.chaos.injector import ChaosEvent

logger = logging.getLogger(__name__)

# Win32 messages
WM_SETREDRAW = 0x000B


class UIDelay(ChaosModule):
    """
    Simulates UI rendering delays.

    Temporarily disables window redraw (WM_SETREDRAW) on the target
    window, creating a frozen/laggy appearance. The window continues
    to function but visually freezes for the delay duration.
    """

    def __init__(self) -> None:
        self._delay_range_ms: tuple[int, int] = (500, 2000)
        self._probability: float = 0.3
        self._rng = random.Random()
        self._frozen_hwnds: list[int] = []
        self._lock = threading.Lock()

    def name(self) -> str:
        return "ui_delay"

    def configure(self, params: dict[str, Any]) -> None:
        self._delay_range_ms = tuple(params.get("delay_range_ms", self._delay_range_ms))
        self._probability = params.get("probability", self._probability)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Inject a UI rendering delay on the target window."""
        # Probabilistic injection
        if self._rng.random() > self._probability:
            return ChaosEvent(
                module_name=self.name(),
                event_type="skipped",
                timestamp=time.time(),
                details={"reason": "probability_skip"},
            )

        hwnd = context.target_window_hwnd
        if not hwnd:
            return ChaosEvent(
                module_name=self.name(),
                event_type="skipped",
                timestamp=time.time(),
                details={"reason": "no_target_hwnd"},
            )

        delay_ms = self._rng.randint(*self._delay_range_ms)
        delay_sec = delay_ms / 1000.0

        try:
            user32 = ctypes.windll.user32

            # Disable redraw
            user32.SendMessageW(hwnd, WM_SETREDRAW, 0, 0)
            with self._lock:
                self._frozen_hwnds.append(hwnd)

            # Schedule re-enable
            def _unfreeze():
                time.sleep(delay_sec)
                try:
                    user32.SendMessageW(hwnd, WM_SETREDRAW, 1, 0)
                    # Force repaint
                    user32.InvalidateRect(hwnd, None, True)
                    user32.UpdateWindow(hwnd)
                    with self._lock:
                        if hwnd in self._frozen_hwnds:
                            self._frozen_hwnds.remove(hwnd)
                except Exception:
                    pass

            t = threading.Thread(target=_unfreeze, daemon=True)
            t.start()

            return ChaosEvent(
                module_name=self.name(),
                event_type="injected",
                timestamp=time.time(),
                duration_seconds=delay_sec,
                details={"delay_ms": delay_ms},
                affected_hwnd=hwnd,
                cleanup_required=True,
            )

        except Exception as e:
            logger.debug(f"UI delay injection failed: {e}")
            return ChaosEvent(
                module_name=self.name(),
                event_type="failed",
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def cleanup(self) -> None:
        """Re-enable redraw on any frozen windows."""
        user32 = ctypes.windll.user32
        with self._lock:
            for hwnd in self._frozen_hwnds:
                try:
                    if user32.IsWindow(hwnd):
                        user32.SendMessageW(hwnd, WM_SETREDRAW, 1, 0)
                        user32.InvalidateRect(hwnd, None, True)
                        user32.UpdateWindow(hwnd)
                except Exception:
                    pass
            self._frozen_hwnds.clear()

    def is_safe(self) -> bool:
        """WM_SETREDRAW is a standard, reversible message — safe."""
        return True
