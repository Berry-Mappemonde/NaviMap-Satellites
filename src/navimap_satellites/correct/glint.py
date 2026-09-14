"""Correction de chatoiement solaire (Hedley) sur des tableaux numpy."""

from __future__ import annotations

import numpy as np


def hedley_slope(
    visible: np.ndarray,
    nir: np.ndarray,
    water_mask: np.ndarray,
) -> float:
    """Pente de régression visible ~ NIR sur les pixels d'eau."""
    vis = np.asarray(visible, dtype=np.float64)[np.asarray(water_mask, dtype=bool)]
    ir = np.asarray(nir, dtype=np.float64)[np.asarray(water_mask, dtype=bool)]
    ok = np.isfinite(vis) & np.isfinite(ir)
    vis, ir = vis[ok], ir[ok]
    if vis.size < 8:
        return 0.0
    ir_c = ir - ir.mean()
    vis_c = vis - vis.mean()
    denom = float(np.dot(ir_c, ir_c))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(ir_c, vis_c) / denom)


def apply_hedley(
    visible: np.ndarray,
    nir: np.ndarray,
    slope: float,
    *,
    nir_min: float | None = None,
) -> np.ndarray:
    """R' = R - slope * (NIR - min NIR)."""
    vis = np.asarray(visible, dtype=np.float64)
    ir = np.asarray(nir, dtype=np.float64)
    floor = float(np.nanmin(ir)) if nir_min is None else float(nir_min)
    return vis - float(slope) * (ir - floor)
