#!/usr/bin/env python3
"""build_spice.py — SPICE behavioral unit-test runner for POGO blocks.

Per-block `sim/` folders hold ngspice decks (`*.cir`) + assertion files
(`*.expect.yaml`). Each deck's `.control` block emits machine-readable
measurements via ngspice `print <name>` (-> stdout line "<name> = <value>").
The `.expect.yaml` maps each measurement name to an expected value + tolerance,
or a boolean/range assertion. This runner ties them together and is the basis
for a future 7th CI `--check` gate (see changes/0021-spice-block-unit-tests.md,
tools/SPICE-PLAN.md).

Discovery: globs specs/**/sim/*.cir; a deck is *checked* only if it has a
sibling <deck>.expect.yaml. Decks without an expect file are listed but skipped
(scratch/exploratory decks are fine).

ngspice absence: `--check` exits 0 (xfail/skip) with a clear notice, so
non-SPICE dev boxes and CI legs without ngspice still pass — matching the
build-graph convention that gates degrade gracefully.

Assertion schema (specs/<block>/sim/<deck>.expect.yaml):

    deck: expo_voct.cir
    description: ...
    plugin_ref: "plugin/src/dsp/LPFilter.hpp ..."
    measurements:
      - name: base_mv_per_volt_mid     # must match a `print <name>` in the deck
        expect: 17.92
        tol_pct: 12                    # |measured-expect| <= tol_pct% of |expect|
      - name: trim_lo
        expect: 19.65
        tol_abs: 0.5                   # absolute tolerance (units of the measurement)
      - name: depth_ok
        expect: true                   # boolean: deck prints 1 (true) / 0 (false)

Usage:
    python3 tools/build_spice.py --list           # enumerate decks + coverage
    python3 tools/build_spice.py --run BLOCK       # run one block's decks, verbose
    python3 tools/build_spice.py --check           # CI gate: all assertions pass
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_GLOB = os.path.join(REPO, "specs", "**", "sim", "*.cir")
# A flat scratch dir (specs/sim/) predates the per-block layout; include it too.
SCRATCH = os.path.join(REPO, "specs", "sim", "*.cir")

# ngspice "name = value" lines (value may be sci-notation, may have a 2nd complex part)
_PRINT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*([-+0-9.eE]+)")


def have_ngspice() -> bool:
    return shutil.which("ngspice") is not None


def discover():
    """Return list of (cir_path, expect_path_or_None), de-duplicated, sorted."""
    seen = {}
    for pat in (SIM_GLOB, SCRATCH):
        for cir in glob.glob(pat, recursive=True):
            cir = os.path.abspath(cir)
            exp = os.path.splitext(cir)[0] + ".expect.yaml"
            seen[cir] = exp if os.path.exists(exp) else None
    return sorted(seen.items())


def block_of(cir_path: str) -> str:
    """Derive the owning block from .../specs/<block>/sim/<deck>.cir."""
    parts = cir_path.split(os.sep)
    try:
        i = parts.index("sim")
        return parts[i - 1]
    except (ValueError, IndexError):
        return "(scratch)"


def run_deck(cir_path: str) -> dict:
    """Run a deck in batch mode; return {measurement_name: float} from print lines."""
    proc = subprocess.run(
        ["ngspice", "-b", cir_path],
        capture_output=True, text=True, timeout=120,
    )
    out = {}
    for line in proc.stdout.splitlines():
        m = _PRINT_RE.match(line)
        if m:
            try:
                # ngspice lowercases vector names in output; key on lowercase so the
                # .expect.yaml can use the deck's mixed-case measurement names.
                out[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
    return out


def check_measurement(spec: dict, measured: dict) -> tuple[bool, str]:
    name = spec["name"]
    key = name.lower()
    if key not in measured:
        return False, f"{name}: NOT EMITTED by deck (expected `print {name}`)"
    val = measured[key]
    exp = spec["expect"]
    # boolean assertion (deck prints 1.0 / 0.0)
    if isinstance(exp, bool):
        ok = (val >= 0.5) == exp
        return ok, f"{name}: {val:g} -> {'true' if val>=0.5 else 'false'} (want {exp})"
    exp = float(exp)
    if "tol_pct" in spec:
        tol = abs(exp) * float(spec["tol_pct"]) / 100.0
    elif "tol_abs" in spec:
        tol = float(spec["tol_abs"])
    else:
        tol = abs(exp) * 0.05  # default ±5%
    delta = abs(val - exp)
    ok = delta <= tol
    return ok, f"{name}: {val:.4g} (expect {exp:.4g} ±{tol:.3g}, Δ={delta:.3g})"


def evaluate(cir_path: str, expect_path: str) -> tuple[bool, list[str]]:
    spec = yaml.safe_load(open(expect_path))
    measured = run_deck(cir_path)
    lines, all_ok = [], True
    for m in spec.get("measurements", []):
        ok, msg = check_measurement(m, measured)
        all_ok = all_ok and ok
        lines.append(("  ✓ " if ok else "  ✗ ") + msg)
    return all_ok, lines


def cmd_list():
    decks = discover()
    print(f"SPICE decks ({len(decks)} found):")
    by_block = {}
    for cir, exp in decks:
        by_block.setdefault(block_of(cir), []).append((cir, exp))
    covered = scratch = 0
    for block in sorted(by_block):
        print(f"\n  {block}:")
        for cir, exp in by_block[block]:
            tag = "checked" if exp else "scratch (no .expect.yaml)"
            if exp:
                covered += 1
            else:
                scratch += 1
            print(f"    {os.path.basename(cir):28s} {tag}")
    print(f"\n{covered} checked, {scratch} scratch.")
    return 0


def cmd_run(block: str):
    if not have_ngspice():
        print("ngspice not installed — cannot run.")
        return 2
    decks = [(c, e) for c, e in discover() if block_of(c) == block]
    if not decks:
        print(f"no decks for block '{block}'. Try --list.")
        return 1
    rc = 0
    for cir, exp in decks:
        print(f"\n=== {os.path.basename(cir)} ({block}) ===")
        if not exp:
            meas = run_deck(cir)
            print("  (scratch deck, no assertions) measured:")
            for k, v in meas.items():
                print(f"    {k} = {v:g}")
            continue
        ok, lines = evaluate(cir, exp)
        print("\n".join(lines))
        print("  -> PASS" if ok else "  -> FAIL")
        rc = rc or (0 if ok else 1)
    return rc


def cmd_check():
    decks = [(c, e) for c, e in discover() if e]  # only decks with assertions
    if not have_ngspice():
        print(f"SPICE CHECK — SKIP (ngspice not installed; {len(decks)} checked decks deferred). "
              "Install ngspice to run the behavioral gate.")
        return 0
    if not decks:
        print("SPICE CHECK — OK (no .expect.yaml assertion files yet; nothing to verify).")
        return 0
    failures = []
    for cir, exp in decks:
        ok, lines = evaluate(cir, exp)
        if not ok:
            failures.append((cir, lines))
    if failures:
        print(f"SPICE CHECK — FAIL ({len(failures)} of {len(decks)} decks):")
        for cir, lines in failures:
            print(f"  {block_of(cir)}/{os.path.basename(cir)}:")
            print("\n".join("  " + l for l in lines if l.strip().startswith("✗")))
        return 1
    print(f"SPICE CHECK — OK ({len(decks)} decks, all assertions pass).")
    return 0


def main():
    ap = argparse.ArgumentParser(description="POGO SPICE behavioral unit-test runner")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="enumerate decks + coverage")
    g.add_argument("--run", metavar="BLOCK", help="run one block's decks, verbose")
    g.add_argument("--check", action="store_true", help="CI gate: all assertions pass")
    args = ap.parse_args()
    if args.list:
        sys.exit(cmd_list())
    if args.run:
        sys.exit(cmd_run(args.run))
    if args.check:
        sys.exit(cmd_check())


if __name__ == "__main__":
    main()
