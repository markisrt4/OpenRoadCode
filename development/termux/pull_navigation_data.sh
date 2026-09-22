#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail

REMOTE="${NAV_DATA_REMOTE:-}"
REMOTE_ROOT="${NAV_DATA_REMOTE_ROOT:-/srv/openroadcode}"
DATA_ROOT="${NAV_DATA_ROOT:-$HOME/.local/share/openroadcode}"
STAGING="${DATA_ROOT}.staging"
BACKUP="${DATA_ROOT}.previous"
FORCE=0

usage() {
  cat <<EOF
Usage: $0 [--force] user@map-host

Pull a validated OpenRoadCode navigation dataset into Termux.

Options:
  --force     allow an intentional downgrade or reinstall
  -h, --help  show this help

Environment:
  NAV_DATA_REMOTE, NAV_DATA_REMOTE_ROOT, NAV_DATA_ROOT
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    -*)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      [[ -z "$REMOTE" ]] || { echo "Only one remote host may be specified" >&2; exit 2; }
      REMOTE="$1"
      ;;
  esac
  shift
done

[[ -n "$REMOTE" ]] || { usage >&2; exit 2; }
command -v rsync >/dev/null || { echo "rsync is required (pkg install rsync)" >&2; exit 2; }
command -v ssh >/dev/null || { echo "ssh is required (pkg install openssh)" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 2; }

remote_manifest="$(mktemp)"
trap 'rm -f "$remote_manifest"' EXIT

echo "[*] Checking remote navigation-data manifest"
ssh "$REMOTE" "cat -- '$REMOTE_ROOT/build-manifest.json'" > "$remote_manifest"
[[ -s "$remote_manifest" ]] || { echo "Remote build-manifest.json is empty" >&2; exit 1; }

relation="$(
python3 - "$remote_manifest" "$DATA_ROOT/build-manifest.json" <<'PY'
import datetime as dt
import json
import pathlib
import sys

remote_path = pathlib.Path(sys.argv[1])
local_path = pathlib.Path(sys.argv[2])

def load_generated(path, label):
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("generated_unix")
    if not isinstance(value, int):
        raise SystemExit(f"{label} manifest has no integer generated_unix: {path}")
    return value

def stamp(value):
    if value is None:
        return "not installed"
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

remote = load_generated(remote_path, "Remote")
local = load_generated(local_path, "Local")
print(f"    remote: {stamp(remote)}", file=sys.stderr)
print(f"    local:  {stamp(local)}", file=sys.stderr)
if local is None or remote > local:
    print("newer")
elif remote < local:
    print("older")
else:
    print("same-time")
PY
)"

if [[ "$relation" == "older" && "$FORCE" -ne 1 ]]; then
  echo "Remote navigation dataset is older than the installed dataset; refusing to downgrade." >&2
  echo "Use --force only when an intentional downgrade is required." >&2
  exit 1
elif [[ "$relation" == "older" ]]; then
  echo "[!] Remote dataset is older; --force permits this intentional downgrade."
fi

if (( ! FORCE )) && [[ -f "$DATA_ROOT/build-manifest.json" ]] \
    && cmp -s "$remote_manifest" "$DATA_ROOT/build-manifest.json" \
    && [[ -s "$DATA_ROOT/maps/search/openroadcode-search.sqlite" ]]; then
  echo "[+] Navigation data already match the remote build manifest; nothing to transfer."
  exit 0
fi

rm -rf "$STAGING"
mkdir -p "$STAGING/maps/routes"

if [[ -d "$DATA_ROOT/maps/routes" ]]; then
  rsync --archive "$DATA_ROOT/maps/routes/" "$STAGING/maps/routes/"
fi

echo "[*] Pulling navigation data from $REMOTE:$REMOTE_ROOT/"
rsync --archive --delete-delay --partial --human-readable --info=progress2 \
  --exclude=maps/routes/ \
  "$REMOTE:$REMOTE_ROOT/" "$STAGING/"

[[ -s "$STAGING/build-manifest.json" ]] || {
  echo "Pulled data is missing build-manifest.json; refusing to activate it." >&2
  exit 1
}
[[ -s "$STAGING/maps/search/openroadcode-search.sqlite" ]] || {
  echo "Pulled data is missing maps/search/openroadcode-search.sqlite; refusing to activate it." >&2
  exit 1
}
cmp -s "$remote_manifest" "$STAGING/build-manifest.json" || {
  echo "Staged manifest changed during transfer; refusing to activate it." >&2
  exit 1
}

rm -rf "$BACKUP"
if [[ -d "$DATA_ROOT" ]]; then mv "$DATA_ROOT" "$BACKUP"; fi
mv "$STAGING" "$DATA_ROOT"
echo "[+] Navigation data activated at $DATA_ROOT"
echo "    Previous dataset: $BACKUP"
