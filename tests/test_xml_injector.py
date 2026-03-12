"""
tests/test_xml_injector.py
Unit tests for engine/xml_injector.py.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest
from lxml import etree
from pptx import Presentation
from pptx.util import Inches

from engine.xml_injector import XMLInjector, ANIMATION_PRESET_MAP, _ptag
from models.animation_plan import AnimationEntry, AnimationPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _make_single_slide_prs() -> Presentation:
    """Return a Presentation with one blank slide."""
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    return prs


def _entry(
    shape_id: int = 5,
    anim: str = "fade",
    dur: int = 400,
    delay: int = 0,
    para_idx=None,
) -> AnimationEntry:
    """Convenience factory for AnimationEntry."""
    return AnimationEntry(
        shape_id=shape_id,
        animation_type=anim,
        duration_ms=dur,
        delay_ms=delay,
        paragraph_index=para_idx,
        start_condition="after_previous",
    )


def _plan(*entries, slide_number=1, skip=False) -> AnimationPlan:
    """Convenience factory for AnimationPlan."""
    return AnimationPlan(
        slide_index=0,
        slide_number=slide_number,
        skip=skip,
        entries=list(entries),
    )


def _get_timing(slide) -> object:
    """Return the <p:timing> element from a slide, or None."""
    sld_el = slide._element
    for child in sld_el:
        if child.tag == _ptag("timing"):
            return child
    return None


def _all_ctn_ids(timing_el) -> list:
    """Collect all cTn id attribute values from a timing element."""
    return [el.get("id") for el in timing_el.iter(_ptag("cTn"))]


def _all_spids(timing_el) -> list:
    """Collect all spTgt spid values from a timing element."""
    return [el.get("spid") for el in timing_el.iter(_ptag("spTgt"))]


# ---------------------------------------------------------------------------
# Tests: inject() skip behaviour
# ---------------------------------------------------------------------------

class TestInjectSkip:
    """inject() is a no-op when the plan is skipped or has no entries."""

    def test_skip_plan_does_not_insert_timing(self):
        """Plan with skip=True leaves slide XML untouched."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        injector = XMLInjector()
        injector.inject(slide, _plan(skip=True))
        assert _get_timing(slide) is None

    def test_empty_entries_does_not_insert_timing(self):
        """Plan with no entries does not insert <p:timing>."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        injector = XMLInjector()
        injector.inject(slide, _plan())
        assert _get_timing(slide) is None


# ---------------------------------------------------------------------------
# Tests: <p:timing> structure
# ---------------------------------------------------------------------------

class TestTimingStructure:
    """Tests that the generated <p:timing> element is structurally valid."""

    def test_timing_element_inserted(self):
        """After inject(), slide XML contains exactly one <p:timing>."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        injector = XMLInjector()
        injector.inject(slide, _plan(_entry()))
        timing = _get_timing(slide)
        assert timing is not None

    def test_existing_timing_replaced(self):
        """Pre-existing <p:timing> is removed and replaced — only one remains."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        injector = XMLInjector()
        injector.inject(slide, _plan(_entry(shape_id=1)))
        injector.inject(slide, _plan(_entry(shape_id=2)))  # second inject
        # Count actual <p:timing> children
        sld_el = slide._element
        timings = [c for c in sld_el if c.tag == _ptag("timing")]
        assert len(timings) == 1

    def test_main_seq_node_present(self):
        """The timing block contains a <p:cTn nodeType=mainSeq>."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry()))
        timing = _get_timing(slide)
        main_seqs = [
            el for el in timing.iter(_ptag("cTn"))
            if el.get("nodeType") == "mainSeq"
        ]
        assert len(main_seqs) == 1

    def test_prev_and_next_cond_lists_present(self):
        """The <p:seq> contains prevCondLst and nextCondLst."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry()))
        timing = _get_timing(slide)
        assert timing.find(f".//{_ptag('prevCondLst')}") is not None
        assert timing.find(f".//{_ptag('nextCondLst')}") is not None


# ---------------------------------------------------------------------------
# Tests: cTn ID uniqueness and sequencing
# ---------------------------------------------------------------------------

class TestCtnIds:
    """Tests for cTn id correctness."""

    def test_ctn_ids_start_at_one(self):
        """The first cTn element has id='1'."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry()))
        timing = _get_timing(slide)
        ids = _all_ctn_ids(timing)
        assert ids[0] == "1"

    def test_all_ctn_ids_unique(self):
        """No two cTn elements share the same id."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(
            _entry(shape_id=1), _entry(shape_id=2), _entry(shape_id=3)
        ))
        timing = _get_timing(slide)
        ids = _all_ctn_ids(timing)
        assert len(ids) == len(set(ids))

    def test_ctn_ids_are_sequential(self):
        """cTn ids are sequential integers with no gaps."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(shape_id=1), _entry(shape_id=2)))
        timing = _get_timing(slide)
        ids = [int(i) for i in _all_ctn_ids(timing)]
        expected = list(range(1, max(ids) + 1))
        assert ids == expected


