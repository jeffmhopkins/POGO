"""panel_svg.py — SVG primitive generators for the POGO panel.

All functions return raw SVG strings (no ElementTree).  The caller is
responsible for assembling them inside an <svg> root element.

Coordinate system: mm, matching the panel viewBox (0 0 203.20 128.5).
"""

from __future__ import annotations
from typing import Any


# ── Shared font style ─────────────────────────────────────────────────────────

_FONT = 'font-family="monospace"'


# ── Jacks ─────────────────────────────────────────────────────────────────────

def svg_jack(
    cx: float,
    cy: float,
    label: str,
    io: str,          # 'input' or 'output'
    rules: Any,       # DesignRules instance
    colors: dict,
    font_size: float = 1.8,
    rect_w: float | None = None,
    label_border: bool = False,
) -> str:
    """Thonkiconn jack symbol: outer ring + centre dot + optional label border + label.

    The rounded-rect label border is drawn when ``label_border`` is set (an explicit
    per-component field), independent of input/output direction.
    """
    label_y = cy + rules.jack_label_dy
    parts = []

    # outer ring
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="none" '
        f'stroke="{colors["jack_outer"]}" stroke-width="0.6"/>'
    )
    # centre dot
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="1.4" '
        f'fill="{colors["jack_inner"]}" stroke="{colors["jack_inner_s"]}" stroke-width="0.4"/>'
    )

    # label border rect (opt-in via label_border)
    if label_border:
        rw = rect_w if rect_w is not None else 7.0
        rx_val = rules.output_rect_rx
        ry = rules.rect_y(label_y)
        rx_left = cx - rw / 2
        parts.append(
            f'<rect x="{rx_left:.2f}" y="{ry:.2f}" width="{rw}" '
            f'height="{rules.output_rect_h}" rx="{rx_val}" '
            f'fill="none" stroke="{colors["output_rect_s"]}" stroke-width="0.3"/>'
        )

    # label
    parts.append(
        f'<text x="{cx}" y="{label_y:.1f}" fill="{colors["jack_text"]}" '
        f'{_FONT} font-size="{font_size}" text-anchor="middle">{label}</text>'
    )

    return "\n".join(parts)


# ── Free text annotation ───────────────────────────────────────────────────────

def svg_text(
    cx: float,
    cy: float,
    text: str,
    colors: dict,
    font_size: float = 2.0,
    fill: str | None = None,
    weight: str = "normal",
    anchor: str = "middle",
) -> str:
    """Free-floating text label (panel annotation; no hole/courtyard)."""
    f = fill or colors["control_text"]
    w = ' font-weight="bold"' if weight == "bold" else ""
    return (
        f'<text x="{cx}" y="{cy}" fill="{f}" {_FONT} font-size="{font_size}" '
        f'text-anchor="{anchor}"{w}>{text}</text>'
    )


# ── Trimpots ──────────────────────────────────────────────────────────────────

def svg_trimpot(
    cx: float,
    cy: float,
    label: str,
    rules: Any,
    colors: dict,
    label_font_size: float = 1.8,
    rotate: int = 0,
) -> str:
    """Small trim-pot symbol: circle + indicator line + label below.

    The body circle is rotation-invariant; `rotate` spins the wiper-indicator
    pointer to match the rotated footprint (a pot mounted rotated sits with its
    pointer rotated). The label stays upright.
    """
    r = 2.5
    label_y = cy + r + 3.0  # consistent spacing below the circle
    if rotate:
        ind_dx, ind_dy = _rotate_vec(0.0, -rules.indicator_length, rotate)
        ind_x2, ind_y2 = f"{cx + ind_dx:.3f}", f"{cy + ind_dy:.3f}"
    else:
        ind_x2, ind_y2 = f"{cx}", f"{cy - rules.indicator_length}"
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{colors["knob_fill"]}" stroke="{colors["knob_stroke"]}" stroke-width="0.5"/>',
        f'<line x1="{cx}" y1="{cy}" x2="{ind_x2}" y2="{ind_y2}" '
        f'stroke="{colors["indicator"]}" stroke-width="0.5"/>',
        f'<text x="{cx}" y="{label_y:.1f}" fill="{colors["control_text"]}" '
        f'{_FONT} font-size="{label_font_size}" text-anchor="middle">{label}</text>',
    ]
    return "\n".join(parts)


# ── Generic knob ──────────────────────────────────────────────────────────────

