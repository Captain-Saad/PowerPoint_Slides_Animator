"""
engine/output_writer.py
Saves the modified python-pptx Presentation to disk, prints a
per-slide animation summary to stdout, and handles dry-run mode.

On --dry-run, only the summary is printed — no file is written.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import List

from engine.rules_loader import RulesConfig
from models.animation_plan import AnimationPlan

logger = logging.getLogger(__name__)

# Width of slide-number column in the summary output
_SLIDE_COL_WIDTH = 10


class OutputWriter:
    """Handles saving the animated presentation and logging results.

    Usage::

        writer = OutputWriter(rules, dry_run=False)
        writer.write(presentation, plans, output_path)
    """

    def __init__(self, rules: RulesConfig, dry_run: bool = False) -> None:
        """Initialize the writer.

        Args:
            rules: Resolved :class:`~engine.rules_loader.RulesConfig`.
            dry_run: If ``True``, print summary but do not write the file.
        """
        self.rules = rules
        self.dry_run = dry_run

    def write(
        self,
        presentation: object,
        plans: List[AnimationPlan],
        output_path: str,
    ) -> None:
        """Write the presentation to disk and print the animation summary.

        Args:
            presentation: Modified python-pptx ``Presentation`` object.
            plans: List of AnimationPlan objects, one per slide.
            output_path: Absolute or relative output file path.
        """
        self._print_summary(plans)

        total = sum(p.animation_count for p in plans)
        logger.info("Total animations injected: %d", total)

        if self.dry_run:
            logger.info("DRY RUN — output file NOT written.")
            return

        self._check_overwrite(output_path)
        self._save_presentation(presentation, output_path)
        logger.info("Output saved: %s", Path(output_path).name)

    def resolve_output_path(self, input_path: str) -> str:
        """Compute the default output path using the configured suffix.

        Args:
            input_path: Path to the source .pptx file.

        Returns:
            Output file path string (e.g. ``deck_animated.pptx``).
        """
        p = Path(input_path)
        return str(p.parent / f"{p.stem}{self.rules.output.suffix}{p.suffix}")

    def _check_overwrite(self, output_path: str) -> None:
        """Prompt the user before overwriting an existing output file.

        Args:
            output_path: Path to the potential output file.

        Raises:
            SystemExit: If the user declines to overwrite.
        """
        if not Path(output_path).exists():
            return
        if self.rules.output.overwrite_if_exists:
            logger.info("Overwriting existing file: %s", output_path)
            return
        # Interactive prompt
        try:
            answer = input(
                f"\nOutput file already exists: {output_path}\n"
                f"Overwrite? [y/N] "
            ).strip().lower()
        except EOFError:
            answer = "n"
        if answer not in {"y", "yes"}:
            sys.exit("Aborted — output file not overwritten.")

    def _save_presentation(self, presentation: object, output_path: str) -> None:
        """Save the Presentation to the output path.

        Args:
            presentation: python-pptx Presentation to save.
            output_path: Destination file path.

        Raises:
            SystemExit: If the path is not writable or file is zero bytes.
        """
        try:
            presentation.save(output_path)
        except PermissionError:
            sys.exit(f"Error: Cannot write to output path: {output_path}")
        except Exception as exc:
            sys.exit(f"Error: Failed to save presentation: {exc}")

        size = Path(output_path).stat().st_size
        if size == 0:
            sys.exit(
                f"Error: Output file is 0 bytes — possible corruption: {output_path}"
            )

    def _print_summary(self, plans: List[AnimationPlan]) -> None:
        """Print a per-slide animation summary matching SRS Section 11.3.

        Args:
            plans: List of AnimationPlan objects, one per slide.
        """
        print()
        for plan in plans:
            print(self._format_slide_line(plan))
        print()

    def _format_slide_line(self, plan: AnimationPlan) -> str:
        """Format one slide's summary line for stdout.

        Example output:
          ``  Slide 2 [content_slide]  → Title: fade(400ms), Body[3]: wipe_left(350ms)``

        Args:
            plan: AnimationPlan for the slide.

        Returns:
            Formatted summary string.
        """
        snum = f"Slide {plan.slide_number}"
        if plan.skip:
            return f"  {snum:<{_SLIDE_COL_WIDTH}} [SKIPPED] — {plan.skip_reason or ''}"

        if not plan.entries:
            return f"  {snum:<{_SLIDE_COL_WIDTH}} → (no animations)"

        # Group entries by shape_id to build a compact description
        parts: List[str] = []
        seen_shapes: set = set()

        for entry in plan.entries:
            if entry.shape_id in seen_shapes:
                continue
            # Count total entries for this shape (by_paragraph may have many)
            count = sum(1 for e in plan.entries if e.shape_id == entry.shape_id)
            label = self._entry_label(entry, count)
            parts.append(label)
            seen_shapes.add(entry.shape_id)

        desc = ", ".join(parts)
        return f"  {snum:<{_SLIDE_COL_WIDTH}} → {desc}"

    def _entry_label(self, entry: object, count: int) -> str:
        """Build a short human-readable label for one animation entry.

        Args:
            entry: The first AnimationEntry for a shape.
            count: Total entries for this shape (1 if not by_paragraph).

        Returns:
            Label string e.g. ``"Body[3]: wipe_left(350ms)"``.
        """
        anim = entry.animation_type
        dur = entry.duration_ms
        if count > 1:
            return f"Body[{count}]: {anim}({dur}ms)"
        return f"{anim}({dur}ms)"
