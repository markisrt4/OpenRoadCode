# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse

from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that a secrets.env or process-environment secret "
            "is available."
        )
    )
    parser.add_argument(
        "name",
        help="Environment variable name to verify.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manager = EnvironmentVariableSecretManager()
    value = manager.get_secret(args.name)

    if value is None:
        print(f"Secret is not available: {args.name}")
        return 1

    # Never print the secret itself. Humans have invented terminal history.
    print(f"Secret is available: {args.name}")
    print(f"Length: {len(value)} characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
