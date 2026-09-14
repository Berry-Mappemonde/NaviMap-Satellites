from pathlib import Path

import numpy as np
import pytest

from navimap_satellites.aoi import load_aoi
from navimap_satellites.cli import main
from navimap_satellites.pipeline_coastline import coastline_from_l2r

ROOT = Path(__file__).resolve().parents[1]


def _write_synthetic_l2r(path: Path) -> Path:
    netCDF4 = pytest.importorskip("netCDF4")
    n = 32
    lon1 = np.linspace(-1.4, -0.9, n)
    lat1 = np.linspace(46.0, 46.4, n)
    lon, lat = np.meshgrid(lon1, lat1)
    water = lon < -1.15
    green = np.where(water, 0.05, 0.20)
    swir = np.where(water, 0.01, 0.25)
    ds = netCDF4.Dataset(path, "w")
    ds.createDimension("y", n)
    ds.createDimension("x", n)
    for name, data in (("lon", lon), ("lat", lat), ("rhos_561", green), ("rhos_1612", swir)):
        var = ds.createVariable(name, "f4", ("y", "x"))
        var[:] = np.asarray(data, dtype=np.float32)
    ds.close()
    return path


def test_coastline_from_synthetic_l2r(tmp_path: Path):
    nc = _write_synthetic_l2r(tmp_path / "S2C_MSI_demo_T30TWR_L2R.nc")
    aoi = load_aoi(ROOT / "aois" / "la-rochelle.yaml")
    dest = tmp_path / "coastline.geojson"
    out = coastline_from_l2r(nc, aoi, dest)
    text = out.read_text(encoding="utf-8")
    assert "natural" in text
    assert "sentinel-pilot" in text
    assert "Ne convient pas à la navigation" in text
    assert '"soundings": false' in text.lower() or '"soundings": False' in text
    assert "seamark:type" not in text or "depth" not in text.split("seamark")[0]
    data = __import__("json").loads(text)
    assert data["features"]
    assert data["metadata"]["soundings"] is False
    assert all(f["properties"].get("natural") == "coastline" for f in data["features"])
    assert all(f["properties"].get("seamark:type") != "depth" for f in data["features"])


def test_cli_coastline_synthetic(tmp_path: Path):
    nc = _write_synthetic_l2r(tmp_path / "S2C_MSI_demo_T30TWR_L2R.nc")
    dest = tmp_path / "out.geojson"
    code = main(
        [
            "coastline",
            "--l2r",
            str(nc),
            "--aoi",
            str(ROOT / "aois" / "la-rochelle.yaml"),
            "--out",
            str(dest),
        ]
    )
    assert code == 0
    assert dest.is_file()
