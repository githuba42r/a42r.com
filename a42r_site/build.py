"""Assemble the site's pages and render them to static files."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from a42r_site.data import Category, Project, Site, load_site
from a42r_site.images import monogram_svg, tint
from a42r_site.seo import ROBOTS, jsonld_for, jsonld_script, sitemap_xml

LINE = "#e4ddd0"  # border colour from the global palette
MARKER = ".a42r-build"  # marks a directory as build output that may be emptied


class BuildError(RuntimeError):
    """Raised when the build refuses to run, e.g. an unsafe output directory."""


@dataclass
class Page:
    path: str
    template: str
    title: str
    description: str
    h1: str
    projects: list[Project] = field(default_factory=list)
    category: Category | None = None
    breadcrumbs: list[tuple[str, str]] = field(default_factory=list)


def _live_first(projects) -> list[Project]:
    return [p for p in projects if p.status == "live"] + [p for p in projects if p.status == "soon"]


def pages_for(site: Site) -> list[Page]:
    """Home, one page per platform and purpose, privacy and 404."""
    pages = [Page("/", "home.html", site.home_title, site.home_description, "Projects",
                  _live_first(site.projects))]
    for cat in site.platforms + site.purposes:
        pages.append(Page(
            f"/{cat.slug}/", "listing.html", cat.title, cat.description, cat.name,
            site.projects_in(cat.slug), cat, [("Home", "/"), (cat.name, f"/{cat.slug}/")],
        ))
    pages.append(Page("/privacy/", "privacy.html", site.privacy_title, site.privacy_description,
                      "Privacy", breadcrumbs=[("Home", "/"), ("Privacy", "/privacy/")]))
    pages.append(Page(
        "/404.html", "404.html", "Page not found — a42r",
        "This page isn't on the a42r site. Head back to the home page, or browse "
        "the projects by platform or by purpose.",
        "Page not found",
    ))
    return pages


def _mix(fg: str, bg: str, amount: float) -> str:
    """Mix `amount` of fg into bg (both #rrggbb), like CSS color-mix in sRGB."""
    a = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(y * (1 - amount) + x * amount):02x}" for x, y in zip(a, b))


def _band_style(accent: str) -> str:
    return f"--accent:{accent};--band-bg:{tint(accent, 0.12)};--band-line:{_mix(accent, LINE, 0.22)}"


def _output_file(out: Path, path: str) -> Path:
    if path.endswith(".html"):
        return out / path.lstrip("/")
    return out / path.strip("/") / "index.html"


def _empty_dir(out: Path, src: Path) -> None:
    """Empty `out` for a fresh build, or raise BuildError having deleted nothing.

    Only a directory that is missing, empty, or marked by an earlier build
    with MARKER may be emptied, and never one that is a symlink, a git
    checkout, the source tree (or a parent of it), the filesystem root or $HOME.
    """
    if out.is_symlink():
        raise BuildError(f"refusing to build into {out}: it is a symlink")
    out_r, src_r = out.resolve(), src.resolve()
    if out_r == src_r or out_r in src_r.parents:
        raise BuildError(f"refusing to empty {out}: it is or contains the site source {src}")
    if out_r == Path(out_r.anchor) or out_r == Path.home().resolve():
        raise BuildError(f"refusing to empty {out}: it is the filesystem root or your home directory")
    if out.exists():
        if not out.is_dir():
            raise BuildError(f"refusing to build into {out}: it is not a directory")
        if (out / ".git").exists():
            raise BuildError(f"refusing to empty {out}: it contains .git")
        children = list(out.iterdir())
        if children and not (out / MARKER).is_file():
            raise BuildError(
                f"refusing to empty {out}: it is not empty and has no {MARKER} marker "
                "from an earlier build; pick an empty directory or remove it yourself"
            )
        for child in children:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    (out / MARKER).write_text("Built by a42r_site.build; this directory is emptied on every build.\n",
                              encoding="utf-8")


def build(src: Path = Path("site"), out: Path = Path("website"), lastmod: str | None = None) -> list[Page]:
    """Empty `out`, copy `src/static/` into it and render every page.

    `lastmod` (YYYY-MM-DD) goes in the sitemap; it defaults to today in UTC.
    """
    lastmod = lastmod or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    src, out = Path(src), Path(out)
    site = load_site(src / "projects.yaml")
    sizes = json.loads((src / "static" / "img" / "sizes.json").read_text(encoding="utf-8"))
    for p in site.projects:
        if p.image and p.image not in sizes:
            raise ValueError(f"project '{p.slug}': image '{p.image}' is missing from img/sizes.json")

    env = Environment(
        loader=FileSystemLoader(src / "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals.update(
        site=site,
        categories={c.slug: c for c in site.platforms + site.purposes},
        img_sizes=sizes,
        monogram=lambda p: Markup(monogram_svg(p.name, p.accent)),
        band_style=_band_style,
        asset_version=hashlib.sha256((src / "static" / "styles.css").read_bytes()).hexdigest()[:10],
    )

    _empty_dir(out, src)
    shutil.copytree(src / "static", out, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("sizes.json"))
    pages = pages_for(site)
    for page in pages:
        docs = [Markup(jsonld_script(d)) for d in jsonld_for(site, page)]
        html = env.get_template(page.template).render(page=page, jsonld=docs)
        dest = _output_file(out, page.path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    urls = [site.base_url + p.path for p in pages if p.path != "/404.html"]
    (out / "sitemap.xml").write_text(sitemap_xml(urls, lastmod), encoding="utf-8")
    (out / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    return pages


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m a42r_site.build", description="Build the a42r site.")
    ap.add_argument("--src", type=Path, default=Path("site"), help="site source directory (default: site)")
    ap.add_argument("--out", type=Path, default=Path("website"), help="output directory (default: website)")
    args = ap.parse_args(argv)
    pages = build(args.src, args.out)
    print(f"built {len(pages)} pages into {args.out}")


if __name__ == "__main__":
    main()
