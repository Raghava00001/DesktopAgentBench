# DesktopAgentBench — Held-Out Evaluation Plan

To prevent agents from overfitting to the public development set, DesktopAgentBench incorporates a private, held-out evaluation set (`tasks/held_out/`). This document outlines the methodology, structure, criteria, and execution protocols for the held-out task corpus.

## 1. Purpose of the Held-Out Split

The primary goals of the held-out split are:
- **Generalization Assessment**: Test the agent's capability to generalize its desktop automation skills to unseen tasks and environments.
- **Overfitting Mitigation**: Prevent benchmark developers and agent creators from hardcoding paths, UI locations, or specific app-state heuristics.
- **Robustness Under Out-of-Distribution (OOD) Scenarios**: Evaluate how agents handle new applications and advanced task combinations under identical chaos profiles.

---

## 2. Directory and Task Structure

The held-out task files are structured identically to the development split, ensuring complete compatibility with the benchmark's runner (`bench.py`) and validator.

```
tasks/
├── dev/                  # Public development split
└── held_out/             # Private/ignored held-out split
    ├── browser/
    ├── calculator/
    ├── file_manager/
    ├── graphics/
    ├── multi_app/
    ├── settings/
    ├── task_manager/
    └── text_editor/
```

### File Format Requirements
Each held-out task is a JSON file satisfying the schema rules defined in `src/schema.py`. It specifies the `split` field as `"held_out"`:
```json
{
  "task_id": "settings_heldout_001",
  "version": "1.0",
  "category": "settings",
  "app": "settings",
  "split": "held_out",
  "difficulty": "medium",
  "title": "Configure Display Scaling",
  "description": "Adjust Windows display scaling settings to 125%.",
  "natural_language_instruction": "Open Windows Settings, go to Display, and change the scale of the text and apps to 125%.",
  "preconditions": {
    "apps_required": ["SystemSettings.exe"]
  },
  "success_criteria": [
    { "type": "window_exists", "window_title": "Settings" }
  ],
  "max_steps": 25,
  "timeout_seconds": 180
}
```

---

## 3. Selection & Authoring Criteria

Held-out tasks must be created according to the following design principles to ensure academic rigor:

1. **Unseen Goals on Common Apps**: Tasks using baseline applications (e.g., Notepad, Calculator, Edge) but with distinct objectives (e.g., using calculator memory registers, complex browser search flows).
2. **Unseen Applications**: Introduces alternative software for the same categories (e.g., using WordPad or VS Code instead of Notepad; using Chrome instead of Edge).
3. **Advanced Multi-App Scenarios**: Chain multiple applications together in a single flow (e.g., calculating a statistical metric, writing the formula in a text file, and searching it on the web).
4. **Stricter Success Criteria**: Utilizing compound success criteria (e.g., matching a file regex AND ensuring the window has closed).

---

## 4. Run & Evaluation Protocols

To maintain the integrity of benchmark results, the held-out suite follows a strict execution protocol:

- **Local Execution**: Running evaluation on the local workspace requires the `tasks/held_out/` directory to be populated manually. Maintainers can run it using:
  ```bash
  python bench.py run --tasks-dir tasks/held_out --agent <agent_name>
  ```
- **Official Submission/Verification**: Authors submitting agent benchmarks for arXiv or the official leaderboard must submit their agent configuration and weights to the core maintainers. Core maintainers run the evaluation on the private held-out dataset and publish the certified scores.
- **Log Sanitation**: Run artifacts for held-out runs are stored with strict logging security, ensuring that no prompt logs or screenshots leak the task specifications.

---

## 5. Summary of Planned Held-Out Tasks

The held-out set includes **15 tasks** mapped across the 8 categories:

| Category | Task ID | App | Difficulty | Target Behavior |
|----------|---------|-----|------------|-----------------|
| `calculator` | `calc_heldout_001` | Calculator | Medium | Chain trigonometric and log operations |
| `text_editor` | `notepad_heldout_001` | WordPad | Easy | Create formatted RTF document |
| `text_editor` | `notepad_heldout_002` | Notepad | Medium | Batch find-and-replace text |
| `file_manager` | `explorer_heldout_001` | Explorer | Medium | Extract nested zip and verify checksum |
| `file_manager` | `explorer_heldout_002` | Command Prompt | Hard | Directory cleanup script creation |
| `graphics` | `paint_heldout_001` | Paint | Hard | Draw a composite shapes layout |
| `browser` | `browser_heldout_001` | Edge | Easy | Download a PDF file from a specific URL |
| `browser` | `browser_heldout_002` | Edge | Medium | Parse table data from local HTML file |
| `browser` | `browser_heldout_003` | Chrome | Hard | Multi-tab form submission flow |
| `multi_app` | `multi_heldout_001` | Calc + Notepad | Medium | Calculate values and log to file |
| `multi_app` | `multi_heldout_002` | Notepad + Browser | Hard | Scrap web quotes and compile a list |
| `settings` | `settings_heldout_001` | Settings | Medium | Toggle high contrast theme |
| `settings` | `settings_heldout_002` | Settings | Hard | Change mouse pointer size & color |
| `task_manager` | `taskmgr_heldout_001` | Task Manager | Easy | Identify and terminate hung processes |
| `task_manager` | `taskmgr_heldout_002` | Process Explorer | Medium | Monitor CPU usage of a specific background task |
