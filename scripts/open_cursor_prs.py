#!/usr/bin/env python3
"""Ouvre une PR pour chaque branche ``cursor/*`` en avance sur ``main``.

Le dépôt est sous l'organisation Berry-Mappemonde. ``ManagePullRequest`` est
la voie normale. Ce script reste le secours Actions : si Cursor échoue
(rate limit, ancien mapping vers le compte personnel, ``must be a
collaborator``), ``GITHUB_TOKEN`` ouvre la PR.

    Validation Failed: {"resource":"Issue","code":"custom","message":"must be a collaborator"}
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

DEFAULT_PREFIX = "cursor/"
DEFAULT_BASE = "main"
BLOCKING_PR_STATES = frozenset({"OPEN", "MERGED", "CLOSED"})
PR_PERMISSION_MARKERS = (
    "not permitted to create or approve pull requests",
    "must be a collaborator",
)


def is_pr_permission_blocked(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PR_PERMISSION_MARKERS)


@dataclass(frozen=True)
class BranchDecision:
    name: str
    ahead_by: int
    title: str
    body: str
    skip_reason: str | None

    @property
    def should_open(self) -> bool:
        return self.skip_reason is None


def cursor_branch_names(names: Sequence[str], prefix: str = DEFAULT_PREFIX) -> list[str]:
    banned = {prefix, prefix.rstrip("/")}
    return sorted(name for name in names if name.startswith(prefix) and name not in banned)


def should_open_pr(ahead_by: int, existing_states: Sequence[str]) -> bool:
    if ahead_by < 1:
        return False
    states = {state.upper() for state in existing_states}
    return not (states & BLOCKING_PR_STATES)


def pr_title(commit_messages: Sequence[str], branch: str) -> str:
    for message in reversed(commit_messages):
        subject = message.splitlines()[0].strip() if message else ""
        if subject and not subject.lower().startswith("merge "):
            return subject[:72]
    slug = branch.removeprefix(DEFAULT_PREFIX).replace("-", " ")
    return f"chore: {slug}"


def pr_body(branch: str, commit_messages: Sequence[str]) -> str:
    subjects = []
    for message in commit_messages:
        subject = message.splitlines()[0].strip() if message else ""
        if subject:
            subjects.append(f"- {subject}")
    commits = "\n".join(subjects) if subjects else "- *(aucun message de commit)*"
    return (
        f"PR ouverte automatiquement pour `{branch}`.\n"
        "\n"
        "Secours Actions : si `ManagePullRequest` a échoué (rate limit, ancien "
        "compte personnel, ou `must be a collaborator`), le bot a poussé la "
        "branche et Actions ouvre la PR avec `GITHUB_TOKEN`.\n"
        "\n"
        "Détail : [`docs/GITHUB_PR_CURSOR.md`](docs/GITHUB_PR_CURSOR.md).\n"
        "\n"
        "### Commits\n"
        f"{commits}\n"
    )


def skip_reason(ahead_by: int, existing_states: Sequence[str]) -> str | None:
    if ahead_by < 1:
        return "pas en avance sur la base"
    states = {state.upper() for state in existing_states}
    if "OPEN" in states:
        return "une PR ouverte existe déjà"
    if "MERGED" in states:
        return "une PR fusionnée existe déjà"
    if "CLOSED" in states:
        return "une PR fermée existe déjà"
    return None


class GitHub:
    def __init__(self, repo: str) -> None:
        self.repo = repo

    def run(self, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["gh", *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def json(self, args: Sequence[str]) -> Any:
        result = self.run(args)
        text = result.stdout.strip()
        return json.loads(text) if text else None

    def list_branch_names(self) -> list[str]:
        result = self.run(
            [
                "api",
                "--paginate",
                "--jq",
                ".[].name",
                f"repos/{self.repo}/branches?per_page=100",
            ]
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def compare(self, base: str, head: str) -> tuple[int, list[str]]:
        data = self.json(["api", f"repos/{self.repo}/compare/{base}...{head}"])
        if not isinstance(data, dict):
            return 0, []
        ahead = int(data.get("ahead_by") or 0)
        messages: list[str] = []
        for commit in data.get("commits") or []:
            if not isinstance(commit, dict):
                continue
            payload = commit.get("commit") or {}
            message = payload.get("message") if isinstance(payload, dict) else None
            if isinstance(message, str):
                messages.append(message)
        return ahead, messages

    def pr_states_by_head(self) -> dict[str, list[str]]:
        # Ne pas filtrer avec --head owner:branche : gh coupe « cursor/foo »
        # comme propriétaire « cursor » et rate à côté des PR.
        data = self.json(
            [
                "pr",
                "list",
                "--repo",
                self.repo,
                "--state",
                "all",
                "--limit",
                "200",
                "--json",
                "state,headRefName",
            ]
        )
        return index_pr_states_by_head(data if isinstance(data, list) else [])

    def create_pr(self, *, base: str, head: str, title: str, body: str) -> str:
        result = self.run(
            [
                "pr",
                "create",
                "--repo",
                self.repo,
                "--base",
                base,
                "--head",
                head,
                "--title",
                title,
                "--body",
                body,
                "--draft",
            ],
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        combined = f"{result.stdout}\n{result.stderr}"
        if "already exists" in combined.lower():
            return ""
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )


def index_pr_states_by_head(items: Sequence[Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        head = item.get("headRefName")
        state = item.get("state")
        if isinstance(head, str) and isinstance(state, str) and head:
            mapping.setdefault(head, []).append(state)
    return mapping


def detect_repo() -> str:
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env:
        return env
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def plan_branch(
    gh: GitHub,
    branch: str,
    base: str,
    existing_states: Sequence[str] | None = None,
) -> BranchDecision:
    ahead_by, messages = gh.compare(base, branch)
    states = list(existing_states) if existing_states is not None else []
    return BranchDecision(
        name=branch,
        ahead_by=ahead_by,
        title=pr_title(messages, branch),
        body=pr_body(branch, messages),
        skip_reason=skip_reason(ahead_by, states),
    )


def open_missing_prs(
    gh: GitHub,
    *,
    base: str = DEFAULT_BASE,
    prefix: str = DEFAULT_PREFIX,
    dry_run: bool = False,
    only: str | None = None,
) -> int:
    names = cursor_branch_names(gh.list_branch_names(), prefix=prefix)
    states_by_head = gh.pr_states_by_head()
    if only:
        names = [name for name in names if name == only]
        if not names:
            print(f"aucune branche {only!r} avec le préfixe {prefix!r}", file=sys.stderr)
            return 1

    opened = 0
    for name in names:
        decision = plan_branch(gh, name, base, states_by_head.get(name, []))
        if not decision.should_open:
            print(f"skip {name} — {decision.skip_reason}")
            continue
        print(f"{'dry-run ' if dry_run else ''}open {name} — {decision.title}")
        if dry_run:
            opened += 1
            continue
        try:
            url = gh.create_pr(
                base=base,
                head=name,
                title=decision.title,
                body=decision.body,
            )
        except subprocess.CalledProcessError as exc:
            combined = f"{exc.stdout or ''}\n{exc.stderr or ''}"
            if is_pr_permission_blocked(combined):
                print(
                    f"skip {name} — GitHub refuse que Actions crée la PR "
                    "(Settings → Actions → General : cocher "
                    "Allow GitHub Actions to create and approve pull requests).",
                    file=sys.stderr,
                )
                continue
            raise
        if url:
            print(url)
        else:
            print(f"skip {name} — une PR existe déjà (course)")
            continue
        opened += 1
    print(f"{opened} PR {'à ouvrir' if dry_run else 'ouverte(s)'}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE, help="Branche cible (défaut: main)")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Préfixe des branches agent")
    parser.add_argument("--branch", help="Ne traiter que cette branche")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans créer")
    parser.add_argument("--repo", help="owner/name (défaut: GITHUB_REPOSITORY ou gh)")
    args = parser.parse_args(argv)

    try:
        repo = args.repo or detect_repo()
        gh = GitHub(repo)
        return open_missing_prs(
            gh,
            base=args.base,
            prefix=args.prefix,
            dry_run=args.dry_run,
            only=args.branch,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        print(stderr or str(exc), file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    sys.exit(main())
