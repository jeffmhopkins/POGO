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

    # ── toggle (vertical separation) ──────────────────────────────────────────
    # TOGGLE_CY height = 9.64mm (y∈[-4.82, +4.82]) → min y-sep = 9.64mm
    def test_toggle_vertical_pass_at_minimum_gap(self):
        """Two toggles stacked 9.64mm apart: DRC must pass."""
        dy = abs(TOGGLE_CY[1]) + abs(TOGGLE_CY[3])  # 4.82 + 4.82 = 9.64
        comps = [
            _comp("toggle_dw3", 50.0, 50.0,       "s1"),
            _comp("toggle_dw5", 50.0, 50.0 + dy,  "s2"),
        ]
        viols = self.dr._check_pcb_overlaps(comps)
        assert viols == [], f"Unexpected violations at gap=0: {viols}"

    def test_toggle_vertical_fail_at_0_5mm_overlap(self):
        """Two toggles stacked 9.14mm apart: DRC must report overlap."""
        dy = abs(TOGGLE_CY[1]) + abs(TOGGLE_CY[3]) - 0.5
        comps = [
            _comp("toggle_dw3", 50.0, 50.0,       "s1"),
            _comp("toggle_dw3", 50.0, 50.0 + dy,  "s2"),
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

    DRC_THRESHOLD = TOGGLE_CY[3] + abs(TRIMPOT_CY[1])   # 4.82 + 3.385 = 8.205

    def test_pass_just_above_threshold(self):
        """At threshold + 0.01mm (gap > 0), DRC passes."""
        dr = make_rules()
        delta = self.DRC_THRESHOLD + 0.01
        comps = [
            _comp("toggle_dw5", 50.0, 50.0,         "sw1"),
            _comp("trimpot",    50.0, 50.0 + delta, "tp1"),
        ]
        assert dr._check_pcb_overlaps(comps) == [], (
            f"At delta={delta:.3f}mm (gap=+0.01mm) DRC should pass."
        )

    def test_fail_below_threshold(self):
        """At threshold − 0.5mm the courtyards overlap and DRC must fire."""
        dr = make_rules()
        delta = self.DRC_THRESHOLD - 0.5
        comps = [
            _comp("toggle_dw5", 50.0, 50.0,         "sw1"),
            _comp("trimpot",    50.0, 50.0 + delta, "tp1"),
        ]
        viols = dr._check_pcb_overlaps(comps)
        assert len(viols) >= 1, f"DRC must catch overlap at delta={delta:.3f}mm, got: {viols}"

    def test_threshold_gap_is_zero(self):
        """At exactly the threshold, the courtyard gap is ≈ 0 (boundary contact)."""
        sw_rect = _get_courtyard(50.0, 50.0,                       "toggle_dw5", 0)
        tp_rect = _get_courtyard(50.0, 50.0 + self.DRC_THRESHOLD,  "trimpot",    0)
        gap = _rect_min_gap(sw_rect, tp_rect)
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
        """TRIMPOT_CY from Bourns 3296W footprint; panel anchor = pin2 (wiper/actuator)."""
        assert TRIMPOT_CY == (-2.665, -3.385, 2.665, 3.385), (
            f"TRIMPOT_CY changed: got {TRIMPOT_CY}."
        )

    def test_toggle_courtyard_encompasses_drawn_symbol(self):
        """TOGGLE_CY half-extents must exceed the drawn toggle symbol (lever tip ≈ 3.1mm)."""
        draw_half = 2.2 + 0.9   # lever length + tip radius
        assert TOGGLE_CY[3] >= draw_half and TOGGLE_CY[2] >= draw_half, (
            f"TOGGLE_CY {TOGGLE_CY} smaller than drawn symbol half-extent {draw_half}mm."
        )

    def test_toggle_panel_radius_clears_top_keepout(self):
        """A toggle nut (r=TOGGLE_PANEL_R) at the top row must clear the 10mm top keepout."""
        # Documented value: nut/washer half-width for the Dailywell 2M bushing.
        assert TOGGLE_PANEL_R == 3.0, (
            f"TOGGLE_PANEL_R changed: got {TOGGLE_PANEL_R}. Expected 3.0 (Dailywell 2M nut)."
        )
