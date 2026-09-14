import numpy as np

from navimap_satellites.extract.coastline import contours_to_lonlat, mask_contours, pixel_to_lonlat


def test_square_island_has_a_ring():
    mask = np.ones((32, 32), dtype=bool)
    mask[12:20, 12:20] = False
    rings = mask_contours(mask)
    assert rings
    longest = max(rings, key=len)
    assert len(longest) >= 8


def test_pixel_to_lonlat_corners():
    bbox = (0.0, 10.0, 2.0, 12.0)
    lon, lat = pixel_to_lonlat(np.array([0.0, 9.0]), np.array([0.0, 9.0]), bbox, 10, 10)
    assert abs(lon[0] - 0.0) < 1e-9
    assert abs(lat[0] - 12.0) < 1e-9
    assert abs(lon[1] - 2.0) < 1e-9
    assert abs(lat[1] - 10.0) < 1e-9


def test_contours_to_lonlat_closed():
    mask = np.ones((16, 16), dtype=bool)
    mask[6:10, 6:10] = False
    lonlat = contours_to_lonlat(mask_contours(mask), (8.0, 42.0, 9.0, 43.0), 16, 16)
    assert lonlat
    ring = lonlat[0]
    assert ring[0] == ring[-1]
    assert len(ring) >= 4
