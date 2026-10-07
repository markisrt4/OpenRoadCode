# SDR Hardware I/O

`hardware_io.sdr` defines the hardware-independent boundary between OpenRoadCode and software-defined radio sample sources.

## Responsibilities

This package owns SDR lifecycle, RF center-frequency control, IQ sample-rate control, tuner gain, capability reporting, and raw IQ acquisition.

It intentionally does **not** own demodulation, filtering, FFT/spectrum analysis, signal-strength calculation, audio output, presets, scanning policy, or presentation.

## Architecture

```text
RTL-SDR / rtl_tcp / Android ORCU / future SDR
                    |
                    v
                SdrSourceIf
                    |
                 raw IQ
                    |
                    v
       controllers/radio processing
                    |
          +---------+---------+
          |                   |
       radio DSP          spectrum data
          |                   |
         PCM               ORC UI
```

A native SDR radio backend can consume `SdrSourceIf` while continuing to expose the existing `controllers.radio.RadioBackendIf` contract to the rest of ORC. This keeps hardware acquisition separate from radio-domain behavior and preserves the current controller boundary.

## Initial Scope

The first implementation target is RTL-SDR. The interface is intentionally transport-independent so local librtlsdr, rtl_tcp, the Android ORCU USB proxy, or future SDR hardware can provide IQ without changing consumers.
