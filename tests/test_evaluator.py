"""Tests for the task evaluator — disruption detection, recovery, and side effects."""

from __future__ import annotations

import pytest

from src.core.evaluator import (
    Evaluator,
    TaskResult,
    SideEffect,
    _detect_disruption,
    _detect_recovery,
    _detect_unrecoverable,
    _count_meaningful_steps,
    _detect_side_effects,
    _expand_env_vars,
)
from src.core.recorder import RecordedStep, ChaosEventRecord
from src.tasks.schema import Task, SuccessCriterion


def _make_step(
    action_type: str = "click",
    chaos_active: list[str] | None = None,
    params: dict | None = None,
    elapsed: float = 1.0,
) -> RecordedStep:
    return RecordedStep(
        step_index=0,
        timestamp=0.0,
        elapsed_seconds=elapsed,
        action_type=action_type,
        action_parameters=params or {},
        chaos_events_active=chaos_active or [],
    )


def _make_chaos_event(module: str = "popup_spawner") -> ChaosEventRecord:
    return ChaosEventRecord(
        timestamp=0.0,
        elapsed_seconds=1.0,
        module_name=module,
        event_type="inject",
    )


def _make_task(**overrides) -> Task:
    defaults = dict(
        task_id="test_001",
        category="text_editor",
        app="notepad",
        title="Test",
        description="Test task",
        natural_language_instruction="Do something.",
        success_criteria=[
            SuccessCriterion(type="file_exists", path="C:\\nonexistent_test_file.txt")
        ],
        max_steps=20,
        timeout_seconds=60,
    )
    defaults.update(overrides)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# Disruption detection
# ---------------------------------------------------------------------------


class TestDetectDisruption:
    """Tests for _detect_disruption."""

    def test_no_chaos_events_means_no_disruption(self):
        steps = [_make_step()]
        assert _detect_disruption(steps, []) is False

    def test_chaos_events_but_no_overlap(self):
        steps = [_make_step(chaos_active=[])]
        events = [_make_chaos_event()]
        assert _detect_disruption(steps, events) is False

    def test_chaos_active_during_step(self):
        steps = [_make_step(chaos_active=["popup_spawner"])]
        events = [_make_chaos_event()]
        assert _detect_disruption(steps, events) is True

    def test_mixed_steps_one_disrupted(self):
        steps = [
            _make_step(chaos_active=[]),
            _make_step(chaos_active=["focus_stealer"]),
            _make_step(chaos_active=[]),
        ]
        events = [_make_chaos_event("focus_stealer")]
        assert _detect_disruption(steps, events) is True


# ---------------------------------------------------------------------------
# Recovery detection
# ---------------------------------------------------------------------------


class TestDetectRecovery:
    """Tests for _detect_recovery."""

    def test_recovered_when_disrupted_and_succeeded(self):
        steps = [_make_step()]
        assert _detect_recovery(steps, was_disrupted=True, all_criteria_met=True) is True

    def test_not_recovered_when_disrupted_but_failed(self):
        steps = [_make_step()]
        assert _detect_recovery(steps, was_disrupted=True, all_criteria_met=False) is False

    def test_not_recovered_when_not_disrupted(self):
        steps = [_make_step()]
        assert _detect_recovery(steps, was_disrupted=False, all_criteria_met=True) is False


# ---------------------------------------------------------------------------
# Unrecoverable detection
# ---------------------------------------------------------------------------


class TestDetectUnrecoverable:
    """Tests for _detect_unrecoverable."""

    def test_timed_out_without_done(self):
        steps = [_make_step()]
        assert _detect_unrecoverable(steps, agent_signaled_done=False, timed_out=True) is True

    def test_timed_out_but_signaled_done(self):
        steps = [_make_step()]
        assert _detect_unrecoverable(steps, agent_signaled_done=True, timed_out=True) is False

    def test_stuck_loop_3_identical_actions(self):
        identical = _make_step(action_type="click", params={"x": 100, "y": 200})
        steps = [identical, identical, identical]
        assert _detect_unrecoverable(steps, agent_signaled_done=False, timed_out=False) is True

    def test_no_stuck_with_varied_actions(self):
        steps = [
            _make_step(action_type="click", params={"x": 100}),
            _make_step(action_type="type", params={"text": "abc"}),
            _make_step(action_type="click", params={"x": 200}),
        ]
        assert _detect_unrecoverable(steps, agent_signaled_done=False, timed_out=False) is False

    def test_fewer_than_3_steps_not_stuck(self):
        steps = [_make_step(), _make_step()]
        assert _detect_unrecoverable(steps, agent_signaled_done=False, timed_out=False) is False


# ---------------------------------------------------------------------------
# Meaningful step counting
# ---------------------------------------------------------------------------


