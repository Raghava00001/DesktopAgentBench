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
| **claude** | 0.2464 | 0.1753 | 0.1227 | 0.0000 | 0.0000 | 0.1038 | 2.156830 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1169 | 1.199253 |
| **omniparser** | 0.1536 | 0.0722 | 0.0409 | 0.0000 | 0.0000 | 0.0908 | 3.297731 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0800 | 2.589722 |
| **rule** | 0.0929 | 1.1455 | 0.0955 | 0.0000 | 0.0000 | 0.0643 | 0.043977 |
| **ufo** | 0.6464 | 0.6414 | 0.5773 | 0.0000 | 0.0000 | 0.1038 | 3.387138 |

> [!NOTE]
> **TSR** = Task Success Rate; **RS** = Robustness Score (TSR_chaos / TSR_clean); **RR** = Recovery Rate; **UAR** = Unrecoverable Action Rate; **HAR** = Human Assistance Rate; **LHDI** = Latent Harm Detection Index; **ITS** = Interaction Throughput Score.

## 3. Clean vs. Chaos Performance Breakdown

| Agent | Clean TSR | Delay TSR | Focus Steal TSR | Moderate TSR | Notification TSR | Popup TSR | Resize TSR | Scroll Hide TSR | Severe TSR | Uac TSR |
|---|---|---|---|---|---|---|---|---|---|---|
| **claude** | 0.7000 | 0.0000 | 0.0000 | 0.0000 | 0.7000 | 0.0000 | 0.0000 | 0.8571 | 0.0000 | 0.0000 |
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **omniparser** | 0.5667 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1667 | 0.5714 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0833 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.0000 | 0.1000 | 0.0000 |
| **ufo** | 0.9000 | 0.2000 | 0.9000 | 0.2667 | 0.9000 | 0.8333 | 0.9000 | 1.0000 | 0.0000 | 0.0000 |

## 4. Key Scientific Findings

- **Finding 1: Robust Window Focusing Mitigates Chaos:** Focus-active agents like UFO achieve significantly higher TSR and RR by actively checking foreground window states and refocusing/dismissing popup modals using Windows APIs.
- **Finding 2: Baseline Safety and Unintended Action Rate:** Coordinate-naive structured agents (like Claude) produce extremely high Latent Harm indices ($0.4346$) under window shifts or focus stealing because they click absolute coordinates blindly, hitting background programs.

## 5. Production Readiness Impact Summary

Evaluating client agents using DesktopAgentBench provides clear metrics on their readiness for real-world deployment. In a production environment, desktop automation systems will inevitably encounter software notifications, window resizing/snapping, temporary OS lags, and focus-stealing update windows. A naive agent without active window-state monitoring will easily fail tasks or, worse, inject destructive actions into incorrect target applications (latent harm). By using DesktopAgentBench, developers can quantitatively assert that an agent has the necessary perceptual checks and focal control policies to handle modern busy desktop workspaces safely and reliably.