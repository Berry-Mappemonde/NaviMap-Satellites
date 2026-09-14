# Leçons Vague 4 (ne pas les reapprendre)

Ces faits viennent du travail Mac du 2026-09-14. On les garde ici
pour ne rien perdre, et pour ne rien refaire pour rien.

## Deux Copernicus

| Compte | Sert à | Où |
|---|---|---|
| **CDSE** (Data Space) | Images Sentinel | [dataspace.copernicus.eu](https://dataspace.copernicus.eu) |
| **CMEMS** (Marine) | Vent, houle, courant | [marine.copernicus.eu](https://marine.copernicus.eu) |

Le login CDSE est **déjà OK** sur le Mac. Fichier secret (gitignoré) :

`/Users/clement/Blue-Intelligence-Map/scripts/satellite/.env`

Mot de passe **entre quotes** à cause du `$`. Ne pas le recoller dans un chat.
Ne pas le committer. NaviMap le relit tout seul.

## L1C, pas L2A

ACOLITE a dit : `Level-2A data not supported`.

- **L2A ESA (Sen2Cor)** = correction **terre**. Ce n’est pas un raccourci mer.
- **L1C** = image brute. ACOLITE part de là et écrit un **L2R.nc**.

Jumeau déjà sur le Bureau (ne pas retélécharger) :

`S2C_MSIL1C_20260912T110631_N0512_R137_T30TWR_20260912T130923`

Le zip L2A du même jour peut rester sur le Bureau : on ne le pointe plus.

## ACOLITE (déjà fait)

- Clone : `~/acolite` (pas dans un repo)
- Env : `conda activate acolite` (`/opt/miniconda3`)
- Recette : `conda env create --file environment.yml` (pas `pip install -r`)
- GUI : Input = dossier `.SAFE` **MSIL1C** ; Output = `~/Desktop/sentinel-pilot/acolite`
- Algorithme : **DSF**. Pas TACT.
- ToS Anaconda déjà acceptées.

Fichier utile :

`~/Desktop/sentinel-pilot/acolite/S2C_MSI_2026_09_12_11_18_31_T30TWR_L2R.nc`

À **ignorer** :

- `*L1R*.nc` (étape intermédiaire)
- PNG rgb / rhos **quasi noir** (aperçu mal étiré, pas un échec)

## Bandes L2R (vérifiées)

`rhos_444, 489, 561, 667, 707, 741, 785, 835, 866, 1612, 2191`

- Vert : **`rhos_561`** (min ≈ −0,0019, max ≈ 0,4171, 100 % valides)
- SWIR MNDWI : **`rhos_1612`** (pas `rhos_1614`)

Formule : `MNDWI = (rhos_561 − rhos_1612) / (rhos_561 + rhos_1612)`, contour **seuil 0**.

## Corridor

~30 milles autour de La Rochelle, centre (−1,167 ; 46,1541) :

`[-1.666, 45.655, -0.668, 46.653]`

Ne pas recaler avec un VLM ni `geo.py`.

## ICESat-2 (plus tard)

CMR, même bbox : **ATL24 = 5**, **ATL03 = 5**. Une SDB sera possible en v0.3.
**Interdit d’inventer une profondeur** tant que les granules ne sont pas
téléchargés et calés. v0.2 = trait de côte seulement.

## Qui fait quoi

| NaviMap Satellites | Blue Intelligence |
|---|---|
| Fabrique (Sentinel → GeoJSON) | Montre, contrôle, versionne (import Science + bandeau) |
| Jamais sur le VPS | Le simulateur s’en sert pour le film |

Phrase métier : **BI montre, contrôle et versionne. Le simulateur s’en sert pour le film.**
