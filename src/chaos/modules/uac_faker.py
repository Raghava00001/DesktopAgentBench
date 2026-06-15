"""
UAC faker chaos module.

Displays a convincing but entirely fake UAC (User Account Control) consent
dialog. No actual elevation occurs — the dialog is a plain WinForms-style
window rendered by the benchmark process with a dimmed background overlay.
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


class UACFaker(ChaosModule):
    """
    Shows a fake UAC consent dialog.

    The dialog:
    - Looks like a UAC prompt (grey background, shield-like styling)
    - Has "Yes" and "No" buttons (both dismiss the dialog)
    - Optionally dims the background
    - Auto-dismisses after a timeout
    - Is clearly tagged [DAB] in the title for transparency

    No actual privilege escalation occurs.
    """

    def __init__(self) -> None:
        self._dim_background: bool = True
        self._require_interaction: bool = True
        self._auto_dismiss_seconds: float = 15.0
        self._overlay_hwnd: int | None = None
        self._dialog_hwnd: int | None = None
        self._lock = threading.Lock()

    def name(self) -> str:
        return "uac_faker"

    def configure(self, params: dict[str, Any]) -> None:
        self._dim_background = params.get("dim_background", self._dim_background)
        self._require_interaction = params.get("require_interaction", self._require_interaction)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Show a fake UAC dialog."""
        try:
            user32 = ctypes.windll.user32

            # Create a semi-transparent overlay to dim the background
            if self._dim_background:
                self._create_dim_overlay(context.screen_resolution)

            # Show the fake UAC dialog (using MessageBox styled as system-modal)
            def _show_dialog():
                try:
                    # MessageBoxTimeoutW for auto-dismiss
                    timeout_ms = int(self._auto_dismiss_seconds * 1000)
                    try:
                        fn = user32.MessageBoxTimeoutW
                        fn(
                            None,
                            "Do you want to allow this app to make changes to your device?\n\n"
                            "Program name: benchmark_task.exe\n"
                            "Verified publisher: DesktopAgentBench\n",
                            "[DAB] User Account Control",
                            0x00000004 | 0x00000030 | 0x00001000,  # MB_YESNO | MB_ICONWARNING | MB_SYSTEMMODAL
                            0,
                            timeout_ms,
                        )
                    except AttributeError:
                        user32.MessageBoxW(
                            None,
                            "Do you want to allow this app to make changes to your device?\n\n"
                            "[DAB Simulated UAC - No actual elevation]",
                            "[DAB] User Account Control",
                            0x00000004 | 0x00000030,  # MB_YESNO | MB_ICONWARNING
                        )
                except Exception as e:
                    logger.debug(f"UAC dialog failed: {e}")
                finally:
                    self._remove_dim_overlay()

            t = threading.Thread(target=_show_dialog, daemon=True, name="uac-faker")
            t.start()

            return ChaosEvent(
                module_name=self.name(),
                event_type="injected",
                timestamp=time.time(),
                duration_seconds=self._auto_dismiss_seconds,
                details={
                    "dim_background": self._dim_background,
                    "auto_dismiss_seconds": self._auto_dismiss_seconds,
                },
                cleanup_required=True,
            )

        except Exception as e:
            logger.debug(f"UAC faker failed: {e}")
            return ChaosEvent(
                module_name=self.name(),
                event_type="failed",
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def cleanup(self) -> None:
        """Remove any remaining overlays or dialogs."""
        self._remove_dim_overlay()

    def is_safe(self) -> bool:
        """No actual elevation — just a styled MessageBox."""
        return True

    def _create_dim_overlay(self, screen_res: tuple[int, int]) -> None:
        """Create a semi-transparent overlay window to dim the screen."""
        try:
            user32 = ctypes.windll.user32
            w, h = screen_res

            # Create a layered, topmost, tool window for the dim effect
            self._overlay_hwnd = user32.CreateWindowExW(
                0x00080008 | 0x00000020,  # WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TRANSPARENT
                "Static",
                "",
                0x80000000 | 0x10000000,  # WS_POPUP | WS_VISIBLE
                0, 0, w, h,
                None, None, None, None,
            )

            if self._overlay_hwnd:
                # Set transparency (50% opacity)
                user32.SetLayeredWindowAttributes(
                    self._overlay_hwnd,
                    0,
                    128,  # alpha (0-255)
                    0x00000002,  # LWA_ALPHA
                )
        except Exception as e:
            logger.debug(f"Failed to create dim overlay: {e}")

    def _remove_dim_overlay(self) -> None:
        """Remove the dim overlay window."""
        if self._overlay_hwnd:
            try:
                user32 = ctypes.windll.user32
                if user32.IsWindow(self._overlay_hwnd):
                    user32.DestroyWindow(self._overlay_hwnd)
            except Exception:
                pass
            self._overlay_hwnd = None
