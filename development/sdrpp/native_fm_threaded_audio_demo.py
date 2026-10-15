# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Threaded RTL-SDR mono FM playback with bounded buffers and diagnostics.

Capture, DSP and playback run independently. This is a diagnostic prototype:
queue drops are counted, but librtlsdr's internal USB overruns are not visible.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave
from dataclasses import dataclass
import queue
import sys
import threading
import time

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import RtlSdrSource


@dataclass
class Counters:
    captured: int = 0
    iq_dropped: int = 0
    pcm_dropped: int = 0
    pcm_underruns: int = 0
    dsp_blocks: int = 0
    dsp_seconds: float = 0.0
    rf_seconds: float = 0.0
    iq_high_water: int = 0
    pcm_high_water: int = 0
    record_dropped: int = 0
    iq_recorded_bytes: int = 0
    pcm_recorded_samples: int = 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=40.0,
                        help="Manual tuner gain in dB (default: known-good 40)")
    parser.add_argument("--tuner-agc", action="store_true",
                        help="Use automatic tuner gain instead of --gain")
    parser.add_argument("--rtl-agc", action="store_true")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--volume", type=float, default=0.6)
    parser.add_argument("--iq-queue", type=int, default=32)
    parser.add_argument("--pcm-queue", type=int, default=32)
    parser.add_argument("--record-dir", type=Path,
                        help="Save same-session raw IQ (.u8), demodulated WAV, and metadata")
    args = parser.parse_args()
    if args.seconds <= 0 or not 0 <= args.volume <= 1:
        parser.error("seconds must be positive and volume in [0,1]")
    if args.iq_queue < 2 or args.pcm_queue < 2:
        parser.error("queue capacities must be at least 2")

    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SystemExit("Install sounddevice: pip install sounddevice") from exc

    source = RtlSdrSource()
    decoder = WbfmMonoDemodulator()
    iq_queue: queue.Queue = queue.Queue(maxsize=args.iq_queue)
    pcm_queue: queue.Queue = queue.Queue(maxsize=args.pcm_queue)
    stop = threading.Event()
    capture_done = threading.Event()
    dsp_done = threading.Event()
    stats = Counters()
    failures: queue.Queue = queue.Queue()
    record_queue: queue.Queue = queue.Queue(maxsize=128)
    record_done = threading.Event()
    target_samples = int(round(args.seconds * 48_000))

    def capture():
        try:
            while not stop.is_set():
                block = source.read_iq()
                stats.captured += 1
                if args.record_dir is not None:
                    try:
                        record_queue.put_nowait(("iq", bytes(block.samples)))
                    except queue.Full:
                        stats.record_dropped += 1
                try:
                    iq_queue.put_nowait(block)
                    stats.iq_high_water = max(stats.iq_high_water, iq_queue.qsize())
                except queue.Full:
                    stats.iq_dropped += 1
        except Exception as exc:
            if not stop.is_set():
                failures.put(("capture", exc))
                stop.set()
        finally:
            capture_done.set()

    def process():
        try:
            while not stop.is_set() or not iq_queue.empty():
                try:
                    block = iq_queue.get(timeout=0.1)
                except queue.Empty:
                    if capture_done.is_set():
                        break
                    continue
                start = time.perf_counter()
                pcm = decoder.process(block)
                stats.dsp_seconds += time.perf_counter() - start
                stats.rf_seconds += len(block.samples) / (2 * block.sample_rate_hz)
                stats.dsp_blocks += 1
                if len(pcm):
                    if args.record_dir is not None:
                        try:
                            record_queue.put_nowait(("pcm", np.ascontiguousarray(
                                pcm, dtype=np.float32).tobytes()))
                        except queue.Full:
                            stats.record_dropped += 1
                    try:
                        pcm_queue.put_nowait(np.ascontiguousarray(
                            pcm * args.volume, dtype=np.float32
                        ))
                        stats.pcm_high_water = max(stats.pcm_high_water, pcm_queue.qsize())
                    except queue.Full:
                        stats.pcm_dropped += 1
        except Exception as exc:
            failures.put(("dsp", exc))
            stop.set()
        finally:
            dsp_done.set()

    def record():
        try:
            args.record_dir.mkdir(parents=True, exist_ok=True)
            with (args.record_dir / "capture.u8").open("wb") as iq_file, wave.open(
                str(args.record_dir / "demodulated.wav"), "wb"
            ) as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(48_000)
                while not record_done.is_set() or not record_queue.empty():
                    try:
                        kind, data = record_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if kind == "iq":
                        iq_file.write(data)
                        stats.iq_recorded_bytes += len(data)
                    else:
                        # Save the *pre-volume* demodulated audio for offline analysis.
                        audio = np.frombuffer(data, dtype=np.float32)
                        pcm16 = np.round(np.clip(audio, -1, 1) * 32767).astype(
                            "<i2"
                        )
                        wav.writeframesraw(pcm16.tobytes())
                        stats.pcm_recorded_samples += len(audio)
        except Exception as exc:
            failures.put(("recorder", exc))
            stop.set()

    threads = []
    recorder_thread = None
    played = 0
    started = time.monotonic()
    try:
        source.open()
        source.set_sample_rate(2_400_000)
        source.set_center_frequency(args.frequency)
        source.set_gain(None if args.tuner_agc else args.gain)
        source.set_rtl_agc(args.rtl_agc)
        source.start()
        if args.record_dir is not None:
            recorder_thread = threading.Thread(
                target=record, name="sdr-recorder", daemon=True
            )
            recorder_thread.start()
        threads = [
            threading.Thread(target=capture, name="sdr-capture", daemon=True),
            threading.Thread(target=process, name="sdr-dsp", daemon=True),
        ]
        for thread in threads:
            thread.start()
        print(f"Threaded WFM {args.frequency / 1e6:.3f} MHz, "
              f"gain={'auto' if args.tuner_agc else str(args.gain) + ' dB'}, "
              f"RTL AGC={'on' if args.rtl_agc else 'off'}", flush=True)
        with sd.OutputStream(samplerate=48_000, channels=1, dtype="float32") as stream:
            while played < target_samples and not stop.is_set():
                if not failures.empty():
                    break
                try:
                    pcm = pcm_queue.get(timeout=0.15)
                except queue.Empty:
                    if dsp_done.is_set():
                        break
                    stats.pcm_underruns += 1
                    continue
                count = min(len(pcm), target_samples - played)
                if count:
                    stream.write(pcm[:count].reshape(-1, 1))
                    played += count
    except (RuntimeError, sd.PortAudioError) as exc:
        print(f"FM audio unavailable: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        stop.set()
        # read_sync can block until USB completes. Join before closing source.
        for thread in threads:
            thread.join(timeout=3.0)
        if not threads or not threads[0].is_alive():
            source.close()
        else:
            print("Warning: capture thread did not stop; skipping unsafe close",
                  file=sys.stderr)
        record_done.set()
        if recorder_thread is not None:
            recorder_thread.join(timeout=10.0)
            if recorder_thread.is_alive():
                print("Warning: recording not fully flushed", file=sys.stderr)
            metadata = {
                "frequency_hz": args.frequency,
                "sample_rate_hz": 2_400_000,
                "audio_rate_hz": 48_000,
                "gain_db": None if args.tuner_agc else args.gain,
                "tuner_agc": args.tuner_agc,
                "rtl_agc": args.rtl_agc,
                "volume": args.volume,
                "iq_format": "u8_interleaved",
                "wav_format": "pcm16_mono_pre_volume",
                "captured_blocks": stats.captured,
                "dsp_blocks": stats.dsp_blocks,
                "iq_queue_dropped": stats.iq_dropped,
                "pcm_queue_dropped": stats.pcm_dropped,
                "record_queue_dropped": stats.record_dropped,
                "iq_recorded_bytes": stats.iq_recorded_bytes,
                "pcm_recorded_samples": stats.pcm_recorded_samples,
                "recording_complete": not recorder_thread.is_alive(),
            }
            args.record_dir.mkdir(parents=True, exist_ok=True)
            (args.record_dir / "metadata.json").write_text(
                json.dumps(metadata, indent=2) + "\\n", encoding="utf-8"
            )
            print(f"Recordings: {args.record_dir} "
                  f"(record queue drops={stats.record_dropped})")
        if not failures.empty():
            stage, exc = failures.get_nowait()
            print(f"{stage} failed: {exc}", file=sys.stderr)
        elapsed = time.monotonic() - started
        print(f"Playback {played / 48000:.2f}s in {elapsed:.2f}s wall time; "
              f"captured={stats.captured} DSP={stats.dsp_blocks}")
        print(f"IQ queue: high-water={stats.iq_high_water}/{args.iq_queue}, "
              f"dropped={stats.iq_dropped}")
        print(f"PCM queue: high-water={stats.pcm_high_water}/{args.pcm_queue}, "
              f"dropped={stats.pcm_dropped}, empty waits={stats.pcm_underruns}")
        if stats.rf_seconds:
            print(f"DSP time {stats.dsp_seconds:.2f}s / RF time "
                  f"{stats.rf_seconds:.2f}s "
                  f"({100 * stats.dsp_seconds / stats.rf_seconds:.1f}%)")
        print("Note: queue counters do not measure internal RTL USB sample loss.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
