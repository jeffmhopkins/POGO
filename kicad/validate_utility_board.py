#!/usr/bin/env python3
"""Coordinate-based pin validator for pogo-utility-board.kicad_sch.

Approach:
  1. Run generate_utility_board.build_schematic() with monkey-patched
     connect_pin / place_symbol to capture every expected
     (ref, net, x, y) pin assignment from the generator itself.
  2. Parse the actual schematic's global_label entries for (net, x, y).
  3. For each expected entry verify the schematic has the same net at
     the same coordinate — PASS or FAIL.

This catches pin swaps, wrong nets, missing labels, and connector pinout
mismatches — things that occurrence-counting cannot detect.

Structural checks (11 total):
  1. Balanced parentheses
  2. All IC references present (CN1/2/3/6, U1–U22, STK_L, STK_R)
  3. Power rails present (+12V, -12V, GND)
  4. Total expected pin assignments match schematic label count (sanity)
  5–11. Per-component: CN6, CN1, CN2, CN3, STK_L, STK_R, all ICs — all pass
        (each component's pins reported; overall fail if any mismatch)
"""

import re
import sys
import os
from collections import defaultdict, Counter


# ---------------------------------------------------------------------------
# Schematic parsing
# ---------------------------------------------------------------------------

def load(path):
    with open(path) as f:
        return f.read()


def has_ref(text, ref):
    return bool(re.search(rf'\(property "Reference" "{re.escape(ref)}"', text))


def parse_actual_labels(text):
    """Return {(x, y): set_of_nets} from global_label entries in the schematic."""
    actual = defaultdict(set)
    pat = re.compile(
        r'\(global_label "([^"]+)"\n\s+\(shape \w+\)\n\s+\(at ([0-9.-]+) ([0-9.-]+)')
    for m in pat.finditer(text):
        net = m.group(1)
        x = round(float(m.group(2)), 3)
        y = round(float(m.group(3)), 3)
        actual[(x, y)].add(net)
    return actual


# ---------------------------------------------------------------------------
# Generator capture — monkey-patch connect_pin / place_symbol
# ---------------------------------------------------------------------------

