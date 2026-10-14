# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Play mono FM broadcast audio from the native RTL-SDR source."""

from __future__ import annotations

import argparse
import sys

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import RtlSdrSource


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--volume", type=float, default=0.6)
    args = parser.parse_args()
    if args.seconds <= 0 or not 0 <= args.volume <= 1:
        parser.error("seconds must be positive; volume must be between 0 and 1")
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SystemExit("Install audio dependencies: pip install scipy sounddevice") from exc

    source = RtlSdrSource()
    decoder = WbfmMonoDemodulator()
    samples_remaining = round(args.seconds * decoder.audio_rate_hz)
    try:
        source.open()
        source.set_sample_rate(2_400_000)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.start()
        print(f"Playing mono FM at {args.frequency / 1e6:.3f} MHz for {args.seconds:g}s")
        with sd.OutputStream(samplerate=48_000, channels=1, dtype="float32") as stream:
            while samples_remaining > 0:
                pcm = decoder.process(source.read_iq())
                count = min(len(pcm), samples_remaining)
                if count:
                    stream.write(np.ascontiguousarray((pcm[:count] * args.volume).reshape(-1, 1)))
                    samples_remaining -= count
    except (RuntimeError, sd.PortAudioError) as exc:
        print(f"FM audio unavailable: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
