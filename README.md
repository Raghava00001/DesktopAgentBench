# DesktopAgentBench

[![CI](https://github.com/Raghava00001/DesktopAgentBench/actions/workflows/ci.yml/badge.svg)](https://github.com/Raghava00001/DesktopAgentBench/actions/workflows/ci.yml)

**A Windows-only, agent-agnostic reliability benchmark for desktop agents with safe chaos injection.**

DesktopAgentBench evaluates the production readiness of desktop automation agents by testing them under realistic but safe adversarial conditions. It doesn't build an agent — it stress-tests yours.

> **v1.0** — 30 tasks · 8 categories · 7 chaos modules · 7 metrics · 6 baseline agents · **7,280 total runs**

| Stat | Value |
|------|-------|
| Tasks (dev split) | 30 |
| Categories | 8 (calculator, text_editor, file_manager, graphics, browser, multi_app, settings, task_manager) |
| Chaos profiles | 10 |
| Baseline agents | 6 (noop, random, rule, ufo, claude, omniparser) |
| Total evaluation runs | 7,280 |
| Best agent TSR (UFO) | 0.6464 |

See [LEADERBOARD.md](LEADERBOARD.md) to compare all six baselines. See [docs/research_paper.md](docs/research_paper.md) for full results and analysis.


## Key Features

- **🎯 Agent-Agnostic** — Plug in any agent by implementing the `AgentAdapter` interface
- **🌪️ Chaos Injection** — 7 safe disruption modules: popups, focus stealing, UI delays, window resizing, fake UAC, notifications, scroll hiding
- **📊 7 Metrics** — TSR, RS, RR, UAR, HAR, LHDI, ITS with statistical confidence intervals
- **🔁 Reproducible** — Deterministic random seeds, JSONL logging, screenshot capture
- **📋 Extensible** — Plugin-based architecture for chaos modules, agents, and tasks

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Validate task corpus
python bench.py validate --tasks-dir tasks/

# List available tasks
python bench.py list-tasks

# Run benchmark with noop agent (harness test)
python bench.py run --agent builtin:noop --config configs/default.yaml

# Run with a specific task and chaos profile
python bench.py run --agent builtin:random --tasks notepad_001 --profile moderate -n 3

# Regenerate reports from existing results
python bench.py report results/
```

## Integrating Your Agent

1. Create `agents/my_agent/adapter.py`
2. Subclass `AgentAdapter` from `src.agents.adapter`
3. Implement all abstract methods (`setup`, `decide`, `execute_action`, etc.)
4. Run: `python bench.py run --agent agents.my_agent.adapter:MyAgent`

See [docs/AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md) for full details.

## Chaos Profiles

| Profile | Modules Enabled | Use Case |
|---------|----------------|----------|
| `clean` | None | Baseline measurement |
| `mild` | UI delay, notifications | Gentle warmup |
| `moderate` | Popups, focus steal, delay, resize, notifications | Realistic workday |
| `severe` | All 7 modules at high frequency | Stress test |

## Metrics

| Metric | Abbrev. | Direction | What it measures |
|--------|---------|-----------|-----------------|
| Task Success Rate | TSR | ↑ | Did the agent complete the task? |
| Robustness Score | RS | ↑ | Performance under chaos vs. clean |
| Recovery Rate | RR | ↑ | Recovery after disruption |
| Unrecoverable Action Rate | UAR | ↓ | Stuck/crashed states |
| Human Assistance Rate | HAR | ↓ | Need for human intervention |
| Latent Harm Detection Index | LHDI | ↓ | Unintended side effects |
| Interaction Throughput Score | ITS | ↑ | Efficiency per unit complexity |

See [docs/METRICS.md](docs/METRICS.md) for formulas and computation details.

## Project Structure

```
├── bench.py                    # CLI entry point
├── configs/                    # YAML configurations
│   ├── default.yaml
│   └── chaos_profiles/         # clean, mild, moderate, severe
├── src/
│   ├── core/                   # Orchestrator, evaluator, recorder
│   ├── tasks/                  # Task schema, loader, variants
│   ├── chaos/                  # Chaos engine & 7 modules
│   ├── agents/                 # Agent adapter ABC & builtins
│   ├── metrics/                # Calculator, statistics, reporter
│   └── platform/               # Win32 utilities
├── tasks/                      # Task corpus (30 tasks, JSON)
│   ├── dev/                    # Public development split
│   └── held_out/               # Private held-out split
├── scripts/                    # Experiment scripts
├── results/                    # Benchmark outputs
└── docs/                       # Documentation
```

## Safety

All chaos injections are:
- **Non-destructive** — No system modifications, registry changes, or file deletions
- **Reversible** — All modules implement cleanup with original state restoration
- **Sandboxed** — Chaos windows are owned by the benchmark process
- **Logged** — Every injection event is recorded with timestamps
- **Tagged** — Chaos windows are prefixed with `[DAB]` for transparency

## License

MIT

## Architecture

DesktopAgentBench isolates orchestrator lifecycle loops, environment setups, and baseline evaluations. Below is an overview of the directory structure:

```
src/
├── core/                   # Orchestrator core
│   ├── config.py           # Benchmark YAML & Pydantic settings schema
│   ├── orchestrator.py     # Setup, run loop control, and clean teardown
│   ├── evaluator.py        # System diffing & task criteria validators
│   └── recorder.py         # JSONL logger, actions and screenshot saver
├── tasks/                  # Task loader and schemas
│   ├── schema.py           # Task criteria, preconditions, and metadata types
│   ├── loader.py           # Scrapes tasks/ folders and verifies structures
│   ├── split_manager.py    # Segment public dev set vs private held-out set
│   └── variant_generator.py# Expands clean configs to combined chaos runs
├── agents/                 # Agent interfaces and baseline adapters
│   ├── adapter.py          # Abstract AgentAdapter interface
│   ├── registry.py         # Dynamic plugin discovery for agent codebases
│   └── builtin/            # Baseline models (noop, random, rule, claude)
├── chaos/                  # Parameterized environment injectors
│   ├── injector.py         # Thread-safe launcher & cleanup tracker
│   ├── scheduler.py        # Poisson timing model for trigger signals
│   ├── registry.py         # Dynamic load mechanisms for chaos tasks
│   └── modules/            # Visual disruption scripts (UAC, popups, etc.)
└── platform/               # Low-level Windows Win32 ctypes hooks
    ├── process_manager.py  # Spawns, monitors, and terminates processes
    ├── window_manager.py   # Locates application HWND boundaries
    └── win32_utils.py      # Win32 DLL calls (foreground locks, displays)
```

#### 🔄 System Sequence Lifecycle
1. **Configure**: `bench.py` reads user parameters and overrides defaults using `src/core/config.py`.
2. **Assemble**: `TaskLoader` validates JSON files against `src/tasks/schema.py` while `VariantGenerator` pairs them with chaos settings.
3. **Execute**: The `Orchestrator` resets the Windows environment (`_clean_task_artifacts`), spins up background scheduler loops (`ChaosScheduler`), launches applications (`ProcessManager`), and yields control to the agent via `AgentAdapter.decide()`.
4. **Evaluate**: At shutdown, `Evaluator` runs success checks, collects files/registry changes to verify `LHDI` (Latent Harm Detection Index), and `Reporter` outputs markdown summaries.
