"""Generate the brand images (favicons, app icons, OG image) into site/static/.

Run from the repo root: python scripts/make_brand_assets.py [NAME ...] [--out DIR]
With NAMEs (e.g. favicon.ico) only those files are written; with none, all are.
Needs Pillow. Uses the first installed serif from FONT_CANDIDATES (found with
fc-match), so output depends on the machine's fonts; the PNGs are committed.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "site" / "static"
PAPER, AMBER, TEXT, MUTED = "#f7f4ee", "#a8701c", "#1c2430", "#5b6573"
FONT_CANDIDATES = ["Iowan Old Style", "Palatino", "URW Palladio", "TeX Gyre Pagella", "DejaVu Serif"]


def find_font() -> str:
    for family in FONT_CANDIDATES:
        # fc-match always returns something, so require the family to match.
        out = subprocess.run(["fc-match", "-f", "%{family}|%{file}", family + ":style=Regular"],
                             capture_output=True, text=True).stdout
        fam, _, path = out.partition("|")
        if path and family.lower() in fam.lower():
            return path
    raise SystemExit("no serif font found among " + ", ".join(FONT_CANDIDATES))


def wordmark_icon(size: int, font_path: str, fill_ratio: float = 0.72) -> Image.Image:
    img = Image.new("RGB", (size, size), PAPER)
    d = ImageDraw.Draw(img)
    fs = size
    while True:
        font = ImageFont.truetype(font_path, fs)
        l, t, r, b = d.textbbox((0, 0), "a42r", font=font)
        if r - l <= size * fill_ratio or fs <= 4:
            break
        fs -= 1
    d.text(((size - (r - l)) / 2 - l, (size - (b - t)) / 2 - t), "a42r", font=font, fill=AMBER)
    return img


def og_image(font_path: str) -> Image.Image:
    img = Image.new("RGB", (1200, 630), PAPER)
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(font_path, 220)
    l, t, r, b = d.textbbox((0, 0), "a42r", font=big)
    d.text((100 - l, 150 - t), "a42r", font=big, fill=AMBER)
    sub = ImageFont.truetype(font_path, 40)
    d.text((100, 150 + (b - t) + 50), "Projects — Things I build, use, and give away.",
           font=sub, fill=TEXT)
    data = yaml.safe_load((ROOT / "site" / "projects.yaml").read_text(encoding="utf-8"))
    accents = [p["accent"] for p in data["projects"] if p["status"] == "live"][:5]
    for i, colour in enumerate(accents):
        x = 100 + i * 64
        d.rounded_rectangle((x, 540, x + 48, 570), radius=6, fill=colour)
    return img


ICO_SIZES = (16, 32, 48)


def favicon_ico(font_path: str, path: Path) -> None:
    """A multi-size favicon.ico (16, 32, 48), each size drawn at its own scale."""
    frames = [wordmark_icon(s, font_path, 0.92) for s in ICO_SIZES]
    frames[-1].save(path, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])


OUTPUTS = {
    "icon-512.png": lambda f, p: wordmark_icon(512, f).save(p),
    "icon-192.png": lambda f, p: wordmark_icon(192, f).save(p),
    "apple-touch-icon.png": lambda f, p: wordmark_icon(180, f, 0.8).save(p),
    "favicon-32.png": lambda f, p: wordmark_icon(32, f, 0.92).save(p),
    "favicon.ico": favicon_ico,
    "og-image.png": lambda f, p: og_image(f).save(p, optimize=True),
}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate the a42r brand images.")
    ap.add_argument("names", nargs="*", metavar="NAME",
                    help=f"files to write (default: all of {', '.join(OUTPUTS)})")
    ap.add_argument("--out", type=Path, default=STATIC, help="output directory (default: site/static)")
    args = ap.parse_args(argv)
    unknown = [n for n in args.names if n not in OUTPUTS]
    if unknown:
        ap.error(f"unknown file(s): {', '.join(unknown)}")
    font = find_font()
    print("font:", font)
    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.names or OUTPUTS:
        OUTPUTS[name](font, args.out / name)
        print(args.out / name)


if __name__ == "__main__":
    main()
