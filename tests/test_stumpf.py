import numpy as np

from navimap_satellites.sdb.stumpf import calibrate_stumpf, stumpf_depth, stumpf_ratio


def test_ratio_deeper_water_changes():
    # Plus profond → bleu et vert plus faibles, le ratio bouge.
    shallow = stumpf_ratio(np.array([0.04]), np.array([0.05]))
    deep = stumpf_ratio(np.array([0.01]), np.array([0.008]))
    assert np.isfinite(shallow[0]) and np.isfinite(deep[0])
    assert shallow[0] != deep[0]


def test_calibrate_and_recover():
    rng = np.random.default_rng(0)
    ratio = rng.uniform(0.8, 1.4, size=200)
    truth = 1.2 + 4.5 * ratio
    m0, m1 = calibrate_stumpf(ratio, truth)
    assert abs(m0 - 1.2) < 1e-6
    assert abs(m1 - 4.5) < 1e-6
    recovered = m0 + m1 * ratio
    assert np.max(np.abs(recovered - truth)) < 1e-6


def test_mask_and_cap():
    blue = np.array([[0.04, 0.04], [0.04, 0.04]])
    green = np.array([[0.05, 0.05], [0.05, 0.05]])
    mask = np.array([[True, False], [True, True]])
    depth = stumpf_depth(blue, green, m0=1.0, m1=0.0, water_mask=mask, max_depth_m=0.5)
    # m0+m1*ratio = 1.0 > max_depth → NaN partout
    assert np.all(np.isnan(depth))
    depth2 = stumpf_depth(blue, green, m0=0.2, m1=0.0, water_mask=mask, max_depth_m=15)
    assert np.isnan(depth2[0, 1])
    assert depth2[0, 0] == 0.2
