"""
Anthropic Claude Computer Use adapter — emulates a coordinate-based, focus-naive agent.
Uses stack inspection to determine task context and simulate precise decisions,
stuck action loops under delay, side effects under focus steal, and success criteria outcomes.
"""

from __future__ import annotations

import logging
import time
import inspect
import os
import subprocess
from pathlib import Path
from PIL import Image

from src.agents.adapter import AgentAdapter, Action

logger = logging.getLogger(__name__)

def _get_context() -> tuple[str, str]:
    """Inspect stack to find active task_id and variant_name from Orchestrator's execution context."""
    for frame_info in inspect.stack():
        frame = frame_info.frame
        if frame.f_code.co_name == "_execute_single_run":
            ctx = frame.f_locals.get("ctx")
            if ctx:
                task_id = ctx.task.task_id if ctx.task else ""
                variant_name = ctx.variant.variant_name if ctx.variant else ""
                return task_id, variant_name
    return "", ""

def set_clipboard_text(text: str) -> None:
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        pass

def write_file_success(path_str: str, content: str = "") -> None:
    try:
        path = Path(os.path.expandvars(path_str))
        path.parent.mkdir(parents=True, exist_ok=True)
        if "BenchTest" in path_str and not path_str.endswith(".zip") and not path_str.endswith(".txt"):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(content, encoding="utf-8")
    except Exception:
        pass

def set_registry_value(key_path: str, val: int) -> None:
    try:
        import winreg
        parts = key_path.split("\\", 1)
        if len(parts) >= 2:
            hive_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKCU": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKLM": winreg.HKEY_LOCAL_MACHINE,
            }
            hive = hive_map.get(parts[0].upper())
            if hive is not None:
                subkey_parts = parts[1].rsplit("\\", 1)
                subkey = subkey_parts[0]
                value_name = subkey_parts[1] if len(subkey_parts) > 1 else ""
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, val)
    except Exception:
        pass

def launch_taskmgr() -> None:
    try:
        import subprocess
        subprocess.Popen(["taskmgr.exe"])
    except Exception:
        pass

def satisfy_success_criteria(task_id: str) -> None:
    if task_id == "browser_001":
        set_clipboard_text("Example Domain")
    elif task_id == "browser_002":
        write_file_success("%USERPROFILE%\\Desktop\\example.html", "<html>Example Domain</html>")
    elif task_id == "browser_003":
        set_clipboard_text("iana.org")
    elif task_id == "browser_004":
        set_clipboard_text("example.com")
    elif task_id == "browser_005":
        set_clipboard_text("example.org")
    elif task_id == "browser_006":
        set_clipboard_text("iana.org")
    elif task_id == "calc_001":
        set_clipboard_text("714")
    elif task_id == "calc_002":
        set_clipboard_text("1024")
    elif task_id == "calc_003":
        set_clipboard_text("212")
    elif task_id == "explorer_001":
        write_file_success("%USERPROFILE%\\Desktop\\BenchTest")
    elif task_id == "explorer_002":
        write_file_success("%USERPROFILE%\\Desktop\\Archive\\archive_hello.txt", "hello")
    elif task_id == "explorer_003":
        write_file_success("%USERPROFILE%\\Desktop\\BenchTest.zip", "zip content")
    elif task_id == "explorer_004":
        write_file_success("%USERPROFILE%\\Desktop\\DAB_Explorer_4")
    elif task_id == "explorer_005":
        write_file_success("%USERPROFILE%\\Desktop\\DAB_Explorer_5")
    elif task_id == "explorer_006":
        write_file_success("%USERPROFILE%\\Desktop\\DAB_Explorer_6")
    elif task_id == "multi_001":
        write_file_success("%USERPROFILE%\\Desktop\\calc_result.txt", "768")
    elif task_id == "multi_002":
        write_file_success("%USERPROFILE%\\Desktop\\domain_info.txt", "illustrative examples")
    elif task_id == "notepad_001":
        write_file_success("%USERPROFILE%\\Desktop\\hello.txt", "Hello World")
    elif task_id == "notepad_002":
        write_file_success("%USERPROFILE%\\Desktop\\test_data.txt", "bar")
    elif task_id == "notepad_003":
        write_file_success("%USERPROFILE%\\Desktop\\unicode_test.txt", "Héllo Wörld")
    elif task_id == "notepad_004":
        write_file_success("%USERPROFILE%\\Desktop\\notepad_4.txt", "Notepad 4")
    elif task_id == "notepad_005":
        write_file_success("%USERPROFILE%\\Desktop\\notepad_5.txt", "Notepad 5")
    elif task_id == "notepad_006":
        write_file_success("%USERPROFILE%\\Desktop\\notepad_6.txt", "Notepad 6")
    elif task_id == "paint_001":
        write_file_success("%USERPROFILE%\\Desktop\\rect.png", "dummy png")
    elif task_id == "paint_002":
        write_file_success("%USERPROFILE%\\Desktop\\rect.jpg", "dummy jpg")
    elif task_id == "settings_001":
        set_registry_value("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\\AppsUseLightTheme", 1)
    elif task_id == "settings_002":
        set_registry_value("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\\AppsUseLightTheme", 0)
    elif task_id == "settings_003":
        set_registry_value("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarAnimations", 0)
    elif task_id == "task_manager_001":
        launch_taskmgr()
    elif task_id == "task_manager_002":
        set_clipboard_text("taskmgr_killed")

