from navimap_satellites.vectorize.chart_layers import layer_rows
from navimap_satellites.vectorize.osm_schema import mapping_by_feature


def test_layers_include_photo_and_non_bathy():
    rows = {r["id"]: r for r in layer_rows()}
    assert rows["photo"]["role"] == "fond"
    assert rows["atl24"]["role"] == "contrôle"
    assert rows["light"]["role"] == "hors"
    assert "mesure" in rows["photo"]["notes"].lower() or "JPEG" in rows["photo"]["notes"]


def test_calibration_mapping():
    mapping = mapping_by_feature("calibration_sounding")
    assert mapping.osm_tags["navimap:role"] == "calibration"
    assert mapping.s57 == "SOUNDG"
