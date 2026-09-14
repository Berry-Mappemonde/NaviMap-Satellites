"""Grandes taches d'eau claire peu profonde — pas un écueil isolé."""

from __future__ import annotations

import numpy as np


def shallow_mask(
    water: np.ndarray,
    blue: np.ndarray,
    green: np.ndarray,
    *,
    quantile: float = 0.75,
    min_pixels: int = 64,
) -> np.ndarray:
    """Eau + fond plutôt clair (bleu+vert élevés). Jette les taches < min_pixels.

    À 10 m, 64 pixels ≈ 0,6 ha : un rocher métrique ne passe pas.
    """
    wet = np.asarray(water, dtype=bool)
    brightness = np.asarray(blue, dtype=np.float64) + np.asarray(green, dtype=np.float64)
    values = brightness[wet & np.isfinite(brightness)]
    if values.size < min_pixels:
        return np.zeros(wet.shape, dtype=bool)
    cut = float(np.nanquantile(values, quantile))
    raw = wet & np.isfinite(brightness) & (brightness >= cut)
    return _keep_large_components(raw, min_pixels)


def _keep_large_components(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    labels, counts = _label(mask)
    keep = np.zeros(mask.shape, dtype=bool)
    for lab, count in counts.items():
        if count >= min_pixels:
            keep |= labels == lab
    return keep


def _label(mask: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    """Composantes 4-connexes. Renvoie (labels, effectifs)."""
    binary = np.asarray(mask, dtype=bool)
    height, width = binary.shape
    labels = np.zeros(binary.shape, dtype=np.int32)
    counts: dict[int, int] = {}
    current = 0
    for i in range(height):
        for j in range(width):
            if not binary[i, j] or labels[i, j]:
                continue
            current += 1
            stack = [(i, j)]
            labels[i, j] = current
            size = 0
            while stack:
                r, c = stack.pop()
                size += 1
                for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < height and 0 <= nc < width and binary[nr, nc] and labels[nr, nc] == 0:
                        labels[nr, nc] = current
                        stack.append((nr, nc))
            counts[current] = size
    return labels, counts
