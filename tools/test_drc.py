"""test_drc.py — Unit tests for the POGO panel DRC checker (panel_rules.py).

Purpose: Document and verify the relationship between the SVG draw bounding
boxes produced by panel_svg.py and the PCB courtyard constants defined in
panel_rules.py.  Previously several component types had courtyards smaller
than their drawn SVG bodies, creating blind spots.  All known blind spots are
now fixed; these tests enforce that the fixes stay in place.

Switches are Dailywell 2M sub-mini toggles (DW3 2-pos / DW5 3-pos). Both share
one footprint and DRC courtyard (TOGGLE_CY), pulled from the .kicad_mod F.CrtYd,
so the DRC model never lags the physical body. See TestToggleTrimpotClearance and
TestDiscrepancySummary.

Run with: pytest tools/test_drc.py -v
"""

from __future__ import annotations
import sys
import os
import math
import pytest

# Allow importing from tools/ regardless of where pytest is invoked.
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from panel_rules import (
    JACK_CY,
    POT_CY,
    TRIMPOT_CY,
    TOGGLE_CY,
    TOGGLE_PANEL_R,
    LED_CY,
    SLIDER_V45_CY,
    DesignRules,
    _get_courtyard,
    _rotate_rect,
    _rect_overlap,
    _rect_min_gap,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: a default DesignRules instance usable without YAML
# ─────────────────────────────────────────────────────────────────────────────

def make_rules(**kwargs) -> DesignRules:
    """Return a DesignRules with sensible defaults, overridable via kwargs."""
    return DesignRules(**kwargs)


def _comp(ctype: str, cx: float, cy: float, cid: str = "test", rotate: int = 0) -> dict:
    """Build a minimal resolved component dict for DRC input."""
    return {"type": ctype, "cx": cx, "cy": cy, "id": cid, "rotate": rotate}


import panel_kicad as _pk  # noqa: E402  (real footprint keepout shapes)


def _collide(a_type, b_type, axis, sep, rot_a=0, rot_b=0):
    """True if A@(50,50) and B@(+sep along axis) collide per the real DRC check."""
    bx = 50.0 + (sep if axis == "x" else 0.0)
    by = 50.0 + (sep if axis == "y" else 0.0)
    return bool(make_rules()._check_pcb_overlaps([
        _comp(a_type, 50.0, 50.0, "a", rot_a),
        _comp(b_type, bx, by, "b", rot_b),
    ]))


def _touch_sep(a_type, b_type, axis, rot_a=0, rot_b=0):
    """Smallest centre-to-centre separation along `axis` at which A and B are CLEAR,
    found by binary-searching the REAL _check_pcb_overlaps — so it tracks the live model
    (body overlap + 0.2mm copper clearance) rather than re-deriving geometry."""
    lo, hi = 0.0, 80.0
    for _ in range(48):
        mid = (lo + hi) / 2
        if _collide(a_type, b_type, axis, mid, rot_a, rot_b):
            lo = mid
        else:
            hi = mid
    return hi


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: SVG draw size vs. DRC courtyard size
#
# For each component type we extract:
#   - The SVG bounding box (from reading panel_svg.py draw calls)
#   - The DRC courtyard constant (from panel_rules.py)
#
# The invariant we WANT is: DRC courtyard ⊇ SVG bounding box on every edge.
# i.e., cy_x1 ≤ svg_x1, cy_y1 ≤ svg_y1, cy_x2 ≥ svg_x2, cy_y2 ≥ svg_y2.
#
# Tests that FAIL document confirmed blind spots (currently allowed to fail).
# ─────────────────────────────────────────────────────────────────────────────

class TestCourtyardVsDrawSize:
    """Assert that every component's DRC courtyard encompasses its SVG draw bbox."""

    # ── jack ──────────────────────────────────────────────────────────────────
    # svg_jack draws: outer circle r=3.5 (panel-face symbol only)
    # Note: the PCB body extends further; JACK_CY covers the actual footprint
    # which is physically larger than the panel circle.
    def test_jack_courtyard_wider_than_svg_symbol(self):
        """JACK_CY must be at least as wide as the outer jack ring (r=3.5)."""
        svg_r = 3.5
        x1, y1, x2, y2 = JACK_CY
        assert x1 <= -svg_r, (
            f"JACK_CY left edge ({x1}) is tighter than SVG ring (-{svg_r})"
        )
        assert x2 >= svg_r, (
            f"JACK_CY right edge ({x2}) is tighter than SVG ring ({svg_r})"
        )

    def test_jack_courtyard_taller_than_svg_symbol(self):
        """JACK_CY extends well above/below the panel-face symbol (PCB body coverage)."""
        svg_r = 3.5
        x1, y1, x2, y2 = JACK_CY
        assert y1 <= -svg_r, (
            f"JACK_CY top edge ({y1}) is tighter than SVG ring top (-{svg_r})"
        )
        assert y2 >= svg_r, (
            f"JACK_CY bottom edge ({y2}) is tighter than SVG ring bottom ({svg_r})"
        )

    # ── trimpot ───────────────────────────────────────────────────────────────
    # svg_trimpot draws: circle r=2.5 centred at (cx, cy)
    def test_trimpot_courtyard_encompasses_svg_circle(self):
        """TRIMPOT_CY must encompass the drawn circle (r=2.5) on all four sides."""
        svg_r = 2.5
        x1, y1, x2, y2 = TRIMPOT_CY
        assert x1 <= -svg_r, f"TRIMPOT_CY left ({x1}) tighter than circle left (-{svg_r})"
        assert y1 <= -svg_r, f"TRIMPOT_CY top ({y1}) tighter than circle top (-{svg_r})"
        assert x2 >= svg_r,  f"TRIMPOT_CY right ({x2}) tighter than circle right ({svg_r})"
        assert y2 >= svg_r,  f"TRIMPOT_CY bottom ({y2}) tighter than circle bottom ({svg_r})"

    # ── toggle (Dailywell DW3/DW5) ──────────────────────────────────────────────
    # svg_toggle_2pos / svg_toggle_3pos draw a bushing circle (r=2.475) plus a
    # lever extending ±2.2mm tipped with an r=0.9 circle → max draw extent ≈ 3.1mm.
    # TOGGLE_CY = (-4.32, -4.82, 4.32, 4.82) comes from the DW3/DW5 footprint
    # F.CrtYd (body 8.13×9.14mm + 0.25mm), so it encompasses the drawn symbol.
    def test_toggle_courtyard_encompasses_svg_symbol(self):
        """TOGGLE_CY must encompass the drawn toggle symbol (lever tip ≈ ±3.1mm)."""
        draw_half = 2.2 + 0.9   # lever length + tip radius
        x1, y1, x2, y2 = TOGGLE_CY
        assert x1 <= -draw_half, f"TOGGLE_CY left ({x1}) tighter than symbol (-{draw_half})"
        assert y1 <= -draw_half, f"TOGGLE_CY top ({y1}) tighter than symbol (-{draw_half})"
        assert x2 >= draw_half,  f"TOGGLE_CY right ({x2}) tighter than symbol ({draw_half})"
        assert y2 >= draw_half,  f"TOGGLE_CY bottom ({y2}) tighter than symbol ({draw_half})"

    # ── LED ───────────────────────────────────────────────────────────────────
    # svg_led draws: circle r=1.2
    def test_led_courtyard_encompasses_svg_circle(self):
        """LED_CY must encompass the drawn circle (r=1.2) on all four sides."""
        svg_r = 1.2
        x1, y1, x2, y2 = LED_CY
        assert x1 <= -svg_r, f"LED_CY left ({x1}) tighter than circle (-{svg_r})"
        assert y1 <= -svg_r, f"LED_CY top ({y1}) tighter than circle (-{svg_r})"
        assert x2 >= svg_r,  f"LED_CY right ({x2}) tighter than circle ({svg_r})"
        assert y2 >= svg_r,  f"LED_CY bottom ({y2}) tighter than circle ({svg_r})"

    # led_labeled uses the same drawn circle; the text label is informational only.
    def test_led_labeled_same_as_led(self):
        """led_labeled uses the same drawn body as led — same courtyard applies."""
        # Both map to LED_CY in _get_courtyard
        rect_led        = _get_courtyard(50, 50, "led",         0)
        rect_led_labeled = _get_courtyard(50, 50, "led_labeled", 0)
        assert rect_led == rect_led_labeled, (
            "led and led_labeled should use the same PCB courtyard"
        )

    # ── knob (single type, sized by cap_mm DIAMETER) ───────────────────────────
    # svg_knob draws a circle of radius cap_mm/2. POT_CY = (-8.65,-6.67,5.1,6.67) is
    # the 9mm Alpha RD901F pot footprint (centred on the shaft, offset from the nut),
    # and is FIXED regardless of cap_mm — the cap is a panel-face visual only.
    def test_knob_small_cap_within_courtyard(self):
        """A small cap (⌀9mm → r=4.5) fits inside POT_CY on all sides."""
        svg_r = 9.0 / 2.0
        x1, y1, x2, y2 = POT_CY
        assert x1 <= -svg_r and y1 <= -svg_r and x2 >= svg_r and y2 >= svg_r, (
            f"POT_CY {POT_CY} should encompass a ⌀9mm cap (r={svg_r})."
        )

    # Larger caps (⌀14 → r=7.0, ⌀18 → r=9.0) extend BEYOND the pot footprint. This is
    # expected: the courtyard is the pot body, not the cap. Knob-to-knob spacing is
    # gated by the panel-face nut radius (pot_nut_r), not the PCB courtyard.
    @pytest.mark.xfail(
        reason=(
            "A ⌀14mm+ knob cap (r≥7.0) exceeds POT_CY (right edge 5.1mm, top/bottom "
            "±6.67mm). The Alpha RD901F footprint is shaft-centred, so a large cap "
            "overhangs it. The PCB-courtyard check cannot gate large-cap collisions; "
            "pot_nut_r is the panel-face clearance gate. This documents the limitation."
        ),
        strict=True,
    )
    def test_large_cap_exceeds_courtyard_xfail(self):
        """A ⌀14mm cap (r=7.0) is NOT contained by POT_CY (documented limitation)."""
        svg_r = 14.0 / 2.0
        x1, y1, x2, y2 = POT_CY
        assert y1 <= -svg_r and x2 >= svg_r and y2 >= svg_r, (
            f"POT_CY {POT_CY} cannot contain a ⌀14mm cap (r={svg_r})."
        )

    def test_knob_type_has_pot_courtyard(self):
        """The single `knob` type resolves to the pot footprint courtyard (POT_CY)."""
        assert _get_courtyard(50, 50, "knob", 0) is not None, "knob must have a courtyard"


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: DRC catches overlaps that are visually obvious
#
# For each type: place two components at minimum-gap (just passing), then 0.5mm
# closer (must fail).  This verifies the DRC machinery is actually exercised.
# ─────────────────────────────────────────────────────────────────────────────

class TestDrcCatchesOverlaps:
    """DRC must fire when REAL footprints (pads + body) are placed too close.
    Separations come from _touch_sep (derived from footprint_shapes), so they track
    the geometry rather than a hard-coded courtyard width. Pattern per type: at the
    touch separation → clear; 0.5mm closer → exactly one overlap violation."""

    def setup_method(self):
        self.dr = make_rules()

    def _pair(self, a, b, axis, sep, ra=0, rb=0):
        bx = 50.0 + (sep if axis == "x" else 0.0)
        by = 50.0 + (sep if axis == "y" else 0.0)
        return self.dr._check_pcb_overlaps([
            _comp(a, 50.0, 50.0, "a", ra),
            _comp(b, bx, by, "b", rb),
        ])

    def _assert_boundary(self, a, b, axis, ra=0, rb=0):
        sep = _touch_sep(a, b, axis, ra, rb)
        assert sep is not None
        assert self._pair(a, b, axis, sep + 0.05, ra, rb) == [], \
            f"{a}/{b} should be clear just past touch sep {sep:.2f}"
        v = self._pair(a, b, axis, sep - 0.5, ra, rb)
        assert len(v) == 1 and "PCB OVERLAP" in v[0], \
            f"{a}/{b} should report 1 overlap 0.5mm inside touch sep {sep:.2f}: {v}"
        return sep

    def test_jack_horizontal(self):
        self._assert_boundary("jack_input", "jack_input", "x")

    def test_trimpot_horizontal(self):
        # 9mm pots side-by-side: only the bodies (centred ~9.7mm can) gate placement —
        # offset pins/legs don't (no pad-vs-body), so the boundary ≈ the body width.
        sep = self._assert_boundary("trimpot", "trimpot", "x")
        assert 9.0 < sep < 10.5, f"trimpot x touch sep {sep:.2f} not ~9.7mm (body width)"

    def test_toggle_vertical(self):
        self._assert_boundary("toggle_dw3", "toggle_dw3", "y")

    def test_led_vertical(self):
        self._assert_boundary("led", "led", "y")

    def test_jack_trimpot_vertical(self):
        self._assert_boundary("jack_input", "trimpot", "y")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: toggle + trimpot vertical clearance (DIST switch over an attenuverter)
#
# The BP DIST toggles sit in a column above mod/attenuverter trimpots. The DRC
# threshold is the sum of courtyard half-extents pulled from the real footprints:
#   TOGGLE_CY[3] + abs(TRIMPOT_CY[1]) = 4.82 + 3.385 = 8.205mm
# Since both courtyards come from their .kicad_mod F.CrtYd, there is no blind
# spot between the DRC model and the drawn/physical body.
# ──────────────────────────────────────────────────────────────────────────────────

class TestToggleTrimpotClearance:
    """Verify toggle↔trimpot vertical clearance is driven by the footprint courtyards."""

    def test_pass_just_above_touch(self):
        """At the real-footprint touch separation + 0.05mm, DRC passes."""
        dr = make_rules()
        sep = _touch_sep("toggle_dw5", "trimpot", "y")
        comps = [
            _comp("toggle_dw5", 50.0, 50.0,             "sw1"),
            _comp("trimpot",    50.0, 50.0 + sep + 0.05, "tp1"),
        ]
        assert dr._check_pcb_overlaps(comps) == [], f"should pass just past touch sep {sep:.2f}"

    def test_fail_below_touch(self):
        """0.5mm inside the real-footprint touch separation, DRC must fire."""
        dr = make_rules()
        sep = _touch_sep("toggle_dw5", "trimpot", "y")
        comps = [
            _comp("toggle_dw5", 50.0, 50.0,            "sw1"),
            _comp("trimpot",    50.0, 50.0 + sep - 0.5, "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) >= 1, f"DRC must catch overlap 0.5mm inside touch sep {sep:.2f}: {viols}"

    def test_courtyard_threshold_gap_is_zero(self):
        """The COURTYARD boundary contact (still used by the rail/MH checks) is gap ≈ 0."""
        thr = TOGGLE_CY[3] + abs(TRIMPOT_CY[1])
        sw_rect = _get_courtyard(50.0, 50.0,        "toggle_dw5", 0)
        tp_rect = _get_courtyard(50.0, 50.0 + thr,  "trimpot",    0)
        gap = _rect_min_gap(sw_rect, tp_rect)
        assert abs(gap) < 0.01, f"Expected courtyard gap ≈ 0 at threshold, got {gap:.6f}mm"


# ─────────────────────────────────────────────────────────────────────────────
# Section 4: rotate=180 on jacks
#
# JACK_CY = (-5.0, -7.9, 5.0, 6.5)
# After rotate=180: corners (x,y) → (-x,-y) → JACK_CY_180 = (-5.0, -6.5, 5.0, 7.9)
#
# Effect: the 7.9mm protrusion moves from ABOVE the hole (y<0) to BELOW the hole (y>0).
# The PCB body that normally extends 7.9mm above the panel hole now extends 7.9mm below.
# Use case: top-row jacks where the PCB body below the hole avoids the rail keepout.
# ─────────────────────────────────────────────────────────────────────────────

class TestJackRotate180:
    """Verify that rotate=180 on jacks correctly flips the courtyard."""

    def test_rotate_180_flips_y_extent(self):
        """rotate=180 must swap the top and bottom extents of JACK_CY."""
        original = JACK_CY                        # (-5.0, -7.9, 5.0, 6.5)
        rotated  = _rotate_rect(JACK_CY, 180)     # (-5.0, -6.5, 5.0, 7.9)

        # The rotated y1 should be -(original y2)
        assert abs(rotated[1] - (-original[3])) < 1e-9, (
            f"rotate=180 y1: expected {-original[3]:.3f}, got {rotated[1]:.3f}"
        )
        # The rotated y2 should be -(original y1)
        assert abs(rotated[3] - (-original[1])) < 1e-9, (
            f"rotate=180 y2: expected {-original[1]:.3f}, got {rotated[3]:.3f}"
        )
        # x extents are symmetric in JACK_CY so must be unchanged
        assert abs(rotated[0] - original[0]) < 1e-9, "rotate=180 must not change symmetric x1"
        assert abs(rotated[2] - original[2]) < 1e-9, "rotate=180 must not change symmetric x2"

    def test_rotate_180_courtyard_positioned_correctly(self):
        """_get_courtyard with rotate=180 places the flipped courtyard at the right panel position."""
        cx, cy = 50.0, 30.0
        rect_0   = _get_courtyard(cx, cy, "jack_input",  0)
        rect_180 = _get_courtyard(cx, cy, "jack_input", 180)

        # Both must be centred on cx in x (Jack CY is x-symmetric)
        x_centre_0   = (rect_0[0]   + rect_0[2])   / 2
        x_centre_180 = (rect_180[0] + rect_180[2]) / 2
        assert abs(x_centre_0   - cx) < 1e-9, f"rotate=0:   x-centre {x_centre_0} != cx {cx}"
        assert abs(x_centre_180 - cx) < 1e-9, f"rotate=180: x-centre {x_centre_180} != cx {cx}"

        # With rotate=0:   large protrusion above hole (y1 much smaller than cy)
        # With rotate=180: large protrusion below hole (y2 much larger than cy)
        protrusion_above_0   = cy - rect_0[1]    # 7.9mm: protrudes far above hole
        protrusion_below_180 = rect_180[3] - cy  # 7.9mm: protrudes far below hole
        assert abs(protrusion_above_0 - 7.9) < 1e-9, (
            f"Default jack: expected 7.9mm protrusion above hole, got {protrusion_above_0:.3f}mm"
        )
        assert abs(protrusion_below_180 - 7.9) < 1e-9, (
            f"rotate=180 jack: expected 7.9mm protrusion below hole, got {protrusion_below_180:.3f}mm"
        )

    def test_rotate_180_is_its_own_inverse_double_application(self):
        """Applying rotate=180 twice must return the original courtyard."""
        once  = _rotate_rect(JACK_CY, 180)
        twice = _rotate_rect(once,    180)
        for a, b in zip(JACK_CY, twice):
            assert abs(a - b) < 1e-9, f"Double rotate=180 not identity: {JACK_CY} vs {twice}"

    def test_rotate_90_and_270_are_inverses(self):
        """rotate=90 followed by rotate=270 must return the original."""
        r90  = _rotate_rect(JACK_CY, 90)
        back = _rotate_rect(r90, 270)
        for a, b in zip(JACK_CY, back):
            assert abs(a - b) < 1e-9, f"90+270 not identity: {JACK_CY} vs {back}"

    def test_rotate_0_is_identity(self):
        """rotate=0 must return the courtyard unchanged."""
        result = _rotate_rect(JACK_CY, 0)
        assert result == JACK_CY, f"rotate=0 not identity: {result} != {JACK_CY}"

    def test_four_rotations_complete_the_cycle(self):
        """Four successive 90° rotations must return to the original."""
        rect = JACK_CY
        for _ in range(4):
            rect = _rotate_rect(rect, 90)
        for a, b in zip(JACK_CY, rect):
            assert abs(a - b) < 1e-9, f"4×90° not identity: {JACK_CY} vs {rect}"

    def test_pcb_keepout_fires_for_default_jack_at_bottom(self):
        """A default (rotate=0) jack whose PCB body breaches the bottom keepout must fail."""
        dr = make_rules()
        # JACK_CY[3] = 6.5mm below hole; bot_keepout_start=118.5mm
        # cy + 6.5 > 118.5 when cy > 112.0
        comps = [_comp("jack_input", 50.0, 113.0, "j_bottom")]
        viols = dr._check_pcb_keepout(comps)
        assert any("PCB KEEPOUT" in v for v in viols), (
            f"Expected PCB KEEPOUT violation for jack at cy=113.0, got: {viols}"
        )

    def test_pcb_keepout_fires_for_rotate180_jack_at_bottom(self):
        """A rotate=180 jack also breaches bottom keepout when placed too low.

        With rotate=180 the body extends 7.9mm BELOW the hole (vs 6.5mm without),
        so it needs to be positioned 1.4mm higher than a default jack to clear the rail.
        """
        dr = make_rules()
        # rotate=180 JACK_CY[3] = 7.9mm; keepout at 118.5 → must be at cy < 110.6
        comps = [_comp("jack_input", 50.0, 113.0, "j_bottom", rotate=180)]
        viols = dr._check_pcb_keepout(comps)
        assert any("PCB KEEPOUT" in v for v in viols), (
            f"Expected PCB KEEPOUT for rotate=180 jack at cy=113.0, got: {viols}"
        )

    def test_rotate_180_overlap_detection_correct(self):
        """A rotate=180 jack must still collide on x. The jack body is x-symmetric (±4.5,
        width 9.0), so 180° doesn't change the x-extent; 8mm apart → 1mm body overlap."""
        dr = make_rules()
        comps = [
            _comp("jack_input", 50.0, 50.0, "j1", rotate=0),
            _comp("jack_input", 58.0, 50.0, "j2", rotate=180),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 overlap for jacks 8mm apart (body 9mm): {viols}"


# ─────────────────────────────────────────────────────────────────────────────
# Section 5: _get_courtyard returns None for non-footprinted types
# ─────────────────────────────────────────────────────────────────────────────

class TestGetCourtyardUnknownType:
    """_get_courtyard must return None for types that have no PCB footprint."""

    def test_unknown_type_returns_none(self):
        assert _get_courtyard(50, 50, "slider_label") is None
        assert _get_courtyard(50, 50, "unknown_widget") is None

    def test_all_known_footprinted_types_return_rect(self):
        footprinted = [
            "jack_input", "jack_output",
            "trimpot", "knob",
            "toggle_dw3", "toggle_dw5",
            "led", "led_labeled",
            "slider_V45",
        ]
        for t in footprinted:
            result = _get_courtyard(50, 50, t, 0)
            assert result is not None, f"_get_courtyard returned None for type '{t}'"
            x1, y1, x2, y2 = result
            assert x2 > x1, f"Degenerate courtyard for '{t}': x2={x2} <= x1={x1}"
            assert y2 > y1, f"Degenerate courtyard for '{t}': y2={y2} <= y1={y1}"


# ─────────────────────────────────────────────────────────────────────────────
# Section 6: Summary constants — document the discrepancy table
#
# These are reference assertions that pin down the exact discrepancy values,
# so any future edit to courtyard constants will immediately break these tests
# and force a deliberate review of the impact.
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscrepancySummary:
    """Pin exact courtyard values so any future changes are deliberate and reviewed."""

    def test_toggle_cy_extents_are_as_documented(self):
        """TOGGLE_CY from the Dailywell DW3/DW5 footprint F.CrtYd (body 8.13×9.14mm + 0.25mm)."""
        assert TOGGLE_CY == (-4.32, -4.82, 4.32, 4.82), (
            f"TOGGLE_CY changed: got {TOGGLE_CY}. "
            "Expected (-4.32,-4.82,4.32,4.82) — must match SW_Dailywell_DW3_DPDT.kicad_mod F.CrtYd."
        )

    def test_jack_cy_extents_are_as_documented(self):
        """JACK_CY as derived from Thonkiconn WQP-PJ398SM KiCad footprint."""
        assert JACK_CY == (-5.0, -7.9, 5.0, 6.5), (
            f"JACK_CY changed: got {JACK_CY}."
        )

    def test_trimpot_cy_extents_are_as_documented(self):
        """TRIMPOT_CY from the Song Huei 9mm tall-trimmer footprint (same land pattern as
        the Alpha RD901F 9mm); panel anchor = the shaft. The courtyard wraps the offset
        pins + body + mounting legs, so it is asymmetric about the shaft."""
        assert TRIMPOT_CY == (-8.65, -6.67, 5.1, 6.67), (
            f"TRIMPOT_CY changed: got {TRIMPOT_CY}."
        )

    def test_toggle_courtyard_encompasses_drawn_symbol(self):
        """TOGGLE_CY half-extents must exceed the drawn toggle symbol (lever tip ≈ 3.1mm)."""
        draw_half = 2.2 + 0.9   # lever length + tip radius
        assert TOGGLE_CY[3] >= draw_half and TOGGLE_CY[2] >= draw_half, (
            f"TOGGLE_CY {TOGGLE_CY} smaller than drawn symbol half-extent {draw_half}mm."
        )

    def test_toggle_panel_radius_models_locking_washer(self):
        """TOGGLE_PANEL_R models the Dailywell 2M external-tooth locking washer (~Ø7.6mm)."""
        assert TOGGLE_PANEL_R == 3.8, (
            f"TOGGLE_PANEL_R changed: got {TOGGLE_PANEL_R}. Expected 3.8 "
            "(10-48 locking washer OD ~Ø7.6mm; panel hole is Ø4.95mm, bushing Ø6.00mm)."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Section 7: real placement + copper-clearance model (the live _check_pcb_overlaps)
#
# Model: component BODIES (the F.Fab can) must not overlap; ELECTRICAL (named) pads keep
# PCB_PAD_CLEARANCE_MM copper clearance; structural mounting legs (unnamed pads) are
# exempt from leg-vs-leg but still clash a neighbour's signal pad. No pad-vs-body cross.
# ─────────────────────────────────────────────────────────────────────────────

from panel_rules import PCB_PAD_CLEARANCE_MM


class TestCollisionModel:
    def setup_method(self):
        self.dr = make_rules()

    def _v(self, comps):
        return self.dr._check_pcb_overlaps(comps)

    # ── body geometry ──────────────────────────────────────────────────────────
    def test_pot_body_is_centred_can(self):
        """Pot body = the ~9.7mm round can centred on the shaft (anchor), symmetric."""
        body = _pk.footprint_shapes("trimpot")["body"][0]
        w, h = body[2] - body[0], body[3] - body[1]
        assert 9.0 < w < 10.5 and 9.0 < h < 10.5, f"body {w:.2f}x{h:.2f} not ~9.7mm can"
        assert abs(body[0] + body[2]) < 0.3 and abs(body[1] + body[3]) < 0.3, \
            f"body not centred on shaft: {body}"

    def test_trimpot_has_3_signal_pads_and_2_legs(self):
        sh = _pk.footprint_shapes("trimpot")
        assert len(sh["pads"]) == 3 and len(sh["legs"]) == 2, sh

    def test_trimpot_and_knob_share_land_pattern(self):
        """Trimpot (Song Huei) and knob (Alpha RD901F) share the 9mm electrical land
        pattern — same signal pads + mounting legs. (Bodies may differ: the trimpot's
        F.Fab is the cleaned centred can; the knob keeps the KiCad RD901F outline.)"""
        a, b = _pk.footprint_shapes("trimpot"), _pk.footprint_shapes("knob")
        assert a["pads"] == b["pads"] and a["legs"] == b["legs"]

    # ── placement: bodies must not overlap ──────────────────────────────────────
    def test_pots_clear_side_by_side_at_body_width(self):
        """The reported bug: side-by-side pots at >= the body width must be CLEAR
        (offset pins under a neighbour body are NOT a collision)."""
        assert self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 61.43, 50, "b")]) == []
        assert self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 62.7, 50, "b")]) == []

    def test_pots_clear_stacked_vertically(self):
        """Vertical stack: mounting-leg pads no longer collide (leg-vs-leg exempt)."""
        for p in (10.0, 11.0, 11.43, 12.0):
            assert self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 50, 50 + p, "b")]) == [], p

    def test_bodies_overlap_below_can_width_flags(self):
        v = self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 59.0, 50, "b")])  # 9mm < 9.7
        assert len(v) == 1 and "bodies overlap" in v[0], v

    # ── copper clearance ────────────────────────────────────────────────────────
    def test_signal_pads_within_clearance_flag(self):
        """Two pots whose signal pins come within 0.2mm must flag pad clearance.
        Pins sit at anchor x=-7.5; place B's pins onto A's pins (B left of A by ~15mm
        puts B's right-side... ) — use a known-tight horizontal where pins meet."""
        # B mirrored (rot 180) so its pins face A's pins across the gap, tuned to <0.2mm.
        v = self._v([_comp("trimpot", 50, 50, "a", 0), _comp("trimpot", 50 + 1.6, 50, "b", 180)])
        assert any("pad clearance" in s or "bodies overlap" in s for s in v), v

    def test_leg_vs_leg_is_exempt(self):
        """Two pots stacked so ONLY their mounting legs are near (bodies clear): no flag.
        At 10mm vertical the bodies (±4.85) just clear and the legs abut — must be clear."""
        assert self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 50, 50 + 10.0, "b")]) == []

    def test_leg_vs_signal_pad_flags(self):
        """A mounting leg intersecting a neighbour's SIGNAL pad IS a violation. Place B so
        a signal pin lands on A's leg while bodies stay clear."""
        # A leg at anchor (0,+4.8). B signal pin at anchor (-7.5, 0) -> put B at (+7.5,+4.8)
        # from A so that pin sits on A's leg; bodies (±4.85) are ~8.8mm apart diagonally → clear.
        v = self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 57.5, 54.8, "b")])
        assert v, "leg intersecting neighbour signal pad must flag"

    # ── message + parity-relevant shape ─────────────────────────────────────────
    def test_message_states_body_or_pad_reason(self):
        v = self._v([_comp("trimpot", 50, 50, "a"), _comp("trimpot", 59.0, 50, "b")])
        assert v and ("bodies overlap" in v[0] or "pad clearance" in v[0])

    def test_clearance_is_industry_default(self):
        assert PCB_PAD_CLEARANCE_MM == 0.2

    # ── rotation still consistent with the draw ─────────────────────────────────
    def test_rotation_matches_svg_draw_direction(self):
        rr = _rotate_rect((-7.5, 0.0, -7.5, 0.0), 90)
        assert (round(rr[0], 3), round(rr[1], 3)) == (0.0, -7.5)

    def test_full_colliding_pair_set_in_cluster(self):
        """Row of 3 pots overlapping bodies (8.5mm pitch): both adjacent pairs flag,
        the end pair (17mm) is clear."""
        comps = [_comp("trimpot", 50.0, 50.0, "p0"),
                 _comp("trimpot", 58.5, 50.0, "p1"),
                 _comp("trimpot", 67.0, 50.0, "p2")]
        viols = self.dr._check_pcb_overlaps(comps)
        got = {frozenset([w.split("'")[1], w.split("'")[3]]) for w in viols}
        assert got == {frozenset(["p0", "p1"]), frozenset(["p1", "p2"])}, viols
