"""Scène synthétique : île, estran, eau peu profonde — pour tester sans satellite."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from navimap_satellites.aoi import AOI
from navimap_satellites.basemap.gibs import write_preview_html
from navimap_satellites.extract.l2w import ReflectanceScene
from navimap_satellites.live import Publisher
from navimap_satellites.process import vectorize_reflectance
from navimap_satellites.sdb.control import synthetic_atl24_track

DEMO_AOI = AOI(
    id="demo-island",
    name="Île synthétique (démo)",
    bbox=(8.70, 42.52, 8.82, 42.60),
    date_from="2025-01-01",
    date_to="2025-12-31",
    purpose="tests sans imagerie",
    water_type="synthetic",
)

DEMO_GIBS_DATE = "2025-08-15"


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


def run_demo(
    out_dir: str | Path,
    *,
    size: int = 96,
    publisher: Publisher | None = None,
) -> dict[str, Path]:
    """Côte + plats + calage ATL24 synthétique + fond GIBS.

    Le calage imite une trace ICESat-2 (points épars), pas la grille entière.
    """
    raw = synthetic_scene(size)
    scene = ReflectanceScene(
        blue=raw["blue"],
        green=raw["green"],
        swir=raw["swir"],
        nir=raw["nir"],
        bbox=DEMO_AOI.bbox,
        source="synthetic-demo",
    )
    points = synthetic_atl24_track(raw["truth_depth"], DEMO_AOI.bbox)
    dest = Path(out_dir)
    paths = vectorize_reflectance(
        scene,
        dest,
        aoi=DEMO_AOI,
        apply_glint=True,
        atl24_points=points,
        sounding_step=8,
        min_shallow_pixels=32,
        publisher=publisher,
    )
    collections = {}
    for key in ("coastline", "shallow", "soundings", "atl24"):
        if key in paths:
            collections[key] = json.loads(paths[key].read_text(encoding="utf-8"))
    paths["preview"] = write_preview_html(
        dest / "preview.html",
        bbox=DEMO_AOI.bbox,
        title=DEMO_AOI.name,
        date=DEMO_GIBS_DATE,
        collections=collections,
    )
    return paths
