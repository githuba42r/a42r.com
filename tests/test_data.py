from pathlib import Path

import pytest

from a42r_site.data import SiteDataError, contrast_ratio, load_site

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site" / "projects.yaml"
# A frozen copy of projects.yaml as specified on 2026-10-20. Spec-specific
# counts and memberships are checked against it, so editing the real YAML
# (adding or launching a project) never breaks the suite.
FIXTURE = ROOT / "tests" / "fixtures" / "projects-2026-10-20.yaml"
PLATFORM_ORDER = ["android", "browser-extensions", "web-apps", "desktop-self-hosted"]
PURPOSE_ORDER = ["development-tools", "euc-riding-tools", "other-tools"]


# --- Invariants of the real data: these hold whatever projects exist. ---

def test_real_data_loads_and_category_order_unchanged():
    s = load_site(SITE)
    assert s.projects
    assert [c.slug for c in s.platforms] == PLATFORM_ORDER
    assert [c.slug for c in s.purposes] == PURPOSE_ORDER


def test_every_project_has_a_platform_and_a_purpose():
    for p in load_site(SITE).projects:
        assert len(p.platforms) >= 1 and len(p.purposes) >= 1, p.slug


def test_project_slugs_unique():
    slugs = [p.slug for p in load_site(SITE).projects]
    assert len(slugs) == len(set(slugs))


def test_every_category_page_non_empty():
    s = load_site(SITE)
    for c in (*s.platforms, *s.purposes):
        assert s.projects_in(c.slug), c.slug


def test_live_first_ordering():
    s = load_site(SITE)
    for c in (*s.platforms, *s.purposes):
        st = [p.status for p in s.projects_in(c.slug)]
        assert st == sorted(st, key=lambda x: x != "live"), c.slug


def test_link_rules():
    for p in load_site(SITE).projects:
        if p.status == "live":
            assert p.url, p.slug
        else:
            assert p.url is None, p.slug


# --- Spec snapshot: checked against the frozen fixture. ---

def test_fixture_has_all_13_projects():
    s = load_site(FIXTURE)
    assert len(s.projects) == 13
    assert [c.slug for c in s.platforms] == PLATFORM_ORDER
    assert [c.slug for c in s.purposes] == PURPOSE_ORDER


def test_membership_matches_spec():
    s = load_site(FIXTURE)
    names = lambda c: {p.name for p in s.projects_in(c)}
    assert names("browser-extensions") == {"ImageTools", "SmartForm Filler"}
    assert names("web-apps") == {"ImageTools", "Scooter Parking Crimes", "GPX Route Exploration", "Sudoku Trainer"}
    assert names("desktop-self-hosted") == {"MDRender", "EUC Charging Monitor", "EUC World Dashboard Overlay", "LinuxTorrentDownloader"}
    assert names("development-tools") == {"ImageTools", "MDRender", "SmartForm Filler"}
    assert names("other-tools") == {"MDRender", "Scooter Parking Crimes", "Sudoku Trainer", "LinuxTorrentDownloader"}
    assert len(names("android")) == 8 and len(names("euc-riding-tools")) == 8


def test_spec_links():
    by = {p.slug: p for p in load_site(FIXTURE).projects}
    assert by["motoeye-remote"].repo_url == "https://github.com/githuba42r/MotoEyeRemote/releases"
    assert by["sudoku-trainer"].repo_url is None  # private repo
    assert by["euc-charging-monitor"].url == "https://github.com/githuba42r/euc_charging"


def test_site_level_metadata_limits():
    s = load_site(SITE)
    titles, descs = [], []
    for c in [*s.platforms, *s.purposes]:
        titles.append(c.title)
        descs.append(c.description)
    titles += [s.home_title, s.privacy_title]
    descs += [s.home_description, s.privacy_description]
    assert all(0 < len(t) <= 60 for t in titles)
    assert all(120 <= len(d) <= 160 for d in descs)
    assert len(set(titles)) == len(titles) and len(set(descs)) == len(descs)


