import httpx

from navimap_satellites.icesat_gate import count_granules, presence_report


def test_count_granules_parses_feed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"feed": {"entry": [{}, {}, {}]}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert count_granules("ATL24", (8.7, 42.5, 8.8, 42.6), client=client) == 3


def test_presence_report_never_writes_soundings(monkeypatch):
    monkeypatch.setattr("navimap_satellites.icesat_gate.count_granules", lambda *a, **k: 2)
    report = presence_report((8.7, 42.5, 8.8, 42.6))
    assert report["soundings_written"] is False
    assert report["sdb_allowed_later"] is True
    assert "worldview.earthdata.nasa.gov" in report["worldview_url"]
    assert "fond visuel" in report["gibs_note"].lower() or "GIBS" in report["gibs_note"]
