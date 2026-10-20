from pathlib import Path

import pytest

from a42r_site.data import SiteDataError, contrast_ratio, load_site

SITE = Path("site/projects.yaml")


def test_real_data_loads_with_all_13_projects():
    s = load_site(SITE)
    assert len(s.projects) == 13
    assert [c.slug for c in s.platforms] == ["android", "browser-extensions", "web-apps", "desktop-self-hosted"]
    assert [c.slug for c in s.purposes] == ["development-tools", "euc-riding-tools", "other-tools"]


def test_membership_matches_spec():
    s = load_site(SITE)
    names = lambda c: {p.name for p in s.projects_in(c)}
    assert names("browser-extensions") == {"ImageTools", "SmartForm Filler"}
    assert names("web-apps") == {"ImageTools", "Scooter Parking Crimes", "GPX Route Exploration", "Sudoku Trainer"}
    assert names("desktop-self-hosted") == {"MDRender", "EUC Charging Monitor", "EUC World Dashboard Overlay", "LinuxTorrentDownloader"}
    assert names("development-tools") == {"ImageTools", "MDRender", "SmartForm Filler"}
    assert names("other-tools") == {"MDRender", "Scooter Parking Crimes", "Sudoku Trainer", "LinuxTorrentDownloader"}
    assert len(names("android")) == 8 and len(names("euc-riding-tools")) == 8


def test_live_first_ordering():
    st = [p.status for p in load_site(SITE).projects_in("android")]
    assert st == sorted(st, key=lambda x: x != "live")


def test_link_rules():
    for p in load_site(SITE).projects:
        if p.status == "live":
            assert p.url
        else:
            assert p.url is None
    by = {p.slug: p for p in load_site(SITE).projects}
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
    bad = SITE.read_text().replace("purposes: [euc-riding-tools]", "purposes: [euc-ridng-tools]", 1)
    (tmp_path / "p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match=r"pev-plugshare.*euc-ridng-tools"):
        load_site(tmp_path / "p.yaml")


def test_bad_status_and_duplicate_slug_rejected(tmp_path):
    text = SITE.read_text()
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
    bad = SITE.read_text().replace("#1e824c", "#9be7b0", 1)
    (tmp_path / "p.yaml").write_text(bad)
    with pytest.raises(SiteDataError, match="contrast"):
        load_site(tmp_path / "p.yaml")
