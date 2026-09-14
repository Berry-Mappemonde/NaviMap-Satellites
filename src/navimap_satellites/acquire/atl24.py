"""ICESat-2 ATL24 : catalogue CMR et points de calage.

La recherche est publique. Le téléchargement HDF5 demandera Earthdata.
Ces points calent Stumpf ; ce ne sont pas des sondages de carte marine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from navimap_satellites.aoi import AOI, BBox

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
CMR_CLIENT_ID = "navimap-satellites"
DEFAULT_TIMEOUT_S = 45.0

CLASS_BATHYMETRY = 40
CLASS_SEA_SURFACE = 41
H5_BEAMS = ("gt1l", "gt1r", "gt2l", "gt2r", "gt3l", "gt3r")


class Atl24Error(RuntimeError):
    """Granule ou fichier ATL24 illisible."""


@dataclass(frozen=True)
class Atl24Granule:
    id: str
    title: str
    time_start: str
    time_end: str
    short_name: str
    size_mb: float | None = None
    href: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "short_name": self.short_name,
            "size_mb": self.size_mb,
            "href": self.href,
        }


@dataclass(frozen=True)
class Atl24Point:
    """Photon de fond (profondeur instantanée, mètres positifs sous la surface)."""

    lon: float
    lat: float
    depth_m: float
    confidence: float | None = None
    granule_id: str = ""
    kind: str = "bathymetry"

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.lon, self.lat, self.depth_m)


def search_granules(
    short_name: str,
    bbox: BBox,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    client: httpx.Client | None = None,
    url: str = CMR_GRANULES_URL,
) -> list[Atl24Granule]:
    """Liste les granules CMR qui croisent la bbox. Sans compte."""
    west, south, east, north = bbox
    params: dict[str, Any] = {
        "short_name": short_name,
        "bounding_box": f"{west},{south},{east},{north}",
        "page_size": int(limit),
    }
    if date_from and date_to:
        params["temporal"] = f"{date_from}T00:00:00Z,{date_to}T23:59:59Z"
    own = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    try:
        response = http.get(
            url,
            params=params,
            headers={"Accept": "application/json", "Client-Id": CMR_CLIENT_ID},
        )
        response.raise_for_status()
        entries = ((response.json() or {}).get("feed") or {}).get("entry") or []
    finally:
        if own:
            http.close()
    return [_granule_from_entry(item, short_name) for item in entries]


def search_atl24(
    aoi: AOI,
    *,
    limit: int = 20,
    client: httpx.Client | None = None,
    url: str = CMR_GRANULES_URL,
) -> list[Atl24Granule]:
    return search_granules(
        "ATL24",
        aoi.bbox,
        date_from=aoi.date_from,
        date_to=aoi.date_to,
        limit=limit,
        client=client,
        url=url,
    )


def points_from_arrays(
    lon: Any,
    lat: Any,
    *,
    class_ph: Any | None = None,
    surface_h: Any | None = None,
    ortho_h: Any | None = None,
    depth_m: Any | None = None,
    confidence: Any | None = None,
    granule_id: str = "",
) -> list[Atl24Point]:
    """Construit des points fond à partir des tableaux ATL24 (class 40)."""
    import numpy as np

    x = np.asarray(lon, dtype=np.float64).ravel()
    y = np.asarray(lat, dtype=np.float64).ravel()
    n = x.size
    if y.size != n:
        raise Atl24Error("lon et lat n'ont pas la même taille.")
    if depth_m is not None:
        z = np.asarray(depth_m, dtype=np.float64).ravel()
    elif surface_h is not None and ortho_h is not None:
        z = np.asarray(surface_h, dtype=np.float64).ravel() - np.asarray(
            ortho_h, dtype=np.float64
        ).ravel()
    else:
        raise Atl24Error("Il faut depth_m, ou surface_h et ortho_h.")
    if z.size != n:
        raise Atl24Error("Les profondeurs n'ont pas la taille des coordonnées.")
    if class_ph is None:
        cls = np.full(n, CLASS_BATHYMETRY)
    else:
        cls = np.asarray(class_ph).ravel()
        if cls.size != n:
            raise Atl24Error("class_ph n'a pas la taille des coordonnées.")
    if confidence is None:
        conf = np.full(n, np.nan)
    else:
        conf = np.asarray(confidence, dtype=np.float64).ravel()
        if conf.size != n:
            conf = np.resize(conf, n)
    out: list[Atl24Point] = []
    for i in range(n):
        if int(cls[i]) != CLASS_BATHYMETRY:
            continue
        depth = float(z[i])
        if not (depth > 0) or not np.isfinite(depth):
            continue
        if not (np.isfinite(x[i]) and np.isfinite(y[i])):
            continue
        cval = float(conf[i]) if np.isfinite(conf[i]) else None
        out.append(
            Atl24Point(
                lon=float(x[i]),
                lat=float(y[i]),
                depth_m=depth,
                confidence=cval,
                granule_id=granule_id,
            )
        )
    return out


def load_atl24_geojson(path: str | Path) -> list[Atl24Point]:
    """Lit des points (lon, lat, depth) depuis un GeoJSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    features = raw.get("features") if isinstance(raw, dict) else raw
    if not isinstance(features, list):
        raise Atl24Error(f"GeoJSON ATL24 invalide : {path}")
    points: list[Atl24Point] = []
    for feat in features:
        if not isinstance(feat, dict):
            continue
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        props = feat.get("properties") or {}
        depth = props.get("depth", props.get("navimap:depth"))
        if depth is None:
            continue
        conf = props.get("confidence", props.get("navimap:confidence"))
        points.append(
            Atl24Point(
                lon=float(coords[0]),
                lat=float(coords[1]),
                depth_m=float(depth),
                confidence=None if conf is None else float(conf),
                granule_id=str(props.get("navimap:granule") or props.get("granule") or ""),
                kind=str(props.get("navimap:kind") or "bathymetry"),
            )
        )
    return points


