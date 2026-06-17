"""
conftest.py — pytest fixtures and Win32 mocks for DesktopAgentBench CI.

On non-Windows or headless CI environments, pywin32 (win32api, win32gui,
win32clipboard, comtypes) are not installed and must be mocked so that
import-time side-effects don't crash the test collection phase.

All mocks are lightweight stubs that provide the attribute surface used
by the benchmark source code without actually calling any Win32 API.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _make_win32_mocks() -> None:
    """Inject stub modules for pywin32 and comtypes if not available."""

    def _stub(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        mod.__all__ = []
        return mod

    # --- win32api ----------------------------------------------------------
    if "win32api" not in sys.modules:
        m = _stub("win32api")
        m.keybd_event = MagicMock()
        m.SetCursorPos = MagicMock()
        m.GetSystemMetrics = MagicMock(return_value=1920)
        m.mouse_event = MagicMock()
        sys.modules["win32api"] = m

    # --- win32con ----------------------------------------------------------
    if "win32con" not in sys.modules:
        m = _stub("win32con")
        # Key codes
        for attr, val in [
            ("VK_CONTROL", 0x11), ("VK_SHIFT", 0x10), ("VK_MENU", 0x12),
            ("VK_TAB", 0x09), ("VK_RETURN", 0x0D), ("VK_ESCAPE", 0x1B),
            ("VK_SPACE", 0x20), ("VK_BACK", 0x08), ("VK_DELETE", 0x2E),
            ("KEYEVENTF_KEYUP", 0x0002),
            ("SW_SHOW", 5), ("SW_RESTORE", 9), ("SW_MINIMIZE", 6),
            ("WM_SETREDRAW", 0x000B), ("GWL_STYLE", -16),
            ("WS_VSCROLL", 0x00200000), ("WS_HSCROLL", 0x00100000),
            ("SB_BOTH", 3), ("SB_VERT", 1), ("SB_HORZ", 0),
            ("MOUSEEVENTF_LEFTDOWN", 0x0002), ("MOUSEEVENTF_LEFTUP", 0x0004),
            ("MOUSEEVENTF_RIGHTDOWN", 0x0008), ("MOUSEEVENTF_RIGHTUP", 0x0010),
            ("MOUSEEVENTF_ABSOLUTE", 0x8000), ("MOUSEEVENTF_MOVE", 0x0001),
        ]:
            setattr(m, attr, val)
        sys.modules["win32con"] = m

    # --- win32gui ----------------------------------------------------------
    if "win32gui" not in sys.modules:
        m = _stub("win32gui")
        m.EnumWindows = MagicMock()
        m.GetWindowText = MagicMock(return_value="")
        m.GetClassName = MagicMock(return_value="")
        m.IsWindowVisible = MagicMock(return_value=False)
        m.IsIconic = MagicMock(return_value=False)
        m.ShowWindow = MagicMock()
        m.SetForegroundWindow = MagicMock()
        m.GetForegroundWindow = MagicMock(return_value=0)
        m.GetWindowRect = MagicMock(return_value=(0, 0, 800, 600))
        m.FindWindow = MagicMock(return_value=0)
        m.ShowScrollBar = MagicMock()
        m.SetWindowLong = MagicMock()
        m.GetWindowLong = MagicMock(return_value=0)
        m.SendMessage = MagicMock()
        m.PostMessage = MagicMock()
        sys.modules["win32gui"] = m

    # --- win32process ------------------------------------------------------
    if "win32process" not in sys.modules:
        m = _stub("win32process")
        m.GetWindowThreadProcessId = MagicMock(return_value=(0, 0))
        sys.modules["win32process"] = m

    # --- win32clipboard ----------------------------------------------------
    if "win32clipboard" not in sys.modules:
        m = _stub("win32clipboard")
        m.OpenClipboard = MagicMock()
        m.CloseClipboard = MagicMock()
        m.EmptyClipboard = MagicMock()
        m.SetClipboardText = MagicMock()
        m.GetClipboardData = MagicMock(return_value="")
        m.CF_UNICODETEXT = 13
        sys.modules["win32clipboard"] = m

    # --- pywintypes --------------------------------------------------------
    if "pywintypes" not in sys.modules:
        m = _stub("pywintypes")
        m.error = Exception
        sys.modules["pywintypes"] = m

    # --- comtypes ----------------------------------------------------------
    if "comtypes" not in sys.modules:
        sys.modules["comtypes"] = _stub("comtypes")
    if "comtypes.client" not in sys.modules:
        sys.modules["comtypes.client"] = _stub("comtypes.client")

    # --- ctypes.wintypes (usually present on non-Windows as well, but ensure)
    try:
        import ctypes.wintypes  # noqa: F401
    except ImportError:
        sys.modules["ctypes.wintypes"] = _stub("ctypes.wintypes")


# Apply mocks at collection time (before any src.* imports)
_make_win32_mocks()
