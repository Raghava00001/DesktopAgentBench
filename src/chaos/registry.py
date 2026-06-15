"""
Chaos module registry for DesktopAgentBench.

Provides auto-discovery and registration of chaos modules, supporting
both built-in modules and custom third-party modules.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.chaos.injector import ChaosModule

logger = logging.getLogger(__name__)

# Built-in module mapping
_BUILTIN_MODULES: dict[str, str] = {
    "popup_spawner": "src.chaos.modules.popup_spawner:PopupSpawner",
    "focus_stealer": "src.chaos.modules.focus_stealer:FocusStealer",
    "ui_delay": "src.chaos.modules.ui_delay:UIDelay",
    "window_resizer": "src.chaos.modules.window_resizer:WindowResizer",
    "uac_faker": "src.chaos.modules.uac_faker:UACFaker",
    "notification_spoofer": "src.chaos.modules.notification_spoofer:NotificationSpoofer",
    "scroll_hider": "src.chaos.modules.scroll_hider:ScrollHider",
}


class ChaosModuleRegistry:
    """
    Registry for chaos injection modules.

    Modules are discovered from:
    1. Built-in modules in src/chaos/modules/
    2. Entry points under 'desktopagentbench.chaos'
    3. Explicit registration via register()
    """

    def __init__(self) -> None:
        self._modules: dict[str, type["ChaosModule"]] = {}

    def register(self, name: str, module_class: type["ChaosModule"]) -> None:
        """Register a chaos module class by name."""
        self._modules[name] = module_class
        logger.debug(f"Registered chaos module: {name}")

    def get(self, name: str) -> type["ChaosModule"] | None:
        """Get a registered module class by name."""
        if name not in self._modules:
            # Try lazy loading from builtins
            self._try_load_builtin(name)
        return self._modules.get(name)

    def get_all(self) -> dict[str, type["ChaosModule"]]:
        """Return all registered modules."""
        return dict(self._modules)

    def discover_builtins(self) -> None:
        """Load all built-in chaos modules."""
        for name in _BUILTIN_MODULES:
            self._try_load_builtin(name)

    def _try_load_builtin(self, name: str) -> None:
        """Attempt to load a built-in module by name."""
        if name in self._modules:
            return

        spec = _BUILTIN_MODULES.get(name)
        if not spec:
            return

        try:
            module_path, class_name = spec.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            self._modules[name] = cls
            logger.debug(f"Loaded built-in chaos module: {name}")
        except Exception as e:
            logger.warning(f"Failed to load chaos module '{name}': {e}")

    def discover_entry_points(self) -> None:
        """Discover chaos modules via setuptools entry points."""
        try:
            from importlib.metadata import entry_points
            eps = entry_points()
            chaos_eps = eps.get("desktopagentbench.chaos", [])
            for ep in chaos_eps:
                try:
                    cls = ep.load()
                    self.register(ep.name, cls)
                except Exception as e:
                    logger.warning(f"Failed to load chaos entry point '{ep.name}': {e}")
        except Exception:
            pass


# Global registry instance
_global_registry = ChaosModuleRegistry()


def get_registry() -> ChaosModuleRegistry:
    """Return the global chaos module registry."""
    return _global_registry
