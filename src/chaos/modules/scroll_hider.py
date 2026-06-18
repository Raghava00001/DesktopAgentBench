"""
Scroll hider chaos module.

Hides scrollbars or modifies scroll behavior on target windows,
forcing agents to handle content navigation without visible scroll
indicators — a common challenge in modern UIs.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import time
from typing import Any

from src.chaos.interface import ChaosModule, ChaosContext
from src.chaos.injector import ChaosEvent

logger = logging.getLogger(__name__)

# Win32 constants
SB_HORZ = 0
SB_VERT = 1
SB_BOTH = 3
GWL_STYLE = -16
WS_VSCROLL = 0x00200000
WS_HSCROLL = 0x00100000


class ScrollHider(ChaosModule):
    """
    Hides scrollbars on the target window.

    Uses the ShowScrollBar Win32 API to hide vertical and/or horizontal
    scrollbars. The scroll functionality still works (keyboard, mouse
    wheel), but the visual indicator is removed.
    """

    def __init__(self) -> None:
        self._hide_vertical: bool = True
        self._hide_horizontal: bool = False
        self._modified_hwnds: list[tuple[int, int]] = []  # (hwnd, original_style)
        self._lock = __import__("threading").Lock()

    def name(self) -> str:
        return "scroll_hider"

    def configure(self, params: dict[str, Any]) -> None:
        self._hide_vertical = params.get("hide_vertical", self._hide_vertical)
        self._hide_horizontal = params.get("hide_horizontal", self._hide_horizontal)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Hide scrollbars on the target window."""
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

            # Save original style
            original_style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            with self._lock:
                self._modified_hwnds.append((hwnd, original_style))

            hidden = []

            if self._hide_vertical:
                user32.ShowScrollBar(hwnd, SB_VERT, False)
                hidden.append("vertical")

            if self._hide_horizontal:
                user32.ShowScrollBar(hwnd, SB_HORZ, False)
                hidden.append("horizontal")

            if not hidden and (self._hide_vertical or self._hide_horizontal):
                user32.ShowScrollBar(hwnd, SB_BOTH, False)
                hidden = ["both"]

            return ChaosEvent(
                module_name=self.name(),
                event_type="injected",
                timestamp=time.time(),
                details={"hidden_scrollbars": hidden},
                affected_hwnd=hwnd,
                cleanup_required=True,
            )

        except Exception as e:
            logger.debug(f"Scroll hide failed: {e}")
            return ChaosEvent(
                module_name=self.name(),
                event_type="failed",
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def cleanup(self) -> None:
        """Restore scrollbars on all modified windows."""
        user32 = ctypes.windll.user32
        with self._lock:
            for hwnd, original_style in self._modified_hwnds:
                try:
                    if user32.IsWindow(hwnd):
                        # Restore scrollbars
                        user32.ShowScrollBar(hwnd, SB_BOTH, True)
                        # Restore original window style
                        user32.SetWindowLongW(hwnd, GWL_STYLE, original_style)
                        user32.SetWindowPos(
                            hwnd, 0, 0, 0, 0, 0,
                            0x0001 | 0x0002 | 0x0004 | 0x0020  # NOMOVE|NOSIZE|NOZORDER|FRAMECHANGED
                        )
                except Exception:
                    pass
            self._modified_hwnds.clear()

    def is_safe(self) -> bool:
        """ShowScrollBar is fully reversible — safe."""
        return True
