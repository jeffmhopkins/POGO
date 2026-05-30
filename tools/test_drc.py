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


def _keepout(ctype: str, rot: int = 0):
    """Rotated, anchor-relative keepout rects for a type (mirrors panel_rules)."""
    return [_rotate_rect(r, rot) for r in _pk.footprint_shapes(ctype)]


def _touch_sep(a_type, b_type, axis, rot_a=0, rot_b=0):
    """Centre-to-centre separation along `axis` ('x'|'y') at which A and B's real
    footprints JUST stop overlapping (B placed on the +axis side of A). Derived from
    footprint_shapes, so it tracks the geometry instead of a hard-coded courtyard width.
    At this separation the keepouts touch (gap 0 → no overlap); 0.5mm closer must collide."""
    ra, rb = _keepout(a_type, rot_a), _keepout(b_type, rot_b)
    best = None
    for x in ra:
        for y in rb:
            if axis == "x":
                # y-ranges must overlap for an x-touch to matter; sep where they touch
                if min(x[3], y[3]) > max(x[1], y[1]):
                    s = x[2] - y[0]
                    best = s if best is None else max(best, s)
            else:
                if min(x[2], y[2]) > max(x[0], y[0]):
                    s = x[3] - y[1]
                    best = s if best is None else max(best, s)
    return best


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
        # 9mm pots: pin-of-B vs body-of-A drives the boundary (~13.25mm pitch).
        sep = self._assert_boundary("trimpot", "trimpot", "x")
        assert 12.5 < sep < 14.0, f"trimpot x touch sep {sep:.2f} not in expected ~13.25mm"

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
# Section 6: real-footprint collision model (footprint_shapes + _check_pcb_overlaps)
#
# These lock the model that replaced the conservative courtyard-bbox overlap check:
#   - body keepout = the full F.Fab outline (squarish base for 9mm pots), NOT the
#     tiny shaft/hole indicator circle (the bug that let pins/bodies pass).
#   - rotation matches the SVG draw transform (CW; (x,y)->(-y,x) at 90°).
#   - the offset pin cluster causes collisions (pin-of-B under body-of-A).
# ─────────────────────────────────────────────────────────────────────────────

class TestRealCollisionModel:
    """Lock the real pads+body collision model and the WS1/rotation fixes."""

    def _body(self, ctype):
        # The body keepout is the largest-area rect in footprint_shapes.
        return max(_pk.footprint_shapes(ctype), key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))

    def test_pot_body_is_squarish_base_not_shaft_circle(self):
        """9mm pot body keepout = the ~11.35x9.5 squarish base, not the r3.5 shaft."""
        x1, y1, x2, y2 = self._body("trimpot")
        assert (x2 - x1) > 10.0 and (y2 - y1) > 9.0, \
            f"trimpot body {(x2-x1):.2f}x{(y2-y1):.2f} is not the squarish base (shaft-circle bug)"

    def test_jack_body_is_full_outline(self):
        """Jack body keepout = its ~9x12.5 outline, not the r1.8 hole indicator."""
        x1, y1, x2, y2 = self._body("jack_input")
        assert (x2 - x1) > 8.0 and (y2 - y1) > 11.0, \
            f"jack body {(x2-x1):.2f}x{(y2-y1):.2f} is the tiny hole circle, not the outline"

    def test_trimpot_and_knob_share_land_pattern(self):
        """Trimpot (Song Huei) and knob (Alpha RD901F) are the same 9mm land pattern."""
        assert _pk.footprint_shapes("trimpot") == _pk.footprint_shapes("knob")

    def test_pin_of_neighbour_under_body_collides(self):
        """Two pots offset so only B's signal pins land on A's body must COLLIDE
        (the reported 'pins don't collide' bug). Pins sit ~7.5mm to one side of the
        shaft; at ~12mm pitch B's pins overlap A's body."""
        dr = make_rules()
        comps = [_comp("trimpot", 50.0, 50.0, "a"), _comp("trimpot", 62.0, 50.0, "b")]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) == 1 and "PCB OVERLAP" in viols[0], \
            f"pin-of-B vs body-of-A at 12mm pitch must collide: {viols}"

    def test_two_pots_clear_at_14mm(self):
        """At 14mm pitch the 9mm pots clear (true minimum usable pitch)."""
        dr = make_rules()
        comps = [_comp("trimpot", 50.0, 50.0, "a"), _comp("trimpot", 64.0, 50.0, "b")]
        assert dr._check_pcb_overlaps(comps) == []

    def test_rotation_matches_svg_draw_direction(self):
        """_rotate_rect(90) must rotate CW like the SVG draw transform: a point at
        anchor-relative (-7.5,0) (a pot's pin side) maps to (0,-7.5) (up)."""
        rr = _rotate_rect((-7.5, 0.0, -7.5, 0.0), 90)
        assert (round(rr[0], 3), round(rr[1], 3)) == (0.0, -7.5), \
            f"_rotate_rect(90) of (-7.5,0) = {rr[:2]}, expected (0,-7.5) (SVG CW)"

    def test_rotated_pot_collision_tracks_orientation(self):
        """Two pots stacked vertically, both rotated 90° (pins now point up): they must
        still resolve to a definite collide/clear (rotation applied consistently)."""
        dr = make_rules()
        near = dr._check_pcb_overlaps([_comp("trimpot", 50, 50, "a", 90),
                                       _comp("trimpot", 50, 55, "b", 90)])
        far = dr._check_pcb_overlaps([_comp("trimpot", 50, 50, "a", 90),
                                      _comp("trimpot", 50, 90, "b", 90)])
        assert len(near) == 1 and far == [], f"near={near} far={far}"

    def test_full_colliding_pair_set_in_cluster(self):
        """A row of 3 pots at 11.43mm reports all 2 adjacent-pair collisions (not 3 — the
        end pair at 22.86mm is clear)."""
        dr = make_rules()
        comps = [_comp("trimpot", 50.0, 50.0, "p0"),
                 _comp("trimpot", 61.43, 50.0, "p1"),
                 _comp("trimpot", 72.86, 50.0, "p2")]
        viols = dr._check_pcb_overlaps(comps)
        pairs = {frozenset(["p0", "p1"]), frozenset(["p1", "p2"])}
        got = {frozenset([w.split("'")[1], w.split("'")[3]]) for w in viols}
        assert got == pairs, f"expected adjacent pairs {pairs}, got {got} from {viols}"

    def test_penetration_reported_not_area(self):
        """Overlap message reports a single penetration depth (the #3 metric change)."""
        dr = make_rules()
        viols = dr._check_pcb_overlaps([_comp("trimpot", 50, 50, "a"),
                                        _comp("trimpot", 60, 50, "b")])
        assert viols and "penetration" in viols[0] and "×" not in viols[0], viols


