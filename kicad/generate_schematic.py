#!/usr/bin/env python3
"""POGO 48HP schematic generator — data-driven, per-block vertical slice.

Reads a block netlist (kicad/nets/<block>.nets.yaml) and emits a KiCad 7
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
  python3 kicad/generate_schematic.py            # regenerate all block schematics
  python3 kicad/generate_schematic.py --check     # CI gate: validate + drift check
  python3 kicad/generate_schematic.py --block block-A
"""

from __future__ import annotations

import sys
import uuid as _uuid
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent           # kicad/
_REPO = _HERE.parent
_NETS_DIR = _HERE / "nets"
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "tools"))

import kicad_common as kc          # noqa: E402
import components as registry      # noqa: E402


# ── deterministic UUIDs (byte-stable output) ─────────────────────────────────

_UUID_NS = _uuid.UUID("0a90f1c0-9060-4b1e-9a3e-b0b0b0b0b0b0")  # fixed POGO namespace


def _make_det_uid():
    n = [0]

    def _uid():
        n[0] += 1
        return str(_uuid.uuid5(_UUID_NS, str(n[0])))
    return _uid


# ── symbol table: sym name -> (lib_id, lib_symbol fn, all-pins fn) ────────────
# all-pins fn returns {pin_number: (x, y)} for EVERY electrical pin of the symbol.

SYM_TABLE = {
    "jack":   ("Device:Audio_Jack_3.5mm_SwitchT", kc.sym_jack,    kc.jack_pins),
    "r":      ("Device:R",                          kc.sym_r,       kc.r_pins),
    "c":      ("Device:C",                          kc.sym_c,       kc.c_pins),
    "bat54s": ("Diode:BAT54S",                      kc.sym_bat54s,  kc.bat54s_pins),
    "opamp2": ("Amplifier_Operational:OPA1612",     kc.sym_opa1612, kc.opamp_dual_all_pins),
}

# Layout grid (mm). Symbols only need to not overlap — nets connect by name.
_COL_DX, _ROW_DY, _NCOLS, _X0, _Y0 = 45.0, 40.0, 3, 40.0, 40.0


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
        if sym not in SYM_TABLE:
            errs.append(f"{ref}: unknown sym '{sym}'")
            continue
        _, _, pins_fn = SYM_TABLE[sym]
        part_pins[ref] = set(pins_fn(0.0, 0.0).keys())

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
        kc.emit(SYM_TABLE[sym][1]())
    kc.emit(")")

    # Place symbols on a grid (declaration order) and record pin coordinates.
    pin_xy: dict[str, tuple[float, float]] = {}
    for i, (ref, spec) in enumerate(parts.items()):
        col, row = i % _NCOLS, i // _NCOLS
        ox, oy = _X0 + col * _COL_DX, _Y0 + row * _ROW_DY
        lib_id, _, pins_fn = SYM_TABLE[spec["sym"]]
        fp = _resolve_footprint(spec.get("part"))
        kc.place_symbol(lib_id, ref, spec.get("value", ""), ox, oy, footprint=fp)
        for pin, (px, py) in pins_fn(ox, oy).items():
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


def out_path_for(block: dict) -> Path:
    return _HERE / f"pogo-{block['block']}.kicad_sch"


def _block_files() -> list[Path]:
    return sorted(_NETS_DIR.glob("*.nets.yaml"))


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
    for f in files:
        block = load_block(f)
        errs = validate_block(block)
        if errs:
            print(f"SCHEMATIC CHECK — FAIL ({f.name}):")
            for e in errs:
                print(f"  - {e}")
            rc = 1
            continue

        text = build(block)
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
    return rc


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
