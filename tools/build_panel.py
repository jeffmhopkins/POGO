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
import re
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
from panel_kicad import build_kicad_layer  # noqa: E402


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
    header = f"{'ZONE':<20} {'ID':<30} {'TYPE':<16} {'cx':>7} {'cy':>7}  {'rot':>3}"
    print(header)
    print("-" * len(header))
    for zone in data.get("zones", []):
        zone_id = zone.get("id", "")
        if zone_id in ("band1", "band2", "band3"):
            comps = _resolve_band_components(zone, rules)
            for comp in comps:
                cid    = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"
                ctype  = comp.get("type", "")
                cx     = float(comp.get("cx", 0))
                cy     = float(comp.get("cy", 0))
                rotate = int(comp.get("rotate", 0))
                rot_s  = f"{rotate}°" if rotate else ""
                print(f"{zone_id:<20} {cid:<30} {ctype:<16} {cx:>7.2f} {cy:>7.2f}  {rot_s:>3}")
        else:
            for comp in zone.get("components", []):
                resolved = _resolve_comp(comp, rules, zone=zone)
                cid    = resolved.get("id") or resolved.get("cpp_id") or resolved.get("cpp_param") or "?"
                ctype  = resolved.get("type", "")
                cx     = float(resolved.get("cx", 0))
                cy     = float(resolved.get("cy", 0))
                rotate = int(resolved.get("rotate", 0))
                rot_s  = f"{rotate}°" if rotate else ""
                print(f"{zone_id:<20} {cid:<30} {ctype:<16} {cx:>7.2f} {cy:>7.2f}  {rot_s:>3}")


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


# ── Query helpers ─────────────────────────────────────────────────────────────

def _comp_index(data: dict, rules: DesignRules) -> dict[str, dict]:
    """Build a dict mapping component ID → resolved component dict."""
    index: dict[str, dict] = {}
    for comp in resolve_components(data, rules):
        key = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param")
        if key:
            index[key] = comp
    return index


def print_dist(data: dict, rules: DesignRules, id1: str, id2: str) -> None:
    """Print center-to-center, nut-edge, and PCB-courtyard distance between two components."""
    from panel_rules import get_panel_r, _get_courtyard, _rect_min_gap  # noqa: E402
    idx = _comp_index(data, rules)
    c1, c2 = idx.get(id1), idx.get(id2)
    if c1 is None:
        print(f"Component '{id1}' not found.", file=sys.stderr)
        return
    if c2 is None:
        print(f"Component '{id2}' not found.", file=sys.stderr)
        return

    cx1, cy1 = float(c1.get("cx", 0)), float(c1.get("cy", 0))
    cx2, cy2 = float(c2.get("cx", 0)), float(c2.get("cy", 0))
    t1,  t2  = c1.get("type", ""),     c2.get("type", "")
    rot1     = int(c1.get("rotate", 0))
    rot2     = int(c2.get("rotate", 0))
    r1       = get_panel_r(t1, rules)
    r2       = get_panel_r(t2, rules)

    dx   = cx2 - cx1
    dy   = cy2 - cy1
    dist = (dx ** 2 + dy ** 2) ** 0.5

    rot1_s = f"  rotate={rot1}°" if rot1 else ""
    rot2_s = f"  rotate={rot2}°" if rot2 else ""
    print(f"\n  {id1:<22} {t1:<14}  cx={cx1:>7.2f}  cy={cy1:>7.2f}{rot1_s}")
    print(f"  {id2:<22} {t2:<14}  cx={cx2:>7.2f}  cy={cy2:>7.2f}{rot2_s}")
    print()

    align_x = "← aligned on cx" if abs(dx) < 0.01 else ""
    align_y = "← aligned on cy" if abs(dy) < 0.01 else ""
    print(f"  Δcx = {dx:+.2f} mm ({abs(dx)/5.08:.2f} HP)  {align_x}")
    print(f"  Δcy = {dy:+.2f} mm ({abs(dy)/5.08:.2f} HP)  {align_y}")
    print(f"  Center-to-center:  {dist:.2f} mm")

    if r1 > 0 and r2 > 0:
        nut_gap = dist - r1 - r2
        status  = "✓" if nut_gap >= 0 else "CLASH"
        print(f"  Nut/hole clearance: {nut_gap:+.2f} mm  (r={r1}+r={r2}={r1+r2})  {status}")

    rect1 = _get_courtyard(cx1, cy1, t1, rot1)
    rect2 = _get_courtyard(cx2, cy2, t2, rot2)
    if rect1 and rect2:
        pcb_gap = _rect_min_gap(rect1, rect2)
        status  = "✓" if pcb_gap >= 0 else "OVERLAP"
        print(f"  PCB courtyard gap:  {pcb_gap:+.2f} mm  {status}")
    print()


