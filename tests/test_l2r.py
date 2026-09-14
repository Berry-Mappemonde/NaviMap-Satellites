from pathlib import Path

import pytest

from navimap_satellites.correct.l2r import L2RError, find_l2r, pick_band


def test_pick_band_prefere_1612():
    names = ["rhos_444", "rhos_561", "rhos_1612", "rhos_1614", "rhos_2191"]
    assert pick_band(names, ("561", "560")) == "rhos_561"
    assert pick_band(names, ("1612", "1614")) == "rhos_1612"


def test_find_l2r_refuse_l1r(tmp_path: Path):
    l1r = tmp_path / "S2C_MSI_2026_09_12_11_18_31_T30TWR_L1R.nc"
    l1r.write_bytes(b"nope")
    with pytest.raises(L2RError, match="L1R"):
        find_l2r(l1r)


def test_find_l2r_dans_dossier(tmp_path: Path):
    (tmp_path / "foo_L1R.nc").write_bytes(b"x")
    good = tmp_path / "S2C_MSI_2026_09_12_11_18_31_T30TWR_L2R.nc"
    good.write_bytes(b"x")
    assert find_l2r(tmp_path) == good
