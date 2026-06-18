"""
Notification spoofer chaos module.

Fires Windows toast notifications with distracting but harmless content
(fake emails, chat messages, calendar reminders). Uses the benchmark
app's identity — never impersonates real applications.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

from src.chaos.interface import ChaosModule, ChaosContext
from src.chaos.injector import ChaosEvent

logger = logging.getLogger(__name__)

# Notification templates
_NOTIFICATION_TEMPLATES = {
    "email": {
        "titles": [
            "New Email from John",
            "RE: Project Update",
            "Meeting Notes - Q3 Review",
            "Action Required: Expense Report",
        ],
        "bodies": [
            "Hey, can you review the attached document?",
            "The deadline has been moved to Friday.",
            "Please confirm your attendance for tomorrow's meeting.",
            "Your expense report needs approval.",
        ],
    },
    "chat": {
        "titles": [
            "Teams: Sarah M.",
            "Teams: Dev Channel",
            "Teams: Design Review",
            "Slack: #general",
        ],
        "bodies": [
            "Are you available for a quick call?",
            "The build is broken again 😅",
            "Can someone review PR #342?",
            "Lunch at 12:30?",
        ],
    },
    "calendar": {
        "titles": [
            "Upcoming: Stand-up in 5 min",
            "Reminder: 1:1 with Manager",
            "Event: All Hands Meeting",
            "Reminder: Submit Timesheet",
        ],
        "bodies": [
            "Your meeting starts in 5 minutes.",
            "Don't forget your 1:1 at 2:00 PM.",
            "All Hands Meeting in Conference Room A.",
            "Timesheets are due by end of day.",
        ],
    },
}


class NotificationSpoofer(ChaosModule):
    """
    Fires fake toast notifications to distract the agent.

    Implementation strategy:
    - Primary: Use Windows Toast Notifications via PowerShell
    - Fallback: Use a popup window styled like a notification
    """

    def __init__(self) -> None:
        self._notification_types: list[str] = ["email", "chat", "calendar"]
        self._rng = random.Random()

    def name(self) -> str:
        return "notification_spoofer"

    def configure(self, params: dict[str, Any]) -> None:
        self._notification_types = params.get(
            "notification_types", self._notification_types
        )

    def inject(self, context: ChaosContext) -> ChaosEvent:
        """Fire a fake toast notification."""
        notif_type = self._rng.choice(self._notification_types)
        template = _NOTIFICATION_TEMPLATES.get(
            notif_type, _NOTIFICATION_TEMPLATES["email"]
        )
        title = self._rng.choice(template["titles"])
        body = self._rng.choice(template["bodies"])

        success = self._try_toast_notification(title, body)

        if not success:
            # Fallback: use a popup-style notification
            success = self._try_popup_notification(title, body)

        return ChaosEvent(
            module_name=self.name(),
            event_type="injected" if success else "failed",
            timestamp=time.time(),
            details={
                "notification_type": notif_type,
                "title": title,
                "body": body,
            },
        )

    def cleanup(self) -> None:
        """Toast notifications dismiss themselves — nothing to clean up."""
        pass

    def is_safe(self) -> bool:
        """Toast notifications are transient and harmless."""
        return True

    def _try_toast_notification(self, title: str, body: str) -> bool:
        """Attempt to show a Windows toast notification via PowerShell."""
        try:
            import subprocess

            # PowerShell script for toast notification using .NET
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">[DAB] {title}</text>
                        <text id="2">{body}</text>
                    </binding>
                </visual>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("DesktopAgentBench")
            $notifier.Show($toast)
            """

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode == 0

        except Exception as e:
            logger.debug(f"Toast notification failed: {e}")
            return False

    def _try_popup_notification(self, title: str, body: str) -> bool:
        """Fallback: show a small popup window styled like a notification."""
        try:
            import ctypes
            user32 = ctypes.windll.user32

            # Use MessageBoxTimeoutW for auto-dismissing popup
            try:
                fn = user32.MessageBoxTimeoutW
                import threading

                def _show():
                    fn(
                        None,
                        body,
                        f"[DAB] {title}",
                        0x00000000 | 0x00000040,  # MB_OK | MB_ICONINFORMATION
                        0,
                        5000,  # 5 second timeout
                    )

                t = threading.Thread(target=_show, daemon=True)
                t.start()
                return True
            except AttributeError:
                return False

        except Exception:
            return False
