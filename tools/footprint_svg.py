"""footprint_svg.py — render a vendored KiCad .kicad_mod to a small SVG land-pattern.

Used by build_components.py to pre-render footprint previews into docs/footprints/
for the interactive BOM viewer (docs/bom.html). Deterministic / byte-stable.

Scope: the subset of .kicad_mod the POGO vendored footprints actually use — pads
(smd/thru_hole; rect, roundrect, oval, circle) with optional rotation + drill, and
graphic lines/rects/circles on the silk (F.SilkS), fab (F.Fab) and courtyard (F.CrtYd)
layers. KiCad footprint coords are +x right / +y down, matching SVG, so no Y flip.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_FP_ROOT = _REPO / "components" / "footprints"

# dark palette matching docs/*.html
_BG = "#141414"
_COPPER = "#c9892f"
_HOLE = "#0d0d0d"
_SILK = "#c9d4da"
_FAB = "#4a5a66"
_CRTYD = "#2a8a5a"
_PADTXT = "#1a1200"


# ── s-expr parse ──────────────────────────────────────────────────────────────

def _parse(text: str):
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


def _f(x):
    return float(x)


# ── extract geometry ──────────────────────────────────────────────────────────

def _layers_of(node):
    ln = _first(node, "layer") or _first(node, "layers")
    return [s for s in (ln[1:] if ln else []) if isinstance(s, str)]


def parse_footprint(text: str) -> dict:
    root = _parse(text)
    if not root or root[0] not in ("footprint", "module"):  # KiCad 6+ / legacy KiCad 5
        raise ValueError("not a footprint")
    pads, lines, rects, circles = [], [], [], []

    for pad in _kids(root, "pad"):
        # (pad "N" <type> <shape> (at x y [rot]) (size w h) [(drill d)] (layers ...))
        num = pad[1] if len(pad) > 1 else ""
        ptype = pad[2] if len(pad) > 2 else "smd"
        shape = pad[3] if len(pad) > 3 else "rect"
        at = _first(pad, "at"); size = _first(pad, "size"); drill = _first(pad, "drill")
        if not at or not size:
            continue
        rot = _f(at[3]) if len(at) > 3 else 0.0
        d = 0.0
        if drill:
            # drill may be "(drill 1.0)" or "(drill oval 1 2)"
            nums = [a for a in drill[1:] if re.match(r"^-?\d", str(a))]
            d = _f(nums[0]) if nums else 0.0
        pads.append({"num": num, "type": ptype, "shape": shape,
                     "x": _f(at[1]), "y": _f(at[2]), "rot": rot,
                     "w": _f(size[1]), "h": _f(size[2]), "drill": d})

    for ln in _kids(root, "fp_line"):
        s, e = _first(ln, "start"), _first(ln, "end")
        if s and e:
            lines.append({"x1": _f(s[1]), "y1": _f(s[2]), "x2": _f(e[1]), "y2": _f(e[2]),
                          "layers": _layers_of(ln)})
    for rc in _kids(root, "fp_rect"):
        s, e = _first(rc, "start"), _first(rc, "end")
        if s and e:
            rects.append({"x1": _f(s[1]), "y1": _f(s[2]), "x2": _f(e[1]), "y2": _f(e[2]),
                          "layers": _layers_of(rc)})
    for ci in _kids(root, "fp_circle"):
        c, e = _first(ci, "center"), _first(ci, "end")
        if c and e:
            r = math.hypot(_f(e[1]) - _f(c[1]), _f(e[2]) - _f(c[2]))
            circles.append({"cx": _f(c[1]), "cy": _f(c[2]), "r": r, "layers": _layers_of(ci)})
    return {"pads": pads, "lines": lines, "rects": rects, "circles": circles}


# ── render ──────────────────────────────────────────────────────────────────--

def _pad_corners(p):
    """Axis-aligned bbox of a pad after rotation (for the drawing bbox)."""
    hw, hh = p["w"] / 2, p["h"] / 2
    pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    a = math.radians(p["rot"])
    ca, sa = math.cos(a), math.sin(a)
    xs = [p["x"] + dx * ca - dy * sa for dx, dy in pts]
    ys = [p["y"] + dx * sa + dy * ca for dx, dy in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox(fp):
    xs, ys = [], []
    for p in fp["pads"]:
        x0, y0, x1, y1 = _pad_corners(p)
        xs += [x0, x1]; ys += [y0, y1]
    for ln in fp["lines"] + fp["rects"]:
        xs += [ln["x1"], ln["x2"]]; ys += [ln["y1"], ln["y2"]]
    for c in fp["circles"]:
        xs += [c["cx"] - c["r"], c["cx"] + c["r"]]; ys += [c["cy"] - c["r"], c["cy"] + c["r"]]
    if not xs:
        return -1, -1, 1, 1
    return min(xs), min(ys), max(xs), max(ys)


def _fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _layer_color(layers):
    if any("CrtYd" in l for l in layers):
        return _CRTYD, "0.4,0.3"
    if any("SilkS" in l for l in layers):
        return _SILK, None
    return _FAB, None


def render_svg(text: str, name: str = "") -> str:
    fp = parse_footprint(text)
    minx, miny, maxx, maxy = _bbox(fp)
    pad_mm = 0.6
    minx -= pad_mm; miny -= pad_mm; maxx += pad_mm; maxy += pad_mm
    w_mm, h_mm = maxx - minx, maxy - miny
    scale = max(6.0, min(40.0, 210.0 / w_mm, 150.0 / h_mm))
    W, H = w_mm * scale, h_mm * scale

    out = [
        '<!-- GENERATED by tools/build_components.py --gen-fp from components/footprints/ — DO NOT EDIT -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(W)}" height="{_fmt(H)}" '
        f'viewBox="0 0 {_fmt(W)} {_fmt(H)}" role="img" aria-label="footprint {name}">',
        f'<rect x="0" y="0" width="{_fmt(W)}" height="{_fmt(H)}" fill="{_BG}"/>',
        f'<g transform="translate({_fmt(-minx*scale)},{_fmt(-miny*scale)}) scale({_fmt(scale)})">',
    ]
    sw = 0.12  # graphic stroke (mm)

    # graphics first (under pads): courtyard, fab, silk
    for c in fp["circles"]:
        col, dash = _layer_color(c["layers"])
        da = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<circle cx="{_fmt(c["cx"])}" cy="{_fmt(c["cy"])}" r="{_fmt(c["r"])}" '
                   f'fill="none" stroke="{col}" stroke-width="{sw}"{da}/>')
    for r in fp["rects"]:
        col, dash = _layer_color(r["layers"])
        da = f' stroke-dasharray="{dash}"' if dash else ""
        x, y = min(r["x1"], r["x2"]), min(r["y1"], r["y2"])
        out.append(f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(abs(r["x2"]-r["x1"]))}" '
                   f'height="{_fmt(abs(r["y2"]-r["y1"]))}" fill="none" stroke="{col}" '
                   f'stroke-width="{sw}"{da}/>')
    for ln in fp["lines"]:
        col, dash = _layer_color(ln["layers"])
        da = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<line x1="{_fmt(ln["x1"])}" y1="{_fmt(ln["y1"])}" x2="{_fmt(ln["x2"])}" '
                   f'y2="{_fmt(ln["y2"])}" stroke="{col}" stroke-width="{sw}"{da} '
                   f'stroke-linecap="round"/>')

    # pads on top
    for p in fp["pads"]:
        hw, hh = p["w"] / 2, p["h"] / 2
        tx = f' transform="rotate({_fmt(p["rot"])} {_fmt(p["x"])} {_fmt(p["y"])})"' if p["rot"] else ""
        if p["shape"] == "circle":
            shape = f'<circle cx="{_fmt(p["x"])}" cy="{_fmt(p["y"])}" r="{_fmt(hw)}" fill="{_COPPER}"/>'
        else:
            rx = min(hw, hh) * (0.5 if p["shape"] == "oval" else 0.22 if p["shape"] == "roundrect" else 0)
            shape = (f'<rect x="{_fmt(p["x"]-hw)}" y="{_fmt(p["y"]-hh)}" width="{_fmt(p["w"])}" '
                     f'height="{_fmt(p["h"])}" rx="{_fmt(rx)}" fill="{_COPPER}"/>')
        out.append(f'<g{tx}>{shape}</g>')
        if p["drill"] > 0:
            out.append(f'<circle cx="{_fmt(p["x"])}" cy="{_fmt(p["y"])}" r="{_fmt(p["drill"]/2)}" fill="{_HOLE}"/>')
        # pad number
        fs = max(0.5, min(p["w"], p["h"]) * 0.55)
        out.append(f'<text x="{_fmt(p["x"])}" y="{_fmt(p["y"])}" fill="{_PADTXT}" '
                   f'font-size="{_fmt(fs)}" font-family="monospace" text-anchor="middle" '
                   f'dominant-baseline="central">{_xesc(p["num"])}</text>')

    out.append("</g></svg>")
    return "\n".join(out) + "\n"


def _xesc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── enumerate vendored footprints ────────────────────────────────────────────--

def slug(footprint_id: str) -> str:
    """'POGO_Package_SO:SOIC-8_..' -> filesystem-safe slug (matches docs/bom.html)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", footprint_id)


def iter_footprints():
    """Yield (footprint_id, slug, kicad_mod_path) for every vendored .kicad_mod."""
    for pretty in sorted(_FP_ROOT.glob("*.pretty")):
        lib = pretty.name[: -len(".pretty")]
        for mod in sorted(pretty.glob("*.kicad_mod")):
            fid = f"POGO_{lib}:{mod.stem}"
            yield fid, slug(fid), mod


def render_all() -> dict[str, str]:
    """{slug: svg_text} for every vendored footprint (deterministic order)."""
    out = {}
    for fid, sl, path in iter_footprints():
        out[sl] = render_svg(path.read_text(), name=fid)
    return out
