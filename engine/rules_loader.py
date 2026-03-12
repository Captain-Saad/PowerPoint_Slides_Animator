"""
engine/rules_loader.py
Reads .antigravity/rules.yaml, merges the selected profile, validates
the schema, and returns a RulesConfig dataclass ready for use by the
rest of the engine.

Evaluation order (highest priority wins):
  1. overrides.yaml  (per-slide manual overrides)
  2. caps            (hard limits — always enforced)
  3. slide rules     (title_slide, content_slide, etc.)
  4. element rules   (title, body_text, image, etc.)
  5. profile yaml    (subtle / balanced / dynamic)  ← lowest priority
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANTIGRAVITY_DIR = ".antigravity"
RULES_FILE = "rules.yaml"
PROFILES_DIR = "profiles"
OVERRIDES_FILE = "overrides.yaml"

VALID_PROFILES = {"subtle", "balanced", "dynamic"}
VALID_START_ON = {"click", "after_previous", "with_previous"}

# Animations the engine will never use regardless of configuration
ALWAYS_FORBIDDEN = {
    "bounce", "spin", "zoom_in_crazy", "boomerang",
    "swivel", "pinwheel", "credits_roll",
}

# Default RulesConfig values — used when rules.yaml is absent
_DEFAULTS: Dict[str, Any] = {
    "profile": "balanced",
    "timing": {
        "default_duration_ms": 500,
        "delay_between_elements_ms": 150,
        "start_on": "after_previous",
        "title_starts_on": "after_previous",
        "body_starts_on": "after_previous",
    },
    "caps": {
        "max_animations_per_slide": 8,
        "max_animated_shapes_per_slide": 6,
        "skip_if_too_many_elements": 12,
        "no_animation_on_last_slide": False,
    },
    "output": {
        "suffix": "_animated",
        "overwrite_if_exists": False,
        "preserve_notes": True,
        "preserve_hyperlinks": True,
        "preserve_masters": True,
    },
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TimingConfig:
    """Global timing settings resolved from rules.yaml."""

    default_duration_ms: int = 500
    delay_between_elements_ms: int = 150
    start_on: str = "after_previous"
    title_starts_on: str = "after_previous"
    body_starts_on: str = "after_previous"


@dataclass
class CapsConfig:
    """Hard animation limits that the engine always enforces."""

    max_animations_per_slide: int = 8
    max_animated_shapes_per_slide: int = 6
    skip_if_too_many_elements: int = 12
    no_animation_on_last_slide: bool = False


@dataclass
class OutputConfig:
    """Output file behaviour settings."""

    suffix: str = "_animated"
    overwrite_if_exists: bool = False
    preserve_notes: bool = True
    preserve_hyperlinks: bool = True
    preserve_masters: bool = True


@dataclass
class RulesConfig:
    """Fully resolved configuration for the animation engine.

    This is the single object passed through the entire pipeline.  All
    rule resolution (profile merge, defaults, validation) has already
    happened before this object is created.

    Attributes:
        profile: Name of the active profile.
        timing: Resolved global timing settings.
        caps: Hard animation limits.
        elements: Per-element-type animation settings keyed by element name.
        slides: Per-slide-type settings keyed by slide type name.
        first_slide: First-slide override settings.
        allowed: Whitelist of permitted animation names.
        forbidden: Blacklist of banned animation names.
        overrides: Per-slide manual overrides dict (keyed by 1-based slide number).
        output: Output file settings.
    """

    profile: str = "balanced"
    timing: TimingConfig = field(default_factory=TimingConfig)
    caps: CapsConfig = field(default_factory=CapsConfig)
    elements: Dict[str, Any] = field(default_factory=dict)
    slides: Dict[str, Any] = field(default_factory=dict)
    first_slide: Dict[str, Any] = field(default_factory=dict)
    allowed: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)
    overrides: Dict[int, Any] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_rules_path(project_root: Optional[str] = None) -> Path:
    """Locate the rules.yaml file relative to the project root.

    Args:
        project_root: Optional explicit root directory.  If ``None``, the
            current working directory is used.

    Returns:
        Path to rules.yaml (may not exist — caller handles that case).
    """
    root = Path(project_root) if project_root else Path.cwd()
    return root / ANTIGRAVITY_DIR / RULES_FILE


def _load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a YAML file, returning ``None`` if not found.

    Args:
        path: Absolute or relative path to the YAML file.

    Returns:
        Parsed dict, or ``None`` if the file does not exist.

    Raises:
        SystemExit: If the file exists but contains invalid YAML syntax.
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        _exit_invalid_yaml(path, exc)


def _exit_invalid_yaml(path: Path, exc: yaml.YAMLError) -> None:
    """Print a clear error message and exit for invalid YAML.

    Args:
        path: Path to the file with bad syntax.
        exc: The YAML exception containing line/column information.
    """
    mark = getattr(exc, "problem_mark", None)
    line = mark.line + 1 if mark else "?"
    raise SystemExit(
        f"Error: {path} has invalid YAML syntax at line {line}.\n"
        f"Details: {exc}"
    )


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge *override* into *base*, returning a new dict.

    Values in *override* take priority.  Nested dicts are merged
    recursively; all other types are replaced wholesale.

    Args:
        base: The lower-priority dictionary.
        override: The higher-priority dictionary.

    Returns:
        A new merged dictionary.
    """
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_profile(profile_name: str, project_root: Optional[str] = None) -> Dict[str, Any]:
    """Load a named profile YAML file from the profiles directory.

    Args:
        profile_name: One of ``"subtle"``, ``"balanced"``, or ``"dynamic"``.
        project_root: Optional project root directory.

    Returns:
        Parsed profile dict, or empty dict if the file is missing.
    """
    root = Path(project_root) if project_root else Path.cwd()
    profile_path = root / ANTIGRAVITY_DIR / PROFILES_DIR / f"{profile_name}.yaml"
    data = _load_yaml_file(profile_path)
    if data is None:
        logger.warning("Profile file not found: %s — using rule defaults.", profile_path)
        return {}
    return data


