# SDR++ retirement audit

## Current status

Source retirement has been implemented on `feature/sdrforge-native-spectrum`. Legacy launchers, telemetry/control clients, C++ modules, installation scripts and the unreferenced deprecated FM panel have been removed. Native SDRForge provides REST (5570), ZeroMQ (5571) and Rigctl (4532). Generic X11 and Rigctl tooling and negative regression guards remain.

The local regression run reported 766 passed, 2 failed, 19 skipped and 43 subtests passed; both outdated assertions were corrected and the affected suites subsequently reported 32 passed. Final post-cleanup regression, installer and hardware acceptance remain pending. The later source reference audit found no callers of the deprecated FM panel and no active references to the retired interfaces.

The inventory below is historical, not a list of remaining implementation blockers.

## Historical inventory

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

## Branch consolidation decision (2026-11-21)

The authoritative integration branch is `feature/sdrforge-native-spectrum`.
Do not reset, replace, or wholesale merge it with any of the branches below.

| Branch | Disposition | Evidence / constraints |
| --- | --- | --- |
| `feature/sdrforge-spectrum-ui` | Eligible for retirement | The spectrum normalizer and its unit-test file have identical Git blob SHAs on the integration branch; review its `AGENTS.md` change separately before deletion if needed. |
| `feature/sdrforge-managed-termux` | Eligible for retirement after final service-test review | Current runit launcher explicitly requires Android-authorized USB handoff for real hardware and uses the radio-region wrapper; current service manager has source-switching and readiness handling. Do not restore older direct hardware startup. |
| `native-sdr-radio` | Legacy, retirement candidate | ORC-native DSP and RDS implementations preceded the independent libSDRForge library. Do not reintroduce duplicate DSP into ORC. |
| `feature/libsdrforge-extraction-plan` | Legacy, retirement candidate | Exactly one documentation commit ahead of `native-sdr-radio`, containing the historical extraction plan. Preserve that document before branch deletion if historical context is required. |
| `android-rtl-tcp-source` | Legacy, retirement candidate | Contains old SDR++ RTL USB proxy experiments. Current design uses Android USB authorization and Termux libSDRForge acquisition. Review non-SDR changes before deleting this branch. |
| `feature/noaa-rf-weather-provider` | **Excluded** | Separate recent NOAA RF weather work. Do not merge, delete, or alter as part of this retirement. |

Branch retirement must not remove files from the current integration branch.
Remote branch deletion requires explicit verification that no unique desired work or open PR depends on the branch.

### Historical SDR++ blockers (resolved in source)

- `apps/orcUi/composition/radio.py` retains the legacy SDR++ fallback, theme synchronization, and X11 embedding path.
- `controllers/radio/rf_radio_session.py` still handles SDR++ embedding and legacy telemetry.
- `apps/carUi/radio/radio_session_controller.py` still imports `SDRTelemetryMonitor` and uses legacy rigctl readiness wording.

Keep these components until their consumers have migrated to native SDRForge contracts and regression coverage.
