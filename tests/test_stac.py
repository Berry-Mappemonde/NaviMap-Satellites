import json

import httpx
import pytest

from navimap_satellites.aoi import aoi_from_dict
from navimap_satellites.acquire.stac import pick_best_scene, search_scenes

SAMPLE = {
    "features": [
        {
            "id": "S2B_MSIL2A_FAKE",
            "collection": "sentinel-2-l2a",
            "bbox": [8.0, 42.0, 9.0, 43.0],
            "properties": {
                "datetime": "2025-08-25T10:05:59Z",
                "eo:cloud_cover": 1.8,
                "platform": "sentinel-2b",
                "grid:code": "MGRS-32TMN",
                "statistics": {"water": 70.0},
            },
            "assets": {
                "Product": {
                    "href": "https://zipper.dataspace.copernicus.eu/odata/v1/Products(060882f4-0a34-5f14-8e25-6876e4470b0d)/$value"
                },
                "thumbnail": {"href": "https://example.test/thumb.jpg"},
            },
        }
    ]
}


def test_search_parses_stac(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["collections"] == ["sentinel-2-l1c"]
        assert body["bbox"] == [8.7, 42.52, 8.82, 42.6]
        return httpx.Response(200, json=SAMPLE)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    aoi = aoi_from_dict(
        {
            "id": "calvi",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-06-01",
            "date_to": "2025-09-30",
            "max_cloud_cover": 15,
        }
    )
    scenes = search_scenes(aoi, client=client, url="https://stac.test/search")
    assert len(scenes) == 1
    assert scenes[0].id == "S2B_MSIL2A_FAKE"
    assert scenes[0].cloud_cover == 1.8
    assert scenes[0].tile == "MGRS-32TMN"
    assert scenes[0].extra["odata_id"] == "060882f4-0a34-5f14-8e25-6876e4470b0d"


def test_pick_best_scene_forces_l1c():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["collections"] == ["sentinel-2-l1c"]
        return httpx.Response(200, json=SAMPLE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    aoi = aoi_from_dict(
        {
            "id": "calvi",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-06-01",
            "date_to": "2025-09-30",
            "collections": ["sentinel-2-l2a"],
        }
    )
    scene = pick_best_scene(aoi, client=client, url="https://stac.test/search")
    assert scene.id == "S2B_MSIL2A_FAKE"


@pytest.mark.network
def test_live_cdse_calvi():
    aoi = aoi_from_dict(
        {
            "id": "calvi",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-06-01",
            "date_to": "2025-09-30",
            "max_cloud_cover": 20,
        }
    )
    scenes = search_scenes(aoi, limit=3)
    assert scenes
    assert scenes[0].id.startswith("S2")
    assert scenes[0].cloud_cover is not None
