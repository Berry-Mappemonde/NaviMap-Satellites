"""Recherche de scènes Sentinel via le catalogue STAC public du CDSE.

La recherche ne demande pas de compte. Le téléchargement des images, lui,
passe par l'identité Copernicus Data Space (voir acquire.auth).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from navimap_satellites.aoi import AOI, BBox

_ODATA_UUID = re.compile(r"Products\(([0-9a-fA-F-]{36})\)")

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
            "odata_id": self.extra.get("odata_id"),
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


def pick_best_scene(
    aoi: AOI,
    *,
    limit: int = 12,
    l1c: bool = True,
    client: httpx.Client | None = None,
    url: str = STAC_SEARCH_URL,
) -> Scene:
    """Première scène (nuages croissants), L1C par défaut pour ACOLITE."""
    target = aoi.for_l1c() if l1c else aoi
    scenes = search_scenes(target, limit=limit, client=client, url=url)
    if not scenes:
        raise LookupError(
            "Aucune scène sous le seuil de nuages. Élargissez les dates ou max_cloud_cover."
        )
    return scenes[0]


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
            "odata_id": _odata_id_from_href(product.get("href")),
        },
    )


def _odata_id_from_href(href: str | None) -> str | None:
    if not href:
        return None
    match = _ODATA_UUID.search(href)
    return match.group(1) if match else None
