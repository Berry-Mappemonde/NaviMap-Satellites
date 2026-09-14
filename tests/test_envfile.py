import os
from pathlib import Path

from navimap_satellites.acquire.envfile import load_cdse_env


def test_loads_quoted_password(tmp_path: Path, monkeypatch):
    env = tmp_path / ".cdse.env"
    env.write_text("CDSE_USERNAME=demo@example.com\nCDSE_PASSWORD='ab$cd'\n", encoding="utf-8")
    monkeypatch.setenv("NAVIMAP_CDSE_ENV", str(env))
    monkeypatch.delenv("CDSE_USERNAME", raising=False)
    monkeypatch.delenv("CDSE_PASSWORD", raising=False)
    loaded = load_cdse_env()
    assert str(env) in loaded
    assert os.environ["CDSE_USERNAME"] == "demo@example.com"
    assert os.environ["CDSE_PASSWORD"] == "ab$cd"
