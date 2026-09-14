"""Présence ICESat-2 (CMR). N'écrit aucune profondeur.

Sur La Rochelle (2026-09-14) : ATL24=5 et ATL03=5 → SDB *possible plus tard*.
Tant qu'aucun granule n'est téléchargé et calé : pas de sondage.
"""

from __future__ import annotations

from typing import Any

import httpx

from navimap_satellites.aoi import BBox
from navimap_satellites.basemap.gibs import worldview_url
from navimap_satellites.quality.disclaimer import NASA_VISUAL_NOTE

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"

# Constat Vague 4 (bbox La Rochelle). Rappel, pas une autorisation de SDB.
LA_ROCHELLE_CMR_NOTE = (
    "CMR a déjà vu ATL24=5 et ATL03=5 sur le corridor La Rochelle "
    "(2026-09-14). On n'invente pas de profondeur tant que les granules "
    "ne sont pas téléchargés et calés (v0.3)."
)


def count_granules(short_name: str, bbox: BBox, *, client: httpx.Client | None = None) -> int:
    west, south, east, north = bbox
    own = client is None
    http = client or httpx.Client(timeout=45.0)
    try:
        response = http.get(
            CMR,
            params={
                "short_name": short_name,
                "bounding_box": f"{west},{south},{east},{north}",
                "page_size": 5,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        entries = ((response.json() or {}).get("feed") or {}).get("entry") or []
    finally:
        if own:
            http.close()
    return len(entries)


def presence_report(bbox: BBox) -> dict[str, Any]:
    atl24 = count_granules("ATL24", bbox)
    atl03 = count_granules("ATL03", bbox)
    allowed = atl24 > 0 or atl03 > 0
    return {
        "bbox": list(bbox),
        "atl24": atl24,
        "atl03": atl03,
        "sdb_allowed_later": allowed,
        "soundings_written": False,
        "worldview_url": worldview_url(bbox),
        "gibs_note": NASA_VISUAL_NOTE,
        "message": (
            LA_ROCHELLE_CMR_NOTE
            if allowed
            else "Aucune trace ICESat-2 : on n'invente pas de profondeur."
        ),
    }
