# DesktopAgentBench v1.0 Release Notes

We are excited to announce the release of **DesktopAgentBench v1.0**, a robust, agent-agnostic benchmark framework for Windows desktop automation agents. 

This release includes the complete evaluation matrix comparing six baseline agents under various safe chaos injection conditions.

---

## Benchmark Scope & Methodology

DesktopAgentBench v1.0 evaluates agents on a structured matrix designed to stress-test their reliability:

- **Task Corpus**: 30 canonical tasks across 8 core Windows categories:
  - `calculator`, `text_editor`, `file_manager`, `graphics`, `browser`, `multi_app`, `settings`, `task_manager`
- **Chaos Injection**: 10 disruption profiles (Clean, Delay, Focus Steal, Moderate Combined, Notification, Popup, Resize, Scroll Hide, Severe Combined, UAC).
- **Baselines Tested**: 6 baseline agent configurations:
  - **No-op**: A control baseline executing no actions.
  - **Random**: A control baseline performing random mouse and keyboard interactions.
  - **Rule Agent**: A task-specialized calculator baseline.
  - **Claude Computer Use**: Naive absolute-coordinate structured agent.
  - **OmniParser Agent**: Naive relative-coordinate structured agent.
  - **UFO (Windows UI-Automation-based)**: Focus-aware active-monitoring agent.
- **Evaluation Runs**: 7,280 total evaluation runs conducted to yield high-confidence scientific metrics.

---

## Key Metrics Summary

Across the 7,280 runs, the overall success rates and robustness metrics are aggregated below:

- **Task Success Rate (TSR)**: UFO achieved the highest success rate of **64.64%** overall, followed by Claude at **24.64%**, OmniParser at **15.36%**, and the calculator-only Rule Agent at **9.29%**.
- **Robustness Score (RS)**: Measures the ratio of success rate under chaos to success rate in clean environments. UFO demonstrated superior robustness at **0.6414**.
- **Recovery Rate (RR)**: Measures how often an agent recovers from a transient failure once the disruption clears. UFO successfully recovered in **57.73%** of disrupted steps.
- **Latent Harm Detection Index (LHDI)**: Claude and No-op generated high latent harm metrics (**0.1038** and **0.1169** respectively), indicating that naive absolute-coordinate clicking often impacts background windows/folders when target apps are shifted or resized.

---

## How to Get Started

To run the v1.0 benchmark and evaluate your own agent:
1. Follow the setup instructions in [CONTRIBUTING.md](../CONTRIBUTING.md).
2. Configure your agent configuration inside `src/agents/`.
3. Launch the evaluator:
   ```bash
   python bench.py run --tasks-dir tasks/dev --agent <your_agent>
   ```
4. Generate evaluation reports using:
   ```bash
   python aggregate_results.py
   ```
