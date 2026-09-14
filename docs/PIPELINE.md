# Chaîne prévue

Chaque produit exporté porte l’avertissement **Ne convient pas à la navigation**.

```
AOI YAML (une baie)
        │
        ▼
  STAC CDSE  ──────────────────────────  v0.1  (sans compte)
        │
        ▼
  Téléchargement SAFE L1C  ────────────  v0.2  (compte CDSE, OData)
        │
        ▼
  ACOLITE CLI + limit=bbox + glint ───  v0.2
        │
        ├─► MNDWI / Otsu / contours ──► coastline.geojson
        ├─► eau claire + grande tache ─► shallow.geojson     (plats, pas un écueil)
        └─► Stumpf (bleu/vert) ──► soundings.geojson
                    ▲
                    │
              calage ICESat-2 ATL24  ──  v0.3
```

## v0.2 — ce qui est dans le code

| Module | Fichier | Rôle |
|---|---|---|
| Zone | `aoi.py`, `aois/*.yaml` | Rectangle, dates, seuil de nuages, phase de campagne |
| Campagne | `campaign.py`, `aois/berry/` | Expédition → route → monde, une baie à la fois |
| Recherche | `acquire/stac.py` | Catalogue STAC CDSE (L2A ou L1C) |
| Catalogue | `acquire/odata.py` | UUID / nom SAFE |
| Téléchargement | `acquire/download.py` | OData `$value`, cache, retries |
| Compte | `acquire/auth.py` | Jeton Data Space + refresh |
| ACOLITE | `correct/acolite.py` | Settings + CLI |
| L2W | `extract/l2w.py` | Bandes `rhos_*` |
| Indices | `extract/water_index.py` | NDWI, MNDWI, NDVI, Otsu |
| Contours | `extract/coastline.py` | Marching squares, sans GDAL |
| Plats | `extract/shallow.py` | Grandes taches claires (min. surface) |
| Glint | `correct/glint.py` | Hedley sur tableaux numpy |
| SDB | `sdb/stumpf.py` | Ratio de bandes + calage linéaire |
| OSM | `vectorize/osm_schema.py` | Tags OpenSeaMap et codes S-57 / S-101 |
| Export | `vectorize/export.py` | GeoJSON + métadonnées d’incertitude |
| Démo | `demo.py` | Île synthétique pour tester les maths |

## Pourquoi L1C, pas L2A

Sen2Cor (L2A) est une correction « terre ». DSF / ACOLITE part du spectre sombre en TOA. Relancer DSF sur un L2A, c’est corriger deux fois. Le L2A peut servir à filtrer les nuages ; l’entrée ACOLITE est le **L1C**.

## Limites physiques (elles resteront)

- Eau turbide (estuaire, lagune) : le fond n’est plus visible → pas de SDB optique.
- Pixel 10 m : pas de détection garantie d’un danger métrique (norme IHO S-44 Exclusive / Special / 1a hors d’atteinte).
- Cible réaliste plus tard : indication type Order 1b / 2, eaux claires, 0–10 m, **non certifiée**.
- Pas de nappe de plastique opérationnelle.
- ACOLITE n’est pas un service CDSE : le satellite s’arrête au SAFE.

## Campagne mondiale (méthode, pas un bouton)

1. `expedition` — escales / fenêtres déjà listées dans `aois/berry/`.
2. `route` — autres segments, une bbox YAML de plus.
3. `world` — autres côtes claires, jamais un traitement global sur un petit serveur.

## Ce qui est volontairement hors v0.2

Super-résolution 2,5 m, SAM-2 / SegFormer, réseaux PINN, encodeur ENC, validation S-58, calage ICESat-2. Sujets de laboratoire, pas ce livrable.
