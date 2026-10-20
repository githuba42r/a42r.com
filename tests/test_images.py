from pathlib import Path

from PIL import Image

from a42r_site.data import load_site
from a42r_site.images import import_image, monogram_svg


def test_import_image_writes_three_sizes(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (2000, 1000), "red").save(src)
    import_image(src, tmp_path / "out", "x")
    assert Image.open(tmp_path / "out/x-640.webp").size == (640, 320)
    assert Image.open(tmp_path / "out/x-1280.webp").size == (1280, 640)
    assert (tmp_path / "out/x-640.jpg").exists()


def test_import_never_upscales(tmp_path):
    src = tmp_path / "s.png"
    Image.new("RGB", (1024, 500), "red").save(src)
    import_image(src, tmp_path / "out", "x")
    assert Image.open(tmp_path / "out/x-1280.webp").size == (1024, 500)
    assert Image.open(tmp_path / "out/x-640.webp").size == (640, 312)


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
