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
    assert "preview.html" in out
    data = json.loads((tmp_path / "coastline.geojson").read_text(encoding="utf-8"))
    assert data["features"]
    assert (tmp_path / "preview.html").is_file()
    assert (tmp_path / "atl24.geojson").is_file()


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


def test_layers_cli(capsys):
    assert main(["layers"]) == 0
    out = capsys.readouterr().out
    assert "photo" in out
    assert "atl24" in out
    assert "bathymétrie" in out


def test_basemap_cli(tmp_path, capsys):
    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    dest = tmp_path / "calvi.html"
    assert main(["basemap", str(aoi), "--out", str(dest)]) == 0
    out = capsys.readouterr().out
    assert dest.is_file()
    assert "worldview.earthdata.nasa.gov" in out
    html = dest.read_text(encoding="utf-8")
    assert "VIIRS_SNPP_CorrectedReflectance_TrueColor" in html


def test_atl24_cli_mocked(monkeypatch, capsys):
    from navimap_satellites.acquire.atl24 import Atl24Granule

    def fake_search(aoi, limit=20):
        return [
            Atl24Granule(
                id="G1",
                title="ATL24_FAKE.h5",
                time_start="2025-08-15T00:00:00Z",
                time_end="2025-08-15T00:10:00Z",
                short_name="ATL24",
            )
        ]

    monkeypatch.setattr("navimap_satellites.acquire.atl24.search_atl24", fake_search)
    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    assert main(["atl24", str(aoi)]) == 0
    out = capsys.readouterr().out
    assert "ATL24_FAKE.h5" in out
    assert "Worldview" in out


def test_auth_check_lists_env_without_secret(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".cdse.env"
    env.write_text("CDSE_USERNAME=demo@example.com\nCDSE_PASSWORD='ab$cd'\n", encoding="utf-8")
    monkeypatch.setenv("NAVIMAP_CDSE_ENV", str(env))
    monkeypatch.setenv("CDSE_ACCESS_TOKEN", "tok-test")
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    assert main(["auth-check"]) == 0
    out = capsys.readouterr().out
    assert str(env) in out
    assert "ab$cd" not in out
    assert "Jeton CDSE obtenu" in out
    assert "Earthdata" in out or "urs.earthdata" in out
