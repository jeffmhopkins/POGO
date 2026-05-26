"""panel_rules.py — Design-rule checking for the POGO panel.

Loads constants from the YAML design_rules block and exposes helper
geometry functions plus a DRC checker.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# ── PCB courtyard dimensions (mm, relative to component origin) ───────────────
# Thonkiconn PJ301M-12: origin = panel hole centre
#   Source: Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles.kicad_mod
JACK_CY = (-5.0, -1.42, 5.0, 12.98)   # (x1, y1, x2, y2)

# Alpha RD901F 9mm: origin = shaft centre (derived from footprint pin 1 origin)
#   Source: Potentiometer_Alpha_RD901F-40-00D_Single_Vertical_CircularHoles.kicad_mod
#   Footprint origin = pin1; shaft centre = (7.5, 2.5) in footprint coords
#   Courtyard footprint coords: x∈[-1.15, 12.6], y∈[-4.17, 9.17]
#   → relative to shaft: x∈[-8.65, 5.1], y∈[-6.67, 6.67]
POT_CY  = (-8.65, -6.67, 5.1, 6.67)

# Sub-mini toggle switch (SPDT THT, e.g. C&K M-series)
# Panel hole: 6.3mm Ø → r=3.15mm
# PCB courtyard: relative to switch body centre
SWITCH_PANEL_R = 3.15
SWITCH_CY      = (-4.5, -3.5, 4.5, 7.5)

# 3mm LED THT
# Panel hole: 3.2mm Ø → r=1.6mm
# PCB courtyard: relative to LED body centre
LED_PANEL_R = 1.6
LED_CY      = (-2.0, -1.5, 2.0, 4.0)

SWITCH_TYPES = {"switch_H2", "switch_H3", "switch_V3"}
LED_TYPES    = {"led", "led_labeled"}

# Minimum clearance from PCB courtyard edge to mounting hole centre (M3, r≈3.5mm)
MOUNTING_HOLE_CLEARANCE_MM = 3.5

JACK_TYPES = {"jack_input", "jack_output"}
POT_TYPES  = {"trimpot", "knob_medium", "knob_large", "knob_xl"}


def _get_courtyard(cx: float, cy: float, ctype: str) -> tuple[float, float, float, float] | None:
    """Return (x1, y1, x2, y2) PCB courtyard rect or None if the type has no footprint."""
    if ctype in JACK_TYPES:
        x1, y1, x2, y2 = JACK_CY
        return (cx + x1, cy + y1, cx + x2, cy + y2)
    if ctype in POT_TYPES:
        x1, y1, x2, y2 = POT_CY
        return (cx + x1, cy + y1, cx + x2, cy + y2)
    if ctype in SWITCH_TYPES:
        x1, y1, x2, y2 = SWITCH_CY
        return (cx + x1, cy + y1, cx + x2, cy + y2)
    if ctype in LED_TYPES:
        x1, y1, x2, y2 = LED_CY
        return (cx + x1, cy + y1, cx + x2, cy + y2)
    return None


def _rect_overlap(r1: tuple, r2: tuple) -> tuple[float, float]:
    """Return (x_overlap_mm, y_overlap_mm); positive = overlap in that axis."""
    dx = min(r1[2], r2[2]) - max(r1[0], r2[0])
    dy = min(r1[3], r2[3]) - max(r1[1], r2[1])
    return dx, dy


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
            return (
                f"JACK '{label}' at cy={cy:.2f}: nut top={top_edge:.2f} "
                f"encroaches TOP keepout ({self.top_keepout:.2f})"
            )
        if bot_edge > self.bot_keepout_start:
            return (
                f"JACK '{label}' at cy={cy:.2f}: nut bottom={bot_edge:.2f} "
                f"exceeds BOT keepout start ({self.bot_keepout_start:.2f})"
            )
        return None

    def _pot_keepout_violation(self, cx: float, cy: float, label: str) -> str | None:
        """Return violation string if pot nut encroaches on keepout, else None."""
        top_edge = cy - self.pot_nut_r
        bot_edge = cy + self.pot_nut_r
        if top_edge < self.top_keepout:
            return (
                f"POT '{label}' at cy={cy:.2f}: nut top={top_edge:.2f} "
                f"encroaches TOP keepout ({self.top_keepout:.2f})"
            )
        if bot_edge > self.bot_keepout_start:
            return (
                f"POT '{label}' at cy={cy:.2f}: nut bottom={bot_edge:.2f} "
                f"exceeds BOT keepout start ({self.bot_keepout_start:.2f})"
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
        [PCB KEEPOUT] entries are informational warnings (not blocking errors).
        """
        violations: list[str] = []
        violations.extend(self._check_nut_keepout(components))
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
            elif ctype in SWITCH_TYPES:
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
        return out

    def _check_pcb_overlaps(self, components: list[dict[str, Any]]) -> list[str]:
        """PCB courtyard rectangles must not overlap each other."""
        out: list[str] = []
        # Build index of components that have PCB footprints
        footprinted = []
        for comp in components:
            ctype = comp.get("type", "")
            if ctype not in JACK_TYPES and ctype not in POT_TYPES:
                continue
            cx = float(comp.get("cx", 0))
            cy = float(comp.get("cy", 0))
            rect = _get_courtyard(cx, cy, ctype)
            if rect:
                footprinted.append((comp, rect))

        for i in range(len(footprinted)):
            for j in range(i + 1, len(footprinted)):
                ca, ra = footprinted[i]
                cb, rb = footprinted[j]
                dx, dy = _rect_overlap(ra, rb)
                if dx > 0 and dy > 0:
                    la = _comp_label(ca)
                    lb = _comp_label(cb)
                    out.append(
                        f"[PCB OVERLAP] '{la}' ({ca['type']}) ↔ '{lb}' ({cb['type']})"
                        f" — overlap {dx:.2f}×{dy:.2f}mm"
                    )
        return out

    def _check_pcb_keepout(self, components: list[dict[str, Any]]) -> list[str]:
        """PCB courtyard rectangles that extend into top/bottom keep-out zones.

        These are informational [PCB KEEPOUT] warnings — expected for through-panel
        components near panel edges — not blocking errors.
        """
        out: list[str] = []
        for comp in components:
            ctype = comp.get("type", "")
            cx = float(comp.get("cx", 0))
            cy = float(comp.get("cy", 0))
            rect = _get_courtyard(cx, cy, ctype)
            if rect is None:
                continue
            rx1, ry1, rx2, ry2 = rect
            label = _comp_label(comp)
            if ry1 < self.top_keepout:
                out.append(
                    f"[PCB KEEPOUT] '{label}' ({ctype}) courtyard top={ry1:.2f}"
                    f" extends into TOP keepout ({self.top_keepout:.2f}) — informational"
                )
            if ry2 > self.bot_keepout_start:
                out.append(
                    f"[PCB KEEPOUT] '{label}' ({ctype}) courtyard bottom={ry2:.2f}"
                    f" extends into BOT keepout ({self.bot_keepout_start:.2f}) — informational"
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
            ctype = comp.get("type", "")
            cx = float(comp.get("cx", 0))
            cy = float(comp.get("cy", 0))
            rect = _get_courtyard(cx, cy, ctype)
            if rect is None:
                continue
            cx1, cy1, cx2, cy2 = rect
            for mh in mounting_holes:
                hx, hy = float(mh["cx"]), float(mh["cy"])
                # Closest point on rect to hole centre
                near_x = max(cx1, min(hx, cx2))
                near_y = max(cy1, min(hy, cy2))
                dist   = ((hx - near_x) ** 2 + (hy - near_y) ** 2) ** 0.5
                if dist < r:
                    label = _comp_label(comp)
                    out.append(
                        f"[MH CLEARANCE] '{label}' ({ctype}) footprint"
                        f" {dist:.2f}mm from mounting hole ({hx},{hy})"
                        f" — min {r:.1f}mm required"
                    )
        return out