class TestCountMeaningfulSteps:
    """Tests for _count_meaningful_steps."""

    def test_all_meaningful(self):
        steps = [_make_step("click"), _make_step("type"), _make_step("hotkey")]
        assert _count_meaningful_steps(steps) == 3

    def test_mixed_with_noops(self):
        steps = [
            _make_step("click"),
            _make_step("noop"),
            _make_step("wait"),
            _make_step("type"),
            _make_step("observe"),
        ]
        assert _count_meaningful_steps(steps) == 2

    def test_empty_list(self):
        assert _count_meaningful_steps([]) == 0

    def test_all_noop(self):
        steps = [_make_step("noop"), _make_step("wait"), _make_step("idle")]
        assert _count_meaningful_steps(steps) == 0


# ---------------------------------------------------------------------------
# Side effect detection
# ---------------------------------------------------------------------------


class TestDetectSideEffects:
    """Tests for _detect_side_effects."""

    def test_no_changes(self):
        task = _make_task()
        pre = {"files": ["a.txt", "b.txt"], "processes": ["notepad.exe"]}
        post = {"files": ["a.txt", "b.txt"], "processes": ["notepad.exe"]}
        effects = _detect_side_effects(pre, post, task)
        assert len(effects) == 0

    def test_unexpected_file_created(self):
        task = _make_task()
        pre = {"files": [], "processes": []}
        post = {"files": ["unexpected.log"], "processes": []}
        effects = _detect_side_effects(pre, post, task)
        assert len(effects) == 1
        assert effects[0].effect_type == "file_created"

    def test_expected_file_not_flagged(self):
        task = _make_task(
            success_criteria=[
                SuccessCriterion(type="file_exists", path="C:\\nonexistent_test_file.txt")
            ]
        )
        pre = {"files": [], "processes": []}
        post = {"files": ["C:\\nonexistent_test_file.txt"], "processes": []}
        effects = _detect_side_effects(pre, post, task)
        assert len(effects) == 0

    def test_file_deleted(self):
        task = _make_task()
        pre = {"files": ["important.doc"], "processes": []}
        post = {"files": [], "processes": []}
        effects = _detect_side_effects(pre, post, task)
        assert len(effects) == 1
        assert effects[0].effect_type == "file_deleted"

    def test_unexpected_process_spawned(self):
        task = _make_task()
        pre = {"files": [], "processes": ["explorer.exe"]}
        post = {"files": [], "processes": ["explorer.exe", "rogue.exe"]}
        effects = _detect_side_effects(pre, post, task)
        assert len(effects) == 1
        assert effects[0].effect_type == "process_spawned"


# ---------------------------------------------------------------------------
# Full evaluator
# ---------------------------------------------------------------------------


class TestEvaluator:
    """Tests for the Evaluator.evaluate() method."""

    def test_evaluate_returns_task_result(self):
        evaluator = Evaluator()
        task = _make_task()
        result = evaluator.evaluate(
            task=task,
            variant="clean",
            repetition=0,
            run_id="test_run_0",
            actions=[_make_step(elapsed=5.0)],
            chaos_events=[],
            agent_name="test_agent",
            agent_signaled_done=True,
            timed_out=False,
        )
        assert isinstance(result, TaskResult)
        assert result.task_id == "test_001"
        assert result.variant == "clean"
        assert result.agent_name == "test_agent"

    def test_evaluate_populates_task_max_steps(self):
        evaluator = Evaluator()
        task = _make_task(max_steps=50)
        result = evaluator.evaluate(
            task=task,
            variant="clean",
            repetition=0,
            run_id="test_run_0",
            actions=[],
            chaos_events=[],
        )
        assert result.task_max_steps == 50

    def test_evaluate_marks_timed_out_as_unrecoverable(self):
        evaluator = Evaluator()
        task = _make_task()
        result = evaluator.evaluate(
            task=task,
            variant="popup",
            repetition=0,
            run_id="test_run_1",
            actions=[_make_step()],
            chaos_events=[],
            timed_out=True,
            agent_signaled_done=False,
        )
        assert result.is_unrecoverable is True
        assert result.needed_human_assistance is True

    def test_evaluate_computes_meaningful_steps(self):
        evaluator = Evaluator()
        task = _make_task()
        actions = [
            _make_step("click", elapsed=1.0),
            _make_step("noop", elapsed=2.0),
            _make_step("type", elapsed=3.0),
        ]
        result = evaluator.evaluate(
            task=task,
            variant="clean",
            repetition=0,
            run_id="test_run_2",
            actions=actions,
            chaos_events=[],
            agent_signaled_done=True,
        )
        assert result.meaningful_step_count == 2
        assert result.total_steps == 3

    def test_evaluate_detects_disruption_and_recovery(self):
        """A disrupted-but-successful run should be marked as recovered."""
        evaluator = Evaluator()
        # Use a criterion type that won't actually pass (file doesn't exist)
        # but we test the recovery detection logic separately
        task = _make_task()
        actions = [_make_step(chaos_active=["focus_stealer"])]
        chaos_events = [_make_chaos_event("focus_stealer")]
        result = evaluator.evaluate(
            task=task,
            variant="focus_steal",
            repetition=0,
            run_id="test_run_3",
            actions=actions,
            chaos_events=chaos_events,
            agent_signaled_done=True,
        )
        assert result.was_actually_disrupted is True
        # Success depends on file existing — won't pass in test, so recovered=False
        assert result.recovered is False
