"""Band image processing and monogram fallback tiles."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

_BASE = "/home/philg/src/AndroidStudioProjects/"

IMAGE_SOURCES: dict[str, str] = {
    "pev-plugshare": _BASE + "PEVPlugShare/website/images/og-card.jpg",
    "destination-eta": _BASE + "DestinationETATracker/website/images/og-image.jpg",
    "euc-world-osmand": _BASE + "OSM-EUC-World/feature_graphic_1024x500.png",
    "scooter-parking-crimes": _BASE
    + "UnsafeRideshareParkingReports/play-store/feature-graphic-1024x500.png",
    "mdrender": _BASE + "MDRender/website/images/app-markdown.png",
    "imagetools": "https://image-tools.a42r.com/images/og-image.jpg",
}


def _flatten(im: Image.Image) -> Image.Image:
    """Convert to RGB, compositing any transparency onto white."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return im.convert("RGB")


def _fit(im: Image.Image, width: int) -> Image.Image:
    if im.width <= width:
        return im.copy()
    height = max(1, round(im.height * width / im.width))
    return im.resize((width, height), Image.LANCZOS)


def import_image(src: Path, dest_dir: Path, base: str) -> None:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as opened:
        im = _flatten(opened)
    small = _fit(im, 640)
    large = _fit(im, 1280)
    small.save(dest_dir / f"{base}-640.webp", "WEBP", quality=82)
    large.save(dest_dir / f"{base}-1280.webp", "WEBP", quality=82)
    small.save(dest_dir / f"{base}-640.jpg", "JPEG", quality=85, progressive=True)


def _initials(name: str) -> str:
    words = name.split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def monogram_svg(name: str, accent: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" '
        f'role="img" aria-label="{escape(name, {chr(34): "&quot;"})}">'
        f'<rect width="640" height="360" fill="{escape(accent)}"/>'
        '<text x="320" y="180" fill="#ffffff" text-anchor="middle" '
        'dominant-baseline="central" font-size="150" '
        'font-family="Iowan Old Style, Palatino, Palatino Linotype, Georgia, serif">'
        f"{escape(_initials(name))}</text></svg>"
    )
