import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

from a42r_site.build import build, pages_for
from a42r_site.data import load_site
from helpers import SITE_SRC, band, band_names, escape, read

SITE = load_site(SITE_SRC / "projects.yaml")
CATEGORIES = SITE.platforms + SITE.purposes
PAGE_FILES = ["index.html", *(f"{c.slug}/index.html" for c in CATEGORIES), "privacy/index.html", "404.html"]


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


def tags(html: str) -> list[tuple[str, dict]]:
    p = _Tags()
    p.feed(html)
    return p.tags


def all_pages(out):
    return {f: read(out, f) for f in PAGE_FILES}


def test_pages_for_returns_ten():
    pages = pages_for(SITE)
    assert len(pages) == 10
    assert [p.path for p in pages] == ["/", *(f"/{c.slug}/" for c in CATEGORIES), "/privacy/", "/404.html"]


def test_ten_pages_written(built):
    for f in PAGE_FILES:
        assert (built / f).is_file(), f
    assert (built / "styles.css").is_file()
    assert (built / "img" / "pev-plugshare-640.webp").is_file()


def test_one_h1_each_and_home_copy(built):
    for f, html in all_pages(built).items():
        assert html.count("<h1") == 1, f
        assert '<html lang="en-AU">' in html, f
    home = read(built, "index.html")
    assert home.count("<h1") == 1 and "<h1>Projects</h1>" in home
    assert "Things I build, use, and give away." in home
    assert escape(SITE.summary) in home


def test_titles_and_descriptions(built):
    home = read(built, "index.html")
    assert f"<title>{escape(SITE.home_title)}</title>" in home
    assert f'<meta name="description" content="{escape(SITE.home_description)}">' in home
    priv = read(built, "privacy/index.html")
    assert f"<title>{escape(SITE.privacy_title)}</title>" in priv
    for c in CATEGORIES:
        html = read(built, f"{c.slug}/index.html")
        assert f"<title>{escape(c.title)}</title>" in html
        assert f'<meta name="description" content="{escape(c.description)}">' in html
        assert f"<h1>{escape(c.name)}</h1>" in html
        assert escape(c.intro) in html
    assert "<title>Page not found — a42r</title>" in read(built, "404.html")


def test_every_project_on_home_and_its_categories(built):
    home_names = band_names(read(built, "index.html"))
    assert sorted(home_names) == sorted(escape(p.name) for p in SITE.projects)
    for c in CATEGORIES:
        names = band_names(read(built, f"{c.slug}/index.html"))
        assert names == [escape(p.name) for p in SITE.projects_in(c.slug)], c.slug
        for p in SITE.projects:
            member = c.slug in p.platforms or c.slug in p.purposes
            assert (escape(p.name) in names) == member, (c.slug, p.slug)


def test_breadcrumbs_on_listing_pages(built):
    for c in CATEGORIES:
        html = read(built, f"{c.slug}/index.html")
        crumbs = re.search(r'<nav class="crumbs" aria-label="Breadcrumb">(.*?)</nav>', html, re.S)
        assert crumbs, c.slug
        assert '<a href="/">Home</a>' in crumbs.group(1)
        assert f'aria-current="page">{escape(c.name)}<' in crumbs.group(1)


def test_band_tags_link_to_categories(built):
    pev = band(read(built, "index.html"), "PEV PlugShare")
    assert 'href="/android/"' in pev and 'href="/euc-riding-tools/"' in pev


def test_header_nav_and_footer(built):
    home = read(built, "index.html")
    assert re.search(r'<a class="wordmark" href="/"[^>]*>a42r</a>', home)
    assert "<details" in home and "<summary" in home
    for c in CATEGORIES:
        assert f'href="/{c.slug}/"' in home
    assert "Platforms" in home and "Purposes" in home
    foot = re.search(r"<footer\b.*?</footer>", home, re.S).group(0)
    assert "© a42r" in foot and 'href="https://github.com/githuba42r"' in foot and 'href="/privacy/"' in foot
    assert "<script" not in home


def test_live_vs_soon_actions(built):
    pev = band(read(built, "android/index.html"), "PEV PlugShare")
    assert 'href="https://pevplugshare.a42r.com/"' in pev and "Visit site" in pev
    sud = band(read(built, "other-tools/index.html"), "Sudoku Trainer")
    assert "Coming soon" in sud and 'href="http' not in sud
    moto = band(read(built, "android/index.html"), "MotoEye Remote")
    assert "View on GitHub" in moto and "Visit site" not in moto
    assert 'href="https://github.com/githuba42r/MotoEyeRemote/releases"' in moto