def capture_expected():
    """Run build_schematic() with patched functions.

    Returns list of (ref, value, net, x, y) tuples in the order the
    generator emits them.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import kicad_common
    import generate_utility_board as gen

    kicad_common.reset()

    expected = []
    context = ["(global)", "(unknown)"]  # [current_ref, current_value]

    def tracking_place(lib_id, ref, value, ox, oy, angle=0, mirror="", unit=1):
        context[0] = ref
        context[1] = value

    def tracking_connect(net, px, py, shape="passive"):
        expected.append((context[0], context[1], net,
                         round(px, 3), round(py, 3)))

    # Save originals and patch both namespaces (gen imports by-name from kicad_common
    # so each module resolves names from its own namespace — must patch both).
    orig_kc_place   = kicad_common.place_symbol
    orig_kc_connect = kicad_common.connect_pin
    orig_gen_place  = gen.place_symbol
    orig_gen_connect = gen.connect_pin

    kicad_common.place_symbol  = tracking_place
    kicad_common.connect_pin   = tracking_connect
    gen.place_symbol           = tracking_place
    gen.connect_pin            = tracking_connect

    try:
        gen.build_schematic()
    finally:
        kicad_common.place_symbol  = orig_kc_place
        kicad_common.connect_pin   = orig_kc_connect
        gen.place_symbol           = orig_gen_place
        gen.connect_pin            = orig_gen_connect
        kicad_common.reset()  # discard accumulated output

    return expected


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "pogo-utility-board.kicad_sch"
    text = load(path)

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

    # ── Check 3: power rails ──────────────────────────────────────────────────
    labels_flat = re.findall(r'\(global_label "([^"]+)"', text)
    cnt = Counter(labels_flat)
    power_nets = ["+12V", "-12V", "GND"]
    missing_pwr = [n for n in power_nets if n not in cnt]
    check("Power rails present", not missing_pwr,
          f"missing: {missing_pwr}" if missing_pwr else "")

    # ── Capture expected from generator ──────────────────────────────────────
    print("\n  Capturing expected pin assignments from generator...")
    expected = capture_expected()
    actual = parse_actual_labels(text)

    # ── Check 4: total label count sanity ────────────────────────────────────
    # Each expected entry should correspond to one global_label in the schematic.
    # The schematic may have more labels (power_sym creates power symbols, not labels;
    # extra labels from manual connect_pin calls outside place helpers are included).
    n_expected = len(expected)
    n_actual_total = sum(len(v) for v in actual.values())
    # Allow schematic to have ≥ expected (extra labels from power rail connects are OK)
    ok4 = n_actual_total >= n_expected
    check(f"Label count sanity (≥{n_expected} global_labels)", ok4,
          f"expected≥{n_expected}, actual={n_actual_total}")

    # ── Checks 5–11: per-component coordinate verification ───────────────────
    # Group expected by ref, preserving order of first appearance.
    by_ref = defaultdict(list)
    ref_value = {}
    ref_order = []
    seen_refs = set()
    for ref, value, net, x, y in expected:
        by_ref[ref].append((net, x, y))
        if ref not in seen_refs:
            ref_order.append(ref)
            ref_value[ref] = value
            seen_refs.add(ref)

    print()
    total_pin_pass = total_pin_fail = 0
    all_pin_failures = []

    # Connector group: CN6, CN1, CN2, CN3
    # STK group: STK_L, STK_R
    # IC group: everything else (U1–U22)
    connector_refs = ["CN6", "CN1", "CN2", "CN3"]
    stk_refs = ["STK_L", "STK_R"]

    for ref in ref_order:
        pins = by_ref[ref]
        value = ref_value[ref]
        pin_pass = pin_fail = 0
        fail_lines = []

        for net, x, y in pins:
            nets_at = actual.get((x, y), set())
            if net in nets_at:
                pin_pass += 1
                total_pin_pass += 1
            else:
                pin_fail += 1
                total_pin_fail += 1
                got = ", ".join(sorted(nets_at)) if nets_at else "(nothing)"
                fail_lines.append(
                    f"      FAIL ({x:.3f}, {y:.3f}): expected={net!r:35s} got={got!r}")
                all_pin_failures.append((ref, net, x, y, got))

        status = "ALL PASS" if pin_fail == 0 else f"{pin_fail} FAIL"
        print(f"  {ref:8s} ({value:20s}) {len(pins):3d} pins: {pin_pass} pass, {status}")
        for line in fail_lines:
            print(line)

    # Roll up per-component results into structural checks
    connector_fail = sum(
        1 for ref, net, x, y, got in all_pin_failures if ref in connector_refs)
    stk_fail = sum(
        1 for ref, net, x, y, got in all_pin_failures if ref in stk_refs)
    ic_fail = sum(
        1 for ref, net, x, y, got in all_pin_failures
        if ref not in connector_refs and ref not in stk_refs)

    connector_total = sum(len(by_ref[r]) for r in connector_refs if r in by_ref)
    stk_total = sum(len(by_ref[r]) for r in stk_refs if r in by_ref)
    ic_total = sum(len(by_ref[r]) for r in ref_order
                   if r not in connector_refs and r not in stk_refs)

    print()
    check(f"Connector pinouts correct ({connector_total} pins: CN6/CN1/CN2/CN3)",
          connector_fail == 0,
          f"{connector_fail} mismatched pin(s)" if connector_fail else "")

    check(f"STK header pinouts correct ({stk_total} pins: STK_L/STK_R)",
          stk_fail == 0,
          f"{stk_fail} mismatched pin(s)" if stk_fail else "")

    check(f"IC signal pins correct ({ic_total} pins: U1–U22 op-amps + THAT340s)",
          ic_fail == 0,
          f"{ic_fail} mismatched pin(s)" if ic_fail else "")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_checks = passed + len(errors)
    singles = [k for k, v in cnt.items() if v == 1]
    print(f"\n{'PASSED' if not errors else 'FAILED'} — {total_checks} checks, "
          f"{len(errors)} error(s)")
    print(f"  Coordinate-verified: {total_pin_pass + total_pin_fail} pin assignments "
          f"({total_pin_pass} pass, {total_pin_fail} fail)")
    print(f"  ({len(cnt)} distinct nets; {sum(cnt.values())} total net label occurrences)")

    if singles:
        print(f"  Single-occurrence nets ({len(singles)}): {singles}")

    if errors:
        print(f"  Failed checks: {errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
