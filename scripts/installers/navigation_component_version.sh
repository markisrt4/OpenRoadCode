#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# Hash tracked build inputs, not generated build directories, checkout paths,
# map data, style files, or unrelated application commits.
# Dependency revisions must be immutable commit IDs.
if (( $# != 3 )); then
  echo "Usage: $0 MAPLIBRE_COMMIT VALHALLA_COMMIT PRIME_SERVER_COMMIT" >&2
  exit 2
fi
for revision in "$@"; do
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || {
    echo "Expected a pinned dependency commit: $revision" >&2
    exit 2
  }
done

{
  printf 'navigation-package-schema=1\nmaplibre=%s\nvalhalla=%s\nprime_server=%s\n' "$@"
  git ls-files -z -- apps/map_renderer development/containers/maplibre development/containers/valhalla scripts/installers/navigation_component_version.sh |
    LC_ALL=C sort -z |
    xargs -0 -r sha256sum
} | sha256sum | awk '{print $1}'
