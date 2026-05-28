"""panel_editor.py — builds the interactive panel editor HTML.

The editor (`design/panel-editor.html`) is a single static HTML+JS file generated
from `tools/panel-data.yaml`.  It lets you drag / rotate / add / delete components,
change panel HP, add dividers, toggle layers, see live DRC, and export a
comment-preserving YAML you can paste back over `tools/panel-data.yaml`.

All heavy geometry/rule logic is shared with the Python build tool by *exporting the
real constants* from `panel_rules` and the real KiCad footprint geometry from
`panel_kicad` into the page as JSON — so the in-browser editor stays in lock-step
with `build_panel.py --check` and never drifts.

This module deliberately has no file-writing side effects of its own; the caller
(`build_panel.py`) decides where to write the returned HTML string.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import panel_rules as rules_mod
import panel_kicad as kicad_mod
from panel_rules import DesignRules

_HERE = Path(__file__).resolve().parent
_EDITOR_JS = _HERE / "editor" / "editor.js"
_EDITOR_CSS = _HERE / "editor" / "editor.css"


# ── Constant export (single source of truth: panel_rules) ─────────────────────

def _export_rules_constants(rules: DesignRules) -> dict[str, Any]:
    """Dump the real DRC constants from panel_rules so the JS port matches exactly."""
    return {
        # PCB courtyard rectangles (x1, y1, x2, y2) relative to component anchor
        "courtyards": {
            "JACK_CY":        list(rules_mod.JACK_CY),
            "POT_CY":         list(rules_mod.POT_CY),
            "TRIMPOT_CY":     list(rules_mod.TRIMPOT_CY),
            "TOGGLE_CY":      list(rules_mod.TOGGLE_CY),
            "LED_CY":         list(rules_mod.LED_CY),
            "SLIDER_V45_CY":  list(rules_mod.SLIDER_V45_CY),
        },
        # Panel-face nut / hole radii
        "panel_r": {
            "jack":        rules.jack_nut_r,
            "trimpot":     rules_mod.TRIMPOT_PANEL_R,
            "pot":         rules.pot_nut_r,
            "toggle":      rules_mod.TOGGLE_PANEL_R,
            "led":         rules_mod.LED_PANEL_R,
            "slider":      rules_mod.SLIDER_V45_PANEL_W,
        },
        # Visual knob-cap radii (panel face)
        "knob_cap_r": {"knob_medium": 4.5, "knob_large": 7.0, "knob_xl": 9.0},
        # Type-set membership
        "type_sets": {
            "jack":       sorted(rules_mod.JACK_TYPES),
            "pot":        sorted(rules_mod.POT_TYPES),
            "trimpot":    ["trimpot"],
            "slider":     sorted(rules_mod.SLIDER_TYPES),
            "toggle_dw3": sorted(rules_mod.TOGGLE_2POS_TYPES),
            "toggle_dw5": sorted(rules_mod.TOGGLE_3POS_TYPES),
            "led":        sorted(rules_mod.LED_TYPES),
        },
        "mounting_hole_clearance_mm": rules_mod.MOUNTING_HOLE_CLEARANCE_MM,
        # Design-rule scalars needed for resolution + keepout in JS
        "design_rules": {
            "top_keepout":       rules.top_keepout,
            "bot_keepout_start": rules.bot_keepout_start,
            "cv_jack_cy":        rules.cv_jack_cy,
            "att_cy":            rules.att_cy,
            "att_offset":        rules.att_offset,
            "jack_label_dy":     rules.jack_label_dy,
            "output_rect_dy":    rules.output_rect_dy,
            "output_rect_h":     rules.output_rect_h,
            "output_rect_rx":    rules.output_rect_rx,
            "jack_pitch":        rules.jack_pitch,
            "indicator_length":  rules.indicator_length,
            "x_offset":          rules.x_offset,
            "jack_nut_r":        rules.jack_nut_r,
            "pot_nut_r":         rules.pot_nut_r,
        },
    }


def _export_kicad_templates() -> dict[str, str]:
    """Per component type: real .kicad_mod geometry rendered as an SVG group at anchor (0,0).

    The JS positions each with `translate(cx,cy) rotate(deg)` wrapping this template,
    which reproduces panel_kicad._prims_to_svg's anchor-rotation semantics exactly.
    """
    templates: dict[str, str] = {}
    for ctype, (rel_path, ox, oy) in kicad_mod._FOOTPRINT_MAP.items():
        prims = kicad_mod._load_footprint(rel_path)
        if not prims:
            templates[ctype] = ""
            continue
        # Render at anchor origin (cx=cy=0, rotate=0) → '<g transform="translate(-ox,-oy)">...'
        templates[ctype] = kicad_mod._prims_to_svg(prims, 0.0, 0.0, ox, oy, 0)
    return templates


def _export_footprint_names() -> dict[str, str]:
    """Human-readable footprint file name per type, for the inspector."""
    out: dict[str, str] = {}
    for ctype, (rel_path, _ox, _oy) in kicad_mod._FOOTPRINT_MAP.items():
        out[ctype] = Path(rel_path).stem
    return out


# ── HTML assembly ─────────────────────────────────────────────────────────────

def build_editor_html(data: dict, rules: DesignRules, yaml_text: str) -> str:
    """Return the full interactive editor HTML as a string."""
    payload = {
        "data":            data,
        "yaml_text":       yaml_text,
        "constants":       _export_rules_constants(rules),
        "kicad_templates": _export_kicad_templates(),
        "footprint_names": _export_footprint_names(),
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    js  = _EDITOR_JS.read_text(encoding="utf-8")
    css = _EDITOR_CSS.read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>POGO Panel Editor</title>
  <style>
{css}
  </style>
</head>
<body>
  <div id="app">
    <header id="topbar"></header>
    <div id="main">
      <aside id="left"></aside>
      <section id="canvas-wrap"><div id="canvas"></div><div id="drc-panel"></div></section>
      <aside id="right"></aside>
    </div>
  </div>
  <div id="export-modal" class="modal hidden"></div>
  <script id="panel-payload" type="application/json">{payload_json}</script>
  <script>
{js}
  </script>
</body>
</html>"""
