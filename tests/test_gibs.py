from pathlib import Path

from navimap_satellites.basemap.gibs import (
    gibs_layer,
    tile_url_template,
    worldview_url,
    write_preview_html,
)


def test_viirs_url_has_date_and_xyz():
    url = tile_url_template("viirs", date="2025-08-15")
    assert "VIIRS_SNPP_CorrectedReflectance_TrueColor" in url
    assert "2025-08-15" in url
    assert "{z}/{y}/{x}" in url
    assert url.startswith("https://gibs.earthdata.nasa.gov/")


def test_blue_marble_has_no_calendar_date():
    url = tile_url_template("blue-marble")
    assert "BlueMarble_NextGeneration" in url
    assert "2025" not in url
    assert gibs_layer("blue-marble").timed is False


def test_worldview_contains_bbox():
    url = worldview_url((8.70, 42.52, 8.82, 42.60), date="2025-08-15")
    assert "worldview.earthdata.nasa.gov" in url
    assert "8.65" in url
    assert "42.47" in url


def test_preview_html_embeds_disclaimer(tmp_path: Path):
    dest = write_preview_html(
        tmp_path / "preview.html",
        bbox=(8.70, 42.52, 8.82, 42.60),
        title="Calvi",
        date="2025-08-15",
        collections={"coastline": {"type": "FeatureCollection", "features": []}},
    )
    text = dest.read_text(encoding="utf-8")
    assert "Ne convient pas à la navigation" in text
    assert "gibs.earthdata.nasa.gov" in text
    assert "pas que la bathymétrie" in text
    assert "<script>" in text
