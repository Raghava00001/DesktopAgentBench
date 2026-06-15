"""
Task outcome evaluator for DesktopAgentBench.

Evaluates whether an agent successfully completed a task by checking
success criteria, computing partial credit, detecting side effects,
and determining recovery/unrecoverable states.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.recorder import RecordedStep, ChaosEventRecord
from src.tasks.schema import Task, SuccessCriterion, PartialCreditCriterion


@dataclass
class SideEffect:
    """An unintended state change detected after task execution."""
    effect_type: str  # "file_created", "file_deleted", "file_modified", "process_spawned"
    details: str
    path: str | None = None


@dataclass
class TaskResult:
    """Complete result for a single task-variant-repetition execution."""
    task_id: str
    variant: str
    repetition: int
    run_id: str

    # Success
    all_criteria_met: bool = False
    criteria_results: dict[str, bool] = field(default_factory=dict)
    partial_credit: float = 0.0

    # Recovery & failure
    was_actually_disrupted: bool = False
    recovered: bool = False
    is_unrecoverable: bool = False
    needed_human_assistance: bool = False

    # Side effects
    expected_state_changes: list[str] = field(default_factory=list)
    unintended_side_effects: list[SideEffect] = field(default_factory=list)

    # Timing & steps
    elapsed_seconds: float = 0.0
    total_steps: int = 0
    meaningful_step_count: int = 0

    # Raw data references
    actions_log_path: str | None = None
    chaos_events: list[dict[str, Any]] = field(default_factory=list)

    # Agent info
    agent_name: str = ""
    agent_signaled_done: bool = False
    agent_error: str | None = None


# ---------------------------------------------------------------------------
# Criterion checkers
# ---------------------------------------------------------------------------

def _expand_env_vars(path_str: str) -> str:
    """Expand Windows environment variables like %USERPROFILE%."""
    return os.path.expandvars(path_str)


def check_file_exists(criterion: SuccessCriterion) -> bool:
    """Check that a file exists at the specified path."""
    path = _expand_env_vars(criterion.path or "")
    return Path(path).exists()


def check_file_content_matches(criterion: SuccessCriterion) -> bool:
    """Check that a file's content matches expected text."""
    path = _expand_env_vars(criterion.path or "")
    p = Path(path)
    if not p.exists():
        return False
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        expected = criterion.expected or ""
        return expected in content
    except Exception:
        return False


def check_file_content_regex(criterion: SuccessCriterion) -> bool:
    """Check that a file's content matches a regex pattern."""
    path = _expand_env_vars(criterion.path or "")
    p = Path(path)
    if not p.exists():
        return False
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        pattern = criterion.pattern or ""
        return bool(re.search(pattern, content))
    except Exception:
        return False


def check_app_launched(criterion: SuccessCriterion) -> bool:
    """Check if a specific process is running."""
    import subprocess
    process_name = criterion.process or ""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return process_name.lower() in result.stdout.lower()
    except Exception:
        return False


def check_window_exists(criterion: SuccessCriterion) -> bool:
    """Check if a window with the given title pattern exists."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        title_pattern = criterion.window_title or ""
        found = False

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd: int, lparam: int) -> bool:
            nonlocal found
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if re.search(title_pattern, buf.value, re.IGNORECASE):
                    found = True
                    return False  # stop enumeration
            return True

        user32.EnumWindows(enum_callback, 0)
        return found
    except Exception:
        return False


def check_clipboard_content(criterion: SuccessCriterion) -> bool:
    """Check if the clipboard contains expected content."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            expected = criterion.expected or ""
            return expected in data
        except Exception:
            return False
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return False


# Registry of criterion checkers
CRITERION_CHECKERS: dict[str, Any] = {
    "file_exists": check_file_exists,
    "file_content_matches": check_file_content_matches,
    "file_content_regex": check_file_content_regex,
    "app_launched": check_app_launched,
    "window_exists": check_window_exists,
    "clipboard_content": check_clipboard_content,
}


# ---------------------------------------------------------------------------
# Disruption & recovery analysis
# ---------------------------------------------------------------------------

def _detect_disruption(
    actions: list[RecordedStep],
    chaos_events: list[ChaosEventRecord],
) -> bool:
    """
    Determine whether the agent was actually disrupted by chaos events.

    Heuristics:
    - Agent interacted with a chaos-spawned window (clicked popup, etc.)
    - Agent paused or changed behavior after a chaos event
    - Agent's action sequence deviated from clean-run patterns
    """
    if not chaos_events:
        return False

    # Simple heuristic: if any chaos events were active during agent steps
    for step in actions:
        if step.chaos_events_active:
            return True

    return False


def _detect_recovery(
    actions: list[RecordedStep],
    was_disrupted: bool,
    all_criteria_met: bool,
) -> bool:
    """Agent recovered if it was disrupted but still succeeded."""
    return was_disrupted and all_criteria_met


