# libSDRForge extraction plan

Status: design and migration planning only. No DSP behavior changes.

## Goal

Create an independent `libSDRForge` Python library following the conventions of
`libMusicForge`: Hatchling, `src/` package layout, optional adapters,
capability-based interfaces, examples, tests, Apache-2.0 licensing decision,
and Ubuntu GitHub Actions. Do not couple the library to OpenRoadCode.

## Component migration map

| Existing OpenRoadCode component | Destination | Notes |
| --- | --- | --- |
| `hardware_io/sdr/sdr_types.py` | `src/sdrforge/models/` | IQ block, formats, capabilities |
| `hardware_io/sdr/sdr_source_if.py` | `src/sdrforge/interfaces/` | Hardware-independent contract |
| `hardware_io/sdr/rtl_sdr_source.py` | `src/sdrforge/adapters/rtl_sdr.py` | Optional librtlsdr dependency |
| `controllers/radio/dsp/digital_downconverter.py` | `src/sdrforge/dsp/` | Preserve current behavior |
| `controllers/radio/dsp/fm_multiplex_discriminator.py` | `src/sdrforge/dsp/` | Preserve current behavior |
| `controllers/radio/dsp/fm_stereo_decoder.py` | `src/sdrforge/dsp/` | Preserve current behavior |
| `controllers/radio/dsp/channelized_*demodulator.py` | `src/sdrforge/receivers/` | AM, NFM, WFM, stereo WFM |
| `controllers/radio/dsp/rds_*.py` | `src/sdrforge/protocols/rds/` | Signal and protocol stages |
| `controllers/radio/rds_receiver_controller.py` | `src/sdrforge/protocols/rds/` | RDS orchestration |
| `controllers/radio/virtual_receiver_manager.py` | `src/sdrforge/core/` | Multi-channel DSP management |
| `controllers/radio/multi_mode_radio_receiver.py` | `src/sdrforge/receivers/` | Public receiver facade candidate |
| `controllers/radio/dsp/channel_rf_telemetry.py` | `src/sdrforge/diagnostics/` | RF diagnostics |
| `controllers/radio/dsp/rds_signal_diagnostics.py` | `src/sdrforge/diagnostics/` | RDS signal metrics |
| `controllers/radio/dsp_performance_monitor.py` | `src/sdrforge/diagnostics/` | Processing budget |
| `controllers/radio/dsp/unit_test/` | `tests/` | Preserve fixtures and assertions |
| `controllers/radio/component_test/native_rds_cli.py` | `examples/` | Standalone live validation |
| `controllers/radio/component_test/native_radio_cli.py` | `examples/` | Split generic demo from ORC wiring |
| `controllers/radio/native_radio_service.py` | ORC | ORC lifecycle and configuration |
| `controllers/radio/recovering_radio_session.py` | ORC initially | Recovery policy; revisit after extraction |
| `controllers/radio/radio_audio_session.py` | ORC | Audio integration |
| `hardware_io/audio/` | ORC | Audio sinks, buffering, playback |
| ORC UI / Android bridge / service manager | ORC | Application-specific integration |

## Existing library comparison

- **liquid-dsp**: candidate for measured acceleration of filtering, NCO,
  resampling, and synchronization. Do not replace tested Python DSP during extraction.
- **SoapySDR**: candidate for optional multi-device hardware adapter. Not a
  demodulation or RDS replacement.
- **GNU Radio**: mature general-purpose processing framework; avoid mandatory
  dependency for lightweight embedded operation.
- **pyrtlsdr / librtlsdr**: hardware acquisition alternatives; assess current
  RTL adapter and platform constraints before switching.
- **csdr**: optional lightweight DSP reference, not a required runtime.

No dependency substitution is approved solely on feature overlap. Benchmark,
verify licensing, and validate Linux/Termux support before selecting one.

## Target layout

```text
libSDRForge/
  .github/workflows/ci.yml
  src/sdrforge/
    __init__.py
    core/
    models/
    interfaces/
    adapters/
    dsp/
    receivers/
    protocols/rds/
    diagnostics/
  tests/
  examples/
  pyproject.toml
  AGENTS.md
  README.md
  LICENSE
```

## Integration boundaries

- `sdrforge` must not import from `controllers`, `hardware_io`, or ORC UI.
- The DSP package must import without USB, sounddevice, or network services.
- Hardware backends must be optional; a fake or recorded IQ source must work.
- ORC owns service lifecycle, audio routing, application UI, and hardware
  resource priorities (including future ADS-B/RDS-TMC device scheduling).
- Do not delete ORC implementations until an independent library and ORC
  integration both pass their regression gates.
- Keep existing receiver semantics, metadata reset behavior, and RDS diagnostics
  unchanged during extraction.

## Library compatibility and release policy

- Follow libMusicForge's Hatchling packaging, `src/` layout, typed public
  interfaces, `tests/`, `examples/`, `AGENTS.md`, and CI conventions.
- Use a minimal public API and versioned releases; avoid exposing DSP internals
  as stable contracts prematurely.
- Existing ORC SDR source files carry MIT notices. libMusicForge is Apache-2.0.
  Resolve project licensing explicitly and retain applicable original notices.
- Run unit tests, lint, types, and packaging on Ubuntu GitHub Actions.
  Hardware-specific validation remains on the user's Linux/Pi/Termux devices.
- Never run tests in the Codex cloud VM unless specifically authorized.

## Ordered implementation gates

1. Review source inventory and existing library overlap (this plan).
2. Define stable IQ source, receiver, PCM, RDS metadata, and diagnostics APIs.
3. Create `markisrt4/libSDRForge` and copy code/tests without algorithm changes.
4. Extract optional RTL-SDR adapter and standalone CLI; verify offline CI.
5. Integrate ORC against a pinned library version; run ORC regression tests.
6. Remove duplicate ORC implementations only after integration succeeds.

Baseline before extraction: 102 passing radio DSP tests reported on
`native-sdr-radio` by the hardware owner. This document does not claim
any new CI/test run.
