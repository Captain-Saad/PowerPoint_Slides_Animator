# Software Requirements Specification (SRS)
## PPTX Animation Engine
**Project:** Intelligent PowerPoint Animation Injector  
**Developer:** Saad (Solo)  
**Version:** 1.0  
**Date:** March 2026  
**Stack:** Python, python-pptx, lxml

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Project Overview](#2-project-overview)
3. [Scope](#3-scope)
4. [Antigravity Rules (.antigravity/rules)](#4-antigravity-rules)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [System Architecture](#7-system-architecture)
8. [Animation Strategy](#8-animation-strategy)
9. [File & Folder Structure](#9-file--folder-structure)
10. [Module Breakdown](#10-module-breakdown)
11. [Input / Output Specification](#11-input--output-specification)
12. [Error Handling](#12-error-handling)
13. [Testing Plan](#13-testing-plan)
14. [Milestones (Solo Developer)](#14-milestones-solo-developer)
15. [Glossary](#15-glossary)

---

## 1. Introduction

### 1.1 Purpose
This document defines the complete software requirements for a command-line tool that accepts a `.pptx` file as input, intelligently analyzes each slide's content and layout, and injects tasteful, professional animations — without breaking the original design or formatting.

### 1.2 Intended Audience
- **Saad** — sole developer, uses this as both a build guide and a reference throughout development.

### 1.3 Background
Tools like Gamma generate beautiful presentations but their animations don't survive PPTX export — exports are static. This tool bridges that gap by programmatically adding animations to any `.pptx` file using `python-pptx` and direct OOXML manipulation, preserving the original design completely.

---

## 2. Project Overview

**User Story:**  
> "As a user, I give the tool my `.pptx` file and it gives me back the same file with clean, professional animations added — nothing broken, nothing over the top."

**What this tool does:**
- Reads any `.pptx` file
- Analyzes each slide: number of elements, element types (title, body, image, shape), slide order
- Applies a smart, restrained animation scheme per slide
- Outputs an animated `.pptx` file — same design, same layout, now alive

**What this tool does NOT do:**
- Does not change colors, fonts, layouts, or content
- Does not add or remove slides
- Does not require internet access
- Does not require a GUI (CLI only, v1.0)

---

## 3. Scope

### 3.1 In Scope (v1.0)
- CLI tool: `python animate.py input.pptx [output.pptx]`
- Slide-by-slide animation injection using OOXML
- Support for: title text, body text, images, shapes, grouped elements
- Entrance animations only (Fade, Appear, Fly In, Wipe) — no exit or motion path
- Timing: sequential within a slide, auto-triggered between elements
- Preserves: all text, images, layouts, masters, themes, notes, hyperlinks

### 3.2 Out of Scope (v1.0)
- GUI or web interface
- Exit animations or motion paths
- Sound effects
- Slide transitions (may be added in v1.1)
- Batch processing of multiple files
- Cloud storage integration

---

## 4. Antigravity Rules (.antigravity/rules)

The `.antigravity/rules` file is the **heart of the animation philosophy**. It defines every decision the engine makes about what animation to apply, when, and how. Saad writes this file in YAML. The engine reads it at runtime. This means animation behavior can be tuned without touching Python code.

### 4.1 What is `.antigravity/`?

`.antigravity/` is a config directory at the root of the project:

```
.antigravity/
├── rules.yaml        ← Main animation rulebook
├── profiles/
│   ├── subtle.yaml   ← Conservative preset
│   ├── balanced.yaml ← Default preset (recommended)
│   └── dynamic.yaml  ← More energetic (still tasteful)
└── overrides.yaml    ← Per-slide manual overrides (optional)
```

### 4.2 rules.yaml — Full Specification

```yaml
# ============================================================
# .antigravity/rules.yaml
# Animation Rulebook — Read by the engine at runtime
# Edit this file to change animation behavior without touching code.
# ============================================================

profile: balanced          # Which profile to inherit defaults from
                           # Options: subtle | balanced | dynamic

# ------------------------------------------------------------
# GLOBAL TIMING
# Controls how fast/slow animations play across all slides
# ------------------------------------------------------------
timing:
  default_duration_ms: 500       # Duration of each animation in ms
  delay_between_elements_ms: 150 # Gap between each element animating in
  start_on: click                # "click" | "after_previous" | "with_previous"
                                 # "click" = user advances manually
                                 # "after_previous" = auto-chain (recommended)
                                 # "with_previous" = all at once (avoid for body text)
  title_starts_on: after_previous
  body_starts_on: after_previous

# ------------------------------------------------------------
# ELEMENT RULES
# Defines which animation to apply to each element type
# ------------------------------------------------------------
elements:

  title:
    animation: fade            # Titles always fade in — clean and readable
    duration_ms: 400
    delay_ms: 0                # Title is always first, no delay

  subtitle:
    animation: fade
    duration_ms: 400
    delay_ms: 100

  body_text:
    animation: wipe_left       # Body text wipes in from left — directional and clean
    duration_ms: 350
    by_paragraph: true         # Animate each paragraph/bullet separately
                               # Set false to animate the whole text box at once
    delay_between_paragraphs_ms: 120

  image:
    animation: fade
    duration_ms: 600           # Images get slightly longer fade — more weight
    delay_ms: 200

  shape_accent:                # Decorative shapes, lines, borders
    animation: appear          # Instant appear — don't draw attention to decorations
    duration_ms: 0
    delay_ms: 50

  shape_content:               # Shapes that contain content (callout boxes, etc.)
    animation: fade
    duration_ms: 400
    delay_ms: 150

  grouped_element:
    animation: fade            # Groups animate as one unit
    duration_ms: 500
    delay_ms: 200

  table:
    animation: fade
    duration_ms: 500
    delay_ms: 100

  chart:
    animation: wipe_bottom     # Charts wipe upward — feels like data "growing"
    duration_ms: 700
    delay_ms: 200

  icon:
    animation: appear
    duration_ms: 0
    delay_ms: 100

# ------------------------------------------------------------
# SLIDE RULES
# Slide-type detection and how to handle each type
# ------------------------------------------------------------
slides:

  title_slide:                 # First slide / slide with only a title + subtitle
    skip_animation: false
    animation_set: [title, subtitle]
    override_timing:
      delay_between_elements_ms: 200

  content_slide:               # Standard slide with title + body content
    skip_animation: false
    animation_set: [title, body_text, image, shape_content]

  section_header:              # Section divider slides (detected by layout name)
    skip_animation: false
    animation_set: [title]
    override_timing:
      default_duration_ms: 600  # Slightly slower for dramatic effect

  blank_slide:
    skip_animation: true       # Nothing to animate

  image_only:                  # Slide with only images, no text
    animation_set: [image]
    override_timing:
      default_duration_ms: 800

# ------------------------------------------------------------
# ANIMATION CAPS — Anti-chaos rules
# These are hard limits. The engine enforces these regardless of other settings.
# ------------------------------------------------------------
caps:
  max_animations_per_slide: 8        # Never add more than 8 animations on one slide
  max_animated_shapes_per_slide: 6   # Cap on shape animations (excludes text)
  skip_if_too_many_elements: 12      # If a slide has 12+ elements, skip animation entirely
                                     # (overly complex slides — don't make it worse)
  no_animation_on_last_slide: false  # Set true to leave the final slide static

# ------------------------------------------------------------
# FORBIDDEN ANIMATIONS
# These are never used — too flashy, distracting, or unprofessional
# ------------------------------------------------------------
forbidden:
  - bounce
  - spin
  - zoom_in_crazy
  - boomerang
  - swivel
  - pinwheel
  - credits_roll
  - fly_in_from_top     # Too abrupt for professional decks
  - typewriter          # Too slow and gimmicky

# ------------------------------------------------------------
# ALLOWED ANIMATIONS (whitelist)
# Only these are permitted by the engine
# ------------------------------------------------------------
allowed:
  - fade                # Smooth opacity fade — always safe
  - appear              # Instant appearance — use for minor elements
  - wipe_left           # Left-to-right reveal — good for text
  - wipe_right          # Right-to-left reveal
  - wipe_bottom         # Bottom-up reveal — good for charts/data
  - fly_in_from_left    # Subtle slide in from left — use sparingly
  - fly_in_from_bottom  # Gentle rise — acceptable for key points

# ------------------------------------------------------------
# FIRST SLIDE OVERRIDE
# The first slide always gets special treatment
# ------------------------------------------------------------
first_slide:
  force_animation: fade
  duration_ms: 600
  delay_between_elements_ms: 250    # More breathing room on the opener

# ------------------------------------------------------------
# OUTPUT BEHAVIOR
# ------------------------------------------------------------
output:
  suffix: _animated                  # Output file: input_animated.pptx
  overwrite_if_exists: false         # Never silently overwrite
  preserve_notes: true
  preserve_hyperlinks: true
  preserve_masters: true
```

### 4.3 Rules Evaluation Order

The engine applies rules in this priority order (highest wins):

```
1. overrides.yaml (manual per-slide overrides)  ← Highest priority
2. caps (hard limits — always enforced)
3. slide-type rules (title_slide, content_slide, etc.)
4. element rules (title, body_text, image, etc.)
5. profile defaults (subtle / balanced / dynamic)   ← Lowest priority
```

---

## 5. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Accept a `.pptx` file path as CLI argument | Must Have |
| FR-02 | Read and parse all slides without modifying content | Must Have |
| FR-03 | Detect element types per slide (title, body, image, shape, group, chart, table) | Must Have |
| FR-04 | Detect slide type (title slide, content slide, section header, blank, image-only) | Must Have |
| FR-05 | Load `.antigravity/rules.yaml` at runtime | Must Have |
| FR-06 | Inject OOXML animation XML (`<p:timing>`, `<p:animEffect>`) per element | Must Have |
| FR-07 | Respect all caps defined in rules.yaml | Must Have |
| FR-08 | Output an animated `.pptx` file with `_animated` suffix | Must Have |
| FR-09 | Preserve all original formatting, fonts, colors, images, layouts | Must Have |
| FR-10 | Log which animations were applied to which slide/element | Should Have |
| FR-11 | Support `--profile` CLI flag to override default profile | Should Have |
| FR-12 | Support `--dry-run` flag to log what would happen without writing | Should Have |
| FR-13 | Support `--skip-slides` CLI flag (e.g. `--skip-slides 1,5,9`) | Should Have |
| FR-14 | Validate rules.yaml schema on load and warn on errors | Should Have |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Processing time | Under 10s for a 30-slide deck |
| NFR-02 | Output file integrity | Must open in PowerPoint and Google Slides without corruption |
| NFR-03 | No content loss | Zero tolerance — if any content is missing, tool fails loudly |
| NFR-04 | No external dependencies beyond pip | Runs fully offline |
| NFR-05 | Python version | 3.9+ |
| NFR-06 | Cross-platform | Windows, macOS, Linux |
| NFR-07 | Code readability | Each module < 300 lines. Functions < 40 lines. |

---

## 7. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                       │
│                        animate.py                           │
└────────────────────────────┬────────────────────────────────┘
                             │
           ┌─────────────────▼──────────────────┐
           │         RulesLoader                 │
           │   Reads .antigravity/rules.yaml     │
           │   Validates schema                  │
           │   Returns RulesConfig object        │
           └─────────────────┬──────────────────┘
                             │
           ┌─────────────────▼──────────────────┐
           │         SlideAnalyzer               │
           │   Opens .pptx with python-pptx      │
           │   Per slide: detects type,          │
           │   enumerates shapes, classifies     │
           │   each shape by type                │
           └─────────────────┬──────────────────┘
                             │
           ┌─────────────────▼──────────────────┐
           │         AnimationPlanner            │
           │   Applies rules to analysis         │
           │   Builds AnimationPlan per slide    │
           │   Enforces all caps                 │
           │   Respects forbidden list           │
           └─────────────────┬──────────────────┘
                             │
           ┌─────────────────▼──────────────────┐
           │         XMLInjector                 │
           │   Directly manipulates slide XML    │
           │   Injects <p:timing> blocks         │
           │   Assigns sp IDs and seq IDs        │
           │   Handles timing chain              │
           └─────────────────┬──────────────────┘
                             │
           ┌─────────────────▼──────────────────┐
           │         OutputWriter                │
           │   Saves modified .pptx              │
           │   Verifies file opens correctly     │
           │   Logs summary report               │
           └────────────────────────────────────┘
```

---

## 8. Animation Strategy

### 8.1 Philosophy
> **"Animations should feel discovered, not performed."**

The goal is that a viewer watching the presentation doesn't think "oh, animations" — they just feel the content is flowing naturally. Every animation decision follows three rules:

1. **Purpose over flair** — every animation must make the content easier to follow, not show off
2. **Restraint** — when in doubt, use Fade. Never use more than one animation style per slide type
3. **Consistency** — titles always animate the same way. Body text always animates the same way. No surprises.

### 8.2 Animation Mapping (Default: Balanced Profile)

| Element | Animation | Why |
|---------|-----------|-----|
| Slide Title | Fade In (400ms) | Clean, instant authority |
| Subtitle | Fade In (400ms, 100ms delay) | Follows title smoothly |
| Body Text (bullets) | Wipe Left (350ms, per paragraph) | Directional, readable, professional |
| Image | Fade In (600ms) | Weight and gravitas |
| Decorative Shape | Appear (instant) | Background — don't distract |
| Content Shape/Box | Fade In (400ms) | Supports the content |
| Chart | Wipe Bottom (700ms) | Data "growing up" — intuitive |
| Table | Fade In (500ms) | Clean reveal |
| Group | Fade In (500ms) | Treat as one unit |

### 8.3 OOXML Animation Snippet Reference

python-pptx doesn't expose animations natively. The engine writes raw XML. Here's the pattern:

```xml
<!-- Inside each slide's <p:sld> > <p:timing> block -->
<p:timing>
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="whenNotActive" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>

                <!-- One <p:par> block per animated element -->
                <p:par>
                  <p:cTn id="3" fill="hold">
                    <p:stCondLst>
                      <p:cond delay="0"/>   <!-- delay in ms -->
                    </p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="4" presetID="10" presetClass="entr"
                               presetSubtype="0" fill="hold"
                               grpId="0" nodeType="clickEffect">
                          <p:stCondLst>
                            <p:cond delay="0"/>
                          </p:stCondLst>
                          <p:childTnLst>
                            <p:set>
                              <p:cBhvr>
                                <p:cTn id="5" dur="1" fill="hold"/>
                                <p:tgtEl>
                                  <p:spTgt spid="123"/> <!-- shape ID -->
                                </p:tgtEl>
                                <p:attrNameLst>
                                  <p:attrName>style.visibility</p:attrName>
                                </p:attrNameLst>
                              </p:cBhvr>
                              <p:to><p:strVal val="visible"/></p:to>
                            </p:set>
                            <p:animEffect transition="in" filter="fade">
                              <p:cBhvr>
                                <p:cTn id="6" dur="500"/> <!-- duration ms -->
                                <p:tgtEl>
                                  <p:spTgt spid="123"/>
                                </p:tgtEl>
                              </p:cBhvr>
                            </p:animEffect>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>

              </p:childTnLst>
            </p:cTn>
            <!-- Required navigation conditions -->
            <p:prevCondLst>
              <p:cond evt="onPrevClick" delay="0">
                <p:tgtEl><p:sldTgt/></p:tgtEl>
              </p:cond>
            </p:prevCondLst>
            <p:nextCondLst>
              <p:cond evt="onNextClick" delay="0">
                <p:tgtEl><p:sldTgt/></p:tgtEl>
              </p:cond>
            </p:nextCondLst>
          </p:seq>
        </p:childTnLst>
      </p:cTn>
    </p:par>
  </p:tnLst>
</p:timing>
```

**presetID reference (entrance animations only):**

| presetID | Animation Name |
|----------|---------------|
| 1 | Appear |
| 10 | Fade |
| 2764 | Wipe (Left) |
| 2765 | Wipe (Right) |
| 2766 | Wipe (Bottom) |
| 27 | Fly In from Left |
| 26 | Fly In from Bottom |

---

## 9. File & Folder Structure

```
pptx-animator/
│
├── animate.py                  ← CLI entry point
│
├── .antigravity/
│   ├── rules.yaml              ← Main rulebook (Saad edits this)
│   ├── profiles/
│   │   ├── subtle.yaml
│   │   ├── balanced.yaml
│   │   └── dynamic.yaml
│   └── overrides.yaml          ← Optional: per-slide manual overrides
│
├── engine/
│   ├── __init__.py
│   ├── rules_loader.py         ← Reads & validates rules.yaml
│   ├── slide_analyzer.py       ← Detects slide type and elements
│   ├── animation_planner.py    ← Maps rules → AnimationPlan
│   ├── xml_injector.py         ← Writes OOXML into slide XML
│   └── output_writer.py        ← Saves file, logs summary
│
├── models/
│   ├── animation_plan.py       ← Dataclass: plan per slide
│   ├── element_type.py         ← Enum: TITLE, BODY, IMAGE, SHAPE, etc.
│   └── slide_type.py           ← Enum: TITLE_SLIDE, CONTENT, SECTION, etc.
│
├── tests/
│   ├── test_rules_loader.py
│   ├── test_slide_analyzer.py
│   ├── test_animation_planner.py
│   ├── test_xml_injector.py
│   └── fixtures/
│       ├── sample_simple.pptx
│       ├── sample_complex.pptx
│       └── sample_gamma_export.pptx
│
├── requirements.txt
├── README.md
└── SRS.md                      ← This document
```

---

## 10. Module Breakdown

### 10.1 `animate.py` — CLI Entry Point

**Responsibilities:** Parse CLI args, orchestrate the pipeline, handle top-level errors.

```
CLI Usage:
  python animate.py input.pptx
  python animate.py input.pptx output.pptx
  python animate.py input.pptx --profile subtle
  python animate.py input.pptx --dry-run
  python animate.py input.pptx --skip-slides 1,5
  python animate.py input.pptx --verbose
```

### 10.2 `engine/rules_loader.py`

**Responsibilities:** Load `.antigravity/rules.yaml`, merge with selected profile, validate schema, return a `RulesConfig` dataclass. Warn (not crash) on unknown keys.

### 10.3 `engine/slide_analyzer.py`

**Responsibilities:**  
- Open `.pptx` with `python-pptx`
- For each slide: detect slide type, enumerate all shapes
- Classify each shape: TITLE / SUBTITLE / BODY / IMAGE / SHAPE_ACCENT / SHAPE_CONTENT / GROUPED / TABLE / CHART / ICON
- Return list of `SlideAnalysis` objects

**Detection logic:**
- `Title` placeholder type → TITLE
- `Body` / `Object` placeholder with text → BODY
- `Picture` placeholder or image shape → IMAGE
- Shape with no text, small dimensions → SHAPE_ACCENT
- Shape with text, non-placeholder → SHAPE_CONTENT
- `GroupShapes` → GROUPED
- `Table` → TABLE
- `Chart` → CHART

### 10.4 `engine/animation_planner.py`

**Responsibilities:**  
- Takes `SlideAnalysis` + `RulesConfig`
- Applies rules in priority order (overrides → caps → slide rules → element rules → profile)
- Returns `AnimationPlan` per slide: ordered list of `(shape_id, animation_type, duration_ms, delay_ms)`

**Key logic:**
- Enforces `max_animations_per_slide` cap
- Skips slides with element count > `skip_if_too_many_elements`
- Refuses any animation in the `forbidden` list
- Only allows animations in the `allowed` list

### 10.5 `engine/xml_injector.py`

**Responsibilities:**  
- Takes a slide's XML element and an `AnimationPlan`
- Removes any existing `<p:timing>` block
- Builds new `<p:timing>` block from scratch using the plan
- Assigns sequential cTn IDs (must be globally unique per slide)
- Handles `by_paragraph` for body text (separate animation per `<a:p>`)
- Injects into slide XML

**Critical rules:**
- Never touch `<p:spTree>` (shape tree) — read-only for this module
- cTn `id` values must start at 1 and be unique per slide
- `spid` must match the actual shape's `id` attribute

### 10.6 `engine/output_writer.py`

**Responsibilities:**  
- Save the modified presentation to output path
- Check output file exists and is non-zero bytes
- Print a per-slide summary of animations applied
- On `--dry-run`, only print the summary without saving

---

## 11. Input / Output Specification

### 11.1 Input
- Any valid `.pptx` file (PowerPoint 2007+ Open XML format)
- Tested against: Gamma exports, Canva exports, native PowerPoint files, Google Slides exports
- Max tested size: 50MB / 60 slides

### 11.2 Output
- A `.pptx` file at the specified output path (default: `{input_name}_animated.pptx`)
- Identical content to input
- Additional `<p:timing>` blocks injected per slide
- Compatible with: Microsoft PowerPoint 2016+, Google Slides, LibreOffice Impress 7+

### 11.3 Log Output (stdout)

```
[PPTX Animator] Loading rules from .antigravity/rules.yaml
[PPTX Animator] Profile: balanced
[PPTX Animator] Analyzing: my_deck.pptx (12 slides)

  Slide 1 [title_slide]    → Title: fade(400ms), Subtitle: fade(400ms, +100ms)
  Slide 2 [content_slide]  → Title: fade(400ms), Body[3 bullets]: wipe_left(350ms each)
  Slide 3 [content_slide]  → Title: fade, Image: fade(600ms), Body: wipe_left
  Slide 4 [section_header] → Title: fade(600ms)
  Slide 5 [content_slide]  → Title: fade, Chart: wipe_bottom(700ms)
  ...
  Slide 12 [content_slide] → Title: fade, Body[2 bullets]: wipe_left

[PPTX Animator] Total animations injected: 47
[PPTX Animator] Output saved: my_deck_animated.pptx
```

---

## 12. Error Handling

| Scenario | Behavior |
|----------|----------|
| Input file not found | Exit with clear message: `Error: File not found: path/to/file.pptx` |
| Input is not a valid .pptx | Exit: `Error: Could not open file as a PowerPoint presentation` |
| rules.yaml missing | Warn and fall back to built-in balanced defaults |
| rules.yaml has invalid YAML | Exit: `Error: .antigravity/rules.yaml has invalid syntax at line N` |
| Shape has no `id` attribute | Skip shape, log warning |
| Output path is not writable | Exit: `Error: Cannot write to output path` |
| Output file already exists | Prompt: `Output exists. Overwrite? [y/N]` (unless `--overwrite` flag) |
| Slide has > `skip_if_too_many_elements` elements | Skip slide silently, log: `Slide N skipped (too complex)` |

---

## 13. Testing Plan

### 13.1 Unit Tests

| Test | What it checks |
|------|----------------|
| `test_rules_loader.py` | Valid YAML loads correctly; missing keys use defaults; invalid YAML raises error |
| `test_slide_analyzer.py` | Title slide detected; body text classified; images found; shapes classified |
| `test_animation_planner.py` | Cap enforced; forbidden animations rejected; correct animation assigned per element type |
| `test_xml_injector.py` | Output XML is valid; cTn IDs are unique; spid matches shape; existing timing removed |

### 13.2 Integration Tests

| Test File | What it tests |
|-----------|---------------|
| `fixtures/sample_simple.pptx` | 3-slide basic deck — core flow works end to end |
| `fixtures/sample_complex.pptx` | 20-slide complex deck — caps and edge cases |
| `fixtures/sample_gamma_export.pptx` | Gamma-exported file — real-world primary use case |

### 13.3 Manual Verification
After each build milestone, open the output in PowerPoint and:
- Play slideshow — verify animations trigger in correct order
- Check no text/images are missing
- Check no weird flickers or invisible elements
- Open in Google Slides — verify compatibility

---

## 14. Milestones (Solo Developer)

Saad works alone. These milestones are sized for realistic solo pacing.

| Milestone | What to build | Estimated time |
|-----------|---------------|---------------|
| M1: Skeleton | Project structure, CLI args, rules.yaml loading, basic logging | 1–2 days |
| M2: Analyzer | `slide_analyzer.py` — detect all element types correctly | 2–3 days |
| M3: Planner | `animation_planner.py` — apply rules, enforce caps | 2 days |
| M4: Injector | `xml_injector.py` — write valid OOXML, test in PowerPoint | 3–4 days |
| M5: Output + Polish | `output_writer.py`, dry-run, logging, error handling | 1–2 days |
| M6: Testing | Write all unit tests, integration tests, manual QA | 2–3 days |
| **Total** | | **~2–2.5 weeks** |

---

## 15. Glossary

| Term | Definition |
|------|------------|
| `.antigravity/` | Project config directory containing the animation rulebook |
| `rules.yaml` | YAML file defining all animation behavior — the brain of the engine |
| OOXML | Office Open XML — the XML-based format inside a `.pptx` file |
| `p:timing` | The OOXML element that contains all animation data for one slide |
| `p:animEffect` | OOXML element defining a single animation (fade, wipe, etc.) |
| `cTn` | Condition Timing Node — core OOXML animation building block |
| `spid` | Shape ID — unique integer identifying a shape within a slide |
| `presetID` | Integer code mapping to a named animation (e.g., 10 = Fade) |
| `by_paragraph` | Mode where each bullet point animates separately instead of all at once |
| AnimationPlan | Internal dataclass: ordered list of animations to apply to one slide |
| SlideAnalysis | Internal dataclass: element inventory of one slide |
| Profile | A named preset (subtle/balanced/dynamic) defining conservative vs. expressive defaults |
| Cap | A hard limit in rules.yaml that the engine always enforces (e.g., max 8 animations) |
| Dry Run | CLI mode that logs what would happen without writing any files |

---

*SRS v1.0 — Written for Saad. Build it once, build it right.*
