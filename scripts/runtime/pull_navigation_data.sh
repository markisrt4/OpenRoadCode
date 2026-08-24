#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

DATA_ROOT="${DATA_ROOT:-/srv/openroadcode}"
STAGING_ROOT="${STAGING_ROOT:-/srv/openroadcode-update}"
BACKUP_ROOT="${BACKUP_ROOT:-/srv/openroadcode-previous}"
SOURCE="${NAVIGATION_DATA_SOURCE:-}"
SSH_OPTS="${NAVIGATION_DATA_SSH_OPTS:-}"
DRY_RUN=0
FORCE=0
NO_RESTART=0

usage() {
  cat <<EOF
Usage: $0 --source USER@HOST:/srv/openroadcode [options]

Pull a validated OpenRoadCode map/routing dataset onto this vehicle.

The remote dataset must contain build-manifest.json and valhalla/valhalla.json.
Data are downloaded into a staging directory, validated, and only then promoted
to $DATA_ROOT. The previous deployed dataset is retained at $BACKUP_ROOT.

Options:
  --source SOURCE      rsync/SSH source (or set NAVIGATION_DATA_SOURCE)
  --dry-run            show rsync changes without modifying data
  --force              deploy even when the manifest matches the installed one
  --no-restart         do not restart/start valhalla.service after promotion
  -h, --help           show this help

Environment overrides:
  DATA_ROOT, STAGING_ROOT, BACKUP_ROOT, NAVIGATION_DATA_SOURCE,
  NAVIGATION_DATA_SSH_OPTS
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --source)
      shift; SOURCE="${1:?--source requires a value}" ;;
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --no-restart) NO_RESTART=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ -n "$SOURCE" ]] || { echo "--source is required" >&2; usage >&2; exit 2; }
command -v rsync >/dev/null 2>&1 || { echo "rsync is required" >&2; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo "ssh is required" >&2; exit 1; }

# Normalize the source so rsync copies the contents rather than nesting the
# remote openroadcode directory inside staging.
SOURCE="${SOURCE%/}/"

rsync_ssh=(ssh)
if [[ -n "$SSH_OPTS" ]]; then
  # Deliberately permit shell-style option splitting from the environment.
  # shellcheck disable=SC2206
  extra_ssh_opts=($SSH_OPTS)
  rsync_ssh+=("${extra_ssh_opts[@]}")
fi
printf -v rsync_shell '%q ' "${rsync_ssh[@]}"
rsync_shell="${rsync_shell% }"

remote_manifest="$(mktemp)"
trap 'rm -f "$remote_manifest"' EXIT

remote_host="${SOURCE%%:*}"
remote_path="${SOURCE#*:}"
remote_manifest_path="${remote_path%/}/build-manifest.json"

if [[ "$remote_host" == "$SOURCE" ]]; then
  echo "Source must be an SSH rsync source such as user@host:/srv/openroadcode" >&2
  exit 2
fi

echo "[*] Checking remote navigation-data manifest"
"${rsync_ssh[@]}" "$remote_host" "cat -- '$remote_manifest_path'" > "$remote_manifest"
[[ -s "$remote_manifest" ]] || { echo "Remote build-manifest.json is empty" >&2; exit 1; }

if (( ! FORCE )) && [[ -f "$DATA_ROOT/build-manifest.json" ]] \
    && cmp -s "$remote_manifest" "$DATA_ROOT/build-manifest.json"; then
  echo "[+] Navigation data already match the remote build manifest; nothing to do."
  exit 0
fi

if (( DRY_RUN )); then
  echo "[*] Dry-run pull from $SOURCE"
  rsync -aH --delete --dry-run --itemize-changes \
    -e "$rsync_shell" \
    --exclude='maps/routes/' \
    "$SOURCE" "$STAGING_ROOT/"
  exit 0
fi

echo "[*] Preparing staging directory: $STAGING_ROOT"
sudo rm -rf "$STAGING_ROOT"
sudo mkdir -p "$STAGING_ROOT/maps/routes"
sudo chown "$(id -u):$(id -g)" "$STAGING_ROOT"

# Preserve locally generated route artifacts in staging so promotion cannot
# erase them. They remain vehicle-owned rather than map-builder-owned.
if [[ -d "$DATA_ROOT/maps/routes" ]]; then
  rsync -a "$DATA_ROOT/maps/routes/" "$STAGING_ROOT/maps/routes/"
fi

echo "[*] Pulling navigation data from $SOURCE"
rsync -aH --delete-delay --itemize-changes \
  -e "$rsync_shell" \
  --exclude='maps/routes/' \
  "$SOURCE" "$STAGING_ROOT/"

# Validation deliberately checks the deployment contract rather than trusting
# rsync success alone.
echo "[*] Validating staged dataset"
test -s "$STAGING_ROOT/build-manifest.json"
test -s "$STAGING_ROOT/valhalla/valhalla.json"
cmp -s "$remote_manifest" "$STAGING_ROOT/build-manifest.json" || {
  echo "Staged manifest does not match the manifest checked before transfer" >&2
  exit 1
}

# At least one recognizable map artifact should accompany the routing config.
if ! find "$STAGING_ROOT" -maxdepth 4 -type f \
    \( -name '*.mbtiles' -o -name '*.pmtiles' -o -name '*.tar' -o -name '*.tar.gz' \) \
    -print -quit | grep -q .; then
  echo "No recognizable map/routing artifact found in staged dataset" >&2
  exit 1
fi

echo "[*] Promoting staged dataset"
sudo rm -rf "$BACKUP_ROOT"
if [[ -d "$DATA_ROOT" ]]; then
  sudo mv "$DATA_ROOT" "$BACKUP_ROOT"
fi
sudo mv "$STAGING_ROOT" "$DATA_ROOT"

# Make the deployed tree readable by runtime services while retaining ordinary
# ownership semantics for future administrator-managed updates.
sudo chmod -R a+rX "$DATA_ROOT"

if (( ! NO_RESTART )) && command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files valhalla.service >/dev/null 2>&1; then
    echo "[*] Restarting Valhalla for the new routing dataset"
    sudo systemctl restart valhalla.service
    if ! systemctl is-active --quiet valhalla.service; then
      echo "Valhalla failed after data promotion; rolling back dataset" >&2
      sudo rm -rf "$STAGING_ROOT"
      sudo mv "$DATA_ROOT" "$STAGING_ROOT"
      if [[ -d "$BACKUP_ROOT" ]]; then
        sudo mv "$BACKUP_ROOT" "$DATA_ROOT"
        sudo systemctl restart valhalla.service || true
      fi
      exit 1
    fi
  fi
fi

echo "[+] Navigation data update complete"
echo "    active:   $DATA_ROOT"
echo "    previous: $BACKUP_ROOT"
