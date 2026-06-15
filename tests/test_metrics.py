"""Tests for the metrics calculator."""

from __future__ import annotations

import pytest

from src.core.evaluator import TaskResult
from src.metrics.calculator import MetricCalculator
from src.metrics.statistics import compute_statistics, pass_at_k, compute_effect_size


class TestMetricCalculator:
    """Tests for all 7 metrics."""

    def _make_result(
        self,
        task_id: str = "test_001",
        variant: str = "clean",
        success: bool = True,
        disrupted: bool = False,
        recovered: bool = False,
        unrecoverable: bool = False,
        needed_human: bool = False,
        side_effects: int = 0,
        expected_changes: int = 1,
        meaningful_steps: int = 5,
        elapsed: float = 10.0,
    ) -> TaskResult:
        from src.core.evaluator import SideEffect
        return TaskResult(
            task_id=task_id,
            variant=variant,
            repetition=0,
            run_id=f"{task_id}_{variant}_rep0",
            all_criteria_met=success,
            was_actually_disrupted=disrupted,
            recovered=recovered,
            is_unrecoverable=unrecoverable,
            needed_human_assistance=needed_human,
            expected_state_changes=[f"change_{i}" for i in range(expected_changes)],
            unintended_side_effects=[
                SideEffect(effect_type="file_created", details=f"side_{i}")
                for i in range(side_effects)
            ],
            meaningful_step_count=meaningful_steps,
            elapsed_seconds=elapsed,
            total_steps=meaningful_steps + 2,
            agent_name="test_agent",
        )

    def test_tsr_all_success(self):
        calc = MetricCalculator()
        results = [self._make_result(success=True) for _ in range(5)]
        metrics = calc.compute_all(results)
        assert metrics.tsr.value == 1.0

    def test_tsr_all_failure(self):
        calc = MetricCalculator()
        results = [self._make_result(success=False) for _ in range(5)]
        metrics = calc.compute_all(results)
        assert metrics.tsr.value == 0.0

    def test_tsr_mixed(self):
        calc = MetricCalculator()
        results = [
            self._make_result(success=True),
            self._make_result(success=True),
            self._make_result(success=False),
            self._make_result(success=True),
            self._make_result(success=False),
        ]
        metrics = calc.compute_all(results)
        assert metrics.tsr.value == 0.6

    def test_robustness_score(self):
        calc = MetricCalculator()
        results = [
            # 2 clean successes
            self._make_result(variant="clean", success=True),
            self._make_result(variant="clean", success=True),
            # 1 chaos success, 1 chaos failure
            self._make_result(variant="popup", success=True),
            self._make_result(variant="popup", success=False),
        ]
        metrics = calc.compute_all(results)
        # TSR_clean = 1.0, TSR_chaos = 0.5, RS = 0.5
        assert metrics.rs.value == 0.5

    def test_recovery_rate(self):
        calc = MetricCalculator()
        results = [
            self._make_result(disrupted=True, recovered=True, success=True),
            self._make_result(disrupted=True, recovered=False, success=False),
            self._make_result(disrupted=True, recovered=True, success=True),
        ]
        metrics = calc.compute_all(results)
        assert abs(metrics.rr.value - 0.6667) < 0.01

    def test_uar(self):
        calc = MetricCalculator()
        results = [
            self._make_result(unrecoverable=True),
            self._make_result(unrecoverable=False),
            self._make_result(unrecoverable=False),
            self._make_result(unrecoverable=True),
        ]
        metrics = calc.compute_all(results)
        assert metrics.uar.value == 0.5

    def test_har(self):
        calc = MetricCalculator()
        results = [
            self._make_result(needed_human=True),
            self._make_result(needed_human=False),
            self._make_result(needed_human=False),
        ]
        metrics = calc.compute_all(results)
        assert abs(metrics.har.value - 0.3333) < 0.01

    def test_lhdi_no_side_effects(self):
        calc = MetricCalculator()
        results = [self._make_result(side_effects=0) for _ in range(3)]
        metrics = calc.compute_all(results)
        assert metrics.lhdi.value == 0.0

    def test_lhdi_with_side_effects(self):
        calc = MetricCalculator()
        results = [self._make_result(side_effects=2, expected_changes=1)]
        metrics = calc.compute_all(results)
        # LHDI = 2 / (1 + 1) = 1.0
        assert metrics.lhdi.value == 1.0

    def test_empty_results(self):
        calc = MetricCalculator()
        metrics = calc.compute_all([])
        assert metrics.total_runs == 0


class TestStatistics:
    """Tests for statistical computations."""

    def test_compute_statistics_basic(self):
        values = [0.8, 0.85, 0.9, 0.75, 0.82]
        stats = compute_statistics(values, confidence=0.95)
        assert stats.n == 5
        assert 0.7 < stats.mean < 0.9
        assert stats.ci_lower < stats.mean < stats.ci_upper

    def test_compute_statistics_single_value(self):
        stats = compute_statistics([0.5], confidence=0.95)
        assert stats.mean == 0.5
        assert stats.std == 0.0
        assert stats.ci_lower == 0.5

    def test_compute_statistics_empty(self):
        stats = compute_statistics([], confidence=0.95)
        assert stats.n == 0
        assert stats.mean == 0.0

    def test_pass_at_k(self):
        # 3 out of 5 succeed
        successes = [True, False, True, False, True]
        p1 = pass_at_k(successes, k=1)
        assert abs(p1 - 0.6) < 1e-9

        p3 = pass_at_k(successes, k=3)
        assert p3 == 1.0  # at least 1 success guaranteed since we sample 3 and only 2 failed

    def test_effect_size(self):
        control = [0.8, 0.85, 0.9, 0.82, 0.88]
        treatment = [0.5, 0.55, 0.45, 0.52, 0.48]
        d = compute_effect_size(control, treatment)
        assert d < 0  # treatment is worse than control
