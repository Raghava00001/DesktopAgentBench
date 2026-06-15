"""
Window resizer chaos module.

Randomly resizes, repositions, and snaps the target application window,
simulating accidental resize, multi-monitor movement, and Windows snap
behavior that agents must handle gracefully.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import random
import threading
import time
from typing import Any

from src.chaos.injector import ChaosModule, ChaosContext, ChaosEvent

logger = logging.getLogger(__name__)

# Resize magnitude presets (fraction of screen)
_MAGNITUDE_PRESETS = {
    "small": {"min_scale": 0.7, "max_scale": 0.95},
    "medium": {"min_scale": 0.4, "max_scale": 0.85},
    "large": {"min_scale": 0.2, "max_scale": 0.7},
}


class WindowResizer(ChaosModule):
    """
    Randomly resizes and repositions the target window.

    Simulates:
    - Accidental window resize
    - Window snap to half/quarter screen
    - Window move to different position
    - Minimize/restore cycles

    Always saves and can restore the original window geometry.
    """

    def __init__(self) -> None:
        self._resize_magnitude: str = "medium"
        self._original_rects: dict[int, tuple[int, int, int, int]] = {}
        self._rng = random.Random()
        self._lock = threading.Lock()

    def name(self) -> str:
        return "window_resizer"

    def configure(self, params: dict[str, Any]) -> None:
        self._resize_magnitude = params.get("resize_magnitude", self._resize_magnitude)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Resize or reposition the target window."""
        hwnd = context.target_window_hwnd
        if not hwnd:
            return ChaosEvent(
                module_name=self.name(),
                event_type="skipped",
                timestamp=time.time(),
                details={"reason": "no_target_hwnd"},
            )

        try:
            user32 = ctypes.windll.user32

            # Save original rect if not already saved
            if hwnd not in self._original_rects:
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                self._original_rects[hwnd] = (
                    rect.left, rect.top, rect.right, rect.bottom
                )

            # Choose a resize action
            action = self._rng.choice(["resize", "snap_left", "snap_right", "move", "shrink"])
            screen_w, screen_h = context.screen_resolution
            preset = _MAGNITUDE_PRESETS.get(self._resize_magnitude, _MAGNITUDE_PRESETS["medium"])

            if action == "resize":
                scale = self._rng.uniform(preset["min_scale"], preset["max_scale"])
                new_w = int(screen_w * scale)
                new_h = int(screen_h * scale)
                new_x = self._rng.randint(0, max(0, screen_w - new_w))
                new_y = self._rng.randint(0, max(0, screen_h - new_h))

            elif action == "snap_left":
                new_x, new_y = 0, 0
                new_w, new_h = screen_w // 2, screen_h

            elif action == "snap_right":
                new_x = screen_w // 2
                new_y = 0
                new_w, new_h = screen_w // 2, screen_h

            elif action == "move":
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                new_x = self._rng.randint(0, max(0, screen_w - w))
                new_y = self._rng.randint(0, max(0, screen_h - h))
                new_w, new_h = w, h

            else:  # shrink
                scale = self._rng.uniform(0.3, 0.6)
                new_w = int(screen_w * scale)
                new_h = int(screen_h * scale)
                new_x = (screen_w - new_w) // 2
                new_y = (screen_h - new_h) // 2

            user32.MoveWindow(hwnd, new_x, new_y, new_w, new_h, True)

            return ChaosEvent(
                module_name=self.name(),
                event_type="injected",
                timestamp=time.time(),
                details={
                    "action": action,
                    "new_rect": [new_x, new_y, new_w, new_h],
                    "magnitude": self._resize_magnitude,
                },
                affected_hwnd=hwnd,
                cleanup_required=True,
            )

        except Exception as e:
            logger.debug(f"Window resize failed: {e}")
            return ChaosEvent(
                module_name=self.name(),
                event_type="failed",
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def cleanup(self) -> None:
        """Restore all windows to their original geometry."""
        user32 = ctypes.windll.user32
        with self._lock:
            for hwnd, (left, top, right, bottom) in self._original_rects.items():
                try:
                    if user32.IsWindow(hwnd):
                        w = right - left
                        h = bottom - top
                        user32.MoveWindow(hwnd, left, top, w, h, True)
                except Exception:
                    pass
            self._original_rects.clear()

    def is_safe(self) -> bool:
        """Window resizing is fully reversible and safe."""
        return True
