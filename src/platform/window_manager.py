"""
Window manager for DesktopAgentBench.

Higher-level window operations: finding target app windows,
waiting for windows to appear, and managing window state.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.platform.win32_utils import (
    WindowInfo,
    find_windows_by_title,
    find_windows_by_process,
    get_window_text,
    get_window_rect,
    is_window_visible,
    is_window_valid,
    set_foreground_window,
    get_foreground_window,
    get_screen_resolution,
)

logger = logging.getLogger(__name__)


class WindowManager:
    """Manages window discovery and manipulation for benchmark tasks."""

    def find_app_window(
        self,
        title_hint: str | None = None,
        process_id: int | None = None,
        process_name: str | None = None,
    ) -> WindowInfo | None:
        """
        Find the primary window of a target application.

        Tries in order:
        1. By window title substring
        2. By process ID
        3. By process name -> PID -> windows
        """
        if title_hint:
            windows = find_windows_by_title(title_hint)
            if windows:
                # Prefer the largest visible window
                windows.sort(key=lambda w: w.rect.width * w.rect.height, reverse=True)
                return windows[0]

        if process_id:
            windows = find_windows_by_process(process_id)
            if windows:
                windows.sort(key=lambda w: w.rect.width * w.rect.height, reverse=True)
                return windows[0]

        if process_name:
            pid = self._get_pid_by_name(process_name)
            if pid:
                windows = find_windows_by_process(pid)
                if windows:
                    windows.sort(key=lambda w: w.rect.width * w.rect.height, reverse=True)
                    return windows[0]

        return None

    def wait_for_window(
        self,
        title_hint: str,
        timeout_seconds: float = 30.0,
        poll_interval: float = 0.5,
    ) -> WindowInfo | None:
        """
        Wait for a window with the given title to appear.

        Returns the WindowInfo when found, or None on timeout.
        """
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            window = self.find_app_window(title_hint=title_hint)
            if window:
                logger.debug(f"Window found: '{window.title}' (hwnd={window.hwnd})")
                return window
            time.sleep(poll_interval)

        logger.warning(f"Timed out waiting for window: '{title_hint}'")
        return None

    def focus_window(self, hwnd: int) -> bool:
        """Bring a window to the foreground and give it focus."""
        if not is_window_valid(hwnd):
            return False
        return set_foreground_window(hwnd)

    def get_all_visible_windows(self) -> list[WindowInfo]:
        """Return info for all visible top-level windows."""
        results: list[WindowInfo] = []

        from src.platform.win32_utils import enum_windows, get_window_class, get_window_process_id

        def _collect(hwnd: int) -> bool:
            if is_window_visible(hwnd):
                title = get_window_text(hwnd)
                if title:  # skip untitled windows
                    results.append(WindowInfo(
                        hwnd=hwnd,
                        title=title,
                        class_name=get_window_class(hwnd),
                        rect=get_window_rect(hwnd),
                        is_visible=True,
                        process_id=get_window_process_id(hwnd),
                    ))
            return True

        enum_windows(_collect)
        return results

    @staticmethod
    def _get_pid_by_name(process_name: str) -> int | None:
        """Find the PID of a running process by name."""
        try:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.strip('"').split('","')
                if len(parts) >= 2 and process_name.lower() in parts[0].lower():
                    return int(parts[1])
        except Exception as e:
            logger.debug(f"PID lookup failed for {process_name}: {e}")
        return None
