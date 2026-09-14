import pytest

from navimap_satellites.acquire.l1c import (
    KNOWN_L1C_LA_ROCHELLE,
    L2ARejected,
    is_l1c_scene,
    is_l2a_scene,
    product_name,
    require_l1c,
)
from navimap_satellites.cli import main


def test_product_name_ajoute_safe():
    assert product_name(KNOWN_L1C_LA_ROCHELLE).endswith(".SAFE")
    assert product_name("X.SAFE") == "X.SAFE"


def test_refuse_l2a_pour_acolite():
    l2a = "S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321"
    assert is_l2a_scene(l2a)
    assert is_l1c_scene(KNOWN_L1C_LA_ROCHELLE)
    with pytest.raises(L2ARejected, match="L2A"):
        require_l1c(l2a)
    require_l1c(KNOWN_L1C_LA_ROCHELLE)


def test_cli_download_refuse_l2a(capsys):
    code = main(["download", "S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321"])
    assert code == 2
    err = capsys.readouterr().err
    assert "L2A" in err
