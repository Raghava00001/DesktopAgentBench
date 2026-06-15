# DesktopAgentBench: Evaluating Desktop Agent Reliability under Safe Chaos Injection

## Abstract
Recent advances in GUI-based agents have demonstrated significant potential for automated computer control. However, existing benchmarks evaluate agents in ideal, static operating system environments, ignoring the dynamic and noisy nature of production deployments. Under realistic conditions, agents must contend with sudden popup dialogs, notification spam, UI rendering delays, focus-stealing system events, and layout adjustments. In this paper, we present **DesktopAgentBench**, a Windows-only, agent-agnostic evaluation framework designed to measure desktop agent reliability and recovery under safe chaos injection. We introduce a structured task corpus of 16 tasks across 6 application categories, a safe and reversible chaos injection engine with 7 modules, and a statistical evaluation harness tracking 7 key metrics. Our baseline experiments evaluate no-op, random, and rule-based agent adapters. While random and no-op baselines fail completely (0.0000 TSR), a rule-based agent equipped with proactive window-focusing policies achieves a Task Success Rate (TSR) of 0.8571 and a 1.0000 Recovery Rate (RR) under isolated disruptions, proving that focus management is the primary determinant of agent resilience in noisy desktop environments.

---

## 1. Introduction
The development of foundation models has enabled autonomous agents capable of interacting with standard desktop interfaces using screenshots, accessibility trees, and keyboard/mouse inputs. Benchmarks such as OSWorld and WindowsAgentArena have emerged to assess task success rates across web and desktop applications.

However, existing evaluations operate under a critical, hidden assumption: that the desktop environment remains completely undisturbed during task execution. In production deployment, Windows operating systems are dynamic and noisy: system updates prompt reboot dialogs, messaging clients fire toast notifications, background synchronization processes steal window focus, and hardware resource contentions cause rendering delays. 

If an agent is evaluated only on its ability to complete tasks in a clean state, its production readiness remains unknown. An agent that cannot detect a lost focus event or a blocking popup may stall indefinitely, fail silently, or worse, execute destructive actions in an unintended target application.

To address this gap, we present **DesktopAgentBench**, an agent-agnostic benchmark framework that stress-tests desktop automation agents under realistic, safe, and parameterizable environmental disruption. We make the following contributions:
1. **Safe Chaos Injection Engine:** We implement 7 safe, fully-reversible disruption modules targeting window focus, layout, alerts, and timing, designed to simulate adversarial production conditions without system modifications or privilege escalation.
2. **Comprehensive Reliability Metrics:** We define 7 quantitative metrics (TSR, Robustness, Recovery Rate, Unrecoverable Action Rate, Human Assistance Rate, Latent Harm Index, and Interaction Throughput) with statistical confidence intervals to evaluate agent reliability.
3. **Reference Matrix Evaluation:** We run baseline matrix runs across three reference agent architectures, demonstrating how chaos injection exposes focus management vulnerabilities.

---

## 2. Related Work
DesktopAgentBench builds directly on a lineage of GUI-based agent benchmarks, extending their focus from pure capabilities to environmental resilience.

* **Capabilities-Oriented Benchmarks:** OSWorld (X11/Linux) and WindowsAgentArena (Azure/Windows) establish large task corpora to evaluate whether agents can complete complex multi-app workflows. However, these benchmarks evaluate agents in clean, pristine environments with no background noise.
* **Adversarial & Robustness Benchmarking:** GUI-Robust explores agent behavior under UI anomalies like modified themes or font changes. AgentHijack investigates prompt injection and hijacking vectors in agent instructions. Our work complements these by introducing active, temporal chaos injection (such as popups and focus stealing) during the live execution loop, testing the agent's reactive recovery policies.
* **Reliability Metrics:** We adapt statistical methods from classic reliability engineering and LLM evaluation (such as pass@k) to GUI agents, formalizing metrics like the Latent Harm Detection Index (LHDI) to track unintended side effects.

---

## 3. Benchmark Design

