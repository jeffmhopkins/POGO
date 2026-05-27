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
) -> str:
    """Thonkiconn jack symbol: outer ring + centre dot + optional output rect + label."""
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

    # output border rect
    if io == "output":
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


# ── Trimpots ──────────────────────────────────────────────────────────────────

def svg_trimpot(
    cx: float,
    cy: float,
    label: str,
    rules: Any,
    colors: dict,
    label_font_size: float = 1.8,
) -> str:
    """Small trim-pot symbol: circle + indicator line + label below."""
    r = 2.5
    label_y = cy + r + 3.0  # consistent spacing below the circle
    ind_y2 = cy - rules.indicator_length
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{colors["knob_fill"]}" stroke="{colors["knob_stroke"]}" stroke-width="0.5"/>',
        f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{ind_y2}" '
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
) -> str:
    label_y = cy + rules.jack_label_dy
    parts = [
        svg_led(cx, cy, colors, fill=fill, stroke=stroke),
        f'<text x="{cx}" y="{label_y:.1f}" fill="{label_fill}" '
        f'{_FONT} font-size="{font_size}" text-anchor="middle">{label}</text>',
    ]
    return "\n".join(parts)


# ── Switches ──────────────────────────────────────────────────────────────────

def svg_switch_H2(
    cx: float,
    cy: float,
    label_above: str,
    label_above_y: float,
    pos_labels: list[str],
    pos_xs: list[float],
    pos_y: float,
    colors: dict,
) -> str:
    """2-position horizontal slide switch."""
    # Body: 9mm wide, 2.4mm tall, centred at cx
    bx = cx - 4.5
    by = cy - 1.2
    # Slug: 3.5mm wide, 2.8mm tall, left position (pos 0)
    sx = bx + 0.5
    sy = cy - 1.4
    parts = [
        f'<text x="{cx}" y="{label_above_y}" fill="{colors["jack_text"]}" '
        f'{_FONT} font-size="1.8" text-anchor="middle">{label_above}</text>',
        f'<rect x="{bx:.2f}" y="{by:.2f}" width="9" height="2.4" rx="1.2" '
        f'fill="{colors["switch_body"]}" stroke="{colors["jack_outer"]}" stroke-width="0.5"/>',
        f'<rect x="{sx:.2f}" y="{sy:.2f}" width="3.5" height="2.8" rx="0.8" '
        f'fill="{colors["switch_slug"]}" stroke="{colors["switch_slug_s"]}" stroke-width="0.3"/>',
    ]
    for px, pl in zip(pos_xs, pos_labels):
        parts.append(
            f'<text x="{px}" y="{pos_y}" fill="{colors["jack_text"]}" '
            f'{_FONT} font-size="1.6" text-anchor="middle">{pl}</text>'
        )
    return "\n".join(parts)


def svg_switch_H3(
    cx: float,
    cy: float,
    pos_labels: list[str],
    pos_xs: list[float],
    pos_y: float,
    label_below: str,
    label_below_y: float,
    colors: dict,
) -> str:
    """3-position horizontal slide switch."""
    # Body: 12mm wide, 2.4mm tall, centred at cx
    bx = cx - 6.0
    by = cy - 1.2
    # Slug starts at centre position
    sx = cx - 1.75
    sy = cy - 1.4
    parts = [
        f'<rect x="{bx:.2f}" y="{by:.2f}" width="12" height="2.4" rx="1.2" '
        f'fill="{colors["switch_body"]}" stroke="{colors["jack_outer"]}" stroke-width="0.5"/>',
        f'<rect x="{sx:.2f}" y="{sy:.2f}" width="3.5" height="2.8" rx="0.8" '
        f'fill="{colors["switch_slug"]}" stroke="{colors["switch_slug_s"]}" stroke-width="0.3"/>',
    ]
    for px, pl in zip(pos_xs, pos_labels):
        parts.append(
            f'<text x="{px}" y="{pos_y}" fill="{colors["switch_label"]}" '
            f'{_FONT} font-size="1.6" text-anchor="middle">{pl}</text>'
        )
    parts.append(
        f'<text x="{cx}" y="{label_below_y}" fill="{colors["control_text"]}" '
        f'{_FONT} font-size="1.8" text-anchor="middle">{label_below}</text>'
    )
    return "\n".join(parts)


def svg_switch_V3(
    cx: float,
    cy_body_top: float,
    body_height: float,
    slug_y_offset: float,
    pos_labels: list[str],
    pos_ys: list[float],
    label_below: str,
    label_below_y: float,
    colors: dict,
) -> str:
    """3-position vertical slide switch."""
    bx = cx - 1.2
    sx = cx - 1.4
    sy = cy_body_top + slug_y_offset
    parts = [
        f'<rect x="{bx:.2f}" y="{cy_body_top}" width="2.4" height="{body_height}" rx="1.2" '
        f'fill="{colors["switch_body"]}" stroke="{colors["jack_outer"]}" stroke-width="0.5"/>',
        f'<rect x="{sx:.2f}" y="{sy:.2f}" width="2.8" height="3.5" rx="0.8" '
        f'fill="{colors["switch_slug"]}" stroke="{colors["switch_slug_s"]}" stroke-width="0.3"/>',
    ]
    lx = cx + 1.4
    for py, pl in zip(pos_ys, pos_labels):
        parts.append(
            f'<text x="{lx}" y="{py}" fill="{colors["switch_label"]}" '
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
    bot_strip_h = 4.5
    bottom_y = h - bot_strip_h
    parts = [
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="{colors["panel_bg"]}"/>',
        f'<rect x="0" y="0" width="{w}" height="{top_strip_h}" fill="{colors["panel_strip"]}"/>',
        f'<rect x="0" y="{bottom_y}" width="{w}" height="{bot_strip_h}" fill="{colors["panel_strip"]}"/>',
    ]
    return "\n".join(parts)
