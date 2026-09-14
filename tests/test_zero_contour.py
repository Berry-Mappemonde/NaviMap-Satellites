import numpy as np

from navimap_satellites.extract.zero_contour import extract_lines


def test_mndwi_contour_separe_eau_et_terre():
    n = 24
    lon = np.tile(np.linspace(-1.4, -0.9, n), (n, 1))
    lat = np.tile(np.linspace(46.0, 46.4, n).reshape(-1, 1), (1, n))
    z = np.where(lon < -1.15, 0.4, -0.4)
    bbox = (-1.5, 45.9, -0.8, 46.5)
    lines = extract_lines(lon, lat, z, bbox, min_pts=8)
    assert lines
    xs = [pt[0] for line in lines for pt in line]
    assert all(-1.25 < x < -1.05 for x in xs)