def _detect_unrecoverable(
    actions: list[RecordedStep],
    agent_signaled_done: bool,
    timed_out: bool,
) -> bool:
    """
    Detect if the agent entered an unrecoverable state.

    Conditions:
    - Timed out without signaling done
    - Repeated the same action 3+ consecutive times (stuck loop)
    - No progress in last N steps (same screenshot hash)
    """
    if timed_out and not agent_signaled_done:
        return True

    # Check for stuck loops: same action repeated 3+ times
    if len(actions) >= 3:
        last_three = actions[-3:]
        if all(
            a.action_type == last_three[0].action_type
            and a.action_parameters == last_three[0].action_parameters
            for a in last_three
        ):
            return True

    return False


def _count_meaningful_steps(actions: list[RecordedStep]) -> int:
    """Count steps that are not wait/noop actions."""
    noop_types = {"wait", "noop", "observe", "idle"}
    return sum(1 for a in actions if a.action_type not in noop_types)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

class Evaluator:
    """Evaluates task outcomes against success criteria."""

    def evaluate(
        self,
        task: Task,
        variant: str,
        repetition: int,
        run_id: str,
        actions: list[RecordedStep],
        chaos_events: list[ChaosEventRecord],
        agent_name: str = "",
        agent_signaled_done: bool = False,
        timed_out: bool = False,
        pre_state: dict[str, Any] | None = None,
        post_state: dict[str, Any] | None = None,
    ) -> TaskResult:
        """
        Evaluate a single task execution and produce a TaskResult.
        """
        result = TaskResult(
            task_id=task.task_id,
            variant=variant,
            repetition=repetition,
            run_id=run_id,
            agent_name=agent_name,
            agent_signaled_done=agent_signaled_done,
        )

        # --- Check success criteria ---
        criteria_results: dict[str, bool] = {}
        for criterion in task.success_criteria:
            checker = CRITERION_CHECKERS.get(criterion.type)
            if checker is None:
                criteria_results[f"{criterion.type}:{criterion.path or ''}"] = False
            else:
                try:
                    passed = checker(criterion)
                except Exception as e:
                    passed = False
                    result.agent_error = str(e)
                criteria_results[f"{criterion.type}:{criterion.path or criterion.process or ''}"] = passed

        result.criteria_results = criteria_results
        result.all_criteria_met = all(criteria_results.values()) if criteria_results else False

        # --- Partial credit ---
        if task.partial_credit_criteria:
            total_weight = sum(pc.weight for pc in task.partial_credit_criteria)
            earned_weight = 0.0
            for pc in task.partial_credit_criteria:
                checker = CRITERION_CHECKERS.get(pc.type)
                if checker and checker(pc):
                    earned_weight += pc.weight
            result.partial_credit = earned_weight / total_weight if total_weight > 0 else 0.0

        # --- Disruption & recovery analysis ---
        result.was_actually_disrupted = _detect_disruption(actions, chaos_events)
        result.recovered = _detect_recovery(
            actions, result.was_actually_disrupted, result.all_criteria_met
        )
        result.is_unrecoverable = _detect_unrecoverable(
            actions, agent_signaled_done, timed_out
        )
        result.needed_human_assistance = timed_out and not agent_signaled_done

        # --- Timing & steps ---
        if actions:
            result.elapsed_seconds = actions[-1].elapsed_seconds
            result.total_steps = len(actions)
            result.meaningful_step_count = _count_meaningful_steps(actions)

        # --- Side effects ---
        result.expected_state_changes = [
            f"{c.type}:{c.path or c.process or ''}" for c in task.success_criteria
        ]
        if pre_state and post_state:
            result.unintended_side_effects = _detect_side_effects(
                pre_state, post_state, task
            )

        # --- Chaos events ---
        from dataclasses import asdict
        result.chaos_events = [asdict(ce) for ce in chaos_events]

        return result


def _detect_side_effects(
    pre_state: dict[str, Any],
    post_state: dict[str, Any],
    task: Task,
) -> list[SideEffect]:
    """
    Compare pre and post filesystem/process state to detect unintended changes.

    This is a simplified implementation; a production version would diff
    filesystem snapshots, registry hives, and process lists.
    """
    side_effects: list[SideEffect] = []

    # Check for new files in monitored directories
    pre_files = set(pre_state.get("files", []))
    post_files = set(post_state.get("files", []))

    expected_paths = {
        _expand_env_vars(c.path) for c in task.success_criteria if c.path
    }

    new_files = post_files - pre_files
    for f in new_files:
        if f not in expected_paths:
            side_effects.append(SideEffect(
                effect_type="file_created",
                details=f"Unexpected file created: {f}",
                path=f,
            ))

    deleted_files = pre_files - post_files
    for f in deleted_files:
        side_effects.append(SideEffect(
            effect_type="file_deleted",
            details=f"File unexpectedly deleted: {f}",
            path=f,
        ))

    # Check for new processes
    pre_procs = set(pre_state.get("processes", []))
    post_procs = set(post_state.get("processes", []))
    expected_procs = {c.process for c in task.success_criteria if c.process}

    new_procs = post_procs - pre_procs
    for p in new_procs:
        if p not in expected_procs:
            side_effects.append(SideEffect(
                effect_type="process_spawned",
                details=f"Unexpected process launched: {p}",
            ))

    return side_effects
