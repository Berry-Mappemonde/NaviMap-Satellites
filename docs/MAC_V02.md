# v0.2 sur votre Mac — pas à pas

Machine : Mac Apple silicon, utilisateur `clement`.
Tout se passe **sur le Mac**, jamais sur le serveur (VPS).

Blue Intelligence reste ici : `/Users/clement/Blue-Intelligence-Map`
(pas `~/Documents/…`).

---

## 0. Une fois — récupérer NaviMap Satellites

Ouvrez **Terminal** (Spotlight → `Terminal`).

```bash
cd ~
git clone https://github.com/NAVIGUIDE-for-Berry-Mappemonde/NaviMap-Satellites.git
cd NaviMap-Satellites
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Si le dossier existe déjà (clone v0.1) :

```bash
cd ~/NaviMap-Satellites
git fetch origin
git pull
source .venv/bin/activate
pip install -e ".[dev]"
```

Le mot de passe CDSE est déjà dans
`/Users/clement/Blue-Intelligence-Map/scripts/satellite/.env`.
On ne le redemande pas. On ne le copie pas.

Vérifier (optionnel) :

```bash
navimap-sat auth-check
```

Vous devez lire qu’un jeton a été obtenu. La recherche d’images, elle,
marche même sans jeton.

---

## 1. Ne pas retélécharger

Vous avez déjà, sur le Bureau :

- le zip / `.SAFE` **L1C** du 12 septembre 2026, tuile **T30TWR**
- `download_receipt.json` (empreinte sha256)
- le résultat ACOLITE utile :

```
~/Desktop/sentinel-pilot/acolite/S2C_MSI_2026_09_12_11_18_31_T30TWR_L2R.nc
```

**On réutilise ce L2R.** Pas de nouvel ACOLITE, pas de nouveau zip.

Si un jour il fallait relancer ACOLITE (déjà fait) :

```bash
cd ~/acolite
conda activate acolite
python launch_acolite.py
```

Input = dossier `.SAFE` dont le nom contient `MSIL1C`.  
Output = `~/Desktop/sentinel-pilot/acolite`.  
DSF, pas TACT.

---

## 2. Extraire le trait de côte (ce que v0.2 ajoute)

Toujours dans Terminal :

```bash
cd ~/NaviMap-Satellites
source .venv/bin/activate
navimap-sat coastline \
  --l2r ~/Desktop/sentinel-pilot/acolite \
  --aoi aois/la-rochelle.yaml \
  --out ~/Desktop/sentinel-pilot/coastline.geojson
```

Le programme :

- prend **`rhos_561`** et **`rhos_1612`**
- calcule le MNDWI, contour au **seuil 0**
- écrit un GeoJSON avec `natural=coastline`, `source=sentinel-pilot`
- ajoute l’avertissement **Ne convient pas à la navigation**
- **n’écrit aucun sondage**

Ouvrez `~/Desktop/sentinel-pilot/coastline.geojson` sur
[geojson.io](https://geojson.io) pour voir la ligne.

---

## 3. Le donner à Blue Intelligence (montrer, pas fabriquer)

1. Lancez Blue Intelligence en local, comme d’habitude.
2. Mode **Science**.
3. Importer le GeoJSON du Bureau.
4. Filtre **Satellite (pilote)**.

La Review reste éteinte. Ce n’est pas une carte marine.

---

## Si ça bloque

| Message | Que faire |
|---|---|
| `aucun *L2R*.nc` | Vérifiez le dossier `~/Desktop/sentinel-pilot/acolite`. Pas le L1R. |
| `L1R est une étape intermédiaire` | Pointez le fichier dont le nom contient `L2R`. |
| `ACOLITE refuse … L2A` | Vous avez donné un `MSIL2A`. Utilisez le L1C / le L2R déjà là. |
| `netCDF4 manquant` | `pip install -e ".[dev]"` dans le `.venv` de NaviMap. |
| PNG ACOLITE tout noir | Normal. On l’ignore. La vérité est dans le `.nc`. |

## Ce qu’on ne fait jamais

- Recaler l’image avec un VLM ou `geo.py`
- Inventer une profondeur sans ICESat-2 calé
- Lancer ACOLITE ou un téléchargement **sur le VPS**
- Mettre le `.env` dans Git
- Relancer `infra/vps/sync-from-atlas.sh`
