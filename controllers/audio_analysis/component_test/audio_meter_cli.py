# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from controllers.audio_analysis.audio_analysis import AudioAnalyzer
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture


def meter(value: float, width: int = 36) -> str:
    filled = max(0, min(width, round(value * width)))
    return "#" * filled + "-" * (width - filled)


def spectrum_line(values: tuple[float, ...]) -> str:
    levels = " ▁▂▃▄▅▆▇█"
    return "".join(levels[min(8, round(value * 8))] for value in values)


def main() -> None:
    capture = PipeWireAudioCapture()
    analyzer = AudioAnalyzer()
    capture.start()
    print("Capturing the default PipeWire output monitor. Ctrl-C to stop.\n")

    try:
        while True:
            state = analyzer.analyze(capture.read())
            print(
                "\033[6A"
                f"LEVEL   [{meter(state.level)}] {state.level:0.2f}\n"
                f"PEAK    [{meter(state.peak)}] {state.peak:0.2f}\n"
                f"BASS    [{meter(state.bass)}] {state.bass:0.2f}\n"
                f"MID     [{meter(state.mid)}] {state.mid:0.2f}\n"
                f"TREBLE  [{meter(state.treble)}] {state.treble:0.2f}\n"
                f"SPECTRUM 31Hz {spectrum_line(state.spectrum)} 16kHz",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        capture.stop()


if __name__ == "__main__":
    print("\n" * 6, end="")
    main()
