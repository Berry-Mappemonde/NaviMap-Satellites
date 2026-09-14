# Deux Copernicus, deux comptes

C’est la confusion la plus fréquente. « J’ai Copernicus » ne dit pas encore de **quel** Copernicus.

## 1. Copernicus Data Space Ecosystem (CDSE)

- Site : https://dataspace.copernicus.eu
- Données : photos des satellites **Sentinel-1** (radar) et **Sentinel-2** (couleurs), etc.
- Utile ici : trouver et plus tard télécharger une image d’une baie.
- Identifiants dans `.env` : `CDSE_USERNAME`, `CDSE_PASSWORD`.

Sur le Mac de Clément, le login CDSE est **déjà** dans
`/Users/clement/Blue-Intelligence-Map/scripts/satellite/.env`
(mot de passe entre quotes). NaviMap le lit tout seul.
Ne créez pas un second fichier secret « pour voir ».

La **recherche** (`navimap-sat search`) parle au catalogue STAC public :

`https://stac.dataspace.copernicus.eu/v1/search`

Elle marche **sans** mot de passe. Le mot de passe sert au **téléchargement** (`navimap-sat download` / `process`).

Créer un compte : bouton Register sur le site Data Space. Ce n’est pas le même login que Marine.

## 2. Copernicus Marine Service (CMEMS)

- Site : https://marine.copernicus.eu
- Données : grilles déjà calculées de **vent**, **houle**, **courant**.
- Utile pour NAVIGUIDE et l’atlas climatologique de Blue Intelligence.
- Identifiants typiques : `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD`.

NaviMap Satellites **n’utilise pas** CMEMS en v0.1. Un compte Marine ne débloque pas les images Sentinel.

## Comment vérifier

```bash
# Dans le dossier du projet, après avoir rempli .env
source .venv/bin/activate
navimap-sat auth-check
```

- Succès : le programme a obtenu un jeton Data Space. Vous pourrez télécharger plus tard.
- Échec « compte manquant » : le fichier `.env` est vide — la recherche d’images reste possible.
- Échec « CDSE a refusé » : vous avez probablement collé le login **Marine**. Créez un compte Data Space.

## Téléchargement (rappel pour plus tard)

Les fichiers Sentinel-2 L2A pèsent souvent **500 Mo à 1 Go** par scène. On ne les mettra jamais sur le petit VPS de production. On travaillera sur le Mac, une baie à la fois, en ne gardant que la fenêtre utile.
