#!/usr/bin/env python3
"""Ouvre une PR pour chaque branche ``cursor/*`` en avance sur ``main``.

Sur ce dépôt (compte GitHub *personnel*, pas une organisation), ``cursor[bot]``
peut pousser une branche mais GitHub refuse la création de PR :

    Validation Failed: {"resource":"Issue","code":"custom","message":"must be a collaborator"}

Ce script tourne dans GitHub Actions avec ``GITHUB_TOKEN``, qui est autorisé à
créer des PR une fois les permissions workflow en écriture.
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
        "GitHub refuse que `cursor[bot]` crée une PR sur ce dépôt **personnel** "
        "(`must be a collaborator`). Le bot peut pousser la branche ; Actions ouvre "
        "la PR avec `GITHUB_TOKEN`.\n"
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
        self.owner = repo.split("/", 1)[0]

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

    def pr_states(self, head: str) -> list[str]:
        data = self.json(
            [
                "pr",
                "list",
                "--repo",
                self.repo,
                "--head",
                f"{self.owner}:{head}",
                "--state",
                "all",
                "--json",
                "state",
            ]
        )
        if not isinstance(data, list):
            return []
        return [str(item["state"]) for item in data if isinstance(item, dict) and "state" in item]

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
            ]
        )
        return result.stdout.strip()


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


def plan_branch(gh: GitHub, branch: str, base: str) -> BranchDecision:
    ahead_by, messages = gh.compare(base, branch)
    states = gh.pr_states(branch)
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
    if only:
        names = [name for name in names if name == only]
        if not names:
            print(f"aucune branche {only!r} avec le préfixe {prefix!r}", file=sys.stderr)
            return 1

    opened = 0
    for name in names:
        decision = plan_branch(gh, name, base)
        if not decision.should_open:
            print(f"skip {name} — {decision.skip_reason}")
            continue
        print(f"{'dry-run ' if dry_run else ''}open {name} — {decision.title}")
        if dry_run:
            opened += 1
            continue
        url = gh.create_pr(
            base=base,
            head=name,
            title=decision.title,
            body=decision.body,
        )
        print(url)
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
