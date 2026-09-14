"""Ce qu'une carte marine contient, et ce que NaviMap extrait vraiment.

Une carte officielle n'est pas que la bathymétrie : feux, balises, TSS,
règlements, dangers isolés. Le satellite n'en voit qu'une petite partie.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartLayer:
    id: str
    title: str
    source: str
    role: str
    status: str
    notes: str


CHART_LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer(
        id="photo",
        title="Photo satellite",
        source="NASA GIBS / Worldview",
        role="fond",
        status="présent",
        notes="Tuiles JPEG. Pas une mesure. Interdit pour Stumpf / MNDWI.",
    ),
    ChartLayer(
        id="coastline",
        title="Trait de côte",
        source="Sentinel-2 + ACOLITE",
        role="extrait",
        status="présent",
        notes="MNDWI. Limite terre/mer indicative.",
    ),
    ChartLayer(
        id="shallow",
        title="Plats clairs",
        source="Sentinel-2",
        role="extrait",
        status="présent",
        notes="Grandes taches. Pas un écueil isolé.",
    ),
    ChartLayer(
        id="atl24",
        title="Points de calage",
        source="ICESat-2 ATL24 (NASA)",
        role="contrôle",
        status="présent",
        notes="Trace lidar. Calent Stumpf. Ce ne sont pas des sondages de carte.",
    ),
    ChartLayer(
        id="soundings",
        title="Sondages dérivés",
        source="Stumpf calé ATL24",
        role="extrait",
        status="si calé",
        notes="Indicatif, eaux claires, 0–15 m. Jamais un ENC.",
    ),
    ChartLayer(
        id="intertidal",
        title="Estran",
        source="schéma OSM",
        role="schéma",
        status="cible",
        notes="Pas encore extrait automatiquement.",
    ),
    ChartLayer(
        id="rock",
        title="Écueil isolé",
        source="hors pixel 10 m",
        role="hors",
        status="invisible",
        notes="Un danger métrique peut disparaître sous un pixel Sentinel-2.",
    ),
    ChartLayer(
        id="light",
        title="Feux / balises / AMS",
        source="hors optique",
        role="hors",
        status="hors périmètre",
        notes="Une carte marine officielle les porte ; le satellite couleur non.",
    ),
    ChartLayer(
        id="tss",
        title="Dispositifs de séparation / règlements",
        source="hors optique",
        role="hors",
        status="hors périmètre",
        notes="Juridique, pas radiométrique.",
    ),
    ChartLayer(
        id="cmems",
        title="Vent / houle / courant",
        source="Copernicus Marine",
        role="hors NaviMap",
        status="autre service",
        notes="NAVIGUIDE / Blue Intelligence. Pas les images Sentinel.",
    ),
)


def layer_rows() -> list[dict[str, str]]:
    return [
        {
            "id": row.id,
            "title": row.title,
            "source": row.source,
            "role": row.role,
            "status": row.status,
            "notes": row.notes,
        }
        for row in CHART_LAYERS
    ]
