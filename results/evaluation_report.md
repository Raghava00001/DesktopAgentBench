# DesktopAgentBench — Empirical Evaluation Report

This report aggregates all baseline evaluations across the task corpus, groups tasks dynamically by category, and validates the benchmark's core hypotheses.

## 1. Core Metrics Comparison Summary

The following table compares the 7 core metrics computed across all runs in the matrix evaluation.

| Agent | TSR (Success Rate) ↑ | RS (Robustness) ↑ | RR (Recovery) ↑ | UAR (Unrecoverable) ↓ | HAR (Human Help) ↓ | LHDI (Latent Harm) ↓ | ITS (Throughput) ↑ |
|-------|----------------------|-------------------|------------------|-----------------------|--------------------|----------------------|--------------------|
| **claude** | 0.2464 | 0.1753 | 0.1227 | 0.0000 | 0.0000 | 0.1038 | 2.156830 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1169 | 1.199253 |
| **omniparser** | 0.1536 | 0.0722 | 0.0409 | 0.0000 | 0.0000 | 0.0908 | 3.297731 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0800 | 2.589722 |
| **rule** | 0.0929 | 1.1455 | 0.0955 | 0.0000 | 0.0000 | 0.0643 | 0.043977 |
| **ufo** | 0.6464 | 0.6414 | 0.5773 | 0.0000 | 0.0000 | 0.1038 | 3.387138 |

Note: The Rule Agent is a Task-Specialized Baseline: Calculator only. It is configured with hardcoded task sequences for calculator and basic notepad tasks, failing to generalize to the rest of the corpus.

## 2. Disruption Profile Breakdown (TSR)

The table below breaks down the Task Success Rate (TSR) across clean runs, isolated chaos modules, and combined chaos profiles.

| Agent | Clean TSR | Delay TSR | Focus Steal TSR | Moderate TSR | Notification TSR | Popup TSR | Resize TSR | Scroll Hide TSR | Severe TSR | Uac TSR |
|---|---|---|---|---|---|---|---|---|---|---|
| **claude** | 0.7000 | 0.0000 | 0.0000 | 0.0000 | 0.7000 | 0.0000 | 0.0000 | 0.8571 | 0.0000 | 0.0000 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **omniparser** | 0.5667 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1667 | 0.5714 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0833 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.0000 | 0.1000 | 0.0000 |
| **ufo** | 0.9000 | 0.2000 | 0.9000 | 0.2667 | 0.9000 | 0.8333 | 0.9000 | 1.0000 | 0.0000 | 0.0000 |

## 3. Dynamic Category Performance (TSR)

The table below shows the average success rate (TSR) grouped dynamically by application category.

| Agent | Browser TSR | Calculator TSR | File Manager TSR | Graphics TSR | Multi App TSR | Settings TSR | Task Manager TSR | Text Editor TSR |
|---|---|---|---|---|---|---|---|---|
| **claude** | 0.2444 | 0.2222 | 0.2333 | 0.1667 | 0.3636 | 0.2222 | 0.0000 | 0.3389 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **omniparser** | 0.0870 | 0.2222 | 0.1778 | 0.1111 | 0.1364 | 0.0741 | 0.0000 | 0.2667 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0000 | 0.2963 | 0.0000 | 0.0000 | 0.0000 | 0.3333 | 0.5000 | 0.0000 |
| **ufo** | 0.5722 | 0.8519 | 0.7426 | 0.3333 | 0.5909 | 0.6667 | 0.3333 | 0.7278 |

## 4. Hypothesis Testing & Validation

We tested the three core hypotheses formulated for DesktopAgentBench reliability evaluation:

- **H1: Combined chaos causes the largest degradation** — **NOT SUPPORTED**
  - UFO Clean Baseline TSR: 0.9000
  - UFO Isolated Chaos TSRs (Min/Max): 0.0000/1.0000
  - UFO Combined Chaos (Moderate) TSR: 0.2667
- **H2: Focus-aware agents recover better than naive agents** — **SUPPORTED**
  - UFO Agent (Focus-Aware) Recovery Rate: 0.5773
  - Rule Agent (Focus-Aware) Recovery Rate: 0.0955
  - Claude Computer Use (Naive) Recovery Rate: 0.1227
  - OmniParser Agent (Naive) Recovery Rate: 0.0409
- **H3: Random agents create more latent harm than structured agents** — **NOT SUPPORTED**
  - Random Agent Latent Harm Index: 0.0800
  - Claude Computer Use Latent Harm Index: 0.1038
  - OmniParser Agent Latent Harm Index: 0.0908
  - Rule Agent Latent Harm Index: 0.0643
  - Noop Agent Latent Harm Index: 0.1169

## 5. Statistical Release Metadata
- **Claude Session Path:** results\session_20260617_014901_90b305
- **Noop Session Path:** results\session_20260616_223041_0a08ee
- **Omniparser Session Path:** results\session_20260617_100741_2b4a9e
- **Random Session Path:** results\session_20260617_005311_f58b96
- **Rule Session Path:** results\session_20260616_143506_d62997
- **Ufo Session Path:** results\session_20260617_002320_391a81
- **Status:** Frozen v1.0, task-agnostic aggregation complete.