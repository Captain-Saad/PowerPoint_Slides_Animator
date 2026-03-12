"""
models/element_type.py
Enum defining every element type the engine can detect on a slide.
"""

from enum import Enum


class ElementType(Enum):
    """Classifies a shape on a slide into a semantic category.

    The engine uses this classification to look up the correct animation
    rule from rules.yaml. Each value maps directly to a key in the
    ``elements`` section of the rulebook.
    """

    TITLE = "title"
    """The primary title placeholder on a slide."""

    SUBTITLE = "subtitle"
    """The subtitle placeholder (typically on title slides only)."""

    BODY = "body_text"
    """A body text / content placeholder (bullets, paragraphs)."""

    IMAGE = "image"
    """A picture, photo, or image shape (picture placeholder or inline image)."""

    SHAPE_ACCENT = "shape_accent"
    """A decorative shape with no text content (lines, borders, dividers)."""

    SHAPE_CONTENT = "shape_content"
    """A non-placeholder shape that contains text (callout boxes, labels)."""

    GROUPED = "grouped_element"
    """A group shape — animated as a single unit."""

    TABLE = "table"
    """A table object on the slide."""

    CHART = "chart"
    """A chart or graph object on the slide."""

    ICON = "icon"
    """A small icon shape (typically small, decorative, no text)."""

    UNKNOWN = "unknown"
    """A shape that could not be classified. The engine skips unknown shapes."""
