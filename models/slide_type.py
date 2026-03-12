"""
models/slide_type.py
Enum defining the slide type categories the engine can detect.
"""

from enum import Enum


class SlideType(Enum):
    """Classifies a slide into a semantic category.

    The engine detects the slide type during the analysis phase and uses
    it to select the correct ``slides`` rule set from rules.yaml. Each
    value maps directly to a key in the ``slides`` section of the rulebook.
    """

    TITLE_SLIDE = "title_slide"
    """The opening slide — typically contains only a title and subtitle.
    Usually the first slide in the deck, but can be detected by layout name."""

    CONTENT_SLIDE = "content_slide"
    """A standard slide with a title and body content (bullets, images,
    shapes, charts, tables). The most common slide type."""

    SECTION_HEADER = "section_header"
    """A section divider slide — usually a large title with no body.
    Detected by layout name (e.g. 'Section Header', 'Divider')."""

    IMAGE_ONLY = "image_only"
    """A slide containing only images, with no text elements."""

    BLANK_SLIDE = "blank_slide"
    """A completely blank slide with no content. The engine skips these."""

    UNKNOWN = "unknown"
    """A slide that does not match any known pattern.
    Falls back to content_slide rules."""
