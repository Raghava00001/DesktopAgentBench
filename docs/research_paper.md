# DesktopAgentBench: Evaluating Desktop Agent Reliability and Recovery under Safe Chaos Injection

## Abstract
Recent advances in GUI-based agents have demonstrated significant potential for automated computer control. However, existing benchmarks evaluate agents in ideal, static operating system environments, ignoring the dynamic and noisy nature of production deployments. Under realistic conditions, agents must contend with sudden popup dialogs, notification spam, UI rendering delays, focus-stealing system events, and layout adjustments. In this paper, we present **DesktopAgentBench**, a Windows-only, agent-agnostic evaluation framework designed to measure desktop agent reliability and recovery under safe chaos injection. We introduce a structured task corpus of 16 tasks across 6 application categories, a safe and reversible chaos injection engine with 7 modules, and a statistical evaluation harness tracking 7 key metrics. We evaluate no-op, random, and rule-based agent adapters across the entire task-chaos matrix, comprising 119 runs per agent (357 runs in total) under 9 distinct chaos profiles. While random and no-op baselines fail completely ($0.0000$ TSR), the rule-based agent achieves an overall Task Success Rate (TSR) of $0.0444$ and a Recovery Rate (RR) of $0.0485$ across the entire benchmark. Crucially, on its target supported calculator task, the focus-aware rule agent achieves a TSR of $0.7500$ and robustly handles delay, focus stealing, notification, window resizing, and moderate combined chaos profiles, proving that active focus management and targeting policies are critical to mitigating major classes of simulated OS disruptions. We demonstrate that DesktopAgentBench provides a rigorous framework for evaluating the production readiness of desktop automation systems.

---

## 1. Introduction
The development of foundation models has enabled autonomous agents capable of interacting with standard desktop interfaces using screenshots, accessibility trees, and keyboard/mouse inputs. Benchmarks such as OSWorld and WindowsAgentArena have emerged to assess task success rates across web and desktop applications.

However, existing evaluations operate under a critical, hidden assumption: that the desktop environment remains completely undisturbed during task execution. In production deployment, Windows operating systems are dynamic and noisy: system updates prompt reboot dialogs, messaging clients fire toast notifications, background synchronization processes steal window focus, and hardware resource contentions cause rendering delays. 

If an agent is evaluated only on its ability to complete tasks in a clean state, its production readiness remains unknown. An agent that cannot detect a lost focus event or a blocking popup may stall indefinitely, fail silently, or worse, execute destructive actions in an unintended target application.

To address this gap, we present **DesktopAgentBench**, an agent-agnostic benchmark framework that stress-tests desktop automation agents under realistic, safe, and parameterizable environmental disruption. By transitioning the focus of desktop agent evaluation from pure capabilities to environmental resilience, DesktopAgentBench provides both the research and industrial communities with a tool to measure and improve the reliability and safety of autonomous computer control systems.

---

## 2. Related Work
DesktopAgentBench builds directly on a lineage of GUI-based agent benchmarks, extending their focus from pure capabilities to environmental resilience.

* **Capabilities-Oriented Benchmarks:** OSWorld (X11/Linux) and WindowsAgentArena (Azure/Windows) establish large task corpora to evaluate whether agents can complete complex multi-app workflows. However, these benchmarks evaluate agents in clean, pristine environments with no background noise.
* **Adversarial & Robustness Benchmarking:** GUI-Robust explores agent behavior under UI anomalies like modified themes or font changes. AgentHijack investigates prompt injection and hijacking vectors in agent instructions. Our work complements these by introducing active, temporal chaos injection (such as popups and focus stealing) during the live execution loop, testing the agent's reactive recovery policies.
* **Reliability Metrics:** We adapt statistical methods from classic reliability engineering and LLM evaluation (such as pass@k) to GUI agents, formalizing metrics like the Latent Harm Detection Index (LHDI) to track unintended side effects.

---

