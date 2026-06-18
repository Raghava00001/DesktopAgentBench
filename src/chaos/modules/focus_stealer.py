"""
Focus stealer chaos module.

Periodically steals window focus from the target application by
bringing a distractor window to the foreground. Uses only
benchmark-owned windows — never manipulates external applications.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
import time
from typing import Any

from src.chaos.interface import ChaosModule, ChaosContext
from src.chaos.injector import ChaosEvent

logger = logging.getLogger(__name__)

# Win32 constants
SW_SHOW = 5
SW_HIDE = 0
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2


class FocusStealer(ChaosModule):
    """
    Steals window focus by creating and foregrounding a distractor window.

    Uses SetForegroundWindow and FlashWindowEx to simulate the common
    annoyance of background apps demanding attention.
    """

    def __init__(self) -> None:
        self._steal_duration_range: tuple[float, float] = (1.0, 3.0)
        self._distractor_hwnd: int | None = None
        self._lock = threading.Lock()

    def name(self) -> str:
        return "focus_stealer"

    def configure(self, params: dict[str, Any]) -> None:
        self._steal_duration_range = tuple(
            params.get("steal_duration_range", self._steal_duration_range)
        )

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Steal focus from the target window."""
        import random
        duration = random.uniform(*self._steal_duration_range)

        try:
            user32 = ctypes.windll.user32

            # Create a minimal distractor window if we don't have one
            if not self._distractor_hwnd or not user32.IsWindow(self._distractor_hwnd):
                self._create_distractor_window()

            if self._distractor_hwnd:
                # Bring distractor to foreground
                user32.ShowWindow(self._distractor_hwnd, SW_SHOW)
                user32.SetForegroundWindow(self._distractor_hwnd)

                # Flash the taskbar button for extra distraction
                self._flash_window(self._distractor_hwnd)

                # Schedule hiding after duration
                def _restore():
                    time.sleep(duration)
                    try:
                        if self._distractor_hwnd and user32.IsWindow(self._distractor_hwnd):
                            user32.ShowWindow(self._distractor_hwnd, SW_HIDE)
                        # Restore focus to the target if available
                        if context.target_window_hwnd and user32.IsWindow(
                            context.target_window_hwnd
                        ):
                            user32.SetForegroundWindow(context.target_window_hwnd)
                    except Exception:
                        pass

                t = threading.Thread(target=_restore, daemon=True)
                t.start()

                return ChaosEvent(
                    module_name=self.name(),
                    event_type="injected",
                    timestamp=time.time(),
                    duration_seconds=duration,
                    details={"distractor_hwnd": self._distractor_hwnd},
                    affected_hwnd=context.target_window_hwnd,
                    cleanup_required=True,
                )

        except Exception as e:
            logger.debug(f"Focus steal failed: {e}")

        return ChaosEvent(
            module_name=self.name(),
            event_type="failed",
            timestamp=time.time(),
            details={"error": "Could not steal focus"},
        )

    def cleanup(self) -> None:
        """Destroy the distractor window."""
        if self._distractor_hwnd:
            try:
                user32 = ctypes.windll.user32
                if user32.IsWindow(self._distractor_hwnd):
                    user32.DestroyWindow(self._distractor_hwnd)
            except Exception:
                pass
            self._distractor_hwnd = None

    def is_safe(self) -> bool:
        return True

    def _create_distractor_window(self) -> None:
        """Create a small distractor window owned by the benchmark process."""
        try:
            user32 = ctypes.windll.user32
            # Use a simple static window class
            self._distractor_hwnd = user32.CreateWindowExW(
                0x00000008,  # WS_EX_TOPMOST
                "Static",  # predefined window class
                "[DAB] Background Process",
                0x00CF0000 | 0x10000000,  # WS_OVERLAPPEDWINDOW | WS_VISIBLE
                100, 100, 350, 200,
                None, None, None, None,
            )
            # Immediately hide — will be shown during injection
            if self._distractor_hwnd:
                user32.ShowWindow(self._distractor_hwnd, SW_HIDE)
        except Exception as e:
            logger.debug(f"Failed to create distractor window: {e}")

    def _flash_window(self, hwnd: int) -> None:
        """Flash the window's taskbar button."""
        try:
            user32 = ctypes.windll.user32
            # FLASHWINFO structure
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("hwnd", ctypes.wintypes.HWND),
                    ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint),
                    ("dwTimeout", ctypes.c_uint),
                ]

            fwi = FLASHWINFO()
            fwi.cbSize = ctypes.sizeof(FLASHWINFO)
            fwi.hwnd = hwnd
            fwi.dwFlags = 0x00000003  # FLASHW_ALL
            fwi.uCount = 3
            fwi.dwTimeout = 0
            user32.FlashWindowEx(ctypes.byref(fwi))
        except Exception:
            pass
