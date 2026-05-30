"""panel_kicad.py — Render actual KiCad footprint geometry as SVG overlay layers.

Parses .kicad_mod files and emits SVG <g> elements positioned at each component's
panel-hole (or shaft) centre so the real PCB geometry is visible in the debug viewer.

Supports: fp_line, fp_circle, pad (thru_hole)
Layers rendered: F.Fab, F.SilkS, plus pad markers.

Footprint origin notes
──────────────────────
Jack     (WQP-PJ398SM): footprint origin = sleeve S pad at (0,0); barrel centre (panel
         hole axis) = (0, 6.48) per datasheet (WQP-PJ398SM PCB layout, "6.48" dim).
         Offset (0, 6.48) aligns the barrel circle with cx,cy.
Pot      (Alpha RD901F): origin = pin 1; shaft centre is at (7.5, 2.5) in footprint
         coords → subtract (7.5, 2.5) to align shaft with cx,cy.
Trimpot  (Bourns 3296W Vertical): origin = pin 1 at (0,0); actuator centre = pin 2
         (wiper) at (0, 2.5) → offset (0, 2.5) aligns actuator with cx,cy.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

# ── Repo-relative paths ────────────────────────────────────────────────────────

_REPO = Path(__file__).resolve().parent.parent
_FP_ROOT = _REPO / "components" / "footprints"

# Map component type → (relative footprint path, origin_offset_x, origin_offset_y)
# origin_offset is the footprint's origin relative to the component's "panel anchor".
# The SVG transform becomes: translate(cx-ox, cy-oy), so any footprint point (px,py)
# renders at panel position (px+cx-ox, py+cy-oy).
#
# Jack (WQP-PJ398SM): footprint origin = sleeve S pad at (0,0); barrel centre (panel hole
#   axis) at footprint (0, 6.48). Offset (0, 6.48): barrel circle renders at (cx, cy).
#   Sleeve S pad renders at panel (cx, cy-6.48) — behind the panel face, physically correct.
#   The green origin cross-hair marks (cx, cy) = panel hole axis = barrel centre.
#
# Pot (Alpha RD901F): footprint origin = pin1; shaft centre = (7.5, 2.5).
#   F.Fab shaft circle is at (center 7.5 2.5) → setting ox=7.5, oy=2.5 aligns it to (cx,cy).
# Built dynamically from components/footprints.yaml via tools/components.py (was a
# hardcoded literal). Same shape {panel_type: (rel_path, ox, oy)} and same order, so
# footprint_courtyard() and the editor payload are byte-identical. Anchor-offset notes:
#   jack:    (0, 6.48) barrel centre = panel hole; trimpot: (0, 2.5) wiper = pin2;
#   knob:    (7.5, 2.5) Alpha RD901F shaft (all knob caps share this footprint);
#   slider/led/toggle: origin already at the panel anchor.
from components import footprint_map as _component_footprint_map  # noqa: E402

_FOOTPRINT_MAP: dict[str, tuple[str, float, float]] = _component_footprint_map()

# Visual style per KiCad layer.
# F.CrtYd is intentionally omitted: the KiCad footprints use a component-specific
# visual anchor (e.g. barrel body for jacks) rather than the sleeve/hole centre, so
# the footprint F.CrtYd lines would be offset from the DRC courtyard boxes shown in
# layer-pcb. Accurate courtyards are provided by layer-pcb (panel_rules.py).
_LAYER_STYLE: dict[str, dict] = {
    "F.Fab":   {"stroke": "#f5a623", "fill": "rgba(245,166,35,0.08)", "sw": 0.10, "dash": ""},
    "F.SilkS": {"stroke": "#cccccc", "fill": "none",                  "sw": 0.10, "dash": ""},
}
_PAD_STYLE  = {"stroke": "#ff44ff", "fill": "rgba(255,68,255,0.30)", "sw": 0.12}
_PAD_RADIUS = 0.7   # visual radius for pad markers (mm)


# ── Parser ─────────────────────────────────────────────────────────────────────

def _parse_footprint(text: str) -> list[dict]:
    """Return a list of primitive dicts from .kicad_mod text."""
    prims: list[dict] = []

    # fp_line — unquoted or quoted layer names
    for m in re.finditer(
        r'\(fp_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+'
        r'\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+'
        r'\(layer\s+"?([^")\s]+)"?\)',
        text,
    ):
        prims.append({
            "t": "line",
            "x1": float(m[1]), "y1": float(m[2]),
            "x2": float(m[3]), "y2": float(m[4]),
            "layer": m[5],
        })

    # fp_circle
    for m in re.finditer(
        r'\(fp_circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+'
        r'\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+'
        r'\(layer\s+"?([^")\s]+)"?\)',
        text,
    ):
        cx, cy = float(m[1]), float(m[2])
        ex, ey = float(m[3]), float(m[4])
        r = math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2)
        prims.append({"t": "circle", "cx": cx, "cy": cy, "r": r, "layer": m[5]})

    # pad (at x y [rot]) (size w h)
    for m in re.finditer(
        r'\(pad\s+("[^"]*"|[^\s)]+)\s+([^\s)]+)\s+([^\s)]+)\s+'
        r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)'
        r'(?:\s+\(size\s+([-\d.]+)\s+([-\d.]+)\))?',
        text,
    ):
        prims.append({
            "t": "pad",
            "name": m[1],
            "pad_type": m[2],
            "shape": m[3],
            "x": float(m[4]),
            "y": float(m[5]),
            "rot": float(m[6]) if m[6] else 0.0,
            "w": float(m[7]) if m[7] else 0.0,
            "h": float(m[8]) if m[8] else 0.0,
        })

    return prims


def footprint_shapes(ctype: str) -> list[tuple[float, float, float, float]]:
    """Real keepout shapes for a component type as anchor-relative rects (x1,y1,x2,y2).

    Unlike footprint_courtyard() (one conservative bounding box), this returns the
    component's ACTUAL physical features: every pad as its own rect, plus the body —
    the F.Fab circle (round pot/jack body) if present, else the F.Fab outline bbox.
    The DRC overlap check (panel_rules) tests these per-feature so densely interleaved
    parts (e.g. 9mm pots whose side pins sit in a neighbour's gap) aren't false-flagged
    by the bounding courtyard. Coordinates are translated from the footprint origin to
    the panel anchor via the (ox,oy) offset in _FOOTPRINT_MAP.
    """
    entry = _FOOTPRINT_MAP.get(ctype)
    if entry is None:
        return []
    rel_path, ox, oy = entry
    prims = _load_footprint(rel_path)
    rects: list[tuple[float, float, float, float]] = []

    # pads → rects (90/270 rotation swaps w/h)
    for p in prims:
        if p.get("t") != "pad":
            continue
        w, h = p.get("w", 0.0), p.get("h", 0.0)
        if w <= 0 or h <= 0:
            continue
        if int(p.get("rot", 0)) % 180 == 90:
            w, h = h, w
        rects.append((p["x"] - w / 2 - ox, p["y"] - h / 2 - oy,
                      p["x"] + w / 2 - ox, p["y"] + h / 2 - oy))

    # body — bounding box of the ENTIRE F.Fab outline (lines ∪ circles). The body
    # keepout is the whole component outline; a footprint may carry both an outline
    # rectangle (the real body, e.g. a 9mm pot's squarish base) AND a small indicator
    # circle (the shaft/bushing) — taking the union avoids grabbing the tiny indicator
    # and under-claiming the body (the bug behind pots/jacks not colliding).
    xs, ys = [], []
    for p in prims:
        if "Fab" not in p.get("layer", ""):
            continue
        if p.get("t") == "line":
            xs += [p["x1"], p["x2"]]; ys += [p["y1"], p["y2"]]
        elif p.get("t") == "circle":
            xs += [p["cx"] - p["r"], p["cx"] + p["r"]]; ys += [p["cy"] - p["r"], p["cy"] + p["r"]]
    if xs:
        rects.append((min(xs) - ox, min(ys) - oy, max(xs) - ox, max(ys) - oy))

    return rects


# Cache parsed footprints so each file is read only once per build
_fp_cache: dict[str, list[dict]] = {}


def _load_footprint(rel_path: str) -> list[dict]:
    if rel_path not in _fp_cache:
        fp_path = _FP_ROOT / rel_path
        if not fp_path.exists():
            _fp_cache[rel_path] = []
        else:
            _fp_cache[rel_path] = _parse_footprint(fp_path.read_text(encoding="utf-8"))
    return _fp_cache[rel_path]


def footprint_courtyard(ctype: str) -> tuple[float, float, float, float] | None:
    """PCB courtyard (x1,y1,x2,y2) for a component type, RELATIVE TO ITS PANEL ANCHOR.

    Derived from the component's KiCad footprint F.CrtYd layer (the single source of
    truth), translated from footprint origin to the panel anchor via the (ox,oy)
    offset in _FOOTPRINT_MAP.  Returns None if the type has no footprint or no
    courtyard layer.  This replaces the hand-maintained *_CY constants — the DRC
    (panel_rules) and the web editor both consume this so they cannot drift.
    """
    entry = _FOOTPRINT_MAP.get(ctype)
    if entry is None:
        return None
    rel_path, ox, oy = entry
    prims = _load_footprint(rel_path)
    xs: list[float] = []
    ys: list[float] = []
    for p in prims:
        if p.get("t") == "line" and "CrtYd" in p.get("layer", ""):
            xs += [p["x1"], p["x2"]]
            ys += [p["y1"], p["y2"]]
    if not xs:
        return None
    return (round(min(xs) - ox, 4), round(min(ys) - oy, 4),
            round(max(xs) - ox, 4), round(max(ys) - oy, 4))


# ── SVG emitter ────────────────────────────────────────────────────────────────

def _prims_to_svg(
    prims: list[dict],
    cx: float, cy: float,
    ox: float, oy: float,
    rotate: int,
) -> str:
    """Render primitives as an SVG <g> positioned so footprint anchor (ox,oy) lands at (cx,cy).

    rotate (CW degrees) rotates around the anchor point (cx,cy), not around the
    footprint's pin-1 origin.  SVG equivalent:
        translate(cx,cy) rotate(r) translate(-ox,-oy)
    This keeps the visual anchor fixed at (cx,cy) for all rotation values.
    """
    parts: list[str] = []

    if rotate:
        transform = (
            f'transform="translate({cx:.3f},{cy:.3f})'
            f' rotate({rotate})'
            f' translate({-ox:.3f},{-oy:.3f})"'
        )
    else:
        transform = f'transform="translate({cx-ox:.3f},{cy-oy:.3f})"'

    parts.append(f'<g {transform}>')

    for p in prims:
        layer = p.get("layer", "")
        st = _LAYER_STYLE.get(layer)
        if p["t"] == "line" and st:
            dash_attr = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
            parts.append(
                f'  <line x1="{p["x1"]}" y1="{p["y1"]}" x2="{p["x2"]}" y2="{p["y2"]}"'
                f' stroke="{st["stroke"]}" stroke-width="{st["sw"]}" fill="none"{dash_attr}/>'
            )
        elif p["t"] == "circle" and st:
            dash_attr = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
            parts.append(
                f'  <circle cx="{p["cx"]:.3f}" cy="{p["cy"]:.3f}" r="{p["r"]:.3f}"'
                f' stroke="{st["stroke"]}" stroke-width="{st["sw"]}" fill="{st["fill"]}"{dash_attr}/>'
            )
        elif p["t"] == "pad":
            s = _PAD_STYLE
            parts.append(
                f'  <circle cx="{p["x"]}" cy="{p["y"]}" r="{_PAD_RADIUS}"'
                f' stroke="{s["stroke"]}" stroke-width="{s["sw"]}" fill="{s["fill"]}"/>'
            )

    parts.append("</g>")
    return "\n".join(parts)


# ── Public API ─────────────────────────────────────────────────────────────────

_ANCHOR_MARKER = (
    '<line x1="-1.8" y1="0" x2="1.8" y2="0"'
    ' stroke="#00ff88" stroke-width="0.18" fill="none"/>'
    '<line x1="0" y1="-1.8" x2="0" y2="1.8"'
    ' stroke="#00ff88" stroke-width="0.18" fill="none"/>'
    '<circle cx="0" cy="0" r="0.6"'
    ' stroke="#00ff88" stroke-width="0.18" fill="none"/>'
)


def build_kicad_layer(components: list[dict[str, Any]]) -> str:
    """Return an SVG <g id='layer-kicad'> element with all footprint geometry.

    Each component in `components` must have resolved cx, cy, type, and optionally rotate.
    A green cross-hair is drawn at each component's panel anchor (cx, cy).
    """
    pieces: list[str] = []

    for comp in components:
        ctype  = comp.get("type", "")
        fp_entry = _FOOTPRINT_MAP.get(ctype)
        if fp_entry is None:
            continue
        rel_path, ox, oy = fp_entry
        prims = _load_footprint(rel_path)
        if not prims:
            continue

        cx     = float(comp.get("cx", 0))
        cy     = float(comp.get("cy", 0))
        rotate = int(comp.get("rotate", 0))

        pieces.append(_prims_to_svg(prims, cx, cy, ox, oy, rotate))

        # Green cross-hair marks the panel anchor (cx, cy) regardless of footprint offset.
        pieces.append(
            f'<g transform="translate({cx:.3f},{cy:.3f})">{_ANCHOR_MARKER}</g>'
        )

    inner = "\n  ".join(pieces)
    return f'<g id="layer-kicad" style="display:none;">\n  {inner}\n</g>'