def _load_overrides(project_root: Optional[str] = None) -> Dict[int, Any]:
    """Load per-slide overrides from overrides.yaml.

    Args:
        project_root: Optional project root directory.

    Returns:
        Dict keyed by 1-based slide number.  Empty if file is absent.
    """
    root = Path(project_root) if project_root else Path.cwd()
    overrides_path = root / ANTIGRAVITY_DIR / OVERRIDES_FILE
    data = _load_yaml_file(overrides_path)
    if not data:
        return {}
    raw_slides = data.get("slides", {}) or {}
    return {int(k): v for k, v in raw_slides.items() if v is not None}


def _validate_and_warn(data: Dict[str, Any]) -> None:
    """Validate required keys and warn (not crash) on unknown/invalid values.

    Args:
        data: The merged rules dictionary to validate.
    """
    profile = data.get("profile", "balanced")
    if profile not in VALID_PROFILES:
        logger.warning(
            "Unknown profile '%s' in rules.yaml. Valid options: %s. "
            "Falling back to 'balanced'.",
            profile, ", ".join(VALID_PROFILES)
        )

    start_on = data.get("timing", {}).get("start_on", "after_previous")
    if start_on not in VALID_START_ON:
        logger.warning(
            "Invalid timing.start_on value '%s'. Valid: %s.",
            start_on, ", ".join(VALID_START_ON)
        )

    allowed = data.get("allowed", [])
    forbidden = data.get("forbidden", [])
    overlap = set(allowed) & set(forbidden)
    if overlap:
        logger.warning(
            "Animations in both 'allowed' and 'forbidden' lists: %s. "
            "Forbidden takes priority.",
            overlap
        )


def _build_timing(data: Dict[str, Any]) -> TimingConfig:
    """Build a TimingConfig from the merged rules dict.

    Args:
        data: Merged rules dictionary containing a 'timing' key.

    Returns:
        Populated TimingConfig dataclass.
    """
    t = data.get("timing", {}) or {}
    return TimingConfig(
        default_duration_ms=int(t.get("default_duration_ms", 500)),
        delay_between_elements_ms=int(t.get("delay_between_elements_ms", 150)),
        start_on=str(t.get("start_on", "after_previous")),
        title_starts_on=str(t.get("title_starts_on", "after_previous")),
        body_starts_on=str(t.get("body_starts_on", "after_previous")),
    )


