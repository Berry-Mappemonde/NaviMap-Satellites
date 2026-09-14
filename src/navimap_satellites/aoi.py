"""Zones d'intérêt (AOI) décrites en YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class AOI:
    """Rectangle géographique : west, south, east, north (degrés, WGS84)."""

    id: str
    name: str
    bbox: BBox
    date_from: str
    date_to: str
    max_cloud_cover: float = 20.0
    collections: tuple[str, ...] = ("sentinel-2-l1c",)
    purpose: str = ""
    notes: str = ""
    water_type: str = "unknown"

    def validate(self) -> None:
        west, south, east, north = self.bbox
        if not (-180 <= west < east <= 180):
            raise ValueError(f"bbox longitude invalide : {self.bbox}")
        if not (-90 <= south < north <= 90):
            raise ValueError(f"bbox latitude invalide : {self.bbox}")
        if not (0 <= self.max_cloud_cover <= 100):
            raise ValueError("max_cloud_cover doit être entre 0 et 100")
        if self.date_from > self.date_to:
            raise ValueError("date_from doit précéder date_to")


def load_aoi(path: str | Path) -> AOI:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"AOI YAML invalide : {path}")
    return aoi_from_dict(raw)


def aoi_from_dict(raw: dict[str, Any]) -> AOI:
    bbox = raw.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox doit être [west, south, east, north]")
    collections = raw.get("collections") or ["sentinel-2-l1c"]
    aoi = AOI(
        id=str(raw["id"]),
        name=str(raw.get("name") or raw["id"]),
        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
        date_from=str(raw["date_from"]),
        date_to=str(raw["date_to"]),
        max_cloud_cover=float(raw.get("max_cloud_cover", 20)),
        collections=tuple(str(c) for c in collections),
        purpose=str(raw.get("purpose") or ""),
        notes=str(raw.get("notes") or "").strip(),
        water_type=str(raw.get("water_type") or "unknown"),
    )
    aoi.validate()
    return aoi
