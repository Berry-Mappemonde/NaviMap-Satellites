"""Chaîne v0.2 : L1C → ACOLITE → trait de côte / plats clairs / sondages."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from navimap_satellites.aoi import AOI
from navimap_satellites.correct.glint import apply_hedley, hedley_slope
from navimap_satellites.extract.coastline import mask_contours
from navimap_satellites.extract.l2w import ReflectanceScene, sample_lonlat
from navimap_satellites.extract.shallow import shallow_mask
from navimap_satellites.extract.water_index import mndwi, water_mask
from navimap_satellites.sdb.stumpf import stumpf_depth
from navimap_satellites.vectorize.export import (
    coastline_collection,
    shallow_collection,
    sounding_collection,
    write_geojson,
)

STUMPF_N = 1000.0


def vectorize_reflectance(
    scene: ReflectanceScene,
    out_dir: str | Path,
    *,
    aoi: AOI | None = None,
    apply_glint: bool = True,
    stumpf_m0: float | None = None,
    stumpf_m1: float | None = None,
    sounding_step: int = 8,
    min_shallow_pixels: int = 64,
) -> dict[str, Path]:
    """Écrit coastline.geojson, shallow.geojson, et soundings.geojson si calé."""
    index = mndwi(scene.green, scene.swir)
    wet = water_mask(index)
    blue, green = scene.blue, scene.green
    if apply_glint and scene.nir is not None:
        slope_b = hedley_slope(blue, scene.nir, wet)
        slope_g = hedley_slope(green, scene.nir, wet)
        blue = apply_hedley(blue, scene.nir, slope_b)
        green = apply_hedley(green, scene.nir, slope_g)
    coast_rings = _rings_lonlat(wet, scene)
    shallow = shallow_mask(wet, blue, green, min_pixels=min_shallow_pixels)
    shallow_rings = _rings_lonlat(shallow, scene)

    dest = Path(out_dir)
    extra = {
        "aoi": aoi.id if aoi else "",
        "glint": "hedley" if apply_glint and scene.nir is not None else "none",
        "not_for_navigation": True,
    }
    paths: dict[str, Path] = {}
    paths["coastline"] = write_geojson(
        coastline_collection(coast_rings, source=scene.source, extra_meta=extra),
        dest / "coastline.geojson",
    )
    paths["shallow"] = write_geojson(
        shallow_collection(shallow_rings, source=scene.source, extra_meta=extra),
        dest / "shallow.geojson",
    )
    if stumpf_m0 is not None and stumpf_m1 is not None:
        depth = stumpf_depth(
            blue,
            green,
            m0=stumpf_m0,
            m1=stumpf_m1,
            n=STUMPF_N,
            water_mask=wet,
            max_depth_m=15.0,
        )
        points = _sample_soundings(depth, scene, step=sounding_step)
        cal = dict(extra)
        cal.update(
            {
                "stumpf_m0": stumpf_m0,
                "stumpf_m1": stumpf_m1,
                "calibrated": True,
            }
        )
        paths["soundings"] = write_geojson(
            sounding_collection(points, source=scene.source, extra_meta=cal),
            dest / "soundings.geojson",
        )
    return paths


def _rings_lonlat(mask: np.ndarray, scene: ReflectanceScene) -> list[list[tuple[float, float]]]:
    height, width = scene.blue.shape
    rings: list[list[tuple[float, float]]] = []
    for ring in mask_contours(mask):
        if ring.size == 0:
            continue
        lon, lat = sample_lonlat(scene, ring[:, 0], ring[:, 1])
        coords = [(float(x), float(y)) for x, y in zip(lon, lat, strict=True)]
        if len(coords) >= 2 and coords[0] != coords[-1]:
            coords.append(coords[0])
        if len(coords) >= 4:
            rings.append(coords)
    return rings


def _sample_soundings(
    depth: np.ndarray,
    scene: ReflectanceScene,
    step: int,
) -> list[tuple[float, float, float]]:
    rows, cols = np.where(np.isfinite(depth))
    points: list[tuple[float, float, float]] = []
    for r, c in zip(rows, cols, strict=True):
        if r % step or c % step:
            continue
        lon, lat = sample_lonlat(scene, np.array([r]), np.array([c]))
        points.append((float(lon[0]), float(lat[0]), float(depth[r, c])))
    return points
