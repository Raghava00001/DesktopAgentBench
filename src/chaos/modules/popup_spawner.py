"""
Popup spawner chaos module.

Spawns fake system dialogs (Windows Update, OneDrive sync, antivirus alerts)
that look authentic but are entirely controlled by the benchmark process.
No actual system changes are made.
"""

from __future__ import annotations

import ctypes
import logging
import random
import threading
import time
from typing import Any

from src.chaos.injector import ChaosModule, ChaosContext, ChaosEvent

logger = logging.getLogger(__name__)

# Win32 constants
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040
MB_ICONWARNING = 0x00000030
MB_SYSTEMMODAL = 0x00001000

# Popup templates — realistic but clearly benchmark-controlled
_POPUP_TEMPLATES = {
    "update": {
        "title": "Windows Update",
        "messages": [
            "Updates are available. Restart now to install.",
            "Your device will restart in 15 minutes to finish installing updates.",
            "Feature update to Windows is ready to install.",
        ],
    },
    "sync": {
        "title": "OneDrive",
        "messages": [
            "Syncing your files... 47 files remaining.",
            "OneDrive is up to date.",
            "Some files couldn't be synced. Click to view details.",
        ],
    },
    "notification": {
        "title": "Windows Security",
        "messages": [
            "Virus & threat protection: No action needed.",
            "Quick scan completed. No threats found.",
            "Your device is protected.",
        ],
    },
    "restart": {
        "title": "System",
        "messages": [
            "An application is requesting a restart.",
            "Please save your work. A restart has been scheduled.",
        ],
    },
}


class PopupSpawner(ChaosModule):
    """
    Spawns fake system-style popup dialogs.

    Uses Win32 MessageBox on a background thread. The popups are owned
    by the benchmark process and auto-dismiss after a configurable duration.
    """

    def __init__(self) -> None:
        self._popup_types: list[str] = ["update", "sync", "notification"]
        self._duration_range: tuple[float, float] = (3.0, 10.0)
        self._max_concurrent: int = 2
        self._active_threads: list[threading.Thread] = []
        self._active_hwnds: list[int] = []
        self._rng = random.Random()
        self._lock = threading.Lock()

    def name(self) -> str:
        return "popup_spawner"

    def configure(self, params: dict[str, Any]) -> None:
        self._popup_types = params.get("popup_types", self._popup_types)
        self._duration_range = tuple(params.get("duration_range", self._duration_range))
        self._max_concurrent = params.get("max_concurrent", self._max_concurrent)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Spawn a fake popup dialog."""
        # Respect concurrency limit
        with self._lock:
            active = sum(1 for t in self._active_threads if t.is_alive())
            if active >= self._max_concurrent:
                return ChaosEvent(
                    module_name=self.name(),
                    event_type="skipped",
                    timestamp=time.time(),
                    details={"reason": "max_concurrent reached"},
                )

        popup_type = self._rng.choice(self._popup_types)
        template = _POPUP_TEMPLATES.get(popup_type, _POPUP_TEMPLATES["notification"])
        title = template["title"]
        message = self._rng.choice(template["messages"])
        duration = self._rng.uniform(*self._duration_range)

        def _show_popup() -> None:
            try:
                # Use MessageBoxTimeout (undocumented but widely used)
                # Falls back to regular MessageBox if not available
                user32 = ctypes.windll.user32
                timeout_ms = int(duration * 1000)

                # Try MessageBoxTimeoutW first (auto-dismisses)
                try:
                    fn = ctypes.windll.user32.MessageBoxTimeoutW
                    fn(
                        None,
                        message,
                        f"[DAB] {title}",
                        MB_OK | MB_ICONINFORMATION,
                        0,
                        timeout_ms,
                    )
                except AttributeError:
                    # Fallback: show for duration then close via thread
                    timer = threading.Timer(duration, lambda: user32.PostQuitMessage(0))
                    timer.daemon = True
                    timer.start()
                    user32.MessageBoxW(
                        None,
                        message,
                        f"[DAB] {title}",
                        MB_OK | MB_ICONINFORMATION,
                    )
            except Exception as e:
                logger.debug(f"Popup display failed: {e}")

        thread = threading.Thread(target=_show_popup, daemon=True, name=f"popup-{popup_type}")
        with self._lock:
            self._active_threads.append(thread)
        thread.start()

        return ChaosEvent(
            module_name=self.name(),
            event_type="injected",
            timestamp=time.time(),
            duration_seconds=duration,
            details={
                "popup_type": popup_type,
                "title": title,
                "message": message,
            },
            cleanup_required=True,
        )

    def cleanup(self) -> None:
        """Dismiss any remaining popups."""
        with self._lock:
            self._active_threads = [t for t in self._active_threads if t.is_alive()]
            # Active MessageBoxes will be auto-dismissed by timeout
            self._active_threads.clear()

    def is_safe(self) -> bool:
        """PopupSpawner is safe — only creates transient MessageBox windows."""
        return True