def print_snap_to(
    data: dict,
    rules: DesignRules,
    comp_id: str,
    direction: str,
    new_type: str,
    gap_mm: float,
) -> None:
    """Print cx/cy for placing new_type with gap_mm nut-edge clearance from comp_id."""
    from panel_rules import get_panel_r, _get_courtyard, _rect_min_gap  # noqa: E402
    idx = _comp_index(data, rules)
    c = idx.get(comp_id)
    if c is None:
        print(f"Component '{comp_id}' not found.", file=sys.stderr)
        return

    cx     = float(c.get("cx", 0))
    cy     = float(c.get("cy", 0))
    ctype  = c.get("type", "")
    rotate = int(c.get("rotate", 0))
    r_ex   = get_panel_r(ctype, rules)
    r_new  = get_panel_r(new_type, rules)
    offset = r_ex + gap_mm + r_new

    direction = direction.lower()
    if direction == "right":
        new_cx, new_cy = cx + offset, cy
    elif direction == "left":
        new_cx, new_cy = cx - offset, cy
    elif direction in ("below", "down"):
        new_cx, new_cy = cx, cy + offset
    elif direction in ("above", "up"):
        new_cx, new_cy = cx, cy - offset
    else:
        print(f"Unknown direction '{direction}'. Use: right, left, above/up, below/down.",
              file=sys.stderr)
        return

    hp_x = new_cx / 5.08
    hp_y = new_cy / 5.08
    print(f"\n  Snap {new_type} {direction} of {comp_id} ({ctype}  r={r_ex:.1f}mm),"
          f" {gap_mm:.1f}mm nut-edge gap:")
    print(f"  offset = r_existing({r_ex}) + gap({gap_mm}) + r_new({r_new}) = {offset:.2f}mm")
    print()
    print(f"  new cx = {new_cx:.2f} mm  ({hp_x:.2f} HP)")
    print(f"  new cy = {new_cy:.2f} mm  ({hp_y:.2f} HP)")

    # PCB courtyard verification at the proposed position
    rect_ex  = _get_courtyard(cx, cy, ctype, rotate)
    rect_new = _get_courtyard(new_cx, new_cy, new_type, 0)
    if rect_ex and rect_new:
        pcb_gap = _rect_min_gap(rect_ex, rect_new)
        status  = "✓" if pcb_gap >= 0 else "OVERLAP — check PCB clearance"
        print(f"  PCB courtyard gap: {pcb_gap:+.2f} mm  {status}")
    print()


def print_zone_bbox(data: dict, rules: DesignRules, zone_id: str) -> None:
    """Print the center-point bounding box and zone parameters for a zone."""
    found = False
    comps = []
    for zone in data.get("zones", []):
        if zone.get("id") != zone_id:
            continue
        found = True
        for comp in zone.get("components", []):
            comps.append(_resolve_comp(comp, rules, zone=zone))

    if not found:
        print(f"Zone '{zone_id}' not found.", file=sys.stderr)
        return
    if not comps:
        print(f"Zone '{zone_id}' has no components.")
        return

    cx_vals = [float(c.get("cx", 0)) for c in comps]
    cy_vals = [float(c.get("cy", 0)) for c in comps]
    min_cx, max_cx = min(cx_vals), max(cx_vals)
    min_cy, max_cy = min(cy_vals), max(cy_vals)

    print(f"\n  Zone '{zone_id}' component bbox (centres):")
    print(f"  cx: {min_cx:.2f} – {max_cx:.2f} mm  (span {max_cx-min_cx:.2f} mm = {(max_cx-min_cx)/5.08:.2f} HP)")
    print(f"  cy: {min_cy:.2f} – {max_cy:.2f} mm  (span {max_cy-min_cy:.2f} mm)")

    for zone in data.get("zones", []):
        if zone.get("id") == zone_id and "x_start" in zone:
            x_start   = float(zone["x_start"])
            col_pitch = float(zone.get("col_pitch", rules.jack_pitch))
            cols      = int(zone.get("cols", 0))
            right_x   = x_start + cols * col_pitch
            print(f"  zone x: {x_start:.2f} – {right_x:.2f} mm"
                  f"  ({cols} cols × {col_pitch:.2f} mm pitch = {right_x-x_start:.2f} mm)")
    print()


