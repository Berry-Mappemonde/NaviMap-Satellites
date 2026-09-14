"""L2R ACOLITE → GeoJSON coastline. Aucun sondage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from navimap_satellites.aoi import AOI
from navimap_satellites.correct.l2r import load_l2r
from navimap_satellites.extract.zero_contour import extract_lines
from navimap_satellites.vectorize.export import coastline_collection, write_geojson
from navimap_satellites.vectorize.stamp import wrap_pilot_export


def coastline_from_l2r(
    l2r_path: str | Path,
    aoi: AOI,
    dest: str | Path,
    *,
    extra_meta: dict[str, Any] | None = None,
) -> Path:
    scene = load_l2r(l2r_path)
    lines = extract_lines(scene.lon, scene.lat, scene.mndwi, aoi.bbox)
    if not lines:
        raise ValueError(
            "aucun trait de côte au seuil MNDWI = 0 dans cette emprise. "
            "Vérifiez la bbox et que le fichier est bien un *L2R*.nc."
        )
    raw = coastline_collection(
        lines,
        source="acolite-l2r",
        extra_meta={
            "green": scene.green_name,
            "swir": scene.swir_name,
            "l2r": scene.path.name,
            "aoi": aoi.id,
            "threshold": 0,
        },
    )
    wrapped = wrap_pilot_export(
        raw,
        extra_meta={
            "green": scene.green_name,
            "swir": scene.swir_name,
            "l2r": scene.path.name,
            "aoi": aoi.id,
            "bbox": list(aoi.bbox),
            **(extra_meta or {}),
        },
    )
    return write_geojson(wrapped, dest)
