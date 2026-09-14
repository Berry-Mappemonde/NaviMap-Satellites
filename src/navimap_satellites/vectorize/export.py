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


def shallow_collection(
    rings_lonlat: list[list[tuple[float, float]]],
    *,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Grands plats clairs (récif / banc). Pas un obstacle isolé."""
    mapping = mapping_by_feature("reef")
    features = []
    for ring in rings_lonlat:
        props = dict(mapping.osm_tags)
        props.update(
            {
                "navimap:feature": mapping.feature,
                "navimap:s57": mapping.s57,
                "navimap:s101": mapping.s101,
                "navimap:not_for_navigation": True,
                "navimap:note": (
                    "Grande tache claire en eau peu profonde. "
                    "Un écueil métrique isolé reste invisible à 10 m."
                ),
            }
        )
        features.append(
            _feature({"type": "Polygon", "coordinates": [ring]}, props)
        )
    extra = {
        "limitation": (
            "Pas de détection d'obstacles isolés ni de nappes de plastique. "
            "Indication de formes larges seulement."
        )
    }
    if extra_meta:
        extra.update(extra_meta)
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": product_metadata(
            kind="shallow",
            method="mndwi+bright-water+min-area",
            source=source,
            extra=extra,
        ),
    }


def atl24_collection(
    points: list[tuple[float, float, float] | Any],
    *,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Points de calage ICESat-2. Pas des sondages de carte."""
    mapping = mapping_by_feature("calibration_sounding")
    features = []
    for item in points:
        if hasattr(item, "lon"):
            lon, lat, depth = float(item.lon), float(item.lat), float(item.depth_m)
            confidence = getattr(item, "confidence", None)
            granule = getattr(item, "granule_id", "")
        else:
            lon, lat, depth = item
            confidence = None
            granule = ""
        props = dict(mapping.osm_tags)
        props.update(
            {
                "depth": round(float(depth), 2),
                "navimap:feature": mapping.feature,
                "navimap:s57": mapping.s57,
                "navimap:s101": mapping.s101,
                "navimap:not_for_navigation": True,
                "navimap:role": "calibration",
            }
        )
        if confidence is not None:
            props["confidence"] = confidence
        if granule:
            props["navimap:granule"] = granule
        features.append(
            _feature({"type": "Point", "coordinates": [float(lon), float(lat)]}, props)
        )
    extra = {
        "limitation": (
            "Points de calage le long d'une trace lidar. "
            "Ce n'est pas un semis de carte, pas une grille de baie."
        )
    }
    if extra_meta:
        extra.update(extra_meta)
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": product_metadata(
            kind="atl24",
            method="icesat2-atl24",
            source=source,
            extra=extra,
        ),
    }


def write_geojson(collection: dict[str, Any], path: str | Path) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
