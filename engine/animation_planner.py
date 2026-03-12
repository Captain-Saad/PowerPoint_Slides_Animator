"""
engine/animation_planner.py
Maps a list of SlideAnalysis objects + RulesConfig to an AnimationPlan
per slide using a strict 5-level rule priority chain:

  1. overrides.yaml  (per-slide manual overrides)     <- highest
  2. caps            (hard limits — always enforced)
  3. slide rules     (slide type config)
  4. element rules   (per element-type animation spec)
  5. profile yaml    (lowest priority defaults)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from engine.rules_loader import RulesConfig
from models.animation_plan import AnimationEntry, AnimationPlan, ShapeInfo, SlideAnalysis
from models.element_type import ElementType
from models.slide_type import SlideType

logger = logging.getLogger(__name__)

# Map ElementType -> the key used in rules.yaml under `elements:`
_ELEMENT_KEY_MAP: Dict[ElementType, str] = {
    ElementType.TITLE:         "title",
    ElementType.SUBTITLE:      "subtitle",
    ElementType.BODY:          "body_text",
    ElementType.IMAGE:         "image",
    ElementType.SHAPE_ACCENT:  "shape_accent",
    ElementType.SHAPE_CONTENT: "shape_content",
    ElementType.GROUPED:       "grouped_element",
    ElementType.TABLE:         "table",
    ElementType.CHART:         "chart",
    ElementType.ICON:          "icon",
}

# Element types that count against max_animated_shapes_per_slide.
# Text-bearing types (TITLE, SUBTITLE, BODY, SHAPE_CONTENT) are
# intentionally excluded — they are controlled by max_animations_per_slide
# only and must never be cut off by the shapes cap.
_SHAPE_ELEMENT_TYPES = {
    ElementType.IMAGE,
    ElementType.SHAPE_ACCENT,
    ElementType.GROUPED,
    ElementType.TABLE,
    ElementType.CHART,
    ElementType.ICON,
}


class AnimationPlanner:
    """Converts slide analysis results into per-slide animation plans.

    Rule evaluation order (highest priority wins):
      1. overrides.yaml  (per-slide manual overrides)
      2. caps            (hard limits — always enforced)
      3. slide rules     (slide type configuration)
      4. element rules   (per element-type animation spec)
      5. profile         (lowest priority defaults)

    Usage::

        planner = AnimationPlanner(rules)
        plans = planner.plan_all(analyses)
    """

    def __init__(self, rules: RulesConfig) -> None:
        self.rules = rules

    def plan_all(self, analyses: List[SlideAnalysis]) -> List[AnimationPlan]:
        """Build an AnimationPlan for every slide."""
        total = len(analyses)
        plans: List[AnimationPlan] = []
        for analysis in analyses:
            is_last = analysis.slide_index == total - 1
            plan = self._plan_slide(analysis, is_last)
            plans.append(plan)
            logger.debug(
                "Slide %d -> skip=%s  entries=%d",
                analysis.slide_number, plan.skip, plan.animation_count,
            )
        return plans

    def _plan_slide(
        self, analysis: SlideAnalysis, is_last_slide: bool
    ) -> AnimationPlan:
        """Build the AnimationPlan for a single slide."""
        should_skip, reason = self._should_skip_slide(analysis, is_last_slide)
        if should_skip:
            logger.info("Slide %d skipped (%s)", analysis.slide_number, reason)
            return AnimationPlan(
                slide_index=analysis.slide_index,
                slide_number=analysis.slide_number,
                skip=True,
                skip_reason=reason,
            )

        raw_entries = self._build_entries(analysis)
        capped_entries = self._apply_caps(raw_entries, analysis)

        return AnimationPlan(
            slide_index=analysis.slide_index,
            slide_number=analysis.slide_number,
            skip=False,
            entries=capped_entries,
        )

    def _should_skip_slide(
        self, analysis: SlideAnalysis, is_last_slide: bool
    ) -> Tuple[bool, str]:
        """Check whether this slide should be skipped entirely."""
        override = self.rules.overrides.get(analysis.slide_number, {})
        if override and override.get("skip"):
            return True, "manual override"

        slide_rule = self.rules.slides.get(analysis.slide_type.value, {})
        if slide_rule.get("skip_animation", False):
            return True, f"{analysis.slide_type.value} skip_animation=true"

        cap = self.rules.caps.skip_if_too_many_elements
        if analysis.total_element_count >= cap:
            return True, f"too many elements ({analysis.total_element_count} >= {cap})"

        if is_last_slide and self.rules.caps.no_animation_on_last_slide:
            return True, "no_animation_on_last_slide=true"

        return False, ""

    def _build_entries(self, analysis: SlideAnalysis) -> List[AnimationEntry]:
        """Build animation entries for all animatable shapes on a slide."""
        is_first = analysis.slide_index == 0
        override = self.rules.overrides.get(analysis.slide_number, {}) or {}

        slide_rule = self.rules.slides.get(analysis.slide_type.value, {}) or {}
        timing = self._resolve_slide_timing(slide_rule, is_first, override)
        anim_set = slide_rule.get("animation_set", None)

        entries: List[AnimationEntry] = []
        is_first_entry = True

        for shape in analysis.shapes:
            key = _ELEMENT_KEY_MAP.get(shape.element_type)
            if key is None:
                continue
            if anim_set and key not in anim_set:
                continue

            if is_first and self.rules.first_slide.get("force_animation"):
                spec = self._forced_first_slide_spec(shape)
            else:
                ov_el = (override.get("elements") or {}).get(key)
                spec = ov_el if ov_el else self._resolve_element_animation(key)

            if spec is None:
                continue

            anim_name = spec.get("animation", "fade")
            duration  = spec.get("duration_ms", timing["default_duration_ms"])
            base_delay = spec.get("delay_ms", 0)

            if not is_first_entry:
                element_start_delay = base_delay + timing["delay_between_elements_ms"]
            else:
                element_start_delay = base_delay

            by_para = spec.get("by_paragraph", False)
            start   = "after_previous"

            if by_para and shape.element_type == ElementType.BODY and shape.paragraph_count > 0:
                para_gap = spec.get("delay_between_paragraphs_ms", 120)
                for p_idx in range(shape.paragraph_count):
                    p_delay = element_start_delay if p_idx == 0 else para_gap
                    entries.append(AnimationEntry(
                        shape_id=shape.shape_id,
                        animation_type=anim_name,
                        duration_ms=duration,
                        delay_ms=p_delay,
                        paragraph_index=p_idx,
                        start_condition=start,
                        has_text=True,
                    ))
            else:
                entries.append(AnimationEntry(
                    shape_id=shape.shape_id,
                    animation_type=anim_name,
                    duration_ms=duration,
                    delay_ms=element_start_delay,
                    paragraph_index=None,
                    start_condition=start,
                    has_text=shape.has_text,
                ))

            is_first_entry = False

        return entries

    def _apply_caps(
        self, entries: List[AnimationEntry], analysis: SlideAnalysis
    ) -> List[AnimationEntry]:
        """Enforce max_animations_per_slide and max_animated_shapes_per_slide.

        Cap behaviour:
          - max_animations_per_slide: hard ceiling on the total number of
            AnimationEntry objects written to the slide. Applies to everything.

          - max_animated_shapes_per_slide: limits unique NON-TEXT shape IDs
            (images, charts, tables, grouped elements, accents, icons).
            Text shapes (title, subtitle, body, shape_content) and their
            paragraph-level entries are NEVER counted against this cap.
            This prevents the shapes cap from silently dropping text animations.

        Args:
            entries:  Full proposed entry list from _build_entries.
            analysis: The SlideAnalysis for this slide (used to look up
                      element_type by shape_id for cap classification).

        Returns:
            Trimmed list respecting both cap limits.
        """
        max_total  = self.rules.caps.max_animations_per_slide
        max_shapes = self.rules.caps.max_animated_shapes_per_slide

        # Build a shape_id -> element_type lookup from the analysis so we
        # can correctly classify each entry without storing element_type
        # on AnimationEntry itself.
        shape_type_lookup: Dict[int, ElementType] = {
            s.shape_id: s.element_type for s in analysis.shapes
        }

        result: List[AnimationEntry] = []
        # Tracks unique shape_ids for NON-TEXT shapes only
        capped_shape_ids: set = set()
        # Tracks NON-TEXT shape_ids that were ACCEPTED (not dropped by cap)
        accepted_shape_ids: set = set()

        for entry in entries:
            # Hard ceiling on total animations
            if len(result) >= max_total:
                logger.debug(
                    "Slide %d: max_animations_per_slide=%d reached, "
                    "dropping %d remaining entries.",
                    analysis.slide_number, max_total,
                    len(entries) - len(result),
                )
                break

            element_type = shape_type_lookup.get(entry.shape_id)
            is_shape_type = element_type in _SHAPE_ELEMENT_TYPES

            if is_shape_type:
                # This is a non-text shape — enforce the shapes cap
                if entry.shape_id not in capped_shape_ids:
                    # First time we see this non-text shape
                    if len(capped_shape_ids) >= max_shapes:
                        logger.debug(
                            "Slide %d: max_animated_shapes_per_slide=%d reached, "
                            "skipping non-text shape_id=%s (%s).",
                            analysis.slide_number, max_shapes,
                            entry.shape_id, element_type,
                        )
                        capped_shape_ids.add(entry.shape_id)  # mark as seen+dropped
                        continue
                    # Accept this shape
                    capped_shape_ids.add(entry.shape_id)
                    accepted_shape_ids.add(entry.shape_id)
                elif entry.shape_id not in accepted_shape_ids:
                    # Seen before but was dropped — drop this entry too
                    continue
            # Text shapes (TITLE, SUBTITLE, BODY, SHAPE_CONTENT) and their
            # paragraph entries pass through freely — never capped by shape limit.

            result.append(entry)

        return result

    def _resolve_element_animation(self, element_key: str) -> Optional[dict]:
        """Resolve the animation spec for an element key from rules."""
        spec = (self.rules.elements or {}).get(element_key)
        if not spec:
            return None
        anim = spec.get("animation", "fade")
        if anim in self.rules.forbidden:
            logger.warning("Animation '%s' is forbidden — skipping %s", anim, element_key)
            return None
        if self.rules.allowed and anim not in self.rules.allowed:
            logger.warning("Animation '%s' not in allowed list — skipping %s", anim, element_key)
            return None
        return spec

    def _resolve_slide_timing(
        self, slide_rule: dict, is_first: bool, override: dict
    ) -> dict:
        """Build effective timing dict for a slide from applicable rules."""
        base = {
            "default_duration_ms":      self.rules.timing.default_duration_ms,
            "delay_between_elements_ms": self.rules.timing.delay_between_elements_ms,
        }
        slide_ot = slide_rule.get("override_timing", {}) or {}
        base.update({k: v for k, v in slide_ot.items() if v is not None})
        if is_first:
            fs = self.rules.first_slide or {}
            if "delay_between_elements_ms" in fs:
                base["delay_between_elements_ms"] = fs["delay_between_elements_ms"]
            if "duration_ms" in fs:
                base["default_duration_ms"] = fs["duration_ms"]
        ov_timing = override.get("timing", {}) or {}
        base.update({k: v for k, v in ov_timing.items() if v is not None})
        return base

    def _forced_first_slide_spec(self, shape: ShapeInfo) -> dict:
        """Build a spec that forces the first-slide animation for a shape."""
        fs = self.rules.first_slide or {}
        anim     = fs.get("force_animation", "fade")
        duration = fs.get("duration_ms", self.rules.timing.default_duration_ms)
        return {"animation": anim, "duration_ms": duration, "delay_ms": 0}