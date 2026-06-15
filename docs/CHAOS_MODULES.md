# Chaos Modules Guide

How the chaos injection system works and how to write new modules.

## Architecture

The chaos engine uses a plugin-based architecture:

1. **ChaosInjector** — Central controller that manages modules and scheduling
2. **ChaosScheduler** — Randomized timing engine (Poisson-inspired)
3. **ChaosModule** (ABC) — Interface that each disruption type implements
4. **ChaosModuleRegistry** — Auto-discovery and registration

## Built-in Modules

| Module | Class | Effect | Win32 Mechanism |
|--------|-------|--------|-----------------|
| popup_spawner | `PopupSpawner` | Fake system dialogs | `MessageBoxTimeoutW` |
| focus_stealer | `FocusStealer` | Steal window focus | `SetForegroundWindow`, `FlashWindowEx` |
| ui_delay | `UIDelay` | Freeze UI rendering | `WM_SETREDRAW` |
| window_resizer | `WindowResizer` | Resize/reposition windows | `MoveWindow`, `SetWindowPos` |
| uac_faker | `UACFaker` | Fake UAC consent dialog | Styled `MessageBox` + overlay |
| notification_spoofer | `NotificationSpoofer` | Toast notifications | PowerShell WinRT / fallback popup |
| scroll_hider | `ScrollHider` | Hide scrollbars | `ShowScrollBar` |

## Writing a New Module

```python
from src.chaos.injector import ChaosModule, ChaosContext, ChaosEvent

class MyModule(ChaosModule):
    def name(self) -> str:
        return "my_module"

    def configure(self, params: dict) -> None:
        self._intensity = params.get("intensity", 0.5)

    def inject(self, context: ChaosContext) -> ChaosEvent:
        # Do your disruption here
        # context.target_window_hwnd has the target window
        return ChaosEvent(
            module_name=self.name(),
            event_type="injected",
            timestamp=time.time(),
            cleanup_required=True,
        )

    def cleanup(self) -> None:
        # Reverse everything you did in inject()
        pass

    def is_safe(self) -> bool:
        # Return True ONLY if your module cannot cause permanent damage
        return True
```

## Safety Contract

Every module MUST:

1. **Not modify system state** — No registry writes, system file changes, or service modifications
2. **Be fully reversible** — `cleanup()` must restore the exact pre-injection state
3. **Own its resources** — Only manipulate windows/processes created by the benchmark
4. **Pass safety check** — `is_safe()` must verify the module's constraints
5. **Tag visibly** — Prefix window titles with `[DAB]` for transparency
6. **Log everything** — Return a `ChaosEvent` with full details

## Registering a Custom Module

### Via Entry Points

```toml
[project.entry-points."desktopagentbench.chaos"]
my_module = "my_package.chaos:MyModule"
```

### Via Registry

```python
from src.chaos.registry import get_registry
get_registry().register("my_module", MyModule)
```

## Chaos Profiles

Modules are configured via YAML profiles in `configs/chaos_profiles/`:

```yaml
my_module:
  enabled: true
  frequency_range: [15, 45]
  intensity: 0.7
```

The `frequency_range` controls how often (in seconds) the module fires. The scheduler adds random jitter.
