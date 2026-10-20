#!/usr/bin/env python3
"""Import every IMAGE_SOURCES entry into site/static/img."""
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a42r_site.images import IMAGE_SOURCES, import_image  # noqa: E402

DEST = ROOT / "site" / "static" / "img"


def main() -> None:
    for base, source in IMAGE_SOURCES.items():
        if source.startswith("https://"):
            tmp = Path(tempfile.mkdtemp())
            src = tmp / "download"
            req = urllib.request.Request(source, headers={"User-Agent": "a42r-import/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                src.write_bytes(r.read())
        else:
            src = Path(source)
        import_image(src, DEST, base)
        for suf in ("-640.webp", "-1280.webp", "-640.jpg"):
            print(DEST / f"{base}{suf}")


if __name__ == "__main__":
    main()
