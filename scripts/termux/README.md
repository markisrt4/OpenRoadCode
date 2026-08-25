# Termux Development Target

This directory provides the initial OpenRoadCode build/run pipeline for native
Termux with an X11 server. It is a development and emulation target, not an
in-vehicle deployment target.

The Termux pipeline intentionally does not select or modify OpenRoadCode TOML
configuration. Runtime configuration remains independent from this target.

## Prerequisites

- Termux
- Termux:X11
- XFCE4
- An X display, normally `:1`

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

The default command attempts to launch the car UI:

```bash
export DISPLAY=:1
./scripts/termux/run.sh
```

A Python module or script may also be supplied explicitly:

```bash
./scripts/termux/run.sh -m some.module
./scripts/termux/run.sh path/to/script.py
```

The first milestone is intentionally limited to proving that OpenRoadCode can
be installed, imported, and launched under Termux/X11. Hardware support and
platform-specific runtime configuration can be added separately as those
interfaces mature.
