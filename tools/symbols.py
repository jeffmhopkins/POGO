"""symbols.py — data-driven KiCad schematic symbols.

Loads `components/symbols.yaml` (authored, archetype-keyed = the nets `sym:` token)
and provides:
  - emit_symbol(spec)               → the `(symbol "lib_id" …)` lib_symbols s-expr
  - pin_points(spec, ox, oy, ang, unit) → {pin_number: (x, y)} connection points
  - placement(spec)                 → [(unit, dx, dy)] multi-unit placement offsets
  - pin_number(spec, name) / power_pins(spec) → for gen_block6's rail wiring

The pin `at` coordinate is the SINGLE source: `connection_point()` returns it, the
emitter writes the same value into the pin's `(at …)`, and `pin_points()` rotates it.
So the symbol and its pin map can't drift (the bug class behind the LM13700 / THAT340 /
CD4053 fixes). `parse_symbol()` is the inverse, used to migrate/verify the old
hand-written `kicad_common.sym_*()` functions into data.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parent.parent
_SYMBOLS_YAML = _REPO / "components" / "symbols.yaml"


# ── s-expr tokenizer (shared shape with generate_schematic) ───────────────────

def _parse_sexpr(text: str):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    pos = [0]

    def atom(t):
        return t[1:-1].replace('\\"', '"') if t.startswith('"') else t

    def walk():
        node = []
        while pos[0] < len(toks):
            t = toks[pos[0]]; pos[0] += 1
            if t == "(":
                node.append(walk())
            elif t == ")":
                return node
            else:
                node.append(atom(t))
        return node

    if not toks or toks[0] != "(":
        raise ValueError("not an s-expression")
    pos[0] = 1
    return walk()


def _kids(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def _first(node, head):
    cs = _kids(node, head)
    return cs[0] if cs else None


def _fnum(s):
    return float(s)


def _fmt(v) -> str:
    """KiCad-style number: no trailing zeros (8.89, 0, -11.43)."""
    if isinstance(v, str):
        return v
    s = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ── parse: old sym_*() s-expr → spec dict (migration / verification) ──────────

def _parse_effects(node):
    """(effects (font (size a b)) [(justify …)] [hide]) → {font:[a,b], justify, hide}."""
    eff = {}
    e = _first(node, "effects")
    if not e:
        return eff
    f = _first(e, "font")
    if f:
        sz = _first(f, "size")
        if sz:
            eff["font"] = [_fnum(sz[1]), _fnum(sz[2])]
    j = _first(e, "justify")
    if j:
        eff["justify"] = j[1:]
    if "hide" in e or any(c == "hide" for c in e):
        eff["hide"] = True
    return eff


def _parse_graphic(g):
    kind = g[0]
    out = {"kind": kind}
    st = _first(g, "stroke")
    if st:
        w = _first(st, "width")
        if w:
            out["width"] = _fnum(w[1])
    fl = _first(g, "fill")
    if fl:
        t = _first(fl, "type")
        if t:
            out["fill"] = t[1]
    if kind == "rectangle":
        s, e = _first(g, "start"), _first(g, "end")
        out["start"] = [_fnum(s[1]), _fnum(s[2])]
        out["end"] = [_fnum(e[1]), _fnum(e[2])]
    elif kind == "polyline":
        pts = _first(g, "pts")
        out["pts"] = [[_fnum(p[1]), _fnum(p[2])] for p in _kids(pts, "xy")]
    elif kind == "circle":
        c = _first(g, "center"); r = _first(g, "radius")
        out["center"] = [_fnum(c[1]), _fnum(c[2])]
        out["radius"] = _fnum(r[1])
    elif kind == "arc":
        for k in ("start", "mid", "end"):
            n = _first(g, k)
            if n:
                out[k] = [_fnum(n[1]), _fnum(n[2])]
    else:
        raise ValueError(f"unhandled graphic {kind}")
    return out


def _parse_pin(p):
    at = _first(p, "at")
    ln = _first(p, "length")
    nm = _first(p, "name")
    num = _first(p, "number")
    out = {
        "type": p[1], "style": p[2],
        "at": [_fnum(at[1]), _fnum(at[2])],
        "angle": _fnum(at[3]) if len(at) > 3 else 0.0,
        "len": _fnum(ln[1]) if ln else 2.54,
        "name": nm[1], "number": num[1],
    }
    nf = _parse_effects(nm).get("font")
    qf = _parse_effects(num).get("font")
    if nf:
        out["name_font"] = nf
    if qf:
        out["num_font"] = qf
    return out


def parse_symbol(text: str) -> dict:
    """Old sym_*() s-expr → spec dict."""
    root = _parse_sexpr(text)
    assert root[0] == "symbol", root[0]
    spec = {"lib_id": root[1], "properties": [], "units": []}
    pn = _first(root, "pin_names")
    if pn:
        d = {}
        off = _first(pn, "offset")
        if off:
            d["offset"] = _fnum(off[1])
        if "hide" in pn:
            d["hide"] = True
        spec["pin_names"] = d
    pnum = _first(root, "pin_numbers")
    if pnum:
        spec["pin_numbers_hide"] = ("hide" in pnum)
    for pr in _kids(root, "property"):
        at = _first(pr, "at")
        p = {"key": pr[1], "val": pr[2],
             "at": [_fnum(at[1]), _fnum(at[2]), _fnum(at[3]) if len(at) > 3 else 0.0]}
        p.update(_parse_effects(pr))
        spec["properties"].append(p)
    for sub in _kids(root, "symbol"):
        name = sub[1]
        m = re.search(r"_(\d+)_(\d+)$", name)
        prefix = name[: m.start()] if m else name
        spec.setdefault("name", prefix)
        unit = int(m.group(1)) if m else 1
        style = int(m.group(2)) if m else 1
        u = {"unit": unit, "style": style, "graphics": [], "pins": []}
        for g in sub[2:]:
            if not isinstance(g, list):
                continue
            if g[0] == "pin":
                u["pins"].append(_parse_pin(g))
            else:
                u["graphics"].append(_parse_graphic(g))
        spec["units"].append(u)
    return spec


# ── emit: spec dict → lib_symbols s-expr (clean, deterministic format) ────────

def _emit_effects(eff, indent):
    parts = [f"(font (size {_fmt(eff['font'][0])} {_fmt(eff['font'][1])}))"] if eff.get("font") else []
    if eff.get("justify"):
        parts.append("(justify " + " ".join(eff["justify"]) + ")")
    if eff.get("hide"):
        parts.append("(hide yes)")
    return " (effects " + " ".join(parts) + ")" if parts else " (effects)"


def _emit_graphic(g):
    w = _fmt(g.get("width", 0))
    fill = f' (fill (type {g.get("fill", "none")}))'
    stroke = f" (stroke (width {w}) (type default))"
    if g["kind"] == "rectangle":
        return (f'(rectangle (start {_fmt(g["start"][0])} {_fmt(g["start"][1])}) '
                f'(end {_fmt(g["end"][0])} {_fmt(g["end"][1])}){stroke}{fill})')
    if g["kind"] == "polyline":
        pts = " ".join(f"(xy {_fmt(x)} {_fmt(y)})" for x, y in g["pts"])
        return f'(polyline (pts {pts}){stroke}{fill})'
    if g["kind"] == "circle":
        return (f'(circle (center {_fmt(g["center"][0])} {_fmt(g["center"][1])}) '
                f'(radius {_fmt(g["radius"])}){stroke}{fill})')
    if g["kind"] == "arc":
        return (f'(arc (start {_fmt(g["start"][0])} {_fmt(g["start"][1])}) '
                f'(mid {_fmt(g["mid"][0])} {_fmt(g["mid"][1])}) '
                f'(end {_fmt(g["end"][0])} {_fmt(g["end"][1])}){stroke}{fill})')
    raise ValueError(g["kind"])


def _emit_pin(p):
    nf = p.get("name_font", [1.27, 1.27])
    qf = p.get("num_font", [1.27, 1.27])
    ang = _fmt(p.get("angle", 0))
    return (f'(pin {p["type"]} {p.get("style", "line")} '
            f'(at {_fmt(p["at"][0])} {_fmt(p["at"][1])} {ang}) (length {_fmt(p["len"])}) '
            f'(name "{p["name"]}" (effects (font (size {_fmt(nf[0])} {_fmt(nf[1])})))) '
            f'(number "{p["number"]}" (effects (font (size {_fmt(qf[0])} {_fmt(qf[1])})))))')


def emit_symbol(spec: dict) -> str:
    name = spec.get("name") or spec["lib_id"].split(":")[-1]
    out = [f'  (symbol "{spec["lib_id"]}"']
    pn = spec.get("pin_names")
    if pn is not None:
        s = f'    (pin_names (offset {_fmt(pn.get("offset", 0))})'
        s += " hide)" if pn.get("hide") else ")"
        out.append(s)
    if spec.get("pin_numbers_hide"):
        out.append("    (pin_numbers hide)")
    for pr in spec["properties"]:
        out.append(f'    (property "{pr["key"]}" "{pr["val"]}" '
                   f'(at {_fmt(pr["at"][0])} {_fmt(pr["at"][1])} {_fmt(pr["at"][2])})'
                   f'{_emit_effects(pr, 0)})')
    for u in spec["units"]:
        out.append(f'    (symbol "{name}_{u["unit"]}_{u.get("style", 1)}"')
        for g in u["graphics"]:
            out.append("      " + _emit_graphic(g))
        for p in u["pins"]:
            out.append("      " + _emit_pin(p))
        out.append("    )")
    out.append("  )")
    return "\n".join(out)


# ── connection points (the single source shared by emit + pins) ───────────────

def _rot(ox, oy, angle, dx, dy):
    a = math.radians(angle)
    return (ox + dx * math.cos(a) - dy * math.sin(a),
            oy + dx * math.sin(a) + dy * math.cos(a))


def connection_point(pin):
    """The pin's local connection point = its (at) coordinate (NOT the stub end)."""
    return (pin["at"][0], pin["at"][1])


