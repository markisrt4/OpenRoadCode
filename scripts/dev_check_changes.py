#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply recorded Ruff edits and optionally publish them after successful checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

if __package__:
    from scripts import quality_gate
else:
    import quality_gate

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], root: Path, *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=root, capture_output=capture, check=False)


def git(root: Path, *arguments: str) -> str:
    result = run(["git", *arguments], root, capture=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    output = os.fsdecode(result.stdout)
    return output if "-z" in arguments else output.strip()


def snapshot(root: Path) -> dict[str, str]:
    result = run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], root, capture=True,
    )
    if result.returncode:
        raise RuntimeError("Could not enumerate repository files")
    files = {}
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        name = os.fsdecode(entry)
        path = root / name
        if path.suffix in {".py", ".pyi", ".ipynb"} and path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def save_report(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def publish(root: Path, report: dict, after: dict[str, str], message: str) -> None:
    if git(root, "symbolic-ref", "--quiet", "--short", "HEAD") != report["branch"]:
        raise RuntimeError("Branch changed during checks; changes were not committed")
    if git(root, "rev-parse", "HEAD") != report["revision"]:
        raise RuntimeError("HEAD changed during checks; changes were not committed")
    files = report["files"]
    expected = set(files)
    actual = set(git(root, "diff", "--name-only", "-z", "HEAD").split("\0")) - {""}
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if actual != expected or untracked or git(root, "diff", "--cached", "--name-only"):
        raise RuntimeError("Other work appeared during checks; changes were not committed")
    if snapshot(root) != after:
        raise RuntimeError("Files changed after Ruff ran; changes were not committed")
    git(root, "add", "--", *files)
    git(root, "commit", "-m", message)
    report["commit"] = git(root, "rev-parse", "HEAD")
    print(f"[*] Committed Ruff changes: {report['commit']}", flush=True)


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks-only", action="store_true")
    parser.add_argument("--format-only", action="store_true")
    parser.add_argument("--fix", action="store_true", help="Apply safe Ruff fixes and formatting")
    parser.add_argument(
        "--publish", action="store_true", help="Fix, check, commit, and push Ruff edits",
    )
    parser.add_argument("--message", default="Apply automated Ruff fixes")
    parser.add_argument("paths", nargs="*", default=[])
    args = parser.parse_args(argv)
    if args.publish and args.format_only:
        parser.error("--publish requires validation; use --all or --full")
    gate = [sys.executable, "scripts/quality_gate.py"]
    if args.checks_only:
        gate.append("--checks-only")
    if not (args.fix or args.publish or args.format_only):
        return run(gate, root).returncode
    report = {"files": [], "status": "started", "commit": None, "pushed": False}
    report_path = None
    try:
        report["revision"] = git(root, "rev-parse", "HEAD")
        report["branch"] = git(root, "branch", "--show-current")
        if args.publish:
            if not report["branch"]:
                raise RuntimeError("Automatic publishing requires a named branch")
            if git(root, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError("Commit or stash existing changes before using --publish")
            try:
                report["remote"] = git(root, "config", "--get", f"branch.{report['branch']}.remote")
                report["target"] = git(root, "config", "--get", f"branch.{report['branch']}.merge")
            except RuntimeError as error:
                raise RuntimeError("Configure a branch upstream before using --publish") from error
            if report["remote"] == "." or not report["target"].startswith("refs/heads/"):
                raise RuntimeError("Automatic publishing requires a remote branch upstream")
        report_path = Path(git(root, "rev-parse", "--git-path", "dev-check-last-run.json"))
        if not report_path.is_absolute():
            report_path = root / report_path
        save_report(report_path, report)
        before = snapshot(root)
        ruff = quality_gate.ruff_executable()
        if ruff is None:
            raise RuntimeError("Ruff is missing; run bash scripts/setup_quality_env.sh")
        paths = args.paths or ["."]
        lint = run([ruff, "check", "--fix", "--", *paths], root).returncode
        formatting = run([ruff, "format", "--", *paths], root).returncode
        after = snapshot(root)
        report["files"] = sorted(
            name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
        )
        report["status"] = "fixed" if not (lint or formatting) else "fix_failed"
        save_report(report_path, report)
        print(f"[*] Ruff changed {len(report['files'])} file(s):", flush=True)
        for name in report["files"]:
            print(f"    {name}", flush=True)
        print(f"[*] Change record: {report_path}", flush=True)
        if lint or formatting:
            return 1
        if args.format_only:
            return 0
        result = run(gate, root).returncode
        report["status"] = "checked" if result == 0 else "checks_failed"
        save_report(report_path, report)
        if result:
            return result
        if args.publish and report["files"]:
            publish(root, report, after, args.message)
            report["status"] = "committed"
            save_report(report_path, report)
            result = run(
                ["git", "push", report["remote"], f"HEAD:{report['target']}"], root
            ).returncode
            report["pushed"] = result == 0
            report["status"] = "pushed" if result == 0 else "push_failed"
            save_report(report_path, report)
            return result
        if args.publish:
            print("[*] No Ruff changes; no commit or push needed.", flush=True)
        return 0
    except (OSError, RuntimeError) as error:
        report["status"] = "failed"
        report["error"] = str(error)
        if report_path is not None:
            save_report(report_path, report)
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
