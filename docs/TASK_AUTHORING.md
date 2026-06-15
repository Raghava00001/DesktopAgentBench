# Task Authoring Guide

How to create new benchmark tasks for DesktopAgentBench.

## Task File Format

Each task is a JSON file placed in `tasks/dev/{category}/` or `tasks/held_out/{category}/`.

### Minimal Example

```json
{
  "task_id": "myapp_001",
  "version": "1.0",
  "category": "text_editor",
  "app": "notepad",
  "split": "dev",
  "difficulty": "easy",
  "title": "Short descriptive title",
  "description": "Detailed description of what the task involves.",
  "natural_language_instruction": "What you would tell a human to do.",
  "preconditions": {
    "apps_required": ["notepad.exe"]
  },
  "success_criteria": [
    { "type": "file_exists", "path": "%USERPROFILE%\\Desktop\\output.txt" }
  ],
  "max_steps": 20,
  "timeout_seconds": 120
}
```

## Task ID Rules

- Lowercase alphanumeric with underscores only: `[a-z0-9_]+`
- Format: `{app}_{number}` e.g., `notepad_001`, `explorer_015`
- Must be unique across the entire corpus

## Success Criterion Types

| Type | Required Fields | Description |
|------|----------------|-------------|
| `file_exists` | `path` | File or directory exists |
| `file_content_matches` | `path`, `expected` | File contains expected text |
| `file_content_regex` | `path`, `pattern` | File matches regex pattern |
| `app_launched` | `process` | Process is running |
| `window_exists` | `window_title` | Window with title pattern exists |
| `clipboard_content` | `expected` | Clipboard contains text |

## Difficulty Levels

- **easy**: Single action or simple sequence (5-10 steps)
- **medium**: Multi-step with some decision-making (10-25 steps)
- **hard**: Complex workflows, multi-app, error handling (25+ steps)

## Chaos Compatibility

Specify which chaos types are safe to inject during this task:

```json
"chaos_compatibility": ["popup", "focus_steal", "delay", "resize", "uac", "notification", "scroll_hide"]
```

Omit types that would make the task impossible (e.g., don't use `uac` if the task requires clicking a specific button that the UAC overlay would block).

## Environment Variables

Use `%USERPROFILE%`, `%TEMP%`, `%APPDATA%` etc. in paths — they're expanded at evaluation time.

## Validation

Always validate new tasks:

```bash
python bench.py validate --tasks-dir tasks/
```
