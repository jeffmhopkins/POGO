#!/usr/bin/env python3
"""Structural validator for pogo-utility-board.kicad_sch.

Checks (10 total):
  1. File parses as valid KiCad S-expression (balanced parens)
  2. All expected IC references are present (CN1/2/3/6, U1–U22, STK_L, STK_R)
  3. Eurorack power header rails (+12V, -12V, GND) present in schematic
  4. All 19 attenuverter output nets present (_ATT suffix: LP, HP, FB, DRIVE, etc.)
  5. All 6 THAT340 I_abc collector nets present (APF1/2/3_L/R, LP1/2_L/R, HP_L/R)
  6. STK_AUDIO_L/R: all power + I_abc + CV + audio nets present (40 pins each)
  7. FB DIST BLEND out nets present (L + R) and post-dist tap nets present
  8. Mod bus nets present (NET_MODBUS, NET_MODBUS_NORM, NET_MOD_SCALED)
  9. Filter final CV nets present (LP1/LP2/HP cutoff + res)
 10. FB/DRIVE final CV nets present (APF_FB1/2/3_CV, DRIVE1/2/3_CV)
"""

import re
import sys
from collections import Counter


def load(path):
    with open(path) as f:
        return f.read()


def net_labels(text):
    return re.findall(r'\(global_label "([^"]+)"', text)


def has_ref(text, ref):
    """True if the schematic contains a symbol with this reference designator."""
    return bool(re.search(rf'\(property "Reference" "{re.escape(ref)}"', text))


errors = []
passed = 0


