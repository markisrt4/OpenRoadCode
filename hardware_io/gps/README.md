# GPS Reader

The `GpsReader` provides a small hardware I/O interface for receiving GPS data
from `gpsd`.

The module does **not** open a USB serial device directly. `gpsd` owns the
physical GPS device, such as `/dev/ttyACM0`, and `GpsReader` connects to the
`gpsd` service over TCP at `127.0.0.1:2947` by default.

<aside class="orc-diagram-legend" aria-label="Architecture diagram legend">
  <strong>Diagram key</strong>
  <span><i class="orc-legend-swatch orc-legend-app"></i>App / UI</span>
  <span><i class="orc-legend-swatch orc-legend-service"></i>Service / runtime</span>
  <span><i class="orc-legend-swatch orc-legend-controller"></i>Controller / domain</span>
  <span><i class="orc-legend-swatch orc-legend-message"></i>Messaging / contract</span>
  <span><i class="orc-legend-swatch orc-legend-adapter"></i>Protocol / hardware</span>
  <span><i class="orc-legend-swatch orc-legend-external"></i>External / input</span>
</aside>

```mermaid
flowchart LR
    gps["USB GPS /dev/ttyACM0"] --> gpsd["gpsd"] --> reader["GpsReader"] --> callback["Callback"]

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;
    class gps,gpsd orcExternal;
    class reader orcAdapter;
    class callback orcController;
```

This keeps USB device discovery and serial protocol handling outside the Python
reader.

## Reported Data

`GpsData` contains:

- Latitude
- Longitude
- Altitude
- Speed
- Track
- GPS fix mode
- Satellites visible
- Satellites used in the current fix

The `has_fix` property is true when `gpsd` reports either a 2D or 3D fix.

The reader only reports hardware data received from `gpsd`. Application-specific
interpretation and behavior belong in higher-level components.

## Dependencies

On Debian, Ubuntu, or Raspberry Pi OS:

```bash
sudo apt install gpsd gpsd-clients python3-gps
python3 -m pip install gps
```


## VM USB Setup

Attach the USB GPS receiver to the Linux VM. Confirm that Linux created a serial
device:

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

For the currently tested receiver, the device appears as:

```text
/dev/ttyACM0
```

The exact name is not guaranteed. Some receivers appear as `/dev/ttyUSB0`, and
the number can change when devices are unplugged or reconnected.

Check which group owns the device:

```bash
ls -l /dev/ttyACM0
```

If the device belongs to the `dialout` group and your user cannot read it:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in after changing group membership.

## Component Test: Start gpsd

A component-test helper launches `gpsd` in the foreground without changing the
system-wide `gpsd` configuration.

From the project root:

```bash
hardware_io/gps/component_test/start_gpsd.sh /dev/ttyACM0
```

The device argument is optional. It defaults to `/dev/ttyACM0`:

```bash
hardware_io/gps/start_gpsd.sh
```

Keep this terminal open while testing. Press `Ctrl+C` to stop `gpsd`.

This script is intended for component testing and VM development. A deployed
system should configure and manage `gpsd` through the operating system's service
configuration.

### Verify gpsd directly

In another terminal, verify that `gpsd` is producing reports:

```bash
gpspipe -w
```

For a graphical or terminal client, depending on the installed package:

```bash
cgps -s
```

Seeing reports without a position is normal before the receiver acquires a fix.
For the first fix, place the antenna where it has a clear view of the sky. A fix
may take several minutes, and indoor testing is frequently an exercise in
watching expensive silence.

## Component Test: GPS CLI

With `gpsd` running, start the Python CLI from the project root:

```bash
python3 -m hardware_io.gps.component_test.gps_cli
```

Before a fix is available, the CLI reports that it is waiting and shows the
visible and used satellite counts when `gpsd` provides them:

```text
Waiting for GPS fix... satellites visible=7, used=0, mode=1
```

After a fix is acquired, the CLI prints the position and fix type:

```text
3D fix: lat=... lon=... alt=... speed=... track=... satellites_used=5
```

Press `Ctrl+C` to stop the reader.

## System gpsd Service

If the operating system's `gpsd` service is already configured for the GPS
receiver, do not run the component-test launcher. Confirm the existing service
instead:

```bash
systemctl status gpsd gpsd.socket
```

Then verify its output:

```bash
gpspipe -w -n 5
```
