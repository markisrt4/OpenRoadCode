#!/usr/bin/env bash
set -euo pipefail

ADDRESS="${ELM327_ADDRESS:-}"
CHANNEL="${ELM327_CHANNEL:-}"
RFCOMM_ID="${ELM327_RFCOMM_ID:-0}"

usage() {
  cat <<'EOF'
Usage: setup_rfcomm0.sh --address MAC [options]

Pair, trust, and bind a Bluetooth Classic Serial Port Profile device.

Options:
  --address MAC       Bluetooth device address (required)
  --channel NUMBER    RFCOMM channel; auto-detected when omitted
  --rfcomm-id NUMBER  RFCOMM device number (default: 0)
  -h, --help          Show this help

Environment alternatives: ELM327_ADDRESS, ELM327_CHANNEL,
ELM327_RFCOMM_ID.
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --address)
      shift
      ADDRESS="${1:-}"
      ;;
    --channel)
      shift
      CHANNEL="${1:-}"
      ;;
    --rfcomm-id)
      shift
      RFCOMM_ID="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[!] Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! "$ADDRESS" =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]]; then
  echo "[!] A valid Bluetooth MAC address is required." >&2
  usage >&2
  exit 1
fi
if [[ ! "$RFCOMM_ID" =~ ^[0-9]+$ ]]; then
  echo "[!] --rfcomm-id must be a non-negative integer." >&2
  exit 1
fi

for command in bluetoothctl sdptool rfcomm; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "[!] Required command is not installed: $command" >&2
    echo "    Install the Bluetooth feature before configuring RFCOMM." >&2
    exit 1
  fi
done

echo "[*] Checking Bluetooth device $ADDRESS..."
device_info="$(bluetoothctl info "$ADDRESS" 2>/dev/null || true)"

if [[ -z "$device_info" ]]; then
  echo "[*] Device is not cached; scanning for up to 15 seconds..."
  bluetoothctl --timeout 15 scan on >/dev/null 2>&1 || true
  device_info="$(bluetoothctl info "$ADDRESS" 2>/dev/null || true)"
fi

if [[ -z "$device_info" ]]; then
  echo "[!] Bluetooth device $ADDRESS was not found." >&2
  echo "    Confirm that it is powered and discoverable, then try again." >&2
  exit 1
fi

if [[ "$device_info" != *"Paired: yes"* ]]; then
  echo "[*] Pairing with $ADDRESS..."
  echo "    Enter the adapter PIN if prompted (commonly 1234 or 0000)."
  if ! bluetoothctl --timeout 30 pair "$ADDRESS"; then
    echo "[!] Automatic pairing failed." >&2
    echo "    Run 'bluetoothctl', then use 'scan on' and 'pair $ADDRESS'." >&2
    exit 1
  fi
else
  echo "[*] Device is already paired."
fi

echo "[*] Trusting $ADDRESS..."
bluetoothctl trust "$ADDRESS" >/dev/null

# A connection held by bluetoothctl can prevent a subsequent Classic RFCOMM
# connection. rfcomm will establish the SPP connection when the tty is opened.
bluetoothctl disconnect "$ADDRESS" >/dev/null 2>&1 || true

if [[ -z "$CHANNEL" ]]; then
  echo "[*] Discovering the Serial Port Profile channel..."
  CHANNEL="$(
    sdptool browse "$ADDRESS" 2>/dev/null \
      | awk '
          /^[[:space:]]*Service Name: Serial Port/ { serial_port = 1; next }
          /"Serial Port" \(0x1101\)/ { serial_port = 1; next }
          serial_port && /^[[:space:]]*Channel:/ { print $2; exit }
        '
  )"
fi

if [[ ! "$CHANNEL" =~ ^[1-9][0-9]*$ ]]; then
  echo "[!] Could not determine an RFCOMM Serial Port channel." >&2
  echo "    Inspect 'sdptool browse $ADDRESS' and rerun with --channel." >&2
  exit 1
fi

device_path="/dev/rfcomm$RFCOMM_ID"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
service_installer="$project_root/scripts/systemd/install_rfcomm_systemd.sh"

echo "[*] Installing the persistent $device_path binding..."
sudo bash "$service_installer" "$ADDRESS" "$CHANNEL" "$RFCOMM_ID"

for _attempt in {1..50}; do
  [[ -e "$device_path" ]] && break
  sleep 0.1
done

if [[ ! -e "$device_path" ]]; then
  echo "[!] RFCOMM service started but $device_path was not created." >&2
  echo "    Check: systemctl status openroadcode-rfcomm${RFCOMM_ID}.service" >&2
  exit 1
fi

echo "[+] ELM327 RFCOMM device configured: $device_path"
ls -l "$device_path"

if ! id -nG | tr ' ' '\n' | grep -qx dialout; then
  echo "[!] The current user is not in the dialout group."
  echo "    Run: sudo usermod -aG dialout \"\$USER\""
  echo "    Then log out and back in before opening $device_path."
fi
