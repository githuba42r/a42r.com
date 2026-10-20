#!/usr/bin/env python3
"""Import every IMAGE_SOURCES entry into site/static/img and write sizes.json."""
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


def main() -> None:
    accents = {p.image: p.accent for p in load_site(ROOT / "site" / "projects.yaml").projects if p.image}
    sizes: dict[str, dict[str, list[int]]] = {}
    for base, source in IMAGE_SOURCES.items():
        bg = tint(accents[base]) if base in accents else "#ffffff"
        if source.startswith("https://"):
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "download"
                req = urllib.request.Request(source, headers={"User-Agent": "a42r-import/1"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    src.write_bytes(r.read())
                sizes[base] = import_image(src, DEST, base, bg=bg)
        else:
            sizes[base] = import_image(Path(source), DEST, base, bg=bg)
        for suf in ("-640.webp", "-1280.webp", "-640.jpg"):
            print(DEST / f"{base}{suf}")
    (DEST / "sizes.json").write_text(json.dumps(sizes, indent=2, sort_keys=True) + "\n")
    print(DEST / "sizes.json")


if __name__ == "__main__":
    main()