# ---------------------------------------------------------------------------
# Tests: spid mapping
# ---------------------------------------------------------------------------

class TestSpidMapping:
    """Tests that spTgt spid values match AnimationEntry.shape_id."""

    def test_spid_matches_entry_shape_id(self):
        """A single entry's shape_id maps to the correct spTgt spid."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(shape_id=42)))
        timing = _get_timing(slide)
        spids = _all_spids(timing)
        assert "42" in spids

    def test_multiple_entries_all_spids_present(self):
        """Multiple entries: all spids appear in the XML."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(
            _entry(shape_id=7), _entry(shape_id=8), _entry(shape_id=9)
        ))
        timing = _get_timing(slide)
        spids = set(_all_spids(timing))
        assert {"7", "8", "9"}.issubset(spids)


# ---------------------------------------------------------------------------
# Tests: animation type attributes
# ---------------------------------------------------------------------------

class TestAnimationTypes:
    """Tests that the correct OOXML attributes are set per animation type."""

    @pytest.mark.parametrize("anim,expected_preset", [
        ("fade", "10"),
        ("appear", "1"),
        ("wipe_left", "2764"),
        ("wipe_right", "2765"),
        ("wipe_bottom", "2766"),
        ("fly_in_from_left", "27"),
        ("fly_in_from_bottom", "26"),
    ])
    def test_preset_id_for_animation(self, anim, expected_preset):
        """Each animation name maps to the correct OOXML presetID."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(anim=anim)))
        timing = _get_timing(slide)
        preset_ids = [
            el.get("presetID")
            for el in timing.iter(_ptag("cTn"))
            if el.get("presetID")
        ]
        assert expected_preset in preset_ids

    def test_fade_has_anim_effect(self):
        """A 'fade' animation has an <p:animEffect filter='fade'> element."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(anim="fade")))
        timing = _get_timing(slide)
        anim_effs = list(timing.iter(_ptag("animEffect")))
        assert len(anim_effs) >= 1
        assert anim_effs[0].get("filter") == "fade"

    def test_appear_has_no_anim_effect(self):
        """An 'appear' animation has no <p:animEffect> (instant visibility)."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(anim="appear")))
        timing = _get_timing(slide)
        anim_effs = list(timing.iter(_ptag("animEffect")))
        assert len(anim_effs) == 0

    def test_duration_in_anim_effect(self):
        """animEffect <p:cTn dur> matches duration_ms of the entry."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(anim="wipe_left", dur=350)))
        timing = _get_timing(slide)
        anim_effs = list(timing.iter(_ptag("animEffect")))
        ae_cTn = anim_effs[0].find(_ptag("cBhvr") + "/" + _ptag("cTn"))
        # Use find with explicit tag
        for el in anim_effs[0].iter(_ptag("cTn")):
            assert el.get("dur") == "350"
            break


# ---------------------------------------------------------------------------
# Tests: paragraph targeting
# ---------------------------------------------------------------------------

class TestParagraphTargeting:
    """Tests for by_paragraph txEl targeting."""

    def test_para_index_adds_tx_el(self):
        """An entry with paragraph_index produces a <p:txEl> in its spTgt."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(para_idx=1)))
        timing = _get_timing(slide)
        tx_els = list(timing.iter(_ptag("txEl")))
        assert len(tx_els) >= 1

    def test_none_para_index_no_tx_el(self):
        """An entry with paragraph_index=None produces no <p:txEl>."""
        prs = _make_single_slide_prs()
        slide = prs.slides[0]
        XMLInjector().inject(slide, _plan(_entry(para_idx=None)))
        timing = _get_timing(slide)
        tx_els = list(timing.iter(_ptag("txEl")))
        assert len(tx_els) == 0


# ---------------------------------------------------------------------------
# Tests: get_preset_id errors
# ---------------------------------------------------------------------------

class TestGetPresetId:
    """Tests for _get_preset_id error handling."""

    def test_unknown_animation_raises_value_error(self):
        """_get_preset_id raises ValueError for unknown animation names."""
        injector = XMLInjector()
        with pytest.raises(ValueError, match="Unknown animation type"):
            injector._get_preset_id("bounce")  # forbidden, not in map
