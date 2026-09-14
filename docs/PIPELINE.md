# Chaîne prévue

Chaque produit exporté porte l’avertissement **Ne convient pas à la navigation**.

Deux chemins v0.2, même tampon.

```
AOI YAML (une baie)
        │
        ▼
  STAC CDSE  ──────────────────────────  v0.1  (sans compte)
        │
        ▼
  Téléchargement SAFE L1C  ────────────  v0.2  (compte CDSE, OData)
        │                                refuse MSIL2A
        ▼
  ACOLITE CLI + limit=bbox + DSF ──────  v0.2
        │
        ├─► L2R (rhos_*) déjà sur le Mac ──► coastline.geojson
        │     MNDWI rhos_561 / rhos_1612, seuil 0
        │
        ├─► L2W (rhos_*) ──► MNDWI / contours ──► coastline.geojson
        ├─► eau claire + grande tache ─► shallow.geojson     (plats, pas un écueil)
        └─► Stumpf (bleu/vert) ──► soundings.geojson
                    ▲                    interdit sans calage
                    │
              calage ICESat-2 ATL24  ──  v0.3
```

Le **L2A Sen2Cor** (BOA) n’est **pas** une entrée ACOLITE. ACOLITE attend le **L1C** (TOA).

## v0.2 — L1C → ACOLITE CLI

| Module | Fichier | Rôle |
|---|---|---|
| Zone | `aoi.py`, `aois/*.yaml` | Rectangle, dates, seuil de nuages, phase de campagne |
| Campagne | `campaign.py`, `aois/berry/` | Expédition → route → monde, une baie à la fois |
| Recherche | `acquire/stac.py` | Catalogue STAC CDSE (L1C par défaut) |
| Catalogue | `acquire/odata.py` | UUID / nom SAFE |
| Téléchargement | `acquire/download.py` | OData `$value`, cache, retries, zip + reçu SHA256 |
| Compte | `acquire/auth.py` | Jeton Data Space + refresh |
| ACOLITE | `correct/acolite.py` | Settings + CLI (`limit=south,west,north,east`) |
| L2W | `extract/l2w.py` | Bandes `rhos_*` |
| Indices | `extract/water_index.py` | NDWI, MNDWI, NDVI, Otsu |
| Contours | `extract/coastline.py` | Marching squares, sans GDAL |
| Plats | `extract/shallow.py` | Grandes taches claires (min. surface) |
| Glint | `correct/glint.py` | Hedley sur tableaux numpy |
| SDB | `sdb/stumpf.py` | Ratio de bandes + calage linéaire |
| Chaîne | `process.py` | `navimap-sat process` / `process-l2w` |
| OSM | `vectorize/osm_schema.py` | Tags OpenSeaMap et codes S-57 / S-101 |
| Export | `vectorize/export.py` | GeoJSON + métadonnées d’incertitude |
| Démo | `demo.py` | Île synthétique pour tester les maths |

```bash
navimap-sat process aois/calvi.yaml --out work/calvi
navimap-sat campaign aois/berry
```

## v0.2 — L2R ACOLITE déjà calculé (Mac)

| Module | Fichier | Rôle |
|---|---|---|
| Corridor | `aois/la-rochelle.yaml` | Bbox Vague 4, collection `sentinel-2-l1c` |
| Scène déjà là | `aois/scenes_la_rochelle.json` | L1C T30TWR + chemin L2R (ne pas retélécharger) |
| Garde L1C | `acquire/l1c.py` | Refuse `MSIL2A` |
| `.env` Mac | `acquire/envfile.py` | Relit le `.env` BI déjà rempli |
| L2R | `correct/l2r.py` | `rhos_561` / `rhos_1612`, refuse L1R |
| Contour 0 | `extract/zero_contour.py` | Grille lon/lat, sans GDAL |
| Tampon OSM | `vectorize/stamp.py` | `source=sentinel-pilot`, jamais de sondage |
| Chaîne | `pipeline_coastline.py` | Une commande : `navimap-sat coastline` |
| ICESat (porte) | `icesat_gate.py` | Compte les granules, **n’écrit pas** de profondeur |

```bash
navimap-sat coastline \
  --l2r ~/Desktop/sentinel-pilot/acolite \
  --aoi aois/la-rochelle.yaml \
  --out ~/Desktop/sentinel-pilot/coastline.geojson
```

Guide Mac : [`MAC_V02.md`](MAC_V02.md). Leçons : [`LECONS_L1C_ACOLITE.md`](LECONS_L1C_ACOLITE.md).

## Téléchargement

Deux formes, une commande :

```bash
navimap-sat download S2C_MSIL1C_…     # zip + SHA256 (recette Mac)
navimap-sat download aois/calvi.yaml  # meilleur L1C, extrait .SAFE
```

Le L2A est refusé (`L2ARejected`). Jeton OData : voir [`.env.example`](../.env.example).

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

## ICESat-2

`navimap-sat icesat-check` : **garde-fou**. Pas de profondeur en mètres
tant que le calage n’est pas fait. ATL24 / OpenOceans : plus tard.

## Hors scope (volontaire)

Super-résolution 2,5 m, SAM-2 / SegFormer, réseaux PINN, encodeur ENC, validation S-58, calage ICESat-2. Sujets de laboratoire, pas ce livrable.

Pipeline ACOLITE / CDSE / MNDWI dans **Blue-Intelligence-Map** : BI importe seulement le GeoJSON final.
