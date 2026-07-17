#  Mark's Bespoke Car Controller (Drive UbiquitOS)

> A Raspberry Pi powered automotive software-defined radio, vehicle information center, and embedded experimentation platform.

## Philosophy

Modern vehicles contain dozens of computers, yet very few are open to customization.

Drive UbiquitOS embraces the opposite philosophy.

The project is designed to be:

- Open
- Modular
- Hardware agnostic
- Extensible
- Educational
- Developer friendly

Rather than replacing factory vehicle systems, Drive UbiquitOS complements them by providing a platform for experimentation, visualization, software-defined radio, and custom applications.
CarSDR is a custom in-vehicle infotainment and software-defined radio platform designed around a Raspberry Pi 4, RTL-SDR, GPS receiver, rotary encoder controls, and a touchscreen display.

The project combines multiple technologies into a single dashboard capable of monitoring radio communications, displaying vehicle information, controlling vehicle lighting, interacting with Bluetooth devices, and serving as a flexible embedded Linux development platform.

Unlike commercial infotainment systems, CarSDR is intended to be completely hackable, modular, and open for experimentation.

---

# Features

Current capabilities include:

* FM Broadcast Radio
* Airband Receiver (AM)
* NOAA Weather Radio
* Multi-band Scanner
* ADS-B Aircraft Tracking
* GPS Positioning
* Bluetooth OBD-II Integration
* Bluetooth Cabin Lighting Control
* Spotify Integration
* Touchscreen User Interface
* Rotary Encoder Hardware Controls
* Remote VNC Display
* Modular Python application framework

Future ideas include:

* APRS
* Digital radio modes
* CAN bus monitoring
* Vehicle gauges
* Offline navigation
* Dashcam integration
* Backup camera
* Reverse engineering proprietary vehicle CAN messages

---

# System Overview

This custom vehicle system is built around a Raspberry Pi 4 installed inside a custom 3D printed enclosure mounted in the dashboard.

The Raspberry Pi interfaces with:

* RTL-SDR receiver
* USB GPS receiver
* Raspberry Pi Touch Display 2
* Rotary encoders
* Bluetooth OBD-II adapter
* Bluetooth LED controller
* External travel router
* Remote tablet running VNC

The current hardware architecture is illustrated in the included 1-Wire system diagram. :contentReference[oaicite:0]{index=0}

---

# Hardware

## Core Components

| Component | Purpose |
|------------|---------|
| Raspberry Pi 4 | Main computer |
| Raspberry Pi Touch Display 2 (7") | Primary user interface |
| RTL-SDR | Software defined radio receiver |
| USB GPS Receiver | GPS location |
| Wideband antenna | RF reception |
| GPS antenna | Positioning |
| Bluetooth OBD-II Adapter | Vehicle telemetry |
| Bluetooth LED Controller | Cabin lighting |
| Rotary Encoders | Physical controls |
| USB Keyboard | Development/debugging |
| Ethernet Travel Router | Local network |
| Samsung Tablet | Remote VNC display |
| Custom 3D Printed Enclosure | Dashboard installation |

---

# Software Architecture

The software is primarily written in Python and organized into independent applications and reusable modules.

Major components include:

```
apps/
    carUi/
    adsb/
    weather/
    scanner/

modules/
    gps/
    media/
    obd/
    lighting/
    radio/
    ui/
```

The goal is to keep hardware-specific code isolated behind reusable interfaces while allowing new applications to share common services.

---

# Radio Features

Supported radio modes currently include:

* Wide FM
* Narrow FM
* AM

Current applications:

* FM Broadcast
* Airband
* NOAA Weather
* Scanner

Future radio applications may include:

* ADS-B
* APRS
* AIS
* P25 monitoring
* DMR monitoring
* HF (with additional hardware)

---

# Vehicle Features

Current integrations:

* Bluetooth OBD-II
* GPS
* Cabin LED control

Planned integrations:

* CAN bus monitoring
* Vehicle gauges
* Engine telemetry
* TPMS
* Steering wheel controls
* HVAC status

---

# Networking

The networked components are designed to operate independently of Internet connectivity.

Networking options include:

* Ethernet
* Wi-Fi
* Mobile hotspot
* Bluetooth
* Local VNC access

A travel router provides an isolated in-vehicle network for remote displays and development.

---

# User Interface

The UI is designed specifically for automotive use.

Current design goals include:

* Large touch targets
* Rotary encoder navigation
* Minimal driver distraction
* Consistent panel layout
* Dark theme
* Responsive scaling

---

# Host Setup

A host setup script is provided to install the required Linux packages, create a Python virtual environment, configure VNC, and install all software dependencies.

The setup script currently installs support for:

* Python
* Tkinter
* BlueZ
* GPSD
* RTL-SDR
* SDR++
* Chromium
* VNC Server
* Openbox
* XFCE
* Streamlit
* Bleak
* GPS Python libraries
* Serial communication libraries

See:

```
host_setup.sh
```

The script also:

* Creates the Python virtual environment
* Installs Python dependencies
* Configures TigerVNC
* Creates a systemd user service
* Enables automatic startup

These dependencies and setup steps are implemented in the included `host_setup.sh` script. :contentReference[oaicite:1]{index=1}

---

# Running

Create the Python environment:

```bash
./host_setup.sh
```

Activate:

```bash
source venv/bin/activate
```

Run the UI:

```bash
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
python3 -m apps.carUi.main
```

For per-application X11 forwarding, connect to the host with `ssh -X` or
`ssh -Y`. SSH assigns and exports `DISPLAY`; CarUI preserves that value. The
VNC display configured by `remote_display` is separate and is not used for the
CarUI window. From a workstation with an X server, launch it with:

```bash
ssh -X username@your-openroad-host
echo "$DISPLAY"
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

Use `ssh -Y` instead if your workstation and security policy require trusted
X11 forwarding. `CARUI_DISPLAY` remains available as an explicit advanced
override, but it is not populated from the VNC configuration.

---

# Project Goals

This project serves several purposes:

* Build a customizable in-vehicle SDR platform
* Explore embedded Linux development
* Experiment with automotive integration
* Develop reusable hardware abstraction layers
* Learn reverse engineering techniques for vehicle networks
* Provide a platform for future experimentation

---

# Safety Notice

This is an experimental project intended for hobbyist and educational purposes.

Never operate or interact with the system in a way that distracts from safe vehicle operation. Any features intended for driver interaction should be used only when it is safe to do so.

Vehicle integrations should be performed carefully and at the user's own risk.

---

# License

Copyright (c) 2026

This project is released under the MIT License.
