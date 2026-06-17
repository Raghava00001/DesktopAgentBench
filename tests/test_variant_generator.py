"""Tests for the variant generator."""

from __future__ import annotations

import pytest

from src.core.config import ChaosProfileConfig, ChaosModuleName
from src.tasks.schema import Task, SuccessCriterion, ChaosType
from src.tasks.variant_generator import (
    VariantGenerator,
    TaskVariant,
    _make_clean_profile,
    _make_isolated_profile,
)


def _make_task(**overrides) -> Task:
    defaults = dict(
        task_id="test_001",
        category="text_editor",
        app="notepad",
        title="Test",
        description="Test",
        natural_language_instruction="Do something.",
        success_criteria=[
            SuccessCriterion(type="file_exists", path="C:\\test.txt")
        ],
        chaos_compatibility=[
            ChaosType.POPUP,
            ChaosType.FOCUS_STEAL,
            ChaosType.DELAY,
        ],
    )
    defaults.update(overrides)
    return Task(**defaults)


class TestCleanProfile:
    """Tests for _make_clean_profile."""

    def test_clean_profile_name(self):
        profile = _make_clean_profile()
        assert profile.profile_name == "clean"

    def test_clean_profile_no_modules_enabled(self):
        profile = _make_clean_profile()
        assert len(profile.get_enabled_modules()) == 0


class TestIsolatedProfile:
    """Tests for _make_isolated_profile."""

    def test_isolated_popup_enables_only_popup(self):
        profile = _make_isolated_profile(ChaosType.POPUP)
        enabled = profile.get_enabled_modules()
        assert len(enabled) == 1
        assert enabled[0] == ChaosModuleName.POPUP_SPAWNER

    def test_isolated_focus_enables_only_focus(self):
        profile = _make_isolated_profile(ChaosType.FOCUS_STEAL)
        enabled = profile.get_enabled_modules()
        assert len(enabled) == 1
        assert enabled[0] == ChaosModuleName.FOCUS_STEALER

    def test_isolated_profile_name_matches_chaos_type(self):
        profile = _make_isolated_profile(ChaosType.DELAY)
        assert profile.profile_name == "delay"

    def test_isolated_with_base_profile_inherits_settings(self):
        base = ChaosProfileConfig(profile_name="moderate")
        base.popup_spawner.enabled = True
        base.popup_spawner.max_concurrent = 5
        profile = _make_isolated_profile(ChaosType.POPUP, base)
        assert profile.popup_spawner.max_concurrent == 5
        assert profile.popup_spawner.enabled is True


class TestVariantGenerator:
    """Tests for VariantGenerator.generate()."""

    def test_generates_clean_baseline(self):
        gen = VariantGenerator(generate_isolated=False)
        task = _make_task()
        variants = gen.generate(task)
        assert any(v.variant_name == "clean" for v in variants)
        clean = [v for v in variants if v.variant_name == "clean"][0]
        assert clean.is_baseline is True

    def test_generates_isolated_variants(self):
        gen = VariantGenerator(generate_isolated=True)
        task = _make_task(
            chaos_compatibility=[ChaosType.POPUP, ChaosType.FOCUS_STEAL, ChaosType.DELAY]
        )
        variants = gen.generate(task)
        variant_names = {v.variant_name for v in variants}
        # Should have clean + 3 isolated
        assert "clean" in variant_names
        assert "popup" in variant_names
        assert "focus_steal" in variant_names
        assert "delay" in variant_names

    def test_no_isolated_when_disabled(self):
        gen = VariantGenerator(generate_isolated=False)
        task = _make_task(
            chaos_compatibility=[ChaosType.POPUP, ChaosType.FOCUS_STEAL]
        )
        variants = gen.generate(task)
        # Only clean, no isolated
        assert len(variants) == 1
        assert variants[0].variant_name == "clean"

    def test_includes_combined_profiles(self):
        moderate = ChaosProfileConfig(profile_name="moderate")
        moderate.popup_spawner.enabled = True
        moderate.focus_stealer.enabled = True

        gen = VariantGenerator(
            combined_profiles=[moderate],
            generate_isolated=False,
        )
        task = _make_task()
        variants = gen.generate(task)
        variant_names = {v.variant_name for v in variants}
        assert "clean" in variant_names
        assert "moderate" in variant_names

    def test_combined_profile_filters_incompatible_modules(self):
        """If a task doesn't support 'resize', the moderate profile should disable it."""
        moderate = ChaosProfileConfig(profile_name="moderate")
        moderate.popup_spawner.enabled = True
        moderate.window_resizer.enabled = True

        gen = VariantGenerator(
            combined_profiles=[moderate],
            generate_isolated=False,
        )
        # Task only supports popup and focus_steal, NOT resize
        task = _make_task(
            chaos_compatibility=[ChaosType.POPUP, ChaosType.FOCUS_STEAL]
        )
        variants = gen.generate(task)
        mod_variant = [v for v in variants if v.variant_name == "moderate"][0]
        # window_resizer should be disabled in the filtered profile
        assert mod_variant.chaos_profile.window_resizer.enabled is False
        # popup should remain enabled
        assert mod_variant.chaos_profile.popup_spawner.enabled is True

    def test_generate_for_tasks(self):
        gen = VariantGenerator(generate_isolated=False)
        tasks = [
            _make_task(task_id="t1"),
            _make_task(task_id="t2"),
        ]
        all_variants = gen.generate_for_tasks(tasks)
        assert len(all_variants) == 2  # 1 clean each
        task_ids = {v.task.task_id for v in all_variants}
        assert task_ids == {"t1", "t2"}

    def test_total_variant_count(self):
        """3 chaos types + clean = 4 variants."""
        gen = VariantGenerator(generate_isolated=True)
        task = _make_task(
            chaos_compatibility=[ChaosType.POPUP, ChaosType.FOCUS_STEAL, ChaosType.DELAY]
        )
        variants = gen.generate(task)
        assert len(variants) == 4  # 1 clean + 3 isolated
