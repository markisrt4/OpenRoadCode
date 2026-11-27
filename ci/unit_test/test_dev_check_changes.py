"""Ruff publication records only its changes and respects failed checks and user work."""

import json
import subprocess

import pytest

from ci import dev_check_changes as changes


def git(root, *arguments):
    return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    git(root, "init", "-b", "feature/ruff-fixture")
    git(root, "config", "user.name", "Quality Test")
    git(root, "config", "user.email", "quality@example.invalid")
    (root / "a file.py").write_text("value=1\n")
    (root / "untouched.py").write_text("other = 1\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initial fixture")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-u", "origin", "feature/ruff-fixture")
    return root


def fake_tools(monkeypatch, *, edit=True, lint=0, gate=0, push=0, during_gate=None):
    original = changes.run
    calls = []

    def execute(command, root, *, capture=False):
        calls.append(command)
        if command[0] == "fake-ruff":
            if command[1] == "check" and edit:
                (root / "a file.py").write_text("value = 1\n")
            code = lint if command[1] == "check" else 0
            return subprocess.CompletedProcess(command, code, b"", b"")
        if "ci/quality_gate.py" in command:
            if during_gate is not None:
                during_gate(root)
            return subprocess.CompletedProcess(command, gate, b"", b"")
        if command[:2] == ["git", "push"] and push:
            return subprocess.CompletedProcess(command, push, b"", b"rejected")
        return original(command, root, capture=capture)

    monkeypatch.setattr(changes, "run", execute)
    monkeypatch.setattr(changes.quality_gate, "ruff_executable", lambda: "fake-ruff")
    return calls


def report(repo):
    return json.loads((repo / ".git/dev-check-last-run.json").read_text())


def test_publishes_only_recorded_ruff_files_and_handles_spaces(repo, monkeypatch):
    fake_tools(monkeypatch)
    assert changes.main(["--publish", "--message", "Ruff cleanup"], root=repo) == 0
    result = report(repo)
    assert result["files"] == ["a file.py"]
    assert result["pushed"] is True
    assert result["commit"] == git(repo, "rev-parse", "HEAD")
    assert git(repo, "show", "--pretty=", "--name-only", "HEAD") == "a file.py"
    assert git(repo, "rev-parse", "origin/feature/ruff-fixture") == result["commit"]


@pytest.mark.parametrize("staged", [False, True])
def test_existing_changes_are_never_included(repo, monkeypatch, staged):
    calls = fake_tools(monkeypatch)
    (repo / "untouched.py").write_text("user_work = True\n")
    if staged:
        git(repo, "add", "untouched.py")
    revision = git(repo, "rev-parse", "HEAD")
    assert changes.main(["--publish"], root=repo) == 1
    assert git(repo, "rev-parse", "HEAD") == revision
    assert not any(command[0] == "fake-ruff" for command in calls)


@pytest.mark.parametrize("lint,gate", [(1, 0), (0, 1)])
def test_failed_checks_keep_recorded_edits_without_committing(repo, monkeypatch, lint, gate):
    fake_tools(monkeypatch, lint=lint, gate=gate)
    revision = git(repo, "rev-parse", "HEAD")
    assert changes.main(["--publish"], root=repo) == 1
    assert report(repo)["files"] == ["a file.py"]
    assert report(repo)["commit"] is None
    assert git(repo, "rev-parse", "HEAD") == revision


def test_no_changes_creates_no_commit_or_push(repo, monkeypatch):
    calls = fake_tools(monkeypatch, edit=False)
    revision = git(repo, "rev-parse", "HEAD")
    assert changes.main(["--publish"], root=repo) == 0
    assert git(repo, "rev-parse", "HEAD") == revision
    assert not any(command[:2] == ["git", "push"] for command in calls)


def test_rejected_push_retains_commit_and_report(repo, monkeypatch):
    fake_tools(monkeypatch, push=1)
    assert changes.main(["--publish"], root=repo) == 1
    assert report(repo)["status"] == "push_failed"
    assert report(repo)["commit"] == git(repo, "rev-parse", "HEAD")
    assert not report(repo)["pushed"]


def test_changes_arriving_during_checks_are_not_committed(repo, monkeypatch):
    fake_tools(
        monkeypatch,
        during_gate=lambda root: (root / "untouched.py").write_text("new_user_work = True\n"),
    )
    revision = git(repo, "rev-parse", "HEAD")
    assert changes.main(["--publish"], root=repo) == 1
    assert git(repo, "rev-parse", "HEAD") == revision


def test_format_only_records_changes_without_running_gate(repo, monkeypatch):
    calls = fake_tools(monkeypatch)
    assert changes.main(["--format-only"], root=repo) == 0
    assert report(repo)["files"] == ["a file.py"]
    assert not any("ci/quality_gate.py" in command for command in calls)
    assert report(repo)["commit"] is None


def test_missing_upstream_is_rejected_before_fixing(repo, monkeypatch):
    git(repo, "branch", "--unset-upstream")
    calls = fake_tools(monkeypatch)
    assert changes.main(["--publish"], root=repo) == 1
    assert not any(command[0] == "fake-ruff" for command in calls)
