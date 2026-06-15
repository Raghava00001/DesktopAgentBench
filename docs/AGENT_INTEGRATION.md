# Agent Integration Guide

This guide explains how to integrate your desktop agent with DesktopAgentBench.

## Overview

To benchmark your agent, you need to:

1. Create an adapter class that subclasses `AgentAdapter`
2. Implement all abstract methods
3. Register the adapter with the benchmark harness

## The AgentAdapter Interface

```python
from src.agents.adapter import AgentAdapter, Action

class MyAgent(AgentAdapter):
    def name(self) -> str:
        return "my_agent"

    def version(self) -> str:
        return "1.0.0"

    def setup(self, task_instruction: str, app_info: dict) -> None:
        """Called once before each task. Initialize your agent here."""
        self.instruction = task_instruction

    def decide(self, screenshot, accessibility_tree, task_instruction) -> Action:
        """Core method: given current state, return the next action."""
        # Your agent's decision logic goes here
        return Action(action_type="click", parameters={"x": 100, "y": 200, "button": "left"})

    def execute_action(self, action: Action) -> bool:
        """Execute the action on the desktop. Return True if successful."""
        # Use pyautogui, pywinauto, or your preferred automation library
        return True

    def get_screenshot(self) -> Image.Image:
        """Capture the current screen."""
        from PIL import ImageGrab
        return ImageGrab.grab()

    def get_state(self) -> dict:
        """Return internal state for logging."""
        return {"step": self.step_count}

    def signals_done(self) -> bool:
        """Return True when the agent believes the task is complete."""
        return self._done

    def teardown(self) -> None:
        """Cleanup after task completion."""
        pass
```

## Supported Action Types

| Type | Parameters | Description |
|------|-----------|-------------|
| `click` | `x`, `y`, `button` | Click at screen coordinates |
| `type` | `text` | Type text at current cursor |
| `hotkey` | `keys` (list) | Press key combination |
| `scroll` | `x`, `y`, `delta` | Scroll at position |
| `drag` | `start_x`, `start_y`, `end_x`, `end_y` | Drag operation |
| `wait` | `seconds` | Wait/sleep |
| `done` | — | Signal task completion |
| `noop` | — | Do nothing this step |

## Registration Methods

### 1. Directory Placement (Recommended)

```
agents/
  my_agent/
    __init__.py
    adapter.py    # Contains your AgentAdapter subclass
```

### 2. CLI Specification

```bash
python bench.py run --agent agents.my_agent.adapter:MyAgent
```

### 3. Entry Points (pyproject.toml)

```toml
[project.entry-points."desktopagentbench.agents"]
my_agent = "my_package.adapter:MyAgent"
```

## What Your Agent Receives

- **Screenshot**: PIL Image of the current screen
- **Accessibility tree**: Optional dict of UI elements (if `supports_accessibility_tree()` returns True)
- **Task instruction**: Natural language description of the task

## What the Benchmark Records

For each step, the harness logs:
- Action type and parameters
- Screenshot at time of action
- Active chaos events (hidden from agent)
- Agent's internal state
- Timestamps and elapsed time

## Tips

1. **Don't assume clean environment** — popups, focus changes, and UI delays may occur at any time
2. **Implement recovery** — if your action fails, try to detect and adapt
3. **Signal done explicitly** — return `Action(action_type="done")` when you believe the task is complete
4. **Handle timeouts** — the harness will stop your agent after `max_steps` or `timeout_seconds`
