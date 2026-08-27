# Termux Development Target

This directory provides the OpenRoadCode build/run pipeline for native Termux
with Termux:X11. It is a development and emulation target rather than the
intended in-vehicle Linux deployment, but it now exercises substantial pieces
of the production architecture directly on Android hardware.

Termux-specific installation and launch helpers live here. Production service
supervision is documented under `scripts/runit/`, and the Termux runtime
composition is defined by `config/runtime.termux.toml`.

## Prerequisites

- Termux
- Termux:X11
- XFCE4
- an X display, normally `:1`
- the OpenRoadCode Android sensor bridge for Android-backed sensor input

Start the graphical session with:

```bash
termux-x11 :1 -xstartup "xfce4-session"
```

## Bootstrap

From the OpenRoadCode repository root:

```bash
chmod +x scripts/termux/*.sh
./scripts/termux/install.sh
```

The installer creates a separate `venv-termux` virtual environment rather than
reusing the Debian/Raspberry Pi installation pipeline.

## Environment check

```bash
./scripts/termux/check_termux.sh
```

## Tk smoke test

With the X server running:

```bash
export DISPLAY=:1
./scripts/termux/run.sh scripts/termux/tk_smoke_test.py
```

## Run OpenRoadCode

The default helper launches CarUi:

```bash
export DISPLAY=:1
./scripts/termux/run.sh
```

A Python module or script may also be supplied explicitly:

```bash
./scripts/termux/run.sh -m some.module
./scripts/termux/run.sh path/to/script.py
```

For the normal Termux navigation runtime, run the ZeroMQ broker and navigation
service through the runit definitions under `scripts/runit/` rather than
starting duplicate long-lived service processes manually.

The current Termux navigation composition uses Android-backed IMU data through
the localhost sensor bridge and simulated geographic position. Android location
and ground-motion bridge support are follow-on work and should remain separate
from the Termux target merge.

## Related documentation

- `development/termux/README.md` describes the native navigation stack, Android
  sensor bridge testing, navigation data, and end-to-end Termux workflow.
- `scripts/runit/README.md` describes installation and control of the Termux
  broker and navigation services.
- `config/runtime.termux.toml` defines the current Termux runtime composition.
