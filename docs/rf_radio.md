# RF radio presentation contracts

ORC's Tk receiver panel receives a supplied `RfRadioSession` and renders frozen
`RfRadioState` values. `RadioRequest` represents launch, tuning, presets, telemetry,
display controls, themes, ADS-B, and native host resizing. The UI formats Hz and dB;
profiles expose presentation metadata and presets without backend configuration paths.
The `UiWidget` marker remains a small policy marker, with no injection machinery.

`ReceiverSession` owns receiver orchestration and generation guards. Composition
constructs the profile controller, telemetry monitor, SDR++ remote controls, managed
application service, ADS-B adapter, and X11 adapter. A composition-owned serial RF
executor keeps shared receiver operations ordered. NOAA launch and retry work also
runs there, outside Tk. Internet radio retains its separate worker pools.

The frontend queue delivers worker results on the UI thread. Closing or hiding a
session invalidates queued requests and results immediately. Native embedding checks
cancellation while discovering a window. Retirement then detaches the native client
before Tk destroys its host. Native launch/embed/resize and cleanup share a lock;
hiding may briefly wait for an already executing native operation. SDR++ startup
itself runs outside that lock, so a slow startup does not prevent retirement.
The application service also rejects launches after terminal runtime shutdown and
serializes shutdown with a startup already in progress.
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

Run `python scripts/quality_gate.py` and the focused receiver/X11 suites. Live SDR++,
rigctl, telemetry sockets, ADS-B, X11 embedding, theme switching, and hardware audio
still require a device acceptance pass. Headless tests cannot verify those behaviors.
