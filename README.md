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
2. sait extraire un trait de côte (indices MNDWI + contours) ;
3. sait estimer une bathymétrie simple (formule de Stumpf), **si** on a de quoi la caler ;
4. écrit du GeoJSON avec les tags OpenSeaMap (`natural=coastline`, `seamark:type=depth`, …).

La version **0.1** fait déjà les étapes 1 et 4, et les étapes 2–3 sur une **île imaginaire** (pour vérifier les maths sans télécharger 800 Mo). Le téléchargement réel des images et la correction atmosphérique marine (ACOLITE) viennent ensuite.

## Ce que ce n’est pas

| Attendu parfois | Réalité v0.1 |
|---|---|
| Carte marine officielle | Non — et ce ne sera jamais un substitut au SHOM |
| Fichier ENC S-57 / S-101 | Non — le tableau de correspondance est là, pas l’encodeur |
| Vent / houle Copernicus | Autre service (**Copernicus Marine**). Voir `docs/COMPTES_COPERNICUS.md` |
| Traitement mondial sur un petit serveur | Non — une zone, hors ligne, sur votre Mac |

## Installation (Mac)

Dans le Terminal, à l’endroit où vous voulez le dossier :

```bash
git clone https://github.com/NAVIGUIDE-for-Berry-Mappemonde/navimap-satellites.git
cd navimap-satellites
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Premier essai — sans compte satellite

```bash
source .venv/bin/activate
navimap-sat demo
```

Deux fichiers apparaissent dans `work/demo/` :

- `coastline.geojson` — trait de côte de l’île imaginaire ;
- `soundings.geojson` — sondages ponctuels (formule de Stumpf calée sur cette scène).

Vous pouvez les ouvrir dans [geojson.io](https://geojson.io) ou QGIS.

Voir le tableau des tags :

```bash
navimap-sat schema
```

## Chercher de vraies images Sentinel-2

La **recherche** est publique. Pas besoin de mot de passe.

```bash
navimap-sat search aois/calvi.yaml
```

Exemple de zone déjà écrite : baie de Calvi (Corse), eaux plutôt claires — un bon premier terrain. L’étang de Thau (`aois/etang-de-thau.yaml`) sert de contre-exemple : eau turbide, mauvaise candidate pour la bathymétrie optique.

Pour du JSON :

```bash
navimap-sat search aois/calvi.yaml --json
```

## Compte Copernicus — lequel ?

Vous avez peut-être déjà un compte **Copernicus Marine** (vent, houle, courant pour NAVIGUIDE). **Ce n’est pas le même** que **Copernicus Data Space** (images Sentinel).

| Service | Sert à | Compte |
|---|---|---|
| Copernicus Data Space (CDSE) | Images Sentinel-1/2 | [dataspace.copernicus.eu](https://dataspace.copernicus.eu) |
| Copernicus Marine (CMEMS) | Vent, vagues, courant | [marine.copernicus.eu](https://marine.copernicus.eu) |

La recherche d’images marche sans compte. Le **téléchargement** (phase suivante) exigera CDSE. Copiez `.env.example` vers `.env` puis :

```bash
navimap-sat auth-check
```

Détails : [`docs/COMPTES_COPERNICUS.md`](docs/COMPTES_COPERNICUS.md). Chaîne prévue : [`docs/PIPELINE.md`](docs/PIPELINE.md).

## Feuille de route

| Version | Objectif |
|---|---|
| **0.1** (cette page) | Recherche STAC, algorithmes testés, démo GeoJSON, schéma OSM / S-57 / S-101 |
| 0.2 | Télécharger une fenêtre Sentinel-2 + ACOLITE (correction marine) |
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
