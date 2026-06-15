"""
Win32 API wrappers for DesktopAgentBench.

Provides safe, typed ctypes wrappers for common Win32 functions
used by chaos modules and platform utilities.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)

# Load DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class WindowRect:
    """Window rectangle (screen coordinates)."""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass
class WindowInfo:
    """Basic information about a window."""
    hwnd: int
    title: str
    class_name: str
    rect: WindowRect
    is_visible: bool
    process_id: int


# ---------------------------------------------------------------------------
# Window operations
# ---------------------------------------------------------------------------

def get_foreground_window() -> int:
    """Return the handle of the current foreground window."""
    return user32.GetForegroundWindow()


def set_foreground_window(hwnd: int) -> bool:
    """Bring a window to the foreground."""
    return bool(user32.SetForegroundWindow(hwnd))


def get_window_text(hwnd: int) -> str:
    """Get the title text of a window."""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_window_class(hwnd: int) -> str:
    """Get the class name of a window."""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_window_rect(hwnd: int) -> WindowRect:
    """Get the bounding rectangle of a window."""
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return WindowRect(rect.left, rect.top, rect.right, rect.bottom)


def is_window_visible(hwnd: int) -> bool:
    """Check if a window is visible."""
    return bool(user32.IsWindowVisible(hwnd))


def is_window_valid(hwnd: int) -> bool:
    """Check if a window handle is valid."""
    return bool(user32.IsWindow(hwnd))


def move_window(
    hwnd: int, x: int, y: int, width: int, height: int, repaint: bool = True
) -> bool:
    """Move and resize a window."""
    return bool(user32.MoveWindow(hwnd, x, y, width, height, repaint))


def show_window(hwnd: int, cmd: int) -> bool:
    """Show/hide/minimize/maximize a window."""
    return bool(user32.ShowWindow(hwnd, cmd))


def get_window_process_id(hwnd: int) -> int:
    """Get the process ID that owns a window."""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


# ---------------------------------------------------------------------------
# Window enumeration
# ---------------------------------------------------------------------------

# Type for EnumWindows callback
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def enum_windows(callback: Callable[[int], bool]) -> None:
    """
    Enumerate all top-level windows.

    Args:
        callback: Function receiving hwnd, returning True to continue.
    """
    @WNDENUMPROC
    def _cb(hwnd: int, lparam: int) -> bool:
        return callback(hwnd)

    user32.EnumWindows(_cb, 0)


def find_windows_by_title(title_substring: str) -> list[WindowInfo]:
    """Find all visible windows whose title contains the substring."""
    results: list[WindowInfo] = []

    def _check(hwnd: int) -> bool:
        if not is_window_visible(hwnd):
            return True
        title = get_window_text(hwnd)
        if title_substring.lower() in title.lower():
            results.append(WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=get_window_class(hwnd),
                rect=get_window_rect(hwnd),
                is_visible=True,
                process_id=get_window_process_id(hwnd),
            ))
        return True

    enum_windows(_check)
    return results


def find_windows_by_process(process_id: int) -> list[WindowInfo]:
    """Find all visible windows owned by a process."""
    results: list[WindowInfo] = []

    def _check(hwnd: int) -> bool:
        if not is_window_visible(hwnd):
            return True
        pid = get_window_process_id(hwnd)
        if pid == process_id:
            results.append(WindowInfo(
                hwnd=hwnd,
                title=get_window_text(hwnd),
                class_name=get_window_class(hwnd),
                rect=get_window_rect(hwnd),
                is_visible=True,
                process_id=pid,
            ))
        return True

    enum_windows(_check)
    return results


# ---------------------------------------------------------------------------
# Screen info
# ---------------------------------------------------------------------------

def get_screen_resolution() -> tuple[int, int]:
    """Return the primary screen resolution."""
    width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    return (width, height)


def get_cursor_position() -> tuple[int, int]:
    """Return the current cursor position."""
    point = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return (point.x, point.y)
