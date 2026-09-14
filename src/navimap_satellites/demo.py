"""Scène synthétique : île, estran, eau peu profonde — pour tester sans satellite."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from navimap_satellites.aoi import AOI
from navimap_satellites.extract.coastline import contours_to_lonlat, mask_contours
from navimap_satellites.extract.water_index import mndwi, water_mask
from navimap_satellites.sdb.stumpf import calibrate_stumpf, stumpf_depth, stumpf_ratio
from navimap_satellites.vectorize.export import (
    coastline_collection,
    sounding_collection,
    write_geojson,
)

DEMO_AOI = AOI(
    id="demo-island",
    name="Île synthétique (démo)",
    bbox=(8.70, 42.52, 8.82, 42.60),
    date_from="2025-01-01",
    date_to="2025-12-31",
    purpose="tests sans imagerie",
    water_type="synthetic",
)

DEMO_N = 1000.0


def synthetic_scene(size: int = 96) -> dict[str, np.ndarray]:
    """Île circulaire, pente sous-marine, terre végétale."""
    yy, xx = np.mgrid[0:size, 0:size]
    cy = cx = (size - 1) / 2.0
    radius = np.hypot(yy - cy, xx - cx)
    land = radius < size * 0.18
    # Profondeur croissante hors de l'île (0 au rivage → 12 m au large).
    shore = size * 0.18
    depth = np.clip((radius - shore) * 0.28, 0.0, 12.0)
    depth = np.where(land, np.nan, depth)

    # Réflectances : terre = NIR élevé ; eau = bleu/vert qui s'atténuent.
    green = np.where(land, 0.08, 0.04 * np.exp(-0.12 * np.nan_to_num(depth, nan=0.0)))
    blue = np.where(land, 0.05, 0.035 * np.exp(-0.08 * np.nan_to_num(depth, nan=0.0)))
    nir = np.where(land, 0.35, 0.012)
    swir = np.where(land, 0.22, 0.006)
    green = green + np.where(land, 0.0, 0.002)
    return {
        "blue": blue.astype(np.float64),
        "green": green.astype(np.float64),
        "nir": nir.astype(np.float64),
        "swir": swir.astype(np.float64),
        "truth_depth": depth.astype(np.float64),
        "land": land,
    }


def run_demo(out_dir: str | Path, *, size: int = 96) -> dict[str, Path]:
    """Exécute indices → trait de côte → SDB Stumpf, écrit deux GeoJSON."""
    scene = synthetic_scene(size)
    index = mndwi(scene["green"], scene["swir"])
    mask = water_mask(index)
    rings = contours_to_lonlat(
        mask_contours(mask),
        DEMO_AOI.bbox,
        height=size,
        width=size,
    )
    ratio = stumpf_ratio(scene["blue"], scene["green"], n=DEMO_N)
    m0, m1 = calibrate_stumpf(ratio, scene["truth_depth"], mask)
    depth = stumpf_depth(
        scene["blue"],
        scene["green"],
        m0=m0,
        m1=m1,
        n=DEMO_N,
        water_mask=mask,
        max_depth_m=15.0,
    )
    soundings = _sample_soundings(depth, DEMO_AOI.bbox, step=8)
    dest = Path(out_dir)
    coast_path = write_geojson(
        coastline_collection(
            rings,
            source="synthetic-demo",
            extra_meta={"aoi": DEMO_AOI.id, "size": size},
        ),
        dest / "coastline.geojson",
    )
    sound_path = write_geojson(
        sounding_collection(
            soundings,
            source="synthetic-demo",
            extra_meta={
                "aoi": DEMO_AOI.id,
                "stumpf_m0": round(m0, 4),
                "stumpf_m1": round(m1, 4),
                "calibrated": True,
                "calibration": "régression sur la profondeur synthétique (démo seulement)",
            },
        ),
        dest / "soundings.geojson",
    )
    return {"coastline": coast_path, "soundings": sound_path}


def _sample_soundings(
    depth: np.ndarray,
    bbox: tuple[float, float, float, float],
    step: int,
) -> list[tuple[float, float, float]]:
    from navimap_satellites.extract.coastline import pixel_to_lonlat

    rows, cols = np.where(np.isfinite(depth))
    points: list[tuple[float, float, float]] = []
    h, w = depth.shape
    for r, c in zip(rows, cols, strict=True):
        if r % step or c % step:
            continue
        lon, lat = pixel_to_lonlat(np.array([r]), np.array([c]), bbox, h, w)
        points.append((float(lon[0]), float(lat[0]), float(depth[r, c])))
    return points
