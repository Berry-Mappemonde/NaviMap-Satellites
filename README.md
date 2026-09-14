# NaviMap Satellites

Atelier d’hydrographie par satellite : des images **Sentinel-2** (Copernicus Data Space) jusqu’à des fichiers **GeoJSON** annotés pour OpenSeaMap.

Projet [Berry-Mappemonde](https://berrymappemonde.org), side-project distinct de Blue Intelligence et de NAVIGUIDE.

> [!WARNING]
> **Ne convient pas à la navigation**
>
> Les traits de côte et les profondeurs calculés ici sont **indicatifs**.
> Ils ne sont pas des cartes officielles, pas des ENC (S-57 / S-101),
> et ne doivent pas être chargés dans un ECDIS. Un pixel Sentinel-2
> mesure 10 mètres : un écueil de 1 m peut être invisible.

## Qu’est-ce que c’est ?

Un petit programme Python qui, pour **une baie à la fois** :

1. cherche les images Sentinel-2 peu nuageuses (catalogue STAC public, **sans compte**) ;
2. télécharge un granule **L1C** (compte Data Space) ;
3. lance **ACOLITE en ligne de commande** sur la fenêtre de la baie (pas la GUI) ;
4. extrait un trait de côte (MNDWI + contours) et de **grands plats clairs** (pas un rocher isolé) ;
5. estime une bathymétrie simple (Stumpf) **si** on a de quoi la caler ;
6. écrit du GeoJSON avec les tags OpenSeaMap.

La version **0.2** enchaîne ces étapes. Sans compte ni ACOLITE, `demo` et `search` suffisent.

## Ce que ce n’est pas

| Attendu parfois | Réalité |
|---|---|
| Carte marine officielle | Non — et ce ne sera jamais un substitut au SHOM |
| Écueil / épave isolée | Non — invisible sous 10 m |
| Continent de plastique | Non — le gyre n’est pas une île sur Sentinel-2 |
| Fichier ENC S-57 / S-101 | Non — le tableau de correspondance est là, pas l’encodeur |
| Vent / houle Copernicus | Autre service (**Copernicus Marine**). Voir `docs/COMPTES_COPERNICUS.md` |
| Le monde entier d’un clic | Non — une baie, hors ligne, sur votre Mac |

## Installation (Mac)

Dans le Terminal, à l’endroit où vous voulez le dossier :

```bash
git clone https://github.com/NAVIGUIDE-for-Berry-Mappemonde/navimap-satellites.git
cd navimap-satellites
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Pour lire un NetCDF ACOLITE : `pip install -e ".[dev,l2w]"`.

ACOLITE n’est pas un paquet pip. Clonez [acolite/acolite](https://github.com/acolite/acolite), puis dans `.env` :

```bash
ACOLITE_DIR=/chemin/vers/acolite
```

## Premier essai — sans compte satellite

```bash
source .venv/bin/activate
navimap-sat demo
```

Trois fichiers apparaissent dans `work/demo/` :

- `coastline.geojson` — trait de côte de l’île imaginaire ;
- `shallow.geojson` — grandes taches d’eau claire (démo) ;
- `soundings.geojson` — sondages ponctuels (Stumpf calé sur cette scène).

Vous pouvez les ouvrir dans [geojson.io](https://geojson.io) ou QGIS.

```bash
navimap-sat schema
```

## Campagne Berry-Mappemonde

On commence par des **fenêtres côtières** (Calvi, puis quelques lagons ultramarins clairs), pas par le globe. Ce n’est pas l’itinéraire officiel.

```bash
navimap-sat campaign aois/berry
navimap-sat search aois/calvi.yaml --l1c
```

Étang de Thau (`aois/etang-de-thau.yaml`) : contre-exemple, eau turbide.

Détail : [`aois/berry/README.md`](aois/berry/README.md).

## Une vraie baie (compte CDSE + ACOLITE)

La recherche est publique. Le **téléchargement** exige un compte [Data Space](https://dataspace.copernicus.eu) — pas Marine. Copiez `.env.example` vers `.env`.

```bash
navimap-sat auth-check
navimap-sat download aois/calvi.yaml --out work/scenes
navimap-sat acolite aois/calvi.yaml --input work/scenes/S2…SAFE --out work/acolite
navimap-sat process-l2w aois/calvi.yaml --l2w work/acolite/…L2W.nc --out work/calvi
```

Ou d’un coup (toujours **une** baie) :

```bash
navimap-sat process aois/calvi.yaml --out work/calvi
```

Sans calage Stumpf, pas de sondages en mètres — seulement côte et plats clairs. Les coefficients viendront plus tard (ICESat-2).

## Compte Copernicus — lequel ?

| Service | Sert à | Compte |
|---|---|---|
| Copernicus Data Space (CDSE) | Images Sentinel-1/2 | [dataspace.copernicus.eu](https://dataspace.copernicus.eu) |
| Copernicus Marine (CMEMS) | Vent, vagues, courant | [marine.copernicus.eu](https://marine.copernicus.eu) |

Détails : [`docs/COMPTES_COPERNICUS.md`](docs/COMPTES_COPERNICUS.md). Chaîne : [`docs/PIPELINE.md`](docs/PIPELINE.md).

## Feuille de route

| Version | Objectif |
|---|---|
| 0.1 | Recherche STAC, algorithmes testés, démo GeoJSON, schéma OSM |
| **0.2** (cette page) | Téléchargement L1C, ACOLITE CLI, plats clairs, campagne Berry |
| 0.3 | Caler Stumpf sur ICESat-2 ATL24 (sans levé bateau) |
| 0.4 | Sentinel-1 (radar) pour le trait de côte par mauvais temps |
| plus tard | Export labo S-57, jamais pour un usage ECDIS |

## Tests

```bash
pytest
NAVIMAP_LIVE=1 pytest -k live_cdse   # optionnel : vraie API Copernicus
```

## Licence et données

- Code : MIT (`LICENSE`).
- Images Sentinel : programme Copernicus. Mentionner « Contains modified Copernicus Sentinel data » sur tout produit dérivé.
- Ce logiciel n’est **pas** un service hydrographique.

---

*Orthographe du dépôt :* **Satellites** (un seul « t » au milieu).
