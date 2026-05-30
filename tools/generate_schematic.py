#!/usr/bin/env python3
"""POGO 48HP schematic generator — data-driven, per-block vertical slice.

Reads a block netlist (specs/<block>/<block>.nets.yaml) and emits a KiCad 7
(into kicad/).
schematic (kicad/pogo-<block>.kicad_sch). Connectivity is name-based: every
REF.PIN listed under a net gets a global label, so pins sharing a net name are
joined. Symbols, pin geometry, and emitters are reused from kicad_common.py;
footprints/MPNs are resolved through the components/ registry (tools/components.py).

The first slice is block-A (input buffers). Adding a block = adding a nets file.

Design properties
─────────────────
- Byte-stable output: UUIDs are derived deterministically from content, so the
  committed .kicad_sch is reproducible and CI can gate on drift (--check).
- Pin coverage is validated: every pin of every placed symbol must appear in
  exactly one net or in `no_connect`; nets may not reference unknown refs/pins.

Usage:
  python3 tools/generate_schematic.py            # regenerate all block schematics
  python3 tools/generate_schematic.py --check     # CI gate: validate + drift check
  python3 tools/generate_schematic.py --block block-A   # nets live in specs/block-*/
"""

from __future__ import annotations

import math
import re
import sys
import uuid as _uuid
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent           # tools/
_REPO = _HERE.parent
_KICAD = _REPO / "kicad"   # generated .kicad_sch live here (artifacts)
_NETS_DIR = _REPO / "specs"      # per-block nets live with each block spec (specs/block-*/)
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "tools"))

import kicad_common as kc          # noqa: E402
import components as registry      # noqa: E402
import symbols as S                # noqa: E402  (data-driven symbol archetypes)


# ── deterministic UUIDs (byte-stable output) ─────────────────────────────────

_UUID_NS = _uuid.UUID("0a90f1c0-9060-4b1e-9a3e-b0b0b0b0b0b0")  # fixed POGO namespace


def _make_det_uid():
    n = [0]

    def _uid():
        n[0] += 1
        return str(_uuid.uuid5(_UUID_NS, str(n[0])))
    return _uid


# ── symbol archetypes: loaded from components/symbols.yaml (keyed by the nets `sym:`
# token). Each carries lib_id, body graphics, per-unit pins (with the connection-point
# `at`), placement offsets, and a datasheet citation. Renderer: tools/symbols.py.
_SYMS = S.load()

# Layout grid (mm). Symbols only need to not overlap — nets connect by name.
_COL_DX, _ROW_DY, _NCOLS, _X0, _Y0 = 60.0, 55.0, 3, 40.0, 40.0



def _resolve_footprint(part_str: str | None) -> str:
    """components.yaml `part:` string -> 'POGO_<lib>:<name>' or '' if unresolved."""
    if not part_str:
        return ""
    p = registry.part_for(part_str)
    fpr = (p or {}).get("footprint") or {}
    if fpr.get("lib") and fpr.get("name"):
        return f'POGO_{fpr["lib"]}:{fpr["name"]}'
    return ""


