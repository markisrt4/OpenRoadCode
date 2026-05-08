#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-/run/readsb}"
LAT="${LAT:-42.63}"
LON="${LON:--83.03}"

echo "[*] Writing fake aircraft data to: $OUT_DIR"
echo "[*] Center: $LAT, $LON"

sudo mkdir -p "$OUT_DIR"
sudo chown "$USER":"$USER" "$OUT_DIR"

while true; do
  NOW="$(date +%s)"
  STEP=$((NOW % 360))

  LAT1=$(awk -v lat="$LAT" -v step="$STEP" 'BEGIN {print lat + 0.08 * sin(step * 3.14159 / 180)}')
  LON1=$(awk -v lon="$LON" -v step="$STEP" 'BEGIN {print lon + 0.08 * cos(step * 3.14159 / 180)}')

  LAT2=$(awk -v lat="$LAT" -v step="$STEP" 'BEGIN {print lat + 0.12 * cos(step * 3.14159 / 180)}')
  LON2=$(awk -v lon="$LON" -v step="$STEP" 'BEGIN {print lon + 0.12 * sin(step * 3.14159 / 180)}')

  cat > "$OUT_DIR/aircraft.json" <<EOF
{
  "now": ${NOW}.0,
  "messages": 42,
  "aircraft": [
    {
      "hex": "a1b2c3",
      "type": "adsb_icao",
      "category": "A3",
      "rssi": -18.5,
      "flight": "TEST101 ",
      "lat": ${LAT1},
      "lon": ${LON1},
      "alt_baro": 12000,
      "gs": 310,
      "track": ${STEP},
      "seen": 0.1,
      "seen_pos": 0.1,
      "messages": 100
    },
    {
      "hex": "d4e5f6",
      "flight": "TEST202 ",
      "type": "adsb_icao",
      "category": "A3",
      "rssi": -18.5,
      "lat": ${LAT2},
      "lon": ${LON2},
      "alt_baro": 28000,
      "gs": 455,
      "track": $(((STEP + 90) % 360)),
      "seen": 0.2,
      "seen_pos": 0.2,
      "messages": 200
    }
  ]
}
EOF

  cat > "$OUT_DIR/receiver.json" <<EOF
{
  "lat": ${LAT},
  "lon": ${LON},
  "version": "fake-carsdr-test"
}
EOF

  sleep 1
done