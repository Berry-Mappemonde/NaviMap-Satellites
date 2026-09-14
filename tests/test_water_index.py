import numpy as np

from navimap_satellites.extract.water_index import mndwi, ndwi, otsu_threshold, water_mask


def test_ndwi_water_positive_land_negative():
    green = np.array([0.08, 0.05])
    nir = np.array([0.02, 0.40])
    values = ndwi(green, nir)
    assert values[0] > 0
    assert values[1] < 0


def test_mndwi_rejects_bright_concrete():
    green = np.array([0.15, 0.08])
    swir = np.array([0.22, 0.01])  # béton / eau
    values = mndwi(green, swir)
    assert values[0] < 0
    assert values[1] > 0


def test_otsu_splits_two_blobs():
    values = np.concatenate([np.full(80, -0.4), np.full(80, 0.5)])
    cut = otsu_threshold(values)
    mask = water_mask(values, threshold=cut)
    assert mask[:80].sum() == 0
    assert mask[80:].sum() == 80


def test_water_mask_otsu():
    index = np.array([[-0.5, -0.4], [0.6, 0.7]])
    mask = water_mask(index)
    assert mask.tolist() == [[False, False], [True, True]]
