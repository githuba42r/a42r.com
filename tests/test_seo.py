import json
import re
import shutil
import struct
from html import unescape

import pytest
import yaml

from helpers import SITE_SRC, band_names, read

BASE = "https://www.a42r.com"
PAGES = ["/", "/android/", "/browser-extensions/", "/web-apps/", "/desktop-self-hosted/",
         "/privacy/"]


def indexable(built):
    from a42r_site.build import pages_for
    from a42r_site.data import load_site

    return [p for p in pages_for(load_site(SITE_SRC / "projects.yaml")) if p.path != "/404.html"]


def meta(html, attr, name):
    m = re.search(r'<meta %s="%s" content="([^"]*)"' % (attr, re.escape(name)), html)
    assert m, f"missing {name}"
    return unescape(m.group(1))


def ldjson_blocks(html):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)


def test_titles_and_descriptions_unique(built):
    pages = indexable(built)
    assert len(pages) == 9
    titles = [p.title for p in pages]
    descs = [p.description for p in pages]
    assert len(set(titles)) == 9 and len(set(descs)) == 9
    assert all(len(t) <= 60 for t in titles), titles
    assert all(120 <= len(d) <= 160 for d in descs), [len(d) for d in descs]


def test_canonical_and_og(built):
    for p in indexable(built):
        html = read(built, p.path.strip("/") + "/index.html" if p.path != "/" else "index.html")
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
        assert canon == BASE + p.path == meta(html, "property", "og:url")
        assert meta(html, "property", "og:image") == BASE + "/og-image.png"
        assert meta(html, "property", "og:image:width") == "1200"
        assert meta(html, "property", "og:image:height") == "630"
        assert meta(html, "property", "og:image:alt")
        assert meta(html, "property", "og:type") == "website"
        assert meta(html, "property", "og:site_name") == "a42r"
        assert meta(html, "property", "og:title") == p.title
        assert meta(html, "property", "og:description") == p.description
        assert meta(html, "name", "twitter:card") == "summary_large_image"
        assert meta(html, "name", "theme-color") == "#f7f4ee"
        assert 'rel="manifest"' in html and "favicon.svg" in html and "apple-touch-icon" in html


def test_jsonld_parses_and_counts(built):
    for p in indexable(built):
        if p.category is None:
            continue
        html = read(built, p.path.strip("/") + "/index.html")
        blocks = [json.loads(b) for b in ldjson_blocks(html)]
        cp = next(b for b in blocks if b["@type"] == "CollectionPage")
        items = cp["mainEntity"]["itemListElement"]
        assert len(items) == len(band_names(html)) == len(p.projects)
        assert [i["position"] for i in items] == list(range(1, len(items) + 1))
        assert all(i["item"]["@type"] == "SoftwareApplication" for i in items)
        assert any(b["@type"] == "BreadcrumbList" for b in blocks)


def test_jsonld_survives_quotes(tmp_path):
    src = tmp_path / "site"
    shutil.copytree(SITE_SRC, src)
    data = yaml.safe_load((src / "projects.yaml").read_text(encoding="utf-8"))
    nasty = '"I\'ll be there at 4:42" & on time </script>'
    for pr in data["projects"]:
        if pr["slug"] == "destination-eta":
            pr["summary"] = nasty
    (src / "projects.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    from a42r_site.build import build

    out = tmp_path / "out"
    build(src, out)
    html = read(out, "android/index.html")
    blocks = ldjson_blocks(html)
    assert blocks
    for b in blocks:
        assert "</script>" not in b
        json.loads(b)
    assert any(nasty in json.dumps(json.loads(b), ensure_ascii=False).replace('\\"', '"')
               or "I'll be there" in b for b in blocks)
    # a page whose description carries the text must escape attributes
    assert "&#34;" in html or "&quot;" in html
    for m in re.finditer(r'<meta [^>]*content="([^"]*)"', html):
        assert '"' not in m.group(1)


def test_home_jsonld_org(built):
    blocks = [json.loads(b) for b in ldjson_blocks(read(built, "index.html"))]
    org = next(b for b in blocks if b["@type"] == "Organization")
    assert org["name"] == "a42r" and org["url"] == BASE
    assert org["logo"] == BASE + "/icon-512.png"
    assert org["sameAs"] == ["https://github.com/githuba42r"]
    assert any(b["@type"] == "WebSite" for b in blocks)


def test_privacy_jsonld(built):
    blocks = [json.loads(b) for b in ldjson_blocks(read(built, "privacy/index.html"))]
    assert [b["@type"] for b in blocks] == ["BreadcrumbList"]


def test_sitemap_and_robots(built):
    sm = read(built, "sitemap.xml")
    assert sm.count("<url>") == 9 and "404" not in sm
    assert f"<loc>{BASE}/</loc>" in sm and f"<loc>{BASE}/android/</loc>" in sm
    assert re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", sm)
    assert "Sitemap: https://www.a42r.com/sitemap.xml" in read(built, "robots.txt")
    assert read(built, "robots.txt").startswith("User-agent: *\nAllow: /\n")


def test_404_noindex(built):
    html = read(built, "404.html")
    assert '<meta name="robots" content="noindex">' in html
    assert 'rel="canonical"' not in html


def test_brand_assets_present(built):
    def png_size(name):
        data = (built / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        return struct.unpack(">II", data[16:24])

    assert png_size("og-image.png") == (1200, 630)
    assert png_size("icon-512.png") == (512, 512)
    assert png_size("icon-192.png") == (192, 192)
    assert png_size("apple-touch-icon.png") == (180, 180)
    assert png_size("favicon-32.png") == (32, 32)
    assert (built / "favicon.svg").read_text(encoding="utf-8").lstrip().startswith("<svg")
    assert json.loads(read(built, "site.webmanifest"))["name"] == "a42r"


def test_no_personal_name(built):
    exts = {".html", ".xml", ".txt", ".json", ".webmanifest", ".svg", ".css"}
    files = [f for f in built.rglob("*") if f.is_file() and f.suffix in exts]
    assert len(files) > 10
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert "Phil" not in text and "Gersekowski" not in text, f
