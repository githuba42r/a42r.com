"""Generate the brand PNGs (favicons, app icons, OG image) into site/static/.

Run from the repo root: python scripts/make_brand_assets.py
Needs Pillow. Uses the first installed serif from FONT_CANDIDATES (found with
fc-match), so output depends on the machine's fonts; the PNGs are committed.
"""
from __future__ import annotations

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


def main() -> None:
    font = find_font()
    print("font:", font)
    big = wordmark_icon(512, font)
    big.save(STATIC / "icon-512.png")
    wordmark_icon(192, font).save(STATIC / "icon-192.png")
    wordmark_icon(180, font, 0.8).save(STATIC / "apple-touch-icon.png")
    wordmark_icon(32, font, 0.92).save(STATIC / "favicon-32.png")
    og_image(font).save(STATIC / "og-image.png", optimize=True)


if __name__ == "__main__":
    main()
