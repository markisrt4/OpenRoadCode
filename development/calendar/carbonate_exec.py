#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Start Carbonate using ORC's existing secret manager."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from security.environment_variable_secret_manager import EnvironmentVariableSecretManager  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: carbonate_exec.py CARBONATE_EXECUTABLE", file=sys.stderr)
        return 2
    try:
        password = EnvironmentVariableSecretManager().require_secret("CARBONATE_BRIDGE_PASSWORD")
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Carbonate startup: {error}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["CARBONATE_BRIDGE_PASSWORD"] = password
    os.execve(sys.argv[1], [sys.argv[1], "serve"], env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