def test_monogram_used_without_image(built):  # Review Focus 3
    ecm = band(read(built, "desktop-self-hosted/index.html"), "EUC Charging Monitor")
    assert "<svg" in ecm and "<img" not in ecm


def test_picture_srcset_from_sizes_json(built):
    home = read(built, "index.html")
    dest = band(home, "Destination ETA")
    assert "/img/destination-eta-640.webp 640w" in dest
    assert "/img/destination-eta-1280.webp 1200w" in dest
    assert 'src="/img/destination-eta-640.jpg"' in dest
    assert 'alt="Destination ETA preview"' in dest
    md = band(home, "MDRender")
    assert "/img/mdrender-1280.webp 1280w" in md
    first = re.search(r"<article\b.*?</article>", home, re.S).group(0)
    assert 'loading="lazy"' not in first
    assert 'loading="lazy"' in dest or dest == first


def test_images_have_dimensions(built):
    for f, html in all_pages(built).items():
        for tag, a in tags(html):
            if tag == "img":
                assert a.get("width") == "640" and a.get("height") == "360", (f, a)
                assert a.get("alt"), (f, a)


def test_internal_links_resolve(built):
    for f, html in all_pages(built).items():
        for tag, a in tags(html):
            for attr in ("href", "src"):
                v = a.get(attr)
                if v and v.startswith("/"):
                    path = v.split("?")[0].split("#")[0]
                    target = built / path.lstrip("/")
                    if path.endswith("/"):
                        target = target / "index.html"
                    assert target.is_file(), (f, v)
            for part in (a.get("srcset") or "").split(","):
                if part.strip():
                    assert (built / part.split()[0].lstrip("/")).is_file(), (f, part)


def _local(url: str) -> bool:
    return url.startswith("/") and not url.startswith("//") or url.startswith("data:")


def test_no_external_requests(built):
    css = read(built, "styles.css")
    assert "@import" not in css
    for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
        assert _local(u), u
    for f, html in all_pages(built).items():
        for tag, a in tags(html):
            if tag == "script" and a.get("src"):
                assert _local(a["src"]), (f, a)
            if tag == "link" and set((a.get("rel") or "").split()) & {"stylesheet", "icon", "preload", "apple-touch-icon", "manifest"}:
                assert _local(a["href"]), (f, a)
            if tag in ("img", "source", "iframe", "video", "audio"):
                for attr in ("src", "srcset"):
                    for part in (a.get(attr) or "").split(","):
                        if part.strip():
                            assert _local(part.split()[0]), (f, a)
        assert "@import" not in html, f


def test_privacy_and_404_copy(built):
    priv = read(built, "privacy/index.html")
    assert "cookies" in priv.lower() and "analytics" in priv.lower()
    nf = read(built, "404.html")
    assert 'href="/"' in nf
    main = re.search(r"<main\b.*?</main>", nf, re.S).group(0)
    for c in CATEGORIES:
        assert f'href="/{c.slug}/"' in main


def test_rebuild_removes_stale_files(tmp_path):  # Review Focus 4
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "index.html").write_text("x")
    build(SITE_SRC, tmp_path)
    assert not (tmp_path / "old").exists()
    assert (tmp_path / "index.html").is_file()


def test_removed_project_disappears_on_rebuild(tmp_path):  # Review Focus 4
    src = tmp_path / "src"
    shutil.copytree(SITE_SRC, src)
    out = tmp_path / "out"
    build(src, out)
    assert "Sudoku Trainer" in read(out, "index.html")
    y = (src / "projects.yaml").read_text()
    start = y.index("  - slug: sudoku-trainer")
    end = y.index("  - slug: linux-torrent-downloader")
    (src / "projects.yaml").write_text(y[:start] + y[end:])
    build(src, out)
    assert "Sudoku Trainer" not in read(out, "index.html")
    assert "Sudoku Trainer" not in read(out, "other-tools/index.html")


def test_cli_builds_to_out_dir(tmp_path, monkeypatch):
    from a42r_site import build as build_mod
    monkeypatch.chdir(SITE_SRC.parent)
    build_mod.main(["--out", str(tmp_path / "w")])
    assert (tmp_path / "w" / "index.html").is_file()
