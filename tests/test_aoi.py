from pathlib import Path

import pytest

from navimap_satellites.aoi import aoi_from_dict, load_aoi

ROOT = Path(__file__).resolve().parents[1]


def test_load_calvi():
    aoi = load_aoi(ROOT / "aois" / "calvi.yaml")
    assert aoi.id == "calvi"
    assert aoi.bbox[0] < aoi.bbox[2]
    assert aoi.water_type == "case-1-ish"
    assert aoi.collections == ("sentinel-2-l1c",)


def test_load_la_rochelle():
    aoi = load_aoi(ROOT / "aois" / "la-rochelle.yaml")
    assert aoi.id == "la-rochelle"
    assert aoi.bbox == (-1.666, 45.655, -0.668, 46.653)
    assert aoi.collections == ("sentinel-2-l1c",)


def test_invalid_bbox():
    with pytest.raises(ValueError):
        aoi_from_dict(
            {
                "id": "x",
                "bbox": [10, 0, 1, 2],
                "date_from": "2025-01-01",
                "date_to": "2025-02-01",
            }
        )
