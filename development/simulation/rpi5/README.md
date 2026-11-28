# Raspberry Pi 5 userspace simulation

Run as an unprivileged user on a Linux host with rootless Podman and ARM64 binfmt/QEMU support. On Debian 13 x86 hosts the relevant packages are qemu-user, qemu-user-binfmt and passt.

From the repository root:

```sh
bash development/simulation/rpi5/build.sh
bash development/simulation/rpi5/run.sh
```

The image uses ARM64 Debian trixie. The read-only checkout and synthetic Raspberry Pi OS/model fixtures exercise installer plan resolution without installing host services. Xvfb checks Tk availability at both supported screen sizes. The runtime has no network, published ports or hardware devices, and is limited to 768 MiB and one CPU. The build needs network access for Debian packages.

This is a smoke harness, not a full application installation or hardware emulator. Actual ORC Python dependencies, application tests, systemd orchestration, Waydroid, GPU and RF hardware remain separate validation tasks. Run only trusted repository code. The base image tag and Debian package versions are mutable.

## Application smoke tests and interactive VNC

Build the application image after building the base image:

```sh
bash development/simulation/rpi5/build-application.sh
bash development/simulation/rpi5/run-application.sh 1280x720
bash development/simulation/rpi5/run-application.sh 800x480
```

The application smoke test uses the lightweight simulation profile and checks
startup, a visible dashboard window, and matching display geometry.

Build the optional VNC image with `bash development/simulation/rpi5/build-vnc.sh`.
Copy the `orc-vnc` launcher to the client PATH. It requires SSH access to the
host (default alias `vps`, override with `ORC_VNC_HOST`), socat and TigerVNC.
On Termux the default X11 display is :1.

```sh
orc-vnc start 1280x720 --simulation
orc-vnc start 800x480 --simulation --opengl
orc-vnc stop
```

Explicit feature arguments restart an existing simulation. With no feature
arguments, a running simulation at the requested resolution is reused.
The VNC relay uses SSH and loopback sockets, not a public VNC port.

## Runtime feature switches

The application accepts positive and negative switches for camera, audio,
native-map, spotify, opengl and adsb (for example, `--no-camera` or `--camera`).
The `--simulation` profile disables all six by default. Explicit switches
override the profile, which overrides existing ORC_NO_* environment flags.
Without a profile or overrides, features default to enabled.

Audio disabling covers system volume and real visualizer capture, not all
radio or external application audio. OpenGL disabling selects Tk/Canvas
fallbacks and blocks native map and Cesium activation; it is not a
process-wide prohibition on graphics APIs in external applications.
Spotify disabling blocks background startup and guarded operations while
retaining presentation objects. ADS-B disabling blocks receiver tracking,
status polling and dashboard launches. Simulation does not emulate physical RF,
GPS, camera, GPU or Android hardware.
