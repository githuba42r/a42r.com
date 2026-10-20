# www.a42r.com Portfolio Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A data-driven static portfolio site for the a42r brand at https://www.a42r.com: a home page, 4 platform pages, 3 purpose pages, privacy and 404 pages, with full SEO. It runs on the Oracle Cloud VM and deploys from GitHub Actions.

**Architecture:** `site/projects.yaml` is the single source of truth. A small Python package `a42r_site` validates it and renders Jinja2 templates to plain static files in `website/`. Band images are imported once by a separate script and committed. The build itself needs only Jinja2 and PyYAML. CI builds the site and rsyncs `website/` to `/opt/apps/a42r/website`, which nginx serves as `www.a42r.com`.

**Tech Stack:** Python 3.11+ (local 3.14), Jinja2 3.1, PyYAML 6, Pillow 12 (image import only), pytest 8, nginx, certbot (dns-cloudflare), GitHub Actions, rrsync.

**Spec:** `docs/superpowers/specs/2026-10-20-a42r-portfolio-design.md`. Project facts, colours and asset paths: `/home/philg/AI-Agent-Config/knowledgebase/personal-projects/projects-overview.md`.

## Global Constraints

- Brand, not person: no personal name anywhere in page copy or metadata; author/publisher is "a42r".
- Light theme only: paper `#f7f4ee`, text `#1c2430` / headings `#141a22`, muted `#5b6573`, borders `#e4ddd0`, brand amber `#a8701c`.
- Fonts: headings `"Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif`; body system sans. No web fonts, no external requests of any kind (no CDN, analytics, cookies).
- Home `<h1>` is exactly **Projects**; subtitle exactly **Things I build, use, and give away.**
- Canonical origin `https://www.a42r.com`, trailing-slash directory URLs, `lang="en-AU"`, exactly one `<h1>` per page.
- All content must be in the generated HTML, with no client-side rendering. JavaScript is optional and must not be needed for any content.
- Live projects: "Visit site →" button. Coming soon: badge, plus "View on GitHub" only for public repos. No outbound link otherwise.
- Do **not** touch the apex `a42r.com` DNS, and add no apex redirect. Do not modify any other project's repo or site.
- Mobile: 16px side gutters, no horizontal scroll at 360px wide.
- Text and button colours must meet WCAG AA contrast (≥ 4.5:1 for body/button text, ≥ 3:1 for large text such as the amber `#a8701c` wordmark, which is 3.83 on paper). Never use the amber or the accents for body-size text on paper.
- Git: the repo is new. Work only on branch `feature/portfolio-site`; never commit to `main`. Creating the GitHub repo, pushing, and adding Actions secrets each need the operator's explicit go-ahead.

## Review Focus

1. **A typo in a category slug or status in `projects.yaml`:** the build must fail with a message naming the project and the bad value. It must not silently drop the project from pages. (Task 1)
2. **Copy with apostrophes, quotes and `&`** (e.g. "I'll be there at 4:42"): it must be escaped correctly in HTML attributes, in `og:` tags and inside JSON-LD, and the JSON-LD must still parse. (Task 4)
3. **A project with no image source** (EUC Charging Monitor, Coming-soon projects): it gets the monogram tile, with no broken `<img>` and no missing width/height. (Tasks 2, 3)
4. **A page or project removed between builds:** the rebuilt `website/` must not keep the stale HTML, and the deploy must remove it from the server (`--delete`). (Tasks 3, 6)
5. **A per-project accent too light for the paper background:** the build must fail on the contrast check rather than ship unreadable buttons. (Task 1)

---

## File Structure