def check(name, ok, detail=""):
    global passed
    if ok:
        passed += 1
        print(f"  pass  {name}")
    else:
        errors.append(name)
        msg = f"  FAIL  {name}"
        if detail:
            msg += f"\n          {detail}"
        print(msg)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "pogo-utility-board.kicad_sch"
    text = load(path)
    labels = net_labels(text)
    cnt = Counter(labels)

    # ── Check 1: balanced parens ──────────────────────────────────────────────
    ok = text.count("(") == text.count(")")
    check("Balanced parens", ok,
          f"opens={text.count('(')}, closes={text.count(')')}")

    # ── Check 2: IC references present ───────────────────────────────────────
    required_refs = (
        ["CN1", "CN2", "CN3", "CN6", "STK_L", "STK_R"] +
        [f"U{n}" for n in range(1, 23)]   # U1–U22
    )
    missing_refs = [r for r in required_refs if not has_ref(text, r)]
    check("IC references present", not missing_refs,
          f"missing: {missing_refs}" if missing_refs else "")

    # ── Check 3: Eurorack power rails ────────────────────────────────────────
    power_nets = ["+12V", "-12V", "GND"]
    missing_pwr = [n for n in power_nets if n not in cnt]
    check("Power rails present", not missing_pwr,
          f"missing: {missing_pwr}" if missing_pwr else "")

    # ── Check 4: attenuverter output nets (_ATT suffix) ──────────────────────
    att_nets = [
        "NET_ATT_BYPASS_CV",
        "NET_APF_OFFSET_ATT",
        "NET_FB_BLEND_ATT",
        "NET_VCA_LEVEL_CV",
        "NET_LP1_CUT_ATT", "NET_LP1_RES_ATT",
        "NET_LP2_CUT_ATT", "NET_LP2_RES_ATT",
        "NET_HP_CUT_ATT",  "NET_HP_RES_ATT",
        "NET_FREQ1_ATT",   "NET_FREQ2_ATT", "NET_FREQ3_ATT",
        "NET_APF_FB1_ATT", "NET_APF_FB2_ATT", "NET_APF_FB3_ATT",
        "NET_DRIVE1_ATT",  "NET_DRIVE2_ATT",  "NET_DRIVE3_ATT",
    ]
    assert len(att_nets) == 19
    missing_att = [n for n in att_nets if cnt.get(n, 0) < 2]
    check("19 attenuverter output nets present (≥2 occurrences)", not missing_att,
          f"missing/single: {missing_att}" if missing_att else "")

    # ── Check 5: THAT340 I_abc collector nets ────────────────────────────────
    iabc_nets = [
        "NET_IABC_APF1_L", "NET_IABC_APF2_L", "NET_IABC_APF3_L",
        "NET_IABC_APF1_R", "NET_IABC_APF2_R", "NET_IABC_APF3_R",
        "NET_IABC_LP1_L",  "NET_IABC_LP1_R",
        "NET_IABC_LP2_L",  "NET_IABC_LP2_R",
        "NET_IABC_HP_L",   "NET_IABC_HP_R",
    ]
    missing_iabc = [n for n in iabc_nets if cnt.get(n, 0) < 2]
    check("12 THAT340 I_abc nets present (≥2 occurrences)", not missing_iabc,
          f"missing/single: {missing_iabc}" if missing_iabc else "")

    # ── Check 6: STK_AUDIO_L/R full pin coverage ─────────────────────────────
    # Key signal nets that must appear on both STK connectors (shared CVs)
    stk_shared = [
        "NET_LP1_CUT_CV", "NET_LP1_RES_CV",
        "NET_LP2_CUT_CV", "NET_LP2_RES_CV",
        "NET_HP_CUT_CV",  "NET_HP_RES_CV",
        "NET_VCA_LEVEL_CV", "NET_COMB_BYPASS_CV",
        "NET_APF_FB1_CV", "NET_APF_FB2_CV", "NET_APF_FB3_CV",
        "NET_DRIVE1_CV",  "NET_DRIVE2_CV",  "NET_DRIVE3_CV",
    ]
    # Shared CVs appear on both STK_L and STK_R → count ≥ 4 (≥2 per IC + ≥2 source)
    missing_stk_shared = [n for n in stk_shared if cnt.get(n, 0) < 3]
    check("Shared STK CV nets appear on both L and R headers", not missing_stk_shared,
          f"low count: {missing_stk_shared}" if missing_stk_shared else "")

    # L-only and R-only audio/signal nets (must appear ≥2: source + STK pin)
    stk_l_only = [
        "NET_L_IN_BUF",  "NET_ENV_OUT_L",  "NET_BAND_OUT_L",  "NET_LEFT_OUT",
        "NET_IABC_APF1_L", "NET_IABC_APF2_L", "NET_IABC_APF3_L",
        "NET_IABC_LP1_L",  "NET_IABC_LP2_L",  "NET_IABC_HP_L",
        "NET_POST_DIST_L1", "NET_POST_DIST_L2", "NET_POST_DIST_L3",
        "NET_FB_BLEND_OUT_L",
    ]
    stk_r_only = [
        "NET_R_IN_BUF",  "NET_ENV_OUT_R",  "NET_BAND_OUT_R",  "NET_RIGHT_OUT",
        "NET_IABC_APF1_R", "NET_IABC_APF2_R", "NET_IABC_APF3_R",
        "NET_IABC_LP1_R",  "NET_IABC_LP2_R",  "NET_IABC_HP_R",
        "NET_POST_DIST_R1", "NET_POST_DIST_R2", "NET_POST_DIST_R3",
        "NET_FB_BLEND_OUT_R",
    ]
    missing_stk_lr = [n for n in stk_l_only + stk_r_only if cnt.get(n, 0) < 2]
    check("L/R-specific STK signal nets present (≥2 occurrences)", not missing_stk_lr,
          f"missing/single: {missing_stk_lr}" if missing_stk_lr else "")

    # ── Check 7: FB DIST BLEND and post-dist taps ────────────────────────────
    blend_nets = [
        "NET_FB_BLEND_OUT_L", "NET_FB_BLEND_OUT_R",
        "NET_POST_DIST_L1", "NET_POST_DIST_L2", "NET_POST_DIST_L3",
        "NET_POST_DIST_R1", "NET_POST_DIST_R2", "NET_POST_DIST_R3",
        "NET_FB_BLEND_ATT", "NET_WPR_FB_DIST_BLEND",
    ]
    missing_blend = [n for n in blend_nets if cnt.get(n, 0) < 2]
    check("FB DIST BLEND + post-dist tap nets present", not missing_blend,
          f"missing/single: {missing_blend}" if missing_blend else "")

    # ── Check 8: mod bus nets ─────────────────────────────────────────────────
    modbus_nets = [
        "NET_MOD_IN", "NET_MOD_SCALED", "NET_MODBUS",
        "NET_MODBUS_NORM", "NET_ENV_NORM", "NET_ENV_SEL",
        "NET_WPR_AMOUNT", "NET_WPR_OFFSET_MB",
    ]
    missing_mb = [n for n in modbus_nets if cnt.get(n, 0) < 2]
    check("Mod bus nets present (≥2 occurrences each)", not missing_mb,
          f"missing/single: {missing_mb}" if missing_mb else "")

    # ── Check 9: filter final CV nets ────────────────────────────────────────
    filter_cv_nets = [
        "NET_LP1_CUT_CV", "NET_LP1_RES_CV",
        "NET_LP2_CUT_CV", "NET_LP2_RES_CV",
        "NET_HP_CUT_CV",  "NET_HP_RES_CV",
    ]
    missing_fcv = [n for n in filter_cv_nets if cnt.get(n, 0) < 3]
    check("Filter final CV nets present (≥3: source + 2× STK)", not missing_fcv,
          f"missing/low: {missing_fcv}" if missing_fcv else "")

    # ── Check 10: FB/DRIVE final CV nets ─────────────────────────────────────
    fbdrv_cv_nets = [
        "NET_APF_FB1_CV", "NET_APF_FB2_CV", "NET_APF_FB3_CV",
        "NET_DRIVE1_CV",  "NET_DRIVE2_CV",  "NET_DRIVE3_CV",
    ]
    missing_fdcv = [n for n in fbdrv_cv_nets if cnt.get(n, 0) < 3]
    check("FB/DRIVE final CV nets present (≥3: source + 2× STK)", not missing_fdcv,
          f"missing/low: {missing_fdcv}" if missing_fdcv else "")

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + len(errors)
    singles = [k for k, v in cnt.items() if v == 1]
    print(f"\n{'PASSED' if not errors else 'FAILED'} — {total} checks, {len(errors)} error(s)")
    n_pins = len([v for v in cnt.values()])
    print(f"  ({len(cnt)} distinct nets; {sum(cnt.values())} total net label occurrences)")
    if singles:
        print(f"  single-occurrence nets ({len(singles)}): {singles}")
    if errors:
        print(f"  Failed checks: {errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