def pin_points(spec, ox=0.0, oy=0.0, angle=0.0, unit=None) -> dict:
    """{pin_number: (x, y)} for one unit (or all units if unit is None)."""
    out = {}
    for u in spec["units"]:
        if unit is not None and u["unit"] != unit:
            continue
        for p in u["pins"]:
            lx, ly = connection_point(p)
            out[p["number"]] = _rot(ox, oy, angle, lx, ly)
    return out


# ── loader + queries ──────────────────────────────────────────────────────────

_CACHE = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = yaml.safe_load(_SYMBOLS_YAML.read_text())["archetypes"]
    return _CACHE


def placement(spec) -> list:
    """[(unit, dx, dy)] multi-unit placement offsets; single-unit → [(unit, 0, 0)]."""
    pl = spec.get("placement")
    if pl:
        return [(p["unit"], p["dx"], p["dy"]) for p in pl]
    return [(spec["units"][0]["unit"], 0.0, 0.0)]


def all_pin_numbers(spec) -> set:
    return {p["number"] for u in spec["units"] for p in u["pins"]}


def pin_number(spec, name) -> list:
    """Pin number(s) whose name == `name` (list — e.g. THAT340 has two SUB)."""
    return [p["number"] for u in spec["units"] for p in u["pins"] if p["name"] == name]


