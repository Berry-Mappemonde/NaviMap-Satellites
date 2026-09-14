# Chaîne prévue

Chaque produit exporté porte l’avertissement **Ne convient pas à la navigation**.

```
AOI YAML (une baie)
        │
        ▼
  STAC CDSE  ──────────────────────────  v0.1  (sans compte)
        │
        ▼
  Téléchargement L1C (refuse MSIL2A) ─  v0.2  (déjà fait sur le Mac)
        │
        ▼
  ACOLITE DSF → *L2R*.nc  ────────────  v0.2  (déjà calculé, on le relit)
        │
        ├─► MNDWI rhos_561/rhos_1612, seuil 0 ──► coastline.geojson   (v0.2)
        │
        └─► Stumpf ── interdit tant que ICESat-2 n'est pas calé ──  v0.3
```

## v0.2 — L2R ACOLITE → trait de côte

| Module | Fichier | Rôle |
|---|---|---|
| Corridor | `aois/la-rochelle.yaml` | Bbox Vague 4, collection `sentinel-2-l1c` |
| Scène déjà là | `aois/scenes_la_rochelle.json` | L1C T30TWR + chemin L2R (ne pas retélécharger) |
| Garde L1C | `acquire/l1c.py` | Refuse `MSIL2A` |
| `.env` Mac | `acquire/envfile.py` | Relit le `.env` BI déjà rempli |
| Téléchargement | `acquire/download.py` | Zip L1C ; saute si le fichier existe |
| L2R | `correct/l2r.py` | `rhos_561` / `rhos_1612`, refuse L1R |
| Contour 0 | `extract/zero_contour.py` | Grille lon/lat, sans GDAL |
| Tampon OSM | `vectorize/stamp.py` | `source=sentinel-pilot`, jamais de sondage |
| Chaîne | `pipeline_coastline.py` | Une commande : `navimap-sat coastline` |
| ICESat (porte) | `icesat_gate.py` | Compte les granules, **n’écrit pas** de profondeur |

Guide Mac : `docs/MAC_V02.md`. Leçons : `docs/LECONS_L1C_ACOLITE.md`.

## v0.1 — ce qui reste (démo, maths)

| Module | Fichier | Rôle |
|---|---|---|
| Zone | `aoi.py`, `aois/*.yaml` | Rectangle, dates, seuil de nuages |
| Recherche | `acquire/stac.py` | Catalogue STAC CDSE |
| Compte | `acquire/auth.py` | Jeton Data Space (téléchargement futur) |
| Indices | `extract/water_index.py` | NDWI, MNDWI, NDVI, Otsu |
| Contours | `extract/coastline.py` | Marching squares, sans GDAL |
| Glint | `correct/glint.py` | Hedley sur tableaux numpy |
| SDB | `sdb/stumpf.py` | Ratio de bandes + calage linéaire |
| OSM | `vectorize/osm_schema.py` | Tags OpenSeaMap et codes S-57 / S-101 |
| Export | `vectorize/export.py` | GeoJSON + métadonnées d’incertitude |
| Démo | `demo.py` | Île synthétique pour tester les maths |

## Limites physiques (elles resteront)

- Eau turbide (estuaire, lagune) : le fond n’est plus visible → pas de SDB optique.
- Pixel 10 m : pas de détection garantie d’un danger métrique (norme IHO S-44 Exclusive / Special / 1a hors d’atteinte).
- Cible réaliste plus tard : indication type Order 1b / 2, eaux claires, 0–10 m, **non certifiée**.
- Sen2Cor (correction « terre ») produit souvent des réflectances marines fausses. D’où ACOLITE en v0.2.

## Hors scope (volontaire)

- Super-résolution, SAM-2, PINN, ENC S-57/S-101
- SDB / sondages (v0.3, après ATL24/ATL03 téléchargés)
- Pipeline ACOLITE / CDSE / MNDWI dans **Blue-Intelligence-Map**
  (BI importe seulement le GeoJSON final)
