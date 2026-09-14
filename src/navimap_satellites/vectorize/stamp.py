"""Tampon OpenSeaMap + source sentinel-pilot. N'invente aucune profondeur."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from navimap_satellites.quality.disclaimer import DISCLAIMER, NOT_FOR_NAVIGATION
from navimap_satellites.quality.metadata import product_metadata

PILOT_SOURCE = "sentinel-pilot"
DATASET_COASTLINE = "sentinel-coastline"


def stamp_coastline_features(fc: dict[str, Any]) -> dict[str, Any]:
    """Ajoute natural=coastline / source=sentinel-pilot. Jamais de depth_area."""
    out = dict(fc)
    feats = []
    for i, feat in enumerate(fc.get("features") or []):
        item = dict(feat)
        props = dict(item.get("properties") or {})
        props.pop("seamark:type", None)
        props.pop("depth", None)
        props["source"] = PILOT_SOURCE
        props["natural"] = "coastline"
        props["kind"] = "coastline"
        props["name"] = "Trait de côte Sentinel (pilote)"
        props["disclaimer"] = DISCLAIMER
        props["navimap:not_for_navigation"] = True
        props.setdefault("id", f"{DATASET_COASTLINE}-{i}")
        item["properties"] = props
        feats.append(item)
    out["features"] = feats
    return out


def wrap_pilot_export(
    fc: dict[str, Any],
    *,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamped = stamp_coastline_features(fc)
    payload = json.dumps(stamped.get("features") or [], ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    meta = product_metadata(
        kind="coastline",
        method="acolite-l2r-mndwi-zero-contour",
        source=PILOT_SOURCE,
        extra={
            "dataset": DATASET_COASTLINE,
            "version": digest[:12],
            "sha256": digest,
            "soundings": False,
            "icesat_calibrated": False,
            "warning": NOT_FOR_NAVIGATION,
            **(extra_meta or {}),
        },
    )
    stamped["metadata"] = meta
    return stamped
