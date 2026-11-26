# Raspberry Pi 5 userspace simulation

Run as an unprivileged user on a Linux host with rootless Podman and ARM64 binfmt/QEMU support. On Debian 13 x86 hosts the relevant packages are qemu-user, qemu-user-binfmt and passt.

From the repository root:

```sh
bash development/simulation/rpi5/build.sh
bash development/simulation/rpi5/run.sh
```

The image uses ARM64 Debian trixie. The read-only checkout and synthetic Raspberry Pi OS/model fixtures exercise installer plan resolution without installing host services. Xvfb checks Tk availability at both supported screen sizes. The runtime has no network, published ports or hardware devices, and is limited to 768 MiB and one CPU. The build needs network access for Debian packages.

This is a smoke harness, not a full application installation or hardware emulator. Actual ORC Python dependencies, application tests, systemd orchestration, Waydroid, GPU and RF hardware remain separate validation tasks. Run only trusted repository code. The base image tag and Debian package versions are mutable.
