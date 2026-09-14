# Données NASA : photo de la Terre, pas une carte marine

Une carte marine n’est **pas** que la bathymétrie (feux, balises, TSS,
règlements). Les « photos NASA de la Terre » non plus : ce sont surtout
un **fond visuel** et, à part, un **lidar de calage**.

Voir `navimap-sat layers`.

## Trois familles

| Famille | Quoi | Pour NaviMap |
|---|---|---|
| Illustration | Blue Marble, Visible Earth | Communication. L’océan profond est souvent un bleu **peint**. |
| Tuiles quotidiennes | [Worldview](https://worldview.earthdata.nasa.gov) + [GIBS](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api) | Fond dans `preview.html`. JPEG colorisé : **interdit** pour Stumpf / MNDWI / ACOLITE. |
| Mesure | ICESat-2 **ATL24**, Landsat L1 | ATL24 cale les profondeurs. Landsat 30 m = secours, pas le chemin nominal. |

HLS (Harmonized Landsat Sentinel-2) : produit **terre**. LaSRC n’estime
pas les aérosols sur l’eau (panaches sombres sur les baies). Même famille
de problème que Sen2Cor. On garde ACOLITE sur du L1C.

## Commandes

```bash
navimap-sat layers
navimap-sat basemap aois/calvi.yaml --out work/calvi.html
navimap-sat atl24 aois/calvi.yaml
navimap-sat icesat-check --aoi aois/la-rochelle.yaml
navimap-sat process-l2w aois/calvi.yaml --l2w …L2W.nc --atl24 points.geojson
```

`icesat-check` et `atl24` **n’écrivent aucun sondage**. Ils disent si une
trace existe. Le calage (m0, m1) part d’un GeoJSON de photons fond, ou
de la trace synthétique de `demo`.

GIBS : **sans compte**. CMR ATL24 : **sans compte**. Téléchargement HDF5 :
compte [Earthdata Login](https://urs.earthdata.nasa.gov) — troisième
compte, voir [`COMPTES_COPERNICUS.md`](COMPTES_COPERNICUS.md).

## Licence

Données d’une mission NASA : ouvertes, en pratique **CC0**, citation
demandée. Pas d’endorsement NASA. Mention GIBS :

> We acknowledge the use of imagery provided by services from NASA's
> Global Imagery Browse Services (GIBS), part of NASA's Earth Science
> Data and Information System (ESDIS).

## Ce que ce n’est pas

- Pas un substitut au SHOM / ENC.
- ATL24 = points **le long d’une orbite**, pas une grille de baie.
- Blue Marble + bathymétrie = ombrage décoratif.
- OPERA DSWx = eau continentale, océan souvent masqué.
- SWOT = hauteur de **surface**, pas le fond.
