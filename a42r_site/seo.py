"""Structured data, sitemap and robots for the a42r site."""
from __future__ import annotations

import json
from xml.sax.saxutils import escape as _xml_escape

from a42r_site.data import Project, Site

GITHUB = "https://github.com/githuba42r"
ROBOTS = "User-agent: *\nAllow: /\nSitemap: https://www.a42r.com/sitemap.xml\n"


def _breadcrumbs(site: Site, page) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": label, "item": site.base_url + href}
            for i, (label, href) in enumerate(page.breadcrumbs, 1)
        ],
    }


def _app(p: Project) -> dict:
    app = {
        "@type": "SoftwareApplication",
        "name": p.name,
        "description": p.summary,
        "operatingSystem": p.os,
        "applicationCategory": p.app_category,
    }
    link = p.url or p.repo_url
    if link:
        app["url"] = link
    return app


def jsonld_for(site: Site, page) -> list[dict]:
    """JSON-LD documents for a page; none for the 404."""
    if page.path == "/":
        return [
            {"@context": "https://schema.org", "@type": "Organization", "name": site.name,
             "url": site.base_url, "logo": site.base_url + "/icon-512.png", "sameAs": [GITHUB]},
            {"@context": "https://schema.org", "@type": "WebSite", "name": site.name,
             "url": site.base_url, "description": site.summary, "inLanguage": "en-AU"},
        ]
    if page.category is not None:
        return [
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": page.title,
             "description": page.description, "url": site.base_url + page.path,
             "mainEntity": {
                 "@type": "ItemList",
                 "itemListElement": [{"@type": "ListItem", "position": i, "item": _app(p)}
                                     for i, p in enumerate(page.projects, 1)],
             }},
            _breadcrumbs(site, page),
        ]
    if page.path == "/privacy/":
        return [_breadcrumbs(site, page)]
    return []


def jsonld_script(doc: dict) -> str:
    """Serialise one document for a <script type=application/ld+json> body."""
    return json.dumps(doc, ensure_ascii=False).replace("</", "<\\/")


def sitemap_xml(urls: list[str], lastmod: str) -> str:
    rows = "".join(
        f"  <url>\n    <loc>{_xml_escape(u)}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>\n"
        for u in urls
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "</urlset>\n")
