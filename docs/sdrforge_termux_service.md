# SDRForge in Termux: supervised simulation and authorized USB

OpenRoadCode integrates libSDRForge through REST on `127.0.0.1:5570`,
ZMQ spectrum/receiver telemetry on `127.0.0.1:5571`, and rigctl on
`127.0.0.1:4532`. Install libSDRForge under
`$HOME/src/libSDRForge`.

## One-time regional radio configuration

Configure SDRForge's persistent regional profile overlay from the ORC checkout:

```bash
cd ~/src/OpenRoadCode
git switch feature/sdrforge-native-spectrum
git pull --ff-only
bash scripts/configure_sdrforge_region.sh romeo
```

This writes `~/.config/sdrforge/radio-region.conf` with an absolute path to
ORC's `config/radio` directory and the selected locale. SDRForge's
region-aware Linux systemd installer, standalone Termux runit installer,
and Android-authorized USB launchers load this file at process startup.
The configuration is optional, and SDRForge still works independently of
ORC. Existing user presets are not modified. Restart the server after
changing the region. Command-line and explicit environment overrides take
precedence over the saved file.

**Important:** ORC's existing managed Termux service definition is not
installed by `scripts/runit/install_termux_services.sh` in this branch.
If a separate ORC-managed SDRForge runit definition is already installed,
it must invoke SDRForge's `scripts/run_radio_region_server.sh` wrapper to
load the saved configuration; the standalone SDRForge installer deliberately
does not overwrite that definition.

## Install and inspect the managed service

```bash
cd ~/src/OpenRoadCode
git switch feature/sdrforge-native-spectrum
git pull --ff-only
bash scripts/runit/install_termux_services.sh
sv status openroadcode-sdrforge
```

The SDRForge runit service is optional. The service manager supports
`simulated` and `local` profiles, but **direct runit startup with
RTL-SDR USB is deliberately blocked**: Android must first authorize
the USB device and hand off its file descriptor. The service manager
can switch to simulated IQ and stop a supervised instance before a
USB handoff. Do not use the old managed-Termux branch's instruction
to select `local` and launch the runit service directly.

## Simulated IQ

Use the service manager to select simulated IQ and start the
`openroadcode-sdrforge` service. Or, if no managed instance is
running, launch a standalone simulated server from libSDRForge:

```bash
cd ~/src/libSDRForge
git switch feature/openroadcode-native-integration
git pull --ff-only
PYTHONPATH=src python examples/live_transport_server.py --simulate --warmup 0
```

## RTL-SDR hardware

Stop any supervised SDRForge server first:

```bash
sv down openroadcode-sdrforge
cd ~/src/libSDRForge
git switch feature/openroadcode-native-integration
git pull --ff-only
termux-usb -l
bash scripts/run_rtlsdr_termux.sh examples/live_transport_server.py \
  --frequency 104.3 --mode WFM --gain 29.7 --warmup 2
```

Approve Android's USB permission request. The launcher re-enumerates
the device and uses `termux-usb -E` to run SDRForge with the authorized
USB descriptor. The standalone hardware server must own the REST,
ZMQ, and rigctl ports; do not run a competing simulated server.

In another Termux session, request acquisition:

```bash
curl -sS -X POST http://127.0.0.1:5570/v1/receiver/start
```

Stop acquisition with POST `/v1/receiver/stop`. Stop the standalone
server with Ctrl+C. There is no automatic USB reconnection guarantee.

## Safety and troubleshooting

Do not pipe live USB-sensitive commands through clipboard or `tee`
process substitution: it can hang the USB handoff. Collect logs
after the command finishes. If REST reports an existing server,
check `sv status openroadcode-sdrforge` and stop the supervised
instance rather than competing for ports.
