# PR GitHub et Cloud Agents Cursor

## État actuel

Le dépôt est sous l’organisation
**[Berry-Mappemonde](https://github.com/Berry-Mappemonde/NaviMap-Satellites)**.
L’app GitHub [Cursor](https://github.com/apps/cursor) y est installée
(tous les dépôts, droits Pull requests + Issues).

`ManagePullRequest` est la voie normale. L’ancien blocage
(`must be a collaborator`) valait pour le compte personnel
`NAVIGUIDE-for-Berry-Mappemonde`.

Le workflow **Ouvrir les PR Cursor** reste en secours : rate limit GitHub,
environnement Cursor encore pointé vers l’ancien propriétaire, ou échec
ponctuel de l’app.

## Créer un agent ou un environnement

Utilisez uniquement :

```text
https://github.com/Berry-Mappemonde/NaviMap-Satellites
```

Pas `NAVIGUIDE-for-Berry-Mappemonde/NaviMap-Satellites`. Cursor affiche alors
*You do not have access to this repository*. Enchaîner les tentatives
produit *GitHub is rate limiting requests* : attendre la fin de l’heure UTC,
puis reconnecter GitHub dans Cursor en accordant l’organisation
Berry-Mappemonde.

## Secours Actions (ce dépôt)

1. **Permissions Actions** (réglage GitHub, hors git) :
   - jeton des workflows en **écriture** ;
   - case *Allow GitHub Actions to create and approve pull requests* cochée.
2. **Workflow** [`.github/workflows/open-cursor-pr.yml`](../.github/workflows/open-cursor-pr.yml) :
   à chaque poussée `cursor/**`, toutes les 6 heures, ou à la main, il lance
   [`scripts/open_cursor_prs.py`](../scripts/open_cursor_prs.py).
3. **CI** aussi sur les poussées `cursor/**`, car une PR créée par
   `GITHUB_TOKEN` ne redéclenche pas les workflows `pull_request`.

## Vérifier

```bash
python3 scripts/open_cursor_prs.py --dry-run
```

Réglages Actions (admin) :

```bash
gh api repos/Berry-Mappemonde/NaviMap-Satellites/actions/permissions/workflow
```

Attendu : `default_workflow_permissions=write` et
`can_approve_pull_request_reviews=true`.

Pour forcer une passe :

```text
Actions → Ouvrir les PR Cursor → Run workflow
```

Jeton de secours (optionnel) : secret dépôt `PR_GITHUB_TOKEN` (PAT `repo`).
Le workflow l’utilise s’il est défini.

## Si ça casse à nouveau

| Symptôme | Cause probable | Quoi faire |
|---|---|---|
| `You do not have access to this repository` | URL ou mapping Cursor encore sur le compte personnel | Reprendre l’URL `Berry-Mappemonde/NaviMap-*`, reconnecter GitHub |
| `GitHub is rate limiting requests` | Trop d’essais API | Attendre la fin de l’heure UTC |
| Workflow vert, pas de PR | Branche déjà suivie, ou pas en avance sur `main` | `python3 scripts/open_cursor_prs.py --dry-run` |
| CI `pull_request` en *action_required* | PR ouverte par `github-actions[bot]` | La CI sur `push` `cursor/**` a déjà tourné ; approuver une fois ou fusionner |
| `GitHub Actions is not permitted to create or approve pull requests` | Case Actions décochée | Recocher + `default_workflow_permissions=write` |
| `must be a collaborator` dans le tableau de bord Cursor | Jeton encore vu comme dépôt personnel | Ignorer ; le workflow Actions ouvre la PR |
| CI absente sur la nouvelle branche | Workflow pas encore sur `main` | Fusionner ce correctif, ou pousser un commit |