def load_atl24_h5(path: str | Path) -> list[Atl24Point]:
    """Lit un granule ATL24 HDF5 (h5py optionnel)."""
    try:
        import h5py
    except ImportError as exc:
        raise Atl24Error(
            "Lecture HDF5 impossible : installez h5py (`pip install -e '.[atl24]'`)."
        ) from exc
    nc_path = Path(path)
    if not nc_path.is_file():
        raise Atl24Error(f"Fichier ATL24 introuvable : {nc_path}")
    points: list[Atl24Point] = []
    with h5py.File(nc_path, "r") as handle:
        for beam in H5_BEAMS:
            if beam not in handle:
                continue
            group = handle[beam]
            lon = _h5_first(group, ("lon_ph", "longitude", "lon"))
            lat = _h5_first(group, ("lat_ph", "latitude", "lat"))
            if lon is None or lat is None:
                continue
            depth = _h5_first(group, ("ortho_depth", "depth", "photon_depth"))
            surface = _h5_first(group, ("surface_h", "surf_h"))
            ortho = _h5_first(group, ("ortho_h", "ortho_height"))
            cls = _h5_first(group, ("class_ph", "class"))
            conf = _h5_first(group, ("confidence", "conf_ph"))
            kwargs: dict[str, Any] = {"class_ph": cls, "confidence": conf, "granule_id": nc_path.name}
            if depth is not None:
                kwargs["depth_m"] = depth
            else:
                kwargs["surface_h"] = surface
                kwargs["ortho_h"] = ortho
            try:
                points.extend(points_from_arrays(lon, lat, **kwargs))
            except Atl24Error:
                continue
    return points


def _h5_first(group: Any, names: tuple[str, ...]) -> Any | None:
    for name in names:
        if name in group:
            return group[name][:]
    return None


def _granule_from_entry(item: dict[str, Any], short_name: str) -> Atl24Granule:
    links = item.get("links") or []
    size_raw = item.get("granule_size")
    try:
        size_mb = float(size_raw) if size_raw is not None else None
    except (TypeError, ValueError):
        size_mb = None
    return Atl24Granule(
        id=str(item.get("id") or item.get("producer_granule_id") or ""),
        title=str(item.get("title") or item.get("producer_granule_id") or ""),
        time_start=str(item.get("time_start") or ""),
        time_end=str(item.get("time_end") or ""),
        short_name=short_name,
        size_mb=size_mb,
        href=_data_href(links),
    )


def _data_href(links: list[dict[str, Any]]) -> str | None:
    fallback = None
    for link in links:
        href = link.get("href")
        if not href:
            continue
        rel = str(link.get("rel") or "")
        if href.lower().endswith(".xml"):
            continue
        if rel.endswith("/data#") or "/data#" in rel:
            return str(href)
        if fallback is None and link.get("hreflang") != "en-US":
            fallback = str(href)
    return fallback
