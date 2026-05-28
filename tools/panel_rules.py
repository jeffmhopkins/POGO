"""panel_rules.py — Design-rule checking for the POGO panel.

Loads constants from the YAML design_rules block and exposes helper
geometry functions plus a DRC checker.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from panel_kicad import footprint_courtyard as _fp_crtyd  # single source of truth

# ── PCB courtyard dimensions (mm, relative to the component's panel anchor) ───
# These are DERIVED from each component's KiCad footprint F.CrtYd layer via
# panel_kicad.footprint_courtyard() — the .kicad_mod files are the single source
# of truth.  The literal fallbacks document the expected values and guard against
# a missing footprint file (parity with the footprints is enforced by test_drc).
def _cy(ctype: str, fallback: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return _fp_crtyd(ctype) or fallback

# Thonkiconn WQP-PJ398SM jack
JACK_CY = _cy("jack_input", (-5.0, -7.90, 5.0, 6.50))    # (x1, y1, x2, y2)
# Alpha RD901F 9mm pot (anchor = shaft centre)
POT_CY  = _cy("knob_medium", (-8.65, -6.67, 5.1, 6.67))
# Bourns 3296W vertical trimpot (anchor = wiper/actuator)
TRIMPOT_CY = _cy("trimpot", (-2.665, -3.385, 2.665, 3.385))
# Potentiometer_Slider_45mm_Vertical (anchor = travel centre)
SLIDER_V45_CY = _cy("slider_V45", (-7.0, -28.5, 7.0, 28.5))
# 3mm LED THT
LED_CY = _cy("led", (-2.0, -1.5, 2.0, 4.0))
# Sub-mini toggle switch (SPDT THT) — switch_H2
SWITCH_CY = _cy("switch_H2", (-4.5, -3.5, 4.5, 7.5))
# E-Switch EG1218 — 2-position horizontal slide (eg_2pos)
EG1218_CY = _cy("eg_2pos", (-6.05, -2.25, 6.05, 2.25))
# E-Switch EG2301 — 3-position vertical slide (eg_3pos)
EG2301_V_CY = _cy("eg_3pos", (-3.5, -8.25, 3.5, 8.25))

# ── Panel-face hole/slot dimensions (NOT courtyards; used by nut/keepout checks) ──
SWITCH_PANEL_R = 3.15      # sub-mini toggle 6.3mm Ø hole
SWITCH_V3_PANEL_R = 1.0    # legacy 3-pos vertical slide actuator slot half-width
LED_PANEL_R = 1.6          # 3mm LED 3.2mm Ø hole
TRIMPOT_PANEL_R = 2.5      # trimpot actuator hole
SLIDER_V45_PANEL_W = 1.5   # 45mm slider slot half-width
EG1218_PANEL_H = 1.5       # EG1218 panel slot half-height
EG2301_V_PANEL_W = 3.25    # EG2301 panel slot half-width
EG2301_V_PANEL_H = 8.25    # EG2301 panel slot half-height

# Legacy slide switches with no dedicated footprint (unused in the current panel;
# SW_SPDT placeholder courtyard would mis-size them) — kept hand-defined.
SWITCH_V3_CY = (-2.0, -6.4, 2.0, 6.4)    # Nidec Copal CAS-120R3 body ±6.35mm + margin
SWITCH_H3_CY = (-6.0, -3.5, 6.0, 7.5)    # 12mm-wide 3-pos horizontal slide

EG_2POS_TYPES = {"eg_2pos"}
EG_3POS_TYPES = {"eg_3pos"}
SLIDER_TYPES = {"slider_V45"}

H_SWITCH_TYPES  = {"switch_H2", "switch_H3"}
V3_SWITCH_TYPES = {"switch_V3"}
SWITCH_TYPES    = H_SWITCH_TYPES | V3_SWITCH_TYPES | EG_2POS_TYPES | EG_3POS_TYPES
LED_TYPES       = {"led", "led_labeled"}

# Minimum clearance from PCB courtyard edge to mounting hole centre (M3, r≈3.5mm)
MOUNTING_HOLE_CLEARANCE_MM = 3.5

JACK_TYPES = {"jack_input", "jack_output"}
POT_TYPES  = {"trimpot", "knob_medium", "knob_large", "knob_xl"}


def _rotate_rect(
    rect: tuple[float, float, float, float],
    degrees: int,
) -> tuple[float, float, float, float]:
    """Rotate a (x1,y1,x2,y2) bounding rect about the origin by degrees CW (0/90/180/270).

    Used to rotate PCB courtyard constants before applying to component position.
    Example: JACK_CY rotated 180° flips the body from extending downward to upward,
    allowing bottom-row jacks to be mounted inverted so the PCB body points up.
    """
    if degrees == 0:
        return rect
    x1, y1, x2, y2 = rect
    corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
    if degrees == 90:
        rotated = [(y, -x) for x, y in corners]
    elif degrees == 180:
        rotated = [(-x, -y) for x, y in corners]
    elif degrees == 270:
        rotated = [(-y, x) for x, y in corners]
    else:
        return rect
    xs = [p[0] for p in rotated]
    ys = [p[1] for p in rotated]
    return (min(xs), min(ys), max(xs), max(ys))


def _get_courtyard(
    cx: float,
    cy: float,
    ctype: str,
    rotate: int = 0,
) -> tuple[float, float, float, float] | None:
    """Return (x1, y1, x2, y2) PCB courtyard rect or None if the type has no footprint.

    rotate (0/90/180/270 CW) rotates the courtyard template before positioning.
    Useful for inverting jacks (rotate=180 moves body above hole instead of below).
    """
    base: tuple[float, float, float, float] | None = None
    if ctype in JACK_TYPES:
        base = JACK_CY
    elif ctype == "trimpot":
        base = TRIMPOT_CY
    elif ctype in POT_TYPES:
        base = POT_CY
    elif ctype in SLIDER_TYPES:
        base = SLIDER_V45_CY
    elif ctype in V3_SWITCH_TYPES:
        base = SWITCH_V3_CY
    elif ctype == "switch_H3":
        base = SWITCH_H3_CY
    elif ctype == "switch_H2":
        base = SWITCH_CY
    elif ctype in LED_TYPES:
        base = LED_CY
    elif ctype in EG_2POS_TYPES:
        base = EG1218_CY
    elif ctype in EG_3POS_TYPES:
        base = EG2301_V_CY
    if base is None:
        return None
    x1, y1, x2, y2 = _rotate_rect(base, rotate)
    return (cx + x1, cy + y1, cx + x2, cy + y2)


def _rect_overlap(r1: tuple, r2: tuple) -> tuple[float, float]:
    """Return (x_overlap_mm, y_overlap_mm); positive = overlap in that axis."""
    dx = min(r1[2], r2[2]) - max(r1[0], r2[0])
    dy = min(r1[3], r2[3]) - max(r1[1], r2[1])
    return dx, dy


def _rect_min_gap(r1: tuple, r2: tuple) -> float:
    """Signed minimum gap between two axis-aligned rects.

    Returns positive = gap (distance between nearest edges), negative = overlap depth.
    For overlapping rects, returns the negative of the minimum penetration axis.
    """
    sep_x = max(0.0, max(r1[0], r2[0]) - min(r1[2], r2[2]))
    sep_y = max(0.0, max(r1[1], r2[1]) - min(r1[3], r2[3]))
    if sep_x > 0 and sep_y > 0:
        return (sep_x ** 2 + sep_y ** 2) ** 0.5
    if sep_x > 0 or sep_y > 0:
        return max(sep_x, sep_y)
    ov_x = min(r1[2], r2[2]) - max(r1[0], r2[0])
    ov_y = min(r1[3], r2[3]) - max(r1[1], r2[1])
    return -min(ov_x, ov_y)


def get_panel_r(ctype: str, rules: Any) -> float:
    """Return the panel-face nut / hole radius (mm) for a component type.

    For slide switches (EG series) this returns 0 — they have rectangular slots,
    not circular holes, so panel-face clearance is checked via PCB courtyard overlap
    rather than circular nut clearance.
    """
    if ctype in JACK_TYPES:
        return rules.jack_nut_r
    if ctype == "trimpot":
        return TRIMPOT_PANEL_R
    if ctype in POT_TYPES:
        return rules.pot_nut_r
    if ctype in SLIDER_TYPES:
        return SLIDER_V45_PANEL_W
    if ctype in V3_SWITCH_TYPES:
        return SWITCH_V3_PANEL_R
    if ctype in H_SWITCH_TYPES:
        return SWITCH_PANEL_R
    if ctype in LED_TYPES:
        return LED_PANEL_R
    # EG_2POS_TYPES and EG_3POS_TYPES: rectangular slot, no circular nut radius
    return 0.0


def _comp_label(comp: dict) -> str:
    return (
        comp.get("id")
        or comp.get("label")
        or comp.get("cpp_id")
        or comp.get("cpp_param")
        or "?"
    )


@dataclass
class DesignRules:
    top_keepout: float = 10.0
    bot_keepout_start: float = 118.5
    cv_jack_cy: float = 112.5
    att_offset: float = -10.75
    jack_label_dy: float = 7.0
    output_rect_dy: float = -1.76
    output_rect_h: float = 2.26
    output_rect_rx: float = 0.6
    jack_pitch: float = 10.16
    indicator_length: float = 2.5
    x_offset: float = 0.0       # mm to shift all zone/component x coords inside panel

    # Footprint radii (loaded separately from footprints block)
    jack_nut_r: float = 5.0
    pot_nut_r: float = 5.5

    # Derived properties
    @property
    def att_cy(self) -> float:
        return self.cv_jack_cy + self.att_offset

    def label_y(self, cy: float) -> float:
        """Label centre-line below a jack/control at cy."""
        return cy + self.jack_label_dy

    def rect_y(self, label_y: float) -> float:
        """Top of output-border rect given label_y."""
        return label_y + self.output_rect_dy

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "DesignRules":
        """Construct from the parsed YAML dict (design_rules + footprints keys)."""
        dr = data.get("design_rules", {})
        fp = data.get("footprints", {})
        obj = cls(
            top_keepout=float(dr.get("top_keepout", cls.top_keepout)),
            bot_keepout_start=float(dr.get("bot_keepout_start", cls.bot_keepout_start)),
            cv_jack_cy=float(dr.get("cv_jack_cy", cls.cv_jack_cy)),
            att_offset=float(dr.get("att_offset", cls.att_offset)),
            jack_label_dy=float(dr.get("jack_label_dy", cls.jack_label_dy)),
            output_rect_dy=float(dr.get("output_rect_dy", cls.output_rect_dy)),
            output_rect_h=float(dr.get("output_rect_h", cls.output_rect_h)),
            output_rect_rx=float(dr.get("output_rect_rx", cls.output_rect_rx)),
            jack_pitch=float(dr.get("jack_pitch", cls.jack_pitch)),
            indicator_length=float(dr.get("indicator_length", cls.indicator_length)),
            x_offset=float(dr.get("x_offset", cls.x_offset)),
        )
        # Pull nut radii from footprints sub-block
        jack_fp = fp.get("jack_thonkiconn", {})
        pot_fp  = fp.get("pot_alpha9mm", {})
        obj.jack_nut_r = float(jack_fp.get("nut_r_mm", cls.jack_nut_r))
        obj.pot_nut_r  = float(pot_fp.get("nut_r_mm",  cls.pot_nut_r))
        return obj

    # ── DRC helpers ──────────────────────────────────────────────────────────

    def _jack_keepout_violation(self, cx: float, cy: float, label: str) -> str | None:
        """Return violation string if jack nut encroaches on keepout, else None."""
        top_edge = cy - self.jack_nut_r
        bot_edge = cy + self.jack_nut_r
        if top_edge < self.top_keepout:
            excess = self.top_keepout - top_edge
            return (
                f"JACK '{label}' @ cx={cx:.2f},cy={cy:.2f}:"
                f" nut top={top_edge:.2f}mm breaches TOP keepout ({self.top_keepout:.2f}mm)"
                f" — move down by ≥{excess:.2f}mm"
            )
        if bot_edge > self.bot_keepout_start:
            excess = bot_edge - self.bot_keepout_start
            return (
                f"JACK '{label}' @ cx={cx:.2f},cy={cy:.2f}:"
                f" nut bottom={bot_edge:.2f}mm breaches BOT keepout ({self.bot_keepout_start:.2f}mm)"
                f" — move up by ≥{excess:.2f}mm"
            )
        return None

    def _pot_keepout_violation(self, cx: float, cy: float, label: str) -> str | None:
        """Return violation string if pot nut encroaches on keepout, else None."""
        top_edge = cy - self.pot_nut_r
        bot_edge = cy + self.pot_nut_r
        if top_edge < self.top_keepout:
            excess = self.top_keepout - top_edge
            return (
                f"POT '{label}' @ cx={cx:.2f},cy={cy:.2f}:"
                f" nut top={top_edge:.2f}mm breaches TOP keepout ({self.top_keepout:.2f}mm)"
                f" — move down by ≥{excess:.2f}mm"
            )
        if bot_edge > self.bot_keepout_start:
            excess = bot_edge - self.bot_keepout_start
            return (
                f"POT '{label}' @ cx={cx:.2f},cy={cy:.2f}:"
                f" nut bottom={bot_edge:.2f}mm breaches BOT keepout ({self.bot_keepout_start:.2f}mm)"
                f" — move up by ≥{excess:.2f}mm"
            )
        return None

    def check_all(
        self,
        components: list[dict[str, Any]],
        mounting_holes: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Run all DRC checks on a flat list of resolved component dicts.

        Returns a list of violation strings (empty = no violations).
        Violations are prefixed with a category tag, e.g. [NUT KEEPOUT].
        All violations are blocking errors.
        """
        violations: list[str] = []
        violations.extend(self._check_nut_keepout(components))
        violations.extend(self._check_panel_clearance(components))
        violations.extend(self._check_pcb_overlaps(components))
        if mounting_holes:
            violations.extend(self._check_mounting_clearance(components, mounting_holes))
        violations.extend(self._check_pcb_keepout(components))
        return violations

    # ── Individual check passes ───────────────────────────────────────────────

    def _check_nut_keepout(self, components: list[dict[str, Any]]) -> list[str]:
        """Panel-face nut circles must not enter the rail keep-out zones."""
        out: list[str] = []
        for comp in components:
            ctype = comp.get("type", "")
            label = _comp_label(comp)
            cx    = float(comp.get("cx", 0))
            cy    = float(comp.get("cy", 0))

            if ctype in JACK_TYPES:
                v = self._jack_keepout_violation(cx, cy, label)
                if v:
                    out.append(f"[NUT KEEPOUT] {v}")
            elif ctype in POT_TYPES:
                v = self._pot_keepout_violation(cx, cy, label)
                if v:
                    out.append(f"[NUT KEEPOUT] {v}")
            elif ctype in V3_SWITCH_TYPES:
                top_edge = cy - SWITCH_V3_PANEL_R
                bot_edge = cy + SWITCH_V3_PANEL_R
            elif ctype in H_SWITCH_TYPES:
                top_edge = cy - SWITCH_PANEL_R
                bot_edge = cy + SWITCH_PANEL_R
                if top_edge < self.top_keepout:
                    out.append(
                        f"[NUT KEEPOUT] SWITCH '{label}' at cy={cy:.2f}: hole top={top_edge:.2f}"
                        f" encroaches TOP keepout ({self.top_keepout:.2f})"
                    )
                if bot_edge > self.bot_keepout_start:
                    out.append(
                        f"[NUT KEEPOUT] SWITCH '{label}' at cy={cy:.2f}: hole bottom={bot_edge:.2f}"
                        f" exceeds BOT keepout start ({self.bot_keepout_start:.2f})"
                    )
            elif ctype in LED_TYPES:
                top_edge = cy - LED_PANEL_R
                bot_edge = cy + LED_PANEL_R
                if top_edge < self.top_keepout:
                    out.append(
                        f"[NUT KEEPOUT] LED '{label}' at cy={cy:.2f}: hole top={top_edge:.2f}"
                        f" encroaches TOP keepout ({self.top_keepout:.2f})"
                    )
                if bot_edge > self.bot_keepout_start:
                    out.append(
                        f"[NUT KEEPOUT] LED '{label}' at cy={cy:.2f}: hole bottom={bot_edge:.2f}"
                        f" exceeds BOT keepout start ({self.bot_keepout_start:.2f})"
                    )
            elif ctype in EG_2POS_TYPES:
                # Rectangular slot: check y-extent only (±EG1218_PANEL_H)
                top_edge = cy - EG1218_PANEL_H
                bot_edge = cy + EG1218_PANEL_H
                if top_edge < self.top_keepout:
                    out.append(
                        f"[NUT KEEPOUT] EG2POS '{label}' at cy={cy:.2f}: slot top={top_edge:.2f}"
                        f" encroaches TOP keepout ({self.top_keepout:.2f})"
                    )
                if bot_edge > self.bot_keepout_start:
                    out.append(
                        f"[NUT KEEPOUT] EG2POS '{label}' at cy={cy:.2f}: slot bottom={bot_edge:.2f}"
                        f" exceeds BOT keepout ({self.bot_keepout_start:.2f})"
                    )
            elif ctype in EG_3POS_TYPES:
                # Rectangular slot: check full y-extent of actuator travel (±EG2301_V_PANEL_H)
                top_edge = cy - EG2301_V_PANEL_H
                bot_edge = cy + EG2301_V_PANEL_H
                if top_edge < self.top_keepout:
                    out.append(
                        f"[NUT KEEPOUT] EG3POS '{label}' at cy={cy:.2f}: slot top={top_edge:.2f}"
                        f" encroaches TOP keepout ({self.top_keepout:.2f})"
                    )
                if bot_edge > self.bot_keepout_start:
                    out.append(
                        f"[NUT KEEPOUT] EG3POS '{label}' at cy={cy:.2f}: slot bottom={bot_edge:.2f}"
                        f" exceeds BOT keepout ({self.bot_keepout_start:.2f})"
                    )
        return out

    def _check_panel_clearance(self, components: list[dict[str, Any]]) -> list[str]:
        """Panel-face nut / hole circles must not overlap each other.

        Each component has a circular nut (jacks, pots) or hole (switches, LEDs) on
        the panel face. If two circles overlap the hardware will physically clash —
        nuts can't be tightened and holes may intersect.
        """
        out: list[str] = []
        circles: list[tuple] = []
        for comp in components:
            ctype = comp.get("type", "")
            cx    = float(comp.get("cx", 0))
            cy    = float(comp.get("cy", 0))
            r     = get_panel_r(ctype, self)
            if r > 0:
                circles.append((cx, cy, r, _comp_label(comp), ctype))

        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                cx1, cy1, r1, l1, t1 = circles[i]
                cx2, cy2, r2, l2, t2 = circles[j]
                dist     = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5
                min_dist = r1 + r2
                if dist < min_dist:
                    overlap = min_dist - dist
                    out.append(
                        f"[NUT CLEARANCE] '{l1}' ({t1} @ cx={cx1:.2f},cy={cy1:.2f}, r={r1}mm)"
                        f" ↔ '{l2}' ({t2} @ cx={cx2:.2f},cy={cy2:.2f}, r={r2}mm)"
                        f" — panel circles overlap {overlap:.2f}mm"
                        f" (centre-to-centre={dist:.2f}mm, need≥{min_dist:.2f}mm;"
                        f" increase separation by ≥{overlap:.2f}mm)"
                    )
        return out

    def _check_pcb_overlaps(self, components: list[dict[str, Any]]) -> list[str]:
        """PCB courtyard rectangles must not overlap each other.

        Checks all component types that have a PCB footprint (jacks, pots,
        switches, LEDs) — not just jacks and pots.
        """
        out: list[str] = []
        footprinted = []
        for comp in components:
            ctype  = comp.get("type", "")
            cx     = float(comp.get("cx", 0))
            cy     = float(comp.get("cy", 0))
            rotate = int(comp.get("rotate", 0))
            rect   = _get_courtyard(cx, cy, ctype, rotate)
            if rect:
                footprinted.append((comp, rect))

        for i in range(len(footprinted)):
            for j in range(i + 1, len(footprinted)):
                ca, ra = footprinted[i]
                cb, rb = footprinted[j]
                dx, dy = _rect_overlap(ra, rb)
                if dx > 0 and dy > 0:
                    la  = _comp_label(ca)
                    lb  = _comp_label(cb)
                    cxa = float(ca.get("cx", 0)); cya = float(ca.get("cy", 0))
                    cxb = float(cb.get("cx", 0)); cyb = float(cb.get("cy", 0))
                    gap = _rect_min_gap(ra, rb)
                    out.append(
                        f"[PCB OVERLAP] '{la}' ({ca['type']} @ cx={cxa:.2f},cy={cya:.2f})"
                        f" ↔ '{lb}' ({cb['type']} @ cx={cxb:.2f},cy={cyb:.2f})"
                        f" — courtyard overlap {dx:.2f}×{dy:.2f}mm (gap={gap:.2f}mm)"
                    )
        return out

    def _check_pcb_keepout(self, components: list[dict[str, Any]]) -> list[str]:
        """PCB courtyard rectangles that extend into top/bottom keep-out zones.

        The PCB is physically bounded by the Eurorack rails, so any courtyard
        rectangle that extends past the keep-out boundary is a real placement error —
        the component body would be inside the rail and cannot be manufactured.
        """
        out: list[str] = []
        for comp in components:
            ctype  = comp.get("type", "")
            cx     = float(comp.get("cx", 0))
            cy     = float(comp.get("cy", 0))
            rotate = int(comp.get("rotate", 0))
            rect   = _get_courtyard(cx, cy, ctype, rotate)
            if rect is None:
                continue
            rx1, ry1, rx2, ry2 = rect
            label = _comp_label(comp)
            rot_s = f" rotate={rotate}°" if rotate else ""
            if ry1 < self.top_keepout:
                excess = self.top_keepout - ry1
                out.append(
                    f"[PCB KEEPOUT] '{label}' ({ctype} @ cx={cx:.2f},cy={cy:.2f}{rot_s})"
                    f" courtyard top={ry1:.2f}mm breaches TOP keepout ({self.top_keepout:.2f}mm)"
                    f" by {excess:.2f}mm — move component down by ≥{excess:.2f}mm"
                )
            if ry2 > self.bot_keepout_start:
                excess = ry2 - self.bot_keepout_start
                out.append(
                    f"[PCB KEEPOUT] '{label}' ({ctype} @ cx={cx:.2f},cy={cy:.2f}{rot_s})"
                    f" courtyard bottom={ry2:.2f}mm breaches BOT keepout ({self.bot_keepout_start:.2f}mm)"
                    f" by {excess:.2f}mm — move up by ≥{excess:.2f}mm or add rotate:180"
                )
        return out

    def _check_mounting_clearance(
        self,
        components: list[dict[str, Any]],
        mounting_holes: list[dict[str, Any]],
    ) -> list[str]:
        """PCB courtyard must not intrude within MOUNTING_HOLE_CLEARANCE_MM of each mounting hole."""
        out: list[str] = []
        r = MOUNTING_HOLE_CLEARANCE_MM
        for comp in components:
            ctype  = comp.get("type", "")
            cx     = float(comp.get("cx", 0))
            cy     = float(comp.get("cy", 0))
            rotate = int(comp.get("rotate", 0))
            rect   = _get_courtyard(cx, cy, ctype, rotate)
            if rect is None:
                continue
            cx1, cy1, cx2, cy2 = rect
            for mh in mounting_holes:
                hx, hy = float(mh["cx"]), float(mh["cy"])
                near_x = max(cx1, min(hx, cx2))
                near_y = max(cy1, min(hy, cy2))
                dist   = ((hx - near_x) ** 2 + (hy - near_y) ** 2) ** 0.5
                if dist < r:
                    label   = _comp_label(comp)
                    deficit = r - dist
                    out.append(
                        f"[MH CLEARANCE] '{label}' ({ctype} @ cx={cx:.2f},cy={cy:.2f})"
                        f" PCB courtyard is {dist:.2f}mm from mounting hole M3 @ ({hx},{hy})"
                        f" — need ≥{r:.1f}mm; move component away by ≥{deficit:.2f}mm"
                    )
        return out