```
a42r.com/
  .gitignore                    # website/, .superpowers/, __pycache__/, .venv/
  requirements.txt              # jinja2, pyyaml
  requirements-dev.txt          # -r requirements.txt, pillow, pytest
  pyproject.toml                # [tool.pytest.ini_options] testpaths=["tests"], pythonpath=["."]
  README.md                     # how to add/launch a project, build, deploy
  site/
    projects.yaml               # site config + categories + projects (source of truth)
    templates/
      base.html                 # <head> (meta/OG/JSON-LD slots), header nav, footer
      _band.html                # one project band (macro)
      home.html  listing.html  privacy.html  404.html
    static/                     # copied verbatim to website/
      styles.css  favicon.svg  favicon-32.png  apple-touch-icon.png
      icon-192.png  icon-512.png  og-image.png  site.webmanifest
      img/<slug>-640.webp  img/<slug>-1280.webp  img/<slug>-640.jpg   # imported
  a42r_site/
    __init__.py
    data.py                     # load + validate projects.yaml
    images.py                   # band-image import + monogram SVG
    seo.py                      # JSON-LD builders, sitemap, robots
    build.py                    # page assembly + render + CLI
  scripts/
    import_images.py            # one-off: source assets -> site/static/img
    make_brand_assets.py        # favicons + OG image from the wordmark
    deploy-website.sh           # manual fallback deploy
  deploy/nginx-www.a42r.com.conf
  .github/workflows/deploy-website.yml
  tests/
    test_data.py  test_images.py  test_build.py  test_seo.py  test_deploy.py
```

---

### Task 1: Repo scaffold, data model and validated project data

**Files:**
- Create: `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `a42r_site/__init__.py`, `a42r_site/data.py`, `site/projects.yaml`
- Test: `tests/test_data.py`

**Interfaces:**
- Produces:
  - `Category(slug: str, kind: Literal["platform","purpose"], name: str, title: str, description: str, intro: str)`, a frozen dataclass.
  - `Project(slug, name, status: Literal["live","soon"], url: str | None, repo_url: str | None, summary: str, platforms: tuple[str,...], purposes: tuple[str,...], accent: str, image: str | None, os: str, app_category: str)`, a frozen dataclass. `image` is the base name under `static/img/` or `None`, which means a monogram. `os` and `app_category` feed the schema.org `operatingSystem` / `applicationCategory` fields.
  - `Site(base_url: str, name: str, tagline: str, summary: str, platforms: tuple[Category,...], purposes: tuple[Category,...], projects: tuple[Project,...])`, with method `projects_in(cat_slug: str) -> list[Project]`. The list is ordered live first, then soon, in YAML order within each group.
  - `load_site(path: Path) -> Site`, which raises `SiteDataError(msg)` and names the offending project slug and field.
  - `contrast_ratio(fg: str, bg: str) -> float` (WCAG 2.x relative luminance; hex `#rrggbb`).
  - Module constant `PAPER = "#f7f4ee"`.

- [ ] **Step 1: Init repo and branch**

```bash
cd /home/philg/src/AndroidStudioProjects/a42r.com
git init -b main && git checkout -b feature/portfolio-site
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # after writing the files below
```

Write the scaffold files listed above (`pyproject.toml` with pytest `pythonpath=["."]`).

- [ ] **Step 2: Write the failing tests** in `tests/test_data.py`

```python
SITE = Path("site/projects.yaml")

def test_real_data_loads_with_all_13_projects():
    s = load_site(SITE)
    assert len(s.projects) == 13
    assert [c.slug for c in s.platforms] == ["android","browser-extensions","web-apps","desktop-self-hosted"]
    assert [c.slug for c in s.purposes] == ["development-tools","euc-riding-tools","other-tools"]

def test_membership_matches_spec():
    s = load_site(SITE)
    names = lambda c: {p.name for p in s.projects_in(c)}
    assert names("browser-extensions") == {"ImageTools","SmartForm Filler"}
    assert names("web-apps") == {"ImageTools","Scooter Parking Crimes","GPX Route Exploration","Sudoku Trainer"}
    assert names("desktop-self-hosted") == {"MDRender","EUC Charging Monitor","EUC World Dashboard Overlay","LinuxTorrentDownloader"}
    assert names("development-tools") == {"ImageTools","MDRender","SmartForm Filler"}
    assert names("other-tools") == {"MDRender","Scooter Parking Crimes","Sudoku Trainer","LinuxTorrentDownloader"}
    assert len(names("android")) == 8 and len(names("euc-riding-tools")) == 8

def test_live_first_ordering():
    st = [p.status for p in load_site(SITE).projects_in("android")]
    assert st == sorted(st, key=lambda x: x != "live")

def test_link_rules():
    for p in load_site(SITE).projects:
        if p.status == "live": assert p.url
        else: assert p.url is None
    by = {p.slug: p for p in load_site(SITE).projects}
    assert by["motoeye-remote"].repo_url == "https://github.com/githuba42r/MotoEyeRemote/releases"
    assert by["sudoku-trainer"].repo_url is None          # private repo
    assert by["euc-charging-monitor"].url == "https://github.com/githuba42r/euc_charging"

def test_unknown_category_names_project(tmp_path):   # Review Focus 1
    bad = SITE.read_text().replace("purposes: [euc-riding-tools]", "purposes: [euc-ridng-tools]", 1)
    (tmp_path/"p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match=r"pev-plugshare.*euc-ridng-tools"):
        load_site(tmp_path/"p.yaml")

def test_bad_status_and_duplicate_slug_rejected(tmp_path): ...  # status "beta" -> SiteDataError naming slug; duplicate slug -> SiteDataError

def test_contrast_ratio_known_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)

def test_low_contrast_accent_rejected(tmp_path):    # Review Focus 5
    bad = SITE.read_text().replace("#1e824c", "#9be7b0", 1)
    (tmp_path/"p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match="contrast"):
        load_site(tmp_path/"p.yaml")
```