def load_block(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if "parts" not in data or "nets" not in data:
        raise ValueError(f"{path}: missing 'parts' or 'nets'")
    return data


# ── validation ───────────────────────────────────────────────────────────────

def validate_block(block: dict) -> list[str]:
    """Pin-coverage + reference integrity check. Returns list of problems."""
    errs: list[str] = []
    parts = block["parts"]
    nets = block["nets"]
    no_connect = set(block.get("no_connect") or [])

    # Every part must use a known symbol; gather its full pin set.
    part_pins: dict[str, set[str]] = {}
    for ref, spec in parts.items():
        sym = spec.get("sym")
        if sym not in _SYMS:
            errs.append(f"{ref}: unknown sym '{sym}'")
            continue
        part_pins[ref] = S.all_pin_numbers(_SYMS[sym])

    # Each net entry must reference a known ref.pin exactly once across all nets.
    seen: dict[str, str] = {}     # "REF.PIN" -> net name
    for net, pts in nets.items():
        for pt in pts:
            if "." not in pt:
                errs.append(f"net {net}: bad pin token '{pt}' (want REF.PIN)")
                continue
            ref, pin = pt.split(".", 1)
            if ref not in parts:
                errs.append(f"net {net}: unknown ref '{ref}' in '{pt}'")
                continue
            if ref in part_pins and pin not in part_pins[ref]:
                errs.append(f"net {net}: {ref} has no pin '{pin}' "
                            f"(has {sorted(part_pins[ref])})")
                continue
            if pt in seen:
                errs.append(f"pin {pt} appears in both '{seen[pt]}' and '{net}'")
            seen[pt] = net

    # no_connect tokens must be real pins and must NOT also be in a net.
    for pt in no_connect:
        if "." not in pt:
            errs.append(f"no_connect: bad token '{pt}'")
            continue
        ref, pin = pt.split(".", 1)
        if ref not in part_pins or pin not in part_pins[ref]:
            errs.append(f"no_connect: '{pt}' is not a real pin")
        elif pt in seen:
            errs.append(f"no_connect: '{pt}' is also wired in net '{seen[pt]}'")

    # Coverage: every pin of every part is wired or explicitly no-connect.
    for ref, pins in sorted(part_pins.items()):
        for pin in sorted(pins):
            pt = f"{ref}.{pin}"
            if pt not in seen and pt not in no_connect:
                errs.append(f"uncovered pin {pt} (wire it or add to no_connect)")

    return errs


# ── structural verification (independent re-parse of the emitted file) ───────
# This is the "would it connect in KiCad?" check done without KiCad: parse the
# generated s-expr, re-derive every pin's connection point straight from the
# lib_symbols geometry, and confirm each global label lands exactly on a pin and
# each pin is either labeled or an intended no-connect. Catches malformed s-expr,
# dangling lib_ids, and any mismatch between the placed-pin coords and the emitted
# lib_symbols geometry (the archetype's connection points, from components/symbols.yaml).

_EPS = 1e-3


def _parse_sexpr(text: str):
    """Parse KiCad s-expression text into nested lists (quoted strings unquoted)."""
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    pos = 0

    def atom(t):
        return t[1:-1].replace('\\"', '"') if t.startswith('"') else t

    def parse():
        nonlocal pos
        node = []
        while pos < len(toks):
            t = toks[pos]; pos += 1
            if t == "(":
                node.append(parse())
            elif t == ")":
                return node
            else:
                node.append(atom(t))
        raise ValueError("unexpected end of input (unbalanced parentheses)")

    if not toks or toks[0] != "(":
        raise ValueError("not an s-expression")
    pos = 1
    root = parse()
    if pos != len(toks):
        raise ValueError("trailing tokens after top-level form")
    return root


def _children(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def _first(node, head):
    cs = _children(node, head)
    return cs[0] if cs else None


def _xform(ox, oy, angle, px, py):
    a = math.radians(angle)
    return (ox + px * math.cos(a) - py * math.sin(a),
            oy + px * math.sin(a) + py * math.cos(a))


def structural_check(text: str, block: dict) -> list[str]:
    """Re-parse the emitted schematic and verify geometry/connectivity."""
    errs: list[str] = []
    try:
        root = _parse_sexpr(text)
    except Exception as e:           # noqa: BLE001
        return [f"s-expr parse failed: {e}"]
    if not root or root[0] != "kicad_sch":
        return ["root node is not kicad_sch"]

    # lib_symbols: lib_id -> {unit_int: {pin_number: (local_x, local_y)}}
    # Sub-symbols are named "<value>_<unit>_<style>"; pins belong to that unit.
    libs: dict[str, dict[int, dict[str, tuple[float, float]]]] = {}
    libnode = _first(root, "lib_symbols")
    for sym in _children(libnode or [], "symbol"):
        name = sym[1] if len(sym) > 1 and isinstance(sym[1], str) else None
        if not name:
            continue
        units: dict[int, dict[str, tuple[float, float]]] = {}
        for sub in _children(sym, "symbol"):
            subname = sub[1] if len(sub) > 1 and isinstance(sub[1], str) else ""
            m = re.search(r"_(\d+)_\d+$", subname)
            u = int(m.group(1)) if m else 1
            for pin in _children(sub, "pin"):
                at = _first(pin, "at")
                num = _first(pin, "number")
                if at and num:
                    units.setdefault(u, {})[num[1]] = (float(at[1]), float(at[2]))
        libs[name] = units

    # placements: REF.PIN -> (x, y). Each placement carries its (unit N); only that
    # unit's pins exist at that instance (multi-unit symbols → one instance per unit).
    pin_xy: dict[str, tuple[float, float]] = {}
    for sym in _children(root, "symbol"):
        libid = _first(sym, "lib_id")
        at = _first(sym, "at")
        if not libid or not at:
            continue
        lib = libid[1]
        if lib not in libs:
            errs.append(f"placement lib_id '{lib}' not in lib_symbols")
            continue
        ref = None
        for prop in _children(sym, "property"):
            if len(prop) > 2 and prop[1] == "Reference":
                ref = prop[2]
        unit_node = _first(sym, "unit")
        unit = int(unit_node[1]) if unit_node and len(unit_node) > 1 else 1
        ox, oy, ang = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        for num, (px, py) in libs[lib].get(unit, {}).items():
            pin_xy[f"{ref}.{num}"] = _xform(ox, oy, ang, px, py)

    # global labels: net -> list of (x, y)
    label_pts: list[tuple[str, float, float]] = []
    for gl in _children(root, "global_label"):
        at = _first(gl, "at")
        if at:
            label_pts.append((gl[1], float(at[1]), float(at[2])))

    def near(a, b):
        return abs(a[0] - b[0]) < _EPS and abs(a[1] - b[1]) < _EPS

    # (0) shorts: two or more DISTINCT nets whose labels land on the same point
    # (catches overlapping symbol pins — e.g. multi-unit gates placed at one origin).
    by_coord: dict[tuple[float, float], set[str]] = {}
    for net, lx, ly in label_pts:
        by_coord.setdefault((round(lx, 3), round(ly, 3)), set()).add(net)
    for (x, y), nets_here in sorted(by_coord.items()):
        if len(nets_here) > 1:
            errs.append(f"short: nets {sorted(nets_here)} coincide at ({x:.3f},{y:.3f})")

    # (1) every label sits exactly on a pin; record which pins are labeled.
    labeled: set[str] = set()
    for net, lx, ly in label_pts:
        hit = [pt for pt, xy in pin_xy.items() if near(xy, (lx, ly))]
        if not hit:
            errs.append(f"net '{net}' label at ({lx:.3f},{ly:.3f}) is not on any pin")
        else:
            labeled.update(hit)

    # (2) coverage: each pin is labeled or an intended no-connect (geometric).
    no_connect = set(block.get("no_connect") or [])
    for pt in sorted(pin_xy):
        if pt not in labeled and pt not in no_connect:
            errs.append(f"pin {pt} has no label and is not in no_connect")
    for pt in sorted(no_connect):
        if pt in labeled:
            errs.append(f"no_connect pin {pt} unexpectedly carries a label")

    return errs


# ── generation ───────────────────────────────────────────────────────────────

def build(block: dict) -> str:
    """Build the schematic text for one block. Deterministic."""
    kc.uid = _make_det_uid()          # byte-stable UUIDs for this build
    kc.reset()
    kc.begin_schematic("A2")

    parts = block["parts"]
    used_syms = {spec["sym"] for spec in parts.values()}

    kc.emit("(lib_symbols")
    for sym in sorted(used_syms):
        kc.emit(S.emit_symbol(_SYMS[sym]))
    kc.emit(")")

    # Place symbols on a grid (declaration order) and record pin coordinates.
    pin_xy: dict[str, tuple[float, float]] = {}
    for i, (ref, spec) in enumerate(parts.items()):
        col, row = i % _NCOLS, i // _NCOLS
        ox, oy = _X0 + col * _COL_DX, _Y0 + row * _ROW_DY
        sym = spec["sym"]
        arch = _SYMS[sym]
        lib_id = arch["lib_id"]
        fp = _resolve_footprint(spec.get("part"))
        layout = S.placement(arch)
        if len(layout) > 1:
            # Place each gate unit as its own instance at a distinct offset.
            host = layout[0][0]
            for unit, dx, dy in layout:
                kc.place_symbol(lib_id, ref, spec.get("value", ""), ox + dx, oy + dy,
                                unit=unit, footprint=(fp if unit == host else ""))
                for pin, (px, py) in S.pin_points(arch, ox + dx, oy + dy, unit=unit).items():
                    pin_xy[f"{ref}.{pin}"] = (px, py)
        else:
            kc.place_symbol(lib_id, ref, spec.get("value", ""), ox, oy, footprint=fp)
            for pin, (px, py) in S.pin_points(arch, ox, oy).items():
                pin_xy[f"{ref}.{pin}"] = (px, py)

    # Drop a global label at every wired pin (name-based connectivity).
    boundary = set(block.get("boundary") or [])
    for net, pts in block["nets"].items():
        shape = "output" if net in boundary else "input"
        for pt in pts:
            if pt in pin_xy:
                px, py = pin_xy[pt]
                kc.connect_pin(net, px, py, shape=shape)

    kc.end_schematic()
    return "\n".join(kc.OUT) + "\n"


def footprint_pad_advisory(blocks: list[dict]) -> list[str]:
    """Warn-first guard: every symbol pin should map to a real footprint pad.

    For each part that binds BOTH a symbol archetype and a footprint, the symbol's
    pin NUMBERS must be a subset of the footprint's pad numbers (allowing the
    archetype's authored `nc_pads`). A symbol pin with no pad is a connection that
    silently vanishes at PCB netlist time — the class of error that the data-driven
    refactor exists to catch. Parts with no footprint yet (generic R/C) are skipped.

    Returned as WARNINGS, not failures: the current jack archetype uses numeric pins
    against an alpha-pad (S/T/TN) footprint — a known, pre-existing divergence to
    reconcile in its own change, not something this refactor should block CI on.
    """
    try:
        import footprint_svg as fps
    except Exception:                                # noqa: BLE001
        return []
    pads: dict[str, set[str]] = {}
    for fid, _slug, path in fps.iter_footprints():
        pads[fid] = {p["num"] for p in fps.parse_footprint(path.read_text())["pads"]}

    warns: list[str] = []
    seen: set[tuple] = set()
    for block in blocks:
        for ref, spec in block["parts"].items():
            sym = spec.get("sym")
            part = spec.get("part")
            if sym not in _SYMS or not part:
                continue
            fid = _resolve_footprint(part)
            if not fid or fid not in pads:
                continue
            key = (sym, fid)
            if key in seen:
                continue
            seen.add(key)
            nc = set(_SYMS[sym].get("nc_pads") or [])
            missing = S.all_pin_numbers(_SYMS[sym]) - pads[fid] - nc
            if missing:
                warns.append(f"{sym} → {fid}: symbol pin(s) {sorted(missing)} "
                             f"have no footprint pad (pads: {sorted(pads[fid])})")
    return warns


def out_path_for(block: dict) -> Path:
    return _KICAD / f"pogo-{block['block']}.kicad_sch"


def _block_files() -> list[Path]:
    return sorted(_NETS_DIR.glob("block-*/*.nets.yaml"))


def _main(argv: list[str]) -> int:
    check = "--check" in argv
    only = None
    if "--block" in argv:
        only = argv[argv.index("--block") + 1]

    files = _block_files()
    if only:
        files = [f for f in files if f.name.startswith(only)]
        if not files:
            print(f"No nets file for block '{only}' in {_NETS_DIR}")
            return 1

    rc = 0
    loaded: list[dict] = []

    # Symbol archetype self-test (structure, emitter faithfulness, datasheet
    # provenance) — a malformed archetype would corrupt every block's symbols.
    sym_errs = S.selfcheck()
    if sym_errs:
        print("SCHEMATIC CHECK — FAIL (symbol archetypes):")
        for e in sym_errs:
            print(f"  - {e}")
        rc = 1

    for f in files:
        block = load_block(f)
        loaded.append(block)
        errs = validate_block(block)
        if errs:
            print(f"SCHEMATIC CHECK — FAIL ({f.name}):")
            for e in errs:
                print(f"  - {e}")
            rc = 1
            continue

        text = build(block)
        serrs = structural_check(text, block)
        if serrs:
            print(f"SCHEMATIC CHECK — FAIL ({f.name}, structural):")
            for e in serrs:
                print(f"  - {e}")
            rc = 1
            continue

        out = out_path_for(block)
        if check:
            if not out.is_file():
                print(f"SCHEMATIC CHECK — FAIL: {out.name} missing (run without --check)")
                rc = 1
            elif out.read_text() != text:
                print(f"SCHEMATIC CHECK — FAIL: {out.name} is stale (regenerate)")
                rc = 1
            else:
                print(f"SCHEMATIC CHECK — OK: {out.name} "
                      f"({len(block['parts'])} parts, {len(block['nets'])} nets)")
        else:
            out.write_text(text)
            opens, closes = text.count("("), text.count(")")
            print(f"Wrote {out.relative_to(_REPO)}  "
                  f"[{len(block['parts'])} parts, {len(block['nets'])} nets, "
                  f"parens {'balanced' if opens == closes else 'UNBALANCED'}]")

    # Warn-first symbol-pin ⊆ footprint-pad guard (does not fail the build).
    for w in footprint_pad_advisory(loaded):
        print(f"SCHEMATIC CHECK — WARN: {w}")

    return rc


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
