"""Lecture d'un NetCDF L2R ACOLITE (rhos_*).

Le L1R est une étape intermédiaire — on le refuse.
Les PNG RGB rhos quasi noirs sont un aperçu mal étiré : les ignorer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from navimap_satellites.extract.water_index import mndwi

GREEN_HINTS = ("561", "560", "559")
SWIR_HINTS = ("1612", "1614", "1610", "1613")
PREFERRED_GREEN = "rhos_561"
PREFERRED_SWIR = "rhos_1612"


class L2RError(ValueError):
    """Fichier ACOLITE illisible ou mauvais niveau."""


@dataclass(frozen=True)
class L2RScene:
    path: Path
    lon: np.ndarray
    lat: np.ndarray
    mndwi: np.ndarray
    green_name: str
    swir_name: str


def pick_band(names: list[str], hints: tuple[str, ...]) -> str | None:
    """Choisit rhos_1612 avant rhos_1614 si les deux existent."""
    lower = {n.lower(): n for n in names}
    for hint in hints:
        for key, original in lower.items():
            if hint in key:
                return original
    return None


def find_l2r(path: str | Path) -> Path:
    src = Path(path).expanduser()
    if src.is_file():
        _reject_wrong_level(src)
        return src
    if not src.is_dir():
        raise L2RError(f"introuvable : {src}")
    files = sorted(p for p in src.glob("*L2R*.nc") if p.is_file())
    if not files:
        raise L2RError(
            f"aucun *L2R*.nc dans {src}. "
            "Ne prenez pas le L1R.nc (intermédiaire) ni un .SAFE L2A."
        )
    return files[0]


def _reject_wrong_level(path: Path) -> None:
    name = path.name.upper()
    if "L1R" in name and "L2R" not in name:
        raise L2RError(
            f"{path.name} est un L1R (étape intermédiaire). "
            "Utilisez le fichier *L2R*.nc."
        )
    if "MSIL2A" in name or (name.endswith(".SAFE") and "L2A" in name):
        raise L2RError(
            "Un produit L2A ESA n'est pas une entrée ACOLITE. "
            "ACOLITE part du L1C et écrit un L2R.nc."
        )


def as_float(raw) -> np.ndarray:
    if hasattr(raw, "filled"):
        return np.array(raw.filled(np.nan), dtype=float)
    return np.array(raw, dtype=float)


def ensure_2d(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if lon.ndim == 1 and lat.ndim == 1:
        return np.meshgrid(lon, lat)
    if lon.shape != lat.shape:
        raise L2RError("lon et lat n'ont pas la même forme")
    return lon, lat


def load_l2r(path: str | Path) -> L2RScene:
    nc = find_l2r(path)
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise L2RError(
            "netCDF4 manquant. Dans le Terminal : "
            "source .venv/bin/activate && pip install -e '.[dev]' "
            "— ou : conda activate acolite"
        ) from exc
    ds = Dataset(nc)
    try:
        names = list(ds.variables)
        green_name = pick_band(names, GREEN_HINTS)
        swir_name = pick_band(names, SWIR_HINTS)
        if not green_name or not swir_name:
            raise L2RError(f"bandes vert/SWIR introuvables dans {names}")
        lon_name = "lon" if "lon" in ds.variables else "longitude"
        lat_name = "lat" if "lat" in ds.variables else "latitude"
        if lon_name not in ds.variables or lat_name not in ds.variables:
            raise L2RError("pas de lon/lat dans le L2R")
        lon, lat = ensure_2d(as_float(ds[lon_name][:]), as_float(ds[lat_name][:]))
        green = as_float(ds[green_name][:])
        swir = as_float(ds[swir_name][:])
    finally:
        ds.close()
    if green.shape != lon.shape:
        raise L2RError("la bande et lon/lat n'ont pas la même taille")
    return L2RScene(
        path=nc,
        lon=lon,
        lat=lat,
        mndwi=mndwi(green, swir),
        green_name=green_name,
        swir_name=swir_name,
    )
