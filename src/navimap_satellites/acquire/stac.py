"""Recherche de scènes Sentinel via le catalogue STAC public du CDSE.

La recherche ne demande pas de compte. Pour ACOLITE, la collection AOI
doit être ``sentinel-2-l1c`` (le L2A ESA est refusé par ACOLITE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from navimap_satellites.aoi import AOI, BBox

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"
DEFAULT_TIMEOUT_S = 45.0


@dataclass(frozen=True)
class Scene:
    id: str
    collection: str
    datetime: str
    cloud_cover: float | None
    platform: str
    bbox: BBox
    tile: str
    product_href: str | None
    thumbnail_href: str | None
    water_percent: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "collection": self.collection,
            "datetime": self.datetime,
            "cloud_cover": self.cloud_cover,
            "platform": self.platform,
            "bbox": list(self.bbox),
            "tile": self.tile,
            "product_href": self.product_href,
            "thumbnail_href": self.thumbnail_href,
            "water_percent": self.water_percent,
        }


def search_scenes(
    aoi: AOI,
    *,
    limit: int = 20,
    client: httpx.Client | None = None,
    url: str = STAC_SEARCH_URL,
) -> list[Scene]:
    """Interroge le STAC CDSE et renvoie les scènes, nuages croissants."""
    body = {
        "collections": list(aoi.collections),
        "bbox": list(aoi.bbox),
        "datetime": f"{aoi.date_from}T00:00:00Z/{aoi.date_to}T23:59:59Z",
        "limit": int(limit),
        "query": {"eo:cloud_cover": {"lt": float(aoi.max_cloud_cover)}},
    }
    own = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    try:
        response = http.post(url, json=body)
        response.raise_for_status()
        payload = response.json()
    finally:
        if own:
            http.close()
    features = payload.get("features") or []
    scenes = [_scene_from_feature(item) for item in features]
    scenes.sort(key=lambda s: (s.cloud_cover is None, s.cloud_cover or 100.0, s.datetime))
    return scenes


def _scene_from_feature(item: dict[str, Any]) -> Scene:
    props = item.get("properties") or {}
    assets = item.get("assets") or {}
    bbox_raw = item.get("bbox") or [0, 0, 0, 0]
    stats = props.get("statistics") or {}
    product = assets.get("Product") or {}
    thumb = assets.get("thumbnail") or {}
    cloud = props.get("eo:cloud_cover")
    water = stats.get("water")
    return Scene(
        id=str(item.get("id") or ""),
        collection=str(item.get("collection") or ""),
        datetime=str(props.get("datetime") or ""),
        cloud_cover=None if cloud is None else float(cloud),
        platform=str(props.get("platform") or ""),
        bbox=(float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3])),
        tile=str(props.get("grid:code") or ""),
        product_href=product.get("href"),
        thumbnail_href=thumb.get("href"),
        water_percent=None if water is None else float(water),
        extra={
            "orbit": props.get("sat:relative_orbit"),
            "sun_elevation": props.get("view:sun_elevation"),
        },
    )
