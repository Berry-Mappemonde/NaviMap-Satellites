from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from navimap_satellites.quality.disclaimer import DISCLAIMER, IHO_NOTE, NOT_FOR_NAVIGATION


def product_metadata(
    *,
    kind: str,
    method: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bloc métadonnées commun à coller sur chaque FeatureCollection."""
    meta: dict[str, Any] = {
        "name": "NaviMap Satellites",
        "kind": kind,
        "method": method,
        "source": source,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_for_navigation": True,
        "warning": NOT_FOR_NAVIGATION,
        "disclaimer": DISCLAIMER,
        "iho_note": IHO_NOTE,
        "license": "MIT for the software; Copernicus Sentinel data remains Copernicus.",
    }
    if extra:
        meta.update(extra)
    return meta
