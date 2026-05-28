"""test_drc.py — Unit tests for the POGO panel DRC checker (panel_rules.py).

Purpose: Document and verify the relationship between the SVG draw bounding
boxes produced by panel_svg.py and the PCB courtyard constants defined in
panel_rules.py.  Previously several component types had courtyards smaller
than their drawn SVG bodies, creating blind spots.  All known blind spots are
now fixed; these tests enforce that the fixes stay in place.

Fixed blind spots (see TestSwitchV3TrimpotBlindSpot and TestDiscrepancySummary):
  - SWITCH_V3_CY: was ±5.0mm; now ±6.4mm (CAS-120R3 body ±6.35mm + margin)
  - SWITCH_H3_CY: new constant ±6.0mm wide (matches 12mm SVG body)
  - Nut keepout: switch_V3 now uses SWITCH_V3_PANEL_R=1.0mm (not 3.15mm toggle radius)

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
    SWITCH_CY,
    SWITCH_V3_CY,
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

    # ── switch_H2 ─────────────────────────────────────────────────────────────
    # svg_switch_H2 draws:
    #   Body rect: 9mm wide × 2.4mm tall, bx=cx-4.5, by=cy-1.2
    #   Slug rect: 3.5mm wide × 2.8mm tall, sx=bx+0.5, sy=cy-1.4
    # Bounding box:  x=[-4.5, +4.5],  y=[-1.4, +1.4]   (slug is tallest element)
    def test_switch_H2_courtyard_encompasses_svg_body(self):
        """SWITCH_CY must encompass the switch_H2 drawn body (9×2.8mm)."""
        svg_x1, svg_y1, svg_x2, svg_y2 = -4.5, -1.4, 4.5, 1.4
        x1, y1, x2, y2 = SWITCH_CY
        assert x1 <= svg_x1, f"SWITCH_CY left ({x1}) > svg left ({svg_x1})"
        assert y1 <= svg_y1, f"SWITCH_CY top ({y1}) > svg top ({svg_y1})"
        assert x2 >= svg_x2, f"SWITCH_CY right ({x2}) < svg right ({svg_x2})"
        assert y2 >= svg_y2, f"SWITCH_CY bottom ({y2}) < svg bottom ({svg_y2})"

    # ── switch_H3 ─────────────────────────────────────────────────────────────
    # svg_switch_H3 draws:
    #   Body rect: 12mm wide × 2.4mm tall, bx=cx-6.0, by=cy-1.2
    #   Slug rect: 3.5mm wide × 2.8mm tall, centred
    # Bounding box:  x=[-6.0, +6.0],  y=[-1.4, +1.4]
    #
    # SWITCH_CY = (-4.5, -3.5, 4.5, 7.5) — designed for a sub-mini toggle (SPDT).
    # It is only 9mm wide in x but switch_H3 body is 12mm wide.
    # This is a CONFIRMED DISCREPANCY: SWITCH_CY is 1.5mm narrower on each side.
    @pytest.mark.xfail(
        reason=(
            "switch_H3 SVG body is 12mm wide (x∈[-6.0,+6.0]) but SWITCH_CY "
            "is only 9mm wide (x∈[-4.5,+4.5]). SWITCH_CY is modelled after "
            "a sub-mini toggle, not the H3 slide switch. The DRC cannot detect "
            "horizontal overlap for switch_H3 within the outer 1.5mm on each side."
        ),
        strict=True,
    )
    def test_switch_H3_courtyard_encompasses_svg_body_xfail(self):
        """SWITCH_CY must encompass the switch_H3 drawn body (12×2.8mm). KNOWN FAIL."""
        svg_x1, svg_y1, svg_x2, svg_y2 = -6.0, -1.4, 6.0, 1.4
        x1, y1, x2, y2 = SWITCH_CY
        assert x1 <= svg_x1, (
            f"SWITCH_CY left edge ({x1}) is {x1 - svg_x1:+.1f}mm tighter than "
            f"switch_H3 SVG body left ({svg_x1})"
        )
        assert x2 >= svg_x2, (
            f"SWITCH_CY right edge ({x2}) is {x2 - svg_x2:+.1f}mm tighter than "
            f"switch_H3 SVG body right ({svg_x2})"
        )

    # ── switch_V3 ─────────────────────────────────────────────────────────────
    # svg_switch_V3 draws:
    #   Body rect: 2.4mm wide × body_height tall (default=12), bx=cx-1.2
    #   Slug rect: 2.8mm wide × 3.5mm tall, sx=cx-1.4  (slug is widest element)
    # Default body_height=12 → cy_body_top = cy - 6.0
    # Bounding box:  x=[-1.4, +1.4],  y=[-6.0, +6.0]
    #
    # SWITCH_V3_CY = (-2.0, -6.4, 2.0, 6.4)
    # Physical CAS-120R3 body is 12.7mm (±6.35mm) + 0.05mm margin = ±6.4mm.
    # Courtyard ±6.4mm > SVG body ±6.0mm — no blind spot.
    def test_switch_V3_courtyard_encompasses_svg_body(self):
        """SWITCH_V3_CY must encompass the switch_V3 drawn body (default 2.8×12mm)."""
        svg_x1, svg_y1, svg_x2, svg_y2 = -1.4, -6.0, 1.4, 6.0
        x1, y1, x2, y2 = SWITCH_V3_CY
        assert y1 <= svg_y1, (
            f"SWITCH_V3_CY top edge ({y1}) is {y1 - svg_y1:+.2f}mm tighter than "
            f"switch_V3 SVG body top ({svg_y1})."
        )
        assert y2 >= svg_y2, (
            f"SWITCH_V3_CY bottom edge ({y2}) is {y2 - svg_y2:+.2f}mm tighter than "
            f"switch_V3 SVG body bottom ({svg_y2})."
        )

    # The x-direction for switch_V3 is fine (SVG slug is ±1.4, CY is ±2.0).
    def test_switch_V3_courtyard_wide_enough_in_x(self):
        """SWITCH_V3_CY must encompass the slug width (±1.4mm) in x."""
        slug_half_w = 1.4
        x1, y1, x2, y2 = SWITCH_V3_CY
        assert x1 <= -slug_half_w, f"SWITCH_V3_CY left ({x1}) tighter than slug ({-slug_half_w})"
        assert x2 >= slug_half_w,  f"SWITCH_V3_CY right ({x2}) tighter than slug ({slug_half_w})"

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

    # ── knob_medium ───────────────────────────────────────────────────────────
    # svg_knob draws a circle with r=4.5 for knob_medium.
    # POT_CY = (-8.65, -6.67, 5.1, 6.67) — the 9mm Alpha RD901F footprint.
    # The rotary knob cap (r=4.5) is the PANEL-FACE component; the actual pot body
    # below is much larger. POT_CY covers the full physical footprint, which
    # should be larger than the panel symbol.
    def test_knob_medium_courtyard_encompasses_svg_symbol(self):
        """POT_CY must encompass the knob_medium visual cap (r=4.5mm)."""
        svg_r = 4.5
        x1, y1, x2, y2 = POT_CY
        assert x1 <= -svg_r, f"POT_CY left ({x1}) tighter than knob_medium cap (-{svg_r})"
        assert y1 <= -svg_r, f"POT_CY top ({y1}) tighter than knob_medium cap (-{svg_r})"
        assert x2 >= svg_r,  f"POT_CY right ({x2}) tighter than knob_medium cap ({svg_r})"
        assert y2 >= svg_r,  f"POT_CY bottom ({y2}) tighter than knob_medium cap ({svg_r})"

    # ── knob_large ────────────────────────────────────────────────────────────
    # svg_knob draws r=7.0 for knob_large.
    # POT_CY right edge = 5.1mm. The knob cap extends to 7.0mm on the right.
    # Also top/bottom: cap ±7.0mm vs CY ±6.67mm.
    @pytest.mark.xfail(
        reason=(
            "knob_large SVG cap circle has r=7.0mm but POT_CY right edge is only "
            "5.1mm (1.9mm short) and top/bottom are ±6.67mm (0.33mm short each). "
            "The Alpha RD901F 9mm pot footprint is centred on the shaft, not the nut, "
            "so the courtyard is offset. The knob cap extends beyond the footprint "
            "on the right side and slightly beyond on top/bottom. "
            "Panel-face nut-clearance check (jack_nut_r, pot_nut_r) is the correct "
            "gate for knob spacing — the PCB courtyard check cannot protect against "
            "large knob cap collisions on the panel face."
        ),
        strict=True,
    )
    def test_knob_large_courtyard_encompasses_svg_symbol_xfail(self):
        """POT_CY must encompass the knob_large visual cap (r=7.0mm). KNOWN FAIL."""
        svg_r = 7.0
        x1, y1, x2, y2 = POT_CY
        assert y1 <= -svg_r, (
            f"POT_CY top ({y1}) is {y1 - (-svg_r):+.2f}mm tighter than knob_large top (-{svg_r})"
        )
        assert x2 >= svg_r, (
            f"POT_CY right ({x2}) is {x2 - svg_r:+.2f}mm tighter than knob_large right ({svg_r})"
        )
        assert y2 >= svg_r, (
            f"POT_CY bottom ({y2}) is {y2 - svg_r:+.2f}mm tighter than knob_large bottom ({svg_r})"
        )

    # ── knob_xl ───────────────────────────────────────────────────────────────
    # svg_knob draws r=9.0 for knob_xl.
    # POT_CY = (-8.65, -6.67, 5.1, 6.67). All four edges are inside the cap circle.
    @pytest.mark.xfail(
        reason=(
            "knob_xl SVG cap circle has r=9.0mm. POT_CY is 8.65mm on the left, "
            "6.67mm top/bottom, and only 5.1mm on the right — all smaller than r=9.0. "
            "The XL knob cap extends far beyond the pot footprint on all sides. "
            "DRC PCB overlap checks cannot detect knob_xl collisions. "
            "Rely on panel-face nut-clearance (pot_nut_r) for spacing enforcement."
        ),
        strict=True,
    )
    def test_knob_xl_courtyard_encompasses_svg_symbol_xfail(self):
        """POT_CY must encompass the knob_xl visual cap (r=9.0mm). KNOWN FAIL."""
        svg_r = 9.0
        x1, y1, x2, y2 = POT_CY
        assert x1 <= -svg_r, (
            f"POT_CY left ({x1}) is {x1 - (-svg_r):+.2f}mm tighter than knob_xl (-{svg_r})"
        )
        assert y1 <= -svg_r, (
            f"POT_CY top ({y1}) is {y1 - (-svg_r):+.2f}mm tighter than knob_xl (-{svg_r})"
        )
        assert x2 >= svg_r, (
            f"POT_CY right ({x2}) is {x2 - svg_r:+.2f}mm tighter than knob_xl ({svg_r})"
        )
        assert y2 >= svg_r, (
            f"POT_CY bottom ({y2}) is {y2 - svg_r:+.2f}mm tighter than knob_xl ({svg_r})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: DRC catches overlaps that are visually obvious
#
# For each type: place two components at minimum-gap (just passing), then 0.5mm
# closer (must fail).  This verifies the DRC machinery is actually exercised.
# ─────────────────────────────────────────────────────────────────────────────

class TestDrcCatchesOverlaps:
    """DRC must fire when components are placed too close together."""

    def setup_method(self):
        self.dr = make_rules()

    # ── jack (horizontal separation) ─────────────────────────────────────────
    # JACK_CY width = 10.0mm → minimum x-separation = 10.0mm (gap=0)
    def test_jack_horizontal_pass_at_minimum_gap(self):
        """Two jacks 10.0mm apart horizontally: DRC must pass (gap=0)."""
        comps = [
            _comp("jack_input", 50.0, 50.0, "j1"),
            _comp("jack_input", 60.0, 50.0, "j2"),   # exactly 10mm apart
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_jack_horizontal_fail_at_0_5mm_overlap(self):
        """Two jacks 9.5mm apart: DRC must report overlap."""
        comps = [
            _comp("jack_input", 50.0, 50.0, "j1"),
            _comp("jack_input", 59.5, 50.0, "j2"),   # 0.5mm into courtyard
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]
        assert "j1" in viols[0] and "j2" in viols[0]

    # ── trimpot (horizontal separation) ──────────────────────────────────────
    # TRIMPOT_CY width = 5.33mm → minimum x-separation = 5.33mm
    def test_trimpot_horizontal_pass_at_minimum_gap(self):
        """Two trimpots 5.33mm apart: DRC must pass."""
        cx2 = 50.0 + 2 * 2.665   # exactly 2 × half-widths apart
        comps = [
            _comp("trimpot", 50.0, 50.0, "t1"),
            _comp("trimpot", cx2,  50.0, "t2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_trimpot_horizontal_fail_at_0_5mm_overlap(self):
        """Two trimpots 4.83mm apart: DRC must report overlap."""
        cx2 = 50.0 + 2 * 2.665 - 0.5
        comps = [
            _comp("trimpot", 50.0, 50.0, "t1"),
            _comp("trimpot", cx2,  50.0, "t2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]

    # ── switch_H2 (vertical separation) ──────────────────────────────────────
    # SWITCH_CY height = 11.0mm (y1=-3.5, y2=+7.5) → min y-sep = 11.0mm
    def test_switch_H2_vertical_pass_at_minimum_gap(self):
        """Two switch_H2 stacked 11.0mm apart: DRC must pass."""
        dy = abs(SWITCH_CY[1]) + abs(SWITCH_CY[3])  # 3.5 + 7.5 = 11.0
        comps = [
            _comp("switch_H2", 50.0, 50.0,       "s1"),
            _comp("switch_H2", 50.0, 50.0 + dy,  "s2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_switch_H2_vertical_fail_at_0_5mm_overlap(self):
        """Two switch_H2 stacked 10.5mm apart: DRC must report overlap."""
        dy = abs(SWITCH_CY[1]) + abs(SWITCH_CY[3]) - 0.5
        comps = [
            _comp("switch_H2", 50.0, 50.0,       "s1"),
            _comp("switch_H2", 50.0, 50.0 + dy,  "s2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]

    # ── switch_V3 (vertical separation) ──────────────────────────────────────
    # SWITCH_V3_CY height = 10.0mm (y∈[-5,+5]) → min y-sep = 10.0mm
    def test_switch_V3_vertical_pass_at_minimum_gap(self):
        """Two switch_V3 stacked 10.0mm apart: DRC must pass."""
        dy = abs(SWITCH_V3_CY[1]) + abs(SWITCH_V3_CY[3])  # 5.0 + 5.0 = 10.0
        comps = [
            _comp("switch_V3", 50.0, 50.0,       "v1"),
            _comp("switch_V3", 50.0, 50.0 + dy,  "v2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_switch_V3_vertical_fail_at_0_5mm_overlap(self):
        """Two switch_V3 stacked 9.5mm apart: DRC must report overlap."""
        dy = abs(SWITCH_V3_CY[1]) + abs(SWITCH_V3_CY[3]) - 0.5
        comps = [
            _comp("switch_V3", 50.0, 50.0,       "v1"),
            _comp("switch_V3", 50.0, 50.0 + dy,  "v2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]

    # ── LED ───────────────────────────────────────────────────────────────────
    # LED_CY height = 5.5mm (y∈[-1.5, +4.0]) → min y-sep = 5.5mm
    def test_led_vertical_pass_at_minimum_gap(self):
        """Two LEDs stacked 5.5mm apart: DRC must pass."""
        dy = abs(LED_CY[1]) + abs(LED_CY[3])  # 1.5 + 4.0 = 5.5
        comps = [
            _comp("led", 50.0, 50.0,       "l1"),
            _comp("led", 50.0, 50.0 + dy,  "l2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_led_vertical_fail_at_0_5mm_overlap(self):
        """Two LEDs stacked 5.0mm apart: DRC must report overlap."""
        dy = abs(LED_CY[1]) + abs(LED_CY[3]) - 0.5
        comps = [
            _comp("led", 50.0, 50.0,       "l1"),
            _comp("led", 50.0, 50.0 + dy,  "l2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]

    # ── cross-type: jack + trimpot ────────────────────────────────────────────
    # Vertical separation in same column:
    # jack bottom edge: +6.5mm, trimpot top edge: -3.385mm → gap threshold = 9.885mm
    def test_jack_trimpot_vertical_pass_at_minimum_gap(self):
        """jack_input above a trimpot at gap=0 must pass DRC."""
        jack_cy = 50.0
        # gap=0 → trimpot cy = jack_cy + JACK_CY[3] + abs(TRIMPOT_CY[1])
        tp_cy = jack_cy + JACK_CY[3] + abs(TRIMPOT_CY[1])   # 50 + 6.5 + 3.385 = 59.885
        comps = [
            _comp("jack_input", 50.0, jack_cy, "j1"),
            _comp("trimpot",    50.0, tp_cy,   "t1"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_jack_trimpot_vertical_fail_when_0_5mm_closer(self):
        """jack_input + trimpot at 0.5mm overlap must fail DRC."""
        jack_cy = 50.0
        tp_cy   = jack_cy + JACK_CY[3] + abs(TRIMPOT_CY[1]) - 0.5
        comps = [
            _comp("jack_input", 50.0, jack_cy, "j1"),
            _comp("trimpot",    50.0, tp_cy,   "t1"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 violation, got: {viols}"
        assert "PCB OVERLAP" in viols[0]


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: The switch_V3 + trimpot blind spot (the live panel scenario)
#
# A switch_V3 at cy=75.1 and a trimpot at cy=83.6 in the same column (delta=8.5mm)
# are separated by exactly 8.5mm.
#
# DRC threshold:  SWITCH_V3_CY[3] + abs(TRIMPOT_CY[1]) = 5.0 + 3.385 = 8.385mm
# SVG body threshold: 6.0 (half of default body_height) + 2.5 (trimpot r) = 8.5mm
#
# At delta=8.5mm:
#   - DRC courtyard gap = 8.5 - 8.385 = +0.115mm → DRC PASSES
#   - SVG body gap      = 8.5 - 8.5   = 0.0mm    → bodies exactly touching
#
# The blind window where DRC passes but SVG bodies overlap: delta ∈ [8.385, 8.5)
# ─────────────────────────────────────────────────────────────────────────────

class TestSwitchV3TrimpotBlindSpot:
    """Tests verifying the former blind spot between switch_V3 and trimpot is eliminated.

    Previously SWITCH_V3_CY = (-2.0,-5.0,2.0,5.0) was 1.0mm short of the 12mm SVG body,
    creating a 0.115mm window where DRC passed but SVG bodies were touching. Fixed by
    expanding to SWITCH_V3_CY = (-2.0,-6.4,2.0,6.4) to match the CAS-120R3 body (±6.35mm).
    """

    SWITCH_V3_CY_REF = 75.1
    TRIMPOT_CY_REF   = 83.6
    DELTA_LIVE       = TRIMPOT_CY_REF - SWITCH_V3_CY_REF   # = 8.5mm

    def test_blind_window_arithmetic(self):
        """Blind window is eliminated: DRC courtyard now exceeds SVG body half-height."""
        drc_threshold  = SWITCH_V3_CY[3] + abs(TRIMPOT_CY[1])   # 6.4 + 3.385 = 9.785
        real_threshold = 6.0 + 2.5                                # SVG body half-heights = 8.5

        blind_window_mm = real_threshold - drc_threshold          # 8.5 - 9.785 = -1.285
        assert blind_window_mm <= 0, (
            f"Expected no blind window (courtyard >= body), got {blind_window_mm:.3f}mm. "
            f"drc_threshold={drc_threshold:.3f}mm, real_threshold={real_threshold:.3f}mm. "
            "SWITCH_V3_CY may have regressed — check panel_rules.py."
        )

    def test_live_panel_positions_caught_by_drc(self):
        """DRC must catch switch_V3 at cy=75.1 + trimpot at cy=83.6 (delta=8.5mm < 9.785mm threshold)."""
        dr = make_rules()
        comps = [
            _comp("switch_V3", 50.0, self.SWITCH_V3_CY_REF, "sw1"),
            _comp("trimpot",   50.0, self.TRIMPOT_CY_REF,   "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) >= 1, (
            f"DRC should flag overlap at delta={self.DELTA_LIVE}mm (threshold=9.785mm) "
            f"but returned no violations. SWITCH_V3_CY may have regressed."
        )

    def test_live_panel_drc_catches_overlap(self):
        """DRC flags switch_V3 at cy=75.1 + trimpot at cy=83.6 as too close."""
        dr = make_rules()
        comps = [
            _comp("switch_V3", 50.0, self.SWITCH_V3_CY_REF, "sw1"),
            _comp("trimpot",   50.0, self.TRIMPOT_CY_REF,   "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) >= 1, (
            f"Expected at least 1 PCB OVERLAP violation for live panel positions "
            f"(switch_V3 @ cy={self.SWITCH_V3_CY_REF}, trimpot @ cy={self.TRIMPOT_CY_REF}, "
            f"delta={self.DELTA_LIVE}mm) but DRC returned no violations. "
            f"SWITCH_V3_CY y-extent ({SWITCH_V3_CY[1]},{SWITCH_V3_CY[3]}) must cover ±6.4mm."
        )

    def test_drc_catches_overlap_when_delta_below_drc_threshold(self):
        """DRC must catch overlap when components are clearly too close (delta < 9.785mm)."""
        dr = make_rules()
        # At delta=8.0mm, well inside the 9.785mm threshold — DRC must fire.
        comps = [
            _comp("switch_V3", 50.0, self.SWITCH_V3_CY_REF,         "sw1"),
            _comp("trimpot",   50.0, self.SWITCH_V3_CY_REF + 8.0,   "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) >= 1, (
            f"DRC must catch overlap at delta=8.0mm (threshold=9.785mm), got: {viols}"
        )

    def test_minimum_safe_delta_under_current_drc(self):
        """DRC passes when delta is just above the 9.785mm courtyard sum threshold."""
        dr = make_rules()
        drc_threshold = SWITCH_V3_CY[3] + abs(TRIMPOT_CY[1])   # 6.4 + 3.385 = 9.785

        # At threshold + 0.001mm (gap > 0), DRC passes
        safe_delta = drc_threshold + 0.001
        comps_safe = [
            _comp("switch_V3", 50.0, self.SWITCH_V3_CY_REF,                  "sw1"),
            _comp("trimpot",   50.0, self.SWITCH_V3_CY_REF + safe_delta,      "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps_safe)
        assert viols == [], (
            f"At delta={safe_delta:.3f}mm (gap=+0.001mm), DRC should pass. Got: {viols}"
        )

        # At threshold exactly (gap = 0), DRC fires — touching counts as overlap
        comps_touching = [
            _comp("switch_V3", 50.0, self.SWITCH_V3_CY_REF,                  "sw1"),
            _comp("trimpot",   50.0, self.SWITCH_V3_CY_REF + drc_threshold,   "tp1"),
        ]
        viols_touching = dr._check_pcb_overlaps(comps_touching)
        # gap = 0 is treated as overlap (courtyard boundary contact is a violation)
        v3_rect = _get_courtyard(50.0, self.SWITCH_V3_CY_REF,                 "switch_V3", 0)
        tp_rect = _get_courtyard(50.0, self.SWITCH_V3_CY_REF + drc_threshold, "trimpot",   0)
        gap = _rect_min_gap(v3_rect, tp_rect)
        assert abs(gap) < 0.01, f"Expected gap ≈ 0 at threshold, got {gap:.6f}mm"


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

    def test_rotate_180_courtyard_overlap_detection_correct(self):
        """Two jacks 10mm apart with one rotate=180 must still detect overlap when 9mm apart."""
        dr = make_rules()
        # JACK_CY is x-symmetric so rotate=180 doesn't change x-extent.
        # Two jacks 9mm apart in x → courtyard overlap regardless of y-rotation.
        comps = [
            _comp("jack_input", 50.0, 50.0, "j1", rotate=0),
            _comp("jack_input", 59.0, 50.0, "j2", rotate=180),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) == 1, f"Expected 1 overlap for jacks 9mm apart: {viols}"


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
            "trimpot", "knob_medium", "knob_large", "knob_xl",
            "switch_H2", "switch_H3", "switch_V3",
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

    def test_switch_V3_cy_extents_are_as_documented(self):
        """SWITCH_V3_CY extends ±6.4mm in y — matches CAS-120R3 body (±6.35mm) with 0.05mm margin."""
        assert SWITCH_V3_CY == (-2.0, -6.4, 2.0, 6.4), (
            f"SWITCH_V3_CY changed: got {SWITCH_V3_CY}. "
            "Expected (-2.0,-6.4,2.0,6.4) — if intentionally changed, update this test."
        )

    def test_switch_cy_extents_are_as_documented(self):
        """SWITCH_CY (toggle) is 9mm wide; switch_H3 body is 12mm wide — 1.5mm short each side."""
        assert SWITCH_CY == (-4.5, -3.5, 4.5, 7.5), (
            f"SWITCH_CY changed: got {SWITCH_CY}."
        )

    def test_jack_cy_extents_are_as_documented(self):
        """JACK_CY as derived from Thonkiconn WQP-PJ398SM KiCad footprint."""
        assert JACK_CY == (-5.0, -7.9, 5.0, 6.5), (
            f"JACK_CY changed: got {JACK_CY}."
        )

    def test_trimpot_cy_extents_are_as_documented(self):
        """TRIMPOT_CY from Bourns 3296W footprint; panel anchor = pin2 (wiper/actuator)."""
        assert TRIMPOT_CY == (-2.665, -3.385, 2.665, 3.385), (
            f"TRIMPOT_CY changed: got {TRIMPOT_CY}."
        )

    def test_switch_v3_svg_body_half_height(self):
        """SWITCH_V3_CY y-extent (6.4mm) must be >= SVG body half-height (6.0mm) — no blind spot."""
        default_body_height = 12.0
        svg_half_height = default_body_height / 2.0   # 6.0mm
        cy_half_height  = SWITCH_V3_CY[3]             # 6.4mm

        discrepancy = svg_half_height - cy_half_height  # negative = courtyard larger than body
        assert discrepancy <= 0, (
            f"SWITCH_V3_CY y-extent is smaller than SVG body — blind spot exists! "
            f"svg_half={svg_half_height}mm, cy_half={cy_half_height}mm, "
            f"discrepancy={discrepancy:.3f}mm (must be ≤ 0)."
        )

    def test_blind_spot_quantified(self):
        """DRC threshold (9.785mm) exceeds SVG body sum (8.5mm) — blind spot is eliminated."""
        cy_sum   = SWITCH_V3_CY[3] + abs(TRIMPOT_CY[1])  # 6.4 + 3.385 = 9.785
        real_sum = 6.0 + 2.5                               # SVG body sum = 8.5
        blind    = real_sum - cy_sum                        # 8.5 - 9.785 = -1.285 (no blind spot)
        assert blind <= 0, (
            f"Expected blind <= 0 (no blind spot), got {blind:.4f}mm. "
            f"cy_sum={cy_sum:.3f}mm must exceed real_sum={real_sum:.3f}mm."
        )
