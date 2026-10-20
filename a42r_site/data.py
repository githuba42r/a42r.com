"""Typed, validated project data for the a42r portfolio site."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

PAPER = "#f7f4ee"
MIN_BUTTON_CONTRAST = 4.5  # white button text on the accent
MIN_ACCENT_CONTRAST = 3.0  # accent on paper (borders, swatches, large text)
STATUSES = ("live", "soon")


class SiteDataError(ValueError):
    """Raised when projects.yaml is invalid; the message names the offender."""


@dataclass(frozen=True)
class Category:
    slug: str
    kind: Literal["platform", "purpose"]
    name: str
    title: str
    description: str
    intro: str


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    status: Literal["live", "soon"]
    url: str | None
    repo_url: str | None
    summary: str
    platforms: tuple[str, ...]
    purposes: tuple[str, ...]
    accent: str
    image: str | None
    os: str
    app_category: str


@dataclass(frozen=True)
class Site:
    base_url: str
    name: str
    tagline: str
    summary: str
    home_title: str
    home_description: str
    privacy_title: str
    privacy_description: str
    platforms: tuple[Category, ...]
    purposes: tuple[Category, ...]
    projects: tuple[Project, ...]

    def projects_in(self, cat_slug: str) -> list[Project]:
        """Projects in a platform or purpose, live first then soon, YAML order within each."""
        found = [p for p in self.projects if cat_slug in p.platforms or cat_slug in p.purposes]
        return [p for p in found if p.status == "live"] + [p for p in found if p.status == "soon"]


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    chans = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.x contrast ratio between two #rrggbb colours."""
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _req(mapping: dict, key: str, where: str):
    if not isinstance(mapping, dict) or mapping.get(key) in (None, ""):
        raise SiteDataError(f"{where}: missing required field '{key}'")
    return mapping[key]


def _slug_list(row: dict, key: str, where: str) -> tuple[str, ...]:
    """A required, non-empty YAML list of category slugs (a bare string is rejected)."""
    if key not in row or row[key] is None:
        raise SiteDataError(f"{where}: missing required field '{key}'")
    vals = row[key]
    if not isinstance(vals, list):
        raise SiteDataError(f"{where}: field '{key}' must be a list like [slug, ...], got {vals!r}")
    if not vals:
        raise SiteDataError(f"{where}: field '{key}' must list at least one category")
    for v in vals:
        if not isinstance(v, str):
            raise SiteDataError(f"{where}: field '{key}' must hold category slugs, got {v!r}")
    return tuple(vals)


def _load_categories(rows, kind: str) -> tuple[Category, ...]:
    if not rows:
        raise SiteDataError(f"at least one {kind} category is required")
    cats, seen = [], set()
    for row in rows:
        slug = _req(row, "slug", f"{kind} category")
        where = f"{kind} category '{slug}'"
        if slug in seen:
            raise SiteDataError(f"{where}: duplicate slug")
        seen.add(slug)
        cats.append(Category(
            slug=slug, kind=kind, name=_req(row, "name", where),
            title=_req(row, "title", where), description=_req(row, "description", where),
            intro=_req(row, "intro", where).strip(),
        ))
    return tuple(cats)


def _load_project(row: dict, platform_slugs: set[str], purpose_slugs: set[str]) -> Project:
    slug = _req(row, "slug", "project")
    where = f"project '{slug}'"
    status = _req(row, "status", where)
    if status not in STATUSES:
        raise SiteDataError(f"{where}: invalid status '{status}' (expected one of {', '.join(STATUSES)})")
    url = row.get("url")
    if status == "live" and not url:
        raise SiteDataError(f"{where}: live project requires 'url'")
    if status == "soon" and url:
        raise SiteDataError(f"{where}: coming-soon project must not set 'url'")
    platforms = _slug_list(row, "platforms", where)
    purposes = _slug_list(row, "purposes", where)
    for field, vals, known in (("platforms", platforms, platform_slugs), ("purposes", purposes, purpose_slugs)):
        for v in vals:
            if v not in known:
                raise SiteDataError(f"{where}: unknown {field[:-1]} '{v}' in field '{field}'")
    accent = str(_req(row, "accent", where))
    if len(accent) != 7 or not accent.startswith("#"):
        raise SiteDataError(f"{where}: field 'accent' must be #rrggbb, got '{accent}'")
    try:
        on_white = contrast_ratio("#ffffff", accent)
        on_paper = contrast_ratio(accent, PAPER)
    except ValueError:
        raise SiteDataError(f"{where}: field 'accent' must be #rrggbb, got '{accent}'") from None
    if on_white < MIN_BUTTON_CONTRAST:
        raise SiteDataError(f"{where}: accent {accent} contrast with white text is {on_white:.2f}, need {MIN_BUTTON_CONTRAST}")
    if on_paper < MIN_ACCENT_CONTRAST:
        raise SiteDataError(f"{where}: accent {accent} contrast with paper is {on_paper:.2f}, need {MIN_ACCENT_CONTRAST}")
    return Project(
        slug=slug, name=_req(row, "name", where), status=status, url=url or None,
        repo_url=row.get("repo_url") or None, summary=_req(row, "summary", where).strip(),
        platforms=platforms, purposes=purposes, accent=accent, image=row.get("image") or None,
        os=_req(row, "os", where), app_category=_req(row, "app_category", where),
    )


def load_site(path: Path) -> Site:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SiteDataError("projects file must be a mapping")
    s = data.get("site") or {}
    platforms = _load_categories(data.get("platforms"), "platform")
    purposes = _load_categories(data.get("purposes"), "purpose")
    plat_slugs = {c.slug for c in platforms}
    purp_slugs = {c.slug for c in purposes}
    if plat_slugs & purp_slugs:
        raise SiteDataError(f"category slugs shared by platform and purpose: {sorted(plat_slugs & purp_slugs)}")
    projects, seen = [], set()
    for row in data.get("projects") or []:
        p = _load_project(row, plat_slugs, purp_slugs)
        if p.slug in seen:
            raise SiteDataError(f"duplicate project slug '{p.slug}'")
        seen.add(p.slug)
        projects.append(p)
    if not projects:
        raise SiteDataError("at least one project is required")
    return Site(
        base_url=_req(s, "base_url", "site").rstrip("/"), name=_req(s, "name", "site"),
        tagline=_req(s, "tagline", "site"), summary=_req(s, "summary", "site").strip(),
        home_title=_req(s, "home_title", "site"), home_description=_req(s, "home_description", "site"),
        privacy_title=_req(s, "privacy_title", "site"), privacy_description=_req(s, "privacy_description", "site"),
        platforms=platforms, purposes=purposes, projects=tuple(projects),
    )
