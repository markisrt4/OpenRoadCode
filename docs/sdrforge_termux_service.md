# Managed SDRForge radio service (Termux)

The Android Companion Radio card controls `openroadcode-sdrforge` through
the existing local service manager on 127.0.0.1:8769. The supervised
process runs `libSDRForge/examples/live_transport_server.py` in Termux.

## Installation

Install libSDRForge in `$HOME/src/libSDRForge`, then from OpenRoadCode:

```bash
git fetch origin
git switch feature/sdrforge-managed-termux
git pull --ff-only
bash scripts/runit/install_termux_services.sh
sv status openroadcode-sdrforge
```

The service is installed **down** by default. Select **Simulated IQ** in
Companion and press **Apply source**, then **Launch**. The service manager
writes a restricted source profile and restarts the service if running.
Use **Receive** to start IQ acquisition via SDRForge REST on 5570.
**End RX** stops acquisition; **Shutdown** stops the supervised server.

For USB operation, select **RTL-SDR USB** before launching. Android does
not claim the USB device. The existing Termux USB permission and handoff
process is still required; the current managed run script does not
automatically obtain USB permission or inject an authorized descriptor.

The SDRForge server owns loopback REST 5570, ZMQ 5571 and rigctl 4532.
Do not start a second standalone server on these ports.

If the app reports a service-manager error, update OpenRoadCode, rerun
the installer, and restart the service manager. If REST is unavailable
but the supervisor says running, inspect `sv status openroadcode-sdrforge`
and the service logs. No automatic USB reconnect is promised yet.
