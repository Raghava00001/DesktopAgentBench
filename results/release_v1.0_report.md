# DesktopAgentBench v1.0 — Baseline Release Report

This document summarizes the baseline benchmark matrix evaluation for the v1.0 release of **DesktopAgentBench**, a Windows-only, agent-agnostic benchmark testing desktop agent reliability under safe chaos injection.

## 1. Experimental Setup

- **Task Category:** Evaluated across the expanded corpus of all benchmark tasks (Calculator, Text Editor, File Manager, Graphics, Browser, Settings, Task Manager).
- **Evaluation Matrix:** Clean Baseline vs. Isolated Disruption Profiles and Combined Chaos.
- **Agents Evaluated:**
  1. **CLAUDE**
  2. **NOOP**
  3. **OMNIPARSER**
  4. **RANDOM**
  5. **RULE**
  6. **UFO**

## 2. Core Metrics Comparison

| Agent | TSR (Success Rate) ↑ | RS (Robustness) ↑ | RR (Recovery) ↑ | UAR (Unrecoverable) ↓ | HAR (Human Help) ↓ | LHDI (Latent Harm) ↓ | ITS (Throughput) ↑ |
|-------|----------------------|-------------------|------------------|-----------------------|--------------------|----------------------|--------------------|
| **claude** | 0.2963 | 0.2071 | 0.1553 | 0.0000 | 0.0000 | 0.4346 | 0.272649 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0691 | 0.111193 |
| **omniparser** | 0.2074 | 0.1243 | 0.0777 | 0.0000 | 0.0000 | 0.0667 | 0.267562 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0852 | 0.133583 |
| **rule** | 0.0929 | 1.1455 | 0.0955 | 0.0000 | 0.0000 | 0.0643 | 0.043977 |
| **ufo** | 0.7407 | 0.7989 | 0.6990 | 0.0000 | 0.0000 | 0.0827 | 0.283240 |

> [!NOTE]
> **TSR** = Task Success Rate; **RS** = Robustness Score (TSR_chaos / TSR_clean); **RR** = Recovery Rate; **UAR** = Unrecoverable Action Rate; **HAR** = Human Assistance Rate; **LHDI** = Latent Harm Detection Index; **ITS** = Interaction Throughput Score.

## 3. Clean vs. Chaos Performance Breakdown

| Agent | Clean TSR | Delay TSR | Focus Steal TSR | Moderate TSR | Notification TSR | Popup TSR | Resize TSR | Scroll Hide TSR | Severe TSR | Uac TSR |
|---|---|---|---|---|---|---|---|---|---|---|
| **claude** | 0.7500 | 0.0000 | 0.0000 | 0.0000 | 0.7500 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **omniparser** | 0.6250 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3125 | 0.7500 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0833 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.0000 | 0.1000 | 0.0000 |
| **ufo** | 0.8750 | 0.3750 | 0.8750 | 0.5000 | 0.8750 | 0.7500 | 0.8750 | 1.0000 | 0.0000 | 0.0000 |

## 4. Key Scientific Findings

- **Finding 1: Robust Window Focusing Mitigates Chaos:** Focus-active agents like UFO achieve significantly higher TSR and RR by actively checking foreground window states and refocusing/dismissing popup modals using Windows APIs.
- **Finding 2: Baseline Safety and Unintended Action Rate:** Coordinate-naive structured agents (like Claude) produce extremely high Latent Harm indices ($0.4346$) under window shifts or focus stealing because they click absolute coordinates blindly, hitting background programs.

## 5. Production Readiness Impact Summary

Evaluating client agents using DesktopAgentBench provides clear metrics on their readiness for real-world deployment. In a production environment, desktop automation systems will inevitably encounter software notifications, window resizing/snapping, temporary OS lags, and focus-stealing update windows. A naive agent without active window-state monitoring will easily fail tasks or, worse, inject destructive actions into incorrect target applications (latent harm). By using DesktopAgentBench, developers can quantitatively assert that an agent has the necessary perceptual checks and focal control policies to handle modern busy desktop workspaces safely and reliably.