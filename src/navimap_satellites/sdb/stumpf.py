"""Bathymétrie dérivée — ratio de bandes de Stumpf (2003).

z = m0 + m1 * ln(n * R_bleu) / ln(n * R_vert)

Les coefficients m0 et m1 doivent être calés sur des sondages
(ICESat-2 ATL24, voir sdb.control). Sans calage, le ratio est un
indice relatif, pas une profondeur en mètres.
"""

from __future__ import annotations

import numpy as np

LN_FLOOR = 1e-6


def stumpf_ratio(
    blue: np.ndarray,
    green: np.ndarray,
    *,
    n: float = 1000.0,
) -> np.ndarray:
    """Ratio logarithmique bleu/vert (sans unité)."""
    b = np.asarray(blue, dtype=np.float64)
    g = np.asarray(green, dtype=np.float64)
    num = np.log(np.clip(n * b, LN_FLOOR, None))
    den = np.log(np.clip(n * g, LN_FLOOR, None))
    out = np.full(b.shape, np.nan, dtype=np.float64)
    ok = np.isfinite(num) & np.isfinite(den) & (np.abs(den) > LN_FLOOR)
    out[ok] = num[ok] / den[ok]
    return out


def calibrate_stumpf(
    ratio: np.ndarray,
    truth_depth_m: np.ndarray,
    water_mask: np.ndarray | None = None,
) -> tuple[float, float]:
    """Régression linéaire profondeur = m0 + m1 * ratio. Renvoie (m0, m1)."""
    r = np.asarray(ratio, dtype=np.float64).ravel()
    z = np.asarray(truth_depth_m, dtype=np.float64).ravel()
    if water_mask is not None:
        m = np.asarray(water_mask, dtype=bool).ravel()
        r, z = r[m], z[m]
    ok = np.isfinite(r) & np.isfinite(z) & (z > 0)
    r, z = r[ok], z[ok]
    if r.size < 8:
        raise ValueError("Pas assez de pixels pour caler Stumpf.")
    a = np.column_stack([np.ones(r.size), r])
    coef, _, _, _ = np.linalg.lstsq(a, z, rcond=None)
    return float(coef[0]), float(coef[1])


def stumpf_depth(
    blue: np.ndarray,
    green: np.ndarray,
    *,
    m0: float,
    m1: float,
    n: float = 1000.0,
    water_mask: np.ndarray | None = None,
    max_depth_m: float = 15.0,
) -> np.ndarray:
    """Profondeur estimée (mètres positifs sous la surface).

    Hors masque d'eau, ou au-delà de max_depth_m, le résultat est NaN.
    """
    ratio = stumpf_ratio(blue, green, n=n)
    depth = m0 + m1 * ratio
    depth = np.where(np.isfinite(depth), depth, np.nan)
    depth = np.where(depth < 0, np.nan, depth)
    depth = np.where(depth > max_depth_m, np.nan, depth)
    if water_mask is not None:
        depth = np.where(water_mask, depth, np.nan)
    return depth
