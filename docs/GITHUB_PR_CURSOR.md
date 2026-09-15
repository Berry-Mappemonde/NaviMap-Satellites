# PR GitHub et Cloud Agents Cursor

## Le blocage

Le dépôt appartient à un **compte utilisateur**
(`NAVIGUIDE-for-Berry-Mappemonde`), pas à une organisation GitHub.

`cursor[bot]` (GitHub App Cursor) **peut pousser** une branche `cursor/*`.
Il **ne peut pas créer** la pull request. GitHub répond :

```text
Validation Failed: {"resource":"Issue","code":"custom","message":"must be a collaborator"}
```

On ne peut pas ajouter `cursor[bot]` comme collaborateur : ce n’est pas un
utilisateur. L’organisation `cursor` non plus.

Les PR #1 à #4 ont donc été ouvertes à la main par le propriétaire du dépôt.
L’agent « Stratégie du projet » a poussé `cursor/mac-venv-setup-cbb0` sans PR.

## Correctif en place (ce dépôt)

1. **Permissions Actions** (réglage GitHub, hors git) :
   - jeton des workflows en **écriture** ;
   - case *Allow GitHub Actions to create and approve pull requests* cochée.
   Sans ça, `GITHUB_TOKEN` ne peut pas ouvrir de PR sur un dépôt personnel.
2. **Workflow** [`.github/workflows/open-cursor-pr.yml`](../.github/workflows/open-cursor-pr.yml) :
   à chaque poussée `cursor/**`, toutes les 6 heures, ou à la main, il lance
   [`scripts/open_cursor_prs.py`](../scripts/open_cursor_prs.py).
3. **CI** aussi sur les poussées `cursor/**`, car une PR créée par
   `GITHUB_TOKEN` ne redéclenche pas les workflows `pull_request`.

Après fusion de ce correctif dans `main`, chaque nouvel agent qui branche
depuis `main` hérite du workflow : la PR s’ouvre toute seule.

## Vérifier

```bash
python3 scripts/open_cursor_prs.py --dry-run
```

Réglages Actions (admin) :

```bash
gh api repos/NAVIGUIDE-for-Berry-Mappemonde/NaviMap-Satellites/actions/permissions/workflow
```

Attendu : `default_workflow_permissions=write` et
`can_approve_pull_request_reviews=true`.

Pour forcer une passe :

```text
Actions → Ouvrir les PR Cursor → Run workflow
```

Jeton de secours (optionnel) : secret dépôt `PR_GITHUB_TOKEN` (PAT `repo`).
Le workflow l’utilise s’il est défini.

## Correctif structurel (organisation)

Pour que `ManagePullRequest` de Cursor fonctionne sans contournement :

1. Créer l’organisation GitHub **Berry-Mappemonde** (ou y transférer ce dépôt).
2. Réinstaller [l’app Cursor](https://github.com/apps/cursor) sur l’organisation,
   avec accès au dépôt et droits **Pull requests** + **Issues** en écriture.
3. Pointer le clone Mac et l’environnement Cloud Agent vers la nouvelle URL.

Tant que le propriétaire est un compte personnel, garder le workflow Actions.

## Si ça casse à nouveau

| Symptôme | Cause probable | Quoi faire |
|---|---|---|
| Workflow vert, pas de PR | Branche déjà suivie, ou pas en avance sur `main` | `python3 scripts/open_cursor_prs.py --dry-run` |
| `GitHub Actions is not permitted to create or approve pull requests` | Case Actions décochée | Recocher + `default_workflow_permissions=write` |
| `must be a collaborator` dans le tableau de bord Cursor | Attendu sur un dépôt personnel | Ignorer ; le workflow Actions ouvre la PR |
| CI absente sur la nouvelle branche | Workflow pas encore sur `main` | Fusionner ce correctif, ou pousser un commit |
