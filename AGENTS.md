# NaviMap Satellites — notes pour les agents

## Projet

Atelier d’hydrographie par satellite (Sentinel-2, ACOLITE, ICESat-2 ATL24, fond
NASA GIBS). **Ne convient pas à la navigation.**

## Environnement

- Install Cloud Agent : `bash .cursor/install.sh` (crée `.venv`, `pip install -e ".[dev]"`).
- Commande : `.venv/bin/navimap-sat` ou `source .venv/bin/activate`.
- Tests : `pytest`. Réseau CDSE optionnel : `NAVIMAP_LIVE=1 pytest -k live_cdse`.

## Cursor Cloud specific instructions

### Pull requests GitHub (compte personnel)

Le dépôt est sous un **compte utilisateur**, pas une organisation.
`cursor[bot]` pousse les branches `cursor/*` mais GitHub refuse la création de
PR (`must be a collaborator`).

**Ne pas abandonner la PR et ne pas la créer avec `gh pr create`.** Après le
`git push` sur `cursor/**`, le workflow **Ouvrir les PR Cursor**
(`.github/workflows/open-cursor-pr.yml`) ouvre les PR manquantes via
`GITHUB_TOKEN`.

- `ManagePullRequest` peut échouer : c’est le symptôme connu. Le workflow
  Actions est la voie officielle.
- La CI tourne aussi sur les poussées `cursor/**` (une PR ouverte par
  `GITHUB_TOKEN` ne déclenche pas `pull_request`).
- Contrôle : `python3 scripts/open_cursor_prs.py --dry-run`.
- Runbook : [`docs/GITHUB_PR_CURSOR.md`](docs/GITHUB_PR_CURSOR.md).

Tant que le propriétaire n’est pas une organisation GitHub, ce contournement
reste nécessaire.