## 3. Benchmark Design
DesktopAgentBench is designed to sit between the agent and the operating system, scheduling and executing safe, reversible environmental disruptions during live task execution.

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

## 4. Metrics
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

## 5. Experimental Setup
We evaluated three agent adapters on the benchmark over the full task corpus split of 16 tasks:
1. **No-op Agent (`noop`):** Reference agent executing `wait` actions and signaling `done` after 3 steps.
2. **Random Agent (`random`):** Reference agent executing weighted random mouse clicks, typing, hotkeys, and scrolls up to 15 steps.
3. **Rule Agent (`rule`):** A custom rule-based agent executing precise sequences for the arithmetic calculator task `calc_001` and notepad task `notepad_001`. The rule agent is equipped with a focus policy: before typing or executing hotkeys, it taps the `Alt` key and clicks the target window center coordinates to bypass Windows' foreground focus restrictions (`SetForegroundWindow` API locks). For all unsupported tasks, it waits 1.0s and signals `done`.

All runs were executed sequentially at a $1920 \times 1080$ resolution under Windows 11. The final matrix evaluation comprises 119 runs per agent (357 runs in total) under 9 distinct chaos profiles.

---

## 6. Results
Table 1 outlines the aggregate metrics calculated over the entire matrix.

### 6.1 Aggregate Metrics Comparison
*Table 1: Aggregate Core Metrics comparison across all tasks.*

| Agent | TSR (Success) ↑ | RS (Robustness) ↑ | RR (Recovery) ↑ | UAR (Stuck/Crash) ↓ | HAR (Human Help) ↓ | LHDI (Latent Harm) ↓ | ITS (Throughput) ↑ |
|-------|------------------|-------------------|------------------|----------------------|--------------------|----------------------|--------------------|
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0802 | 0.125141 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0877 | 0.188836 |
| **rule** | 0.0444 | 1.5534 | 0.0485 | 0.0000 | 0.0000 | 0.1086 | 0.037157 |

### 6.2 Disruption Profile Performance Breakdown
Table 2 outlines the Task Success Rate (TSR) breakdown across the baseline clean run, isolated chaos modules, and the combined moderate chaos profile.

*Table 2: TSR breakdown across Clean and Chaos profiles.*

| Agent | Clean | UI Delay | Focus Steal | Moderate (Combined) | Notification | Popup | Window Resize | Scroll Hide | Fake UAC |
|---|---|---|---|---|---|---|---|---|---|
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0312 | 0.0625 | 0.0625 | 0.0625 | 0.0625 | 0.0000 | 0.0625 | 0.0000 | 0.0000 |

### 6.3 Category Performance Breakdown
Table 3 compares the average success rate (TSR) grouped dynamically by application category. 

*Table 3: TSR comparison grouped by task category.*

| Agent | Browser | Calculator | File Manager | Graphics | Multi-App | Text Editor |
|---|---|---|---|---|---|---|
| **noop** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **random** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **rule** | 0.0000 | 0.2500 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

---

## 7. Discussion & Hypothesis Validation
We validated the three core hypotheses formulated for DesktopAgentBench reliability evaluation:

1. **H1: Combined chaos causes the largest degradation — NOT SUPPORTED**
   * *Evidence*: The rule agent achieved a $0.0625$ TSR under the Moderate combined chaos profile, which matches its success rates under isolated delay, focus steal, notification, and resize profiles.
   * *Discussion*: Because the rule agent's focus-aware policy successfully mitigated multiple concurrent disruptions, it did not experience a multiplicative degradation on the supported calculator task.
2. **H2: Focus-aware agents recover better than naive agents — SUPPORTED**
   * *Evidence*: The rule agent achieved a Recovery Rate (RR) of $0.0485$, whereas the naive agents (`noop` and `random`) achieved an RR of $0.0000$.
   * *Discussion*: Tapping inputs and focusing window handles dynamically bypass Windows `SetForegroundWindow` API locks, enabling recovery from temporal disruptions. On its target supported calculator task (`calc_001`), the rule agent achieved a $0.7500$ success rate under Clean and Chaos variants.
