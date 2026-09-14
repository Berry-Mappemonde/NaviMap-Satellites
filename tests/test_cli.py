import json

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
