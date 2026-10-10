# Logging device validation

The implementation and CI checks cover ORC-owned Python/C++ events, privacy,
operation correlation, bounded storage and live paging. This checklist verifies
the installed hardware, supervisors and Android viewer. Record pass/fail and the
relevant event names; attach only the failing check and a short error excerpt.

## Update and local gate

From your OpenRoadCode checkout, switch branches before updating or installing:

```bash
git switch feature/bridge-live-logs
git pull --ff-only
source venv/bin/activate
python scripts/quality_gate.py
```

Use your existing installation scripts to update/restart deployed ORC services.
No new logger dependency or Android APK change is introduced by this final pass.
The existing bridge APK must include **Diagnostics → Logs**. If its service-manager
API is older, update/restart that manager as described in the [logging guide](README.md).

## Runtime and hardware

Start ORC normally first, using `./runOrcUi --follow-logs` for readable live output.
Routine capture, inference, sensor polls and lighting commands should stay quiet
at INFO. INFO records identify state changes; WARNING records identify a new
failure signature. A successful retry should produce a recovery record.

| Check | Exercise | Expected diagnostic behavior |
| --- | --- | --- |
| Vision | Open VISION, change camera mode/AI, hide and reopen it | Session/model/tracker/camera lifecycle records; worker events retain the session operation ID; hidden sessions deliver no obsolete frames |
| Camera failure | Start with an unavailable test camera, then restore it and reopen VISION | One warning per repeated failure signature and a recovery record after the camera starts successfully |
| Inference/tracking | Use a deliberately failing test detector/tracker, then allow a successful frame | Failure identifies `inference` or `tracking`; the next successful frame recovers without restarting the capture session |
| Sensors | Start with configured and unavailable test sensors; restore the test source and read again | `environmental.*` start/stop, failure/recovery or unconfigured state; no raw measurements in new records |
| Lighting | Connect, change power/color/brightness, enable reactive lighting, then exercise an unavailable test controller and reconnect | `lighting.*` connection changes, command failures and recovery; repeated reactive updates remain DEBUG |
| Earth | Enter Earth with GPS unavailable, restore fixes, pause follow and recenter | Waiting/ready/follow/tracking transitions; bridge failures and recovery without coordinates or browser endpoints |
| POIs | Search and select, launch an action, clear/close before a delayed action completes; test a missing offline database and restore it | Search/action operation IDs, bounded result count, database failure/recovery and discarded late results |
| Existing subsystems | Exercise one navigation, radio, automotive, media and weather action | Existing structured component/event names and request IDs continue to appear |

For targeted detail, restart the relevant process with component overrides:

```bash
ORC_LOG_COMPONENT_LEVELS='vision=DEBUG,environmental=DEBUG,lighting=DEBUG,navigation.earth=DEBUG,navigation.poi=DEBUG,navigation.gps=DEBUG' ./runOrcUi --follow-logs
```

An already running service needs its own environment settings and restart to
enable DEBUG. Return to normal levels after the diagnostic session. These new
ORC-owned records exclude image/model contents, detection labels/boxes/track IDs,
GPS coordinates, sensor readings, addresses, URLs, paths, BLE packets, place names,
and exception messages. UI status and separate third-party diagnostic output are
outside that field-exclusion guarantee.

## Android and retention

1. Open **Diagnostics → Logs** and select the intended runtime. Confirm the stated
   store scope. Termux normally shares the ORC store; the restricted Linux manager
   exposes its private service-manager store, not another user's UI log directory.
2. Trigger an operation visible in that store and confirm it arrives live. Filter
   by component and severity; changing a filter must start a fresh history page.
3. Pause, trigger another operation, then resume. Leave the screen and background
   the app; polling should stop, and returning should resume without duplicated
   polling loops. Copy/share should include only displayed bounded history.
4. If a natural rotation occurs during the session, confirm terminal/Android
   viewing continues. Expired cursors may reset to retained history. CI already
   exercises small-budget rotations; generating 50 MiB on the device is unnecessary.
5. Inspect the configured ORC log directory: the active JSONL file plus at most
   four backups, each at most 10 MiB. Supervisor journals and third-party files
   have separate retention policies.

Full local-gate results and this device checklist remain awaiting user validation.
