# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Resolve the development checkout label once, outside frontend widgets."""
from pathlib import Path
import subprocess


def application_name(repository: Path | None = None) -> str:
    repository = repository or Path(__file__).resolve().parents[3]
    base = 'OpenRoadCode'
    if not (repository / '.git').exists():
        return base
    try:
        result = subprocess.run(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'],
            cwd=repository, capture_output=True, text=True, timeout=1, check=False)
    except (OSError, subprocess.SubprocessError):
        return base
    branch = result.stdout.strip() if result.returncode == 0 else ''
    return f'{base} [{branch}]' if branch and branch != 'master' else base
