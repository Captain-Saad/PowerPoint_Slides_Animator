"""
engine/xml_injector.py
Writes OOXML animation blocks (<p:timing>) directly into slide XML.

Takes a python-pptx Slide object and an AnimationPlan, removes any
pre-existing <p:timing> element, and builds a fresh one from scratch
using the plan's AnimationEntry list.

Critical rules (SRS Section 10.5):
- NEVER touch <p:spTree> — read-only for this module
- cTn id values must start at 1 and be unique per slide
- spid must match the actual shape id attribute
- Handles by_paragraph (paragraph_index is not None) for body text
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from lxml import etree

from models.animation_plan import AnimationEntry, AnimationPlan

logger = logging.getLogger(__name__)

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _ptag(local: str) -> str:
    return f"{{{_P}}}{local}"


ANIMATION_PRESET_MAP = {
    "fade":              (10,   "fade",           0),
    "appear":            (1,    None,             0),
    "wipe_left":         (2764, "wipe(dir=left)", 0),
    "wipe_right":        (2765, "wipe(dir=right)",0),
    "wipe_bottom":       (2766, "wipe(dir=up)",   0),
    "fly_in_from_left":  (27,   None,             3),
    "fly_in_from_bottom":(26,   None,             8),
}


class XMLInjector:
    """Injects OOXML <p:timing> animation blocks into a slide."""

    def inject(self, slide: object, plan: AnimationPlan) -> None:
        if plan.skip or not plan.entries:
            logger.debug(
                "Slide %d: no animation injected (skip=%s, entries=%d)",
                plan.slide_number, plan.skip, len(plan.entries),
            )
            return

        for e in plan.entries:
            logger.debug(
                "  Entry shape_id=%-4s  type=%-20s  start=%-16s  delay=%s",
                e.shape_id, e.animation_type, e.start_condition, e.delay_ms,
            )

        sld_el = slide._element
        self._remove_existing_timing(sld_el)
        timing_el = self._build_timing_element(plan.entries)
        sld_el.append(timing_el)
        logger.debug(
            "Slide %d: injected %d animation entries",
            plan.slide_number, len(plan.entries),
        )

    def _remove_existing_timing(self, slide_element: object) -> None:
        for child in list(slide_element):
            if child.tag == _ptag("timing"):
                slide_element.remove(child)

    def _build_timing_element(self, entries: List[AnimationEntry]) -> object:
        """Build a complete <p:timing> element.

        Proven auto-play structure (verified against reference PPTX):

        RULE 1 — First entry outer stCondLst must be:
            <p:cond evt="begin" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>
            Fires automatically when the slide begins.

        RULE 2 — All subsequent entries outer stCondLst must be:
            <p:cond evt="endSync" delay="0"><p:tgtEl><p:spTgt spid="0"/></p:tgtEl></p:cond>
            spid="0" means "previous animation". Chains automatically.

        RULE 3 — No <p:set style.visibility> block.
            Shapes are visible by default. The set block hides them first,
            then reveals on animation — if timing is off, shapes stay invisible.
            The animEffect alone is sufficient for fade/wipe/fly-in animations.
        """
        timing = etree.Element(_ptag("timing"))

        tnLst    = etree.SubElement(timing,   _ptag("tnLst"))
        root_par = etree.SubElement(tnLst,    _ptag("par"))
        root_cTn = etree.SubElement(root_par, _ptag("cTn"))
        root_cTn.set("id",       "1")
        root_cTn.set("dur",      "indefinite")
        root_cTn.set("restart",  "never")
        root_cTn.set("nodeType", "tmRoot")
        root_child = etree.SubElement(root_cTn, _ptag("childTnLst"))

        seq = etree.SubElement(root_child, _ptag("seq"))
        seq.set("concurrent", "1")
        seq.set("nextAc",     "seek")

        main_cTn = etree.SubElement(seq, _ptag("cTn"))
        main_cTn.set("id",       "2")
        main_cTn.set("dur",      "indefinite")
        main_cTn.set("nodeType", "mainSeq")

        seq_child = etree.SubElement(main_cTn, _ptag("childTnLst"))

        ctn_id = 3
        for idx, entry in enumerate(entries):
            par_el, ctn_id = self._build_entry_par(entry, ctn_id, is_first=(idx == 0))
            seq_child.append(par_el)

        self._append_nav_conditions(seq)
        self._append_build_list(timing, entries)

        return timing

    def _append_nav_conditions(self, seq_el: object) -> None:
        prev_lst  = etree.SubElement(seq_el, _ptag("prevCondLst"))
        prev_cond = etree.SubElement(prev_lst, _ptag("cond"))
        prev_cond.set("evt",   "onPrev")
        prev_cond.set("delay", "0")
        etree.SubElement(prev_cond, _ptag("tgtEl")).append(
            etree.Element(_ptag("sldTgt"))
        )
        next_lst  = etree.SubElement(seq_el, _ptag("nextCondLst"))
        next_cond = etree.SubElement(next_lst, _ptag("cond"))
        next_cond.set("evt",   "onNext")
        next_cond.set("delay", "0")
        etree.SubElement(next_cond, _ptag("tgtEl")).append(
            etree.Element(_ptag("sldTgt"))
        )

    def _append_build_list(
        self, timing_el: object, entries: List[AnimationEntry]
    ) -> None:
        bldLst     = etree.SubElement(timing_el, _ptag("bldLst"))
        seen_spids: set = set()
        for entry in entries:
            spid = str(entry.shape_id)
            if spid in seen_spids:
                if entry.paragraph_index is not None:
                    for child in bldLst:
                        if child.get("spid") == spid:
                            child.set("bld", "p")
                continue
            seen_spids.add(spid)
            bldP = etree.SubElement(bldLst, _ptag("bldP"))
            bldP.set("spid",  spid)
            bldP.set("grpId", "0")
            if entry.paragraph_index is not None:
                bldP.set("bld", "p")

    def _build_entry_par(
        self,
        entry: AnimationEntry,
        ctn_id_start: int,
        is_first: bool,
    ) -> Tuple[etree.Element, int]:
        """Build three-level <p:par> for one animation entry.

        Outer stCondLst:
          - First entry:  evt="begin"   → sldTgt   (auto-start on slide open)
          - Others:       evt="endSync" → spTgt spid="0"  (chain from previous)

        Inner stCondLst:
          - delay_ms: the gap between this and the previous animation finishing.
        """
        outer_id = ctn_id_start
        mid_id   = ctn_id_start + 1
        inner_id = ctn_id_start + 2

        preset_id            = self._get_preset_id(entry.animation_type)
        _, _, preset_subtype = ANIMATION_PRESET_MAP[entry.animation_type]
        total_slot_dur       = entry.delay_ms + entry.duration_ms

        inner_node_type = {
            "after_previous": "afterEffect",
            "with_previous":  "withEffect",
            "click":          "afterEffect",
        }.get(entry.start_condition, "afterEffect")

        # ── OUTER par ────────────────────────────────────────────────────────
        outer_par = etree.Element(_ptag("par"))
        outer_cTn = etree.SubElement(outer_par, _ptag("cTn"))
        outer_cTn.set("id",   str(outer_id))
        outer_cTn.set("dur",  str(total_slot_dur))
        outer_cTn.set("fill", "hold")

        outer_stCond = etree.SubElement(outer_cTn, _ptag("stCondLst"))
        if is_first:
            cond = etree.SubElement(outer_stCond, _ptag("cond"))
            cond.set("evt",   "begin")
            cond.set("delay", "0")
            tgt = etree.SubElement(cond, _ptag("tgtEl"))
            etree.SubElement(tgt, _ptag("sldTgt"))
        else:
            cond = etree.SubElement(outer_stCond, _ptag("cond"))
            cond.set("evt",   "endSync")
            cond.set("delay", "0")
            tgt    = etree.SubElement(cond, _ptag("tgtEl"))
            spTgt0 = etree.SubElement(tgt,  _ptag("spTgt"))
            spTgt0.set("spid", "0")

        outer_child = etree.SubElement(outer_cTn, _ptag("childTnLst"))

        # ── MIDDLE par ───────────────────────────────────────────────────────
        mid_par = etree.SubElement(outer_child, _ptag("par"))
        mid_cTn = etree.SubElement(mid_par, _ptag("cTn"))
        mid_cTn.set("id",   str(mid_id))
        mid_cTn.set("fill", "hold")
        mid_stCond = etree.SubElement(mid_cTn, _ptag("stCondLst"))
        etree.SubElement(mid_stCond, _ptag("cond")).set("delay", "0")
        mid_child = etree.SubElement(mid_cTn, _ptag("childTnLst"))

        # ── INNER par ────────────────────────────────────────────────────────
        inner_par = etree.SubElement(mid_child, _ptag("par"))
        inner_cTn = etree.SubElement(inner_par, _ptag("cTn"))
        inner_cTn.set("id",            str(inner_id))
        inner_cTn.set("fill",          "hold")
        inner_cTn.set("presetID",      str(preset_id))
        inner_cTn.set("presetClass",   "entr")
        inner_cTn.set("presetSubtype", str(preset_subtype))
        inner_cTn.set("grpId",         "0")
        inner_cTn.set("nodeType",      inner_node_type)

        inner_stCond = etree.SubElement(inner_cTn, _ptag("stCondLst"))
        etree.SubElement(inner_stCond, _ptag("cond")).set(
            "delay", str(entry.delay_ms)
        )
        inner_child = etree.SubElement(inner_cTn, _ptag("childTnLst"))

        next_id = self._append_anim_children(inner_child, entry, inner_id + 1)

        return outer_par, next_id

    def _append_anim_children(
        self, parent: object, entry: AnimationEntry, ctn_id: int
    ) -> int:
        """Append animEffect child only — no visibility set.

        The <p:set style.visibility> pattern (hide-then-reveal) was removed
        because it causes shapes to be invisible if the timing engine
        misreads the condition. Shapes are visible by default in PPTX;
        the animEffect alone produces the correct fade/wipe/fly-in effect.

        'appear' gets no animEffect since it is an instant show with no motion.
        """
        spid = str(entry.shape_id)

        if entry.animation_type == "appear":
            # 'appear' is instant — no animEffect needed, shape is visible by default
            return ctn_id

        _, filt, _ = ANIMATION_PRESET_MAP[entry.animation_type]
        anim_eff = etree.SubElement(parent, _ptag("animEffect"))
        anim_eff.set("transition", "in")
        if filt:
            anim_eff.set("filter", filt)

        ae_cBhvr = etree.SubElement(anim_eff, _ptag("cBhvr"))
        ae_cTn   = etree.SubElement(ae_cBhvr, _ptag("cTn"))
        ae_cTn.set("id",  str(ctn_id))
        ae_cTn.set("dur", str(entry.duration_ms))
        ctn_id += 1

        ae_tgtEl = etree.SubElement(ae_cBhvr, _ptag("tgtEl"))
        ae_spTgt = etree.SubElement(ae_tgtEl, _ptag("spTgt"))
        ae_spTgt.set("spid", spid)
        if entry.paragraph_index is not None:
            self._add_para_target(ae_spTgt, entry.paragraph_index)

        return ctn_id

    def _add_para_target(
        self, spTgt: etree.Element, para_idx: int, whole_box: bool = False
    ) -> None:
        txEl   = etree.SubElement(spTgt, _ptag("txEl"))
        charRg = etree.SubElement(txEl,  _ptag("charRg"))
        charRg.set("st",  str(para_idx))
        charRg.set("end", "1073741823" if whole_box else str(para_idx))

    def _get_preset_id(self, animation_type: str) -> int:
        entry = ANIMATION_PRESET_MAP.get(animation_type)
        if entry is None:
            raise ValueError(
                f"Unknown animation type: {animation_type!r}. "
                f"Valid: {list(ANIMATION_PRESET_MAP)}"
            )
        return entry[0]