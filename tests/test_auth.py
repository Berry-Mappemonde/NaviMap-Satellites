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


def test_refresh_token():
    import httpx

    from navimap_satellites.acquire.auth import refresh_cdse_token

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"refresh_token" in request.content
        return httpx.Response(
            200,
            json={"access_token": "new", "refresh_token": "r2", "expires_in": 600},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token = refresh_cdse_token("old", client=client)
    assert token.access_token == "new"
    assert token.expires_in == 600
