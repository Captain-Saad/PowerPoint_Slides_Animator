"""
models/animation_plan.py
Dataclasses representing the analysis of a slide and the animation
plan the planner produces for that slide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from models.element_type import ElementType
from models.slide_type import SlideType


@dataclass
class ShapeInfo:
    """Describes a single shape found on a slide after analysis.

    Attributes:
        shape_id: The integer ``id`` attribute of the shape in the slide XML.
            This value is used as the ``spid`` when injecting animations.
        shape_name: Human-readable name of the shape (from the XML ``name``
            attribute). Used for logging only.
        element_type: The semantic classification of this shape.
        paragraph_count: For text shapes, the number of non-empty paragraphs.
            Used when ``by_paragraph`` is enabled in the rules.
        has_text: Whether the shape contains any text content.
    """

    shape_id: int
    shape_name: str
    element_type: ElementType
    paragraph_count: int = 0
    has_text: bool = False


@dataclass
class SlideAnalysis:
    """The result of analyzing one slide — its type and element inventory.

    Attributes:
        slide_index: Zero-based index of the slide within the presentation.
        slide_number: One-based slide number shown to the user in logs.
        slide_type: The detected semantic type of this slide.
        shapes: Ordered list of all shapes found on the slide.
        total_element_count: Total number of shapes (used for cap checks).
        layout_name: The name of the slide layout, if available.
    """

    slide_index: int
    slide_number: int
    slide_type: SlideType
    shapes: List[ShapeInfo] = field(default_factory=list)
    total_element_count: int = 0
    layout_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Sync total_element_count with shapes list length after init."""
        if self.total_element_count == 0 and self.shapes:
            self.total_element_count = len(self.shapes)


@dataclass
class AnimationEntry:
    """A single animation to be applied to one shape (or one paragraph).

    Attributes:
        shape_id: The ``spid`` of the target shape in the slide XML.
        animation_type: Name of the animation (e.g. ``"fade"``, ``"wipe_left"``).
        duration_ms: Duration of the animation in milliseconds.
        delay_ms: Delay before this animation starts, in milliseconds.
        paragraph_index: If animating a specific paragraph (by_paragraph mode),
            the zero-based index of the paragraph. ``None`` means animate the
            whole shape.
        start_condition: How this animation is triggered.
            One of ``"click"``, ``"after_previous"``, ``"with_previous"``.
    """

    shape_id: int
    animation_type: str
    duration_ms: int
    delay_ms: int
    paragraph_index: Optional[int] = None
    start_condition: str = "after_previous"
    has_text: bool = False


@dataclass
class AnimationPlan:
    """The complete animation plan for one slide.

    Produced by the AnimationPlanner and consumed by the XMLInjector.

    Attributes:
        slide_index: Zero-based index of the slide this plan applies to.
        slide_number: One-based slide number for display in logs.
        skip: If ``True``, the injector will not write any animations for
            this slide (e.g. blank slides, or slides exceeding the element cap).
        skip_reason: Human-readable reason for skipping (logged to stdout).
        entries: Ordered list of animations to inject, in trigger sequence.
    """

    slide_index: int
    slide_number: int
    skip: bool = False
    skip_reason: Optional[str] = None
    entries: List[AnimationEntry] = field(default_factory=list)

    @property
    def animation_count(self) -> int:
        """Return the total number of animation entries in this plan."""
        return len(self.entries)