def svg_knob(
    cx: float,
    cy: float,
    r: float,
    label: str,
    rules: Any,
    colors: dict,
    label_lines: list[str] | None = None,
    label_fill: str | None = None,
) -> str:
    """Knob circle + indicator line + one or more label lines below.

    If label_lines is given it overrides label (for multi-line labels).
    First label line is at cy + r + 3.0; subsequent lines at +2.3 spacing.

    Note: knobs intentionally do NOT honour `rotate`. The pointer is a value
    indicator on a removable cap, set independently of how the pot body is mounted;
    a rotated pot (e.g. rotate:180 for PCB-courtyard fit) still takes a cap pointing
    up. Only the PCB courtyard rotates (shown in the KiCad layer). Toggles, sliders
    and trimpots — whose actuator is fixed to the body — do honour rotation.
    """
    if label_lines is None:
        label_lines = [label]

    stroke_w = 0.5 + (r - 2.5) * 0.05  # scales mildly with radius
    if r >= 9:
        stroke_w = 0.7
    elif r >= 7:
        stroke_w = 0.6
    ind_stroke = 0.5 + (r - 2.5) * 0.06
    if r >= 9:
        ind_stroke = 0.8
    elif r >= 7:
        ind_stroke = 0.7

    fill_color = label_fill or colors["control_text"]

    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{colors["knob_fill"]}" stroke="{colors["knob_stroke"]}" stroke-width="{stroke_w:.1f}"/>',
        f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r}" '
        f'stroke="{colors["indicator"]}" stroke-width="{ind_stroke:.1f}"/>',
    ]

    base_y = cy + r + 3.0
    for i, line in enumerate(label_lines):
        ly = base_y + i * 2.3
        parts.append(
            f'<text x="{cx}" y="{ly:.1f}" fill="{fill_color}" '
            f'{_FONT} font-size="1.8" text-anchor="middle">{line}</text>'
        )

    return "\n".join(parts)


# ── LED ───────────────────────────────────────────────────────────────────────

def svg_led(cx: float, cy: float, colors: dict, fill: str = "", stroke: str = "") -> str:
    f = fill or colors["led_fill"]
    s = stroke or colors["led_stroke"]
    return (
        f'<circle cx="{cx}" cy="{cy}" r="1.2" '
        f'fill="{f}" stroke="{s}" stroke-width="0.4"/>'
    )


def svg_led_labeled(
    cx: float,
    cy: float,
    label: str,
    label_fill: str,
    rules: Any,
    colors: dict,
    font_size: float = 1.8,
    fill: str = "",
    stroke: str = "",
    label_dy: float | None = None,
    label_border: bool = False,
    rect_w: float | None = None,
) -> str:
    dy = label_dy if label_dy is not None else rules.jack_label_dy
    label_y = cy + dy
    parts = [svg_led(cx, cy, colors, fill=fill, stroke=stroke)]
    if label_border:
        rw = rect_w if rect_w is not None else 7.0
        ry = rules.rect_y(label_y)
        parts.append(
            f'<rect x="{cx - rw / 2:.2f}" y="{ry:.2f}" width="{rw}" '
            f'height="{rules.output_rect_h}" rx="{rules.output_rect_rx}" '
            f'fill="none" stroke="{colors["output_rect_s"]}" stroke-width="0.3"/>'
        )
    parts.append(
        f'<text x="{cx}" y="{label_y:.1f}" fill="{label_fill}" '
        f'{_FONT} font-size="{font_size}" text-anchor="middle">{label}</text>'
    )
    return "\n".join(parts)


# ── Switches ──────────────────────────────────────────────────────────────────

# Dailywell 2M sub-miniature toggles are rendered top-view: a round bushing/nut
# with a short toggle lever. The lever rests toward the default position so the
# panel mock-up reads as a toggle, not a slide. The bushing is a circle (rotation-
# invariant); a `rotate` value spins the lever vector by the same SVG rotate(deg)
# convention used for the KiCad footprint overlay, so the front-panel symbol stays
# in agreement with the rotated footprint. Silkscreen labels are not rotated.
_TOGGLE_NUT_R = 2.475   # panel hole Ø4.95mm
_TOGGLE_LEVER = 2.2     # lever length from bushing centre


def _rotate_vec(dx: float, dy: float, deg: float) -> tuple[float, float]:
    """Rotate (dx, dy) by deg using the SVG rotate() convention (CW, y-down)."""
    if not deg:
        return dx, dy
    import math
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return dx * c - dy * s, dx * s + dy * c


def _toggle_bushing(cx: float, cy: float, colors: dict) -> str:
    return (
        f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{_TOGGLE_NUT_R}" '
        f'fill="{colors["switch_body"]}" stroke="{colors["jack_outer"]}" stroke-width="0.4"/>'
    )


def _toggle_lever(cx: float, cy: float, dx: float, dy: float, colors: dict) -> str:
    tx, ty = cx + dx, cy + dy
    return (
        f'<line x1="{cx:.3f}" y1="{cy:.3f}" x2="{tx:.3f}" y2="{ty:.3f}" '
        f'stroke="{colors["switch_slug_s"]}" stroke-width="1.0" stroke-linecap="round"/>'
        f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="0.9" '
        f'fill="{colors["switch_slug"]}" stroke="{colors["switch_slug_s"]}" stroke-width="0.3"/>'
    )


