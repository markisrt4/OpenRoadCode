#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MAP_BUILDER_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$MAP_BUILDER_ROOT/../.." && pwd)"

OUTPUT_ROOT="${OPENROAD_OUTPUT_ROOT:-$MAP_BUILDER_ROOT/build-output}"
SOURCE_DIR="$OUTPUT_ROOT/maps/source"
SEARCH_DB="$OUTPUT_ROOT/maps/search/openroadcode-search.sqlite"

mapfile -t SOURCE_PBFS < <(
  find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.osm.pbf' -print | sort
)

if (( ${#SOURCE_PBFS[@]} == 0 )); then
  echo "No source PBF files found in: $SOURCE_DIR" >&2
  echo "Run the map builder first to populate maps/source." >&2
  exit 2
fi

SEARCH_DIR="$(dirname -- "$SEARCH_DB")"
mkdir -p "$SEARCH_DIR"

if [[ ! -w "$SEARCH_DIR" ]]; then
  echo "Search-index output directory is not writable: $SEARCH_DIR" >&2
  echo "Fix its ownership rather than running this build with sudo." >&2
  exit 2
fi

echo "[*] Rebuilding OpenRoadCode search index"
echo "    source directory: $SOURCE_DIR"
echo "    source PBFs:      ${#SOURCE_PBFS[@]}"
echo "    destination:      $SEARCH_DB"

PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$SEARCH_DB" "${SOURCE_PBFS[@]}" <<'PY'
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from tools.map_builder.builder.poi_index import build_search_index
from tools.map_builder.builder.validate import validate_search_index


destination = Path(sys.argv[1])
sources = [Path(value) for value in sys.argv[2:]]

for source in sources:
    if not source.is_file():
        raise SystemExit(f"Missing source PBF: {source}")

with tempfile.TemporaryDirectory(prefix="openroadcode-search-") as directory:
    temporary_root = Path(directory)

    if len(sources) == 1:
        build_input = sources[0]
    else:
        build_input = temporary_root / "merged.osm.pbf"
        command = [
            "osmium",
            "merge",
            *map(str, sources),
            "-o",
            str(build_input),
            "--overwrite",
        ]
        print("+", " ".join(command), flush=True)
        subprocess.run(command, check=True)

    temporary_database = temporary_root / "openroadcode-search.sqlite"

    counts = build_search_index(build_input, temporary_database)
    validation = validate_search_index(temporary_database)

    destination.parent.mkdir(parents=True, exist_ok=True)

    # The temporary build directory may be on a different filesystem
    # (for example /tmp), so os.replace() cannot move directly from it
    # to build-output. Copy into the destination filesystem first, then
    # atomically replace the live database.
    staged_database = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(temporary_database, staged_database)
    staged_database.replace(destination)

print(f"Built search index: {counts}")
print(f"Tables: {', '.join(validation['tables'])}")
print(f"POI columns: {', '.join(validation['poi_columns'])}")
print(f"Installed: {destination}")
PY

echo "[+] Search index rebuild complete"
