"""Indices spectraux terre / eau et seuillage d'Otsu."""

from __future__ import annotations

import numpy as np

EPS = 1e-6


def normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(a - b) / (a + b), pixels nuls → NaN."""
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    denom = aa + bb
    out = np.full(aa.shape, np.nan, dtype=np.float64)
    ok = np.abs(denom) > EPS
    out[ok] = (aa[ok] - bb[ok]) / denom[ok]
    return out


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDWI de McFeeters : (vert - PIR) / (vert + PIR)."""
    return normalized_difference(green, nir)


def mndwi(green: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """MNDWI de Xu : (vert - SWIR) / (vert + SWIR) — meilleur en zone portuaire."""
    return normalized_difference(green, swir)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """NDVI : (PIR - rouge) / (PIR + rouge)."""
    return normalized_difference(nir, red)


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Seuil qui sépare au mieux deux classes (histogramme).

    On ignore les NaN. S'il n'y a pas assez de pixels, on renvoie 0.
    """
    data = np.asarray(values, dtype=np.float64)
    data = data[np.isfinite(data)]
    if data.size < 8:
        return 0.0
    hist, edges = np.histogram(data, bins=int(bins))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return float(np.median(data))
    centers = 0.5 * (edges[:-1] + edges[1:])
    w_b = 0.0
    sum_b = 0.0
    sum_all = float(np.dot(hist, centers))
    max_var = -1.0
    best = float(centers[len(centers) // 2])
    for i, count in enumerate(hist):
        w_b += count
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += count * centers[i]
        mean_b = sum_b / w_b
        mean_f = (sum_all - sum_b) / w_f
        var_between = w_b * w_f * (mean_b - mean_f) ** 2
        if var_between > max_var:
            max_var = var_between
            best = float(centers[i])
    return best


def water_mask(index: np.ndarray, threshold: float | None = None) -> np.ndarray:
    """True = eau. Seuil d'Otsu par défaut (eau = index au-dessus du seuil)."""
    idx = np.asarray(index, dtype=np.float64)
    cut = otsu_threshold(idx) if threshold is None else float(threshold)
    return np.isfinite(idx) & (idx > cut)
