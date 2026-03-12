"""
animate.py
CLI entry point for the PPTX Animation Engine.

Usage:
  python animate.py input.pptx
  python animate.py input.pptx output.pptx
  python animate.py input.pptx --profile subtle
  python animate.py input.pptx --dry-run
  python animate.py input.pptx --skip-slides 1,5,9
  python animate.py input.pptx --verbose
  python animate.py input.pptx --overwrite
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_FORMAT = "[PPTX Animator] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` with all supported flags.
    """
    parser = argparse.ArgumentParser(
        prog="animate",
        description=(
            "PPTX Animation Engine — Intelligently inject professional animations "
            "into any PowerPoint file without touching a single design element."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python animate.py deck.pptx
  python animate.py deck.pptx out.pptx --profile subtle
  python animate.py deck.pptx --dry-run --verbose
  python animate.py deck.pptx --skip-slides 1,5,9 --overwrite
""",
    )

    # Positional: input file (required)
    parser.add_argument(
        "input",
        metavar="input.pptx",
        help="Path to the source PowerPoint file (.pptx).",
    )

    # Optional positional: output file
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        metavar="output.pptx",
        help=(
            "Path for the animated output file. "
            "Default: <input_name>_animated.pptx in the same directory."
        ),
    )

    # --profile
    parser.add_argument(
        "--profile",
        metavar="PROFILE",
        default=None,
        choices=["subtle", "balanced", "dynamic"],
        help=(
            "Animation profile to use. Overrides the profile set in "
            ".antigravity/rules.yaml. "
            "Choices: subtle | balanced | dynamic. "
            "Default: uses value from rules.yaml (balanced)."
        ),
    )

    # --dry-run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Analyze and plan animations, print a full summary, "
            "but do NOT write any output file."
        ),
    )

    # --skip-slides
    parser.add_argument(
        "--skip-slides",
        metavar="N,N,...",
        default=None,
        help=(
            "Comma-separated list of 1-based slide numbers to skip. "
            "Example: --skip-slides 1,5,9"
        ),
    )

    # --verbose
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose logging (DEBUG level). Shows detailed rule resolution.",
    )

    # --overwrite
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help=(
            "Silently overwrite the output file if it already exists. "
            "Without this flag, the tool will prompt for confirmation."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Argument validation helpers
# ---------------------------------------------------------------------------

def validate_input_path(input_path: str) -> Path:
    """Validate that the input path exists and is a .pptx file.

    Args:
        input_path: The raw input path string from CLI args.

    Returns:
        Resolved :class:`~pathlib.Path` to the input file.

    Raises:
        SystemExit: If the file does not exist or has the wrong extension.
    """
    path = Path(input_path).resolve()
    if not path.exists():
        sys.exit(f"Error: File not found: {input_path}")
    if path.suffix.lower() != ".pptx":
        sys.exit(
            f"Error: Input file must be a .pptx file, got: {path.suffix!r}"
        )
    return path


def parse_skip_slides(skip_arg: Optional[str]) -> List[int]:
    """Parse the --skip-slides argument into a list of 1-based integers.

    Args:
        skip_arg: Raw string from CLI (e.g. ``"1,5,9"``) or ``None``.

    Returns:
        List of integers (1-based slide numbers to skip). Empty list if
        ``skip_arg`` is ``None``.

    Raises:
        SystemExit: If any value in the list cannot be parsed as an integer.
    """
    if not skip_arg:
        return []
    try:
        return [int(n.strip()) for n in skip_arg.split(",") if n.strip()]
    except ValueError:
        sys.exit(
            f"Error: --skip-slides must be comma-separated integers, "
            f"got: {skip_arg!r}"
        )


def resolve_output_path(input_path: Path, output_arg: Optional[str]) -> Path:
    """Determine the final output file path.

    Uses the explicit output argument if given, otherwise appends the
    configured suffix (``_animated``) to the input filename.

    Args:
        input_path: Resolved input :class:`~pathlib.Path`.
        output_arg: Optional explicit output path string from CLI.

    Returns:
        Resolved output :class:`~pathlib.Path`.
    """
    if output_arg:
        return Path(output_arg).resolve()
    stem = input_path.stem
    output_name = f"{stem}_animated{input_path.suffix}"
    return input_path.parent / output_name


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def run_pipeline(args: argparse.Namespace) -> None:
    """Orchestrate the full animation pipeline.

    Steps:
      1. Load rules         (RulesLoader)
      2. Analyse slides     (SlideAnalyzer)
      3. Build plans        (AnimationPlanner)
      4. Inject XML         (XMLInjector)
      5. Write output       (OutputWriter)

    Args:
        args: Parsed CLI arguments from :func:`build_parser`.
    """
    from engine.rules_loader import load_rules
    from engine.slide_analyzer import SlideAnalyzer
    from engine.animation_planner import AnimationPlanner
    from engine.xml_injector import XMLInjector
    from engine.output_writer import OutputWriter

    # --- Validate inputs ---
    input_path = validate_input_path(args.input)
    skip_slides = parse_skip_slides(args.skip_slides)
    output_path = resolve_output_path(input_path, args.output)

    # --- Step 1: Load rules ---
    rules = load_rules(profile_override=args.profile)
    if args.overwrite:
        rules.output.overwrite_if_exists = True

    if args.dry_run:
        logger.info("DRY RUN — no output file will be written.")

    # --- Step 2: Analyse slides ---
    logger.info("Analyzing: %s", input_path.name)
    analyzer = SlideAnalyzer(str(input_path))
    analyses = analyzer.analyze_all()
    logger.info("Found %d slide%s", len(analyses), "s" if len(analyses) != 1 else "")

    for analysis in analyses:
        skip_tag = " [SKIPPED via --skip-slides]" if analysis.slide_number in skip_slides else ""
        logger.info(
            "  Slide %d [%s]  →  %d element%s%s",
            analysis.slide_number,
            analysis.slide_type.value,
            analysis.total_element_count,
            "s" if analysis.total_element_count != 1 else "",
            skip_tag,
        )

    # --- Step 3: Build animation plans ---
    planner = AnimationPlanner(rules)
    plans = planner.plan_all(analyses)

    # Apply --skip-slides: mark those slides as skipped
    for plan in plans:
        if plan.slide_number in skip_slides and not plan.skip:
            plan.skip = True
            plan.skip_reason = "--skip-slides flag"
            plan.entries.clear()

    # --- Step 4: Inject XML into each slide ---
    injector = XMLInjector()
    for slide, plan in zip(analyzer.prs.slides, plans):
        injector.inject(slide, plan)

    # --- Step 5: Write output ---
    writer = OutputWriter(rules, dry_run=args.dry_run)
    writer.write(analyzer.prs, plans, str(output_path))



# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point: parse args, configure logging, run the pipeline."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")

    run_pipeline(args)


if __name__ == "__main__":
    main()
