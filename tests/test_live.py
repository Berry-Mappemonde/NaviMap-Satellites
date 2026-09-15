import base64
import json
import struct
from pathlib import Path

import numpy as np

from navimap_satellites.cli import main
from navimap_satellites.demo import DEMO_AOI, run_demo, synthetic_scene
from navimap_satellites.extract.l2w import ReflectanceScene
from navimap_satellites.live import (
    PNG_DATA_URL_PREFIX,
    LivePublisher,
    bbox_image_coordinates,
    layer_payload,
    make_publisher,
    reflectance_png_data_url,
    status_payload,
)


class Collector:
    def __init__(self):
        self.events = []

    def publish(self, payload):
        self.events.append(payload)
        return True


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_reflectance_png_is_valid_data_url_and_downsampled():
    blue = np.linspace(0.01, 0.2, 700 * 900).reshape(700, 900)
    green = np.flipud(blue)
    nir = np.fliplr(blue)

    url = reflectance_png_data_url(blue, green, nir)

    assert url.startswith(PNG_DATA_URL_PREFIX)
    png = base64.b64decode(url.removeprefix(PNG_DATA_URL_PREFIX))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (512, 512)


def test_status_and_layer_payloads_follow_live_protocol():
    status = status_payload("correction", "Réflectances", 0.6)
    assert status == {
        "type": "status",
        "pipeline": "satellites",
        "phase": "correction",
        "message": "Réflectances",
        "progress": 0.6,
    }

    data = {"type": "FeatureCollection", "features": []}
    event = layer_payload(
        layer_id="satellites-coastline",
        title="Côte",
        kind="geojson",
        data=data,
        style={"line-color": "orange"},
    )
    assert event["type"] == "layer"
    assert event["action"] == "upsert"
    assert event["pipeline"] == "satellites"
    assert event["layer"] == {
        "id": "satellites-coastline",
        "title": "Côte",
        "group": "satellites",
        "kind": "geojson",
        "data": data,
        "style": {"line-color": "orange"},
        "visible": True,
    }


def test_image_payload_uses_bbox_corners():
    coordinates = bbox_image_coordinates((8.7, 42.52, 8.82, 42.6))
    event = layer_payload(
        layer_id="satellites-image",
        title="Image",
        kind="image",
        url="data:image/png;base64,AAAA",
        coordinates=coordinates,
        style={"opacity": 0.7},
    )
    assert event["layer"]["coordinates"] == [
        [8.7, 42.6],
        [8.82, 42.6],
        [8.82, 42.52],
        [8.7, 42.52],
    ]
    assert "data" not in event["layer"]


def test_live_publisher_posts_json_and_delays_between_events():
    requests = []
    sleeps = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return Response()

    publisher = LivePublisher(
        "http://127.0.0.1:8765/",
        delay=0.25,
        opener=opener,
        sleeper=sleeps.append,
    )
    assert publisher.publish(status_payload("download", "L1C", 0.1))
    assert publisher.publish(status_payload("acolite", "ACOLITE", 0.3))

    assert sleeps == [0.25]
    request, timeout = requests[0]
    assert request.full_url == "http://127.0.0.1:8765/api/events"
    assert request.method == "POST"
    assert request.headers["Content-type"] == "application/json"
    assert json.loads(request.data) == status_payload("download", "L1C", 0.1)
    assert timeout == 2.0


def test_hub_failure_is_best_effort(tmp_path: Path):
    def broken_opener(*_args, **_kwargs):
        raise OSError("hub down")

    publisher = LivePublisher("http://hub.invalid", opener=broken_opener)
    assert publisher.publish(status_payload("correction", "test", 0.5)) is False

    paths = run_demo(tmp_path, size=48, publisher=publisher)
    assert paths["coastline"].is_file()
    assert paths["soundings"].is_file()


def test_demo_publishes_layers_in_file_write_order(tmp_path: Path):
    publisher = Collector()
    paths = run_demo(tmp_path, size=64, publisher=publisher)

    layers = [event["layer"] for event in publisher.events if event["type"] == "layer"]
    assert [layer["id"] for layer in layers] == [
        "satellites-image",
        "satellites-coastline",
        "satellites-shallow",
        "satellites-atl24",
        "satellites-soundings",
    ]
    assert publisher.events[0]["phase"] == "correction"
    assert layers[0]["kind"] == "image"
    assert layers[0]["url"].startswith(PNG_DATA_URL_PREFIX)
    for key, layer in zip(("coastline", "shallow", "atl24", "soundings"), layers[1:]):
        posted_data = json.loads(json.dumps(layer["data"]))
        assert posted_data == json.loads(paths[key].read_text(encoding="utf-8"))


def test_make_publisher_uses_environment(monkeypatch):
    monkeypatch.setenv("NAVIMAP_LIVE_MAP_URL", "http://localhost:9999")
    publisher = make_publisher(delay=0.2)
    assert publisher is not None
    assert publisher.url == "http://localhost:9999/api/events"
    assert publisher.delay == 0.2


def test_demo_cli_passes_live_options(monkeypatch, tmp_path: Path):
    publisher = Collector()
    received = {}

    def fake_make_publisher(url, *, delay):
        received.update(url=url, delay=delay)
        return publisher

    monkeypatch.setattr("navimap_satellites.live.make_publisher", fake_make_publisher)
    assert (
        main(
            [
                "demo",
                "--out",
                str(tmp_path),
                "--live-url",
                "http://charts.local",
                "--live-delay",
                "0.4",
            ]
        )
        == 0
    )
    assert received == {"url": "http://charts.local", "delay": 0.4}
    assert any(event["type"] == "layer" for event in publisher.events)


def test_process_publishes_download_acolite_and_correction_statuses(monkeypatch, tmp_path: Path):
    publisher = Collector()
    raw = synthetic_scene(48)
    scene = ReflectanceScene(
        blue=raw["blue"],
        green=raw["green"],
        swir=raw["swir"],
        nir=raw["nir"],
        bbox=DEMO_AOI.bbox,
        source="fake-L2W.nc",
    )
    safe = tmp_path / "scene.SAFE"
    l2w = tmp_path / "fake-L2W.nc"

    monkeypatch.setattr(
        "navimap_satellites.live.make_publisher",
        lambda _url, *, delay: publisher,
    )
    monkeypatch.setattr(
        "navimap_satellites.acquire.auth.fetch_cdse_session",
        lambda: None,
    )
    monkeypatch.setattr(
        "navimap_satellites.acquire.download.download_best_l1c",
        lambda *_args, **_kwargs: safe,
    )
    monkeypatch.setattr("navimap_satellites.cli._cmd_acolite", lambda _args: 0)
    monkeypatch.setattr(
        "navimap_satellites.correct.acolite.find_l2w",
        lambda _path: l2w,
    )
    monkeypatch.setattr(
        "navimap_satellites.extract.l2w.read_l2w",
        lambda *_args, **_kwargs: scene,
    )

    aoi = Path(__file__).resolve().parents[1] / "aois" / "calvi.yaml"
    assert main(["process", str(aoi), "--out", str(tmp_path), "--live-url", "http://hub"]) == 0
    phases = [event["phase"] for event in publisher.events if event["type"] == "status"]
    assert phases == ["download", "acolite", "correction", "complete"]
