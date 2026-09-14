"""Fond visuel NASA GIBS / Worldview.

Tuiles JPEG déjà colorisées : utiles pour se situer, interdites pour
Stumpf, MNDWI ou ACOLITE. Blue Marble peint souvent le large en bleu plat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from navimap_satellites.aoi import BBox
from navimap_satellites.quality.disclaimer import NASA_GIBS_ACK, NASA_VISUAL_NOTE, NOT_FOR_NAVIGATION

GIBS_WMTS_ROOT = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
WORLDVIEW_URL = "https://worldview.earthdata.nasa.gov/"


@dataclass(frozen=True)
class GibsLayer:
    id: str
    layer: str
    title: str
    tile_matrix_set: str
    extension: str
    timed: bool
    max_native_zoom: int
    notes: str


GIBS_LAYERS: tuple[GibsLayer, ...] = (
    GibsLayer(
        id="viirs",
        layer="VIIRS_SNPP_CorrectedReflectance_TrueColor",
        title="VIIRS SNPP — vraies couleurs (quotidien)",
        tile_matrix_set="GoogleMapsCompatible_Level9",
        extension="jpg",
        timed=True,
        max_native_zoom=9,
        notes="~375 m. Fond du jour. Trop grossier pour une baie à 10 m.",
    ),
    GibsLayer(
        id="modis",
        layer="MODIS_Terra_CorrectedReflectance_TrueColor",
        title="MODIS Terra — vraies couleurs (quotidien)",
        tile_matrix_set="GoogleMapsCompatible_Level9",
        extension="jpg",
        timed=True,
        max_native_zoom=9,
        notes="~250 m. Archive longue. Même limite : pas une mesure.",
    ),
    GibsLayer(
        id="blue-marble",
        layer="BlueMarble_NextGeneration",
        title="Blue Marble Next Generation (mosaïque 2004)",
        tile_matrix_set="GoogleMapsCompatible_Level8",
        extension="jpeg",
        timed=False,
        max_native_zoom=8,
        notes="500 m. Le large est souvent un bleu peint. Décoratif seulement.",
    ),
    GibsLayer(
        id="blue-marble-bathy",
        layer="BlueMarble_ShadedRelief_Bathymetry",
        title="Blue Marble + ombrage bathymétrique (décoratif)",
        tile_matrix_set="GoogleMapsCompatible_Level8",
        extension="jpeg",
        timed=False,
        max_native_zoom=8,
        notes="Ombrage, pas une grille de sondages. Ne pas y lire des profondeurs.",
    ),
)


def gibs_layer(layer_id: str) -> GibsLayer:
    for row in GIBS_LAYERS:
        if row.id == layer_id:
            return row
    known = ", ".join(row.id for row in GIBS_LAYERS)
    raise KeyError(f"Couche GIBS inconnue : {layer_id}. Choisir : {known}")


def tile_url_template(layer: GibsLayer | str, *, date: str | None = None) -> str:
    """URL Leaflet / XYZ ({z}/{y}/{x}). Sans compte."""
    spec = gibs_layer(layer) if isinstance(layer, str) else layer
    if spec.timed:
        day = date or "default"
        return (
            f"{GIBS_WMTS_ROOT}/{spec.layer}/default/{day}/"
            f"{spec.tile_matrix_set}/{{z}}/{{y}}/{{x}}.{spec.extension}"
        )
    return (
        f"{GIBS_WMTS_ROOT}/{spec.layer}/default/"
        f"{spec.tile_matrix_set}/{{z}}/{{y}}/{{x}}.{spec.extension}"
    )


def worldview_url(bbox: BBox, *, date: str | None = None, layer_id: str = "viirs") -> str:
    """Lien Worldview cadré sur la baie (exploration, pas un export)."""
    west, south, east, north = bbox
    pad_x = max((east - west) * 0.25, 0.05)
    pad_y = max((north - south) * 0.25, 0.05)
    spec = gibs_layer(layer_id)
    day = date or "default"
    time = f"{day}-T00:00:00Z" if day != "default" else "default"
    return (
        f"{WORLDVIEW_URL}?v={west - pad_x},{south - pad_y},{east + pad_x},{north + pad_y}"
        f"&t={time}&l={spec.layer},Coastlines_15m"
    )


def write_preview_html(
    path: str | Path,
    *,
    bbox: BBox,
    title: str,
    date: str,
    collections: dict[str, dict[str, Any]] | None = None,
    default_layer: str = "viirs",
) -> Path:
    """Carte Leaflet : fond GIBS + GeoJSON (côte, plats, calage, sondages)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    layers = {spec.id: spec for spec in GIBS_LAYERS}
    if default_layer not in layers:
        raise KeyError(default_layer)
    payload = {
        "bbox": list(bbox),
        "date": date,
        "defaultLayer": default_layer,
        "disclaimer": NOT_FOR_NAVIGATION,
        "visualNote": NASA_VISUAL_NOTE,
        "ack": NASA_GIBS_ACK,
        "collections": collections or {},
        "tiles": {
            spec.id: {
                "title": spec.title,
                "url": tile_url_template(spec, date=date if spec.timed else None),
                "maxNativeZoom": spec.max_native_zoom,
                "notes": spec.notes,
            }
            for spec in GIBS_LAYERS
        },
    }
    body = _PREVIEW_HTML.replace("__TITLE__", _escape_html(title)).replace(
        "__PAYLOAD__", _json_for_script(payload)
    )
    dest.write_text(body, encoding="utf-8")
    return dest


