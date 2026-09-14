"""Calage Stumpf sur des points épars (ICESat-2 ATL24)."""

from __future__ import annotations

from typing import Any

import numpy as np

from navimap_satellites.acquire.atl24 import Atl24Point
from navimap_satellites.aoi import BBox
from navimap_satellites.extract.coastline import lonlat_to_pixel
from navimap_satellites.extract.l2w import ReflectanceScene
from navimap_satellites.sdb.stumpf import calibrate_stumpf, stumpf_ratio


def sample_at_lonlat(
    grid: np.ndarray,
    bbox: BBox,
    lons: np.ndarray,
    lats: np.ndarray,
) -> np.ndarray:
    """Plus proche voisin sur une grille régulière (ligne 0 au nord)."""
    height, width = grid.shape
    row, col = lonlat_to_pixel(lons, lats, bbox, height, width)
    ri = np.rint(row).astype(int)
    ci = np.rint(col).astype(int)
    out = np.full(np.asarray(lons).shape, np.nan, dtype=np.float64)
    inside = (ri >= 0) & (ri < height) & (ci >= 0) & (ci < width)
    out[inside] = grid[ri[inside], ci[inside]]
    return out


def sample_scene_at_lonlat(
    grid: np.ndarray,
    scene: ReflectanceScene,
    lons: np.ndarray,
    lats: np.ndarray,
) -> np.ndarray:
    """Échantillonne une bande aux lon/lat. Grilles ACOLITE si présentes."""
    if scene.lon is None or scene.lat is None:
        return sample_at_lonlat(grid, scene.bbox, lons, lats)
    lon2d = np.asarray(scene.lon, dtype=np.float64)
    lat2d = np.asarray(scene.lat, dtype=np.float64)
    xs = np.asarray(lons, dtype=np.float64).ravel()
    ys = np.asarray(lats, dtype=np.float64).ravel()
    out = np.full(xs.shape, np.nan, dtype=np.float64)
    for i, (lon, lat) in enumerate(zip(xs, ys, strict=True)):
        if not (np.isfinite(lon) and np.isfinite(lat)):
            continue
        d2 = (lon2d - lon) ** 2 + (lat2d - lat) ** 2
        idx = int(np.nanargmin(d2))
        r, c = np.unravel_index(idx, d2.shape)
        out[i] = grid[int(r), int(c)]
    return out.reshape(np.asarray(lons).shape)


def calibrate_from_atl24(
    blue: np.ndarray,
    green: np.ndarray,
    points: list[Atl24Point],
    *,
    scene: ReflectanceScene | None = None,
    bbox: BBox | None = None,
    n: float = 1000.0,
) -> tuple[float, float, dict[str, Any]]:
    """Calage linéaire Stumpf sur les photons fond. Renvoie (m0, m1, stats)."""
    if not points:
        raise ValueError("Aucun point ATL24 pour caler Stumpf.")
    ratio = stumpf_ratio(blue, green, n=n)
    lons = np.array([p.lon for p in points], dtype=np.float64)
    lats = np.array([p.lat for p in points], dtype=np.float64)
    depths = np.array([p.depth_m for p in points], dtype=np.float64)
    if scene is not None:
        sampled = sample_scene_at_lonlat(ratio, scene, lons, lats)
    else:
        if bbox is None:
            raise ValueError("bbox ou scene requis pour échantillonner le ratio.")
        sampled = sample_at_lonlat(ratio, bbox, lons, lats)
    m0, m1 = calibrate_stumpf(sampled, depths)
    pred = m0 + m1 * sampled
    ok = np.isfinite(pred) & np.isfinite(depths) & (depths > 0)
    rmse = float(np.sqrt(np.mean((pred[ok] - depths[ok]) ** 2))) if int(ok.sum()) else None
    return m0, m1, {"n": int(ok.sum()), "rmse_m": rmse}


def synthetic_atl24_track(
    truth_depth: np.ndarray,
    bbox: BBox,
    *,
    n_along: int = 36,
    n_beams: int = 3,
    noise_m: float = 0.04,
    seed: int = 2,
) -> list[Atl24Point]:
    """Trace type ICESat-2 (presque N-S, quelques faisceaux) sur une scène démo."""
    from navimap_satellites.extract.coastline import pixel_to_lonlat

    height, width = truth_depth.shape
    rng = np.random.default_rng(seed)
    points: list[Atl24Point] = []
    for beam in range(n_beams):
        offset = (beam - (n_beams - 1) / 2.0) * 0.07
        t = np.linspace(0.08, 0.92, n_along)
        cols = (0.40 + offset + 0.10 * t) * max(width - 1, 1)
        rows = t * max(height - 1, 1)
        lon, lat = pixel_to_lonlat(rows, cols, bbox, height, width)
        for i in range(n_along):
            r = int(round(float(rows[i])))
            c = int(round(float(cols[i])))
            if not (0 <= r < height and 0 <= c < width):
                continue
            depth = float(truth_depth[r, c])
            if not np.isfinite(depth) or depth < 0.25 or depth > 12.0:
                continue
            noisy = depth + float(rng.normal(0.0, noise_m))
            if noisy <= 0:
                continue
            points.append(
                Atl24Point(
                    lon=float(lon[i]),
                    lat=float(lat[i]),
                    depth_m=noisy,
                    confidence=0.9,
                    granule_id="ATL24_SYNTHETIC",
                )
            )
    return points
