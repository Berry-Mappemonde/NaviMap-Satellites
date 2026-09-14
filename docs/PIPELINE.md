# Chaîne prévue

Chaque produit exporté porte l’avertissement **Ne convient pas à la navigation**.

```
AOI YAML (une baie)
        │
        ▼
  STAC CDSE  ──────────────────────────  v0.1  (sans compte)
        │
        ▼
  Téléchargement fenêtre Sentinel-2  ──  v0.2  (compte CDSE)
        │
        ▼
  Correction marine (ACOLITE) + glint ─  v0.2
        │
        ├─► MNDWI / Otsu / contours ──► coastline.geojson     (v0.1 démo)
        │
        └─► Stumpf (bleu/vert) ──► soundings.geojson
                    ▲
                    │
              calage ICESat-2 ATL24  ──  v0.3
```

## v0.1 — ce qui est dans le code

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

## Ce qui est volontairement hors v0.1

Super-résolution 2,5 m, SAM-2 / SegFormer, réseaux PINN, encodeur ENC, validation S-58. Ce sont des sujets de laboratoire, pas le premier livrable.
