#!/usr/bin/env python3
"""Import IMAGE_SOURCES entries into site/static/img and update sizes.json.

Usage:
    scripts/import_images.py            # re-import every source, rewrite sizes.json
    scripts/import_images.py BASE ...   # import only these bases, merge into sizes.json

Local sources are read from A42R_PROJECTS_ROOT (default ~/src/AndroidStudioProjects).
"""
import argparse
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a42r_site.data import load_site  # noqa: E402
from a42r_site.images import IMAGE_SOURCES, import_image, tint  # noqa: E402

DEST = ROOT / "site" / "static" / "img"
PROJECTS = ROOT / "site" / "projects.yaml"


def _import_one(base: str, source: str, dest: Path, bg: str) -> dict[str, list[int]]:
    if source.startswith("https://"):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "download"
            req = urllib.request.Request(source, headers={"User-Agent": "a42r-import/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                src.write_bytes(r.read())
            return import_image(src, dest, base, bg=bg)
    return import_image(Path(source), dest, base, bg=bg)


def run(bases: list[str], sources: dict[str, str] = IMAGE_SOURCES, dest: Path = DEST,
        projects: Path = PROJECTS) -> dict[str, dict[str, list[int]]]:
    """Import `bases` (all sources when empty) and return the new sizes.json content.

    With named bases the existing sizes.json is kept and only those entries are
    replaced; with none it is rewritten from scratch.
    """
    unknown = [b for b in bases if b not in sources]
    if unknown:
        raise SystemExit(f"unknown image base(s): {', '.join(unknown)} "
                         f"(known: {', '.join(sorted(sources))})")
    accents = {p.image: p.accent for p in load_site(projects).projects if p.image}
    sizes_file = dest / "sizes.json"
    sizes: dict[str, dict[str, list[int]]] = {}
    if bases and sizes_file.is_file():
        sizes = json.loads(sizes_file.read_text(encoding="utf-8"))
    for base in bases or list(sources):
        bg = tint(accents[base]) if base in accents else "#ffffff"
        sizes[base] = _import_one(base, sources[base], dest, bg)
        for suf in ("-640.webp", "-1280.webp", "-640.jpg"):
            print(dest / f"{base}{suf}")
    sizes_file.write_text(json.dumps(sizes, indent=2, sort_keys=True) + "\n")
    print(sizes_file)
    return sizes


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bases", nargs="*", help="image bases from IMAGE_SOURCES (default: all)")
    run(ap.parse_args(argv).bases)


if __name__ == "__main__":
    main()
