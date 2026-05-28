"""panel_cpp.py — Generate VCV Rack C++ widget stub lines from panel data.

Returns a multi-line string of addParam / addInput / addOutput / addChild
calls matching Pogo.cpp style.
"""

from __future__ import annotations
from typing import Any


# ── VCV Rack type mapping ─────────────────────────────────────────────────────

_KNOB_TYPE = {
    "trimpot":    "Trimpot",
    "slider":      "PogoSlider",
}

# Single `knob` type sized by cap_mm (diameter); pick the nearest stock VCV knob.
def _knob_widget(cap_mm: float) -> str:
    if cap_mm < 11.0:
        return "RoundBlackKnob"       # ~9mm
    if cap_mm < 16.0:
        return "RoundLargeBlackKnob"  # ~14mm
    return "RoundHugeBlackKnob"       # ~18mm

_SWITCH_TYPE = {
    "toggle_dw3": "PogoToggle2",
    "toggle_dw5": "PogoToggle3",
}

_JACK_TYPE = "PJ301MPort"
_LED_TYPE  = "SmallLight<RedLight>"


def _cx(comp: dict) -> float:
    return float(comp.get("cx", 0))


def _cy(comp: dict, rules: Any) -> float:
    cy = comp.get("cy")
    if cy is None or str(cy).startswith("_"):
        ctype = comp.get("type", "")
        if ctype in {"jack_input", "jack_output"}:
            return rules.cv_jack_cy
        else:
            return rules.att_cy
    return float(cy)


def _mm_to_vcv(x: float, y: float) -> str:
    """Return mm2px(Vec(x, y)) call string."""
    return f"mm2px(Vec({x:.2f}, {y:.2f}))"


def _param_line(vcv_type: str, param_id: str, cx: float, cy: float) -> str:
    return f"\t\taddParam(createParamCentered<{vcv_type}>(mm2px(Vec({cx:.2f}, {cy:.2f})), module, Pogo::{param_id}));"


def _input_line(input_id: str, cx: float, cy: float) -> str:
    return f"\t\taddInput(createInputCentered<{_JACK_TYPE}>(mm2px(Vec({cx:.2f}, {cy:.2f})), module, Pogo::{input_id}));"


def _output_line(output_id: str, cx: float, cy: float) -> str:
    return f"\t\taddOutput(createOutputCentered<{_JACK_TYPE}>(mm2px(Vec({cx:.2f}, {cy:.2f})), module, Pogo::{output_id}));"


def _light_line(light_id: str, cx: float, cy: float) -> str:
    return f"\t\taddChild(createLightCentered<{_LED_TYPE}>(mm2px(Vec({cx:.2f}, {cy:.2f})), module, Pogo::{light_id}));"


def _section_comment(label: str) -> str:
    pad = max(0, 55 - len(label))
    return f"\t\t// ── {label} {'─' * pad}"


def _resolve_band_id(s: str, n: int) -> str:
    return s.replace("{N}", str(n))


# ── Band zone helper ──────────────────────────────────────────────────────────

def _band_lines(zone: dict, rules: Any) -> list[str]:
    """Generate C++ lines for a band zone (band1 / band2 / band3)."""
    n       = int(zone.get("band_n", 1))
    cx_l    = float(zone.get("cx_left",   0))
    cx_c    = float(zone.get("cx_center", 0))
    cx_r    = float(zone.get("cx_right",  0))
    att_cy  = rules.att_cy
    cv_cy   = rules.cv_jack_cy
    cxs     = [cx_l, cx_c, cx_r]

    # Resolve param names
    cpp_params = zone.get("cpp_params", {})
    freq_p  = _resolve_band_id(cpp_params.get("freq",  f"FREQ_{n}_PARAM"), n)
    focus_p = _resolve_band_id(cpp_params.get("focus", f"FB_{n}_PARAM"),   n)
    drive_p = _resolve_band_id(cpp_params.get("drive", f"DRIVE_{n}_PARAM"),n)

    # Att params
    cv_jacks = zone.get("cv_jacks", {})
    att_params  = [_resolve_band_id(p, n) for p in cv_jacks.get("cpp_params", [
        f"FREQ_ATT_{n}_PARAM", f"FB_ATT_{n}_PARAM", f"DRIVE_ATT_{n}_PARAM"
    ])]
    cv_inputs   = [_resolve_band_id(p, n) for p in cv_jacks.get("cpp_inputs", [
        f"FREQ_CV_{n}_INPUT", f"FB_CV_{n}_INPUT", f"DRIVE_CV_{n}_INPUT"
    ])]

    lines = []
    lines.append(_param_line("RoundHugeBlackKnob", freq_p,  cx_c, float(zone.get("freq",  {}).get("cy", 34))))
    lines.append(_param_line("RoundLargeBlackKnob", focus_p, cx_c, float(zone.get("focus", {}).get("cy", 63))))
    lines.append(_param_line("RoundLargeBlackKnob", drive_p, cx_c, float(zone.get("drive", {}).get("cy", 89))))
    for cx, att_p, cv_inp in zip(cxs, att_params, cv_inputs):
        lines.append(_param_line("Trimpot", att_p, cx, att_cy))
    for cx, cv_inp in zip(cxs, cv_inputs):
        lines.append(_input_line(cv_inp, cx, cv_cy))

    return lines


# ── Main generator ────────────────────────────────────────────────────────────

def generate_cpp_stubs(zones: list[dict], rules: Any) -> str:
    """Return a C++ string of all widget add* calls, grouped by zone."""
    out: list[str] = []

    for zone in zones:
        zone_id    = zone.get("id", "")
        zone_label = zone.get("label", zone_id)

        out.append("")
        out.append(_section_comment(zone_label))

        # ── Band zones handled separately ──────────────────────────────────
        if zone_id in ("band1", "band2", "band3"):
            out.extend(_band_lines(zone, rules))
            continue

        # ── Generic component list ─────────────────────────────────────────
        components = zone.get("components", [])
        if not components:
            continue

        for comp in components:
            ctype = comp.get("type", "")
            cx    = _cx(comp)
            cy    = _cy(comp, rules)

            # Params
            if ctype == "trimpot":
                param_id = comp.get("cpp_param", "")
                if param_id:
                    out.append(_param_line("Trimpot", param_id, cx, cy))

            elif ctype == "knob":
                param_id  = comp.get("cpp_param", "")
                vcv_type  = _knob_widget(float(comp.get("cap_mm", 14.0)))
                if param_id:
                    out.append(_param_line(vcv_type, param_id, cx, cy))

            elif ctype == "slider":
                param_id = comp.get("cpp_param", "")
                if param_id:
                    out.append(_param_line("PogoSlider", param_id, cx, cy))

            elif ctype in _SWITCH_TYPE:
                param_id = comp.get("cpp_param", "")
                if param_id:
                    out.append(_param_line(_SWITCH_TYPE[ctype], param_id, cx, cy))

            # Inputs
            elif ctype == "jack_input":
                input_id = comp.get("cpp_id", "")
                if input_id:
                    out.append(_input_line(input_id, cx, cy))

            # Outputs
            elif ctype == "jack_output":
                output_id = comp.get("cpp_id", "")
                if output_id:
                    out.append(_output_line(output_id, cx, cy))

            # Lights
            elif ctype in ("led", "led_labeled"):
                light_id = comp.get("cpp_light", "")
                if light_id:
                    out.append(_light_line(light_id, cx, cy))

            # slider_label: no widget emitted (label only in SVG)
            # else: unknown type — skip silently

    return "\n".join(out)
