"""
Configuration loading and validation for DesktopAgentBench.

Provides Pydantic models for the full benchmark configuration, including
chaos profiles, environment settings, and run parameters.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SplitType(str, Enum):
    DEV = "dev"
    HELD_OUT = "held_out"
    ALL = "all"


class ChaosModuleName(str, Enum):
    POPUP_SPAWNER = "popup_spawner"
    FOCUS_STEALER = "focus_stealer"
    UI_DELAY = "ui_delay"
    WINDOW_RESIZER = "window_resizer"
    UAC_FAKER = "uac_faker"
    NOTIFICATION_SPOOFER = "notification_spoofer"
    SCROLL_HIDER = "scroll_hider"


class ResizeMagnitude(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# ---------------------------------------------------------------------------
# Chaos module configs
# ---------------------------------------------------------------------------

class ChaosModuleConfig(BaseModel):
    """Base configuration shared by all chaos modules."""
    enabled: bool = False
    frequency_range: tuple[float, float] = (30.0, 60.0)

    @field_validator("frequency_range")
    @classmethod
    def validate_frequency_range(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError("Frequency range values must be positive")
        if v[0] > v[1]:
            raise ValueError("frequency_range[0] must be <= frequency_range[1]")
        return v


class PopupSpawnerConfig(ChaosModuleConfig):
    duration_range: tuple[float, float] = (3.0, 10.0)
    popup_types: list[str] = Field(default_factory=lambda: ["update", "sync", "notification"])
    max_concurrent: int = Field(default=2, ge=1, le=10)


class FocusStealerConfig(ChaosModuleConfig):
    steal_duration_range: tuple[float, float] = (1.0, 3.0)


class UIDelayConfig(ChaosModuleConfig):
    delay_range_ms: tuple[int, int] = (500, 2000)
    probability: float = Field(default=0.3, ge=0.0, le=1.0)


class WindowResizerConfig(ChaosModuleConfig):
    resize_magnitude: ResizeMagnitude = ResizeMagnitude.MEDIUM


class UACFakerConfig(ChaosModuleConfig):
    dim_background: bool = True
    require_interaction: bool = True


class NotificationSpooferConfig(ChaosModuleConfig):
    notification_types: list[str] = Field(
        default_factory=lambda: ["email", "chat", "calendar"]
    )


class ScrollHiderConfig(ChaosModuleConfig):
    hide_vertical: bool = True
    hide_horizontal: bool = False


# ---------------------------------------------------------------------------
# Chaos profile
# ---------------------------------------------------------------------------

class ChaosRandomizationConfig(BaseModel):
    seed: int | None = None
    injection_jitter_pct: float = Field(default=20.0, ge=0.0, le=100.0)


class ChaosProfileConfig(BaseModel):
    """Full chaos profile combining all module configs."""
    profile_name: str = "clean"
    description: str = ""

    popup_spawner: PopupSpawnerConfig = Field(default_factory=PopupSpawnerConfig)
    focus_stealer: FocusStealerConfig = Field(default_factory=FocusStealerConfig)
    ui_delay: UIDelayConfig = Field(default_factory=UIDelayConfig)
    window_resizer: WindowResizerConfig = Field(default_factory=WindowResizerConfig)
    uac_faker: UACFakerConfig = Field(default_factory=UACFakerConfig)
    notification_spoofer: NotificationSpooferConfig = Field(
        default_factory=NotificationSpooferConfig
    )
    scroll_hider: ScrollHiderConfig = Field(default_factory=ScrollHiderConfig)

    randomization: ChaosRandomizationConfig = Field(
        default_factory=ChaosRandomizationConfig
    )

    def get_module_config(self, name: ChaosModuleName) -> ChaosModuleConfig:
        """Return the config for a specific chaos module by name."""
        return getattr(self, name.value)

    def get_enabled_modules(self) -> list[ChaosModuleName]:
        """Return list of enabled module names."""
        return [
            name for name in ChaosModuleName
            if self.get_module_config(name).enabled
        ]


# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------

class EnvironmentConfig(BaseModel):
    """Windows environment configuration."""
    use_vm: bool = False
    vm_provider: str = "hyperv"  # hyperv | virtualbox
    snapshot_name: str = "clean_baseline"
    screen_resolution: tuple[int, int] = (1920, 1080)
    dpi_scale: float = 1.0


# ---------------------------------------------------------------------------
# Top-level benchmark config
# ---------------------------------------------------------------------------

class BenchmarkConfig(BaseModel):
    """Top-level configuration for a benchmark run."""
    # Run parameters
    split: SplitType = SplitType.DEV
    task_filter: list[str] | None = None  # specific task IDs, or None for all
    category_filter: list[str] | None = None  # specific categories
    repetitions: int = Field(default=5, ge=1, le=100)
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.999)

    # Chaos
    chaos_profiles: list[str] = Field(
        default_factory=lambda: ["clean", "moderate"]
    )
    generate_isolated_variants: bool = True  # auto-generate per-module variants

    # Paths
    tasks_dir: Path = Path("tasks")
    results_dir: Path = Path("results")
    chaos_profiles_dir: Path = Path("configs/chaos_profiles")

    # Agent
    agent: str = "builtin:noop"

    # Environment
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)

    # Timeouts
    global_timeout_minutes: int = Field(default=240, ge=1)

    @field_validator("tasks_dir", "results_dir", "chaos_profiles_dir")
    @classmethod
    def resolve_path(cls, v: Path) -> Path:
        return v.resolve() if not v.is_absolute() else v


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> BenchmarkConfig:
    """Load a BenchmarkConfig from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return BenchmarkConfig(**raw)


def load_chaos_profile(path: str | Path) -> ChaosProfileConfig:
    """Load a ChaosProfileConfig from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Chaos profile not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return ChaosProfileConfig(**raw)


def load_chaos_profiles_from_dir(
    profiles_dir: Path,
    profile_names: list[str],
) -> dict[str, ChaosProfileConfig]:
    """Load multiple chaos profiles by name from a directory."""
    profiles: dict[str, ChaosProfileConfig] = {}
    for name in profile_names:
        profile_path = profiles_dir / f"{name}.yaml"
        profiles[name] = load_chaos_profile(profile_path)
    return profiles
