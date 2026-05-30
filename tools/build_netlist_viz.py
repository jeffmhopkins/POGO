"""build_netlist_viz.py — generate the interactive netlist visualizer (docs/netlist.html).

Reads the authored netlist sources and the component registry, and emits ONE
self-contained, dependency-free HTML page: a force-directed netlist viewer where
each part is drawn as its real KiCad footprint (when a footprint resolves) or its
schematic-symbol glyph (passives), with pad-to-pad ratsnest wires along shared nets.

This is a *read-only comprehension artifact* — it authors nothing in specs/ or
components/; the .kicad_sch and pogo-bom.csv remain the truth. See
changes/0018-netlist-visualizer.md.

Reads:
  specs/<block>/<block>.nets.yaml          parts{sym,part,value}, nets, boundary
  components/parts/<slug>/component.yaml    footprint{lib,name} + symbol (via components.py)
  components/symbols/<token>.yaml           glyph graphics + pins   (via symbols.py)
  components/footprints/<lib>.pretty/*.kicad_mod  pad geometry (via footprint_svg.py)

CLI:
  python3 tools/build_netlist_viz.py            write docs/netlist.html
  python3 tools/build_netlist_viz.py --check    validate extraction (CI gate), no write
  python3 tools/build_netlist_viz.py --stats    print coverage stats
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import sys
from pathlib import Path

import yaml

import components
import footprint_svg
import symbols

_REPO = Path(__file__).resolve().parent.parent
_NETS_GLOB = sorted((_REPO / "specs").glob("block-*/block-*.nets.yaml"))
_OUT = _REPO / "docs" / "netlist.html"

POWER_NETS = {"+12V", "-12V", "GND"}

# arc sampling for symbol graphics (rare; keeps the glyph faithful)
_ARC_SEG = 12


# ── geometry extraction ───────────────────────────────────────────────────────

def _footprint_geom(rel_lib: str, rel_name: str) -> dict:
    """Parse a .kicad_mod into a render+wire geom (mm, +x right / +y down)."""
    path = _REPO / "components" / "footprints" / f"{rel_lib}.pretty" / f"{rel_name}.kicad_mod"
    fp = footprint_svg.parse_footprint(path.read_text())
    shapes, pads = [], {}
    for p in fp["pads"]:
        shapes.append({"t": "pad", "x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"],
                       "rot": p["rot"], "shape": p["shape"], "num": p["num"],
                       "drill": p["drill"]})
        # last pad wins for a duplicated number (e.g. multi-pad nets) — fine for wiring
        pads[str(p["num"])] = [round(p["x"], 4), round(p["y"], 4)]
    for ln in fp["lines"]:
        shapes.append({"t": "line", "x1": ln["x1"], "y1": ln["y1"], "x2": ln["x2"], "y2": ln["y2"],
                       "lyr": _layer_tag(ln["layers"])})
    for r in fp["rects"]:
        shapes.append({"t": "rect", "x": min(r["x1"], r["x2"]), "y": min(r["y1"], r["y2"]),
                       "w": abs(r["x2"] - r["x1"]), "h": abs(r["y2"] - r["y1"]),
                       "lyr": _layer_tag(r["layers"])})
    for c in fp["circles"]:
        shapes.append({"t": "circ", "cx": c["cx"], "cy": c["cy"], "r": c["r"],
                       "lyr": _layer_tag(c["layers"])})
    return {"kind": "fp", "shapes": shapes, "pads": pads, "bbox": _bbox(shapes)}


def _layer_tag(layers) -> str:
    for l in layers:
        if "CrtYd" in l:
            return "crtyd"
        if "SilkS" in l:
            return "silk"
    return "fab"


def _symbol_geom(token: str) -> dict:
    """Build a render+wire geom from an authored symbol primitive (Y flipped to +down)."""
    spec = symbols.load().get(token)
    if not spec:
        return None
    shapes = []
    for u in spec["units"]:
        if u["unit"] not in (0, 1):     # passives are single-unit; ignore extra units
            continue
        for g in u["graphics"]:
            shapes.append(_sym_shape(g))
    pads = {num: [round(x, 4), round(-y, 4)]                    # flip Y: KiCad sym +y is up
            for num, (x, y) in symbols.pin_points(spec).items()}
    # pin stubs (short whiskers from body to connection point) for visual identity
    for u in spec["units"]:
        for p in u.get("pins", []):
            cx, cy = p["at"][0], -p["at"][1]
            a = math.radians(p.get("angle", 0))
            ex, ey = cx - p["len"] * math.cos(a), cy + p["len"] * math.sin(a)
            shapes.append({"t": "line", "x1": ex, "y1": ey, "x2": cx, "y2": cy, "lyr": "silk"})
    return {"kind": "sym", "shapes": [s for s in shapes if s], "pads": pads,
            "bbox": _bbox(shapes)}


def _sym_shape(g) -> dict | None:
    k = g["kind"]
    if k == "rectangle":
        x1, y1 = g["start"]; x2, y2 = g["end"]
        return {"t": "rect", "x": min(x1, x2), "y": -max(y1, y2),
                "w": abs(x2 - x1), "h": abs(y2 - y1), "lyr": "fab"}
    if k == "polyline":
        return {"t": "poly", "pts": [[x, -y] for x, y in g["pts"]], "lyr": "fab"}
    if k == "circle":
        return {"t": "circ", "cx": g["center"][0], "cy": -g["center"][1], "r": g["radius"], "lyr": "fab"}
    if k == "arc":
        return {"t": "poly", "pts": _arc_pts(g["start"], g["mid"], g["end"]), "lyr": "fab"}
    return None


def _arc_pts(s, m, e):
    """Sample a 3-point arc into a polyline (Y flipped)."""
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return [[x1, -y1], [x3, -y3]]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1, a3 = math.atan2(y1 - uy, x1 - ux), math.atan2(y3 - uy, x3 - ux)
    if a3 < a1:
        a3 += 2 * math.pi
    return [[ux + r * math.cos(a1 + (a3 - a1) * i / _ARC_SEG),
             -(uy + r * math.sin(a1 + (a3 - a1) * i / _ARC_SEG))] for i in range(_ARC_SEG + 1)]


def _bbox(shapes) -> list:
    xs, ys = [], []
    for s in shapes:
        t = s["t"]
        if t == "pad":
            hw, hh = s["w"] / 2, s["h"] / 2
            xs += [s["x"] - hw, s["x"] + hw]; ys += [s["y"] - hh, s["y"] + hh]
        elif t == "rect":
            xs += [s["x"], s["x"] + s["w"]]; ys += [s["y"], s["y"] + s["h"]]
        elif t == "line":
            xs += [s["x1"], s["x2"]]; ys += [s["y1"], s["y2"]]
        elif t == "circ":
            xs += [s["cx"] - s["r"], s["cx"] + s["r"]]; ys += [s["cy"] - s["r"], s["cy"] + s["r"]]
        elif t == "poly":
            xs += [p[0] for p in s["pts"]]; ys += [p[1] for p in s["pts"]]
    if not xs:
        return [-1.0, -1.0, 1.0, 1.0]
    return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]


# ── netlist extraction ────────────────────────────────────────────────────────

def _geom_id(symtok, rec) -> tuple[str, str]:
    """Return (geom_id, kind) for a part: footprint if the registry resolves one, else symbol."""
    if rec and rec.get("footprint", {}).get("lib") and rec["footprint"].get("name"):
        fp = rec["footprint"]
        return f'fp:{fp["lib"]}/{fp["name"]}', "fp"
    return f"sym:{symtok}", "sym"


def extract() -> dict:
    """Build the full data model + a list of warnings."""
    geom: dict[str, dict] = {}
    parts: list[dict] = []
    nets: list[dict] = []
    blocks: list[dict] = []
    warnings: list[str] = []
    n_fp = n_sym = 0

    for path in _NETS_GLOB:
        doc = yaml.safe_load(path.read_text())
        bid = doc.get("block", path.parent.name)
        board = doc.get("board", "?")
        boundary = list(doc.get("boundary") or [])
        block_refs = []
        # refs are unique only *within* a block (R1 exists in several blocks), so the
        # part identity = block-qualified uid; `label` keeps the short ref for display.
        local_gid: dict[str, str] = {}     # bare ref -> geom_id (this block only)

        for ref, spec in (doc.get("parts") or {}).items():
            symtok = spec.get("sym")
            partstr = spec.get("part")
            rec = components.part_for(partstr) if partstr else None
            gid, kind = _geom_id(symtok, rec)
            if gid not in geom:
                try:
                    if kind == "fp":
                        geom[gid] = _footprint_geom(rec["footprint"]["lib"], rec["footprint"]["name"])
                    else:
                        g = _symbol_geom(symtok)
                        if g is None:
                            warnings.append(f"{bid}/{ref}: no symbol primitive '{symtok}'")
                            geom[gid] = {"kind": "sym", "shapes": [], "pads": {}, "bbox": [-1, -1, 1, 1]}
                        else:
                            geom[gid] = g
                except Exception as e:                       # noqa: BLE001
                    warnings.append(f"{bid}/{ref}: geom '{gid}' failed: {e}")
                    geom[gid] = {"kind": kind, "shapes": [], "pads": {}, "bbox": [-1, -1, 1, 1]}
            if geom[gid]["kind"] == "fp":
                n_fp += 1
            else:
                n_sym += 1
            local_gid[ref] = gid
            uid = f"{bid}::{ref}"
            parts.append({"ref": uid, "label": ref, "block": bid, "board": board,
                          "value": str(spec.get("value", "")), "part": partstr or "",
                          "sym": symtok or "?", "geom": gid})
            block_refs.append(uid)

        for name, pins in (doc.get("nets") or {}).items():
            kind = "power" if name in POWER_NETS else ("boundary" if name in boundary else "signal")
            ep = []
            for tok in pins:
                ref, _, pin = str(tok).rpartition(".")
                if not ref:
                    continue
                g = geom.get(local_gid.get(ref))
                mapped = bool(g and pin in g["pads"])
                if not mapped and g is not None and g["pads"]:
                    warnings.append(f"{bid}/{name}: pin {tok} not a pad/pin of its geom "
                                    f"(centroid fallback)")
                ep.append({"ref": f"{bid}::{ref}", "pin": pin, "m": 1 if mapped else 0})
            nets.append({"name": name, "kind": kind, "block": bid, "pins": ep})

        blocks.append({"id": bid, "board": board, "title": doc.get("title", bid),
                       "boundary": boundary, "refs": block_refs})

    return {
        "meta": {
            "generated": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "parts": len(parts), "footprinted": n_fp, "passive_or_symbol": n_sym,
            "nets": len(nets), "blocks": len(blocks), "geoms": len(geom),
            "warnings": len(warnings),
        },
        "geom": geom, "parts": parts, "nets": nets, "blocks": blocks,
    }, warnings


# ── HTML emit ─────────────────────────────────────────────────────────────────

def render_html(model: dict) -> str:
    data = json.dumps(model, separators=(",", ":"))
    return _TEMPLATE.replace("/*__DATA__*/", data)


def _stats(model, warnings) -> str:
    m = model["meta"]
    lines = [
        f"  parts={m['parts']}  footprinted={m['footprinted']}  "
        f"symbol/passive={m['passive_or_symbol']}",
        f"  nets={m['nets']}  blocks={m['blocks']}  distinct-geoms={m['geoms']}",
        f"  warnings={len(warnings)}",
    ]
    return "\n".join(lines)


def main(argv) -> int:
    model, warnings = extract()
    if "--stats" in argv:
        print("NETLIST-VIZ stats:")
        print(_stats(model, warnings))
        for w in warnings[:40]:
            print(f"  ! {w}")
        if len(warnings) > 40:
            print(f"  … +{len(warnings) - 40} more")
        return 0
    if "--check" in argv:
        # Gate: every block parsed, no hard extraction failure. Pin-mapping mismatches
        # are advisory (centroid fallback), surfaced but non-fatal — the .nets.yaml
        # pin-coverage gate already lives in generate_schematic.py.
        ok = model["meta"]["blocks"] == len(_NETS_GLOB) and model["meta"]["parts"] > 0
        hard = [w for w in warnings if "failed:" in w or "no symbol primitive" in w]
        print("NETLIST-VIZ CHECK — " + ("OK" if ok and not hard else "FAIL"))
        print(_stats(model, warnings))
        for w in hard:
            print(f"  - {w}")
        return 0 if (ok and not hard) else 1
    _OUT.write_text(render_html(model))
    print(f"wrote {_OUT.relative_to(_REPO)}")
    print(_stats(model, warnings))
    return 0


# ── self-contained viewer (no external deps; canvas + vanilla JS) ─────────────

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>POGO — Netlist Visualizer</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #0d0d0d; color: #ccc;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 13px; }
  #app { display: flex; height: 100%; }
  #side { width: 240px; flex: 0 0 240px; background: #111; border-right: 1px solid #222;
    padding: 12px; overflow-y: auto; }
  #stage { flex: 1; position: relative; overflow: hidden; }
  canvas { display: block; position: absolute; inset: 0; }
  h1 { color: #00d4ff; letter-spacing: .08em; margin: 0 0 2px; font-size: 16px; }
  h1 .dot { color: #ff8800; }
  .sub { color: #4a6070; margin: 0 0 12px; font-size: 11px; letter-spacing: .06em; }
  h2 { color: #7fe7ff; font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
    margin: 14px 0 6px; border-bottom: 1px solid #1c1c1c; padding-bottom: 3px; }
  label.row { display: flex; align-items: center; gap: 7px; padding: 2px 0; cursor: pointer; }
  label.row:hover { color: #fff; }
  .bd { color: #4a6070; font-size: 10px; margin-left: auto; }
  .blk { display: flex; align-items: center; gap: 5px; padding: 1px 0; }
  .blk input { margin: 0; }
  .blk .nm { cursor: pointer; }
  .blk .nm:hover { color: #fff; }
  .blk button { background: #1a1a1a; border: 1px solid #2a2a2a; color: #9ab; cursor: pointer;
    font: inherit; font-size: 10px; border-radius: 3px; padding: 0 5px; margin-left: auto; }
  .blk button:hover { color: #fff; border-color: #00d4ff; }
  .readout { color: #6a8090; font-size: 11px; line-height: 1.7; margin-top: 8px; }
  .readout b { color: #cfe; font-weight: normal; }
  .hint { position: absolute; left: 10px; bottom: 8px; color: #3a4a55; font-size: 11px; }
  #tip { position: absolute; pointer-events: none; background: #1a1f24; border: 1px solid #2a3a44;
    color: #cfe; padding: 5px 8px; border-radius: 4px; font-size: 11px; display: none; z-index: 5;
    white-space: nowrap; box-shadow: 0 3px 12px #0008; }
  #tip .r { color: #ffd27f; } #tip .n { color: #7fe7ff; }
  .legend { font-size: 10px; color: #5a7080; line-height: 1.8; }
  .sw { display: inline-block; width: 18px; height: 0; border-top: 2px solid; vertical-align: middle;
    margin-right: 5px; }
  a { color: #7fe7ff; text-decoration: none; } a:hover { text-decoration: underline; }
  .toolbtn { background: #161616; border: 1px solid #2a2a2a; color: #9ab; cursor: pointer;
    font: inherit; font-size: 11px; border-radius: 4px; padding: 4px 8px; width: 100%; margin-top: 4px; }
  .toolbtn:hover { color: #fff; border-color: #00d4ff; }
</style>
</head>
<body>
<div id="app">
  <div id="side">
    <h1>POGO<span class="dot">.</span> Netlist</h1>
    <div class="sub" id="metasub"></div>

    <h2>View</h2>
    <label class="row"><input type="checkbox" id="hidePower" checked> Hide power → flags</label>
    <label class="row"><input type="checkbox" id="showLabels" checked> Ref labels</label>
    <button class="toolbtn" id="expandAll">Expand all</button>
    <button class="toolbtn" id="collapseAll">Collapse all</button>
    <button class="toolbtn" id="fit">Fit view</button>

    <h2>Blocks</h2>
    <div id="blocks"></div>

    <h2>Component types</h2>
    <div style="display:flex;gap:6px;margin-bottom:4px">
      <button class="toolbtn" id="typeAll" style="margin-top:0">All</button>
      <button class="toolbtn" id="typeNone" style="margin-top:0">None</button>
    </div>
    <div id="types"></div>

    <h2>Readout</h2>
    <div class="readout" id="readout"></div>

    <h2>Legend</h2>
    <div class="legend">
      <span class="sw" style="border-color:#00d4ff"></span>signal net<br>
      <span class="sw" style="border-color:#ff8800"></span>boundary net<br>
      <span class="sw" style="border-color:#c9892f"></span>copper pad / pin<br>
      <span class="sw" style="border-color:#00d4ff;border-top-style:dashed"></span>bridged (via hidden part)<br>
      <span style="color:#e05050">⚑</span> power flag (+12V/−12V/GND)
    </div>
    <div class="legend" style="margin-top:10px">
      drag a part to re-anneal · scroll to zoom · drag bg to pan ·
      shift-drag bg to marquee-select blocks
    </div>
  </div>
  <div id="stage">
    <canvas id="cv"></canvas>
    <div id="tip"></div>
    <div class="hint">POGO stereo filter bank — netlist comprehension view (not authoritative). Generated artifact.</div>
  </div>
</div>
<script>
const MODEL = /*__DATA__*/;
const POWER = new Set(["+12V","-12V","GND"]);
const COL = { signal:"#1f6f8f", signalHi:"#00d4ff", boundary:"#9a5a18", boundaryHi:"#ff8800",
  pad:"#c9892f", fab:"#4a5a66", silk:"#8895a0", crtyd:"#2a6a4a", body:"#222",
  bodyEdge:"#3a4650", label:"#aebfc9", flag:"#e05050", block:"#0e1418", blockEdge:"#26506a" };

// ---- index the model -------------------------------------------------------
const partByRef = {}; MODEL.parts.forEach(p => partByRef[p.ref] = p);
const blockById = {}; MODEL.blocks.forEach(b => blockById[b.id] = b);
const boardOf = {}; MODEL.blocks.forEach(b => boardOf[b.id] = b.board);

// component types (the nets `sym:` token) — friendly labels + visibility filter
const TYPE_LABEL = { r:"Resistor", c:"Capacitor", diode:"Diode", bat54s:"Schottky clamp",
  zener:"Zener", led:"LED", opamp2:"Op-amp (dual)", opamp4:"Op-amp (quad)", ota:"OTA (LM13700)",
  vca:"VCA (THAT2180)", expo:"Expo (THAT340)", cd4053:"Mux (CD4053)", trimpot:"Trimpot",
  jack:"Jack", dw3:"Switch (DW3)", dw5:"Switch (DW5)" };
const typeCount = {}; MODEL.parts.forEach(p => typeCount[p.sym] = (typeCount[p.sym]||0)+1);
const typeVisible = {}; Object.keys(typeCount).forEach(t => typeVisible[t] = true);

// per-part runtime node
const nodes = {};        // ref -> {x,y,vx,vy,fixed}
const blockState = {};   // id -> {visible, collapsed, x,y,vx,vy}  (collapsed super-node uses x,y)
MODEL.blocks.forEach((b,i) => {
  blockState[b.id] = { visible:true, collapsed:true,
    x:(i%4)*240-360, y:Math.floor(i/4)*240-180, vx:0, vy:0 };
});
MODEL.parts.forEach(p => { nodes[p.ref] = { x:0, y:0, vx:0, vy:0, fixed:false }; });

// seed part positions around their block centre (deterministic)
let _seed = 1337; function rnd(){ _seed=(_seed*1103515245+12345)&0x7fffffff; return _seed/0x7fffffff; }
MODEL.parts.forEach(p => { const bs=blockState[p.block];
  nodes[p.ref].x = bs.x + (rnd()-0.5)*120; nodes[p.ref].y = bs.y + (rnd()-0.5)*120; });

// ---- component incidence + bridging through hidden pass-through parts --------
const partNets = {};       // ref -> [netIdx,...] distinct nets touching the part
const partPinCount = {};   // ref -> number of pin endpoints
MODEL.parts.forEach(p => { partNets[p.ref]=[]; partPinCount[p.ref]=0; });
MODEL.nets.forEach((n,i) => n.pins.forEach(e => { partPinCount[e.ref]++;
  if(!partNets[e.ref].includes(i)) partNets[e.ref].push(i); }));
// A part may "bridge" (dashed pass-through) when hidden iff it is a 2-terminal series
// element on two non-power nets — so removing it joins those nets (IC—R—IC ⇒ IC···IC),
// while a shunt/decoupling part (one pin on a rail) is excluded and never merges signal↔GND.
const bridgeable = {};
MODEL.parts.forEach(p => { const ns=partNets[p.ref];
  bridgeable[p.ref] = partPinCount[p.ref]===2 && ns.length===2
    && !POWER.has(MODEL.nets[ns[0]].name) && !POWER.has(MODEL.nets[ns[1]].name); });

// Merged-net "groups" (a group = one or more raw nets joined through hidden bridge parts).
// Rebuilt only when the visibility topology changes (bumpTopo); the force sim + renderer
// both consume groups, so with nothing filtered each group == its raw net (solid, unchanged).
let topoVersion=0, _groups=null, _groupsV=-1;
function bumpTopo(){ topoVersion++; }
function topology(){ if(_groupsV===topoVersion && _groups) return _groups;
  _groups=buildGroups(); _groupsV=topoVersion; return _groups; }
function buildGroups(){
  const N=MODEL.nets.length, par=new Array(N); for(let i=0;i<N;i++) par[i]=i;
  const find=a=>{ while(par[a]!==a){ par[a]=par[par[a]]; a=par[a]; } return a; };
  const uni=(a,b)=>{ a=find(a); b=find(b); if(a!==b) par[a]=b; };
  MODEL.parts.forEach(p => { const bs=blockState[p.block];
    if(bs.visible && !bs.collapsed && !typeVisible[p.sym] && bridgeable[p.ref]){
      const ns=partNets[p.ref]; uni(ns[0],ns[1]); } });
  const byRoot={};
  for(let i=0;i<N;i++){ const r=find(i); (byRoot[r]=byRoot[r]||[]).push(i); }
  return Object.values(byRoot).map(members => {
    let boundary=false, power=false;
    members.forEach(i=>{ const k=MODEL.nets[i].kind;
      if(k==='boundary')boundary=true; if(k==='power')power=true; });
    return { members, bridged: members.length>1, cx:0, cy:0,
      kind: power?'power':(boundary?'boundary':'signal') };
  });
}
function groupVisiblePins(g){ const out=[];
  g.members.forEach(i => MODEL.nets[i].pins.forEach(e => { if(partVisible(e.ref)) out.push(e); }));
  return out; }
function groupActive(g){            // draws iff ≥2 visible pins and not a hidden power net
  if(g.kind==='power' && hidePower.checked) return false;
  return groupVisiblePins(g).length>=2; }

// ---- geometry helpers ------------------------------------------------------
function geomOf(ref){ return MODEL.geom[partByRef[ref].geom]; }
function padLocal(ref,pin){ const g=geomOf(ref); return (g&&g.pads[pin]) || [0,0]; }
function pinAbs(ref,pin){ const n=nodes[ref], l=padLocal(ref,pin); return [n.x+l[0], n.y+l[1]]; }
function partVisible(ref){ const p=partByRef[ref], b=blockState[p.block];
  return b.visible && !b.collapsed && typeVisible[p.sym]; }
function centroidOf(pins){ let x=0,y=0; pins.forEach(e=>{const a=pinAbs(e.ref,e.pin);x+=a[0];y+=a[1];});
  return [x/pins.length, y/pins.length]; }

// boundary endpoints that cross between two *collapsed/visible* blocks
function blockBoundaryLinks(){
  const links=[];
  MODEL.nets.forEach(n => {
    if (POWER.has(n.name) && hidePower.checked) return;
    const blks = new Set(n.pins.map(e=>partByRef[e.ref].block).filter(b=>blockState[b].visible));
    if (blks.size>=2){ const arr=[...blks];
      for(let i=0;i<arr.length;i++) for(let j=i+1;j<arr.length;j++)
        links.push({a:arr[i], b:arr[j], net:n}); }
  });
  return links;
}

// ---- force simulation ------------------------------------------------------
let alpha=1;
function step(){
  if (alpha < 0.02) return;
  const SPRING=0.02, REST=14, REP=2600, BREP=9000, CENTER=0.002, COLL=0.9;
  // active part nodes (expanded+visible)
  const active = MODEL.parts.filter(p=>partVisible(p.ref)).map(p=>p.ref);
  // collapsed/visible block super-nodes
  const sblocks = MODEL.blocks.filter(b=>blockState[b.id].visible && blockState[b.id].collapsed).map(b=>b.id);

  // spring: each group's visible pins -> the group's (merged) centroid
  topology().forEach(g => {
    if(!groupActive(g)) return;
    const vp=groupVisiblePins(g); if(vp.length<2) return;
    const c=centroidOf(vp); g.cx=c[0]; g.cy=c[1];
    vp.forEach(e => { const n=nodes[e.ref], a=pinAbs(e.ref,e.pin);
      if(!n.fixed){ n.vx+=(g.cx-a[0])*SPRING; n.vy+=(g.cy-a[1])*SPRING; } });
  });
  // boundary springs between collapsed block super-nodes
  blockBoundaryLinks().forEach(l => {
    const A=blockState[l.a], B=blockState[l.b];
    if(!(A.collapsed&&B.collapsed)) return;
    const dx=B.x-A.x, dy=B.y-A.y, d=Math.hypot(dx,dy)||1;
    const f=(d-180)*0.0015; A.vx+=dx/d*f; A.vy+=dy/d*f; B.vx-=dx/d*f; B.vy-=dy/d*f;
  });
  // repulsion among active parts (block-local to bound cost)
  for(const bid of new Set(active.map(r=>partByRef[r].block))){
    const refs=active.filter(r=>partByRef[r].block===bid);
    for(let i=0;i<refs.length;i++) for(let j=i+1;j<refs.length;j++){
      const a=nodes[refs[i]], b=nodes[refs[j]];
      let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+0.01; const f=REP/d2;
      const d=Math.sqrt(d2); dx/=d; dy/=d;
      if(!a.fixed){a.vx+=dx*f;a.vy+=dy*f;} if(!b.fixed){b.vx-=dx*f;b.vy-=dy*f;}
    }
  }
  // repulsion among collapsed block super-nodes
  for(let i=0;i<sblocks.length;i++) for(let j=i+1;j<sblocks.length;j++){
    const a=blockState[sblocks[i]], b=blockState[sblocks[j]];
    let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+1; const f=BREP/d2, d=Math.sqrt(d2);
    a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f;
  }
  // integrate parts
  active.forEach(r => { const n=nodes[r]; if(n.fixed) return;
    n.vx-=n.x*CENTER; n.vy-=n.y*CENTER; n.vx*=0.86; n.vy*=0.86;
    n.x+=n.vx*alpha; n.y+=n.vy*alpha; });
  // integrate super-nodes
  sblocks.forEach(b => { const s=blockState[b]; if(s.fixed) return;
    s.vx-=s.x*CENTER; s.vy-=s.y*CENTER; s.vx*=0.86; s.vy*=0.86;
    s.x+=s.vx*alpha; s.y+=s.vy*alpha; });
  alpha*=0.992;
}
function reheat(a=0.7){ alpha=Math.max(alpha,a); }

// ---- view transform --------------------------------------------------------
let view={x:0,y:0,k:1.4};
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
function resize(){ const r=cv.parentElement.getBoundingClientRect();
  cv.width=r.width*devicePixelRatio; cv.height=r.height*devicePixelRatio;
  cv.style.width=r.width+'px'; cv.style.height=r.height+'px'; }
window.addEventListener('resize',()=>{resize();});
function toScreen(x,y){ return [ (x*view.k+view.x)*devicePixelRatio + cv.width/2,
                                 (y*view.k+view.y)*devicePixelRatio + cv.height/2 ]; }
function toWorld(sx,sy){ return [ ((sx*devicePixelRatio - cv.width/2)/devicePixelRatio - view.x)/view.k,
                                  ((sy*devicePixelRatio - cv.height/2)/devicePixelRatio - view.y)/view.k ]; }

// ---- drawing ---------------------------------------------------------------
let hoverNetIdx=-1, hoverRef=null, selBlocks=new Set();
function draw(){
  ctx.setTransform(1,0,0,1,0,0); ctx.clearRect(0,0,cv.width,cv.height);
  ctx.save(); ctx.translate(cv.width/2, cv.height/2);
  ctx.scale(view.k*devicePixelRatio, view.k*devicePixelRatio); ctx.translate(view.x/view.k, view.y/view.k);
  const k=view.k;

  // selection rectangles around selected (collapsed) blocks group
  if(selBlocks.size){ drawSelectionGroup(); }

  // wires (merged-group star) for expanded blocks; dashed = bridged through hidden parts
  topology().forEach(g => {
    if(!groupActive(g)) return;
    const vp=groupVisiblePins(g); if(vp.length<2) return;
    const hi = hoverNetIdx>=0 && g.members.includes(hoverNetIdx);
    ctx.strokeStyle = hi ? (g.kind==='boundary'?COL.boundaryHi:COL.signalHi)
                         : (g.kind==='boundary'?COL.boundary:COL.signal);
    ctx.lineWidth=(hi?1.4:0.6)/k;
    ctx.setLineDash(g.bridged ? [1.5/k,1.1/k] : []);
    vp.forEach(e => { const a=pinAbs(e.ref,e.pin);
      ctx.beginPath(); ctx.moveTo(g.cx,g.cy); ctx.lineTo(a[0],a[1]); ctx.stroke(); });
  });
  ctx.setLineDash([]);
  // boundary links between collapsed blocks
  ctx.lineWidth=1.0/k;
  blockBoundaryLinks().forEach(l => {
    const A=blockState[l.a], B=blockState[l.b]; if(!(A.collapsed&&B.collapsed)) return;
    ctx.strokeStyle=COL.boundary; ctx.globalAlpha=0.5;
    ctx.beginPath(); ctx.moveTo(A.x,A.y); ctx.lineTo(B.x,B.y); ctx.stroke(); ctx.globalAlpha=1;
  });

  // parts (expanded) + collapsed block squares
  MODEL.blocks.forEach(b => {
    const bs=blockState[b.id]; if(!bs.visible) return;
    if(bs.collapsed){ drawCollapsed(b,bs,k); }
    else { b.refs.forEach(r=>drawPart(r,k)); }
  });

  // power flags on expanded parts
  if(hidePower.checked){
    MODEL.nets.forEach(net=>{ if(!POWER.has(net.name)) return;
      net.pins.forEach(e=>{ if(!partVisible(e.ref)) return;
        const a=pinAbs(e.ref,e.pin); drawFlag(a[0],a[1],net.name,k); }); });
  }
  ctx.restore();
}

function drawPart(ref,k){
  const g=geomOf(ref), n=nodes[ref];
  ctx.save(); ctx.translate(n.x,n.y);
  for(const s of g.shapes){
    if(s.t==='pad'){
      ctx.save(); ctx.translate(s.x,s.y); if(s.rot) ctx.rotate(-s.rot*Math.PI/180);
      ctx.fillStyle=COL.pad;
      if(s.shape==='circle'){ ctx.beginPath(); ctx.arc(0,0,s.w/2,0,7); ctx.fill(); }
      else { const rx=(s.shape==='oval'?Math.min(s.w,s.h)/2:0); rr(-s.w/2,-s.h/2,s.w,s.h,rx); ctx.fill(); }
      if(s.drill>0){ ctx.fillStyle=COL.body; ctx.beginPath(); ctx.arc(0,0,s.drill/2,0,7); ctx.fill(); }
      ctx.restore();
    } else { ctx.strokeStyle = s.lyr==='silk'?COL.silk : s.lyr==='crtyd'?COL.crtyd : COL.fab;
      ctx.lineWidth=0.12; stroke(s); }
  }
  if(hoverRef===ref){ ctx.strokeStyle=COL.signalHi; ctx.lineWidth=0.2;
    const bb=g.bbox; ctx.strokeRect(bb[0]-0.4,bb[1]-0.4,bb[2]-bb[0]+0.8,bb[3]-bb[1]+0.8); }
  ctx.restore();
  if(showLabels.checked && k>2.2){ const bb=g.bbox; ctx.fillStyle=COL.label;
    ctx.font=`${1.4}px ui-monospace`; ctx.textAlign='center';
    ctx.fillText(partByRef[ref].label, n.x, n.y+bb[3]+1.6); }
}
function stroke(s){ ctx.beginPath();
  if(s.t==='line'){ ctx.moveTo(s.x1,s.y1); ctx.lineTo(s.x2,s.y2); }
  else if(s.t==='rect'){ ctx.rect(s.x,s.y,s.w,s.h); }
  else if(s.t==='circ'){ ctx.arc(s.cx,s.cy,s.r,0,7); }
  else if(s.t==='poly'){ s.pts.forEach((p,i)=> i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])); }
  ctx.stroke(); }
function rr(x,y,w,h,r){ r=Math.min(r,w/2,h/2); ctx.beginPath();
  ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r);
  ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }

function blockSize(b){ const n=b.refs.length; const s=Math.max(34, Math.min(110, 26+Math.sqrt(n)*7));
  return s; }
function drawCollapsed(b,bs,k){
  const s=blockSize(b), h=s*0.72;
  ctx.fillStyle=COL.block; ctx.strokeStyle = selBlocks.has(b.id)?COL.signalHi:COL.blockEdge;
  ctx.lineWidth=(selBlocks.has(b.id)?1.6:1.0)/k;
  rr(bs.x-s/2,bs.y-h/2,s,h,4); ctx.fill(); ctx.stroke();
  ctx.fillStyle=COL.label; ctx.textAlign='center'; ctx.font=`bold ${Math.max(7,s*0.13)}px ui-monospace`;
  ctx.fillText(b.id, bs.x, bs.y-2);
  ctx.fillStyle='#5a7080'; ctx.font=`${Math.max(6,s*0.10)}px ui-monospace`;
  ctx.fillText(b.refs.length+' parts · '+b.board, bs.x, bs.y+s*0.16);
  if(b.boundary.length){ ctx.fillStyle='#7a6a40';
    ctx.fillText(b.boundary.length+' boundary', bs.x, bs.y+s*0.30); }
}
function drawFlag(x,y,name,k){
  ctx.save(); ctx.translate(x,y); ctx.fillStyle=COL.flag; ctx.strokeStyle=COL.flag;
  ctx.lineWidth=0.12; ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(0,-1.6); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0,-1.6); ctx.lineTo(2.4,-1.6); ctx.lineTo(3.0,-2.3);
  ctx.lineTo(2.4,-3.0); ctx.lineTo(0,-3.0); ctx.closePath(); ctx.globalAlpha=0.85; ctx.fill();
  ctx.globalAlpha=1; if(k>3){ ctx.fillStyle='#fff'; ctx.font='1.0px ui-monospace'; ctx.textAlign='left';
    ctx.fillText(name,0.3,-1.9); } ctx.restore();
}
function drawSelectionGroup(){
  const sel=[...selBlocks].map(id=>blockState[id]).filter(b=>b.visible&&b.collapsed);
  if(sel.length<1) return; let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  [...selBlocks].forEach(id=>{const b=blockById[id],bs=blockState[id]; if(!bs.collapsed)return;
    const s=blockSize(b); x0=Math.min(x0,bs.x-s/2);y0=Math.min(y0,bs.y-s/2);
    x1=Math.max(x1,bs.x+s/2);y1=Math.max(y1,bs.y+s/2);});
  if(x0>x1) return; const pad=16;
  ctx.strokeStyle='#ff8800'; ctx.setLineDash([4/view.k,3/view.k]); ctx.lineWidth=1.2/view.k;
  ctx.strokeRect(x0-pad,y0-pad,x1-x0+pad*2,y1-y0+pad*2); ctx.setLineDash([]);
  ctx.fillStyle='#ff8800'; ctx.font=`${10/view.k}px ui-monospace`; ctx.textAlign='left';
  ctx.fillText('selection — boundary signals between '+selBlocks.size+' blocks', x0-pad, y0-pad-4/view.k);
}

// ---- interaction -----------------------------------------------------------
let drag=null, pan=null, marquee=null;
cv.addEventListener('mousedown', ev => {
  const [wx,wy]=toWorld(ev.offsetX,ev.offsetY);
  if(ev.shiftKey){ marquee={x0:wx,y0:wy,x1:wx,y1:wy}; return; }
  const hit=pick(wx,wy);
  if(hit && hit.ref){ drag={ref:hit.ref}; nodes[hit.ref].fixed=true; reheat(); return; }
  if(hit && hit.block){ drag={block:hit.block}; blockState[hit.block].fixed=true; reheat(); return; }
  pan={sx:ev.offsetX, sy:ev.offsetY, vx:view.x, vy:view.y};
});
window.addEventListener('mousemove', ev => {
  const rect=cv.getBoundingClientRect(), ox=ev.clientX-rect.left, oy=ev.clientY-rect.top;
  const [wx,wy]=toWorld(ox,oy);
  if(drag){ if(drag.ref){nodes[drag.ref].x=wx;nodes[drag.ref].y=wy;}
    else {blockState[drag.block].x=wx;blockState[drag.block].y=wy;} reheat(0.4); return; }
  if(pan){ view.x=pan.vx+(ox-pan.sx); view.y=pan.vy+(oy-pan.sy); return; }
  if(marquee){ marquee.x1=wx; marquee.y1=wy; updateMarquee(); return; }
  // hover
  const hit=pick(wx,wy); const tip=document.getElementById('tip');
  hoverRef=hit&&hit.ref?hit.ref:null; hoverNetIdx=-1;
  if(hit&&hit.ref){ const p=partByRef[hit.ref];
    tip.innerHTML=`<span class="r">${p.label}</span> ${p.value||''}<br>${p.part||p.geom}<br><span class="n">${p.block}</span>`;
    tip.style.display='block'; tip.style.left=(ox+14)+'px'; tip.style.top=(oy+12)+'px';
    // highlight the group of the first net touching this ref
    hoverNetIdx=MODEL.nets.findIndex(n=>n.pins.some(e=>e.ref===hit.ref));
  } else if(hit&&hit.block){ const b=blockById[hit.block];
    tip.innerHTML=`<span class="r">${b.id}</span><br>${b.refs.length} parts · ${b.board}<br>${b.boundary.length} boundary nets`;
    tip.style.display='block'; tip.style.left=(ox+14)+'px'; tip.style.top=(oy+12)+'px';
  } else { tip.style.display='none'; }
});
window.addEventListener('mouseup', () => {
  if(drag){ if(drag.ref)nodes[drag.ref].fixed=false; else blockState[drag.block].fixed=false; drag=null; }
  pan=null;
  if(marquee){ commitMarquee(); marquee=null; document.getElementById('tip').style.display='none'; }
});
function updateMarquee(){ /* visual handled in draw via selBlocks preview */ commitMarquee(true); }
function commitMarquee(preview){
  if(!marquee) return; const x0=Math.min(marquee.x0,marquee.x1), x1=Math.max(marquee.x0,marquee.x1),
    y0=Math.min(marquee.y0,marquee.y1), y1=Math.max(marquee.y0,marquee.y1);
  const s=new Set();
  MODEL.blocks.forEach(b=>{ const bs=blockState[b.id]; if(!bs.visible) return;
    if(bs.x>=x0&&bs.x<=x1&&bs.y>=y0&&bs.y<=y1) s.add(b.id); });
  selBlocks=s; syncBlockList();
}
cv.addEventListener('wheel', ev => { ev.preventDefault();
  const [wx,wy]=toWorld(ev.offsetX,ev.offsetY); const f=Math.exp(-ev.deltaY*0.0015);
  view.k=Math.max(0.15,Math.min(40,view.k*f));
  const [nx,ny]=toWorld(ev.offsetX,ev.offsetY); view.x+=(nx-wx)*view.k; view.y+=(ny-wy)*view.k;
}, {passive:false});
cv.addEventListener('dblclick', ev => { const [wx,wy]=toWorld(ev.offsetX,ev.offsetY);
  const hit=pick(wx,wy); if(hit&&hit.block){ toggleCollapse(hit.block); } });

function pick(wx,wy){
  // collapsed blocks first
  for(const b of MODEL.blocks){ const bs=blockState[b.id]; if(!bs.visible||!bs.collapsed) continue;
    const s=blockSize(b), h=s*0.72;
    if(Math.abs(wx-bs.x)<s/2 && Math.abs(wy-bs.y)<h/2) return {block:b.id}; }
  // expanded parts (bbox hit)
  for(const p of MODEL.parts){ if(!partVisible(p.ref)) continue; const g=geomOf(p.ref), n=nodes[p.ref];
    const bb=g.bbox; if(wx>=n.x+bb[0]-1&&wx<=n.x+bb[2]+1&&wy>=n.y+bb[1]-1&&wy<=n.y+bb[3]+1)
      return {ref:p.ref}; }
  return null;
}

// ---- side panel ------------------------------------------------------------
const hidePower=document.getElementById('hidePower'), showLabels=document.getElementById('showLabels');
function buildSide(){
  document.getElementById('metasub').textContent =
    `${MODEL.meta.parts} parts · ${MODEL.meta.footprinted} fp / ${MODEL.meta.passive_or_symbol} sym · ${MODEL.meta.nets} nets · ${MODEL.meta.generated}`;
  const host=document.getElementById('blocks'); host.innerHTML='';
  const boards={}; MODEL.blocks.forEach(b=>(boards[b.board]=boards[b.board]||[]).push(b));
  Object.keys(boards).sort().forEach(board=>{
    const hd=document.createElement('div'); hd.className='bd'; hd.style.margin='6px 0 2px';
    hd.style.color='#456'; hd.textContent='— '+board+' board —'; host.appendChild(hd);
    boards[board].forEach(b=>{
      const row=document.createElement('div'); row.className='blk';
      const cb=document.createElement('input'); cb.type='checkbox'; cb.checked=true;
      cb.onchange=()=>{ blockState[b.id].visible=cb.checked; bumpTopo(); reheat(); syncBlockList(); };
      const nm=document.createElement('span'); nm.className='nm'; nm.textContent=b.id;
      nm.title=b.title; nm.onclick=()=>{ selBlocks=new Set([b.id]); syncBlockList(); };
      const bt=document.createElement('button'); bt.textContent='▣';
      bt.title='collapse / expand'; bt.onclick=()=>toggleCollapse(b.id);
      row.append(cb,nm,bt); row.dataset.bid=b.id; host.appendChild(row);
    });
  });
  syncBlockList();
  buildTypes();
}
function buildTypes(){
  const host=document.getElementById('types'); host.innerHTML='';
  Object.keys(typeCount).sort((a,b)=>typeCount[b]-typeCount[a]).forEach(t=>{
    const row=document.createElement('label'); row.className='row';
    const cb=document.createElement('input'); cb.type='checkbox'; cb.checked=typeVisible[t];
    cb.onchange=()=>{ typeVisible[t]=cb.checked; bumpTopo(); reheat(); };
    const nm=document.createElement('span'); nm.textContent=TYPE_LABEL[t]||t;
    const ct=document.createElement('span'); ct.className='bd'; ct.textContent=typeCount[t];
    row.append(cb,nm,ct); row.dataset.type=t; host.appendChild(row);
  });
}
function syncTypeList(){ document.querySelectorAll('#types .row').forEach(r=>{
  r.querySelector('input').checked=typeVisible[r.dataset.type]; }); }
function syncBlockList(){
  document.querySelectorAll('.blk').forEach(row=>{ const b=row.dataset.bid; if(!b) return;
    const bs=blockState[b]; row.querySelector('.nm').style.color = selBlocks.has(b)?'#ff8800':
      (bs.collapsed?'#9ab':'#cfe'); row.querySelector('input').checked=bs.visible;
    row.querySelector('button').style.color = bs.collapsed?'#9ab':'#00d4ff'; });
}
function toggleCollapse(id){ const bs=blockState[id]; bs.collapsed=!bs.collapsed; bumpTopo();
  if(!bs.collapsed){ // expanding: seed parts around the (former) super-node
    blockById[id].refs.forEach(r=>{ nodes[r].x=bs.x+(rnd()-0.5)*blockSize(blockById[id]);
      nodes[r].y=bs.y+(rnd()-0.5)*blockSize(blockById[id]); }); }
  reheat(); syncBlockList(); }

document.getElementById('expandAll').onclick=()=>{ MODEL.blocks.forEach(b=>{
  if(blockState[b.id].collapsed) toggleCollapse(b.id); }); };
document.getElementById('collapseAll').onclick=()=>{ MODEL.blocks.forEach(b=>blockState[b.id].collapsed=true);
  bumpTopo(); reheat(); syncBlockList(); };
document.getElementById('fit').onclick=fitView;
document.getElementById('typeAll').onclick=()=>{ Object.keys(typeVisible).forEach(t=>typeVisible[t]=true);
  syncTypeList(); bumpTopo(); reheat(); };
document.getElementById('typeNone').onclick=()=>{ Object.keys(typeVisible).forEach(t=>typeVisible[t]=false);
  syncTypeList(); bumpTopo(); reheat(); };
hidePower.onchange=()=>reheat(); showLabels.onchange=()=>{};

function fitView(){ let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  MODEL.blocks.forEach(b=>{ const bs=blockState[b.id]; if(!bs.visible) return;
    if(bs.collapsed){ const s=blockSize(b); x0=Math.min(x0,bs.x-s);y0=Math.min(y0,bs.y-s);
      x1=Math.max(x1,bs.x+s);y1=Math.max(y1,bs.y+s); }
    else b.refs.forEach(r=>{const n=nodes[r];x0=Math.min(x0,n.x-6);y0=Math.min(y0,n.y-6);
      x1=Math.max(x1,n.x+6);y1=Math.max(y1,n.y+6);}); });
  if(x0>x1) return; const w=x1-x0,h=y1-y0, r=cv.getBoundingClientRect();
  view.k=Math.max(0.15,Math.min(8, 0.9*Math.min(r.width/w, r.height/h)));
  view.x=-(x0+x1)/2*view.k; view.y=-(y0+y1)/2*view.k; }

// ---- readout ---------------------------------------------------------------
function updateReadout(){
  let vis=0, len=0, brid=0;
  topology().forEach(g=>{ if(!groupActive(g)) return; const vp=groupVisiblePins(g);
    if(vp.length<2) return; vis++; if(g.bridged) brid++;
    vp.forEach(e=>{const a=pinAbs(e.ref,e.pin); len+=Math.hypot(g.cx-a[0],g.cy-a[1]);}); });
  const expanded=MODEL.blocks.filter(b=>blockState[b.id].visible&&!blockState[b.id].collapsed).length;
  const vparts=MODEL.parts.reduce((a,p)=>a+(partVisible(p.ref)?1:0),0);
  const types=Object.values(typeVisible).filter(v=>v).length, ntypes=Object.keys(typeVisible).length;
  document.getElementById('readout').innerHTML =
    `visible parts <b>${vparts}</b><br>visible nets <b>${vis}</b>`+
    (brid?` <span style="color:#7a8a96">(${brid} bridged)</span>`:'')+`<br>`+
    `ratsnest length <b>${len.toFixed(0)}</b> mm<br>`+
    `expanded blocks <b>${expanded}</b>/${MODEL.blocks.length}<br>`+
    `types <b>${types}</b>/${ntypes} · selected <b>${selBlocks.size}</b>`;
}

// ---- main loop -------------------------------------------------------------
function loop(){ step(); draw();
  if(marquee){ // live marquee rectangle
    ctx.save(); ctx.translate(cv.width/2,cv.height/2);
    ctx.scale(view.k*devicePixelRatio,view.k*devicePixelRatio); ctx.translate(view.x/view.k,view.y/view.k);
    ctx.strokeStyle='#ff8800'; ctx.lineWidth=1/view.k; ctx.setLineDash([4/view.k,3/view.k]);
    ctx.strokeRect(Math.min(marquee.x0,marquee.x1),Math.min(marquee.y0,marquee.y1),
      Math.abs(marquee.x1-marquee.x0),Math.abs(marquee.y1-marquee.y0)); ctx.setLineDash([]); ctx.restore(); }
  updateReadout(); requestAnimationFrame(loop); }

resize(); buildSide(); fitView(); reheat(1); loop();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
