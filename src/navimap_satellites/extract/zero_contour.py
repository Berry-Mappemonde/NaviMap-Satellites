"""Contour MNDWI = 0 sur une grille lon/lat (port Vague 4, sans GDAL)."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from navimap_satellites.aoi import BBox


def crop_to_bbox(
    lon: np.ndarray,
    lat: np.ndarray,
    z: np.ndarray,
    bbox: BBox,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    west, south, east, north = bbox
    inside = (lon >= west) & (lon <= east) & (lat >= south) & (lat <= north)
    if not np.any(inside):
        raise ValueError("aucun pixel dans l'emprise demandée")
    rows, cols = np.where(inside)
    sl = np.s_[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
    return lon[sl], lat[sl], z[sl]


def downsample(
    lon: np.ndarray,
    lat: np.ndarray,
    z: np.ndarray,
    max_side: int = 900,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ny, nx = z.shape
    step = max(1, int(np.ceil(max(ny, nx) / max_side)))
    if step == 1:
        return lon, lat, z
    return lon[::step, ::step], lat[::step, ::step], z[::step, ::step]


def _crossing(p0, p1, v0, v1) -> tuple[float, float]:
    t = 0.5 if v1 == v0 else v0 / (v0 - v1)
    t = min(1.0, max(0.0, float(t)))
    return (p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]))


def zero_segments(lon: np.ndarray, lat: np.ndarray, z: np.ndarray):
    segs = []
    ny, nx = z.shape
    for i in range(ny - 1):
        for j in range(nx - 1):
            corners = ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))
            vals = [z[r, c] for r, c in corners]
            if not all(np.isfinite(v) for v in vals):
                continue
            pts = []
            for a in range(4):
                b = (a + 1) % 4
                va, vb = vals[a], vals[b]
                r0, c0 = corners[a]
                p0 = (float(lon[r0, c0]), float(lat[r0, c0]))
                if va == 0:
                    pts.append(p0)
                    continue
                if va * vb < 0:
                    r1, c1 = corners[b]
                    p1 = (float(lon[r1, c1]), float(lat[r1, c1]))
                    pts.append(_crossing(p0, p1, va, vb))
            if len(pts) >= 2:
                segs.append((pts[0], pts[1]))
            if len(pts) >= 4:
                segs.append((pts[2], pts[3]))
    return segs


def stitch(segs, min_pts: int = 12) -> list[list[tuple[float, float]]]:
    def key(p, nd=6):
        return (round(p[0], nd), round(p[1], nd))

    adj: dict[tuple[float, float], list] = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        adj[key(a)].append((i, 0))
        adj[key(b)].append((i, 1))
    used = [False] * len(segs)
    lines: list[list[tuple[float, float]]] = []
    for i, (a, b) in enumerate(segs):
        if used[i]:
            continue
        used[i] = True
        line = [a, b]
        for start in (False, True):
            while True:
                k = key(line[0] if start else line[-1])
                found = False
                for j, end in adj[k]:
                    if used[j]:
                        continue
                    used[j] = True
                    p0, p1 = segs[j]
                    other = p1 if end == 0 else p0
                    if start:
                        line.insert(0, other)
                    else:
                        line.append(other)
                    found = True
                    break
                if not found:
                    break
        if len(line) >= min_pts:
            lines.append([(float(x), float(y)) for x, y in line])
    return lines


def extract_lines(
    lon: np.ndarray,
    lat: np.ndarray,
    z: np.ndarray,
    bbox: BBox,
    *,
    max_side: int = 900,
    min_pts: int = 12,
) -> list[list[tuple[float, float]]]:
    lon, lat, z = crop_to_bbox(lon, lat, z, bbox)
    lon, lat, z = downsample(lon, lat, z, max_side=max_side)
    return stitch(zero_segments(lon, lat, z), min_pts=min_pts)