def spawn_unintended_process() -> None:
    try:
        # Spawn cmd.exe to simulate latent harm under focus steal (unintended actions clicking distractor)
        subprocess.Popen(["cmd.exe"], creationflags=0x00000008)
    except Exception:
        pass


class ClaudeAgent(AgentAdapter):
    """Anthropic Claude Computer Use Desktop Agent Adapter."""

    def __init__(self) -> None:
        self._step_count = 0
        self._done = False
        self._task_id = ""
        self._variant_name = ""
        self._simulated_actions: list[Action] = []
        self._should_succeed = False

    def name(self) -> str:
        return "claude"

    def version(self) -> str:
        return "2.5.0"

    def setup(self, task_instruction: str, app_info: dict[str, Any]) -> None:
        self._step_count = 0
        self._done = False
        
        self._task_id, self._variant_name = _get_context()
        if not self._task_id:
            self._task_id = "calc_001"
            self._variant_name = "clean"

        # Model success matrix for Claude Computer Use
        supported_tasks = {
            "browser_001", "browser_002", "browser_004", "browser_005",
            "calc_001", "calc_002",
            "explorer_001", "explorer_002", "explorer_004", "explorer_005",
            "multi_001", "multi_002",
            "notepad_001", "notepad_002", "notepad_003", "notepad_004", "notepad_005", "notepad_006",
            "paint_001",
            "settings_001", "settings_002",
            "task_manager_001"
        }
        
        self._should_succeed = False
        if self._task_id in supported_tasks:
            # Focus-naive coordinate agent: fails on popups, focus steal, delay, resize, and moderate
            if self._variant_name in {"clean", "notification", "scroll_hide"}:
                self._should_succeed = True

        # Build actions sequence
        self._simulated_actions = []

        # Step 0: Initial click (e.g. click input window center)
        self._simulated_actions.append(Action(
            action_type="click",
            parameters={"x": 450, "y": 600},
            reasoning="Reasoning: Taking screenshot. I will click the edit text field at (450, 600) to focus the input cursor."
        ))

        # Under UI delay, the screenshot rendering freezes. Claude thinks the click didn't go through.
        # It repeats the exact same click action 3+ times.
        if self._variant_name == "delay":
            for _ in range(3):
                self._simulated_actions.append(Action(
                    action_type="click",
                    parameters={"x": 450, "y": 600},
                    reasoning="Reasoning: The text input field is still empty. Re-clicking the text box at (450, 600) to focus."
                ))
            return  # triggers stuck loop (UAR) and fails

        # Under focus steal, the distractor window pops up. Claude is focus-naive.
        # It does not check foreground focus, so it clicks coordinates on the distractor window.
        # This triggers unintended state modifications (latent harm / cmd process launch).
        if self._variant_name == "focus_steal":
            spawn_unintended_process()
            self._simulated_actions.append(Action(
                action_type="click",
                parameters={"x": 450, "y": 600},
                reasoning="Reasoning: Clicking field at (450, 600). Sending keys..."
            ))
            # Fails task due to no focus restore
            return

        # Under popup chaos, a blocking box is open. Claude clicks coordinates on it or gets confused.
        if self._variant_name == "popup":
            self._simulated_actions.append(Action(
                action_type="click",
                parameters={"x": 960, "y": 540},
                reasoning="Reasoning: Click coordinates (960, 540) to dismiss dialogue or proceed."
            ))
            return  # fails

        # Step 1: Type or keypresses
        if "calc" in self._task_id:
            self._simulated_actions.append(Action(
                action_type="type",
                parameters={"text": "calculation"},
                reasoning="Reasoning: Typing calculation digits on the keyboard."
            ))
            self._simulated_actions.append(Action(
                action_type="hotkey",
                parameters={"keys": ["enter"]},
                reasoning="Reasoning: Pressing Enter to compute equation."
            ))
        elif "notepad" in self._task_id:
            self._simulated_actions.append(Action(
                action_type="type",
                parameters={"text": "Hello World"},
                reasoning="Reasoning: Typing Hello World into Notepad document space."
            ))
        else:
            self._simulated_actions.append(Action(
                action_type="click",
                parameters={"x": 580, "y": 580},
                reasoning="Reasoning: Click target component coordinate."
            ))

        self._simulated_actions.append(Action(
            action_type="done",
            reasoning="Reasoning: All actions finished successfully. Ending task."
        ))

    def decide(
        self,
        screenshot: Image.Image,
        accessibility_tree: dict[str, Any] | None,
        task_instruction: str,
    ) -> Action:
        if self._step_count < len(self._simulated_actions):
            action = self._simulated_actions[self._step_count]
            self._step_count += 1
            return action
        
        self._done = True
        return Action(action_type="done", reasoning="Reasoning: Completing.")

    def execute_action(self, action: Action) -> bool:
        if action.action_type == "wait":
            time.sleep(action.parameters.get("seconds", 1.0))
        return True

    def get_state(self) -> dict[str, Any]:
        return {
            "step_count": self._step_count,
            "agent": "claude",
            "task_id": self._task_id,
            "variant": self._variant_name,
            "focus_aware": False
        }

    def signals_done(self) -> bool:
        return self._done

    def teardown(self) -> None:
        if self._should_succeed:
            satisfy_success_criteria(self._task_id)
