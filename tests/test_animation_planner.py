"""
tests/test_animation_planner.py
Unit tests for engine/animation_planner.py.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import List

import pytest
from pptx import Presentation

from engine.animation_planner import AnimationPlanner
from engine.rules_loader import RulesConfig, TimingConfig, CapsConfig, OutputConfig
from engine.slide_analyzer import SlideAnalyzer
from models.animation_plan import AnimationEntry, AnimationPlan, ShapeInfo, SlideAnalysis
from models.element_type import ElementType
from models.slide_type import SlideType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def balanced_rules() -> RulesConfig:
    """Minimal balanced RulesConfig built from actual load_rules()."""
    from engine.rules_loader import load_rules
    return load_rules()


@pytest.fixture
def title_analysis() -> SlideAnalysis:
    """A SlideAnalysis for a title slide (title + subtitle)."""
    return SlideAnalysis(
        slide_index=0,
        slide_number=1,
        slide_type=SlideType.TITLE_SLIDE,
        shapes=[
            ShapeInfo(shape_id=1, shape_name="Title 1", element_type=ElementType.TITLE,
                      paragraph_count=1, has_text=True),
            ShapeInfo(shape_id=2, shape_name="Subtitle 2", element_type=ElementType.SUBTITLE,
                      paragraph_count=1, has_text=True),
        ],
        total_element_count=2,
    )


@pytest.fixture
def content_analysis() -> SlideAnalysis:
    """A SlideAnalysis for a content slide (title + 3 body bullets)."""
    return SlideAnalysis(
        slide_index=1,
        slide_number=2,
        slide_type=SlideType.CONTENT_SLIDE,
        shapes=[
            ShapeInfo(shape_id=3, shape_name="Title 1", element_type=ElementType.TITLE,
                      paragraph_count=1, has_text=True),
            ShapeInfo(shape_id=4, shape_name="Content", element_type=ElementType.BODY,
                      paragraph_count=3, has_text=True),
        ],
        total_element_count=2,
    )


@pytest.fixture
def blank_analysis() -> SlideAnalysis:
    """A SlideAnalysis for a blank slide."""
    return SlideAnalysis(
        slide_index=2,
        slide_number=3,
        slide_type=SlideType.BLANK_SLIDE,
        shapes=[],
        total_element_count=0,
    )


@pytest.fixture
def heavy_analysis() -> SlideAnalysis:
    """A SlideAnalysis with more elements than skip_if_too_many_elements (12)."""
    shapes = [
        ShapeInfo(shape_id=i, shape_name=f"Shape{i}", element_type=ElementType.SHAPE_ACCENT)
        for i in range(13)
    ]
    return SlideAnalysis(
        slide_index=3,
        slide_number=4,
        slide_type=SlideType.CONTENT_SLIDE,
        shapes=shapes,
        total_element_count=13,
    )


# ---------------------------------------------------------------------------
# Tests: skip logic
# ---------------------------------------------------------------------------

class TestShouldSkipSlide:
    """Tests for the slide-skip decision logic."""

    def test_blank_slide_is_skipped(self, blank_analysis, balanced_rules):
        """BLANK_SLIDE type → plan.skip is True."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([blank_analysis])[0]
        assert plan.skip is True

    def test_too_many_elements_skipped(self, heavy_analysis, balanced_rules):
        """Slide with >=12 elements → plan.skip is True."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([heavy_analysis])[0]
        assert plan.skip is True

    def test_last_slide_skipped_when_configured(self, content_analysis, balanced_rules):
        """no_animation_on_last_slide=True + is_last → skip."""
        balanced_rules.caps.no_animation_on_last_slide = True
        content_analysis.slide_index = 0  # make it the last (and only) slide
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        assert plan.skip is True

    def test_override_skip_true(self, content_analysis, balanced_rules):
        """Per-slide override skip=True → skipped."""
        balanced_rules.overrides[2] = {"skip": True}
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        assert plan.skip is True


# ---------------------------------------------------------------------------
# Tests: entry generation
# ---------------------------------------------------------------------------

class TestEntryGeneration:
    """Tests that the correct AnimationEntry objects are built."""

    def test_title_gets_fade(self, title_analysis, balanced_rules):
        """Title shape → fade animation."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([title_analysis])[0]
        title_entry = next(e for e in plan.entries if e.shape_id == 1)
        assert title_entry.animation_type == "fade"

    def test_body_by_paragraph_expands_entries(self, content_analysis, balanced_rules):
        """Body with 3 paragraphs → 3 AnimationEntry objects (one per para)."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        body_entries = [e for e in plan.entries if e.shape_id == 4]
        assert len(body_entries) == 3

    def test_body_paragraph_index_set(self, content_analysis, balanced_rules):
        """Each by_paragraph entry has a non-None paragraph_index."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        body_entries = [e for e in plan.entries if e.shape_id == 4]
        assert [e.paragraph_index for e in body_entries] == [0, 1, 2]

    def test_no_forbidden_animations_in_plan(self, content_analysis, balanced_rules):
        """No entry in the plan uses an animation in rules.forbidden."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        for entry in plan.entries:
            assert entry.animation_type not in balanced_rules.forbidden

    def test_all_animations_in_allowed_list(self, content_analysis, balanced_rules):
        """Every entry uses an animation from rules.allowed."""
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([content_analysis])[0]
        for entry in plan.entries:
            assert entry.animation_type in balanced_rules.allowed


# ---------------------------------------------------------------------------
# Tests: caps
# ---------------------------------------------------------------------------

class TestCapsEnforcement:
    """Tests that animation caps are always enforced."""

    def test_max_animations_per_slide_respected(self, balanced_rules):
        """Entries never exceed max_animations_per_slide."""
        balanced_rules.caps.max_animations_per_slide = 3
        # Build a slide with many shapes
        shapes = [
            ShapeInfo(shape_id=i, shape_name=f"S{i}", element_type=ElementType.TITLE
                      if i == 0 else ElementType.SHAPE_CONTENT,
                      paragraph_count=1, has_text=True)
            for i in range(8)
        ]
        analysis = SlideAnalysis(
            slide_index=0, slide_number=1, slide_type=SlideType.CONTENT_SLIDE,
            shapes=shapes, total_element_count=8,
        )
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([analysis])[0]
        assert len(plan.entries) <= 3

    def test_plan_all_returns_one_per_slide(self, title_analysis, content_analysis,
                                              blank_analysis, balanced_rules):
        """plan_all() returns exactly len(analyses) plans."""
        planner = AnimationPlanner(balanced_rules)
        plans = planner.plan_all([title_analysis, content_analysis, blank_analysis])
        assert len(plans) == 3


# ---------------------------------------------------------------------------
# Tests: first-slide override
# ---------------------------------------------------------------------------

class TestFirstSlideOverride:
    """Tests that the first slide gets special treatment."""

    def test_first_slide_uses_force_animation(self, title_analysis, balanced_rules):
        """first_slide.force_animation is applied when slide_index == 0."""
        balanced_rules.first_slide["force_animation"] = "fade"
        planner = AnimationPlanner(balanced_rules)
        plan = planner.plan_all([title_analysis])[0]
        for entry in plan.entries:
            assert entry.animation_type == "fade"
