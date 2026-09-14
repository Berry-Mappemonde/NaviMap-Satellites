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
