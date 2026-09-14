"""Écriture GeoJSON + tags OpenSeaMap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from navimap_satellites.quality.metadata import product_metadata
from navimap_satellites.vectorize.osm_schema import mapping_by_feature


def _feature(
    geom: dict[str, Any],
    properties: dict[str, Any],
) -> dict[str, Any]:
    return {"type": "Feature", "geometry": geom, "properties": properties}


def coastline_collection(
    rings_lonlat: list[list[tuple[float, float]]],
    *,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mapping = mapping_by_feature("coastline_high_water")
    features = []
    for ring in rings_lonlat:
        props = dict(mapping.osm_tags)
        props.update(
            {
                "navimap:feature": mapping.feature,
                "navimap:s57": mapping.s57,
                "navimap:s101": mapping.s101,
                "navimap:not_for_navigation": True,
            }
        )
        features.append(_feature({"type": "LineString", "coordinates": ring}, props))
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": product_metadata(
            kind="coastline",
            method="mndwi+otsu+marching-squares",
            source=source,
            extra=extra_meta,
        ),
    }


def sounding_collection(
    points: list[tuple[float, float, float]],
    *,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """points = (lon, lat, depth_m)."""
    mapping = mapping_by_feature("sounding")
    features = []
    for lon, lat, depth in points:
        props = dict(mapping.osm_tags)
        props.update(
            {
                "depth": round(float(depth), 2),
                "navimap:feature": mapping.feature,
                "navimap:s57": mapping.s57,
                "navimap:s101": mapping.s101,
                "navimap:not_for_navigation": True,
            }
        )
        features.append(
            _feature({"type": "Point", "coordinates": [float(lon), float(lat)]}, props)
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": product_metadata(
            kind="soundings",
            method="stumpf-ratio",
            source=source,
            extra=extra_meta,
        ),
    }


def write_geojson(collection: dict[str, Any], path: str | Path) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
