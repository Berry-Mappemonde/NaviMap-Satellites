from pathlib import Path

import numpy as np

from navimap_satellites.aoi import aoi_from_dict
from navimap_satellites.demo import synthetic_scene
from navimap_satellites.extract.l2w import L2WError, ReflectanceScene, read_l2w, sample_lonlat
from navimap_satellites.extract.shallow import shallow_mask
from navimap_satellites.extract.water_index import mndwi, water_mask
from navimap_satellites.process import vectorize_reflectance


def test_shallow_drops_tiny_speckle():
    water = np.ones((8, 8), dtype=bool)
    blue = np.full((8, 8), 0.01)
    green = np.full((8, 8), 0.01)
    blue[0, 0] = 1.0
    green[0, 0] = 1.0
    mask = shallow_mask(water, blue, green, quantile=0.9, min_pixels=4)
    assert not mask[0, 0]


def test_sample_lonlat_uses_bbox():
    scene = ReflectanceScene(
        blue=np.zeros((3, 3)),
        green=np.zeros((3, 3)),
        swir=np.zeros((3, 3)),
        bbox=(0.0, 10.0, 2.0, 12.0),
        source="t",
    )
    lon, lat = sample_lonlat(scene, np.array([0.0]), np.array([0.0]))
    assert lon[0] == 0.0
    assert lat[0] == 12.0


def test_vectorize_without_calibration(tmp_path: Path):
    raw = synthetic_scene(64)
    scene = ReflectanceScene(
        blue=raw["blue"],
        green=raw["green"],
        swir=raw["swir"],
        nir=raw["nir"],
        bbox=(8.70, 42.52, 8.82, 42.60),
        source="test",
    )
    aoi = aoi_from_dict(
        {
            "id": "t",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-01-01",
            "date_to": "2025-12-31",
        }
    )
    paths = vectorize_reflectance(scene, tmp_path, aoi=aoi, min_shallow_pixels=16)
    assert "coastline" in paths
    assert "shallow" in paths
    assert "soundings" not in paths
    assert paths["coastline"].is_file()


def test_water_center_still_land():
    raw = synthetic_scene(64)
    index = mndwi(raw["green"], raw["swir"])
    mask = water_mask(index)
    assert not mask[32, 32]


def test_read_l2w_missing_file(tmp_path: Path):
    try:
        read_l2w(tmp_path / "missing.nc", bbox=(0.0, 0.0, 1.0, 1.0))
    except L2WError as exc:
        assert "netCDF4" in str(exc) or "introuvable" in str(exc)
    else:
        raise AssertionError("L2WError attendu")