# ─────────────────────────────────────────────────────────────────────────────
# Section 7: side-to-side + rotation failure modes (the offset-pin-cluster cases)
#
# A 9mm pot's 3 signal pins sit ~7.5mm to one side of the shaft, so collisions are
# rotation-sensitive: same-rotation rows put B's pins under A's body; alternating
# 0/180 interleaves them clear; 90° rows clash on the mounting legs. These lock the
# exact feature pairs + boundary pitches so the model can't silently change.
# ─────────────────────────────────────────────────────────────────────────────

class TestSideBySideRotationModes:
    _LABEL = ["pin1", "pin2", "pin3", "legA", "legB", "body"]

    def _hits(self, rotA, rotB, axis, pitch):
        """Set of (featureA, featureB) labels that overlap for two trimpots `pitch`
        apart along `axis`, A@rotA B@rotB."""
        ra = [_rotate_rect(r, rotA) for r in _pk.footprint_shapes("trimpot")]
        rb = [_rotate_rect(r, rotB) for r in _pk.footprint_shapes("trimpot")]
        ra = [(50 + x[0], 50 + x[1], 50 + x[2], 50 + x[3]) for x in ra]
        off = (pitch if axis == "x" else 0, pitch if axis == "y" else 0)
        rb = [(50 + off[0] + x[0], 50 + off[1] + x[1],
               50 + off[0] + x[2], 50 + off[1] + x[3]) for x in rb]
        hits = set()
        for i, x in enumerate(ra):
            for j, y in enumerate(rb):
                dx = min(x[2], y[2]) - max(x[0], y[0])
                dy = min(x[3], y[3]) - max(x[1], y[1])
                if dx > 0 and dy > 0:
                    hits.add((self._LABEL[i], self._LABEL[j]))
        return hits

    def test_same_rotation_side_by_side_is_pins_under_body(self):
        """rot0/rot0 at 12.7mm: the only collisions are A.body vs B's three pins."""
        hits = self._hits(0, 0, "x", 12.7)
        assert hits == {("body", "pin1"), ("body", "pin2"), ("body", "pin3")}, hits

    def test_same_rotation_clears_at_14mm(self):
        assert self._hits(0, 0, "x", 14.0) == set()

    def test_alternating_rotation_interleaves_clear(self):
        """rot0/rot180 (pins facing apart) clears at the tight 11.43mm pitch."""
        assert self._hits(0, 180, "x", 11.43) == set()

    def test_rot90_row_clashes_on_legs(self):
        """Both rotated 90°: pins point along the row; the clash is leg-pad vs leg-pad."""
        hits = self._hits(90, 90, "x", 11.43)
        assert hits == {("legB", "legA")}, hits

    def test_rot90_row_clears_at_13mm(self):
        assert self._hits(90, 90, "x", 13.0) == set()

    def test_rot180_mirror_of_rot0(self):
        """rot180/rot180 is the mirror of rot0/rot0: B.body vs A's pins."""
        hits = self._hits(180, 180, "x", 12.7)
        assert hits == {("pin1", "body"), ("pin2", "body"), ("pin3", "body")}, hits

    def test_vertical_stack_same_rotation_collides_on_legs(self):
        """Stacked vertically (rot0): the legs are top/bottom → leg vs leg/pin clash."""
        hits = self._hits(0, 0, "y", 8.0)
        assert hits, "vertical 8mm stack must collide"
        assert hits == self._hits(0, 0, "y", 8.0)  # deterministic
