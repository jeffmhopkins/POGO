"""components.py — dynamic component registry for POGO.

Single read-API over the canonical `components/` tree:
  components/footprints.yaml        panel-type -> KiCad footprint + anchor offset
  components/parts/<slug>/component.yaml   one sourced part (mpn, footprint, datasheet, ...)

Consumers (panel_kicad, build tools, future KiCad generator) resolve parts and
footprints through here instead of hardcoding paths. `specs/components.yaml`
remains the hand-maintained BOM for now; this loader is the programmatic API.

CLI:
  python3 tools/components.py --check     validate the registry (CI gate)
  python3 tools/components.py --list      list parts + footprint bindings
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parent.parent
_COMPONENTS = _REPO / "components"
_FOOTPRINTS_YAML = _COMPONENTS / "footprints.yaml"
_PARTS_DIR = _COMPONENTS / "parts"
_FP_ROOT = _REPO / "components" / "footprints"

# Required fields for every part record.
_PART_REQUIRED = ("slug", "mpn", "package")


@lru_cache(maxsize=1)
def _footprints_raw() -> list[dict[str, Any]]:
    data = yaml.safe_load(_FOOTPRINTS_YAML.read_text())
    return list(data.get("footprints", []))


def footprint_map() -> dict[str, tuple[str, float, float]]:
    """Ordered {panel_type: (rel_path, ox, oy)} — drop-in for the legacy _FOOTPRINT_MAP.

    rel_path is "<lib>.pretty/<name>.kicad_mod" relative to components/footprints/.
    Order follows components/footprints.yaml (significant: feeds the editor payload).
    """
    out: dict[str, tuple[str, float, float]] = {}
    for fp in _footprints_raw():
        rel = f'{fp["lib"]}.pretty/{fp["name"]}.kicad_mod'
        out[fp["type"]] = (rel, float(fp["ox"]), float(fp["oy"]))
    return out


def footprint_rel_paths() -> list[str]:
    """Distinct footprint rel-paths referenced by the panel (for fp-lib-table gen)."""
    seen: list[str] = []
    for rel, _, _ in footprint_map().values():
        if rel not in seen:
            seen.append(rel)
    return seen


@lru_cache(maxsize=1)
def parts() -> list[dict[str, Any]]:
    """All sourced-part records (components/parts/<slug>/component.yaml), slug-sorted."""
    out = []
    if _PARTS_DIR.is_dir():
        for d in sorted(_PARTS_DIR.iterdir()):
            f = d / "component.yaml"
            if f.is_file():
                rec = yaml.safe_load(f.read_text()) or {}
                rec.setdefault("slug", d.name)
                out.append(rec)
    return out


def part(slug: str) -> dict[str, Any] | None:
    for p in parts():
        if p.get("slug") == slug:
            return p
    return None


@lru_cache(maxsize=1)
def _match_index() -> dict[str, dict[str, Any]]:
    """components.yaml `part:` string -> registry part (via each part's matches[])."""
    idx: dict[str, dict[str, Any]] = {}
    for p in parts():
        for m in (p.get("matches") or []):
            idx[m] = p
    return idx


def part_for(part_str: str) -> dict[str, Any] | None:
    """Resolve a components.yaml `part:` value to its registry part, or None."""
    return _match_index().get(part_str)


_SPEC_COMPONENTS = _REPO / "specs" / "components.yaml"


@lru_cache(maxsize=1)
def bom_components() -> list[dict[str, Any]]:
    """The hand-maintained BOM rows from specs/components.yaml (in file order)."""
    data = yaml.safe_load(_SPEC_COMPONENTS.read_text())
    return list(data.get("components", []))


# ── Validation ──────────────────────────────────────────────────────────────

def validate() -> list[str]:
    """Return a list of human-readable problems (empty = OK)."""
    errs: list[str] = []

    # Footprint bindings: required keys + the .kicad_mod file must exist.
    fps = _footprints_raw()
    if not fps:
        errs.append("footprints.yaml: no entries")
    seen_types: set[str] = set()
    for i, fp in enumerate(fps):
        for k in ("type", "lib", "name", "ox", "oy"):
            if k not in fp:
                errs.append(f"footprints[{i}]: missing '{k}'")
        t = fp.get("type")
        if t in seen_types:
            errs.append(f"footprints: duplicate type '{t}'")
        seen_types.add(t)
        if "lib" in fp and "name" in fp:
            path = _FP_ROOT / f'{fp["lib"]}.pretty' / f'{fp["name"]}.kicad_mod'
            if not path.is_file():
                errs.append(f"footprints[{t}]: footprint file not found: {path.relative_to(_REPO)}")

    # Parts: required fields, unique slugs, footprint files exist when declared.
    slugs: set[str] = set()
    for p in parts():
        slug = p.get("slug", "?")
        for k in _PART_REQUIRED:
            if not p.get(k):
                errs.append(f"part '{slug}': missing required field '{k}'")
        if slug in slugs:
            errs.append(f"part: duplicate slug '{slug}'")
        slugs.add(slug)
        fpr = p.get("footprint")
        if fpr:
            if not (fpr.get("lib") and fpr.get("name")):
                errs.append(f"part '{slug}': footprint needs both lib and name")
            else:
                path = _FP_ROOT / f'{fpr["lib"]}.pretty' / f'{fpr["name"]}.kicad_mod'
                if not path.is_file():
                    errs.append(f"part '{slug}': footprint file not found: {path.relative_to(_REPO)}")
        ds = p.get("datasheet")
        if ds and not ds.get("url"):
            errs.append(f"part '{slug}': datasheet present but has no url")

    return errs


def _main(argv: list[str]) -> int:
    if "--list" in argv:
        print("# Footprint bindings (panel_type -> rel_path  @ ox,oy)")
        for t, (rel, ox, oy) in footprint_map().items():
            print(f"  {t:14} {rel}  @ {ox},{oy}")
        print(f"\n# Parts ({len(parts())})")
        for p in parts():
            fpr = p.get("footprint") or {}
            fp = f'{fpr.get("lib","-")}/{fpr.get("name","-")}' if fpr else "(no footprint)"
            print(f"  {p.get('slug',''):24} {p.get('mpn',''):28} {fp}")
        return 0

    # default / --check
    errs = validate()
    if errs:
        print("COMPONENTS CHECK — FAIL:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"COMPONENTS CHECK — OK ({len(_footprints_raw())} footprint bindings, {len(parts())} parts).")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
