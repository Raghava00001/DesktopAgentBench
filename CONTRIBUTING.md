# Contributing to DesktopAgentBench

Welcome! We appreciate your interest in contributing to DesktopAgentBench. This document provides step-by-step guidelines for setting up the environment, writing unit tests, and adding new tasks, agents, and chaos modules to the benchmark.

---

## 1. Development Setup & Running Tests

DesktopAgentBench is designed to run on **Windows** environments, but code development and unit testing can also be performed with Win32 API mocks in headless CI environments.

### Environment Setup
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/Raghava00001/DesktopAgentBench.git
   cd DesktopAgentBench
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install pytest pytest-cov
   ```

### Running Verification & Tests
Before making a pull request, verify that the task corpus is valid and all unit tests pass:
- **Corpus Validation**:
  ```bash
  python bench.py validate
  ```
- **Run Unit Tests**:
  ```bash
  python -m pytest
  ```

---

## 2. How to Add a New Task

Benchmark tasks are defined as JSON files grouped by category under the `tasks/dev/` directory.

### Steps to Add a Task:
1. Identify the application category (e.g., `text_editor`, `browser`, `calculator`).
2. Create a new JSON file under `tasks/dev/{category}/` named `{app}_{id}.json` (e.g., `notepad_004.json`).
3. Fill out the task schema. Refer to [TASK_AUTHORING.md](docs/TASK_AUTHORING.md) for a detailed reference on preconditions, success criteria, and schema types.
4. Validate the task definition file:
   ```bash
   python bench.py validate
   ```

---

## 3. How to Add a New Agent

To integrate a new baseline or custom agent into the benchmark runner:

### Steps to Add an Agent:
1. Create a new subclass of `BaseAgent` under `src/agents/` (e.g., `src/agents/my_custom_agent.py`):
   ```python
   from src.agents.base import BaseAgent
   
   class MyCustomAgent(BaseAgent):
       """Your agent implementation details."""
       def take_action(self, observation):
           # Analyze observation and return action
           return {"action": "click", "coords": (100, 200)}
   ```
2. Register your agent inside the runner:
   - Modify `src/agents/__init__.py` or the agent factory/registry to include your custom class.
3. Document any API keys or specific runtime configuration needed in a markdown file under `docs/`.
4. Detailed integration requirements can be found in [AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md).

---

## 4. How to Add a New Chaos Module

Adversarial chaos modules are defined as custom components that inject window-level or system-level disruptions.

### Steps to Add a Chaos Module:
1. Implement your chaos logic inside a class in `src/chaos/` (e.g., `src/chaos/my_new_disruption.py`):
   ```python
   from src.chaos.base import BaseChaosModule
   
   class MyNewDisruption(BaseChaosModule):
       def inject(self):
           # Perform temporary win32 window movement or notification popups
           pass
           
       def restore(self):
           # Restore the original desktop state
           pass
   ```
2. Register the module in `src/chaos/__init__.py` so that it can be enabled via profiles.
3. Update [CHAOS_MODULES.md](docs/CHAOS_MODULES.md) with parameters and descriptions of the disruption.
4. Add unit tests for your chaos module in `tests/test_chaos_modules.py`.