def svg_toggle_2pos(
    cx: float,
    cy: float,
    label_above: str,
    label_above_y: float,
    pos_labels: list[str],
    pos_xs: list[float],
    pos_y: float,
    colors: dict,
    rotate: int = 0,
) -> str:
    """Dailywell DW3 2-position (ON-ON) sub-mini toggle, top-view. Lever rests toward
    position 0 (left at rotate=0), rotated by `rotate` to match the footprint."""
    dx, dy = _rotate_vec(-_TOGGLE_LEVER, 0.0, rotate)
    parts = [
        f'<text x="{cx}" y="{label_above_y}" fill="{colors["jack_text"]}" '
        f'{_FONT} font-size="1.8" text-anchor="middle">{label_above}</text>',
        _toggle_bushing(cx, cy, colors),
        _toggle_lever(cx, cy, dx, dy, colors),
    ]
    for lx, pl in zip(pos_xs, pos_labels):
        parts.append(
            f'<text x="{lx}" y="{pos_y}" fill="{colors["jack_text"]}" '
            f'{_FONT} font-size="1.6" text-anchor="middle">{pl}</text>'
        )
    return "\n".join(parts)


def svg_toggle_3pos(
    cx: float,
    cy: float,
    pos_labels: list[str],
    pos_ys: list[float],
    label_below: str,
    label_below_y: float,
    colors: dict,
    rotate: int = 0,
) -> str:
    """Dailywell DW5 3-position (ON-ON-ON) sub-mini toggle, top-view. Lever rests
    toward the top position (rotate=0), rotated by `rotate` to match the footprint."""
    dx, dy = _rotate_vec(0.0, -_TOGGLE_LEVER, rotate)
    parts = [
        _toggle_bushing(cx, cy, colors),
        _toggle_lever(cx, cy, dx, dy, colors),
    ]
    lx = cx + _TOGGLE_NUT_R + 1.2    # position labels to the right
    for ply, pl in zip(pos_ys, pos_labels):
        parts.append(
            f'<text x="{lx:.2f}" y="{ply}" fill="{colors["switch_label"]}" '
            f'{_FONT} font-size="1.4" text-anchor="start">{pl}</text>'
        )
    parts.append(
        f'<text x="{cx}" y="{label_below_y}" fill="{colors["control_text"]}" '
        f'{_FONT} font-size="1.8" text-anchor="middle">{label_below}</text>'
    )
    return "\n".join(parts)


# ── Slider label (the widget itself is drawn by VCV Rack) ─────────────────────

def svg_slider_label(cx: float, y: float, colors: dict) -> str:
    return (
        f'<text x="{cx}" y="{y}" fill="{colors["control_text"]}" '
        f'{_FONT} font-size="1.8" text-anchor="middle">CUTOFF</text>'
    )


def svg_slider_V45(
    cx: float,
    cy: float,
    label: str,
    colors: dict,
    travel: float = 45.0,
    rotate: int = 0,
) -> str:
    """45mm travel vertical slide potentiometer panel symbol.

    cx, cy = centre of travel (panel anchor).  The slot spans ±(travel/2+1.5)mm
    vertically; the label appears above the slot. `rotate` spins the directional
    track/ticks (about the anchor, matching the rotated footprint) while the label
    stays upright.
    """
    half_travel = travel / 2.0          # 22.5 mm
    slot_h = travel + 3.0               # 48 mm — 1.5 mm margin each end
    slot_w = 2.5
    slot_x = cx - slot_w / 2
    slot_y = cy - slot_h / 2

    top_y = cy - half_travel
    bot_y = cy + half_travel
    label_y = slot_y - 3.5

    body = [
        # Slot body
        f'<rect x="{slot_x:.2f}" y="{slot_y:.2f}" width="{slot_w}" height="{slot_h:.1f}"'
        f' rx="1.2" fill="{colors["knob_fill"]}" stroke="{colors["knob_stroke"]}"'
        f' stroke-width="0.4"/>',
        # Travel-end tick marks
        f'<line x1="{cx-3.5:.2f}" y1="{top_y:.2f}" x2="{cx+3.5:.2f}" y2="{top_y:.2f}"'
        f' stroke="{colors["knob_stroke"]}" stroke-width="0.5"/>',
        f'<line x1="{cx-3.5:.2f}" y1="{bot_y:.2f}" x2="{cx+3.5:.2f}" y2="{bot_y:.2f}"'
        f' stroke="{colors["knob_stroke"]}" stroke-width="0.5"/>',
        # Centre (neutral) tick — subtle reference mark only; handle drawn by VCV Rack widget
        f'<line x1="{cx-2:.2f}" y1="{cy:.2f}" x2="{cx+2:.2f}" y2="{cy:.2f}"'
        f' stroke="{colors["indicator"]}" stroke-width="0.35"/>',
    ]
    # The track/ticks are body-fixed and rotate with the part; the label stays upright.
    if rotate:
        body = [f'<g transform="rotate({rotate} {cx} {cy})">' + "".join(body) + "</g>"]

    parts = body + [
        # Label above slot (stays upright regardless of rotation)
        f'<text x="{cx}" y="{label_y:.1f}" fill="{colors["jack_text"]}"'
        f' {_FONT} font-size="1.8" text-anchor="middle">{label}</text>',
    ]
    return "\n".join(parts)


