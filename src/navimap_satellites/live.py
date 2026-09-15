"""Publication best-effort des étapes Satellites vers NaviMap Charts."""

from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.request
import zlib
from collections.abc import Callable, Mapping
from typing import Any, Protocol

import numpy as np

PIPELINE = "satellites"
LIVE_URL_ENV = "NAVIMAP_LIVE_MAP_URL"
PNG_DATA_URL_PREFIX = "data:image/png;base64,"


class Publisher(Protocol):
    """Interface minimale acceptée par le pipeline de traitement."""

    def publish(self, payload: Mapping[str, Any]) -> bool | None:
        """Publie un événement sans imposer de valeur de retour."""


class LivePublisher:
    """Envoie des événements JSON au hub, sans jamais propager ses pannes."""

    def __init__(
        self,
        live_url: str,
        *,
        delay: float = 0.0,
        timeout: float = 2.0,
        opener: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.url = f"{live_url.rstrip('/')}/api/events"
        self.delay = max(0.0, float(delay))
        self.timeout = timeout
        self._opener = opener
        self._sleeper = sleeper
        self._attempted = False

    def publish(self, payload: Mapping[str, Any]) -> bool:
        """POSTe un événement ; retourne False si le hub est indisponible."""
        try:
            if self.delay and self._attempted:
                self._sleeper(self.delay)
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            request = urllib.request.Request(
                self.url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            opener = self._opener or urllib.request.urlopen
            with opener(request, timeout=self.timeout):
                pass
        except Exception:  # noqa: BLE001 - le hub live ne doit jamais arrêter le pipeline
            return False
        finally:
            self._attempted = True
        return True


def make_publisher(
    live_url: str | None = None,
    *,
    delay: float = 0.0,
) -> LivePublisher | None:
    """Construit le publisher depuis l'option CLI ou NAVIMAP_LIVE_MAP_URL."""
    url = live_url or os.environ.get(LIVE_URL_ENV)
    if not url or not url.strip():
        return None
    return LivePublisher(url.strip(), delay=delay)


def status_payload(phase: str, message: str, progress: float) -> dict[str, Any]:
    return {
        "type": "status",
        "pipeline": PIPELINE,
        "phase": phase,
        "message": message,
        "progress": float(progress),
    }


def layer_payload(
    *,
    layer_id: str,
    title: str,
    kind: str,
    style: Mapping[str, Any],
    data: Mapping[str, Any] | None = None,
    url: str | None = None,
    coordinates: list[list[float]] | None = None,
) -> dict[str, Any]:
    if kind not in {"geojson", "image"}:
        raise ValueError(f"Type de couche live inconnu : {kind}")
    layer: dict[str, Any] = {
        "id": layer_id,
        "title": title,
        "group": PIPELINE,
        "kind": kind,
        "style": dict(style),
        "visible": True,
    }
    if kind == "geojson":
        if data is None:
            raise ValueError("Une couche GeoJSON live exige data.")
        layer["data"] = dict(data)
    else:
        if url is None or coordinates is None:
            raise ValueError("Une couche image live exige url et coordinates.")
        layer["url"] = url
        layer["coordinates"] = coordinates
    return {
        "type": "layer",
        "action": "upsert",
        "pipeline": PIPELINE,
        "layer": layer,
    }


def bbox_image_coordinates(
    bbox: tuple[float, float, float, float],
) -> list[list[float]]:
    """Coins MapLibre : nord-ouest, nord-est, sud-est, sud-ouest."""
    west, south, east, north = bbox
    return [
        [float(west), float(north)],
        [float(east), float(north)],
        [float(east), float(south)],
        [float(west), float(south)],
    ]


def reflectance_png_data_url(
    blue: np.ndarray,
    green: np.ndarray,
    nir: np.ndarray,
    *,
    max_size: int = 512,
) -> str:
    """Compose un PNG fausses couleurs NIR/vert/bleu, sans bibliothèque image."""
    channels = [np.asarray(channel, dtype=np.float64) for channel in (nir, green, blue)]
    if any(channel.ndim != 2 for channel in channels):
        raise ValueError("Les bandes live doivent être des tableaux 2D.")
    if len({channel.shape for channel in channels}) != 1:
        raise ValueError("Les bandes live doivent avoir la même forme.")
    height, width = channels[0].shape
    if not height or not width:
        raise ValueError("Les bandes live ne peuvent pas être vides.")
    if max_size < 1:
        raise ValueError("max_size doit être positif.")

    row_idx = _sample_indices(height, max_size)
    col_idx = _sample_indices(width, max_size)
    rgb = np.stack(
        [_stretch_channel(channel[np.ix_(row_idx, col_idx)]) for channel in channels],
        axis=-1,
    )
    png = _encode_rgb_png(rgb.tobytes(), len(col_idx), len(row_idx))
    return PNG_DATA_URL_PREFIX + base64.b64encode(png).decode("ascii")


def _sample_indices(length: int, max_size: int) -> np.ndarray:
    if length <= max_size:
        return np.arange(length)
    return np.linspace(0, length - 1, num=max_size, dtype=np.int64)


def _stretch_channel(channel: np.ndarray) -> np.ndarray:
    finite = channel[np.isfinite(channel)]
    if not finite.size:
        return np.zeros(channel.shape, dtype=np.uint8)
    low, high = np.percentile(finite, (2.0, 98.0))
    if high <= low:
        scaled = np.clip(np.nan_to_num(channel, nan=0.0), 0.0, 1.0)
    else:
        scaled = (np.nan_to_num(channel, nan=low) - low) / (high - low)
    return np.rint(np.clip(scaled, 0.0, 1.0) * 255.0).astype(np.uint8)


def _encode_rgb_png(rgb: bytes, width: int, height: int) -> bytes:
    stride = width * 3
    scanlines = b"".join(
        b"\x00" + rgb[offset : offset + stride]
        for offset in range(0, len(rgb), stride)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=6))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