def test_unknown_category_names_project(tmp_path):  # Review Focus 1
    bad = FIXTURE.read_text().replace("purposes: [euc-riding-tools]", "purposes: [euc-ridng-tools]", 1)
    (tmp_path / "p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match=r"pev-plugshare.*euc-ridng-tools"):
        load_site(tmp_path / "p.yaml")


def test_bad_status_and_duplicate_slug_rejected(tmp_path):
    text = FIXTURE.read_text()
    (tmp_path / "a.yaml").write_text(text.replace("status: live", "status: beta", 1))
    with pytest.raises(SiteDataError, match=r"pev-plugshare.*beta"):
        load_site(tmp_path / "a.yaml")
    (tmp_path / "b.yaml").write_text(text.replace("slug: destination-eta", "slug: pev-plugshare", 1))
    with pytest.raises(SiteDataError, match=r"duplicate.*pev-plugshare"):
        load_site(tmp_path / "b.yaml")


def test_contrast_ratio_known_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)


def test_low_contrast_accent_rejected(tmp_path):  # Review Focus 5
    bad = FIXTURE.read_text().replace("#1e824c", "#9be7b0", 1)
    (tmp_path / "p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match="contrast"):
        load_site(tmp_path / "p.yaml")


def _project_block(text: str, slug: str) -> tuple[int, int]:
    start = text.index(f"  - slug: {slug}\n")
    nxt = text.find("\n  - slug: ", start + 1)
    return start, (len(text) if nxt == -1 else nxt + 1)


def _edit_project(tmp_path, slug: str, old: str, new: str) -> Path:
    text = FIXTURE.read_text()
    s, e = _project_block(text, slug)
    block = text[s:e]
    assert old in block, (slug, old)
    out = tmp_path / f"{slug}.yaml"
    out.write_text(text[:s] + block.replace(old, new, 1) + text[e:])
    return out


@pytest.mark.parametrize("field", ["platforms", "purposes"])
def test_empty_category_list_rejected(tmp_path, field):
    import re
    text = FIXTURE.read_text()
    s, e = _project_block(text, "mdrender")
    block = re.sub(rf"{field}: \[[^\]]*\]", f"{field}: []", text[s:e], count=1)
    (tmp_path / "p.yaml").write_text(text[:s] + block + text[e:])
    with pytest.raises(SiteDataError, match=rf"mdrender.*{field}.*at least one"):
        load_site(tmp_path / "p.yaml")


@pytest.mark.parametrize("field,value", [("platforms", "android"), ("purposes", "other-tools")])
def test_bare_string_category_rejected(tmp_path, field, value):
    import re
    text = FIXTURE.read_text()
    s, e = _project_block(text, "mdrender")
    block = re.sub(rf"{field}: \[[^\]]*\]", f"{field}: {value}", text[s:e], count=1)
    (tmp_path / "p.yaml").write_text(text[:s] + block + text[e:])
    with pytest.raises(SiteDataError, match=rf"mdrender.*{field}.*must be a list"):
        load_site(tmp_path / "p.yaml")


def test_live_without_url_rejected(tmp_path):
    bad = _edit_project(tmp_path, "mdrender", "url: https://mdrender.a42r.com/", "url: null")
    with pytest.raises(SiteDataError, match=r"mdrender.*live project requires 'url'"):
        load_site(bad)


def test_soon_with_url_rejected(tmp_path):
    bad = _edit_project(tmp_path, "sudoku-trainer", "    url: null\n", "    url: https://sudoku.a42r.com/\n")
    with pytest.raises(SiteDataError, match=r"sudoku-trainer.*must not set 'url'"):
        load_site(bad)


def test_privacy_description_matches_page():
    d = load_site(SITE).privacy_description
    assert 120 <= len(d) <= 160
    assert "collect nothing" not in d.lower()
    assert "cookies" in d and "analytics" in d and "access logs" in d and "Cloudflare" in d
