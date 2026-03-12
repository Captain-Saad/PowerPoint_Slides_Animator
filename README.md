# PPTX Animation Engine

> Intelligently inject professional, restrained animations into any `.pptx` file — without touching your design.

**Developer:** Saad · **Version:** 1.0 (M1 Skeleton) · **Stack:** Python 3.9+, python-pptx, lxml, PyYAML

---

## What it does

Takes any `.pptx` file and injects tasteful, professional entrance animations — slide by slide — preserving every pixel of your original design.

- Titles fade in clean. Body text wipes left. Charts grow upward.
- Configurable via `.antigravity/rules.yaml` — no code changes needed.
- Three presets: `subtle`, `balanced` (default), `dynamic`.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Animate a deck (output: my_deck_animated.pptx)
python animate.py my_deck.pptx

# Use the subtle profile
python animate.py my_deck.pptx --profile subtle

# Preview without writing (dry run)
python animate.py my_deck.pptx --dry-run --verbose

# Skip specific slides, force overwrite
python animate.py my_deck.pptx --skip-slides 1,5 --overwrite
```

## CLI Reference

```
python animate.py input.pptx [output.pptx] [options]

Arguments:
  input.pptx          Source PowerPoint file (required)
  output.pptx         Output path (default: input_animated.pptx)

Options:
  --profile PROFILE   Animation profile: subtle | balanced | dynamic
  --dry-run           Print plan without writing output
  --skip-slides N,N   Comma-separated 1-based slide numbers to skip
  --verbose, -v       Show DEBUG-level log output
  --overwrite         Overwrite output without prompting
  -h, --help          Show this help message
```

## Configuration

Edit `.antigravity/rules.yaml` to control every animation decision:

```yaml
profile: balanced          # subtle | balanced | dynamic

timing:
  default_duration_ms: 500
  delay_between_elements_ms: 150

caps:
  max_animations_per_slide: 8
  skip_if_too_many_elements: 12
```

Per-slide overrides: `.antigravity/overrides.yaml`

## Project Structure

```
pptx-animator/
├── animate.py              ← CLI entry point
├── .antigravity/
│   ├── rules.yaml          ← Main animation rulebook
│   ├── profiles/           ← subtle / balanced / dynamic presets
│   └── overrides.yaml      ← Per-slide manual overrides
├── engine/
│   ├── rules_loader.py     ← Loads & validates rules.yaml  [M1 ✅]
│   ├── slide_analyzer.py   ← Detects slide & element types [M2]
│   ├── animation_planner.py← Maps rules → AnimationPlan   [M3]
│   ├── xml_injector.py     ← Writes OOXML into slides      [M4]
│   └── output_writer.py    ← Saves file, logs summary      [M5]
├── models/
│   ├── element_type.py     ← ElementType enum
│   ├── slide_type.py       ← SlideType enum
│   └── animation_plan.py   ← Core dataclasses
└── tests/                  ← Unit & integration tests       [M6]
```

## Milestones

| Milestone | Status | What |
|-----------|--------|------|
| M1: Skeleton | ✅ Done | Structure, CLI, rules loader |
| M2: Analyzer | ⬜ Next | Slide & element type detection |
| M3: Planner | ⬜ | Rule application, animation planning |
| M4: Injector | ⬜ | OOXML writing |
| M5: Output | ⬜ | File saving, dry-run, summary |
| M6: Testing | ⬜ | Unit + integration tests |

## Allowed Animations

| Name | OOXML presetID | Use for |
|------|---------------|---------|
| `fade` | 10 | Titles, images, tables |
| `appear` | 1 | Decorative shapes, icons |
| `wipe_left` | 2764 | Body text bullets |
| `wipe_right` | 2765 | Alternate text direction |
| `wipe_bottom` | 2766 | Charts (grows upward) |
| `fly_in_from_left` | 27 | Titles (dynamic profile) |
| `fly_in_from_bottom` | 26 | Images (dynamic profile) |

---

*Built by Saad. SRS v1.0.*