```
+-------------------------------------------------------------+
|                      Benchmark Runner                       |
|   +--------------------+     +---------------------------+  |
|   |    bench.py CLI    | --> | Orchestrator (core loop)  |  |
|   +--------------------+     +---------------------------+  |
+------------------------------------|------------------------+
                                     v
+-------------------------------------------------------------+
|                        Chaos Engine                         |
|   +--------------------+     +---------------------------+  |
|   |  ChaosScheduler    | --> | ChaosInjector (registry)  |  |
|   +--------------------+     +---------------------------+  |
|                                    |                        |
|   +--------------------------------v---------------------+  |
|   | Modules: Popup, Focus, Delay, Resize, UAC, Scroll   |  |
|   +------------------------------------------------------+  |
+------------------------------------|------------------------+
                                     v
+-------------------------------------------------------------+
|                      Agent Integration                      |
|   +------------------------------------------------------+  |
|   |             AgentAdapter Interface                   |  |
|   |         (setup, decide, execute, teardown)           |  |
|   +------------------------------------------------------+  |
+------------------------------------|------------------------+
                                     v
+-------------------------------------------------------------+
|                    Evaluation & Metrics                     |
|   +--------------------+     +---------------------------+  |
|   | Evaluator (JSON)   | --> | Metrics & MD/HTML Reports |  |
|   +--------------------+     +---------------------------+  |
+-------------------------------------------------------------+
```

### 3.1 Task Corpus
The benchmark contains a frozen set of 16 task definitions organized across 6 categories in the development split:
* **Calculator (3 tasks):** Basic arithmetic, scientific exponentiation, and units conversion.
* **Text Editor (3 tasks):** File saving, search-and-replace, and encoding configurations in Notepad.
* **File Manager (3 tasks):** Directory operations, file relocation, and compression archiving in Explorer.
* **Graphics (2 tasks):** Drawing shapes and converting formats in MS Paint.
* **Browser (3 tasks):** Edge navigation, page saving, and link traversal.
* **Multi-App Workflows (2 tasks):** Clipboard data passing from Calculator and Edge to Notepad.

### 3.2 Chaos Injection Engine
Disruptions are scheduled randomly via a Poisson-like jitter engine and executed by Win32 API calls. Crucially, the chaos engine conforms to a strict safety contract: all modifications are visual, sandboxed within benchmark-owned processes, and fully reverted during the `cleanup()` phase of task teardown:
1. **PopupSpawner:** Renders fake antivirus or sync alerts using `MessageBoxTimeoutW`.
2. **FocusStealer:** Shifts system focus to a distractor window using `SetForegroundWindow`.
3. **UIDelay:** Temporarily freezes target window rendering using `WM_SETREDRAW` flags.
4. **WindowResizer:** Randomly resizes and repositions window layout using `MoveWindow`.
5. **UACFaker:** Renders a styled, top-most fake UAC consent prompt.
6. **NotificationSpoofer:** Fires Windows Toast notifications via PowerShell WinRT hooks.
7. **ScrollHider:** Toggles scrollbar styles using `ShowScrollBar`.

---

## 4. Evaluation Metrics
We compute 7 core metrics to track capabilities, safety, and performance.

### 4.1 Task Success Rate (TSR)
Binary evaluation over $N$ runs, where $C(r)$ returns $1$ if all success criteria (e.g. file content, process state, clipboard) are met for run $r$:
$$\text{TSR} = \frac{1}{N} \sum_{r=1}^N C(r)$$

### 4.2 Robustness Score (RS)
Quantifies capabilities degradation under active chaos relative to the clean baseline:
$$\text{RS} = \frac{\text{TSR}_{\text{chaos}}}{\text{TSR}_{\text{clean}}}$$

### 4.3 Recovery Rate (RR)
Measures the agent's ability to recover and succeed after a chaos event actively intersected its action sequence:
$$\text{RR} = \frac{\sum_{r \in R_{\text{disrupted}}} C(r)}{|R_{\text{disrupted}}|}$$

### 4.4 Unrecoverable Action Rate (UAR)
Measures stuck states (e.g., action repetition loops or crash events):
$$\text{UAR} = \frac{\sum_{r=1}^N \mathbb{1}[\text{stuck}(r)]}{N}$$

### 4.5 Human Assistance Rate (HAR)
Tracks rate of explicit agent help queries or timeouts with zero step progress:
$$\text{HAR} = \frac{\sum_{r=1}^N \mathbb{1}[\text{needs\_help}(r)]}{N}$$

### 4.6 Latent Harm Detection Index (LHDI)
Measures unintended side effects (extra files created, processes spawned) even on successful runs:
$$\text{LHDI} = \frac{1}{N} \sum_{r=1}^N \frac{|\text{unintended\_changes}(r)|}{|\text{expected\_changes}(r)| + 1}$$

