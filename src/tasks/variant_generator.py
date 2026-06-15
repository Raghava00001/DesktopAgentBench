"""
Variant generator for DesktopAgentBench.

For each task, generates multiple chaos variants: a clean baseline plus
isolated single-module variants and combined profile variants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config import ChaosProfileConfig, ChaosModuleName, load_chaos_profile
from src.tasks.schema import Task, ChaosType


# Mapping from task chaos types to chaos module names
_CHAOS_TYPE_TO_MODULE: dict[ChaosType, ChaosModuleName] = {
    ChaosType.POPUP: ChaosModuleName.POPUP_SPAWNER,
    ChaosType.FOCUS_STEAL: ChaosModuleName.FOCUS_STEALER,
    ChaosType.DELAY: ChaosModuleName.UI_DELAY,
    ChaosType.RESIZE: ChaosModuleName.WINDOW_RESIZER,
    ChaosType.UAC: ChaosModuleName.UAC_FAKER,
    ChaosType.NOTIFICATION: ChaosModuleName.NOTIFICATION_SPOOFER,
    ChaosType.SCROLL_HIDE: ChaosModuleName.SCROLL_HIDER,
}


@dataclass
class TaskVariant:
    """A specific variant of a task with an associated chaos profile."""
    task: Task
    variant_name: str
    chaos_profile: ChaosProfileConfig
    is_baseline: bool = False


def _make_clean_profile() -> ChaosProfileConfig:
    """Create a clean (no chaos) profile."""
    return ChaosProfileConfig(
        profile_name="clean",
        description="No chaos injection — clean baseline",
    )


def _make_isolated_profile(
    chaos_type: ChaosType,
    base_profile: ChaosProfileConfig | None = None,
) -> ChaosProfileConfig:
    """
    Create a profile with only a single chaos module enabled.

    Uses moderate settings from the base profile if provided,
    otherwise uses sensible defaults.
    """
    module_name = _CHAOS_TYPE_TO_MODULE[chaos_type]

    # Start from a clean profile
    profile = _make_clean_profile()
    profile.profile_name = chaos_type.value
    profile.description = f"Isolated {chaos_type.value} disruption"

    # Enable just the one module
    if base_profile:
        module_config = base_profile.get_module_config(module_name).model_copy()
    else:
        module_config = profile.get_module_config(module_name).model_copy()

    module_config.enabled = True
    setattr(profile, module_name.value, module_config)

    return profile


class VariantGenerator:
    """
    Generates task variants by combining tasks with chaos profiles.
    """

    def __init__(
        self,
        profiles_dir: Path | None = None,
        combined_profiles: list[ChaosProfileConfig] | None = None,
        generate_isolated: bool = True,
    ) -> None:
        self._profiles_dir = profiles_dir
        self._combined_profiles = combined_profiles or []
        self._generate_isolated = generate_isolated

    def generate(self, task: Task) -> list[TaskVariant]:
        """
        Generate all variants for a single task.

        Returns:
            - 1 clean baseline variant
            - N isolated variants (one per compatible chaos type)
            - M combined profile variants
        """
        variants: list[TaskVariant] = []

        # 1. Clean baseline — always included
        variants.append(TaskVariant(
            task=task,
            variant_name="clean",
            chaos_profile=_make_clean_profile(),
            is_baseline=True,
        ))

        # 2. Isolated variants — one per compatible chaos type
        if self._generate_isolated:
            for chaos_type in task.chaos_compatibility:
                # Use moderate profile as base for isolated settings if available
                base = next(
                    (p for p in self._combined_profiles if "moderate" in p.profile_name),
                    None,
                )
                profile = _make_isolated_profile(chaos_type, base)
                variants.append(TaskVariant(
                    task=task,
                    variant_name=chaos_type.value,
                    chaos_profile=profile,
                ))

        # 3. Combined profiles (moderate, severe, etc.)
        for combined in self._combined_profiles:
            # Filter profile to only enable modules the task is compatible with
            filtered = self._filter_profile(combined, task)
            variants.append(TaskVariant(
                task=task,
                variant_name=combined.profile_name,
                chaos_profile=filtered,
            ))

        return variants

    def generate_for_tasks(self, tasks: list[Task]) -> list[TaskVariant]:
        """Generate variants for all tasks."""
        variants: list[TaskVariant] = []
        for task in tasks:
            variants.extend(self.generate(task))
        return variants

    @staticmethod
    def _filter_profile(
        profile: ChaosProfileConfig,
        task: Task,
    ) -> ChaosProfileConfig:
        """
        Create a copy of the profile with incompatible modules disabled.
        """
        compatible_modules = {
            _CHAOS_TYPE_TO_MODULE[ct] for ct in task.chaos_compatibility
        }

        filtered = profile.model_copy(deep=True)
        for module_name in ChaosModuleName:
            if module_name not in compatible_modules:
                config = filtered.get_module_config(module_name)
                config.enabled = False

        return filtered
