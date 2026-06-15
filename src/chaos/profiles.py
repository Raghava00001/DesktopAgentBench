"""
Chaos profile configuration helpers for DesktopAgentBench.

Provides utility functions for working with chaos profiles,
including profile merging, validation, and summary generation.
"""

from __future__ import annotations

from src.core.config import ChaosProfileConfig, ChaosModuleName


def profile_summary(profile: ChaosProfileConfig) -> dict[str, bool]:
    """Return a dict of module_name -> enabled for quick inspection."""
    return {
        name.value: profile.get_module_config(name).enabled
        for name in ChaosModuleName
    }


def count_enabled_modules(profile: ChaosProfileConfig) -> int:
    """Return the number of enabled chaos modules."""
    return len(profile.get_enabled_modules())


def is_clean_profile(profile: ChaosProfileConfig) -> bool:
    """Check if a profile has no chaos modules enabled."""
    return count_enabled_modules(profile) == 0


def merge_profiles(
    base: ChaosProfileConfig,
    overlay: ChaosProfileConfig,
) -> ChaosProfileConfig:
    """
    Merge two profiles: overlay's enabled modules override base.

    Useful for creating custom profiles from a base template.
    """
    merged = base.model_copy(deep=True)
    merged.profile_name = overlay.profile_name
    merged.description = overlay.description

    for name in ChaosModuleName:
        overlay_config = overlay.get_module_config(name)
        if overlay_config.enabled:
            setattr(merged, name.value, overlay_config.model_copy())

    if overlay.randomization.seed is not None:
        merged.randomization = overlay.randomization.model_copy()

    return merged
