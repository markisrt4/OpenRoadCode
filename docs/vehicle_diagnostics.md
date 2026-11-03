# Vehicle diagnostics and Android simulated faults

The automotive service owns the only ELM327 connection. Diagnostic commands wait
on a bounded worker while `Obd2Manager.read_state()` alternates diagnostic and
telemetry requests at the configured request rate. Four services require seven
polling steps (plus adapter response time). There is one active scan; competing
runtime requests receive a busy response. Scans time out after ten seconds.
Disconnect and shutdown release the waiting scan. No code-clearing commands exist.

`services.automotive.command_endpoint` defaults to `tcp://127.0.0.1:5561` in the
runtime configuration. Both UI composition and service consume that setting.
The endpoint accepts ZeroMQ REQ/REP JSON:

```json
{"command":"automotive.diagnostics.scan","arguments":{}}
```

The response has `ok`, `message`, and on success `data`. Data includes `mil_on`,
`stored_dtc_count`, `emissions_ready`, `responding_ecus`, `trouble_codes` (with
`code`, `status`, `ecu_id`), and `completed_services` (valid coverage from every observed ECU). Missing services are
unavailable coverage, never evidence of no faults. Coverage is generic emissions
OBD-II only, even when all four services respond.

HEALTH → Scan Now uses a controller worker and the UI dispatcher. Hiding the
vehicle screen unsubscribes its widgets. Remounting gets cached state; closing
discards late completions. The UI never opens an adapter or blocks Tk on a scan.

## Repeatable Android device check

Install the exact branch-head APK with the Android repository's supported
`development/termux/install_latest_apk.sh` after switching, fetching and pulling
`automotive-fault-injector`. Its CI run must be successful for the current commit.
In Advanced mode, enable the **simulated vehicle** endpoint and select a fault.
The physical Bluetooth bridge must be stopped so the simulator can own port
35000. Check its observed running status; a saved enabled preference alone does
not establish a bound listener. Injection changes only the simulated ECU.

Run the usual automotive service with the Termux TCP input profile pointing to
127.0.0.1:35000. Keep the normal message broker and UI running. Do not start a
second automotive service or a separate adapter client. In the OpenRoadCode repo:

```sh
git switch vehicle-diagnostics-integration
python -m services.automotive.diagnostics_cli --config config/runtime.termux.toml --expect-code P0300 --expect-status stored --expect-mil on --expect-readiness ready
```

The CLI talks only to the command service. Confirm the same result in VEHICLE →
HEALTH → Scan Now. Switch scenarios and repeat using the expected values below.
Watch RPM, MAP and vehicle speed continue updating during and after every scan.

| Scenario | Stored | Pending | Permanent | MIL | Ready |
| --- | --- | --- | --- | --- | --- |
| OFF | none | none | none | off | yes |
| P0300 / P0171 / P0420 / P0455 | selected code | none | none | on | yes |
| PENDING | none | P0300 | none | off | yes |
| PERMANENT | none | none | P0300 | off | yes |
| NOT_READY | none | none | none | off | no |

For pending/permanent use `--expect-status pending` / `permanent`; for NOT_READY
use `--expect-mil off --expect-readiness not-ready`. Repeat scans, hide/remount the
screen during a scan, and stop the simulator during a scan: HEALTH must show an
unavailable/partial result rather than a healthy result. Restore the simulator
and verify reconnection. An empty service result differs from a valid zero-code
response. The current decoder expects ECU header, payload length, service, and
payload pairs; the simulator honors ATH1/ATS0 for this path.

## Automated focused validation

```sh
git switch vehicle-diagnostics-integration
python -m pytest controllers/automotive/obd2/unit_test controllers/automotive/unit_test/test_diagnostics_scan_controller.py services/automotive/unit_test/test_diagnostics_commands.py config/unit_test/test_service_runtime_config.py common/logging/unit_test/test_automotive_logging.py apps/orcUi/frontend/tk/unit_test/test_vehicle_diagnostics_lifecycle.py
```

The command component test binds an actual ephemeral loopback ZeroMQ listener,
checks scan output and interleaved telemetry, and verifies a single adapter owner
through shutdown. Decoder tests use Android wire examples. Android's Build
Android APK workflow tests the actual Java response helper and builds the APK.
These checks do not replace a device run of the Android service or read-only
KONNWEI testing. Complete simulation/device verification before physical testing.
The project-wide quality gate remains the user's final branch validation.
