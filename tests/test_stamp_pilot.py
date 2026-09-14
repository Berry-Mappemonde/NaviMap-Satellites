from navimap_satellites.vectorize.stamp import PILOT_SOURCE, stamp_coastline_features, wrap_pilot_export


def test_stamp_coastline_no_depth():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-1.2, 46.1], [-1.1, 46.2]]},
                "properties": {"seamark:type": "depth", "depth": 4.2},
            }
        ],
    }
    out = stamp_coastline_features(raw)
    props = out["features"][0]["properties"]
    assert props["source"] == PILOT_SOURCE
    assert props["natural"] == "coastline"
    assert "depth" not in props
    assert props.get("seamark:type") != "depth"


def test_wrap_has_sha_and_no_soundings():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-1.2, 46.1], [-1.1, 46.2]]},
                "properties": {"natural": "coastline"},
            }
        ],
    }
    wrapped = wrap_pilot_export(raw)
    meta = wrapped["metadata"]
    assert meta["soundings"] is False
    assert meta["icesat_calibrated"] is False
    assert meta["not_for_navigation"] is True
    assert len(meta["sha256"]) == 64
