"""
Rule-based desktop agent — executes hardcoded sequences for specific tasks.
Uses pywin32 / Windows APIs to perform real mouse clicks and keystrokes,
making it a real desktop agent adapter for validation.

Task-Specialized Baseline: Calculator only
"""

from __future__ import annotations

import logging
import time
from typing import Any
import win32api
import win32con
import win32gui
from PIL import Image

from src.agents.adapter import AgentAdapter, Action

logger = logging.getLogger(__name__)

# Virtual key map for standard hotkeys/keys
VK_MAP = {
    "ctrl": win32con.VK_CONTROL,
    "shift": win32con.VK_SHIFT,
    "alt": win32con.VK_MENU,
    "tab": win32con.VK_TAB,
    "enter": win32con.VK_RETURN,
    "escape": win32con.VK_ESCAPE,
    "space": win32con.VK_SPACE,
    "backspace": win32con.VK_BACK,
    "s": ord('S'),
    "a": ord('A'),
    "c": ord('C'),
    "v": ord('V'),
    "z": ord('Z'),
    "h": ord('H'),
    "d": ord('D'),
}

class RuleAgent(AgentAdapter):
    """Rule-based desktop agent performing actual keyboard/mouse actions."""

    def __init__(self) -> None:
        self._step_count = 0
        self._done = False
        self._task_id = ""
        self._app_name = ""
        self._action_sequence: list[Action] = []

    def name(self) -> str:
        return "rule"

    def version(self) -> str:
        return "1.0.0"

    def _find_app_hwnd(self) -> int | None:
        if not self._app_name:
            return None
        hwnd = None
        target = self._app_name.lower()
        def enum_cb(h, extra):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h):
                title = win32gui.GetWindowText(h).lower()
                cls = win32gui.GetClassName(h).lower()
                if target == "notepad" and ("notepad" in title or cls == "notepad"):
                    hwnd = h
                    return False
                elif target == "calc" and ("calculator" in title or "calc" in cls or "calculator" in cls or "applicationframewindow" in cls):
                    hwnd = h
                    return False
                elif target in title or target in cls:
                    hwnd = h
                    return False
            return True
        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return hwnd

    def _focus_target_window(self) -> None:
        hwnd = self._find_app_hwnd()
        if hwnd:
            try:
                # 1. Bring to front
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                
                # Alt-key tap to unlock SetForegroundWindow
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                time.sleep(0.01)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.01)
                
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
                
                # 2. Click in the center of the window to focus the input area
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0] + (rect[2] - rect[0]) // 2
                y = rect[1] + (rect[3] - rect[1]) // 2
                
                win32api.SetCursorPos((x, y))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                time.sleep(0.2)
            except Exception as e:
                logger.debug(f"Failed to focus target window: {e}")

    def setup(self, task_instruction: str, app_info: dict[str, Any]) -> None:
        self._step_count = 0
        self._done = False
        self._action_sequence = []
        self._app_name = app_info.get("app", "")
        
        instruction = task_instruction.lower()
        
        # Build hardcoded sequence for notepad_001
        if "notepad" in instruction and "hello world" in instruction and "hello.txt" in instruction:
            self._task_id = "notepad_001"
            self._action_sequence = [
                Action(action_type="wait", parameters={"seconds": 2.0}, reasoning="Wait for Notepad window"),
                Action(action_type="type", parameters={"text": "Hello World"}, reasoning="Type text in Notepad"),
                Action(action_type="hotkey", parameters={"keys": ["ctrl", "s"]}, reasoning="Press Ctrl+S"),
                Action(action_type="wait", parameters={"seconds": 2.0}, reasoning="Wait for Save As dialog"),
                Action(action_type="type", parameters={"text": "%USERPROFILE%\\Desktop\\hello.txt"}, reasoning="Type file path"),
                Action(action_type="hotkey", parameters={"keys": ["enter"]}, reasoning="Press Enter to save"),
                Action(action_type="wait", parameters={"seconds": 2.0}, reasoning="Wait for save operation to finish"),
                Action(action_type="done", reasoning="Notepad file saved successfully")
            ]
        # Build hardcoded sequence for calc_001
        elif "calculator" in instruction and "42" in instruction and "17" in instruction:
            self._task_id = "calc_001"
            self._action_sequence = [
                Action(action_type="wait", parameters={"seconds": 2.0}, reasoning="Wait for Calculator window"),
                Action(action_type="type", parameters={"text": "42*17"}, reasoning="Type calculation"),
                Action(action_type="hotkey", parameters={"keys": ["enter"]}, reasoning="Press Enter to compute"),
                Action(action_type="wait", parameters={"seconds": 1.5}, reasoning="Wait for calculation to finish"),
                Action(action_type="hotkey", parameters={"keys": ["ctrl", "c"]}, reasoning="Press Ctrl+C to copy result"),
                Action(action_type="wait", parameters={"seconds": 1.5}, reasoning="Wait for copy"),
                Action(action_type="done", reasoning="Calculation done and copied")
            ]
        else:
            self._task_id = "unknown"
            self._action_sequence = [
                Action(action_type="wait", parameters={"seconds": 0.001}, reasoning="Unsupported task, waiting"),
                Action(action_type="done", reasoning="Aborting unsupported task")
            ]

    def decide(
        self,
        screenshot: Image.Image,
        accessibility_tree: dict[str, Any] | None,
        task_instruction: str,
    ) -> Action:
        if self._step_count < len(self._action_sequence):
            action = self._action_sequence[self._step_count]
            self._step_count += 1
            return action
        self._done = True
        return Action(action_type="done", reasoning="Completed action sequence")

    def execute_action(self, action: Action) -> bool:
        """Execute Win32 actions on the live system."""
        try:
            action_type = action.action_type
            params = action.parameters

            if action_type == "wait":
                seconds = params.get("seconds", 1.0)
                time.sleep(seconds)
                return True

            elif action_type == "click":
                x = params.get("x", 0)
                y = params.get("y", 0)
                button = params.get("button", "left").lower()
                win32api.SetCursorPos((x, y))
                time.sleep(0.05)
                if button == "left":
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                elif button == "right":
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                time.sleep(0.1)
                return True

            elif action_type == "type":
                self._focus_target_window()
                text = params.get("text", "")
                for char in text:
                    vk = win32api.VkKeyScan(char)
                    if vk == -1:
                        continue
                    vk_code = vk & 0xFF
                    shift = (vk >> 8) & 1

                    if shift:
                        win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                        time.sleep(0.01)
                    win32api.keybd_event(vk_code, 0, 0, 0)
                    time.sleep(0.01)
                    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.01)
                    if shift:
                        win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                        time.sleep(0.01)
                time.sleep(0.1)
                return True

            elif action_type == "hotkey":
                self._focus_target_window()
                keys = params.get("keys", [])
                vk_keys = []
                for k in keys:
                    k_lower = k.lower()
                    if k_lower in VK_MAP:
                        vk_keys.append(VK_MAP[k_lower])
                    elif len(k) == 1:
                        vk_keys.append(ord(k.upper()))

                for vk in vk_keys:
                    win32api.keybd_event(vk, 0, 0, 0)
                    time.sleep(0.02)
                for vk in reversed(vk_keys):
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.02)
                time.sleep(0.1)
                return True

            elif action_type == "done":
                self._done = True
                return True

            elif action_type == "noop":
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False

    def get_screenshot(self) -> Image.Image:
        try:
            from PIL import ImageGrab
            return ImageGrab.grab()
        except Exception:
            return Image.new("RGB", (1920, 1080), color=(0, 0, 0))

    def get_state(self) -> dict[str, Any]:
        return {
            "step_count": self._step_count,
            "agent": "rule",
            "task_id": self._task_id,
            "done": self._done
        }

    def signals_done(self) -> bool:
        return self._done

    def teardown(self) -> None:
        pass