# ── YAML patcher ─────────────────────────────────────────────────────────────

def _yaml_repr(val: Any) -> str:
    """Return the canonical YAML text representation of a parsed scalar value."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        for d in range(0, 8):
            s = f"{val:.{d}f}"
            if abs(float(s) - val) < 1e-9:
                return s
        return repr(val)
    if isinstance(val, str):
        return val
    return str(val)


def _fmt_val(v: float) -> str:
    """Format a float for YAML output — strip trailing zeros (80.0 → '80', 79.5 → '79.5')."""
    if v == int(v):
        return str(int(v))
    s = f"{v:.3f}".rstrip("0")
    return s if not s.endswith(".") else s[:-1]


def _apply_yaml_patches(data_path: Path, patches: list[tuple[str, str, str, str]]) -> None:
    """Apply targeted text patches to a YAML file preserving comments/formatting.

    Each patch is (entity_id, key, old_str, new_str).
    Locates 'id: entity_id' then finds 'key: old_str' within the same YAML block.
    """
    text  = data_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    for entity_id, key, old_str, new_str in patches:
        id_pat = re.compile(r'^(\s*)(?:- )?id:\s+' + re.escape(entity_id) + r'\s*$')
        id_line   = None
        id_indent = 0
        for i, line in enumerate(lines):
            m = id_pat.match(line)
            if m:
                id_line   = i
                id_indent = len(m.group(1))
                break

        if id_line is None:
            print(f"  WARNING: entity '{entity_id}' not found in YAML", file=sys.stderr)
            continue

        key_pat = re.compile(
            r'^(\s+)' + re.escape(key) + r':\s+' + re.escape(old_str) + r'(\s*(?:#.*)?)$'
        )
        patched = False
        for j in range(id_line + 1, min(id_line + 40, len(lines))):
            line     = lines[j]
            stripped = line.lstrip()
            if not stripped:
                continue
            if len(line) - len(stripped) <= id_indent and stripped.startswith("-"):
                break  # entered the next entity at the same nesting level
            m = key_pat.match(line)
            if m:
                lines[j] = f"{m.group(1)}{key}: {new_str}{m.group(2)}"
                patched = True
                break

        if not patched:
            print(
                f"  WARNING: '{entity_id}.{key}: {old_str}' not found in patch window",
                file=sys.stderr,
            )

    data_path.write_text("\n".join(lines), encoding="utf-8")


# ── Select / shift helpers ────────────────────────────────────────────────────

def print_select(
    data: dict, rules: DesignRules, x1: float, y1: float, x2: float, y2: float
) -> None:
    """Print all components whose resolved panel-hole centres fall within a bounding box."""
    lx, rx = min(x1, x2), max(x1, x2)
    ty, by = min(y1, y2), max(y1, y2)

    hits: list[tuple[str, dict]] = []
    for zone in data.get("zones", []):
        zone_id = zone.get("id", "")
        if zone_id in ("band1", "band2", "band3"):
            for comp in _resolve_band_components(zone, rules):
                cx = float(comp.get("cx", 0))
                cy = float(comp.get("cy", 0))
                if lx <= cx <= rx and ty <= cy <= by:
                    hits.append((zone_id, comp))
        else:
            for comp in zone.get("components", []):
                resolved = _resolve_comp(comp, rules, zone=zone)
                cx = float(resolved.get("cx", 0))
                cy = float(resolved.get("cy", 0))
                if lx <= cx <= rx and ty <= cy <= by:
                    hits.append((zone_id, resolved))

    if not hits:
        print(f"  No components in bbox ({lx:.2f},{ty:.2f})–({rx:.2f},{by:.2f}).")
        return

    header = f"{'ZONE':<20} {'ID':<30} {'TYPE':<16} {'cx':>7} {'cy':>7}  {'rot':>3}"
    print(f"\n  Selection bbox: x=[{lx:.2f}–{rx:.2f}]  y=[{ty:.2f}–{by:.2f}]"
          f"  ({len(hits)} component(s))\n")
    print("  " + header)
    print("  " + "-" * len(header))
    for zone_id, comp in hits:
        cid    = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"
        ctype  = comp.get("type", "")
        cx     = float(comp.get("cx", 0))
        cy     = float(comp.get("cy", 0))
        rotate = int(comp.get("rotate", 0))
        rot_s  = f"{rotate}°" if rotate else ""
        print(f"  {zone_id:<20} {cid:<30} {ctype:<16} {cx:>7.2f} {cy:>7.2f}  {rot_s:>3}")
    print()


def shift_zone(
    data: dict,
    rules: DesignRules,
    zone_id: str,
    dx: float,
    dy: float,
    apply: bool = False,
    data_path: Path | None = None,
) -> None:
    """Print (and optionally apply) a bulk position shift for all components in a zone."""
    target_zone = None
    for zone in data.get("zones", []):
        if zone.get("id") == zone_id:
            target_zone = zone
            break

    if target_zone is None:
        print(f"Zone '{zone_id}' not found.", file=sys.stderr)
        return

    if zone_id in ("band1", "band2", "band3"):
        print(
            "Band zones use cx_left/cx_center/cx_right — edit the YAML directly for band shifts.",
            file=sys.stderr,
        )
        return

    patches: list[tuple[str, str, str, str]] = []
    preview: list[str] = []

    if dx != 0 and "x_start" in target_zone:
        old_xs = target_zone["x_start"]
        new_xs = float(old_xs) + dx
        old_s  = _yaml_repr(old_xs)
        new_s  = _fmt_val(new_xs)
        preview.append(f"  zone  {zone_id:<26}  x_start: {old_s} → {new_s}")
        patches.append((zone_id, "x_start", old_s, new_s))

    col_rel_noted = False
    for comp in target_zone.get("components", []):
        resolved = _resolve_comp(comp, rules, zone=target_zone)
        cid = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"

        if dx != 0 and "cx" in comp:
            old_cx = comp["cx"]
            new_cx = float(old_cx) + dx
            old_s  = _yaml_repr(old_cx)
            new_s  = _fmt_val(new_cx)
            preview.append(f"  comp  {cid:<26}  cx: {old_s} → {new_s}")
            patches.append((cid, "cx", old_s, new_s))
        elif dx != 0 and "col" in comp and not col_rel_noted:
            preview.append(f"  (column-relative components shift via zone x_start above)")
            col_rel_noted = True

        if dy != 0 and "cy" in comp:
            old_cy_raw  = comp["cy"]
            resolved_cy = float(resolved.get("cy", 0))
            new_cy      = resolved_cy + dy
            old_s       = _yaml_repr(old_cy_raw)
            new_s       = _fmt_val(new_cy)
            preview.append(f"  comp  {cid:<26}  cy: {old_s} → {new_s}")
            patches.append((cid, "cy", old_s, new_s))

    if not patches:
        print(f"  Nothing to shift in zone '{zone_id}' (dx={dx:+.3g}, dy={dy:+.3g}).")
        return

    print(f"\n  Shift zone '{zone_id}'  dx={dx:+.3g}mm  dy={dy:+.3g}mm"
          f"  ({len(patches)} change(s)):\n")
    for ln in preview:
        print(ln)
    print()

    dp = data_path or DATA_FILE
    if apply:
        _apply_yaml_patches(dp, patches)
        print(f"  Applied {len(patches)} patch(es) to {dp.name}")
        new_data  = load_data(dp)
        new_rules = DesignRules.from_data(new_data)
        viols     = run_drc(new_data, new_rules)
        if viols:
            print(f"\n  DRC after shift: {len(viols)} violation(s):", file=sys.stderr)
            for v in viols:
                print(f"    {v}", file=sys.stderr)
        else:
            print("  DRC after shift: PASS")
    else:
        print(f"  (dry-run — add --apply to write changes to {dp.name})")


def shift_select(
    data: dict,
    rules: DesignRules,
    x1: float, y1: float,
    x2: float, y2: float,
    dx: float, dy: float,
    apply: bool = False,
    data_path: Path | None = None,
) -> None:
    """Print (and optionally apply) a bulk shift for all components inside a bounding box."""
    lx, rx = min(x1, x2), max(x1, x2)
    ty, by = min(y1, y2), max(y1, y2)

    patches: list[tuple[str, str, str, str]] = []
    preview: list[str] = []
    col_rel_warned: set[str] = set()

    for zone in data.get("zones", []):
        zone_id = zone.get("id", "")
        if zone_id in ("band1", "band2", "band3"):
            continue
        for comp in zone.get("components", []):
            resolved = _resolve_comp(comp, rules, zone=zone)
            cx = float(resolved.get("cx", 0))
            cy = float(resolved.get("cy", 0))
            if not (lx <= cx <= rx and ty <= cy <= by):
                continue

            cid = comp.get("id") or comp.get("cpp_id") or comp.get("cpp_param") or "?"

            if dx != 0:
                if "cx" in comp:
                    old_cx = comp["cx"]
                    new_cx = float(old_cx) + dx
                    old_s  = _yaml_repr(old_cx)
                    new_s  = _fmt_val(new_cx)
                    preview.append(f"  [{zone_id}] {cid:<28}  cx: {old_s} → {new_s}")
                    patches.append((cid, "cx", old_s, new_s))
                elif "col" in comp and zone_id not in col_rel_warned:
                    col_rel_warned.add(zone_id)
                    preview.append(
                        f"  [{zone_id}] NOTE: column-relative components — "
                        f"use --shift {zone_id} {dx:+.3g} 0 to shift the zone's x_start"
                    )

            if dy != 0 and "cy" in comp:
                old_cy_raw  = comp["cy"]
                resolved_cy = float(resolved.get("cy", 0))
                new_cy      = resolved_cy + dy
                old_s       = _yaml_repr(old_cy_raw)
                new_s       = _fmt_val(new_cy)
                preview.append(f"  [{zone_id}] {cid:<28}  cy: {old_s} → {new_s}")
                patches.append((cid, "cy", old_s, new_s))

    if not preview:
        print(f"  No components in bbox ({lx:.2f},{ty:.2f})–({rx:.2f},{by:.2f}).")
        return

    print(f"\n  Shift-select  bbox=({lx:.2f},{ty:.2f})–({rx:.2f},{by:.2f})"
          f"  dx={dx:+.3g}  dy={dy:+.3g}  ({len(patches)} patch(es)):\n")
    for ln in preview:
        print(ln)
    print()

    if not patches:
        print("  No patches to apply (all matching components are column-relative for cx).")
        return

    dp = data_path or DATA_FILE
    if apply:
        _apply_yaml_patches(dp, patches)
        print(f"  Applied {len(patches)} patch(es) to {dp.name}")
        new_data  = load_data(dp)
        new_rules = DesignRules.from_data(new_data)
        viols     = run_drc(new_data, new_rules)
        if viols:
            print(f"\n  DRC after shift: {len(viols)} violation(s):", file=sys.stderr)
            for v in viols:
                print(f"    {v}", file=sys.stderr)
        else:
            print("  DRC after shift: PASS")
    else:
        print(f"  (dry-run — add --apply to write changes to {dp.name})")


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
    lines.append("  <!-- ── ZONE DIVIDERS (dim gray horizontal) ──────────────────────────────── -->")
    for sep in data.get("separators", []):
        if sep["type"] == "h" and sep["style"] == "zone_div":
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
        return svg.svg_led(cx, cy, colors,
                           fill=comp.get("led_fill", ""),
                           stroke=comp.get("led_stroke", ""))

    elif ctype == "led_labeled":
        lbl_fill = comp.get("label_fill", colors["jack_text"])
        lbl      = comp.get("label", "")
        return svg.svg_led_labeled(cx, cy, lbl, lbl_fill, rules, colors,
                                   fill=comp.get("led_fill", ""),
                                   stroke=comp.get("led_stroke", ""))

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
    """Return component positions grouped by type for overlay rendering.

    Each entry is (cx, cy, rotate) for types with PCB courtyards, or
    (cx, cy, r_cap) for knob visual caps.
    """
    jacks:    list[tuple] = []  # (cx, cy, rotate)
    pots:     list[tuple] = []  # (cx, cy, rotate)
    knobs:    list[tuple] = []  # (cx, cy, r_cap) — visual nut cap only
    switches: list[tuple] = []  # (cx, cy, rotate)
    leds:     list[tuple] = []  # (cx, cy, rotate)

    r_cap_map = {"knob_medium": 4.5, "knob_large": 7.0, "knob_xl": 9.0}

    from panel_rules import SWITCH_TYPES, LED_TYPES, JACK_TYPES, POT_TYPES  # noqa: E402

    for comp in resolve_components(data, rules):
        cx     = float(comp.get("cx", 0))
        cy     = float(comp.get("cy", 0))
        ctype  = comp.get("type", "")
        rotate = int(comp.get("rotate", 0))

        if ctype in JACK_TYPES:
            jacks.append((cx, cy, rotate))
        elif ctype in POT_TYPES:
            pots.append((cx, cy, rotate))
            if ctype in r_cap_map:
                knobs.append((cx, cy, r_cap_map[ctype]))
        elif ctype in SWITCH_TYPES:
            switches.append((cx, cy, rotate))
        elif ctype in LED_TYPES:
            leds.append((cx, cy, rotate))

    return {
        "jacks": jacks, "pots": pots, "knobs": knobs,
        "switches": switches, "leds": leds,
        "_components": list(resolve_components(data, rules)),
    }


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

    m_w = re.search(r'width="([\d.]+)px"', svg_content)
    m_h = re.search(r'height="([\d.]+)px"', svg_content)
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
    # Nut circles are rotationally symmetric — rotation doesn't change their shape.
    nuts_parts: list[str] = []
    for cx, cy, _rot in overlay["jacks"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="5" fill="rgba(255,204,0,0.35)" stroke="#ffcc00" stroke-width="0.25"/>'
        )
    for cx, cy, _rot in overlay["pots"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="5.5" fill="rgba(100,180,255,0.35)" stroke="#64b4ff" stroke-width="0.25"/>'
        )
    for cx, cy, r in overlay["knobs"]:
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="{r}" fill="rgba(255,140,0,0.25)" stroke="#ff8c00" stroke-width="0.25"/>'
        )
    for cx, cy, _rot in overlay.get("switches", []):
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="3.15" fill="rgba(220,100,255,0.35)" stroke="#dc64ff" stroke-width="0.25"/>'
        )
    for cx, cy, _rot in overlay.get("leds", []):
        nuts_parts.append(
            f'    <circle cx="{cx}" cy="{cy}" r="1.6" fill="rgba(100,220,100,0.35)" stroke="#64dc64" stroke-width="0.25"/>'
        )
    nuts_layer = (
        '\n  <g id="layer-nuts" style="display:none;">\n'
        + "\n".join(nuts_parts)
        + "\n  </g>"
    )

    # ── PCB footprints layer (KiCad courtyards, rotation-aware) ──────────────────
    from panel_rules import _get_courtyard as _cy_rect  # noqa: E402
    pcb_parts: list[str] = []

    def _pcb_rect(cx, cy, ctype, rotate, fill, stroke):
        rect = _cy_rect(cx, cy, ctype, rotate)
        if rect is None:
            return
        x1, y1, x2, y2 = rect
        pcb_parts.append(
            f'    <rect x="{x1:.3f}" y="{y1:.3f}" width="{x2-x1:.3f}" height="{y2-y1:.3f}"'
            f' fill="{fill}" stroke="{stroke}" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>'
        )

    for cx, cy, rotate in overlay["jacks"]:
        _pcb_rect(cx, cy, "jack_input", rotate, "rgba(255,204,0,0.15)", "#ffcc00")
    for cx, cy, rotate in overlay["pots"]:
        _pcb_rect(cx, cy, "trimpot", rotate, "rgba(100,180,255,0.15)", "#64b4ff")
    for cx, cy, r in overlay["knobs"]:
        _pcb_rect(cx, cy, "knob_medium", 0, "rgba(255,140,0,0.12)", "#ff8c00")
    for cx, cy, rotate in overlay.get("switches", []):
        _pcb_rect(cx, cy, "switch_H2", rotate, "rgba(220,100,255,0.15)", "#dc64ff")
    for cx, cy, rotate in overlay.get("leds", []):
        _pcb_rect(cx, cy, "led", rotate, "rgba(100,220,100,0.15)", "#64dc64")
    pcb_layer = (
        '\n  <g id="layer-pcb" style="display:none;">\n'
        + "\n".join(pcb_parts)
        + "\n  </g>"
    )

    # ── KiCad footprint layer ───────────────────────────────────────────────────
    if overlay:
        # Rebuild resolved component list from overlay tuples (not stored separately)
        # — pass the raw resolved list in via overlay["_components"] if available
        raw_comps = overlay.get("_components", [])
        kicad_svg = build_kicad_layer(raw_comps)
    else:
        kicad_svg = '<g id="layer-kicad" style="display:none;"></g>'

    assembled = svg_open + "\n"
    assembled += f'  <g id="layer-panel">\n{inner}\n  </g>\n'
    assembled += keepout_layer + "\n"
    assembled += nuts_layer    + "\n"
    assembled += pcb_layer     + "\n"
    assembled += "\n" + kicad_svg + "\n"
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
            "NUT CLEARANCE":  "#ff88aa",
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
        ("layer-pcb",     "PCB Courtyards (simplified)",  False),
        ("layer-kicad",   "KiCad Footprints (actual)",    False),
    ]

    checkboxes_html = ""
    for lid, lname, checked in layers:
        ck = "checked" if checked else ""
        checkboxes_html += (
            f'<label style="margin-right:16px;cursor:pointer;">'
            f'<input type="checkbox" {ck} onchange="toggleLayer(\'{lid}\', this.checked)"> '
            f'{lname}</label>\n'
        )

    legend_items = [
        ("#ffcc00", "●", "Jack nut  r=5.0mm"),
        ("#64b4ff", "●", "Pot / trimpot nut  r=5.5mm"),
        ("#ff8c00", "●", "Knob cap  (visual)"),
        ("#dc64ff", "●", "Switch hole  r=3.15mm"),
        ("#64dc64", "●", "LED hole  r=1.6mm"),
        ("#ffcc00", "⬚", "PCB courtyard  (simplified bbox; dashed)"),
        ("#f5a623", "⬚", "KiCad fab outline  F.Fab"),
        ("#cccccc", "⬚", "KiCad silkscreen  F.SilkS"),
        ("#ff44ff", "●", "KiCad pad  (through-hole marker)"),
        ("rgba(255,60,60,0.7)", "■", "Rail keep-out  y&lt;10 / y&gt;118.5mm"),
    ]
    legend_html = '<div style="margin-top:8px;padding:7px 14px;background:#161616;border:1px solid #2a2a2a;border-radius:4px;max-width:812px;font-size:0.82em;color:#999;">'
    legend_html += '<span style="color:#aaa;font-weight:bold;">Overlay legend: </span>'
    for color, sym, desc in legend_items:
        legend_html += (
            f'<span style="margin-right:18px;white-space:nowrap;">'
            f'<span style="color:{color};">{sym}</span> {desc}</span>'
        )
    legend_html += '</div>'

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
  {legend_html}
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
        epilog="""
