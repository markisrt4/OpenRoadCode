#!/usr/bin/env bash
set -euo pipefail

echo "[*] Writing RTL-SDR blacklist..."
sudo tee /etc/modprobe.d/blacklist-rtl-sdr.conf >/dev/null <<'EOF'
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist rtl2830
blacklist rtl2838
EOF

echo "[*] Unloading DVB drivers if loaded..."
for mod in dvb_usb_rtl28xxu rtl2832 rtl2830 rtl2838; do
  if lsmod | awk '{print $1}' | grep -qx "$mod"; then
    echo "    unloading $mod"
    sudo modprobe -r "$mod" || true
  fi
done

echo "[*] Reloading udev rules..."
sudo udevadm control --reload-rules || true

echo
echo "[*] Current RTL/DVB modules:"
lsmod | grep -E 'rtl|dvb' || true

echo
echo "[+] Done."
echo "Unplug/replug the RTL-SDR, then run:"
echo "    rtl_test -t"