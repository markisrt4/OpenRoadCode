# SDR++ retirement audit (in progress)

This inventory identifies migration work before deleting SDR++ code. It is based on the
current `feature/sdrforge-rigctl-cli` integration and repository code-search results.
Code search indexes the default branch, so this is **not** an exhaustive feature-branch
reference count. Run the local search below before removing anything.

## Active dependencies: do not delete yet

| Component | Dependency | Migration gate |
| --- | --- | --- |
| `apps/orcUi/composition/radio.py` | Instantiates `SDRPPControl`, `SDRTelemetryMonitor`, `X11WindowEmbedder`; calls `sync_sdrpp_theme` | Native RF composition, themes and aircraft navigation verified |
| `controllers/radio/rf_radio_session.py` | SDR++ launch/embed, native control actions and legacy telemetry path coexist with SDRForge REST/ZMQ | Split or eliminate legacy session responsibilities with tests |
| `controllers/sdr/sdrpp_control.py` | SDR++ remote-control protocol (port 4533) | Native waterfall, bandplan, FFT hold, auto-range and theme controls |
| `controllers/sdr/sdr_telemetry_monitor.py` | SDR++ telemetry protocol (port 4534) | Migrate all callers, including car UI |
| `apps/carUi/radio/radio_session_controller.py` | Constructs `SDRTelemetryMonitor` | Replace car UI telemetry source and validate UI |
| `apps/launchers/sdrpp_launcher.py` and `apps/launchers/managed_sdrpp_launcher.py` | SDR++ process lifecycle | Confirm no remaining launch/management consumers |
| `protocols/sdrpp_remote_control/` and `protocols/sdrpp_telemetry/` | SDR++ wire protocols | Delete only after all callers are gone |

## Likely removal candidates after gates pass

- `development/debian/setup_sdrpp.sh`
- `development/termux/setup_sdrpp.sh`
- `development/termux/run_sdrpp.sh`
- `scripts/runtime/run_sdrpp_vnc.sh`
- SDR++-specific launcher, configuration, docs and tests discovered in local audit.

Keep frontend-neutral `RadioTelemetry`, `SpectrumPresentation`, radio profile
interfaces and SDRForge ZMQ/REST/rigctl adapters. Do not delete them based on naming.

## Local verification

```bash
git grep -n -i -E 'sdrpp|sdr\+\+|SDRTelemetryMonitor|SDRPPControl' -- \
  ':!development/sdrpp/RETIREMENT_AUDIT.md'
git ls-files | grep -Ei 'sdrpp|sdr_plus_plus'
```

Before each deletion: remove imports and composition wiring, update targeted unit
tests, run full relevant test suites on Ubuntu runners, then validate native
spectrum/waterfall reset and real USB disconnect/reconnect on hardware.
