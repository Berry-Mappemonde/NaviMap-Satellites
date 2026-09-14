import httpx
import pytest

from navimap_satellites.acquire.earthdata import EarthdataAuthError, fetch_earthdata_token


def test_earthdata_without_credentials(monkeypatch):
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    with pytest.raises(EarthdataAuthError, match="urs.earthdata.nasa.gov"):
        fetch_earthdata_token()


def test_earthdata_uses_existing_token(monkeypatch):
    monkeypatch.setenv("EARTHDATA_TOKEN", "nasa-tok")
    assert fetch_earthdata_token() == "nasa-tok"


def test_earthdata_posts_to_urs(monkeypatch):
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("EARTHDATA_USERNAME", "user")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "urs.earthdata.nasa.gov" in str(request.url)
        return httpx.Response(200, json={"access_token": "from-urs"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_earthdata_token(client=client) == "from-urs"
