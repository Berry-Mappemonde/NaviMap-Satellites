"""Scène synthétique : île, estran, eau peu profonde — pour tester sans satellite."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from navimap_satellites.aoi import AOI
from navimap_satellites.extract.l2w import ReflectanceScene
from navimap_satellites.extract.water_index import mndwi, water_mask
from navimap_satellites.process import vectorize_reflectance
from navimap_satellites.sdb.stumpf import calibrate_stumpf, stumpf_ratio

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
    """Exécute indices → trait de côte → plats clairs → SDB Stumpf."""
    raw = synthetic_scene(size)
    index = mndwi(raw["green"], raw["swir"])
    mask = water_mask(index)
    ratio = stumpf_ratio(raw["blue"], raw["green"], n=DEMO_N)
    m0, m1 = calibrate_stumpf(ratio, raw["truth_depth"], mask)
    scene = ReflectanceScene(
        blue=raw["blue"],
        green=raw["green"],
        swir=raw["swir"],
        nir=raw["nir"],
        bbox=DEMO_AOI.bbox,
        source="synthetic-demo",
    )
    return vectorize_reflectance(
        scene,
        out_dir,
        aoi=DEMO_AOI,
        apply_glint=True,
        stumpf_m0=m0,
        stumpf_m1=m1,
        sounding_step=8,
        min_shallow_pixels=32,
    )
