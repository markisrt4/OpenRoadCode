#!/usr/bin/env bash
set -euo pipefail

USERNAME="${SUDO_USER:-$USER}"

SYSTEMCTL_PATH="$(which systemctl)"

if [[ -z "${SYSTEMCTL_PATH}" ]]; then
    echo "[ERROR] systemctl not found"
    exit 1
fi

SUDOERS_FILE="/etc/sudoers.d/carsdr-readsb"

echo "[INFO] Creating sudoers rule for user: ${USERNAME}"
echo "[INFO] systemctl path: ${SYSTEMCTL_PATH}"

TMP_FILE="$(mktemp)"

cat > "${TMP_FILE}" <<EOF
${USERNAME} ALL=(root) NOPASSWD: \
${SYSTEMCTL_PATH} start readsb, \
${SYSTEMCTL_PATH} stop readsb, \
${SYSTEMCTL_PATH} restart readsb
EOF

echo "[INFO] Validating sudoers syntax..."

sudo visudo -cf "${TMP_FILE}"

echo "[INFO] Installing sudoers file..."

sudo cp "${TMP_FILE}" "${SUDOERS_FILE}"
sudo chmod 440 "${SUDOERS_FILE}"

rm -f "${TMP_FILE}"

echo "[INFO] Done."
echo
echo "You can now run:"
echo "  sudo systemctl start readsb"
echo "  sudo systemctl stop readsb"
echo "without password prompts."