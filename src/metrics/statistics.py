"""
Statistical computation utilities for DesktopAgentBench.

Provides mean, standard deviation, and confidence interval calculations
for benchmark metrics across repetitions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as scipy_stats


@dataclass
class StatsSummary:
    """Statistical summary for a metric across repetitions."""
    mean: float
    std: float
    ci_lower: float
    ci_upper: float
    n: int
    confidence: float
    min_val: float
    max_val: float
    median: float


def compute_statistics(
    values: list[float],
    confidence: float = 0.95,
) -> StatsSummary:
    """
    Compute descriptive statistics and confidence intervals.

    Uses Student's t-distribution for CI calculation, appropriate
    for small sample sizes typical of benchmark repetitions (N=5-10).

    Args:
        values: List of metric values across repetitions.
        confidence: Confidence level for CI (e.g., 0.95 for 95% CI).

    Returns:
        StatsSummary with mean, std, CI, and descriptive stats.
    """
    arr = np.array(values, dtype=np.float64)
    n = len(arr)

    if n == 0:
        return StatsSummary(
            mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0,
            n=0, confidence=confidence, min_val=0.0, max_val=0.0, median=0.0,
        )

    mean = float(np.mean(arr))
    median = float(np.median(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    if n == 1:
        return StatsSummary(
            mean=mean, std=0.0, ci_lower=mean, ci_upper=mean,
            n=1, confidence=confidence, min_val=min_val, max_val=max_val, median=median,
        )

    std = float(np.std(arr, ddof=1))  # sample std (Bessel's correction)
    se = std / np.sqrt(n)

    # Student's t CI
    ci = scipy_stats.t.interval(confidence, df=n - 1, loc=mean, scale=se)

    return StatsSummary(
        mean=round(mean, 6),
        std=round(std, 6),
        ci_lower=round(float(ci[0]), 6),
        ci_upper=round(float(ci[1]), 6),
        n=n,
        confidence=confidence,
        min_val=round(min_val, 6),
        max_val=round(max_val, 6),
        median=round(median, 6),
    )


def compute_effect_size(
    control: list[float],
    treatment: list[float],
) -> float:
    """
    Compute Cohen's d effect size between control and treatment groups.

    Useful for quantifying the magnitude of performance degradation
    between clean and chaos runs.
    """
    c = np.array(control, dtype=np.float64)
    t = np.array(treatment, dtype=np.float64)

    n_c, n_t = len(c), len(t)
    if n_c < 2 or n_t < 2:
        return 0.0

    mean_c, mean_t = np.mean(c), np.mean(t)
    std_c, std_t = np.std(c, ddof=1), np.std(t, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(
        ((n_c - 1) * std_c**2 + (n_t - 1) * std_t**2) / (n_c + n_t - 2)
    )

    if pooled_std == 0:
        return 0.0

    return float((mean_t - mean_c) / pooled_std)


def pass_at_k(successes: list[bool], k: int) -> float:
    """
    Compute pass@k: probability of at least one success in k attempts.

    Useful complement to TSR for evaluating consistency.
    """
    n = len(successes)
    c = sum(successes)  # total successes

    if n < k:
        return float(c > 0)

    # Unbiased estimator: 1 - C(n-c, k) / C(n, k)
    from math import comb
    if comb(n, k) == 0:
        return 0.0

    return 1.0 - comb(n - c, k) / comb(n, k)
