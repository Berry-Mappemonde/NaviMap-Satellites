import pytest

from navimap_satellites.acquire.auth import CdseAuthError, fetch_cdse_token


def test_auth_without_credentials(monkeypatch):
    monkeypatch.delenv("CDSE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CDSE_USERNAME", raising=False)
    monkeypatch.delenv("CDSE_PASSWORD", raising=False)
    with pytest.raises(CdseAuthError, match="dataspace.copernicus.eu"):
        fetch_cdse_token()


def test_auth_uses_existing_token(monkeypatch):
    monkeypatch.setenv("CDSE_ACCESS_TOKEN", "abc123")
    assert fetch_cdse_token() == "abc123"
