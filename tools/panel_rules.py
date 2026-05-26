"""panel_rules.py — Design-rule checking for the POGO panel.

Loads constants from the YAML design_rules block and exposes helper
geometry functions plus a DRC checker.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


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

    def check_all(self, components: list[dict[str, Any]]) -> list[str]:
        """Run DRC on a flat list of component dicts.

        Each dict must have at least: type, cx, cy (or y for slider_label),
        and optionally label/id for the violation message.

        Returns a list of violation strings (empty = no violations).
        """
        violations: list[str] = []

        JACK_TYPES = {"jack_input", "jack_output"}
        POT_TYPES  = {"trimpot", "knob_medium", "knob_large", "knob_xl"}

        for comp in components:
            ctype = comp.get("type", "")
            label = comp.get("label") or comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"
            cx    = float(comp.get("cx", 0))
            cy    = comp.get("cy")

            if cy is None or str(cy).startswith("_"):
                # Placeholder — resolve before checking
                if ctype in JACK_TYPES:
                    cy = self.cv_jack_cy
                elif ctype in POT_TYPES:
                    cy = self.att_cy
                else:
                    continue
            cy = float(cy)

            if ctype in JACK_TYPES:
                v = self._jack_keepout_violation(cx, cy, label)
                if v:
                    violations.append(v)
            elif ctype in POT_TYPES:
                v = self._pot_keepout_violation(cx, cy, label)
                if v:
                    violations.append(v)

        return violations
