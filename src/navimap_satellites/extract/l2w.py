"""Lecture d'un NetCDF ACOLITE L2W → bandes de réflectance de surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from navimap_satellites.aoi import BBox

# Noms fréquents ACOLITE / longueurs d'onde Sentinel-2 (nm).
_BAND_ALIASES: dict[str, tuple[str, ...]] = {
    "blue": ("rhos_492", "rhos_490", "rhos_443", "rhow_492", "rhow_443"),
    "green": ("rhos_560", "rhos_559", "rhow_560"),
    "red": ("rhos_665", "rhow_665"),
    "nir": ("rhos_833", "rhos_842", "rhos_865", "rhow_833"),
    "swir": ("rhos_1614", "rhos_1610", "rhos_2202", "rhos_2190", "rhow_1614"),
}


class L2WError(RuntimeError):
    """NetCDF illisible ou extra netCDF4 manquant."""


@dataclass
class ReflectanceScene:
    """Bandes alignées, bbox WGS84, éventuellement grilles lon/lat ACOLITE."""

    blue: np.ndarray
    green: np.ndarray
    swir: np.ndarray
    bbox: BBox
    nir: np.ndarray | None = None
    red: np.ndarray | None = None
    lon: np.ndarray | None = None
    lat: np.ndarray | None = None
    source: str = "l2w"

    @property
    def shape(self) -> tuple[int, int]:
        return tuple(int(x) for x in self.blue.shape)  # type: ignore[return-value]


def read_l2w(path: str | Path, *, bbox: BBox | None = None) -> ReflectanceScene:
    """Ouvre un L2W.nc. Nécessite `pip install -e '.[l2w]'`."""
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise L2WError(
            "Lecture L2W impossible : installez netCDF4 (`pip install -e '.[l2w]'`)."
        ) from exc
    nc_path = Path(path)
    if not nc_path.is_file():
        raise L2WError(f"Fichier L2W introuvable : {nc_path}")
    with Dataset(str(nc_path), "r") as dataset:
        names = set(dataset.variables)
        blue = _first_var(dataset, names, _BAND_ALIASES["blue"])
        green = _first_var(dataset, names, _BAND_ALIASES["green"])
        swir = _first_var(dataset, names, _BAND_ALIASES["swir"])
        nir = _optional_var(dataset, names, _BAND_ALIASES["nir"])
        red = _optional_var(dataset, names, _BAND_ALIASES["red"])
        lon, lat = _lon_lat(dataset, names, blue.shape)
    used_bbox = bbox or _bbox_from_lonlat(lon, lat)
    return ReflectanceScene(
        blue=blue,
        green=green,
        swir=swir,
        nir=nir,
        red=red,
        lon=lon,
        lat=lat,
        bbox=used_bbox,
        source=str(nc_path.name),
    )


def sample_lonlat(
    scene: ReflectanceScene,
    rows: np.ndarray,
    cols: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Pixel (ligne, colonne) → lon/lat. Grilles ACOLITE si présentes, sinon bbox."""
    from navimap_satellites.extract.coastline import pixel_to_lonlat

    height, width = scene.blue.shape
    if scene.lon is None or scene.lat is None:
        return pixel_to_lonlat(rows, cols, scene.bbox, height, width)
    lon2d, lat2d = _as_2d_lonlat(scene.lon, scene.lat, scene.blue.shape)
    ri = np.clip(np.rint(np.asarray(rows, dtype=np.float64)).astype(int), 0, height - 1)
    ci = np.clip(np.rint(np.asarray(cols, dtype=np.float64)).astype(int), 0, width - 1)
    return lon2d[ri, ci], lat2d[ri, ci]


def _first_var(dataset, names: set[str], aliases: tuple[str, ...]) -> np.ndarray:
    found = _optional_var(dataset, names, aliases)
    if found is None:
        raise L2WError(f"Bande absente du L2W (cherché : {', '.join(aliases)}).")
    return found


def _optional_var(dataset, names: set[str], aliases: tuple[str, ...]) -> np.ndarray | None:
    for alias in aliases:
        if alias in names:
            return np.array(dataset.variables[alias][:], dtype=np.float64)
    return None


def _lon_lat(dataset, names: set[str], shape: tuple[int, ...]) -> tuple[np.ndarray | None, np.ndarray | None]:
    lon_name = next((n for n in ("lon", "longitude") if n in names), None)
    lat_name = next((n for n in ("lat", "latitude") if n in names), None)
    if not lon_name or not lat_name:
        return None, None
    lon = np.array(dataset.variables[lon_name][:], dtype=np.float64)
    lat = np.array(dataset.variables[lat_name][:], dtype=np.float64)
    lon2d, lat2d = _as_2d_lonlat(lon, lat, shape)
    return lon2d, lat2d


def _as_2d_lonlat(
    lon: np.ndarray,
    lat: np.ndarray,
    shape: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray]:
    if lon.ndim == 2 and lat.ndim == 2:
        return lon, lat
    if lon.ndim == 1 and lat.ndim == 1:
        lon2d, lat2d = np.meshgrid(lon, lat)
        return lon2d, lat2d
    raise L2WError("Grilles lon/lat de forme inattendue.")


def _bbox_from_lonlat(lon: np.ndarray | None, lat: np.ndarray | None) -> BBox:
    if lon is None or lat is None:
        raise L2WError("Pas de lon/lat dans le L2W et aucune bbox fournie.")
    return (
        float(np.nanmin(lon)),
        float(np.nanmin(lat)),
        float(np.nanmax(lon)),
        float(np.nanmax(lat)),
    )
