#!/usr/bin/env python3
"""test_parity.py — assert the JS editor DRC == the Python CLI DRC.

The web editor's live collision check (tools/editor/drc.js → PogoDRC.pcbOverlaps,
embedded in docs/panel-editor.html) is a hand-written twin of
panel_rules._check_pcb_overlaps. This gate feeds BOTH the same components + the same
footprint shapes and asserts they report the identical set of colliding id-pairs and
penetration depths — on a battery of synthetic placements (every type × rotation ×
separation, plus a cluster) AND on the real panel. Any algorithm drift fails CI.

Requires Node. Run: python3 tools/test_parity.py    (exit 0 = parity holds)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import panel_kicad as pk          # noqa: E402
import build_panel                # noqa: E402
from panel_rules import DesignRules  # noqa: E402

_DRC_CLI = os.path.join(_HERE, "editor", "drc_cli.js")
_RULES = DesignRules()
_SHAPES = {t: [list(r) for r in pk.footprint_shapes(t)] for t in pk._FOOTPRINT_MAP}

_OVL = re.compile(r"\[PCB OVERLAP\] '([^']+)'.*?'([^']+)'.*?penetration ([\d.]+)mm")


def _c(t, cx, cy, cid, rot=0):
    return {"type": t, "cx": float(cx), "cy": float(cy), "id": cid, "rotate": int(rot)}


def _py(comps):
    """Python DRC → {frozenset{a,b}: penetration(2dp)}."""
    out = {}
    for line in _RULES._check_pcb_overlaps(comps):
        m = _OVL.search(line)
        assert m, f"unparseable violation: {line}"
        out[frozenset((m[1], m[2]))] = round(float(m[3]), 2)
    return out


def _js(comps):
    """JS PogoDRC.pcbOverlaps (via Node) → {frozenset{a,b}: penetration(2dp)}."""
    payload = json.dumps({"comps": comps, "shapes": _SHAPES})
    res = subprocess.run(["node", _DRC_CLI], input=payload, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"node failed: {res.stderr}")
    return {frozenset((o["a"], o["b"])): round(o["pen"], 2) for o in json.loads(res.stdout)}


def _scenarios():
    s = []
    for t in ("trimpot", "jack_input", "knob", "toggle_dw3", "led", "slider_V45"):
        for rot in (0, 90, 180, 270):
            for sep in (4, 6, 8, 10, 11.43, 12.7, 14, 18, 30):
                s.append([_c(t, 50, 50, "a", rot), _c(t, 50 + sep, 50, "b", rot)])
                s.append([_c(t, 50, 50, "a", rot), _c(t, 50, 50 + sep, "b", rot)])
    # mixed type + asymmetric rotation
    for sep in (8, 11, 14):
        s.append([_c("trimpot", 50, 50, "a", 90), _c("jack_input", 50, 50 + sep, "b", 180)])
    # cluster (3 pots in a row)
    s.append([_c("trimpot", 50, 50, "p0"), _c("trimpot", 61.43, 50, "p1"),
              _c("trimpot", 72.86, 50, "p2")])
    # the REAL panel (algorithm on production data)
    data = build_panel.load_data() if hasattr(build_panel, "load_data") else None
    if data is not None:
        comps = build_panel.resolve_components(data, _RULES)
        flat = [{"type": c.get("type", ""), "cx": float(c.get("cx", 0)),
                 "cy": float(c.get("cy", 0)), "rotate": int(c.get("rotate", 0)),
                 "id": c.get("id") or c.get("cpp_id") or c.get("cpp_param") or f"_{i}"}
                for i, c in enumerate(comps)]
        s.append(flat)
    return s


def main() -> int:
    if subprocess.run(["node", "--version"], capture_output=True).returncode != 0:
        print("PARITY CHECK — SKIP (node not available)")
        return 0
    mismatches = 0
    scs = _scenarios()
    for n, comps in enumerate(scs):
        py, js = _py(comps), _js(comps)
        if py != js:
            mismatches += 1
            print(f"  scenario {n}: PY≠JS\n    py={dict(sorted((tuple(sorted(k)),v) for k,v in py.items()))}"
                  f"\n    js={dict(sorted((tuple(sorted(k)),v) for k,v in js.items()))}")
    if mismatches:
        print(f"PARITY CHECK — FAIL ({mismatches}/{len(scs)} scenarios diverge)")
        return 1
    print(f"PARITY CHECK — OK (Python == JS on {len(scs)} scenarios incl. the real panel)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
