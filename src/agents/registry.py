"""
Agent registry — discovery and loading of agent adapters.

Supports three discovery mechanisms:
1. Directory scanning: agents/{name}/adapter.py
2. Entry points: [project.entry-points."desktopagentbench.agents"]
3. CLI specification: --agent module.path:ClassName
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.adapter import AgentAdapter

logger = logging.getLogger(__name__)

# Built-in agents
_BUILTIN_AGENTS: dict[str, str] = {
    "noop": "src.agents.builtin.noop_agent:NoopAgent",
    "random": "src.agents.builtin.random_agent:RandomAgent",
    "rule": "src.agents.builtin.rule_agent:RuleAgent",
}


class AgentRegistry:
    """Registry for agent adapter classes."""

    def __init__(self) -> None:
        self._agents: dict[str, type["AgentAdapter"]] = {}

    def register(self, name: str, agent_class: type["AgentAdapter"]) -> None:
        """Register an agent adapter class by name."""
        self._agents[name] = agent_class
        logger.debug(f"Registered agent: {name}")

    def get(self, name: str) -> type["AgentAdapter"] | None:
        """Get an agent class by name, with lazy loading."""
        if name not in self._agents:
            self._try_load(name)
        return self._agents.get(name)

    def get_all(self) -> dict[str, type["AgentAdapter"]]:
        """Return all registered agents."""
        return dict(self._agents)

    def load_from_spec(self, spec: str) -> type["AgentAdapter"]:
        """
        Load an agent from a specification string.

        Formats:
        - "builtin:noop"         — built-in agent
        - "module.path:Class"    — explicit module:class
        - "agent_name"           — lookup in registry
        """
        if spec.startswith("builtin:"):
            name = spec.split(":", 1)[1]
            cls = self.get(name)
            if cls is None:
                raise ValueError(f"Built-in agent not found: {name}")
            return cls

        if ":" in spec:
            module_path, class_name = spec.rsplit(":", 1)
            try:
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                self.register(class_name.lower(), cls)
                return cls
            except Exception as e:
                raise ValueError(f"Failed to load agent from '{spec}': {e}")

        cls = self.get(spec)
        if cls is None:
            raise ValueError(f"Agent not found: {spec}")
        return cls

    def discover_builtins(self) -> None:
        """Load all built-in agents."""
        for name in _BUILTIN_AGENTS:
            self._try_load(name)

    def discover_directory(self, agents_dir: Path) -> None:
        """Discover agents from the agents/ directory."""
        if not agents_dir.exists():
            return

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue

            adapter_path = agent_dir / "adapter.py"
            if adapter_path.exists():
                try:
                    # Import the module
                    module_name = f"agents.{agent_dir.name}.adapter"
                    module = importlib.import_module(module_name)

                    # Find AgentAdapter subclasses
                    from src.agents.adapter import AgentAdapter
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, AgentAdapter)
                            and attr is not AgentAdapter
                        ):
                            self.register(agent_dir.name, attr)
                            logger.info(f"Discovered agent: {agent_dir.name} -> {attr_name}")
                            break

                except Exception as e:
                    logger.warning(f"Failed to load agent from {agent_dir}: {e}")

    def discover_entry_points(self) -> None:
        """Discover agents via setuptools entry points."""
        try:
            from importlib.metadata import entry_points
            eps = entry_points()
            agent_eps = eps.get("desktopagentbench.agents", [])
            for ep in agent_eps:
                try:
                    cls = ep.load()
                    self.register(ep.name, cls)
                    logger.info(f"Loaded agent entry point: {ep.name}")
                except Exception as e:
                    logger.warning(f"Failed to load agent entry point '{ep.name}': {e}")
        except Exception:
            pass

    def _try_load(self, name: str) -> None:
        """Attempt to load a built-in or registered agent."""
        if name in self._agents:
            return

        spec = _BUILTIN_AGENTS.get(name)
        if not spec:
            return

        try:
            module_path, class_name = spec.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            self._agents[name] = cls
        except Exception as e:
            logger.warning(f"Failed to load agent '{name}': {e}")


# Global registry instance
_global_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Return the global agent registry."""
    return _global_registry
