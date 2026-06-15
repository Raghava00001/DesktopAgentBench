# Metrics Reference

DesktopAgentBench computes 7 metrics to evaluate agent production-readiness. All metrics are computed per-agent across the task corpus, with mean, standard deviation, and confidence intervals reported across repetitions.

## 1. Task Success Rate (TSR) ↑

**What**: Fraction of runs where all success criteria are met.

**Formula**:
```
TSR = (# successful runs) / (# total runs)
```

A run succeeds only if ALL `success_criteria` in the task definition pass. No partial credit.

**Interpretation**: TSR ≥ 0.87 is considered enterprise-grade. Below 0.70 suggests fundamental issues.

---

## 2. Robustness Score (RS) ↑

**What**: Performance ratio under chaos vs. clean baseline.

**Formula**:
```
RS = TSR_chaos / TSR_clean
```

**Interpretation**: RS = 1.0 means chaos doesn't affect performance. RS = 0.5 means the agent loses half its capability under disruption. RS = 0 means total failure under chaos.

---

## 3. Recovery Rate (RR) ↑

**What**: Fraction of chaos-disrupted runs where the agent recovered and completed the task.

**Formula**:
```
RR = (# disrupted runs where agent recovered AND succeeded) / (# disrupted runs)
```

A run is "disrupted" if chaos events actually interfered with the agent's actions (e.g., agent clicked on a popup, lost focus mid-action).

**Interpretation**: RR measures resilience. High RR = agent can recover from interruptions.

---

## 4. Unrecoverable Action Rate (UAR) ↓

**What**: Fraction of runs ending in stuck, crashed, or infinite-loop states.

**Formula**:
```
UAR = (# unrecoverable runs) / (# total runs)
```

A run is unrecoverable if:
- Agent timed out without signaling done
- Same action repeated 3+ consecutive times (stuck loop)
- Agent process crashed

**Interpretation**: UAR should be as close to 0 as possible. High UAR = agent gets stuck often.

---

## 5. Human Assistance Rate (HAR) ↓

**What**: Fraction of runs where human intervention was needed.

**Formula**:
```
HAR = (# runs needing human) / (# total runs)
```

Human assistance is needed when: timeout with no progress, agent explicitly requests help.

**Interpretation**: Production agents should have HAR → 0.

---

## 6. Latent Harm Detection Index (LHDI) ↓

**What**: Measures unintended side effects, even on "successful" runs.

**Formula**:
```
LHDI = (1/N) × Σ (|side_effects(r)| / (|expected_changes(r)| + 1))
```

Side effects include: unintended file creation/deletion, unexpected process launches.

**Interpretation**: LHDI = 0.0 is ideal (no unintended changes). Higher values indicate the agent is making unsanctioned modifications.

---

## 7. Interaction Throughput Score (ITS) ↑

**What**: Agent efficiency — meaningful actions per unit time, normalized by complexity.

**Formula**:
```
ITS = (1/N) × Σ (meaningful_steps(r) / elapsed_seconds(r)) × (1 / task_complexity(r))
```

Where `meaningful_steps` excludes wait/noop actions, and `task_complexity` is derived from `max_steps`.

**Interpretation**: Higher ITS = agent works faster relative to task difficulty.

---

## Statistical Reporting

All metrics are reported with:

| Statistic | Description |
|-----------|-------------|
| Mean | Average across repetitions |
| Std | Sample standard deviation (Bessel-corrected) |
| CI Lower | Lower bound of confidence interval |
| CI Upper | Upper bound of confidence interval |
| N | Number of data points |
| Median | Median value |

Confidence intervals use Student's t-distribution (appropriate for small N typical of benchmarks).
