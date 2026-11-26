#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
release=latest
options=()

while (( $# )); do
  case "$1" in
    --version)
      if (( $# < 2 )); then
        echo "--version requires a release tag" >&2
        exit 2
      fi
      release="$2"
      shift 2
      ;;
    --update|--yes)
      options+=("$1")
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--update] [--yes] [--version metro-detroit-imagery-VERSION]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--update] [--yes] [--version metro-detroit-imagery-VERSION]" >&2
      exit 2
      ;;
  esac
done

cd "$PROJECT_ROOT"
exec "${OPENROADCODE_PYTHON:-python}" -m development.maps.install_region \
  --coverage metro-detroit --github-release "$release" "${options[@]}"
