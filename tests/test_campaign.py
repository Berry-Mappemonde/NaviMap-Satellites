from pathlib import Path

import pytest

from navimap_satellites.aoi import aoi_from_dict, load_aoi
from navimap_satellites.campaign import load_campaign
from navimap_satellites.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_load_berry_campaign():
    campaign = load_campaign(ROOT / "aois" / "berry")
    assert campaign.id == "berry-mappemonde"
    ids = [a.id for a in campaign.stages]
    assert ids[0] == "calvi"
    assert "nouvelle-caledonie-lagon" in ids
    assert all(a.phase == "expedition" for a in campaign.stages)
    assert all(a.collections == ("sentinel-2-l1c",) for a in campaign.stages)


def test_filter_phase_empty():
    campaign = load_campaign(ROOT / "aois" / "berry").filter_phase("world")
    assert campaign.stages == ()


def test_campaign_cli(capsys):
    assert main(["campaign", str(ROOT / "aois" / "berry")]) == 0
    out = capsys.readouterr().out
    assert "calvi" in out
    assert "navimap-sat process" in out


def test_invalid_phase():
    with pytest.raises(ValueError, match="phase"):
        aoi_from_dict(
            {
                "id": "x",
                "bbox": [0, 0, 1, 1],
                "date_from": "2025-01-01",
                "date_to": "2025-02-01",
                "phase": "orbit",
            }
        )


def test_calvi_has_campaign_fields():
    aoi = load_aoi(ROOT / "aois" / "calvi.yaml")
    assert aoi.for_l1c().collections == ("sentinel-2-l1c",)
    assert aoi.phase == "expedition"
    assert aoi.acolite_limit().startswith("42.52,")