# ── self-test (CI gate, run from generate_schematic.py --check) ───────────────

# A citation that names neither a document number nor a page/section is a
# placeholder, not a verification — these strings would have hidden the
# LM13700 / THAT340 / CD4053 pinout bugs.
_PLACEHOLDER = re.compile(r"\b(tbd|todo|fixme|verify|placeholder|unknown)\b", re.I)


def selfcheck() -> list:
    """Validate every archetype in components/symbols.yaml. Returns problems.

    - structural: lib_id present, ≥1 unit, ≥1 pin, pin NUMBERS globally unique
      within the symbol (a repeated number is two pins fighting for one pad);
    - emitter faithfulness: emit → parse → emit is byte-stable, so the YAML is a
      sound symbol and the connection-point is the single source for emit + pins;
    - multi-unit: placement (if present) covers exactly the symbol's unit set;
    - provenance: every NON-primitive archetype carries a real `pinout_datasheet`
      citation (a document/page, not a "verify before layout" placeholder).
    """
    syms = load()
    errs = []
    for key, spec in sorted(syms.items()):
        if not spec.get("lib_id"):
            errs.append(f"{key}: missing lib_id")
        units = spec.get("units") or []
        if not units:
            errs.append(f"{key}: no units")
            continue
        nums = [p["number"] for u in units for p in u["pins"]]
        if not nums:
            errs.append(f"{key}: no pins")
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        if dupes:
            errs.append(f"{key}: duplicate pin number(s) {dupes} (one pad, two pins)")

        # emit must round-trip through the parser unchanged.
        try:
            text = emit_symbol(spec)
            if emit_symbol(parse_symbol(text)) != text:
                errs.append(f"{key}: emit→parse→emit not byte-stable")
        except Exception as e:                       # noqa: BLE001
            errs.append(f"{key}: emit/parse failed: {e}")

        # placement (multi-unit) must name exactly the real units. Unit 0 is the
        # common/background graphics drawn for every unit, not a placeable instance.
        pl = spec.get("placement")
        if pl:
            placed = {p["unit"] for p in pl}
            have = {u["unit"] for u in units if u["unit"] != 0}
            if placed != have:
                errs.append(f"{key}: placement units {sorted(placed)} != symbol units {sorted(have)}")

        # provenance for real parts (primitives like R/C/D are self-evident).
        if not spec.get("primitive"):
            cite = (spec.get("pinout_datasheet") or "").strip()
            if not cite:
                errs.append(f"{key}: non-primitive needs a pinout_datasheet citation")
            elif _PLACEHOLDER.search(cite):
                errs.append(f"{key}: pinout_datasheet looks like a placeholder: {cite!r}")
    return errs


if __name__ == "__main__":
    import sys
    problems = selfcheck()
    if problems:
        print("SYMBOLS CHECK — FAIL:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"SYMBOLS CHECK — OK ({len(load())} archetypes).")
