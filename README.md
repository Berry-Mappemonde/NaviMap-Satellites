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
2. télécharge un granule **L1C** (compte Data Space ; le L2A Sen2Cor est refusé) ;
3. lance **ACOLITE en ligne de commande** sur la fenêtre de la baie (pas la GUI) ;
4. relit aussi un **L2R déjà calculé** sur le Mac (`navimap-sat coastline`) ;
5. extrait un trait de côte (MNDWI) et de **grands plats clairs** (pas un rocher isolé) ;
6. estime une bathymétrie simple (Stumpf) **si** on la cale (ICESat-2 ATL24 ou coefficients) ;
7. pose un fond **NASA GIBS** (photo, pas une mesure) ;
8. écrit du GeoJSON avec les tags OpenSeaMap.

La version **0.3** ajoute le calage ATL24 et le fond GIBS. Une carte marine
n’est **pas** que la bathymétrie : `navimap-sat layers`. Sans compte ni
ACOLITE, `demo`, `search` et `basemap` suffisent.

## Ce que ce n’est pas

| Attendu parfois | Réalité |
|---|---|
| Carte marine officielle | Non — et ce ne sera jamais un substitut au SHOM |
| Écueil / épave isolée | Non — invisible sous 10 m |
| Continent de plastique | Non — le gyre n’est pas une île sur Sentinel-2 |
| Fichier ENC S-57 / S-101 | Non — le tableau de correspondance est là, pas l’encodeur |
| Vent / houle Copernicus | Autre service (**Copernicus Marine**). Voir `docs/COMPTES_COPERNICUS.md` |
| Le monde entier d’un clic | Non — une baie, hors ligne, sur votre Mac |
| Profondeur officielle | Non — ATL24 cale Stumpf, ce n’est pas un ENC |
| Photo NASA = carte | Non — GIBS est un fond JPEG, pas une réflectance |

## Installation (Mac)

Dans le Terminal, à l’endroit où vous voulez le dossier :

```bash
git clone https://github.com/NAVIGUIDE-for-Berry-Mappemonde/NaviMap-Satellites.git
cd NaviMap-Satellites
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Si le clone est déjà là mais que `.venv` n’existe pas
(`activate: No such file` / `navimap-sat: command not found`) :

```bash
cd ~/NaviMap-Satellites
bash scripts/setup-mac.sh
source .venv/bin/activate
navimap-sat --version
```

`(base)` est conda : ça ne contient pas `navimap-sat`. Le prompt doit montrer `(.venv)`.

Pour lire un NetCDF ACOLITE (L2R ou L2W) : `pip install -e ".[dev]"` suffit
(`netCDF4` est dans l’extra `dev`). Sinon : `pip install -e ".[l2r]"` ou `".[l2w]"`.

ACOLITE n’est pas un paquet pip. Clonez [acolite/acolite](https://github.com/acolite/acolite), puis dans `.env` :

```bash
ACOLITE_DIR=/chemin/vers/acolite
```

## Premier essai — sans compte satellite

```bash
source .venv/bin/activate
navimap-sat demo
```

Fichiers dans `work/demo/` :

- `coastline.geojson` — trait de côte de l’île imaginaire ;
- `shallow.geojson` — grandes taches d’eau claire (démo) ;
- `atl24.geojson` — trace de calage (ICESat-2 **synthétique**) ;
- `soundings.geojson` — sondages Stumpf calés sur cette trace ;
- `preview.html` — fond NASA GIBS + couches (ouvrir dans un navigateur).

Vous pouvez ouvrir les GeoJSON dans [geojson.io](https://geojson.io) ou QGIS.

```bash
navimap-sat schema
navimap-sat layers
navimap-sat basemap aois/calvi.yaml --out work/calvi.html
```

## Trait de côte depuis le L2R déjà sur le Bureau

Vous avez déjà le fichier ACOLITE. On ne le recalcule pas.

```bash
navimap-sat coastline \
  --l2r ~/Desktop/sentinel-pilot/acolite \
  --aoi aois/la-rochelle.yaml \
  --out ~/Desktop/sentinel-pilot/coastline.geojson
```

Résultat : `natural=coastline`, `source=sentinel-pilot`, bandeau *pas pour la navigation*.
Importez ce GeoJSON dans Blue Intelligence (mode Science). Pas de profondeur.

Guide Mac : [`docs/MAC_V02.md`](docs/MAC_V02.md). Leçons L1C : [`docs/LECONS_L1C_ACOLITE.md`](docs/LECONS_L1C_ACOLITE.md).

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
navimap-sat download S2C_MSIL1C_20260912T110631_N0512_R137_T30TWR_20260912T130923
navimap-sat acolite aois/calvi.yaml --input work/scenes/S2…SAFE --out work/acolite
navimap-sat process-l2w aois/calvi.yaml --l2w work/acolite/…L2W.nc --out work/calvi
```

`download` accepte un YAML d’AOI (meilleur L1C, extrait `.SAFE`) **ou** un identifiant `MSIL1C` (zip + reçu SHA256, recette Mac). `MSIL2A` est refusé.

Ou d’un coup (toujours **une** baie) :

```bash
navimap-sat process aois/calvi.yaml --out work/calvi
```

Sans calage, pas de sondages en mètres — seulement côte et plats clairs.
Le calage : `--atl24 points.geojson` (photons ICESat-2) ou `--stumpf-m0` / `--stumpf-m1`.

```bash
navimap-sat atl24 aois/calvi.yaml          # CMR, sans filtrer sur les dates Sentinel
navimap-sat atl24 aois/calvi.yaml --dates  # fenêtre de l'AOI (souvent vide)
navimap-sat process-l2w aois/calvi.yaml --l2w work/acolite/…L2W.nc --atl24 points.geojson
```

## Compte Copernicus — lequel ?

| Service | Sert à | Compte |
|---|---|---|
| Copernicus Data Space (CDSE) | Images Sentinel-1/2 | [dataspace.copernicus.eu](https://dataspace.copernicus.eu) |
| Copernicus Marine (CMEMS) | Vent, vagues, courant | [marine.copernicus.eu](https://marine.copernicus.eu) |
| NASA Earthdata | ICESat-2 ATL24 (calage) ; GIBS sans login | [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov) |

Détails : [`docs/COMPTES_COPERNICUS.md`](docs/COMPTES_COPERNICUS.md), [`docs/NASA.md`](docs/NASA.md). Chaîne : [`docs/PIPELINE.md`](docs/PIPELINE.md).

## Feuille de route

| Version | Objectif |
|---|---|
| 0.1 | Recherche STAC, algorithmes testés, démo GeoJSON, schéma OSM |
| 0.2 | L1C, ACOLITE CLI, L2R déjà calculé, plats clairs, campagne Berry |
| **0.3** (cette page) | Fond GIBS, CMR ATL24, calage Stumpf sur points ICESat-2 |
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
- Fond GIBS : mentionner NASA ESDIS (voir `docs/NASA.md`).
- ICESat-2 ATL24 : citer le DOI NSIDC du produit utilisé.
- Ce logiciel n’est **pas** un service hydrographique.

---

*Orthographe du dépôt :* **Satellites** (un seul « t » au milieu).
