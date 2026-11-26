# RF radio presentation contracts

ORC's Tk receiver panel receives a supplied `RfRadioSession` and renders frozen
`RfRadioState` values. `RadioRequest` represents launch, tuning, presets, telemetry,
display controls, themes, ADS-B, and native host resizing. The UI formats Hz and dB;
profiles expose presentation metadata and presets without backend configuration paths.
The `UiWidget` marker remains a small policy marker, with no injection machinery.

`ReceiverSession` owns receiver orchestration and generation guards. Composition
constructs the profile controller, SDRForge telemetry subscriber, native display controls,
application service, ADS-B adapter, and X11 adapter. A composition-owned serial RF
executor keeps shared receiver operations ordered. NOAA launch and retry work also
runs there, outside Tk. Internet radio retains its separate worker pools.

The frontend queue delivers worker results on the UI thread. Closing or hiding a
session invalidates queued requests and results immediately. ADS-B native embedding checks
cancellation while discovering a window. Retirement then detaches the native client
before Tk destroys its host. Native launch/embed/resize and cleanup share a lock;
hiding may briefly wait for an already executing native operation. RF service startup is managed independently of the frontend.
Application-owned RF audio can continue after leaving the radio screen. Explicit
ADS-B selection relinquishes RF first because both use the same SDR.

Session close is terminal and idempotent. Composition closes sessions before shutting
down the RF executor, including partial widget-construction rollback. Widgets do not
construct controllers, start workers, access transports, or call native adapters.
The radio screen delegates cleanup to its panel/session instead of clearing a shared
adapter directly.

## Enforcement and validation

The dependency gate removes the five former RF widget exceptions. The strict mypy
scope includes RF contracts, session, receiver panel, entry panel, composition, and
static bindings for the real Tk view and X11 adapter. The Tk menu and drawer
share declared presentation fields through `RadioPresentationFrame`; their code
is also checked strictly, without adding behavior to the shared `UiWidget` marker. Behavioral tests exercise
queued and in-flight launch retirement, stale UI delivery, native cancellation,
telemetry measurements, preset/tuning requests, ADS-B ownership, and cleanup failure.

Run `python scripts/quality_gate.py` and the focused receiver/X11 suites. Live SDRForge,
rigctl, telemetry sockets, ADS-B, X11 embedding, theme switching, and hardware audio
still require a device acceptance pass. Headless tests cannot verify those behaviors.

## Weather NOAA action diagnostics

Weather's NOAA button keeps Weather visible and submits startup/tuning to the RF
worker. Events under `orc.radio.noaa` distinguish button presses, missing bindings,
queued work, worker startup, cancellation, tuning completion, and failures. Worker
exceptions are logged with a traceback and dispatched as RF status instead of being
lost inside a worker future. Terminal shutdown drops pending work and status delivery.

To watch just these events during device acceptance:

```bash
python -m apps.orcUi --follow-logs --log-component orc.radio.noaa --log-level INFO
```

Controller state reports requested tuning. Confirm actual tuning separately with
`RigctlClient().get_frequency()`; a success label alone is not receiver readback.

### Managed SDRForge control

The desktop UI uses authenticated REST mutations when its environment contains
`SDRFORGE_ACQUISITION_TOKEN`. The token must match the local SDRForge service's
credential. REST client requests attach it only for local control mutations,
and rigctl remains available for standalone control and read-only telemetry.

On a Pi 5, opt in during host setup with
`--target rpi5 --feature sdrforge --feature adsb --managed-rf`. Use `./runOrcUi`
so the launcher loads the private per-user credential and excludes a second
managed UI process. The settings tab **RF Receivers** discovers USB devices and
saves assignments for **Radio / Airband**, **NOAA Weather Radio**, and **ADS-B**.

Radio uses the primary user service. NOAA shares the primary instance when
assigned the same serial and uses a separate supervised instance when assigned a
different serial. To free a shared radio receiver, stop reception before
starting NOAA or ADS-B. The on-demand readsb unit runs with the desktop user's
USB permissions, with automatic restart disabled. Opening or leaving its
dashboard does not stop tracking. Use the aircraft tracking control.

readsb can interpret a plain integer as a device index. For an ADS-B assignment,
use a unique alphanumeric receiver serial or a numeric serial with leading
zeroes. The coordinator verifies the USB device held by the readsb process
before reporting tracking active.

#### Raspberry Pi 5 acceptance

From the OpenRoadCode checkout, with the UI closed:

```bash
git fetch origin
git switch feature/rpi5-integration
git pull --ff-only
./scripts/installers/host_setup.sh --target rpi5 --feature sdrforge --feature adsb --managed-rf --show-plan
./scripts/installers/host_setup.sh --target rpi5 --feature sdrforge --feature adsb --managed-rf
systemctl --user is-active libsdrforge.service
curl -fsS http://127.0.0.1:5570/v1/health
lsusb -d 0bda:2838
lsusb -d 0bda:2832
xrandr --current
./runOrcUi
```

1. In **Settings → RF Receivers**, refresh discovery, verify the USB serials and
   assign Radio / Airband, NOAA Weather Radio, and ADS-B. Reopen the page and
   confirm the settings persisted. Check for clipping at 1280×720 and 800×480.
2. Start the radio receiver and tune a locally receivable FM station and an
   airband AM channel. Navigate away and return while monitoring reception.
3. With one receiver, try NOAA or ADS-B while radio is active. Confirm the
   request leaves reception intact. Stop radio, verify release, then start NOAA
   or ADS-B. Tune the NOAA preset for your region.
4. Assign distinct devices and run radio and NOAA simultaneously. Enable ADS-B
   tracking alongside either consumer on a different receiver. Confirm live
   aircraft in the dashboard and reopen it while tracking stays active.
5. Unplug an active receiver. Refresh **RF Receivers**, check the disconnected
   assignment, reconnect it, and retry the consumer. If release was unconfirmed,
   the assignment must remain reserved until the service can confirm cleanup.
6. During reception, run the scoped service-termination check below, then use
   **Start Receiver** again. For ADS-B, stop and re-enable tracking with its
   control after terminating the corresponding user instance.
7. Exit the UI and verify the primary service still answers with acquisition
   stopped and hardware released. Repeat setup, reopen the UI and check the
   saved assignments and receiver availability.

```bash
systemctl --user kill --signal=SIGKILL libsdrforge.service
systemctl --user list-units 'libsdrforge*.service' 'openroadcode-readsb@*.service' --all
journalctl --user -u libsdrforge.service -u libsdrforge-weather.service -n 70 --no-pager
curl -fsS http://127.0.0.1:5570/v1/receiver
curl -fsS http://127.0.0.1:5572/v1/receiver
```

The NOAA endpoint comes up on demand when NOAA has a distinct receiver. Release
confirmation is `hardware_released: true` with `starting` and `running` false.
The controlled native-close failure case is exercised by the hardware-free
regression suite.