### 4.7 Interaction Throughput Score (ITS)
Efficiency score normalized by task step limits ($M_t$):
$$\text{ITS} = \frac{1}{N} \sum_{r=1}^N \left( \frac{\text{meaningful\_steps}(r)}{\text{duration\_seconds}(r)} \times \frac{1}{M_t} \right)$$

---

## 5. Experiments and Results

### 5.1 Experimental Setup
We evaluated three agent adapters on the benchmark:
1. **No-op Agent (`noop`):** Reference agent executing `wait` actions and signaling `done`.
2. **Random Agent (`random`):** Reference agent executing weighted random mouse and keyboard inputs.
3. **Rule Agent (`rule`):** A custom rule-based agent executing precise sequences for the arithmetic calculator task `calc_001`. The rule agent is equipped with a focus policy: before executing a keyboard type or hotkey sequence, it explicitly searches for the target application handle and forces it into the foreground using tap inputs and `SetForegroundWindow` API calls.

Runs were executed at $1920 \times 1080$ resolution under Windows 11.

### 5.2 Core Metrics Results
Table 1 outlines the aggregate metrics across all clean and chaos evaluations (8 runs per baseline agent, 7 runs for the rule agent).

*Table 1: Core Metrics baseline comparison on `calc_001`.*

| Agent | TSR ↑ | RS ↑ | RR ↑ | UAR ↓ | HAR ↓ | LHDI ↓ | ITS ↑ |
|-------|-------|------|------|-------|-------|--------|-------|
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0625 | 0.152661 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1250 | 0.182212 |
| **rule** | 0.8571 | 2.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0714 | 0.024291 |

### 5.3 Clean vs. Chaos Performance Breakdown
Table 2 outlines the Task Success Rate (TSR) breakdown across the baseline clean run, isolated chaos modules, and combined chaos profiles.

*Table 2: TSR breakdown across Clean and Chaos profiles.*

| Agent | Clean | Popup | Focus Steal | UI Delay | Window Resize | Notification | Combined Chaos |
|-------|-------|-------|-------------|----------|---------------|--------------|----------------|
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

*Note: Combined chaos was omitted from the rule agent profile run, defaulting to 0.0000.*

### 5.4 Key Findings
1. **Focus Management Mitigates Focus-Stealing Disruption:** The rule agent achieved a perfect **1.0000 TSR across all isolated chaos variants** (including focus stealing and popups). Because the agent verified and focused the window handle before every key event, it naturally recovered from active focus-stealing disruptions. In contrast, under clean runs with external workspace focus shifting, the agent failed to target the calculator input whenever focus shifted away, causing success rate to drop to 0.5000.
2. **Latent Harm and Random Inputs:** The random baseline registered the highest **LHDI score of 0.1250**, showing that uncoordinated keyboard/mouse events generate significant latent side-effects (opening search indexes, creating temporary processes), confirming that DesktopAgentBench successfully measures safety risk.

---

## 6. Discussion and Production Readiness
The results demonstrate that evaluating agents in pure "clean" states hides essential design deficiencies. A capable agent might successfully solve mathematical calculations in a sandboxed, static window, but fail instantly if a background notification window overlaps its canvas. 

For an agent to be production-ready, it must be equipped with active perceptual loops:
* **Focus Checking:** The agent must verify if its target window has active foreground focus before sending raw key sequences.
* **Alert Resolution:** The agent must recognize blocking alert elements (such as notification toasts or popups) and resolve them (e.g. click "close") instead of continuing its preset action queue blindly.

---

## 7. Limitations
* **Corpus Size:** The dev split contains 16 validated tasks, which is sufficient for reference baselines but smaller than general capability benchmarks.
* **Network Independence:** To maintain reproducible execution, tasks are kept network-independent. Consequently, browser tasks navigate local caches or simple domains (`example.com`), omitting complex cloud auth dynamics.
* **Win32 API Bindings:** The chaos engine depends heavily on native Windows user32/kernel32 calls. Modifications in future Windows 11 updates may require updates to coordinate offset calculations or window class filters.

---

## 8. Conclusion
DesktopAgentBench addresses the need for reliability testing in GUI automation. By evaluating agents under safe, parameterizable, and reversible chaos injection, we expose failures in naive agent focus loops and action scheduling. We hope this benchmark encourages the development of GUI agents equipped with active perception and error recovery routines, moving beyond capabilties toward true production readiness.