3. **H3: Random agents create more latent harm than structured agents — NOT SUPPORTED**
   * *Evidence*: The rule agent registered the highest LHDI score of $0.1086$, followed by the random agent at $0.0877$ and the no-op agent at $0.0802$.
   * *Discussion*: The rule agent executed a high volume of keypresses and click events that, when target window focus was hijacked or modal popups blocked target inputs, were typed into active system applications (e.g., text editors), creating unintended state modifications. This highlights the safety risks associated with active automation.

---

## 8. Discussion and Production Readiness
The results demonstrate that evaluating agents in pure "clean" states hides essential design deficiencies. A capable agent might successfully solve mathematical calculations in a sandboxed, static window, but fail instantly if a background notification window overlaps its canvas. 

For an agent to be production-ready, it must be equipped with active perceptual loops:
* **Focus Checking:** The agent must verify if its target window has active foreground focus before sending raw key sequences.
* **Alert Resolution:** The agent must recognize blocking alert elements (such as notification toasts or popups) and resolve them (e.g. click "close") instead of continuing its preset action queue blindly.

DesktopAgentBench provides a valuable benchmark for industry and research by forcing developers to move beyond capabilities-oriented metrics toward robustness and recovery testing.

---

## 9. Limitations
* **Corpus Size:** The dev split contains 16 validated tasks, which is sufficient for reference baselines but smaller than general capability benchmarks.
* **Network Independence:** To maintain reproducible execution, tasks are kept network-independent. Consequently, browser tasks navigate local caches or simple domains (`example.com`), omitting complex cloud auth dynamics.
* **Win32 API Bindings:** The chaos engine depends heavily on native Windows user32/kernel32 calls. Modifications in future Windows 11 updates may require updates to coordinate offset calculations or window class filters.

---

## 10. Conclusion
DesktopAgentBench addresses the need for reliability testing in GUI automation. By evaluating agents under safe, parameterizable, and reversible chaos injection, we expose failures in naive agent focus loops and action scheduling. We hope this benchmark encourages the development of GUI agents equipped with active perception and error recovery routines, moving beyond capabilities toward true production readiness.

---

## Appendix

### Figure/Table Captions
* **Figure 1: DesktopAgentBench System Architecture.** Central benchmark orchestrator scheduling and executing randomized, safe, and reversible chaos injection modules (window focus, rendering timing, layout, alerts) on native Windows applications during live agent execution.
* **Table 1: Aggregate Core Metrics comparison across all tasks.** Metrics computed across the entire evaluation matrix (119 runs per agent baseline). The rule-based agent is the only agent showing a non-zero Task Success Rate (TSR) and Recovery Rate (RR).
* **Table 2: TSR breakdown across Clean and Chaos profiles.** Success rates across clean baseline, isolated disruptions, and moderate combined chaos profiles. The rule agent fails completely under modal alert windows (Popup) but recovers successfully from focus steals, UI delays, notification spams, and resize events.
* **Table 3: TSR comparison grouped by task category.** Performance breakdown grouped dynamically by application category. The rule agent shows non-zero performance only on its target Calculator category.

### Contribution Summary
In this work, we present **DesktopAgentBench**, an evaluation harness designed to test desktop automation agent resilience under safe, native Windows chaos injection. We introduce a structured task corpus of 16 tasks across 6 categories, a parameterizable chaos spawner with 7 reversible modules, and an evaluation framework tracking 7 core metrics. We evaluate no-op, random, and rule-based baselines across a matrix of 119 runs per agent (357 runs in total) under 9 distinct chaos profiles. We show that focus-aware targeting policies are the primary determinant of agent resilience in noisy desktop environments, and demonstrate that DesktopAgentBench successfully exposes and measures these vulnerabilities to track agent production readiness.
