"""Correspondances télédétection → OpenSeaMap / S-57 / S-101.

Ce tableau est un *schéma cible*. v0.1 n'écrit que du GeoJSON annoté
(tags OSM). Il n'émet pas de fichier ENC.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OsmMapping:
    feature: str
    osm_tags: dict[str, str]
    s57: str
    s101: str
    notes: str


FEATURE_MAP: tuple[OsmMapping, ...] = (
    OsmMapping(
        feature="coastline_high_water",
        osm_tags={"natural": "coastline"},
        s57="COALNE",
        s101="Coastline",
        notes="Ligne de pleine mer. WATLEV=2 (always dry) côté S-57.",
    ),
    OsmMapping(
        feature="intertidal",
        osm_tags={"natural": "wetland", "tidal": "yes"},
        s57="DEPARE",
        s101="DepthArea",
        notes="Estran. DRVAL1 < 0, DRVAL2 = 0.",
    ),
    OsmMapping(
        feature="depth_area",
        osm_tags={"seamark:type": "depth_area"},
        s57="DEPARE",
        s101="DepthArea",
        notes="Polygone entre deux isobathes. DRVAL1 / DRVAL2.",
    ),
    OsmMapping(
        feature="depth_contour",
        osm_tags={"contour": "elevation", "seamark:type": "depth_contour"},
        s57="DEPCNT",
        s101="DepthContour",
        notes="Isobathe. VALDCO en mètres.",
    ),
    OsmMapping(
        feature="sounding",
        osm_tags={"seamark:type": "depth"},
        s57="SOUNDG",
        s101="Sounding",
        notes="Sondage ponctuel. Tag OSM depth=* (mètres).",
    ),
    OsmMapping(
        feature="calibration_sounding",
        osm_tags={"seamark:type": "depth", "navimap:role": "calibration"},
        s57="SOUNDG",
        s101="Sounding",
        notes="Point de calage ICESat-2 ATL24. Ce n'est pas un sondage de carte.",
    ),
    OsmMapping(
        feature="breakwater",
        osm_tags={"man_made": "breakwater"},
        s57="SLCONS",
        s101="ShorelineConstruction",
        notes="Digue / brise-lames. CATSLC=1.",
    ),
    OsmMapping(
        feature="pier",
        osm_tags={"man_made": "pier"},
        s57="SLCONS",
        s101="ShorelineConstruction",
        notes="Jetée / ponton. CATSLC=4.",
    ),
    OsmMapping(
        feature="reef",
        osm_tags={"natural": "reef", "seamark:type": "reef"},
        s57="OBSTRN",
        s101="Obstruction",
        notes="Récif. CATOBS=6 possible.",
    ),
    OsmMapping(
        feature="rock",
        osm_tags={"seamark:type": "rock"},
        s57="UWTROC",
        s101="UnderwaterAwashRock",
        notes="Écueil isolé. Invisible sous un pixel de 10 m.",
    ),
)


def mapping_by_feature(name: str) -> OsmMapping:
    for row in FEATURE_MAP:
        if row.feature == name:
            return row
    raise KeyError(name)


def schema_rows() -> list[dict[str, str]]:
    return [
        {
            "feature": row.feature,
            "osm": " ".join(f"{k}={v}" for k, v in row.osm_tags.items()),
            "s57": row.s57,
            "s101": row.s101,
            "notes": row.notes,
        }
        for row in FEATURE_MAP
    ]
