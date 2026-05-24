#!/usr/bin/env python3
"""
POGO control board schematic validator.

Uses kiutils to parse the generated .kicad_sch and check:
  - Component counts match spec (J×28, RV×43, SW×4, CN×3)
  - No duplicate reference designators
  - No single-occurrence (floating) nets, except known intentional spares
  - All expected audio/CV signal nets are present
  - All expected connector pin nets are present
  - Power nets (+12V, -12V, GND) are used

Install dependency once:  pip3 install kiutils

Run from the kicad/ directory:
    python3 validate_schematic.py [schematic.kicad_sch]
"""

import sys
import re
from collections import Counter

try:
    from kiutils.schematic import Schematic
except ImportError:
    print("ERROR: kiutils not installed. Run: pip3 install kiutils")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Expected values — update these if the schematic changes
# ---------------------------------------------------------------------------

EXPECTED_COUNTS = {"J": 28, "RV": 43, "SW": 4, "CN": 3}

KNOWN_SPARE_NETS = {"SPARE_CN2_28", "SPARE_CN2_40", "SPARE_CN3_24"}

# Every net that must appear at least twice (non-exhaustive; catch regressions)
REQUIRED_NETS = [
    # Audio I/O
    "NET_L_IN", "NET_R_IN",
    "NET_ENV_OUT_L", "NET_ENV_OUT_R",
    "NET_BAND_OUT_L", "NET_BAND_OUT_R",
    "NET_LEFT_OUT", "NET_RIGHT_OUT",
    # Mod bus
    "NET_MOD_IN", "NET_ENV_NORM", "NET_MODBUS_NORM",
    # Pot wipers — main params
    "NET_WPR_ATTACK", "NET_WPR_RELEASE",
    "NET_WPR_AMOUNT", "NET_WPR_OFFSET_MB",
    "NET_WPR_COMB_BYPASS", "NET_WPR_WIDTH",
    "NET_WPR_MASTER_OFFSET", "NET_WPR_FB_DIST_BLEND",
    "NET_WPR_FREQ1", "NET_WPR_FREQ2", "NET_WPR_FREQ3",
    "NET_WPR_FB1", "NET_WPR_FB2", "NET_WPR_FB3",
    "NET_WPR_DRIVE1", "NET_WPR_DRIVE2", "NET_WPR_DRIVE3",
    "NET_WPR_LP1_CUT", "NET_WPR_LP1_RES", "NET_WPR_LP1_SPREAD",
    "NET_WPR_LP2_CUT", "NET_WPR_LP2_RES",
    "NET_WPR_HP_CUT", "NET_WPR_HP_RES",
    # Attenuverter wipers
    "NET_WPR_ATT_BYPASS", "NET_WPR_ATT_OFFSET", "NET_WPR_ATT_BLEND",
    "NET_WPR_ATT_VCA_AMT",
    "NET_WPR_ATT_FREQ1", "NET_WPR_ATT_FREQ2", "NET_WPR_ATT_FREQ3",
    "NET_WPR_ATT_FB1", "NET_WPR_ATT_FB2", "NET_WPR_ATT_FB3",
    "NET_WPR_ATT_DRIVE1", "NET_WPR_ATT_DRIVE2", "NET_WPR_ATT_DRIVE3",
    "NET_WPR_ATT_LP1_CUT", "NET_WPR_ATT_LP1_RES",
    "NET_WPR_ATT_LP2_CUT", "NET_WPR_ATT_LP2_RES",
    "NET_WPR_ATT_HP_CUT", "NET_WPR_ATT_HP_RES",
    # CV override jack tips
    "NET_CV_BYPASS", "NET_CV_OFFSET", "NET_CV_BLEND", "NET_CV_VCA_AMT",
    "NET_CV_LP1_CUT", "NET_CV_LP1_RES",
    "NET_CV_LP2_CUT", "NET_CV_LP2_RES",
    "NET_CV_HP_CUT", "NET_CV_HP_RES",
    "NET_CV_FREQ1", "NET_CV_FREQ2", "NET_CV_FREQ3",
    "NET_CV_FB1", "NET_CV_FB2", "NET_CV_FB3",
    "NET_CV_DRIVE1", "NET_CV_DRIVE2", "NET_CV_DRIVE3",
    # Switch outputs
    "NET_SW_GAIN_COM",
    "NET_SW_MODE_SFT", "NET_SW_MODE_HRD", "NET_SW_MODE_WFD",
    "NET_SW_MODSRC_L", "NET_SW_MODSRC_MAX", "NET_SW_MODSRC_AVG",
    "NET_SW_POL_POS", "NET_SW_POL_OFF", "NET_SW_POL_NEG",
    # Power rails
    "+12V", "-12V", "GND",
]


# ---------------------------------------------------------------------------

