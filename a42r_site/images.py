"""Band image processing and monogram fallback tiles."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps

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


def _flatten(im: Image.Image, bg: str = "#ffffff") -> Image.Image:
    """Convert to RGB, compositing any transparency onto bg."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, bg)
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return im.convert("RGB")


def _to_16x9(im: Image.Image, bg: str) -> Image.Image:
    """Normalise to 16:9: centre-crop landscape, letterbox portrait on bg."""
    w, h = im.size
    if w / h >= 1.2:
        if w * 9 > h * 16:  # wider than 16:9: crop width
            cw = round(h * 16 / 9)
            left = (w - cw) // 2
            return im.crop((left, 0, left + cw, h))
        ch = round(w * 9 / 16)  # between 1.2 and 16:9: crop height
        top = (h - ch) // 2
        return im.crop((0, top, w, top + ch))
    cw = round(h * 16 / 9)
    canvas = Image.new("RGB", (cw, h), bg)
    canvas.paste(im, ((cw - w) // 2, 0))
    return canvas


def tint(accent: str, amount: float = 0.15) -> str:
    """Mix `amount` of accent into white, returned as #rrggbb."""
    rgb = [int(accent[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(255 * (1 - amount) + c * amount):02x}" for c in rgb)


def import_image(
    src: Path, dest_dir: Path, base: str, bg: str = "#ffffff"
) -> dict[str, list[int]]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as opened:
        im = _flatten(ImageOps.exif_transpose(opened), bg)
    band = _to_16x9(im, bg)
    lw = min(1280, band.width)
    lw -= lw % 2
    lh = round(lw * 9 / 16)
    small = band.resize((640, 360), Image.LANCZOS)
    large = band if band.size == (lw, lh) else band.resize((lw, lh), Image.LANCZOS)
    small.save(dest_dir / f"{base}-640.webp", "WEBP", quality=82)
    large.save(dest_dir / f"{base}-1280.webp", "WEBP", quality=82)
    small.save(dest_dir / f"{base}-640.jpg", "JPEG", quality=85, progressive=True)
    return {"640": [640, 360], "1280": [lw, lh]}


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
