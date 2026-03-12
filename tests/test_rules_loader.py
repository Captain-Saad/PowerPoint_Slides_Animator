"""
tests/test_rules_loader.py
Unit tests for engine/rules_loader.py.

Status: STUB — M6 implementation pending.
"""

from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path
from typing import Generator

import pytest

from engine.rules_loader import RulesConfig, load_rules


class TestLoadRulesFromValidYaml:
    """Tests for loading a well-formed rules.yaml file."""

    def test_returns_rules_config_instance(self, tmp_rules_dir):
        """load_rules() returns a RulesConfig dataclass."""
        ...

    def test_profile_defaults_to_balanced(self, tmp_rules_dir):
        """When no profile is specified, the profile defaults to 'balanced'."""
        ...

    def test_profile_override_takes_precedence(self, tmp_rules_dir):
        """CLI --profile argument overrides the profile key in rules.yaml."""
        ...

    def test_timing_values_loaded_correctly(self, tmp_rules_dir):
        """All timing fields are parsed and stored correctly."""
        ...

    def test_caps_values_loaded_correctly(self, tmp_rules_dir):
        """All caps fields are parsed and stored correctly."""
        ...

    def test_allowed_animations_loaded(self, tmp_rules_dir):
        """The 'allowed' list is populated from rules.yaml."""
        ...

    def test_forbidden_animations_loaded(self, tmp_rules_dir):
        """The 'forbidden' list is populated and always includes engine defaults."""
        ...

    def test_elements_dict_contains_title(self, tmp_rules_dir):
        """The elements dict contains at least a 'title' key."""
        ...

    def test_output_suffix_loaded(self, tmp_rules_dir):
        """output.suffix is loaded from rules.yaml."""
        ...


class TestLoadRulesMissingFile:
    """Tests for graceful fallback when rules.yaml is absent."""

    def test_missing_rules_does_not_crash(self, tmp_path):
        """load_rules() with no rules.yaml logs a warning and returns defaults."""
        ...

    def test_missing_rules_returns_balanced_defaults(self, tmp_path):
        """Fallback config uses balanced profile defaults."""
        ...


class TestLoadRulesInvalidYaml:
    """Tests for invalid YAML content handling."""

    def test_invalid_yaml_exits_with_message(self, tmp_path):
        """rules.yaml with invalid syntax causes SystemExit with a clear message."""
        ...

    def test_invalid_yaml_mentions_file_path(self, tmp_path):
        """The SystemExit message includes the path to the bad file."""
        ...


class TestProfileMerge:
    """Tests for profile YAML loading and deep-merge logic."""

    def test_profile_file_values_are_lower_priority(self, tmp_rules_dir):
        """Values in rules.yaml override conflicting profile YAML values."""
        ...

    def test_missing_profile_file_logs_warning(self, tmp_rules_dir, caplog):
        """A missing profile YAML logs a warning but does not crash."""
        ...


class TestOverrides:
    """Tests for per-slide override loading from overrides.yaml."""

    def test_overrides_loaded_as_int_keys(self, tmp_rules_dir):
        """Slide numbers in overrides.yaml are stored as integer keys."""
        ...

    def test_missing_overrides_file_returns_empty_dict(self, tmp_rules_dir):
        """Absent overrides.yaml results in an empty overrides dict."""
        ...


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_rules_dir(tmp_path) -> Path:
    """Create a temp directory with a minimal .antigravity/rules.yaml.

    Returns the project root (tmp_path) so tests can call load_rules()
    with project_root=str(tmp_path).
    """
    ...
