from pathlib import Path
from types import SimpleNamespace

import pytest

from navimap_satellites.aoi import aoi_from_dict
from navimap_satellites.correct.acolite import (
    AcoliteError,
    acolite_command,
    find_l2w,
    run_acolite,
    write_settings,
)


def _aoi():
    return aoi_from_dict(
        {
            "id": "calvi",
            "bbox": [8.70, 42.52, 8.82, 42.60],
            "date_from": "2025-01-01",
            "date_to": "2025-12-31",
        }
    )


def test_acolite_limit_order():
    assert _aoi().acolite_limit() == "42.52,8.7,42.6,8.82"


def test_write_settings(tmp_path: Path):
    settings = write_settings(
        tmp_path / "s.txt",
        inputfile=tmp_path / "in.SAFE",
        output=tmp_path / "out",
        aoi=_aoi(),
    )
    text = settings.read_text(encoding="utf-8")
    assert "limit=42.52,8.7,42.6,8.82" in text
    assert "s2_target_res=10" in text
    assert "rgb_rhot=False" in text


def test_find_l2w(tmp_path: Path):
    target = tmp_path / "S2C_MSI_2026_T30TWR_L2W.nc"
    target.write_bytes(b"nc")
    assert find_l2w(tmp_path) == target
    with pytest.raises(AcoliteError, match="L2W"):
        find_l2w(tmp_path / "empty")


def test_run_acolite_ok(tmp_path: Path):
    settings = tmp_path / "s.txt"
    settings.write_text("inputfile=x\n", encoding="utf-8")

    def runner(cmd, **kwargs):
        assert cmd[:2] == ["acolite", "--cli"]
        assert cmd[2].startswith("--settings=")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    run_acolite(settings, command=["acolite"], runner=runner)


def test_run_acolite_fails(tmp_path: Path):
    settings = tmp_path / "s.txt"
    settings.write_text("x\n", encoding="utf-8")

    def runner(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    with pytest.raises(AcoliteError, match="boom"):
        run_acolite(settings, command=["acolite"], runner=runner)


def test_acolite_command_from_dir(tmp_path: Path, monkeypatch):
    script = tmp_path / "launch_acolite.py"
    script.write_text("#\n", encoding="utf-8")
    monkeypatch.delenv("ACOLITE_LAUNCH", raising=False)
    monkeypatch.delenv("ACOLITE_BIN", raising=False)
    monkeypatch.setenv("ACOLITE_DIR", str(tmp_path))
    cmd = acolite_command()
    assert cmd[-1] == str(script)


def test_acolite_missing(monkeypatch):
    monkeypatch.delenv("ACOLITE_LAUNCH", raising=False)
    monkeypatch.delenv("ACOLITE_DIR", raising=False)
    monkeypatch.delenv("ACOLITE_BIN", raising=False)
    with pytest.raises(AcoliteError, match="ACOLITE introuvable"):
        acolite_command()