- [ ] **Step 3: Run:** `.venv/bin/pytest tests/test_data.py -v`. Expected: FAIL (ImportError).

- [ ] **Step 4: Implement `a42r_site/data.py` and write `site/projects.yaml`**

YAML shape: top-level `site:` (base_url `https://www.a42r.com`, name `a42r`, tagline, summary), `platforms:` and `purposes:` (lists of category mappings), `projects:` (list). Use flow lists such as `platforms: [android]`, which the tests rely on. Validation rules: unique slugs; status in {live, soon}; every platform/purpose slug exists; at least one of each; live ⇒ `url` set; soon ⇒ `url` null; accent must give `contrast_ratio("#ffffff", accent) >= 4.5` (white button text) **and** `contrast_ratio(accent, PAPER) >= 3.0` (accent borders, swatches and large text only; body-size links and tags use the text colour, not the accent). Checked values: `#1e824c` 4.82 / 4.39 ✓, `#1976d2` 4.60 / 4.19 ✓, `#dc2626` 4.83 / 4.40 ✓, `#c4314b` 5.40 / 4.92 ✓; `#6366f1` fails (4.47), so use `#4f46e5`.

Project rows (slug · status · url/repo_url · platforms · purposes · accent · image):

| slug | status | url / repo_url | platforms | purposes | accent | image |
|---|---|---|---|---|---|---|
| pev-plugshare | live | https://pevplugshare.a42r.com/ | android | euc-riding-tools | `#1e824c` | pev-plugshare |
| destination-eta | live | https://destination.a42r.com/ | android | euc-riding-tools | `#1976d2` | destination-eta |
| euc-world-osmand | live | https://osmand-euc.a42r.com/ | android | euc-riding-tools | builder (orange family) | euc-world-osmand |
| scooter-parking-crimes | live | https://spc.a42r.com/ | android, web-apps | euc-riding-tools, other-tools | `#dc2626` | scooter-parking-crimes |
| mdrender | live | https://mdrender.a42r.com/ | android, desktop-self-hosted | development-tools, other-tools | `#c4314b` | mdrender |
| imagetools | live | https://image-tools.a42r.com/ | web-apps, browser-extensions, android | development-tools | `#4f46e5` | imagetools |
| euc-charging-monitor | live | https://github.com/githuba42r/euc_charging | desktop-self-hosted | euc-riding-tools | builder (HA blue) | null |
| motoeye-remote | soon | repo https://github.com/githuba42r/MotoEyeRemote/releases | android | euc-riding-tools | builder | null |
| eucworld-dashboard-overlay | soon | repo https://github.com/githuba42r/eucworld-dashboard-overlay | desktop-self-hosted | euc-riding-tools | builder | null |
| gpx-route-exploration | soon | repo https://github.com/githuba42r/gpx-route-exploration | web-apps | euc-riding-tools | builder | null |
| smartform-filler | soon | — | browser-extensions | development-tools | builder | null |
| sudoku-trainer | soon | — | web-apps, android | other-tools | builder | null |
| linux-torrent-downloader | soon | — | desktop-self-hosted | other-tools | builder | null |

