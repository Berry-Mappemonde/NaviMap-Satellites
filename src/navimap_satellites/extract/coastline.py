"""Contours terre/eau par marching squares (sans GDAL)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from navimap_satellites.aoi import BBox

# Segments (départ, arrivée) dans chaque cellule 2×2, indexés 0-15.
# Coins : 0=tl, 1=tr, 2=br, 3=bl. Côtés : 0=top, 1=right, 2=bottom, 3=left.
# Un bit à 1 = coin au-dessus du niveau (eau si on contourne un masque eau=1).
_CASES: dict[int, tuple[tuple[int, int], ...]] = {
    0: (),
    1: ((3, 0),),
    2: ((0, 1),),
    3: ((3, 1),),
    4: ((1, 2),),
    5: ((3, 2), (0, 1)),  # selle : choix conventionnel
    6: ((0, 2),),
    7: ((3, 2),),
    8: ((2, 3),),
    9: ((2, 0),),
    10: ((0, 1), (2, 3)),
    11: ((2, 1),),
    12: ((1, 3),),
    13: ((1, 0),),
    14: ((0, 3),),
    15: (),
}


def _edge_point(r: int, c: int, edge: int) -> tuple[float, float]:
    """Point milieu d'un côté de la cellule (r, c) → (row, col) flottants."""
    if edge == 0:  # top
        return (float(r), c + 0.5)
    if edge == 1:  # right
        return (r + 0.5, float(c + 1))
    if edge == 2:  # bottom
        return (float(r + 1), c + 0.5)
    return (r + 0.5, float(c))  # left


def mask_contours(mask: np.ndarray) -> list[np.ndarray]:
    """Anneaux (row, col) le long du seuil 0.5 d'un masque booléen.

    `True` = eau. Chaque anneau est un tableau (N, 2), fermé si possible.
    """
    binary = np.asarray(mask, dtype=np.uint8)
    if binary.ndim != 2 or min(binary.shape) < 2:
        return []
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    rows, cols = binary.shape
    for r in range(rows - 1):
        for c in range(cols - 1):
            bits = (
                int(binary[r, c])
                | (int(binary[r, c + 1]) << 1)
                | (int(binary[r + 1, c + 1]) << 2)
                | (int(binary[r + 1, c]) << 3)
            )
            for a, b in _CASES.get(bits, ()):
                segments.append((_edge_point(r, c, a), _edge_point(r, c, b)))
    return _join_segments(segments)


def _join_segments(
    segments: Sequence[tuple[tuple[float, float], tuple[float, float]]],
    snap: float = 1e-6,
) -> list[np.ndarray]:
    unused = list(segments)
    rings: list[np.ndarray] = []

    def key(pt: tuple[float, float]) -> tuple[int, int]:
        return (round(pt[0] / snap), round(pt[1] / snap))

    while unused:
        start, nxt = unused.pop()
        chain = [start, nxt]
        grew = True
        while grew:
            grew = False
            end = chain[-1]
            ek = key(end)
            for i, (a, b) in enumerate(unused):
                if key(a) == ek:
                    chain.append(b)
                    unused.pop(i)
                    grew = True
                    break
                if key(b) == ek:
                    chain.append(a)
                    unused.pop(i)
                    grew = True
                    break
        rings.append(np.asarray(chain, dtype=np.float64))
    return rings


def pixel_to_lonlat(
    row: np.ndarray,
    col: np.ndarray,
    bbox: BBox,
    height: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Centre de pixel → lon/lat. Ligne 0 en haut (nord)."""
    west, south, east, north = bbox
    lon = west + (np.asarray(col, dtype=np.float64) / max(width - 1, 1)) * (east - west)
    lat = north - (np.asarray(row, dtype=np.float64) / max(height - 1, 1)) * (north - south)
    return lon, lat


def contours_to_lonlat(
    contours: Sequence[np.ndarray],
    bbox: BBox,
    height: int,
    width: int,
) -> list[list[tuple[float, float]]]:
    """Contours pixel → listes de (lon, lat) pour du GeoJSON."""
    out: list[list[tuple[float, float]]] = []
    for ring in contours:
        if ring.size == 0:
            continue
        lon, lat = pixel_to_lonlat(ring[:, 0], ring[:, 1], bbox, height, width)
        coords = [(float(x), float(y)) for x, y in zip(lon, lat, strict=True)]
        if len(coords) >= 2 and coords[0] != coords[-1]:
            coords.append(coords[0])
        if len(coords) >= 4:
            out.append(coords)
    return out
