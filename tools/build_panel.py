#!/usr/bin/env python3
"""build_panel.py — POGO panel build tool.

Usage (run from repo root):
    python3 tools/build_panel.py              # --resource + --design (default)
    python3 tools/build_panel.py --resource   # writes res/Pogo-source.svg
    python3 tools/build_panel.py --design     # writes design/panel-debug.html
    python3 tools/build_panel.py --mfr        # writes res/Pogo.svg via inkscape
    python3 tools/build_panel.py --cpp        # prints C++ stubs to stdout
    python3 tools/build_panel.py --check      # DRC only; exit 1 on violations
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml  # PyYAML

# ── Repo-relative paths ───────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).resolve().parent.parent
SVG_SOURCE  = REPO_ROOT / "res" / "Pogo-source.svg"
SVG_MFR     = REPO_ROOT / "res" / "Pogo.svg"
HTML_DEBUG  = REPO_ROOT / "design" / "panel-debug.html"
DATA_FILE   = REPO_ROOT / "tools" / "panel-data.yaml"

# Add tools/ to path so sibling modules are importable
sys.path.insert(0, str(REPO_ROOT / "tools"))

from panel_rules import DesignRules   # noqa: E402
import panel_svg as svg               # noqa: E402
from panel_cpp import generate_cpp_stubs  # noqa: E402


# ── YAML loader ───────────────────────────────────────────────────────────────

def load_data(path: Path = DATA_FILE) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Component resolution ──────────────────────────────────────────────────────

def resolve_components(data: dict, rules: DesignRules) -> list[dict]:
    """Return a flat list of all components with placeholder cy values resolved."""
    flat: list[dict] = []
    for zone in data.get("zones", []):
        zone_id = zone.get("id", "")
        if zone_id in ("band1", "band2", "band3"):
            flat.extend(_resolve_band_components(zone, rules))
        else:
            for comp in zone.get("components", []):
                flat.append(_resolve_comp(comp, rules, zone=zone))
    return flat


def _resolve_comp(comp: dict, rules: DesignRules, zone: dict | None = None) -> dict:
    c = dict(comp)
    # Column-relative x resolution
    if 'col' in c and zone and 'x_start' in zone:
        x_start   = float(zone['x_start'])
        col_pitch = float(zone.get('col_pitch', rules.jack_pitch))
        c['cx'] = x_start + (float(c['col']) + 0.5) * col_pitch
    cy = c.get("cy")
    if cy == "_cv_jack_cy_" or cy is None and c.get("type", "") in {"jack_input", "jack_output"}:
        c["cy"] = rules.cv_jack_cy
    elif cy == "_att_cy_" or cy is None:
        c["cy"] = rules.att_cy
    elif isinstance(cy, str) and cy.startswith("_"):
        # Unknown template — fall back by type
        c["cy"] = rules.cv_jack_cy if c.get("type", "") in {"jack_input", "jack_output"} else rules.att_cy
    else:
        c["cy"] = float(cy)
    return c


def _resolve_band_components(zone: dict, rules: DesignRules) -> list[dict]:
    n       = int(zone.get("band_n", 1))
    cx_l    = float(zone.get("cx_left",   0))
    cx_c    = float(zone.get("cx_center", 0))
    cx_r    = float(zone.get("cx_right",  0))
    att_cy  = rules.att_cy
    cv_cy   = rules.cv_jack_cy

    comps = []
    for ctrl, ctype, cy_key in [
        ("freq",  "knob_xl",    "cy"),
        ("focus", "knob_large", "cy"),
        ("drive", "knob_large", "cy"),
    ]:
        ctrl_data = zone.get(ctrl, {})
        cy_val    = float(ctrl_data.get("cy", 34 if ctrl == "freq" else (63 if ctrl == "focus" else 89)))
        comps.append({"type": ctype, "cx": cx_c, "cy": cy_val, "id": f"{ctrl}_{n}"})

    cv_jacks = zone.get("cv_jacks", {})
    cv_labels = zone.get("cv_labels", ["FREQ", "FOCUS", "DRIVE"])
    att_params = [p.replace("{N}", str(n)) for p in cv_jacks.get("cpp_params", [
        f"FREQ_ATT_{n}_PARAM", f"FB_ATT_{n}_PARAM", f"DRIVE_ATT_{n}_PARAM"
    ])]
    cv_inputs  = [p.replace("{N}", str(n)) for p in cv_jacks.get("cpp_inputs", [
        f"FREQ_CV_{n}_INPUT", f"FB_CV_{n}_INPUT", f"DRIVE_CV_{n}_INPUT"
    ])]

    for cx, att_p in zip([cx_l, cx_c, cx_r], att_params):
        comps.append({"type": "trimpot", "cx": cx, "cy": att_cy, "id": att_p})
    for cx, cv_inp, lbl in zip([cx_l, cx_c, cx_r], cv_inputs, cv_labels):
        comps.append({"type": "jack_input", "cx": cx, "cy": cv_cy, "label": lbl, "id": cv_inp})

    return comps


# ── DRC ───────────────────────────────────────────────────────────────────────

def run_drc(data: dict, rules: DesignRules) -> list[str]:
    components    = resolve_components(data, rules)
    mh            = data.get("mounting_holes", [])
    return rules.check_all(components, mounting_holes=mh)


# ── Component list / next-x helpers ──────────────────────────────────────────

def print_component_list(data: dict, rules: DesignRules) -> None:
    """Print a table of all resolved components grouped by zone."""
    header = f"{'ZONE':<20} {'ID':<30} {'TYPE':<16} {'cx':>7} {'cy':>7}"
    print(header)
    print("-" * len(header))
    for zone in data.get("zones", []):
        zone_id = zone.get("id", "")
        if zone_id in ("band1", "band2", "band3"):
            comps = _resolve_band_components(zone, rules)
            for comp in comps:
                cid   = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"
                ctype = comp.get("type", "")
                cx    = float(comp.get("cx", 0))
                cy    = float(comp.get("cy", 0))
                print(f"{zone_id:<20} {cid:<30} {ctype:<16} {cx:>7.2f} {cy:>7.2f}")
        else:
            for comp in zone.get("components", []):
                resolved = _resolve_comp(comp, rules, zone=zone)
                cid   = resolved.get("id") or resolved.get("cpp_id") or resolved.get("cpp_param") or "?"
                ctype = resolved.get("type", "")
                cx    = float(resolved.get("cx", 0))
                cy    = float(resolved.get("cy", 0))
                print(f"{zone_id:<20} {cid:<30} {ctype:<16} {cx:>7.2f} {cy:>7.2f}")


def get_next_x(data: dict, rules: DesignRules, zone_id: str) -> float | None:
    """Return the next x_start after a column-relative zone, or None if not found."""
    for zone in data.get("zones", []):
        if zone.get("id") == zone_id:
            if "x_start" not in zone or "cols" not in zone:
                return None
            x_start   = float(zone["x_start"])
            col_pitch = float(zone.get("col_pitch", rules.jack_pitch))
            cols      = int(zone["cols"])
            return x_start + cols * col_pitch
    return None


# ── SVG generation ────────────────────────────────────────────────────────────

_FONT = 'font-family="monospace"'


def _build_svg_lines(data: dict, rules: DesignRules) -> list[str]:
    colors  = data["colors"]
    meta    = data["meta"]
    W       = float(meta["width_mm"])
    H       = float(meta["height_mm"])
    lines   = []

    # ── SVG root ──────────────────────────────────────────────────────────
    lines.append('<!-- GENERATED by tools/build_panel.py — edit tools/panel-data.yaml -->')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}mm" height="{H}mm" viewBox="{meta["viewBox"]}">'
    )
    lines.append("")
    lines.append("  <!-- ── PANEL BACKGROUND ─────────────────────────────────────────────────── -->")
    lines.append("  " + svg.svg_panel_background(W, H, colors).replace("\n", "\n  "))

    # ── Comment block (spacing reference) ────────────────────────────────
    hp   = float(meta.get("width_mm", W)) / float(meta.get("hp", round(W / 5.08)))
    lines.append(f"""
  <!--
    PANEL: {W:.2f} mm wide × {H:.2f} mm tall
    1 HP = 5.08 mm   jack pitch = 10.16 mm (2 HP)
    Jack x centres in an N-HP zone starting at x0:
      2 HP (1 j): x0+5.08
      4 HP (2 j): x0+5.08, x0+15.24
      6 HP (3 j): x0+5.08, x0+15.24, x0+25.40
      8 HP (4 j): x0+5.08, x0+15.24, x0+25.40, x0+35.56
  -->""")

    # ── Mounting holes ─────────────────────────────────────────────────────
    lines.append("")
    lines.append("  <!-- Mounting holes: M3 -->")
    for mh in data.get("mounting_holes", []):
        lines.append("  " + svg.svg_mounting_hole(mh["cx"], mh["cy"]))

    # ── Title strip ────────────────────────────────────────────────────────
    title      = meta["title"]
    dot_color  = meta["title_dot_color"]
    # Split title at the · dot so we can colour it
    if "·" in title:
        before_dot, after_dot = title.split("·", 1)
        title_svg = (
            f'<text x="101.60" y="3.5" fill="{colors["cyan"]}" {_FONT} font-size="3.5" '
            f'font-weight="bold" text-anchor="middle">'
            f'{before_dot}<tspan fill="{dot_color}">·</tspan>{after_dot}</text>'
        )
    else:
        title_svg = (
            f'<text x="101.60" y="3.5" fill="{colors["cyan"]}" {_FONT} font-size="3.5" '
            f'font-weight="bold" text-anchor="middle">{title}</text>'
        )
    lines.append("")
    lines.append("  <!-- ── TOP STRIP ──────────────────────────────────────────────────────────── -->")
    lines.append(f"  {title_svg}")

    brand = meta["brand"]
    lines.append("")
    lines.append("  <!-- ── BOTTOM STRIP ───────────────────────────────────────────────────────── -->")
    lines.append(
        f'  <text x="101.60" y="127.5" fill="{colors["brand_text"]}" {_FONT} font-size="2.4" '
        f'text-anchor="middle" letter-spacing="0.15">{brand}</text>'
    )

    # ── Separators ─────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  <!-- ── MAIN ZONE SEPARATOR LINES (cyan) ──────────────────────────────────── -->")
    main_cyan_done = False
    for sep in data.get("separators", []):
        s = sep["style"]
        if s == "main_cyan" and sep["type"] == "v":
            lines.append(
                "  " + svg.svg_separator_v(sep["x"], sep["y1"], sep["y2"], s, colors)
            )
        elif s == "subdiv_gray" and not main_cyan_done:
            main_cyan_done = True
            lines.append("")
            lines.append("  <!-- ── BAND GROUP SUB-DIVIDERS (dim gray vertical) ───────────────────────── -->")
    for sep in data.get("separators", []):
        if sep["style"] == "subdiv_gray" and sep["type"] == "v":
            lines.append(
                "  " + svg.svg_separator_v(sep["x"], sep["y1"], sep["y2"], sep["style"], colors)
            )

    lines.append("")
    lines.append("  <!-- ── ZONE 0 MINI-ZONE DIVIDERS (dim gray horizontal) ───────────────────── -->")
    for sep in data.get("separators", []):
        if sep["type"] == "h" and sep["style"] == "zone_div" and sep.get("x2", 999) < 21:
            lines.append(
                "  " + svg.svg_separator_h(sep["x1"], sep["x2"], sep["y"], sep["style"], colors)
            )

    lines.append("")
    lines.append("  <!-- ── ZONE 1: BAND / DIST SUBSECTION DIVIDER (horizontal) ──────────────── -->")
    for sep in data.get("separators", []):
        if sep["type"] == "h" and sep["style"] == "zone_div" and sep.get("x1", 0) > 20:
            lines.append(
                "  " + svg.svg_separator_h(sep["x1"], sep["x2"], sep["y"], sep["style"], colors)
            )

    lines.append("")
    lines.append("  <!-- ── LP2+HP+OUT ZONE: TOP STRIP / FILTER SECTION DIVIDER ──────────────── -->")
    for sep in data.get("separators", []):
        if sep["type"] == "h" and sep["style"] == "main_cyan":
            lines.append(
                "  " + svg.svg_separator_h(sep["x1"], sep["x2"], sep["y"], sep["style"], colors)
            )

    # ── Zone labels ────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  <!-- ════════════════════════════════════════════════════════════════════════ -->")
    lines.append("  <!-- ZONE LABELS                                                              -->")
    lines.append("  <!-- ════════════════════════════════════════════════════════════════════════ -->")
    for zl in data.get("zone_labels", []):
        lines.append("")
        sub = zl.get("subtitle")
        comment_text = zl["text"].replace('"', "'")
        lines.append(f'  <!-- {comment_text} -->')
        chunk = svg.svg_zone_title(zl["x"], zl["y"], zl["text"], colors, subtitle=sub)
        lines.append("  " + chunk.replace("\n", "\n  "))

    # ── Zone content ───────────────────────────────────────────────────────
    for zone in data.get("zones", []):
        zone_id    = zone.get("id", "")
        zone_label = zone.get("label", zone_id)

        lines.append("")
        sep_line = "═" * 72
        lines.append(f"  <!-- {sep_line} -->")
        lines.append(f"  <!-- {zone_label:<72} -->")
        lines.append(f"  <!-- {sep_line} -->")
        lines.append("")

        if zone_id in ("band1", "band2", "band3"):
            lines.extend(_band_svg_lines(zone, rules, colors))
        else:
            for comp in zone.get("components", []):
                resolved = _resolve_comp(comp, rules, zone=zone)
                chunk = _component_svg(resolved, rules, colors)
                if chunk:
                    lines.append("  " + chunk.replace("\n", "\n  "))

    lines.append("")
    lines.append("</svg>")
    return lines


def _component_svg(comp: dict, rules: DesignRules, colors: dict) -> str:
    """Return SVG string for a single component, resolving placeholder cy."""
    ctype = comp.get("type", "")
    cx    = float(comp.get("cx", 0))
    raw_cy = comp.get("cy")
    if raw_cy is None or (isinstance(raw_cy, str) and raw_cy.startswith("_")):
        if ctype in {"jack_input", "jack_output"}:
            cy = rules.cv_jack_cy
        else:
            cy = rules.att_cy
    else:
        cy = float(raw_cy)

    label      = comp.get("label", "")
    font_size  = float(comp.get("font_size", 1.8))
    label_lines = comp.get("label_lines")
    label_fill  = comp.get("label_fill")

    if ctype == "jack_input":
        rect_w = comp.get("rect_w")
        return svg.svg_jack(cx, cy, label, "input", rules, colors, font_size=font_size,
                            rect_w=rect_w)

    elif ctype == "jack_output":
        rect_w = comp.get("rect_w")
        # For outputs with an explicit rect, use provided rect data if available
        explicit_rect = comp.get("rect")
        if explicit_rect:
            # Use the explicitly stored rect coordinates (e.g. LFO outputs)
            parts = [
                f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="none" '
                f'stroke="{colors["jack_outer"]}" stroke-width="0.6"/>',
                f'<circle cx="{cx}" cy="{cy}" r="1.4" '
                f'fill="{colors["jack_inner"]}" stroke="{colors["jack_inner_s"]}" stroke-width="0.4"/>',
                f'<rect x="{explicit_rect["x"]}" y="{explicit_rect["y"]}" '
                f'width="{explicit_rect["w"]}" height="{explicit_rect["h"]}" '
                f'rx="{rules.output_rect_rx}" fill="none" '
                f'stroke="{colors["output_rect_s"]}" stroke-width="0.3"/>',
                f'<text x="{cx}" y="{cy + rules.jack_label_dy:.1f}" fill="{colors["jack_text"]}" '
                f'font-family="monospace" font-size="{font_size}" text-anchor="middle">{label}</text>',
            ]
            return "\n".join(parts)
        return svg.svg_jack(cx, cy, label, "output", rules, colors, font_size=font_size,
                            rect_w=rect_w)

    elif ctype == "trimpot":
        tp_label       = comp.get("label", "")
        lfs            = float(comp.get("label_font_size", 1.8))
        return svg.svg_trimpot(cx, cy, tp_label, rules, colors, label_font_size=lfs)

    elif ctype in ("knob_medium", "knob_large", "knob_xl"):
        r_map = {"knob_medium": 4.5, "knob_large": 7.0, "knob_xl": 9.0}
        r     = r_map[ctype]
        lbl   = label if not label_lines else ""
        return svg.svg_knob(cx, cy, r, lbl, rules, colors,
                            label_lines=label_lines, label_fill=label_fill)

    elif ctype == "slider":
        # Slider widget drawn by VCV Rack; nothing to emit in SVG (label handled by slider_label)
        return ""

    elif ctype == "slider_label":
        return svg.svg_slider_label(float(comp.get("cx", cx)), float(comp.get("y", 38)), colors)

    elif ctype == "switch_H2":
        return svg.svg_switch_H2(
            cx=cx, cy=cy,
            label_above=comp.get("label_above", ""),
            label_above_y=float(comp.get("label_above_y", cy - 3.5)),
            pos_labels=comp.get("pos_labels", []),
            pos_xs=comp.get("pos_xs", []),
            pos_y=float(comp.get("pos_y", cy + 4)),
            colors=colors,
        )

    elif ctype == "switch_H3":
        return svg.svg_switch_H3(
            cx=cx, cy=cy,
            pos_labels=comp.get("pos_labels", []),
            pos_xs=comp.get("pos_xs", []),
            pos_y=float(comp.get("pos_y", cy + 5.3)),
            label_below=comp.get("label_below", ""),
            label_below_y=float(comp.get("label_below_y", cy + 8.8)),
            colors=colors,
        )

    elif ctype == "switch_V3":
        return svg.svg_switch_V3(
            cx=cx,
            cy_body_top=float(comp.get("cy_body_top", cy)),
            body_height=float(comp.get("body_height", 12)),
            slug_y_offset=float(comp.get("slug_y_offset", 4.25)),
            pos_labels=comp.get("pos_labels", []),
            pos_ys=comp.get("pos_ys", []),
            label_below=comp.get("label_below", ""),
            label_below_y=float(comp.get("label_below_y", cy + 15)),
            colors=colors,
        )

    elif ctype == "led":
        return svg.svg_led(cx, cy, colors)

    elif ctype == "led_labeled":
        lbl_fill = comp.get("label_fill", colors["jack_text"])
        lbl      = comp.get("label", "")
        return svg.svg_led_labeled(cx, cy, lbl, lbl_fill, rules, colors)

    return ""


def _band_svg_lines(zone: dict, rules: DesignRules, colors: dict) -> list[str]:
    """Return SVG lines for a band zone."""
    n       = int(zone.get("band_n", 1))
    cx_l    = float(zone.get("cx_left",   0))
    cx_c    = float(zone.get("cx_center", 0))
    cx_r    = float(zone.get("cx_right",  0))
    att_cy  = rules.att_cy
    cv_cy   = rules.cv_jack_cy
    cxs     = [cx_l, cx_c, cx_r]
    cv_labels = zone.get("cv_labels", ["FREQ", "FOCUS", "DRIVE"])

    lines = []

    # Main knobs
    for ctrl_key, r, cy_default in [("freq", 9.0, 34), ("focus", 7.0, 63), ("drive", 7.0, 89)]:
        ctrl_data = zone.get(ctrl_key, {})
        cy_val = float(ctrl_data.get("cy", cy_default))
        lbl    = ctrl_data.get("label", ctrl_key.upper())
        chunk  = svg.svg_knob(cx_c, cy_val, r, lbl, rules, colors)
        lines.append("  " + chunk.replace("\n", "\n  "))

    # ATT row
    for cx in cxs:
        chunk = svg.svg_trimpot(cx, att_cy, "", rules, colors)
        lines.append("  " + chunk.replace("\n", "\n  "))

    # CV jacks
    for cx, lbl in zip(cxs, cv_labels):
        chunk = svg.svg_jack(cx, cv_cy, lbl, "input", rules, colors)
        lines.append("  " + chunk.replace("\n", "\n  "))

    return lines


def build_svg(data: dict, rules: DesignRules) -> str:
    return "\n".join(_build_svg_lines(data, rules))


# ── HTML debug viewer ─────────────────────────────────────────────────────────

def _scale_svg_for_html(svg_content: str, scale: float = 4.0) -> str:
    """Replace mm dimensions in the SVG root element with px for screen display."""
    import re
    m_w = re.search(r'<svg[^>]*\swidth="([\d.]+)mm"', svg_content)
    m_h = re.search(r'<svg[^>]*\sheight="([\d.]+)mm"', svg_content)
    W_px = round(float(m_w.group(1)) * scale) if m_w else round(203.20 * scale)
    H_px = round(float(m_h.group(1)) * scale) if m_h else round(128.5  * scale)
    svg_content = re.sub(
        r'<svg([^>]*?)width="[^"]*"([^>]*?)height="[^"]*"',
        f'<svg\\1width="{W_px}px"\\2height="{H_px}px"',
        svg_content, count=1,
    )
    return svg_content


def _collect_overlay_positions(data: dict, rules: DesignRules) -> dict:
    """Return component positions grouped by type for overlay rendering."""
    jacks:   list[tuple[float, float]] = []
    pots:    list[tuple[float, float]] = []
    knobs:   list[tuple[float, float, float]] = []  # cx, cy, r_mm
    switches: list[tuple[float, float]] = []
    leds:    list[tuple[float, float]] = []

    r_map = {"knob_medium": 4.5, "knob_large": 7.0, "knob_xl": 9.0}

    from panel_rules import SWITCH_TYPES, LED_TYPES  # noqa: E402

    for comp in resolve_components(data, rules):
        cx    = float(comp.get("cx", 0))
        cy    = float(comp.get("cy", 0))
        ctype = comp.get("type", "")

        if ctype in ("jack_input", "jack_output"):
            jacks.append((cx, cy))
        elif ctype == "trimpot":
            pots.append((cx, cy))
        elif ctype in r_map:
            knobs.append((cx, cy, r_map[ctype]))
        elif ctype in SWITCH_TYPES:
            switches.append((cx, cy))
        elif ctype in LED_TYPES:
            leds.append((cx, cy))

    return {"jacks": jacks, "pots": pots, "knobs": knobs, "switches": switches, "leds": leds}


def _wrap_svg_in_layers(
    svg_content: str,
    rules: DesignRules,
    overlay: dict | None = None,
    scale: float = 4.0,
) -> str:
    """Inject named <g> layer groups and DRC/footprint overlays into the SVG."""
    import re

    m = re.search(r"<svg[^>]*>(.*)</svg>", svg_content, re.DOTALL)
    if not m:
        return svg_content
    inner    = m.group(1)
    svg_open = svg_content[: m.start(1)].rstrip()

    if overlay is None:
        overlay = {"jacks": [], "pots": [], "knobs": [], "switches": [], "leds": []}

    # Extract panel dimensions from SVG attributes (works for any HP width).
    import re as _re
    m_w = _re.search(r'width="([\d.]+)px"', svg_content)
    m_h = _re.search(r'height="([\d.]+)px"', svg_content)
    scale_used = scale  # SVG has already been scaled by _scale_svg_for_html
    W = float(m_w.group(1)) / scale_used if m_w else 203.20
    H = float(m_h.group(1)) / scale_used if m_h else 128.5
    kot = rules.top_keepout        # 10.0
    kob = rules.bot_keepout_start  # 118.5

    # ── Keep-out layer ────────────────────────────────────────────────────────
    dash = "1 0.7"  # ~4px dash at 4px/mm
    keepout_layer = f"""
  <g id="layer-keepout" style="display:none;">
    <rect x="0" y="0" width="{W}" height="{kot}" fill="rgba(255,0,0,0.18)"/>
    <rect x="0" y="{kob}" width="{W}" height="{H - kob}" fill="rgba(255,0,0,0.18)"/>
    <line x1="0" y1="{kot}" x2="{W}" y2="{kot}" stroke="#ff4444" stroke-width="0.35" stroke-dasharray="{dash}"/>
    <line x1="0" y1="{kob}" x2="{W}" y2="{kob}" stroke="#ff4444" stroke-width="0.35" stroke-dasharray="{dash}"/>
    <text x="1" y="{kot - 0.4}" fill="#ff4444" font-family="monospace" font-size="1.8">TOP KEEP-OUT</text>
    <text x="1" y="{kob - 0.5}" fill="#ff4444" font-family="monospace" font-size="1.8">BOT KEEP-OUT</text>
  </g>"""

    # ── Nuts / knob-caps layer ─────────────────────────────────────────────────
    nuts_parts: list[str] = []
    for cx, cy in overlay["jacks"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="5" fill="rgba(255,204,0,0.35)" stroke="#ffcc00" stroke-width="0.25"/>'
        )
    for cx, cy in overlay["pots"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="5.5" fill="rgba(100,180,255,0.35)" stroke="#64b4ff" stroke-width="0.25"/>'
        )
    for cx, cy, r in overlay["knobs"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="{r}" fill="rgba(255,140,0,0.25)" stroke="#ff8c00" stroke-width="0.25"/>'
        )
    for cx, cy in overlay.get("switches", []):
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="3.15" fill="rgba(220,100,255,0.35)" stroke="#dc64ff" stroke-width="0.25"/>'
        )
    for cx, cy in overlay.get("leds", []):
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="1.6" fill="rgba(100,220,100,0.35)" stroke="#64dc64" stroke-width="0.25"/>'
        )
    nuts_layer = (
        '\n  <g id="layer-nuts" style="display:none;">\n'
        + "\n".join(nuts_parts)
        + "\n  </g>"
    )

    # ── PCB footprints layer (KiCad courtyard projected onto panel plane) ──────
    # Thonkiconn PJ301M-12: courtyard x∈[-5,5] y∈[-1.42,12.98] (origin = panel hole)
    # Alpha RD901F 9mm:     courtyard relative to shaft center x∈[-8.65,5.1] y∈[-6.67,6.67]
    # Switch: courtyard SWITCH_CY = (-4.5,-3.5,4.5,7.5) relative to switch centre
    # LED:    courtyard LED_CY    = (-2.0,-1.5,2.0,4.0) relative to LED centre
    pcb_parts: list[str] = []
    for cx, cy in overlay["jacks"]:
        pcb_parts.append(
            f'    <rect x="{cx - 5}" y="{cy - 1.42}" width="10" height="14.4"'
            f' fill="rgba(255,204,0,0.15)" stroke="#ffcc00" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )
    for cx, cy in overlay["pots"]:
        pcb_parts.append(
            f'    <rect x="{cx - 8.65}" y="{cy - 6.67}" width="13.75" height="13.34"'
            f' fill="rgba(100,180,255,0.15)" stroke="#64b4ff" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )
    for cx, cy, r in overlay["knobs"]:
        pcb_parts.append(
            f'    <rect x="{cx - 8.65}" y="{cy - 6.67}" width="13.75" height="13.34"'
            f' fill="rgba(255,140,0,0.12)" stroke="#ff8c00" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )
    for cx, cy in overlay.get("switches", []):
        pcb_parts.append(
            f'    <rect x="{cx - 4.5}" y="{cy - 3.5}" width="9" height="11"'
            f' fill="rgba(220,100,255,0.15)" stroke="#dc64ff" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )
    for cx, cy in overlay.get("leds", []):
        pcb_parts.append(
            f'    <rect x="{cx - 2.0}" y="{cy - 1.5}" width="4" height="5.5"'
            f' fill="rgba(100,220,100,0.15)" stroke="#64dc64" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )
    pcb_layer = (
        '\n  <g id="layer-pcb" style="display:none;">\n'
        + "\n".join(pcb_parts)
        + "\n  </g>"
    )

    assembled = svg_open + "\n"
    assembled += f'  <g id="layer-panel">\n{inner}\n  </g>\n'
    assembled += keepout_layer + "\n"
    assembled += nuts_layer    + "\n"
    assembled += pcb_layer     + "\n"
    assembled += "</svg>"
    return assembled


def build_html(svg_content: str, rules: DesignRules, violations: list[str], data: dict | None = None) -> str:
    """Build the debug HTML with layer-toggle checkboxes."""
    overlay     = _collect_overlay_positions(data, rules) if data else None
    svg_scaled  = _scale_svg_for_html(svg_content, scale=4.0)
    svg_layered = _wrap_svg_in_layers(svg_scaled, rules, overlay=overlay, scale=4.0)

    # Build DRC violation report, grouped by category tag
    if violations:
        from collections import defaultdict
        groups: dict[str, list[str]] = defaultdict(list)
        for v in violations:
            tag = v.split("]")[0].lstrip("[") if v.startswith("[") else "OTHER"
            groups[tag].append(v)

        _CAT_COLOR = {
            "NUT KEEPOUT":    "#ff6666",
            "PCB OVERLAP":    "#ffaa44",
            "MH CLEARANCE":   "#ffdd55",
            "PCB KEEPOUT":    "#88aaff",
            "OTHER":          "#cc99ff",
        }
        parts = []
        for tag, items in sorted(groups.items()):
            color = _CAT_COLOR.get(tag, "#cc99ff")
            parts.append(
                f'<details open><summary style="color:{color};cursor:pointer;">'
                f'{tag} ({len(items)})</summary><ul>'
            )
            for item in items:
                parts.append(f"<li style='color:{color}'>{item}</li>")
            parts.append("</ul></details>")

        vio_html  = "\n".join(parts)
        vio_label = f"DRC — {len(violations)} violation(s)"
    else:
        vio_html  = "<p style='color:#44ff44'>No DRC violations.</p>"
        vio_label = "DRC: PASS"

    layers = [
        ("layer-panel",   "Panel (front)",               True),
        ("layer-keepout", "Rail Keep-Out",                False),
        ("layer-nuts",    "Nuts / Knob Caps",             False),
        ("layer-pcb",     "PCB Footprints (backside)",    False),
    ]

    checkboxes_html = ""
    for lid, lname, checked in layers:
        ck = "checked" if checked else ""
        checkboxes_html += (
            f'<label style="margin-right:16px;cursor:pointer;">'
            f'<input type="checkbox" {ck} onchange="toggleLayer(\'{lid}\', this.checked)"> '
            f'{lname}</label>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>POGO Panel Debug</title>
  <style>
    body  {{ background:#111; color:#ccc; font-family:monospace; padding:16px; }}
    h1    {{ color:#00d4ff; margin-bottom:8px; }}
    .controls {{ margin-bottom:12px; display:flex; flex-wrap:wrap; gap:4px; align-items:center; }}
    .drc  {{ background:#1a0000; border:1px solid #553333; padding:8px 14px;
             margin-top:12px; border-radius:4px; max-width:812px; }}
    .drc h2 {{ color:#ff8888; margin:0 0 6px; font-size:1em; }}
    #svg-wrap {{ border:1px solid #333; display:inline-block; margin-top:8px; }}
  </style>
</head>
<body>
  <h1>POGO Panel Debug</h1>
  <div class="controls">
    {checkboxes_html}
  </div>
  <div id="svg-wrap">
    {svg_layered}
  </div>
  <div class="drc">
    <h2>{vio_label}</h2>
    {vio_html}
  </div>
  <script>
    function toggleLayer(id, visible) {{
      var el = document.getElementById(id);
      if (el) el.style.display = visible ? '' : 'none';
    }}
  </script>
</body>
</html>"""
    return html


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="POGO panel build tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--resource", action="store_true", help="Write res/Pogo-source.svg")
    parser.add_argument("--design",   action="store_true", help="Write design/panel-debug.html")
    parser.add_argument("--mfr",      action="store_true", help="Write res/Pogo.svg via inkscape")
    parser.add_argument("--cpp",      action="store_true", help="Print C++ stubs to stdout")
    parser.add_argument("--check",    action="store_true", help="DRC only; exit 1 on blocking violations")
    parser.add_argument("--list",     action="store_true", help="Print table of all resolved components")
    parser.add_argument("--next",     metavar="ZONE_ID",   help="Print next x_start after a column-relative zone")
    args = parser.parse_args()

    # Default: both --resource and --design
    if not any([args.resource, args.design, args.mfr, args.cpp, args.check,
                args.list, args.next]):
        args.resource = True
        args.design   = True

    data  = load_data()
    rules = DesignRules.from_data(data)

    violations = run_drc(data, rules)

    if args.check:
        blocking = [v for v in violations if not v.startswith("[PCB KEEPOUT]")]
        informational = [v for v in violations if v.startswith("[PCB KEEPOUT]")]
        if blocking:
            from collections import defaultdict
            groups: dict[str, list[str]] = defaultdict(list)
            for v in blocking:
                tag = v.split("]")[0].lstrip("[") if v.startswith("[") else "OTHER"
                groups[tag].append(v)
            print(f"DRC FAILED — {len(blocking)} violation(s):", file=sys.stderr)
            for tag, items in sorted(groups.items()):
                print(f"\n  [{tag}] ({len(items)})", file=sys.stderr)
                for v in items:
                    print(f"    {v}", file=sys.stderr)
            if informational:
                print(f"\n  [PCB KEEPOUT] ({len(informational)}) — informational only:",
                      file=sys.stderr)
                for v in informational:
                    print(f"    {v}", file=sys.stderr)
            return 1
        if informational:
            print(f"DRC PASS (with {len(informational)} [PCB KEEPOUT] informational warning(s)):")
            for v in informational:
                print(f"  {v}")
        else:
            print("DRC PASS — no violations.")
        return 0

    if args.list:
        print_component_list(data, rules)
        return 0

    if args.next:
        nx = get_next_x(data, rules, args.next)
        if nx is None:
            print(f"Zone '{args.next}' not found or not column-relative.", file=sys.stderr)
            return 1
        hp = nx / 5.08
        print(f"{args.next}  next x_start = {nx:.2f} mm  (HP {hp:.2f})")
        return 0

    svg_content = build_svg(data, rules)

    if args.resource:
        SVG_SOURCE.parent.mkdir(parents=True, exist_ok=True)
        SVG_SOURCE.write_text(svg_content, encoding="utf-8")
        print(f"Wrote {SVG_SOURCE.relative_to(REPO_ROOT)}")

    if args.design:
        html_content = build_html(svg_content, rules, violations, data=data)
        HTML_DEBUG.parent.mkdir(parents=True, exist_ok=True)
        HTML_DEBUG.write_text(html_content, encoding="utf-8")
        vio_msg = f"  ({len(violations)} DRC violation(s))" if violations else "  (DRC PASS)"
        print(f"Wrote {HTML_DEBUG.relative_to(REPO_ROOT)}{vio_msg}")

    if args.mfr:
        if not args.resource:
            SVG_SOURCE.parent.mkdir(parents=True, exist_ok=True)
            SVG_SOURCE.write_text(svg_content, encoding="utf-8")
        inkscape_cmd = [
            "inkscape",
            "--export-plain-svg",
            f"--export-filename={SVG_MFR}",
            str(SVG_SOURCE),
        ]
        try:
            subprocess.run(inkscape_cmd, check=True)
            print(f"Wrote {SVG_MFR.relative_to(REPO_ROOT)}")
        except FileNotFoundError:
            print("inkscape not found; copying source SVG as mfr SVG instead.", file=sys.stderr)
            import shutil
            shutil.copy(SVG_SOURCE, SVG_MFR)
            print(f"Wrote {SVG_MFR.relative_to(REPO_ROOT)} (inkscape unavailable)")
        except subprocess.CalledProcessError as e:
            print(f"inkscape failed: {e}", file=sys.stderr)
            return 1

    if args.cpp:
        zones = data.get("zones", [])
        cpp   = generate_cpp_stubs(zones, rules)
        print(cpp)

    if violations and not args.check:
        print(f"\nWARNING: {len(violations)} DRC violation(s):", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
