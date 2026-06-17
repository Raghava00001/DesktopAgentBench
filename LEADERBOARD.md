# DesktopAgentBench Official Leaderboard

This leaderboard presents the comparative evaluation of the six baseline agents tested on the frozen v1.0 benchmark (30 tasks, 8 categories, 10 disruption profiles, 7,280 total evaluation runs).

---

## Table 1: Overall Agent Reliability Metrics

Evaluates core reliability, recovery, latent harm, and throughput metrics across all task-chaos configurations.

| Agent | TSR (Success Rate) ↑ | RS (Robustness) ↑ | RR (Recovery) ↑ | UAR (Unrecoverable) ↓ | HAR (Human Help) ↓ | LHDI (Latent Harm) ↓ | ITS (Throughput) ↑ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **UFO** | **0.6464** | **0.6414** | **0.5773** | 0.0000 | 0.0000 | 0.1038 | 3.387138 |
| **Claude** | 0.2464 | 0.1753 | 0.1227 | 0.0000 | 0.0000 | 0.1038 | 2.156830 |
| **OmniParser** | 0.1536 | 0.0722 | 0.0409 | 0.0000 | 0.0000 | 0.0908 | 3.297731 |
| **Rule Agent** | 0.0929 | 1.1455 | 0.0955 | 0.0000 | 0.0000 | **0.0643** | 0.043977 |
| **Random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0800 | 2.589722 |
| **No-op** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1169 | 1.199253 |

*Note on Rule Agent:* The Rule Agent is a task-specialized calculator baseline. It operates with hardcoded task sequences for calculator and basic notepad tasks, failing to generalize to the rest of the corpus.

---

## Table 2: Success Rate (TSR) by Disruption Profile

Breaks down agent performance under isolated and combined chaos profiles to analyze specific points of vulnerability.

| Agent | Clean | Delay | Focus Steal | Moderate (Combined) | Notification | Popup | Resize | Scroll Hide | Severe (Combined) | UAC |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **UFO** | **0.9000** | **0.2000** | **0.9000** | **0.2667** | **0.9000** | **0.8333** | **0.9000** | **1.0000** | 0.0000 | 0.0000 |
| **Claude** | 0.7000 | 0.0000 | 0.0000 | 0.0000 | 0.7000 | 0.0000 | 0.0000 | 0.8571 | 0.0000 | 0.0000 |
| **OmniParser** | 0.5667 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1667 | 0.5714 | 0.0000 | 0.0000 |
| **Rule Agent** | 0.0833 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.1000 | 0.0000 | **0.1000** | 0.0000 |
| **Random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **No-op** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

---

## Table 3: Success Rate (TSR) by Application Category

Evaluates performance across the 8 functional categories of the public development task corpus.

| Agent | Browser | Calculator | File Manager | Graphics | Multi App | Settings | Task Manager | Text Editor |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **UFO** | **0.5722** | **0.8519** | **0.7426** | **0.3333** | **0.5909** | **0.6667** | 0.3333 | **0.7278** |
| **Claude** | 0.2444 | 0.2222 | 0.2333 | 0.1667 | 0.3636 | 0.2222 | 0.0000 | 0.3389 |
| **OmniParser** | 0.0870 | 0.2222 | 0.1778 | 0.1111 | 0.1364 | 0.0741 | 0.0000 | 0.2667 |
| **Rule Agent** | 0.0000 | 0.2963 | 0.0000 | 0.0000 | 0.0000 | 0.3333 | **0.5000** | 0.0000 |
| **Random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **No-op** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
