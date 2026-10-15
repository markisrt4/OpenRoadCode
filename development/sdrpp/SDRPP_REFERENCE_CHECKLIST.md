# SDR++ reference receiver checklist for ORC WBFM

Use the same RTL-SDR dongle, antenna, station, and listening device.
Record settings that are *actually displayed* by SDR++; do not infer defaults.

## SDR++ known-good configuration

- SDR++ version / build:
- Source: RTL-SDR
- Sample rate:
- Hardware center frequency:
- Selected WFM station:
- WFM channel bandwidth:
- WFM stereo enabled (yes/no):
- De-emphasis (none/50 us/75 us):
- Tuner gain (automatic/manual and displayed dB):
- RTL AGC (on/off/unknown):
- Bias tee (on/off):
- Frequency correction (PPM):
- IF/offset tuning (if present):
- Squelch, noise reduction, audio processing:
- Audio output sample rate (if displayed):
- Subjective quality (0-100%):

## ORC baseline for comparison

- Capture sample rate: 2,400,000 samples/s
- Original target: 104.3 MHz
- Offset experiment: RTL center 104.5 MHz, station -200 kHz
- Gain: explicit --gain value or librtlsdr automatic tuner gain
- RTL digital AGC: not currently exposed by RtlSdrSource
- FM output: mono, 48 kHz, 75 us de-emphasis
- Existing channel filters: 2.4M -> 480k -> 240k
- Known subjective quality: approximately 80-85% of SDR++ per user
- Liquid discriminator A/B: similar sound, liquid quieter
- FIR-vs-IIR RF filtering A/B: similar sound

## Next diagnostic decision

1. Match SDR++ source/sample rate/gain/AGC/PPM and mono/de-emphasis settings.
2. Compare a *single* saved IQ capture processed by ORC against SDR++'s
   demodulation of the same IQ file, if SDR++ can load that file with known
   sample format and rate. Do not compare two separate over-the-air captures
   as if they are bit-identical.
3. If both pipelines differ on identical IQ, focus on WFM channel/audio
   processing. If not, investigate device configuration or playback.
4. Consider adding explicit RTL digital AGC and PPM controls to ORC only
   after the SDR++ reference values are established.

This is a diagnostic checklist, not a claim that settings have been verified.