Query commands (no files written):
  --check                        DRC report; exit 1 on violations
  --list                         Table of all resolved component positions
  --next ZONE_ID                 Next x_start after a column-relative zone
  --dist ID1 ID2                 Center-to-center, nut-edge, and PCB courtyard distances
  --snap-to ID DIR TYPE GAP      cx/cy for TYPE with GAP mm nut-edge clearance from ID
                                 DIR: right | left | above | below
                                 TYPE: jack_input | trimpot | knob_medium | switch_H2 | led | …
  --zone-bbox ZONE_ID            Component bounding box for a zone
  --select X1 Y1 X2 Y2           List components whose centres fall within the bbox
  --shift ZONE_ID DX DY          Preview bulk shift of all components in a zone
  --shift-select X1 Y1 X2 Y2 DX DY  Preview bulk shift of components in a bbox
  --apply                        Write --shift / --shift-select changes to panel-data.yaml
""",
    )
    parser.add_argument("--resource",  action="store_true", help="Write res/Pogo-source.svg")
    parser.add_argument("--design",    action="store_true", help="Write design/panel-debug.html")
    parser.add_argument("--mfr",       action="store_true", help="Write res/Pogo.svg via inkscape")
    parser.add_argument("--cpp",       action="store_true", help="Print C++ stubs to stdout")
    parser.add_argument("--check",     action="store_true", help="DRC only; exit 1 on violations")
    parser.add_argument("--list",      action="store_true", help="Print table of all resolved components")
    parser.add_argument("--next",      metavar="ZONE_ID",   help="Print next x_start after a zone")
    parser.add_argument("--dist",      nargs=2, metavar=("ID1", "ID2"),
                        help="Distance and clearance between two components")
    parser.add_argument("--snap-to",   nargs=4, metavar=("ID", "DIR", "TYPE", "GAP"),
                        help="cx/cy for placing TYPE component GAP mm from ID in DIR")
    parser.add_argument("--zone-bbox",     metavar="ZONE_ID",   help="Bounding box of a zone's components")
    parser.add_argument("--select",        nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                        help="List components within a bounding box (mm)")
    parser.add_argument("--shift",         nargs=3, metavar=("ZONE_ID", "DX", "DY"),
                        help="Preview (or --apply) bulk shift of all components in a zone")
    parser.add_argument("--shift-select",  nargs=6,
                        metavar=("X1", "Y1", "X2", "Y2", "DX", "DY"),
                        help="Preview (or --apply) bulk shift of components in a bbox")
    parser.add_argument("--apply",         action="store_true",
                        help="Apply --shift / --shift-select changes to panel-data.yaml")
    args = parser.parse_args()

    is_query = any([args.check, args.list, args.next, args.dist,
                    getattr(args, "snap_to", None), getattr(args, "zone_bbox", None),
                    getattr(args, "select", None),  getattr(args, "shift", None),
                    getattr(args, "shift_select", None)])

    # Default: both --resource and --design
    if not any([args.resource, args.design, args.mfr, args.cpp, is_query]):
        args.resource = True
        args.design   = True

    data  = load_data()
    rules = DesignRules.from_data(data)

    # ── Query-only paths (no SVG build needed) ────────────────────────────────
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

    if args.dist:
        print_dist(data, rules, args.dist[0], args.dist[1])
        return 0

    snap_to = getattr(args, "snap_to", None)
    if snap_to:
        try:
            gap_mm = float(snap_to[3])
        except ValueError:
            print(f"GAP must be a number, got '{snap_to[3]}'", file=sys.stderr)
            return 1
        print_snap_to(data, rules, snap_to[0], snap_to[1], snap_to[2], gap_mm)
        return 0

    zone_bbox = getattr(args, "zone_bbox", None)
    if zone_bbox:
        print_zone_bbox(data, rules, zone_bbox)
        return 0

    if args.select:
        x1, y1, x2, y2 = [float(v) for v in args.select]
        print_select(data, rules, x1, y1, x2, y2)
        return 0

    if args.shift:
        try:
            dx, dy = float(args.shift[1]), float(args.shift[2])
        except ValueError as e:
            print(f"DX and DY must be numbers: {e}", file=sys.stderr)
            return 1
        shift_zone(data, rules, args.shift[0], dx, dy, apply=args.apply, data_path=DATA_FILE)
        return 0

    shift_sel = getattr(args, "shift_select", None)
    if shift_sel:
        try:
            x1, y1, x2, y2, dx, dy = [float(v) for v in shift_sel]
        except ValueError as e:
            print(f"All --shift-select arguments must be numbers: {e}", file=sys.stderr)
            return 1
        shift_select(data, rules, x1, y1, x2, y2, dx, dy, apply=args.apply, data_path=DATA_FILE)
        return 0

    violations = run_drc(data, rules)

    if args.check:
        if violations:
            from collections import defaultdict
            groups: dict[str, list[str]] = defaultdict(list)
            for v in violations:
                tag = v.split("]")[0].lstrip("[") if v.startswith("[") else "OTHER"
                groups[tag].append(v)
            print(f"DRC FAILED — {len(violations)} violation(s):", file=sys.stderr)
            for tag, items in sorted(groups.items()):
                print(f"\n  [{tag}] ({len(items)})", file=sys.stderr)
                for v in items:
                    print(f"    {v}", file=sys.stderr)
            return 1
        print("DRC PASS — no violations.")
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
