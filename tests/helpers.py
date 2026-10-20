"""Shared helpers for tests that read the built site."""
from __future__ import annotations

import re
from pathlib import Path

from markupsafe import escape as _esc

ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = ROOT / "site"


def escape(s: str) -> str:
    """HTML-escape exactly as the Jinja templates do."""
    return str(_esc(s))


def read(out: Path, relpath: str) -> str:
    """Text of a built file, relative to the output directory."""
    return (Path(out) / relpath).read_text(encoding="utf-8")


def band(html: str, name: str) -> str:
    """The <article>...</article> slice whose <h2> holds exactly `name`."""
    for m in re.finditer(r"<article\b.*?</article>", html, re.S):
        if re.search(r"<h2\b[^>]*>\s*" + re.escape(escape(name)) + r"\s*</h2>", m.group(0)):
            return m.group(0)
    raise AssertionError(f"no band for {name!r}")


def band_names(html: str) -> list[str]:
    """Project names of every band on a page, in order."""
    out = []
    for m in re.finditer(r"<article\b.*?</article>", html, re.S):
        h2 = re.search(r"<h2\b[^>]*>\s*(.*?)\s*</h2>", m.group(0), re.S)
        if h2:
            out.append(h2.group(1))
    return out
