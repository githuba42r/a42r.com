import json
from pathlib import Path

from PIL import Image

from a42r_site.data import load_site
from a42r_site.images import import_image, monogram_svg, tint


def test_import_image_writes_three_sizes(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (2000, 1000), "red").save(src)
    sizes = import_image(src, tmp_path / "out", "x")
    assert Image.open(tmp_path / "out/x-640.webp").size == (640, 360)
    assert Image.open(tmp_path / "out/x-1280.webp").size == (1280, 720)
    assert Image.open(tmp_path / "out/x-640.jpg").size == (640, 360)
    assert sizes == {"640": [640, 360], "1280": [1280, 720]}


def test_import_never_upscales(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (1024, 500), "red").save(src)
    sizes = import_image(src, tmp_path / "out", "x")
    w, h = Image.open(tmp_path / "out/x-1280.webp").size
    assert w <= 1024 and w % 2 == 0 and h == round(w * 9 / 16)
    assert sizes["1280"] == [w, h]
    assert Image.open(tmp_path / "out/x-640.webp").size == (640, 360)


def test_wide_source_not_cropped(tmp_path):
    src = tmp_path / "s.png"
    im = Image.new("RGB", (2000, 900), "white")
    for x in list(range(10)) + list(range(1990, 2000)):
        for y in range(900):
            im.putpixel((x, y), (255, 0, 0))
    im.save(src)
    import_image(src, tmp_path / "out", "x")
    out = Image.open(tmp_path / "out/x-640.jpg")
    for x in (0, 639):
        r, g, b = out.getpixel((x, 180))
        assert r > 200 and g < 80 and b < 80


def test_wide_pad_matches_edge_colour(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (2000, 900), "#123456").save(src)
    import_image(src, tmp_path / "out", "x")
    px = Image.open(tmp_path / "out/x-640.jpg").getpixel((0, 0))
    assert all(abs(a - b) <= 3 for a, b in zip(px, (0x12, 0x34, 0x56)))


def test_portrait_letterboxed_on_tint(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (1080, 2400), "black").save(src)
    bg = tint("#1565c0")
    import_image(src, tmp_path / "out", "x", bg=bg)
    im = Image.open(tmp_path / "out/x-640.jpg")
    assert im.size == (640, 360)
    want = tuple(int(bg[i : i + 2], 16) for i in (1, 3, 5))
    assert all(abs(a - b) <= 3 for a, b in zip(im.getpixel((2, 2)), want))
    assert sum(im.getpixel((320, 180))) < 40  # screenshot centred


def test_tint():
    assert tint("#000000") == "#d9d9d9"


def test_import_alpha_flattened_for_jpeg(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGBA", (800, 400), (0, 0, 0, 0)).save(src)
    import_image(src, tmp_path / "out", "x")
    im = Image.open(tmp_path / "out/x-640.jpg")
    assert im.mode == "RGB"
    assert im.getpixel((10, 10))[0] > 240


def test_monogram_svg():
    svg = monogram_svg("EUC Charging Monitor", "#1565c0")
    assert svg.startswith("<svg") and 'viewBox="0 0 640 360"' in svg
    assert ">EC<" in svg and "#1565c0" in svg and 'aria-label="EUC Charging Monitor"' in svg
    assert 'role="img"' in svg


def test_monogram_single_word():
    assert ">MD<" in monogram_svg("MDRender", "#123456")


def test_monogram_escapes_name():
    assert "&amp;" in monogram_svg("A & B", "#123456")
    assert 'aria-label="Say &quot;hi&quot;"' in monogram_svg('Say "hi"', "#123456")


def test_every_live_image_present():
    for p in load_site(Path("site/projects.yaml")).projects:
        if p.image:
            for suf in ("-640.webp", "-1280.webp", "-640.jpg"):
                assert Path(f"site/static/img/{p.image}{suf}").exists()


def test_sizes_json_matches_files():
    img = Path("site/static/img")
    sizes = json.loads((img / "sizes.json").read_text())
    for p in load_site(Path("site/projects.yaml")).projects:
        if p.image:
            assert Image.open(img / f"{p.image}-640.webp").size == tuple(sizes[p.image]["640"])
            assert Image.open(img / f"{p.image}-1280.webp").size == tuple(sizes[p.image]["1280"])


def _import_script():
    import importlib.util

    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("import_images", root / "scripts/import_images.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_import_named_bases_merges_into_sizes_json(tmp_path):
    mod = _import_script()
    for name, size in (("a.png", (2000, 1125)), ("b.png", (1024, 576))):
        Image.new("RGB", size, "red").save(tmp_path / name)
    sources = {"aaa": str(tmp_path / "a.png"), "bbb": str(tmp_path / "b.png")}
    dest = tmp_path / "img"
    dest.mkdir()
    keep = {"640": [640, 360], "1280": [1200, 675]}
    (dest / "sizes.json").write_text(json.dumps({"old": keep, "bbb": {"640": [1, 1], "1280": [2, 2]}}))
    mod.run(["bbb"], sources=sources, dest=dest, projects=Path("site/projects.yaml"))
    sizes = json.loads((dest / "sizes.json").read_text())
    assert sizes == {"old": keep, "bbb": {"640": [640, 360], "1280": [1024, 576]}}
    assert (dest / "bbb-640.webp").is_file() and not (dest / "aaa-640.webp").exists()


def test_import_without_bases_imports_all_and_rewrites(tmp_path):
    mod = _import_script()
    Image.new("RGB", (2000, 1125), "red").save(tmp_path / "a.png")
    dest = tmp_path / "img"
    dest.mkdir()
    (dest / "sizes.json").write_text(json.dumps({"stale": {"640": [640, 360], "1280": [1, 1]}}))
    mod.run([], sources={"aaa": str(tmp_path / "a.png")}, dest=dest, projects=Path("site/projects.yaml"))
    assert json.loads((dest / "sizes.json").read_text()) == {"aaa": {"640": [640, 360], "1280": [1280, 720]}}


def test_import_rejects_unknown_base(tmp_path):
    import pytest

    with pytest.raises(SystemExit, match="nope"):
        _import_script().run(["nope"], sources={}, dest=tmp_path, projects=Path("site/projects.yaml"))


def test_projects_root_from_env(monkeypatch, tmp_path):
    import importlib

    import a42r_site.images as images

    try:
        monkeypatch.setenv("A42R_PROJECTS_ROOT", str(tmp_path))
        importlib.reload(images)
        assert images.IMAGE_SOURCES["mdrender"] == str(tmp_path / "MDRender/website/images/app-markdown.png")
        monkeypatch.setenv("A42R_PROJECTS_ROOT", "~/elsewhere")
        importlib.reload(images)
        assert images.PROJECTS_ROOT == Path.home() / "elsewhere"
        monkeypatch.delenv("A42R_PROJECTS_ROOT")
        importlib.reload(images)
        assert images.PROJECTS_ROOT == Path.home() / "src/AndroidStudioProjects"
        assert images.IMAGE_SOURCES["imagetools"] == "https://image-tools.a42r.com/images/og-image.jpg"
    finally:
        monkeypatch.delenv("A42R_PROJECTS_ROOT", raising=False)
        importlib.reload(images)


def test_no_home_path_in_source():
    root = Path(__file__).resolve().parent.parent
    files = [*root.glob("a42r_site/*.py"), *root.glob("scripts/*"), *root.glob("tests/*.py")]
    for f in files:
        if f.is_file():
            assert "/" + "home/" not in f.read_text(encoding="utf-8"), f