def ref_prefix(ref):
    return re.match(r"[A-Za-z]+", ref).group(0)


def validate(path):
    print(f"Validating: {path}\n")
    sch = Schematic().from_file(path)
    errors = []
    warnings = []

    # ------------------------------------------------------------------
    # 1. Component counts
    # ------------------------------------------------------------------
    refs = [
        next(p.value for p in sym.properties if p.key == "Reference")
        for sym in sch.schematicSymbols
        if not next(p.value for p in sym.properties if p.key == "Reference").startswith("#")
    ]
    # Deduplicate multi-unit ICs (same ref appears once per unit)
    unique_refs = sorted(set(refs))
    counts = Counter(ref_prefix(r) for r in unique_refs)

    print("── Component counts ──────────────────────────────────")
    all_counts_ok = True
    for prefix, expected in EXPECTED_COUNTS.items():
        actual = counts.get(prefix, 0)
        status = "✓" if actual == expected else "✗"
        print(f"  {status}  {prefix}: {actual}  (expected {expected})")
        if actual != expected:
            errors.append(f"{prefix} count {actual} ≠ expected {expected}")
            all_counts_ok = False
    if all_counts_ok:
        print(f"  All counts correct. Total unique refs: {len(unique_refs)}")

    # ------------------------------------------------------------------
    # 2. Duplicate reference designators
    # ------------------------------------------------------------------
    print("\n── Duplicate references ──────────────────────────────")
    dup_refs = [r for r, c in Counter(refs).items() if c > 1 and not r.startswith("#")]
    # Multi-unit ICs appear multiple times — ignore those whose base ref appears
    # in unique_refs (they're legitimate). Only flag true duplicates where two
    # distinct symbols claim the same ref.
    true_dups = []
    seen = {}
    for sym in sch.schematicSymbols:
        ref = next(p.value for p in sym.properties if p.key == "Reference")
        if ref.startswith("#"):
            continue
        lib_id = sym.libId
        if ref in seen:
            if seen[ref] != lib_id:
                true_dups.append(f"{ref} (libs: {seen[ref]} vs {lib_id})")
        else:
            seen[ref] = lib_id
    if true_dups:
        for d in true_dups:
            print(f"  ✗  Duplicate: {d}")
            errors.append(f"Duplicate ref: {d}")
    else:
        print("  ✓  No duplicate references")

    # ------------------------------------------------------------------
    # 3. Floating (single-occurrence) nets
    # ------------------------------------------------------------------
    print("\n── Floating nets ─────────────────────────────────────")
    net_counts = Counter(gl.text for gl in sch.globalLabels)
    singles = {n for n, c in net_counts.items() if c == 1}
    unexpected_singles = singles - KNOWN_SPARE_NETS
    expected_spares_present = KNOWN_SPARE_NETS & singles
    expected_spares_missing = KNOWN_SPARE_NETS - singles

    if unexpected_singles:
        for n in sorted(unexpected_singles):
            print(f"  ✗  Floating: {n}  (count=1, unexpected)")
            errors.append(f"Floating net: {n}")
    else:
        print("  ✓  No unexpected floating nets")

    for n in sorted(expected_spares_present):
        print(f"  ·  Spare (intentional): {n}")
    for n in sorted(expected_spares_missing):
        print(f"  ✗  Expected spare missing: {n}")
        errors.append(f"Expected spare net missing: {n}")

    # ------------------------------------------------------------------
    # 4. Required nets present
    # ------------------------------------------------------------------
    print("\n── Required nets present ─────────────────────────────")
    all_nets = set(net_counts.keys())
    missing = [n for n in REQUIRED_NETS if n not in all_nets]
    if missing:
        for n in missing:
            print(f"  ✗  Missing: {n}")
            errors.append(f"Required net missing: {n}")
    else:
        print(f"  ✓  All {len(REQUIRED_NETS)} required nets present")

    # ------------------------------------------------------------------
    # 5. MODBUS_NORM connectivity (must appear 20× — 19 SW lugs + 1 CN2 pin)
    # ------------------------------------------------------------------
    print("\n── NET_MODBUS_NORM connectivity ──────────────────────")
    modbus_count = net_counts.get("NET_MODBUS_NORM", 0)
    if modbus_count == 20:
        print(f"  ✓  NET_MODBUS_NORM appears {modbus_count}× (19 SW lugs + 1 CN2 pin)")
    else:
        msg = f"NET_MODBUS_NORM appears {modbus_count}× (expected 20)"
        print(f"  ✗  {msg}")
        errors.append(msg)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n══ Summary ═══════════════════════════════════════════")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  • {e}")
        return False
    else:
        print("  PASSED — schematic looks valid")
        return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "pogo-control-board.kicad_sch"
    ok = validate(path)
    sys.exit(0 if ok else 1)
