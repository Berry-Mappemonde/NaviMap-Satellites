# NaviMap Satellites — notes pour les agents

## Projet

Atelier d’hydrographie par satellite (Sentinel-2, ACOLITE, ICESat-2 ATL24, fond
NASA GIBS). **Ne convient pas à la navigation.**

Dépôt officiel : `https://github.com/Berry-Mappemonde/NaviMap-Satellites`
(organisation, pas `NAVIGUIDE-for-Berry-Mappemonde`).

## Environnement

- Install Cloud Agent : `bash .cursor/install.sh` (crée `.venv`, `pip install -e ".[dev]"`).
- Commande : `.venv/bin/navimap-sat` ou `source .venv/bin/activate`.
- Tests : `pytest`. Réseau CDSE optionnel : `NAVIMAP_LIVE=1 pytest -k live_cdse`.

## Cursor Cloud specific instructions

### Pull requests GitHub

Le dépôt est sous l’organisation **Berry-Mappemonde**. L’app Cursor y a accès.

1. Pousser la branche `cursor/**`.
2. Ouvrir ou mettre à jour la PR avec `ManagePullRequest` (pas `gh pr create`).
3. Si `ManagePullRequest` échoue (rate limit, ancien mapping vers le compte
   personnel), le workflow **Ouvrir les PR Cursor**
   (`.github/workflows/open-cursor-pr.yml`) ouvre la PR via `GITHUB_TOKEN`.

- Contrôle : `python3 scripts/open_cursor_prs.py --dry-run`.
- Runbook : [`docs/GITHUB_PR_CURSOR.md`](docs/GITHUB_PR_CURSOR.md).
- La CI tourne aussi sur les poussées `cursor/**`.