Names in the YAML: "PEV PlugShare", "Destination ETA", "EUC World for OsmAnd", "Scooter Parking Crimes", "MDRender", "ImageTools", "EUC Charging Monitor", "MotoEye Remote", "EUC World Dashboard Overlay", "GPX Route Exploration", "SmartForm Filler", "Sudoku Trainer", "LinuxTorrentDownloader". Write each `summary` as two short plain sentences, taken from the KB article and not copied from the project sites. Write each category `intro` as 2–3 unique sentences. `title` and `description` are the page `<title>` and meta description: unique, title ≤ 60 characters, description 120–160 characters. Use `os` values like `Android`, `Web`, `Chrome, Firefox`, `Linux`, `Home Assistant`, and `app_category` values like `UtilitiesApplication`, `TravelApplication`, `DeveloperApplication`, `GameApplication`, `MultimediaApplication`.

- [ ] **Step 5: Run:** `.venv/bin/pytest tests/test_data.py -v`. Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements*.txt pyproject.toml a42r_site site/projects.yaml tests/test_data.py
git commit -m "feat: validated project data model for a42r portfolio"
```

---

### Task 2: Band images and monograms

**Files:**
- Create: `a42r_site/images.py`, `scripts/import_images.py`, `site/static/img/*`
- Test: `tests/test_images.py`

**Interfaces:**
- Consumes: `load_site`, `Project.image`, `Project.accent`, `Project.name`.
- Produces:
  - `import_image(src: Path, dest_dir: Path, base: str) -> None`. It writes `<base>-640.webp`, `<base>-1280.webp` and `<base>-640.jpg`, each resized to fit 640/1280 wide while keeping the aspect ratio, with the 1280 version never upscaled. Quality: WebP 82, JPEG 85 progressive.
  - `monogram_svg(name: str, accent: str) -> str`. It returns an inline SVG with a 16:9 viewBox (`0 0 640 360`), the accent fill and the initials of the first two words in white serif. It carries `role="img"` and `aria-label="<name>"`.
  - `IMAGE_SOURCES: dict[str, str]`, which maps a base name to its source, a local path or an https URL.

Sources (all paths under `/home/philg/src/AndroidStudioProjects/` unless absolute):

| base | source |
|---|---|
| pev-plugshare | `PEVPlugShare/website/images/og-card.jpg` |
| destination-eta | `DestinationETATracker/website/images/og-image.jpg` |
| euc-world-osmand | `OSM-EUC-World/feature_graphic_1024x500.png` |
| scooter-parking-crimes | `UnsafeRideshareParkingReports/play-store/feature-graphic-1024x500.png` |
| mdrender | `MDRender/website/images/app-markdown.png` |
| imagetools | `https://image-tools.a42r.com/images/og-image.jpg` (download into a fresh temp dir first) |

- [ ] **Step 1: Write the failing tests**

```python
def test_import_image_writes_three_sizes(tmp_path):
    src = tmp_path/"s.png"; Image.new("RGB", (2000, 1000), "red").save(src)
    import_image(src, tmp_path/"out", "x")
    assert Image.open(tmp_path/"out/x-640.webp").size == (640, 320)
    assert Image.open(tmp_path/"out/x-1280.webp").size == (1280, 640)
    assert (tmp_path/"out/x-640.jpg").exists()

def test_import_never_upscales(tmp_path):   # 1024x500 source -> 1280 variant stays 1024 wide

def test_monogram_svg():
    svg = monogram_svg("EUC Charging Monitor", "#1565c0")
    assert svg.startswith("<svg") and 'viewBox="0 0 640 360"' in svg
    assert ">EC<" in svg and "#1565c0" in svg and 'aria-label="EUC Charging Monitor"' in svg

def test_monogram_escapes_name():
    assert "&amp;" in monogram_svg("A & B", "#123456")

def test_every_live_image_present():
    for p in load_site(Path("site/projects.yaml")).projects:
        if p.image:
            for suf in ("-640.webp", "-1280.webp", "-640.jpg"):
                assert Path(f"site/static/img/{p.image}{suf}").exists()
```

- [ ] **Step 2: Run:** `.venv/bin/pytest tests/test_images.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `images.py` and `scripts/import_images.py`** (CLI: `python scripts/import_images.py`, imports every `IMAGE_SOURCES` entry, prints each output path).
- [ ] **Step 4: Run** `.venv/bin/python scripts/import_images.py && .venv/bin/pytest tests/test_images.py -v`. Expected: all PASS. Then view one image of each to sanity-check the crop.
- [ ] **Step 5: Commit** `a42r_site/images.py scripts/import_images.py site/static/img tests/test_images.py` with `feat: band images and monogram fallback`.

---

### Task 3: Templates, styles and page build

**Files:**
- Create: `a42r_site/build.py`, `site/templates/{base,_band,home,listing,privacy,404}.html`, `site/static/styles.css`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `Site`, `Project`, `Category`, `monogram_svg`.
- Produces:
  - `Page(path: str, template: str, title: str, description: str, h1: str, projects: list[Project], category: Category | None, breadcrumbs: list[tuple[str,str]])`, a dataclass. `path` is `"/"`, `"/android/"`, `"/privacy/"` or `"/404.html"`.
  - `pages_for(site: Site) -> list[Page]`, which returns 10 pages: home, 4 platform pages, 3 purpose pages, privacy and 404.
  - `build(src: Path = Path("site"), out: Path = Path("website")) -> list[Page]`. It **empties `out` first**, copies `static/` and renders every page to `out/<path>/index.html` (404 → `out/404.html`).
  - CLI: `python -m a42r_site.build [--out DIR]`.
  - Jinja env with `autoescape=True` and `StrictUndefined`.

Layout rules (from the agreed mockup `.superpowers/brainstorm/4034189-1792500369/content/showcase-light.html`):
- **Header:** the "a42r" serif wordmark in `#a8701c`, linking to `/`, and a nav with two labelled groups, Platforms and Purposes. On mobile the nav uses a `<details>` disclosure, with no JavaScript.
- **Home:** `<h1>Projects</h1>`, then the subtitle, the `site.summary` and every project band.
- **Listing pages:** the `h1` is the category name, then the intro, the bands and breadcrumbs (Home › Category).
- **Bands:** each is an `<article>` with an `<h2>` holding the project name, the summary, tag links to each platform/purpose page, and the action.
  - The image alternates left/right using `:nth-child(even)`.
  - The background is a gradient from accent at 12% to white, with a 1px accent-tinted border, as in the mockup.
  - Images use `<picture>` with the webp srcset `640w, 1280w`, an `<img>` jpg fallback, `width=640` with the matching height, `alt="<name> preview"`, and `loading="lazy"` except for the first band. Projects with no image get the inline monogram.
  - Actions: live → `<a class="btn" href=url rel="noopener">Visit site →</a>`; soon → `<span class="badge">Coming soon</span>`, plus `<a href=repo_url rel="noopener">View on GitHub</a>` when `repo_url` is set.
- **Footer:** © a42r, GitHub (https://github.com/githuba42r), Privacy.
- **CSS:** custom properties for every colour in Global Constraints, visible `:focus-visible` outline, `overflow-wrap: anywhere` on headings, and below 720px bands stack with the image first.

- [ ] **Step 1: Write the failing tests** (build into `tmp_path` once with a module fixture, then parse with `html.parser` or regex)

```python
def test_ten_pages_written(built): # "/", 7 category dirs, privacy/, 404.html each exist
def test_one_h1_each_and_home_copy(built):
    home = read(built, "index.html")
    assert home.count("<h1") == 1 and "<h1>Projects</h1>" in home
    assert "Things I build, use, and give away." in home
def test_every_project_on_home_and_its_categories(built):
    # for each project: its name in home; in each of its category pages; absent from a category it isn't in
def test_live_vs_soon_actions(built):
    pev = band(read(built,"android/index.html"), "PEV PlugShare")
    assert 'href="https://pevplugshare.a42r.com/"' in pev and "Visit site" in pev
    sud = band(read(built,"other-tools/index.html"), "Sudoku Trainer")
    assert "Coming soon" in sud and "href=\"http" not in sud
    moto = band(read(built,"android/index.html"), "MotoEye Remote")
    assert "View on GitHub" in moto and "Visit site" not in moto
def test_monogram_used_without_image(built):   # Review Focus 3
    ecm = band(read(built,"desktop-self-hosted/index.html"), "EUC Charging Monitor")
    assert "<svg" in ecm and "<img" not in ecm
def test_images_have_dimensions(built): # every <img> has width= and height= and alt=
def test_internal_links_resolve(built): # every href starting "/" maps to a file in out
def test_no_external_requests(built): # no <script src=http, <link href=http (except canonical/og meta), no @import
def test_rebuild_removes_stale_files(tmp_path):  # Review Focus 4
    (tmp_path/"old"/"index.html").parent.mkdir(parents=True); (tmp_path/"old/index.html").write_text("x")
    build(Path("site"), tmp_path); assert not (tmp_path/"old").exists()
```

`band(html, name)` is a test helper that returns the `<article>…</article>` slice containing `<h2…>name</h2>`.

- [ ] **Step 2: Run:** `.venv/bin/pytest tests/test_build.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `build.py`, the templates and `styles.css`.** Leave the SEO `<head>` blocks as Jinja `{% block %}` slots that Task 4 fills; give them a plain `<title>` and meta description for now.
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all PASS. Then run `.venv/bin/python -m a42r_site.build && python -m http.server -d website 8642` and look at `/` and `/android/` at 1280px and 360px wide, checking there's no horizontal scroll and that the long names (EUC World Dashboard Overlay, LinuxTorrentDownloader) wrap.
- [ ] **Step 5: Commit** templates, CSS, `build.py` and tests with `feat: render home and category pages`.

---

### Task 4: SEO layer and brand assets

**Files:**
- Create: `a42r_site/seo.py`, `scripts/make_brand_assets.py`, `site/static/{favicon.svg,favicon-32.png,apple-touch-icon.png,icon-192.png,icon-512.png,og-image.png,site.webmanifest}`
- Modify: `a42r_site/build.py` (write sitemap/robots; pass JSON-LD to templates), `site/templates/base.html` (head)
- Test: `tests/test_seo.py`

**Interfaces:**
- Consumes: `Site`, `Page`, `pages_for`, `build`.
- Produces:
  - `jsonld_for(site: Site, page: Page) -> list[dict]`:
    - home: `Organization` (name "a42r", url, logo `https://www.a42r.com/icon-512.png`, `sameAs: ["https://github.com/githuba42r"]`) and `WebSite`;
    - category pages: `CollectionPage` with `mainEntity` = `ItemList` of `ListItem` (position, `item`: `SoftwareApplication` with name, description=summary, `operatingSystem`, `applicationCategory`, and `url` = url or repo_url when present), plus `BreadcrumbList`;
    - privacy: `BreadcrumbList`.
  - `sitemap_xml(urls: list[str], lastmod: str) -> str`, which excludes 404.
  - `ROBOTS: str`, which is `User-agent: *\nAllow: /\nSitemap: https://www.a42r.com/sitemap.xml\n`.
  - Render JSON-LD with `json.dumps(..., ensure_ascii=False).replace("</", "<\\/")` inside `<script type="application/ld+json">`.

Head contents for every page:
- `<title>` and meta description from `Page`;
- `<link rel=canonical href="https://www.a42r.com{path}">`;
- `og:type` website, `og:site_name` a42r, `og:title`, `og:description`, `og:url`, `og:image` `https://www.a42r.com/og-image.png` (1200×630) with width, height and alt;
- `twitter:card` summary_large_image;
- `theme-color` `#f7f4ee`, the manifest link and the favicon links.

The 404 page gets `<meta name="robots" content="noindex">` and no canonical.

`make_brand_assets.py`: rasterise the "a42r" amber serif wordmark on paper for the favicons and icons using Pillow, with a fallback serif TTF found via `fc-match serif`. The OG image is 1200×630 paper, the wordmark, "Projects — Things I build, use, and give away." and a row of the five live accent colours as small swatches. `favicon.svg` is hand-written SVG text.

- [ ] **Step 1: Write the failing tests**

```python
def test_titles_and_descriptions_unique(built): # 9 indexable pages; titles unique, ≤60; descs unique, 120–160
def test_canonical_and_og(built): # each indexable page: canonical == og:url == base+path; og:image absolute
def test_jsonld_parses_and_counts(built):
    for page in category pages: data = json.loads(ldjson(page))
    # ItemList length == number of bands on the page; positions 1..n
def test_jsonld_survives_quotes(tmp_path):    # Review Focus 2
    # copy site/ to tmp, set destination-eta summary to `"I'll be there at 4:42" & on time </script>`
    # build; json.loads every ld+json block; the literal "</script>" does not appear inside the block;
    # the og:description attribute contains &quot; / &amp; escapes
def test_home_jsonld_org(built): # @type Organization, name "a42r", sameAs github
def test_sitemap_and_robots(built):
    sm = read(built,"sitemap.xml"); assert sm.count("<url>") == 9 and "404" not in sm
    assert "Sitemap: https://www.a42r.com/sitemap.xml" in read(built,"robots.txt")
def test_404_noindex(built)
def test_brand_assets_present(built): # og-image.png is 1200x630; icon-512.png is 512x512; manifest JSON has name "a42r"
def test_no_personal_name(built): # "Phil" / "Gersekowski" absent from every built file
```

- [ ] **Step 2: Run:** `.venv/bin/pytest tests/test_seo.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `seo.py`, the head template, the build additions and `make_brand_assets.py`; run the script.**
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all PASS.
- [ ] **Step 5: Commit** with `feat: SEO metadata, structured data, sitemap and brand assets`.

---

### Task 5: Deploy pipeline (CI workflow, manual script, nginx vhost file)

**Files:**
- Create: `.github/workflows/deploy-website.yml`, `scripts/deploy-website.sh`, `deploy/nginx-www.a42r.com.conf`, `README.md`
- Test: `tests/test_deploy.py`

**Interfaces:**
- Consumes: `python -m a42r_site.build` CLI.
- Produces: the workflow and vhost that Task 6 installs.

Workflow: copy `/home/philg/src/AndroidStudioProjects/PEVPlugShare/.github/workflows/deploy-website.yml` and change it as follows.
- Triggers: `push` to `main` touching `site/**`, `a42r_site/**`, `requirements.txt` or the workflow file, plus `workflow_dispatch`.
- Add steps before the sync: `actions/setup-python@v5` (3.12), `pip install -r requirements-dev.txt`, `pytest -q`, `python -m a42r_site.build`.
- `DEPLOY_PATH` defaults to `/opt/apps/a42r/website`.
- Purge base and smoke-test base are `https://www.a42r.com/`. Smoke-test paths: `""`, `robots.txt`, `sitemap.xml`, `favicon.ico` → use `favicon-32.png`, `android/`.
- Secret names are unchanged (`WEBSITE_DEPLOY_*`, `CLOUDFLARE_*`).

`deploy-website.sh`: `set -euo pipefail`; build; `rsync -rlvz --delete --chmod=D755,F644 website/ oracle-cloud:/opt/apps/a42r/website/`. It accepts `--dry-run`, which adds `-n`.

`nginx-www.a42r.com.conf`: modelled on the server's `image-tools.a42r.com` vhost.
- `server_name www.a42r.com`, `root /opt/apps/a42r/website`, `try_files $uri $uri/ =404`, `error_page 404 /404.html`.
- gzip on CSS, JS, SVG, XML and the manifest; the `site.webmanifest` type override.
- Caching: `location ~* \.(webp|jpg|png|svg|css)$ { expires 30d; }`, with HTML at the default. The CSS URL carries `?v=<short git sha or build hash>`, which `build.py` adds through a `asset_version` template global.
- 443 with `/etc/letsencrypt/live/www.a42r.com/` paths, and port 80 → 301 to https.
- **No** `a42r.com` in `server_name`.

README: how to add or launch a project (edit YAML, run tests, build), how to import images, and how deploy works.

- [ ] **Step 1: Write the failing tests**

```python
def test_workflow_targets_www():
    wf = yaml.safe_load(Path(".github/workflows/deploy-website.yml").read_text())
    text = Path(".github/workflows/deploy-website.yml").read_text()
    assert "/opt/apps/a42r/website" in text and "https://www.a42r.com/" in text
    assert "pevplugshare" not in text
    assert "--delete" in text and "pytest" in text and "a42r_site.build" in text
def test_vhost_is_www_only():
    conf = Path("deploy/nginx-www.a42r.com.conf").read_text()
    names = re.findall(r"server_name\s+([^;]+);", conf)
    assert names and all(n.strip() == "www.a42r.com" for n in names)
    assert "/opt/apps/a42r/website" in conf and "error_page 404 /404.html" in conf
def test_css_cache_busted(built): # base.html references styles.css?v=
```

- [ ] **Step 2: Run:** `.venv/bin/pytest tests/test_deploy.py -v`. Expected: FAIL.
- [ ] **Step 3: Write the four files** (and the `asset_version` global in `build.py`).
- [ ] **Step 4: Run** `.venv/bin/pytest -v` and `bash -n scripts/deploy-website.sh`. If `actionlint` is installed, run it too. Expected: all PASS.
- [ ] **Step 5: Commit** with `feat: deploy workflow, manual deploy script and nginx vhost`.

---

### Task 6: Server provisioning, first deploy, verification and KB update

This task changes the live server. The commands run via `ssh oracle-cloud`, and `sudo -n` works for the `ubuntu` user. Steps marked **[operator]** need the operator.

**Files:**
- Modify: `/home/philg/AI-Agent-Config/knowledgebase/personal-projects/oracle-cloud-server.md`, `.../projects-overview.md`, `.../INDEX.md`

- [ ] **Step 1: Web root:** `sudo mkdir -p /opt/apps/a42r/website && sudo chown ubuntu:ubuntu /opt/apps/a42r/website`.
- [ ] **Step 2: Certificate, before the vhost:**
  `sudo certbot certonly --dns-cloudflare --dns-cloudflare-credentials /root/.secrets/cloudflare.ini -d www.a42r.com`
  Expected: the certificate is saved to `/etc/letsencrypt/live/www.a42r.com/`. This uses DNS-01, the same method as image-tools, so it doesn't depend on the 1016 origin issue.
- [ ] **Step 3: vhost:** copy `deploy/nginx-www.a42r.com.conf` to `/etc/nginx/sites-available/www.a42r.com`, symlink it into `sites-enabled/`, then run `sudo nginx -t && sudo systemctl reload nginx`. Expected: `syntax is ok` and the other sites are unaffected (`curl -sI https://pevplugshare.a42r.com` returns 200).
- [ ] **Step 4: First deploy (manual):** `scripts/deploy-website.sh --dry-run`, then run it for real.
- [ ] **Step 5: Verify at the origin:** `curl -s --resolve www.a42r.com:443:161.33.93.37 https://www.a42r.com/ | grep "<h1>Projects</h1>"`. Expected: a match.
- [ ] **Step 6: Verify through Cloudflare:** `curl -s -o /dev/null -w '%{http_code}' --resolve www.a42r.com:443:104.21.19.228 https://www.a42r.com/`. Expected: `200`. If it's `530` with body `error code: 1016`, stop and report to the operator: the `www` record in Cloudflare must be a proxied **A** record → `161.33.93.37`. **[operator]**
- [ ] **Step 7: Quality check:** run Lighthouse on `/` and `/euc-riding-tools/`, mobile and desktop: `npx lighthouse https://www.a42r.com/ --only-categories=performance,accessibility,best-practices,seo --quiet --chrome-flags=--headless`. Expected: ≥ 95 in each category. Fix and redeploy if not. Also check `curl -s https://www.a42r.com/nope` → 404 page, and that `https://a42r.com` still behaves as before (unchanged).
- [ ] **Step 8: CI handover [operator]:** ask the operator before each of these:
  1. create the GitHub repo `githuba42r/a42r.com` (`gh repo create githuba42r/a42r.com --public --source . --push` from `feature/portfolio-site`), then open a PR to `main`;
  2. generate a deploy key (`ssh-keygen -t ed25519 -N "" -f a42r-deploy`) and append to `~ubuntu/.ssh/authorized_keys` on the server: `command="/usr/bin/rrsync /opt/apps/a42r/website",restrict <pubkey>`;
  3. set the secrets `WEBSITE_DEPLOY_HOST=161.33.93.37`, `WEBSITE_DEPLOY_USER=ubuntu`, `WEBSITE_DEPLOY_SSH_KEY`, `WEBSITE_DEPLOY_KNOWN_HOSTS` (`ssh-keyscan -t ed25519 161.33.93.37`), `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` (the operator supplies the Cloudflare values);
  4. after the merge, confirm the workflow run is green.
- [ ] **Step 9: Update the KB.**
  - `oracle-cloud-server.md`: add `www.a42r.com` to the vhost list, add the `/opt/apps/a42r/website` path, record the certificate method (DNS-01, its own cert) and note how the 1016 issue resolved.
  - `projects-overview.md`: add a "Portfolio site" section with the repo, the build command and how to add or launch a project.
  - `INDEX.md`: add a row.
- [ ] **Step 10: Commit** any fixes from Step 7 on the feature branch with `fix: lighthouse findings`. KB changes are in `/home/philg/AI-Agent-Config`; commit them there only if the operator asks.