def _json_for_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_PREVIEW_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>__TITLE__ — NaviMap (pas pour la navigation)</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    html, body { height: 100%; margin: 0; font-family: system-ui, sans-serif; }
    #map { height: 100%; }
    .banner {
      position: absolute; z-index: 1000; left: 12px; right: 12px; top: 12px;
      background: #7a1f1f; color: #fff; padding: 8px 12px; border-radius: 6px;
      font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.25);
    }
    .panel {
      position: absolute; z-index: 1000; left: 12px; bottom: 24px;
      background: rgba(255,255,255,.94); padding: 10px 12px; border-radius: 6px;
      max-width: 360px; font-size: 12px; line-height: 1.4;
      box-shadow: 0 2px 8px rgba(0,0,0,.2);
    }
    .panel h1 { font-size: 14px; margin: 0 0 6px; }
    .panel label { display: block; margin: 4px 0; }
    .swatch { display: inline-block; width: 10px; height: 10px; margin-right: 4px; }
  </style>
</head>
<body>
  <div class="banner">Ne convient pas à la navigation — croquis satellite, pas une carte officielle.</div>
  <div id="map"></div>
  <div class="panel" id="panel"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
  const P = __PAYLOAD__;
  const map = L.map("map");
  const [w,s,e,n] = P.bbox;
  map.fitBounds([[s, w], [n, e]]);
  const tiles = {};
  Object.entries(P.tiles).forEach(([id, spec], i) => {
    tiles[id] = L.tileLayer(spec.url, {
      attribution: "NASA GIBS / ESDIS",
      maxNativeZoom: spec.maxNativeZoom,
      maxZoom: 16,
    });
    if (id === P.defaultLayer) tiles[id].addTo(map);
  });
  const colors = {
    coastline: "#111",
    shallow: "#c9a227",
    atl24: "#c0392b",
    soundings: "#1f4e79",
  };
  function addCollection(key, style) {
    const fc = P.collections[key];
    if (!fc || !fc.features || !fc.features.length) return null;
    return L.geoJSON(fc, {
      style: () => style,
      pointToLayer: (feat, latlng) => L.circleMarker(latlng, {
        radius: key === "atl24" ? 5 : 3,
        color: style.color,
        fillColor: style.color,
        fillOpacity: 0.8,
        weight: 1,
      }),
      onEachFeature: (feat, layer) => {
        const p = feat.properties || {};
        const depth = p.depth != null ? p.depth + " m" : "";
        layer.bindPopup((p["navimap:feature"] || key) + (depth ? " — " + depth : ""));
      },
    }).addTo(map);
  }
  addCollection("coastline", {color: colors.coastline, weight: 2, fill: false});
  addCollection("shallow", {color: colors.shallow, weight: 1, fillColor: colors.shallow, fillOpacity: 0.25});
  addCollection("soundings", {color: colors.soundings});
  addCollection("atl24", {color: colors.atl24});
  const panel = document.getElementById("panel");
  let radios = "";
  Object.entries(P.tiles).forEach(([id, spec]) => {
    const checked = id === P.defaultLayer ? " checked" : "";
    radios += `<label><input type="radio" name="gibs" value="${id}"${checked}> ${spec.title}</label>`;
  });
  panel.innerHTML = `
    <h1>__TITLE__</h1>
    <p><strong>${P.disclaimer}</strong></p>
    <p>${P.visualNote}</p>
    ${radios}
    <p>
      <span class="swatch" style="background:${colors.coastline}"></span>trait de côte
      <span class="swatch" style="background:${colors.shallow}"></span>plats clairs
      <span class="swatch" style="background:${colors.atl24}"></span>calage ATL24
      <span class="swatch" style="background:${colors.soundings}"></span>sondages dérivés
    </p>
    <p>Pas de feux, balises, règlements, TSS. Une carte marine n'est pas que la bathymétrie.</p>
    <p>${P.ack}</p>
  `;
  panel.querySelectorAll("input[name=gibs]").forEach((el) => {
    el.addEventListener("change", () => {
      Object.values(tiles).forEach((t) => map.removeLayer(t));
      tiles[el.value].addTo(map);
    });
  });
  </script>
</body>
</html>
"""
