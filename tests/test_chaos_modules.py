"""Tests for chaos modules."""

from __future__ import annotations

import pytest

from src.chaos.interface import ChaosModule, ChaosContext
from src.chaos.injector import ChaosEvent, ChaosInjector
from src.chaos.scheduler import ChaosScheduler
from src.chaos.registry import ChaosModuleRegistry
from src.chaos.profiles import profile_summary, is_clean_profile, count_enabled_modules
from src.core.config import ChaosProfileConfig


class TestChaosModuleRegistry:
    """Tests for the chaos module registry."""

    def test_register_and_get(self):
        registry = ChaosModuleRegistry()

        class FakeModule(ChaosModule):
            def name(self): return "fake"
            def inject(self, ctx): return ChaosEvent("fake", "test", 0.0)
            def cleanup(self): pass
            def is_safe(self): return True

        registry.register("fake", FakeModule)
        assert registry.get("fake") is FakeModule

    def test_get_unknown_returns_none(self):
        registry = ChaosModuleRegistry()
        assert registry.get("nonexistent") is None


class TestChaosScheduler:
    """Tests for the chaos scheduler."""

    def test_start_stop(self):
        scheduler = ChaosScheduler(seed=42)
        scheduler.start()
        assert scheduler._running
        scheduler.stop()
        assert not scheduler._running

    def test_random_delay(self):
        scheduler = ChaosScheduler(seed=42)
        delay = scheduler._random_delay((10.0, 20.0))
        assert 5.0 < delay < 30.0  # within range + jitter


class TestChaosProfiles:
    """Tests for chaos profile utilities."""

    def test_clean_profile(self):
        profile = ChaosProfileConfig(profile_name="clean")
        assert is_clean_profile(profile)
        assert count_enabled_modules(profile) == 0

    def test_profile_summary(self):
        profile = ChaosProfileConfig(profile_name="test")
        summary = profile_summary(profile)
        assert all(v is False for v in summary.values())
        assert "popup_spawner" in summary

    def test_enabled_modules(self):
        profile = ChaosProfileConfig(profile_name="test")
        profile.popup_spawner.enabled = True
        profile.focus_stealer.enabled = True
        assert count_enabled_modules(profile) == 2
        assert not is_clean_profile(profile)


class TestChaosInjector:
    """Tests for the central chaos injector."""

    def test_configure_clean_profile(self):
        injector = ChaosInjector()
        profile = ChaosProfileConfig(profile_name="clean")
        injector.configure(profile)
        assert len(injector._active_modules) == 0

    def test_event_log_empty_initially(self):
        injector = ChaosInjector()
        assert injector.get_event_log() == []

    def test_is_not_running_initially(self):
        injector = ChaosInjector()
        assert not injector.is_running
