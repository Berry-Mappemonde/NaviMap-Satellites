import json
from pathlib import Path

from navimap_satellites.cli import main


def test_schema_cli(capsys):
    assert main(["schema"]) == 0
    out = capsys.readouterr().out
    assert "COALNE" in out
    assert "SOUNDG" in out


def test_demo_cli(tmp_path, capsys):
    assert main(["demo", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "coastline.geojson" in out
    data = json.loads((tmp_path / "coastline.geojson").read_text(encoding="utf-8"))
    assert data["features"]


def test_search_missing_file():
    assert main(["search", "/tmp/does-not-exist-navimap.yaml"]) == 1


def test_download_without_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("CDSE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CDSE_USERNAME", raising=False)
    monkeypatch.delenv("CDSE_PASSWORD", raising=False)
    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    assert main(["download", str(aoi), "--out", str(tmp_path), "--scene", "S2C_MSIL1C_x"]) == 1


def test_process_l2w_missing_file(tmp_path):
    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    assert main(["process-l2w", str(aoi), "--l2w", str(tmp_path / "no.nc")]) == 1


def test_acolite_without_binary(monkeypatch, tmp_path):
    monkeypatch.delenv("ACOLITE_LAUNCH", raising=False)
    monkeypatch.delenv("ACOLITE_DIR", raising=False)
    monkeypatch.delenv("ACOLITE_BIN", raising=False)
    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    fake = tmp_path / "x.SAFE"
    fake.mkdir()
    (fake / "MTD_MSIL1C.xml").write_text("<xml/>", encoding="utf-8")
    assert main(["acolite", str(aoi), "--input", str(fake), "--out", str(tmp_path / "ac")]) == 1


def test_auth_check_lists_env_without_secret(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".cdse.env"
    env.write_text("CDSE_USERNAME=demo@example.com\nCDSE_PASSWORD='ab$cd'\n", encoding="utf-8")
    monkeypatch.setenv("NAVIMAP_CDSE_ENV", str(env))
    monkeypatch.setenv("CDSE_ACCESS_TOKEN", "tok-test")
    assert main(["auth-check"]) == 0
    out = capsys.readouterr().out
    assert str(env) in out
    assert "ab$cd" not in out
    assert "Jeton CDSE obtenu" in out