def _build_caps(data: Dict[str, Any]) -> CapsConfig:
    """Build a CapsConfig from the merged rules dict.

    Args:
        data: Merged rules dictionary containing a 'caps' key.

    Returns:
        Populated CapsConfig dataclass.
    """
    c = data.get("caps", {}) or {}
    return CapsConfig(
        max_animations_per_slide=int(c.get("max_animations_per_slide", 8)),
        max_animated_shapes_per_slide=int(c.get("max_animated_shapes_per_slide", 6)),
        skip_if_too_many_elements=int(c.get("skip_if_too_many_elements", 12)),
        no_animation_on_last_slide=bool(c.get("no_animation_on_last_slide", False)),
    )


def _build_output(data: Dict[str, Any]) -> OutputConfig:
    """Build an OutputConfig from the merged rules dict.

    Args:
        data: Merged rules dictionary containing an 'output' key.

    Returns:
        Populated OutputConfig dataclass.
    """
    o = data.get("output", {}) or {}
    return OutputConfig(
        suffix=str(o.get("suffix", "_animated")),
        overwrite_if_exists=bool(o.get("overwrite_if_exists", False)),
        preserve_notes=bool(o.get("preserve_notes", True)),
        preserve_hyperlinks=bool(o.get("preserve_hyperlinks", True)),
        preserve_masters=bool(o.get("preserve_masters", True)),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rules(
    project_root: Optional[str] = None,
    profile_override: Optional[str] = None,
) -> RulesConfig:
    """Load, merge, validate, and return the full animation rules config.

    This is the primary public function of this module. It:
      1. Locates and reads ``.antigravity/rules.yaml``
      2. Determines which profile to use (CLI override > rules.yaml > 'balanced')
      3. Loads the profile YAML and deep-merges it under the main rules
      4. Loads any per-slide overrides from ``overrides.yaml``
      5. Validates the merged config and warns on issues
      6. Returns a fully resolved ``RulesConfig`` dataclass

    If ``rules.yaml`` is missing, a warning is logged and built-in
    balanced defaults are used — the tool continues working.

    Args:
        project_root: Optional path to the project root directory.  If
            ``None``, the current working directory is used.
        profile_override: If provided (from ``--profile`` CLI flag), this
            profile name takes priority over the ``profile:`` key in
            rules.yaml.

    Returns:
        A fully populated :class:`RulesConfig` instance.

    Raises:
        SystemExit: If rules.yaml exists but has invalid YAML syntax.
        SystemExit: If ``profile_override`` names an unknown profile.
    """
    rules_path = _find_rules_path(project_root)

    # Step 1 — Load main rules.yaml (or fall back to defaults)
    if not rules_path.exists():
        logger.warning(
            "rules.yaml not found at %s — using built-in balanced defaults.",
            rules_path,
        )
        raw_rules: Dict[str, Any] = dict(_DEFAULTS)
    else:
        logger.info("Loading rules from %s", rules_path)
        raw_rules = _load_yaml_file(rules_path) or dict(_DEFAULTS)

    # Step 2 — Resolve profile name
    profile_name = profile_override or raw_rules.get("profile", "balanced")
    if profile_name not in VALID_PROFILES:
        logger.warning(
            "Unknown profile '%s' requested. Falling back to 'balanced'.",
            profile_name,
        )
        profile_name = "balanced"

    logger.info("Profile: %s", profile_name)

    # Step 3 — Load profile YAML and merge (profile is lowest priority)
    profile_data = _load_profile(profile_name, project_root)
    merged = _deep_merge(profile_data, raw_rules)
    merged["profile"] = profile_name

    # Step 4 — Load per-slide overrides
    overrides = _load_overrides(project_root)

    # Step 5 — Validate (warn, don't crash)
    _validate_and_warn(merged)

    # Step 6 — Build and return RulesConfig
    forbidden_set = list(
        set(merged.get("forbidden", [])) | ALWAYS_FORBIDDEN
    )

    return RulesConfig(
        profile=profile_name,
        timing=_build_timing(merged),
        caps=_build_caps(merged),
        elements=merged.get("elements", {}),
        slides=merged.get("slides", {}),
        first_slide=merged.get("first_slide", {}),
        allowed=merged.get("allowed", []),
        forbidden=forbidden_set,
        overrides=overrides,
        output=_build_output(merged),
    )
