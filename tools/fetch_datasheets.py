"""fetch_datasheets.py — cache component datasheet PDFs + record integrity metadata.

Each components/parts/<slug>/component.yaml has a `datasheet: {url, version}`. This
tool downloads PDF datasheets into a GITIGNORED cache and records `sha256` + `bytes`
back into component.yaml (committed), so the BOM has verifiable datasheet integrity
without committing copyrighted binaries.

Only PDF URLs are cached. Supplier/landing pages (version: "supplier page") are
skipped — there is no manufacturer PDF for that panel hardware.

  python3 tools/fetch_datasheets.py            # download missing PDFs, write sha256/bytes
  python3 tools/fetch_datasheets.py --force    # re-download everything
  python3 tools/fetch_datasheets.py --check    # offline: metadata complete + (if cached) sha matches
  python3 tools/fetch_datasheets.py --verify   # online: re-download, fail on sha drift

CI uses --check (offline, no network, no cached PDFs required).
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parent.parent
_PARTS = _REPO / "components" / "parts"
_CACHE = _REPO / "components" / "datasheets"
_UA = "Mozilla/5.0 (X11; Linux x86_64) POGO-datasheet-fetch/1.0"


def _parts():
    for f in sorted(_PARTS.glob("*/component.yaml")):
        yield f, yaml.safe_load(f.read_text())


def _is_pdf(ds: dict) -> bool:
    url = (ds or {}).get("url", "")
    return url.lower().endswith(".pdf")


def _write_back(path: Path, doc: dict) -> None:
    lines = path.read_text().split("\n")
    comment = lines[0] + "\n" if lines and lines[0].startswith("#") else ""
    out = yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True, width=100)
    path.write_text(comment + out)


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (trusted vendor URLs)
        return r.read()


def fetch(force: bool) -> int:
    _CACHE.mkdir(parents=True, exist_ok=True)
    ok = fail = skip = 0
    for path, doc in _parts():
        ds = doc.get("datasheet") or {}
        slug = doc.get("slug", path.parent.name)
        if not _is_pdf(ds):
            skip += 1
            continue
        cached = _CACHE / f"{slug}.pdf"
        if cached.exists() and not force and ds.get("sha256"):
            ok += 1
            continue
        try:
            data = _download(ds["url"])
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {slug}: {type(e).__name__} {e}")
            fail += 1
            continue
        if not data.startswith(b"%PDF"):
            print(f"  FAIL {slug}: response is not a PDF ({len(data)} bytes)")
            fail += 1
            continue
        cached.write_bytes(data)
        ds["sha256"] = hashlib.sha256(data).hexdigest()
        ds["bytes"] = len(data)
        doc["datasheet"] = ds
        _write_back(path, doc)
        print(f"  ok   {slug}: {len(data)} bytes  sha256={ds['sha256'][:12]}…")
        ok += 1
    print(f"\nfetched/ok={ok}  failed={fail}  skipped(non-PDF)={skip}")
    return 1 if fail else 0


def check(verify_online: bool) -> int:
    errs = []
    for path, doc in _parts():
        ds = doc.get("datasheet") or {}
        slug = doc.get("slug", path.parent.name)
        if not _is_pdf(ds):
            continue
        if not ds.get("sha256") or not ds.get("bytes"):
            errs.append(f"{slug}: PDF datasheet missing sha256/bytes (run fetch_datasheets.py)")
            continue
        cached = _CACHE / f"{slug}.pdf"
        if verify_online:
            try:
                data = _download(ds["url"])
                h = hashlib.sha256(data).hexdigest()
                if h != ds["sha256"]:
                    errs.append(f"{slug}: sha256 drift (recorded {ds['sha256'][:12]}… got {h[:12]}…)")
            except Exception as e:  # noqa: BLE001
                errs.append(f"{slug}: re-download failed: {type(e).__name__} {e}")
        elif cached.exists():
            h = hashlib.sha256(cached.read_bytes()).hexdigest()
            if h != ds["sha256"]:
                errs.append(f"{slug}: cached PDF sha256 mismatch vs recorded")
    if errs:
        print("DATASHEET CHECK — FAIL:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("DATASHEET CHECK — OK (metadata complete; cached PDFs match where present).")
    return 0


def _main(argv: list[str]) -> int:
    if "--check" in argv:
        return check(verify_online=False)
    if "--verify" in argv:
        return check(verify_online=True)
    return fetch(force="--force" in argv)


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
