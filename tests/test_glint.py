import numpy as np

from navimap_satellites.correct.glint import apply_hedley, hedley_slope


def test_hedley_recovers_linear_glint():
    rng = np.random.default_rng(1)
    nir = rng.uniform(0.01, 0.08, size=200)
    true_vis = 0.03 + np.zeros(200)
    slope = 0.4
    observed = true_vis + slope * (nir - nir.min())
    mask = np.ones(200, dtype=bool)
    fitted = hedley_slope(observed, nir, mask)
    assert abs(fitted - slope) < 0.05
    corrected = apply_hedley(observed, nir, fitted, nir_min=float(nir.min()))
    assert abs(corrected.mean() - 0.03) < 0.01
