#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This setup script must run inside Termux." >&2
  exit 2
}

HOST_SRC="${HOST_SRC:-$HOME/src}"
TAR1090_SRC="${TAR1090_SRC:-$HOST_SRC/tar1090}"
TAR1090_REF="${TAR1090_REF:-master}"
TAR1090_PORT="${TAR1090_PORT:-8081}"
DATA_DIR="$TAR1090_SRC/html/data"

mkdir -p "$HOST_SRC"

if [[ ! -d "$TAR1090_SRC/.git" ]]; then
  echo "[*] Cloning tar1090"
  git clone https://github.com/wiedehopf/tar1090.git "$TAR1090_SRC"
fi

echo "[*] Updating tar1090"
git -C "$TAR1090_SRC" fetch --tags --prune origin
git -C "$TAR1090_SRC" checkout "$TAR1090_REF"
git -C "$TAR1090_SRC" pull --ff-only origin "$TAR1090_REF" || true

[[ -f "$TAR1090_SRC/html/index.html" ]] || {
  echo "tar1090 html/index.html was not found at $TAR1090_SRC/html" >&2
  exit 1
}

mkdir -p "$DATA_DIR"

if [[ ! -f "$DATA_DIR/receiver.json" ]]; then
  cat > "$DATA_DIR/receiver.json" <<'EOF'
{
  "version": "OpenRoadCode-test",
  "refresh": 1000,
  "lat": 42.8028,
  "lon": -83.0127
}
EOF
fi

if [[ ! -f "$DATA_DIR/aircraft.json" ]]; then
  NOW="$(date +%s)"
  cat > "$DATA_DIR/aircraft.json" <<EOF
{
  "now": $NOW,
  "messages": 12345,
  "aircraft": [
    {
      "hex": "a1b2c3",
      "flight": "ORC101  ",
      "lat": 42.86,
      "lon": -82.98,
      "alt_baro": 12500,
      "gs": 245.0,
      "track": 215.0,
      "seen": 0.5,
      "seen_pos": 0.5,
      "messages": 500
    },
    {
      "hex": "d4e5f6",
      "flight": "ORC202  ",
      "lat": 42.72,
      "lon": -83.08,
      "alt_baro": 5400,
      "gs": 160.0,
      "track": 35.0,
      "seen": 0.2,
      "seen_pos": 0.2,
      "messages": 210
    }
  ]
}
EOF
fi

cat <<EOF

[+] tar1090 Termux setup complete
    source: $TAR1090_SRC
    data:   $DATA_DIR
    URL:    http://127.0.0.1:$TAR1090_PORT/

Start the local presentation server with:
    cd "$TAR1090_SRC/html"
    python -m http.server "$TAR1090_PORT" --bind 127.0.0.1

The seeded JSON files are only for presentation testing. A future readsb
integration can replace aircraft.json and receiver.json in the same data directory.
EOF