# ── Separators ────────────────────────────────────────────────────────────────

def svg_separator_v(
    x: float,
    y1: float,
    y2: float,
    style: str,
    colors: dict,
) -> str:
    if style == "main_cyan":
        return (
            f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
            f'stroke="{colors["cyan"]}" stroke-width="0.5" opacity="0.55"/>'
        )
    elif style == "subdiv_gray":
        return (
            f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
            f'stroke="{colors["subdiv"]}" stroke-width="0.4"/>'
        )
    else:
        return (
            f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
            f'stroke="{colors["zone_div"]}" stroke-width="0.5"/>'
        )


def svg_separator_h(
    x1: float,
    x2: float,
    y: float,
    style: str,
    colors: dict,
) -> str:
    if style == "main_cyan":
        return (
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
            f'stroke="{colors["cyan"]}" stroke-width="0.5" opacity="0.55"/>'
        )
    else:
        return (
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
            f'stroke="{colors["zone_div"]}" stroke-width="0.5"/>'
        )


def svg_separator_h_labeled(
    x1: float,
    x2: float,
    y: float,
    label: str,
    label_x: float,
    style: str,
    colors: dict,
    font_size: float = 2.0,
    char_width_factor: float = 0.65,
    gap: float = 2.0,
) -> str:
    """Horizontal separator with an inline label that breaks the line.

    The line is drawn in two segments — left and right of the text — with
    a small gap on each side.  The text sits centred on the line using
    dominant-baseline="middle".
    """
    half_w = len(label) * font_size * char_width_factor / 2
    x_gap_left  = label_x - half_w - gap
    x_gap_right = label_x + half_w + gap

    if style == "main_cyan":
        stroke = colors["cyan"]
        extra  = ' opacity="0.55"'
    else:
        stroke = colors["zone_div"]
        extra  = ""

    parts = []
    if x1 < x_gap_left:
        parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x_gap_left:.2f}" y2="{y}" '
            f'stroke="{stroke}" stroke-width="0.5"{extra}/>'
        )
    if x_gap_right < x2:
        parts.append(
            f'<line x1="{x_gap_right:.2f}" y1="{y}" x2="{x2}" y2="{y}" '
            f'stroke="{stroke}" stroke-width="0.5"{extra}/>'
        )
    parts.append(
        f'<text x="{label_x}" y="{y}" fill="{colors["control_text"]}" '
        f'{_FONT} font-size="{font_size}" text-anchor="middle" '
        f'dominant-baseline="middle">{label}</text>'
    )
    return "\n".join(parts)


# ── Zone title ────────────────────────────────────────────────────────────────

def svg_zone_title(
    x: float,
    y: float,
    text: str,
    colors: dict,
    subtitle: str | None = None,
) -> str:
    parts = [
        f'<text x="{x}" y="{y}" fill="{colors["cyan"]}" '
        f'{_FONT} font-size="2.4" text-anchor="middle" font-weight="bold">{text}</text>'
    ]
    if subtitle:
        sub_y = y + 4.5
        parts.append(
            f'<text x="{x}" y="{sub_y}" fill="{colors["brand_text"]}" '
            f'{_FONT} font-size="1.6" text-anchor="middle">{subtitle}</text>'
        )
    return "\n".join(parts)


# ── Mounting hole ─────────────────────────────────────────────────────────────

def svg_mounting_hole(cx: float, cy: float) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="1.6" '
        f'fill="#0d0d0d" stroke="#2a2a2a" stroke-width="0.5"/>'
    )


# ── Panel background ──────────────────────────────────────────────────────────

def svg_panel_background(w: float, h: float, colors: dict) -> str:
    top_strip_h = 9.0   # extends to the INPUT zone separator line
    bot_strip_h = top_strip_h   # symmetric with the top strip
    bottom_y = h - bot_strip_h
    parts = [
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="{colors["panel_bg"]}"/>',
        f'<rect x="0" y="0" width="{w}" height="{top_strip_h}" fill="{colors["panel_strip"]}"/>',
        f'<rect x="0" y="{bottom_y}" width="{w}" height="{bot_strip_h}" fill="{colors["panel_strip"]}"/>',
    ]
    return "\n".join(parts)
