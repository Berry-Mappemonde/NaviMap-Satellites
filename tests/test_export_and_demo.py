import json
from pathlib import Path

from navimap_satellites.demo import run_demo, synthetic_scene
from navimap_satellites.extract.water_index import mndwi, water_mask
from navimap_satellites.vectorize.osm_schema import mapping_by_feature, schema_rows


def test_schema_has_coastline_and_sounding():
    rows = {r["feature"] for r in schema_rows()}
    assert "coastline_high_water" in rows
    assert "sounding" in rows
    mapping = mapping_by_feature("sounding")
    assert mapping.s57 == "SOUNDG"
    assert mapping.osm_tags["seamark:type"] == "depth"


def test_synthetic_center_is_land():
    scene = synthetic_scene(64)
    mid = 32
    assert scene["land"][mid, mid]
    index = mndwi(scene["green"], scene["swir"])
    mask = water_mask(index)
    assert not mask[mid, mid]
    assert mask[0, 0]


def test_demo_writes_geojson(tmp_path: Path):
    paths = run_demo(tmp_path, size=64)
    coast = json.loads(paths["coastline"].read_text(encoding="utf-8"))
    sound = json.loads(paths["soundings"].read_text(encoding="utf-8"))
    assert coast["type"] == "FeatureCollection"
    assert coast["features"]
    assert coast["metadata"]["not_for_navigation"] is True
    assert "navigation" in coast["metadata"]["warning"].lower()
    assert coast["features"][0]["properties"]["natural"] == "coastline"
    assert sound["features"]
    assert sound["features"][0]["properties"]["seamark:type"] == "depth"
    assert sound["features"][0]["properties"]["depth"] > 0
