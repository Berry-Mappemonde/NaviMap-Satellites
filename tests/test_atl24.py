import json

import httpx
import numpy as np
import pytest

from navimap_satellites.acquire.atl24 import (
    CLASS_BATHYMETRY,
    CLASS_SEA_SURFACE,
    load_atl24_geojson,
    points_from_arrays,
    search_atl24,
)
from navimap_satellites.aoi import aoi_from_dict
from navimap_satellites.demo import DEMO_AOI, synthetic_scene
from navimap_satellites.extract.l2w import ReflectanceScene
from navimap_satellites.sdb.control import calibrate_from_atl24, synthetic_atl24_track
from navimap_satellites.sdb.stumpf import stumpf_ratio


SAMPLE = {
    "feed": {
        "entry": [
            {
                "id": "G123",
                "title": "ATL24_20250815_0000_002_01.h5",
                "time_start": "2025-08-15T00:00:00.000Z",
                "time_end": "2025-08-15T00:20:00.000Z",
                "granule_size": "12.5",
                "links": [
                    {
                        "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                        "href": "https://example.test/ATL24.h5",
                    }
                ],
            }
        ]
    }
}


def _calvi():
    return aoi_from_dict(
        {
            "id": "calvi",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-06-01",
            "date_to": "2025-09-30",
        }
    )


def test_search_parses_cmr():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "ATL24" in str(request.url)
        assert "8.7" in str(request.url)
        assert "temporal" not in str(request.url)
        return httpx.Response(200, json=SAMPLE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    granules = search_atl24(_calvi(), client=client, url="https://cmr.test/granules.json")
    assert len(granules) == 1
    assert granules[0].title.startswith("ATL24_")
    assert granules[0].href.endswith(".h5")
    assert granules[0].size_mb == 12.5


def test_search_can_apply_aoi_dates():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=SAMPLE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    search_atl24(_calvi(), temporal=True, client=client, url="https://cmr.test/granules.json")
    assert "temporal" in seen[0]
    assert "2025-06-01" in seen[0]


def test_points_from_arrays_keeps_bathymetry_only():
    points = points_from_arrays(
        lon=[8.71, 8.72, 8.73],
        lat=[42.53, 42.54, 42.55],
        class_ph=[CLASS_BATHYMETRY, CLASS_SEA_SURFACE, CLASS_BATHYMETRY],
        surface_h=[0.2, 0.2, 0.1],
        ortho_h=[-3.0, 0.2, 0.4],
        confidence=[0.9, 0.8, 0.7],
        granule_id="G1",
    )
    assert len(points) == 1
    assert points[0].depth_m == pytest.approx(3.2)
    assert points[0].granule_id == "G1"


def test_load_geojson(tmp_path):
    path = tmp_path / "atl24.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [8.71, 42.53]},
                        "properties": {"depth": 4.2, "confidence": 0.8},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    points = load_atl24_geojson(path)
    assert len(points) == 1
    assert points[0].depth_m == 4.2


def test_synthetic_track_can_calibrate():
    raw = synthetic_scene(64)
    points = synthetic_atl24_track(raw["truth_depth"], DEMO_AOI.bbox)
    assert len(points) >= 8
    scene = ReflectanceScene(
        blue=raw["blue"],
        green=raw["green"],
        swir=raw["swir"],
        bbox=DEMO_AOI.bbox,
    )
    m0, m1, stats = calibrate_from_atl24(
        raw["blue"], raw["green"], points, scene=scene
    )
    assert stats["n"] >= 8
    assert stats["rmse_m"] is not None
    assert stats["rmse_m"] < 1.5
    ratio = stumpf_ratio(raw["blue"], raw["green"])
    assert np.isfinite(m0 + m1 * np.nanmean(ratio))


@pytest.mark.network
def test_live_atl24_cmr():
    granules = search_atl24(_calvi(), limit=3)
    assert isinstance(granules, list)
