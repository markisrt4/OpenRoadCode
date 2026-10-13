# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone live RF spectrum viewer using ORC's native SDR stack."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from controllers.radio.spectrum.spectrum_analyzer import SpectrumAnalyzer
from hardware_io.sdr import RtlSdrSource


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--sample-rate", type=int, default=2_400_000)
    parser.add_argument("--fft-size", type=int, default=2048)
    parser.add_argument("--gain", type=float, default=None)
    args = parser.parse_args()

    analyzer = SpectrumAnalyzer(args.fft_size)
    source = RtlSdrSource()
    try:
        source.open()
        source.set_sample_rate(args.sample_rate)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.start()

        fig, ax = plt.subplots()
        x_mhz = (
            args.frequency
            + np.fft.fftshift(np.fft.fftfreq(args.fft_size, d=1 / args.sample_rate))
        ) / 1e6
        line, = ax.plot(x_mhz, np.full(args.fft_size, -100.0), linewidth=1)
        ax.set_xlabel("Frequency (MHz)")
        ax.set_ylabel("Relative power (dBFS)")
        ax.set_title("OpenRoadCode Native SDR Spectrum")
        ax.set_ylim(-110, 0)
        ax.set_xlim(x_mhz[0], x_mhz[-1])
        ax.grid(True, alpha=0.3)
        plt.show(block=False)
        while plt.fignum_exists(fig.number):
            frame = analyzer.analyze(source.read_iq())
            line.set_ydata(frame.power_db)
            fig.canvas.draw_idle()
            plt.pause(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        plt.close("all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
