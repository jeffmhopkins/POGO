"""panel_kicad.py — Render actual KiCad footprint geometry as SVG overlay layers.

Parses .kicad_mod files and emits SVG <g> elements positioned at each component's
panel-hole (or shaft) centre so the real PCB geometry is visible in the debug viewer.

Supports: fp_line, fp_circle, pad (thru_hole)
Layers rendered: F.CrtYd, F.Fab, F.SilkS, plus pad markers.

Footprint origin notes
──────────────────────
Jack  (WQP-PJ398SM): origin = panel hole centre → no offset needed.
Pot   (Alpha RD901F): origin = pin 1; shaft centre is at (7.5, 2.5) in footprint
      coords → subtract (7.5, 2.5) to align shaft with cx,cy.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

# ── Repo-relative paths ────────────────────────────────────────────────────────

_REPO = Path(__file__).resolve().parent.parent
_FP_ROOT = _REPO / "kicad" / "footprints"

# Map component type → (relative footprint path, origin_offset_x, origin_offset_y)
# origin_offset is the footprint's origin relative to the component's "panel anchor"
# (panel hole centre for jacks; shaft centre for pots).
# The SVG transform becomes: translate(cx-ox, cy-oy)
_FOOTPRINT_MAP: dict[str, tuple[str, float, float]] = {
    "jack_input": (
        "Connector_Audio.pretty/Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles.kicad_mod",
        0.0, 0.0,
    ),
    "jack_output": (
        "Connector_Audio.pretty/Jack_3.5mm_QingPu_WQP-PJ398SM_Vertical_CircularHoles.kicad_mod",
        0.0, 0.0,
    ),
    "trimpot": (
        "Potentiometer_THT.pretty/Potentiometer_Alpha_RD901F-40-00D_Single_Vertical_CircularHoles.kicad_mod",
        7.5, 2.5,   # footprint origin = pin1; shaft centre = (7.5, 2.5)
    ),
    "knob_medium": (
        "Potentiometer_THT.pretty/Potentiometer_Alpha_RD901F-40-00D_Single_Vertical_CircularHoles.kicad_mod",
        7.5, 2.5,
    ),
    "knob_large": (
        "Potentiometer_THT.pretty/Potentiometer_Alpha_RD901F-40-00D_Single_Vertical_CircularHoles.kicad_mod",
        7.5, 2.5,
    ),
    "knob_xl": (
        "Potentiometer_THT.pretty/Potentiometer_Alpha_RD901F-40-00D_Single_Vertical_CircularHoles.kicad_mod",
        7.5, 2.5,
    ),
}

# Visual style per KiCad layer
_LAYER_STYLE: dict[str, dict] = {
    "F.CrtYd": {"stroke": "#00d4ff", "fill": "none",                  "sw": 0.12, "dash": "0.8 0.5"},
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

    # pad (at x y [rot])
    for m in re.finditer(
        r'\(pad\s+("[^"]*"|[^\s)]+)\s+([^\s)]+)\s+([^\s)]+)\s+'
        r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+[-\d.]+)?\)',
        text,
    ):
        prims.append({
            "t": "pad",
            "name": m[1],
            "pad_type": m[2],
            "shape": m[3],
            "x": float(m[4]),
            "y": float(m[5]),
        })

    return prims


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


# ── SVG emitter ────────────────────────────────────────────────────────────────

def _prims_to_svg(prims: list[dict], tx: float, ty: float, rotate: int) -> str:
    """Render primitives as an SVG <g> group translated to (tx,ty) and rotated."""
    parts: list[str] = []

    # SVG transform: first rotate (around footprint origin), then translate.
    # KiCad rotate convention: CW degrees; SVG rotate() is also CW for y-down coords.
    if rotate:
        transform = f'transform="translate({tx:.3f},{ty:.3f}) rotate({rotate})"'
    else:
        transform = f'transform="translate({tx:.3f},{ty:.3f})"'

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

def build_kicad_layer(components: list[dict[str, Any]]) -> str:
    """Return an SVG <g id='layer-kicad'> element with all footprint geometry.

    Each component in `components` must have resolved cx, cy, type, and optionally rotate.
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

        # Translate so that the panel anchor (shaft/hole) lands at (cx, cy).
        # footprint origin is at (ox, oy) relative to the panel anchor → subtract offset.
        tx = cx - ox
        ty = cy - oy

        pieces.append(_prims_to_svg(prims, tx, ty, rotate))

    inner = "\n  ".join(pieces)
    return f'<g id="layer-kicad" style="display:none;">\n  {inner}\n</g>'
