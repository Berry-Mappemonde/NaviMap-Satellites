import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "open_cursor_prs.py"


def load_script():
    spec = importlib.util.spec_from_file_location("open_cursor_prs", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = load_script()


def workflow_on(data: dict):
    if True in data:
        return data[True]
    return data["on"]


def test_cursor_branch_names_keep_prefix_only():
    names = mod.cursor_branch_names(
        ["main", "cursor/foo", "feature/bar", "cursor/", "cursor/github-pr-collaborator-dfe8"]
    )
    assert names == ["cursor/foo", "cursor/github-pr-collaborator-dfe8"]


def test_should_open_pr_when_ahead_and_no_existing():
    assert mod.should_open_pr(1, []) is True
    assert mod.should_open_pr(3, []) is True


def test_should_not_open_pr_when_not_ahead_or_already_tracked():
    assert mod.should_open_pr(0, []) is False
    assert mod.should_open_pr(2, ["OPEN"]) is False
    assert mod.should_open_pr(2, ["MERGED"]) is False
    assert mod.should_open_pr(2, ["closed"]) is False


def test_pr_title_uses_latest_non_merge_subject():
    title = mod.pr_title(
        ["docs: premier", "Merge pull request #4 from x", "fix: droits collaborateur"],
        "cursor/github-pr-collaborator-dfe8",
    )
    assert title == "fix: droits collaborateur"


def test_pr_title_falls_back_to_branch_slug():
    assert mod.pr_title([], "cursor/mac-venv-setup-cbb0") == "chore: mac venv setup cbb0"


def test_pr_body_mentions_collaborator_limitation():
    body = mod.pr_body("cursor/demo-dfe8", ["fix: exemple"])
    assert "must be a collaborator" in body
    assert "ManagePullRequest" in body
    assert "`cursor/demo-dfe8`" in body
    assert "- fix: exemple" in body
    assert "docs/GITHUB_PR_CURSOR.md" in body


def test_index_pr_states_by_head_keeps_cursor_slashes():
    mapping = mod.index_pr_states_by_head(
        [
            {"headRefName": "cursor/github-pr-collaborator-dfe8", "state": "OPEN"},
            {"headRefName": "cursor/mac-venv-setup-cbb0", "state": "OPEN"},
            {"headRefName": "cursor/nasa-gibs-atl24-7805", "state": "MERGED"},
            {"state": "OPEN"},
        ]
    )
    assert mapping["cursor/github-pr-collaborator-dfe8"] == ["OPEN"]
    assert mapping["cursor/mac-venv-setup-cbb0"] == ["OPEN"]
    assert mapping["cursor/nasa-gibs-atl24-7805"] == ["MERGED"]


def test_skip_reason_messages():
    assert "avance" in (mod.skip_reason(0, []) or "")
    assert "ouverte" in (mod.skip_reason(1, ["OPEN"]) or "")
    assert "fusionnée" in (mod.skip_reason(1, ["MERGED"]) or "")
    assert "fermée" in (mod.skip_reason(1, ["CLOSED"]) or "")
    assert mod.skip_reason(1, []) is None


def test_open_cursor_pr_workflow_can_write_pull_requests():
    data = yaml.safe_load((ROOT / ".github/workflows/open-cursor-pr.yml").read_text(encoding="utf-8"))
    assert data["permissions"]["pull-requests"] == "write"
    assert data["permissions"]["issues"] == "write"
    branches = workflow_on(data)["push"]["branches"]
    assert "cursor/**" in branches
    assert "open_cursor_prs.py" in data["jobs"]["open-prs"]["steps"][-1]["run"]


def test_ci_runs_on_cursor_feature_branches():
    data = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert "cursor/**" in workflow_on(data)["push"]["branches"]
    assert data["permissions"]["contents"] == "read"
