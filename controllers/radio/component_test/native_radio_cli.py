# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component-test console for the native multichannel SDR radio.

Examples:
  python -m controllers.radio.component_test.native_radio_cli --dry-run
  python -m controllers.radio.component_test.native_radio_cli --channel fm:104300000:wfm
  python -m controllers.radio.component_test.native_radio_cli --center 104300000 \
      --channel a:104100000:wfm --channel b:104500000:wfm --listen a
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict

from controllers.radio.dsp_performance_monitor import DspPerformanceMonitor

from controllers.radio.multi_mode_radio_receiver import MultiModeRadioReceiver, RadioChannel
from controllers.radio.native_radio_service import NativeRadioService
from controllers.radio.radio_audio_session import RadioAudioSession
from controllers.radio.recovering_radio_session import RecoveringRadioSession
from hardware_io.audio.pcm_playback_worker import PcmPlaybackWorker
from hardware_io.audio.sounddevice_pcm_output_adapter import SounddevicePcmOutputAdapter
from hardware_io.sdr.rtl_sdr_source import RtlSdrSource


def channel_arg(value: str) -> RadioChannel:
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("expected NAME:FREQUENCY_HZ:MODE")
    name, frequency, mode = parts
    if not name.strip() or not frequency.isdecimal() or int(frequency) <= 0:
        raise argparse.ArgumentTypeError("invalid channel name or frequency")
    if mode.lower() not in ("wfm", "nfm", "am"):
        raise argparse.ArgumentTypeError("mode must be wfm, nfm or am")
    return RadioChannel(name, int(frequency), mode.upper())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=channel_arg, action="append",
                        help="repeat NAME:FREQUENCY_HZ:MODE (default fm:104300000:wfm)")
    parser.add_argument("--center", type=int, default=None,
                        help="RF center Hz (default first channel frequency)")
    parser.add_argument("--gain", type=float, default=30.0,
                        help="RTL tuner manual gain dB (default 30; measured preferred FM setting)")
    parser.add_argument("--tuner-agc", action="store_true")
    parser.add_argument("--stereo", action="store_true",
                        help="enable experimental WFM stereo decoding and output")
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--listen", help="channel to play (default first channel)")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--volume", type=float, default=0.6)
    parser.add_argument("--audio-prime-ms", type=int, default=1000)
    parser.add_argument("--pcm-queue", type=int, default=32)
    parser.add_argument("--report-seconds", type=float, default=2.0)
    parser.add_argument("--warmup-seconds", type=float, default=5.0,
                        help="exclude first N seconds from steady throughput")
    parser.add_argument("--rf-warmup-seconds", type=float, default=2.0)
    parser.add_argument("--audio-prebuffer-ms", type=int, default=400)
    parser.add_argument("--reconnect-retries", type=int, default=5)
    parser.add_argument("--reconnect-delay", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and display configuration without SDR hardware")
    return parser


def configuration(args: argparse.Namespace, parser: argparse.ArgumentParser):
    channels = args.channel or [RadioChannel("fm", 104_300_000, "WFM")]
    center = args.center if args.center is not None else channels[0].frequency_hz
    if center <= 0 or args.seconds <= 0 or args.report_seconds <= 0 or args.warmup_seconds < 0:
        parser.error("center, seconds and report-seconds must be positive")
    if (args.device_index < 0 or args.pcm_queue < 1 or args.audio_prime_ms < 0
            or args.reconnect_retries < 0 or args.reconnect_delay < 0
            or args.rf_warmup_seconds < 0 or args.audio_prebuffer_ms < 0):
        parser.error("invalid device index, PCM queue size or audio prime")
    if not 0 <= args.volume <= 1:
        parser.error("volume must be between 0 and 1")
    listen = args.listen or channels[0].name
    if listen not in [c.name for c in channels]:
        parser.error("--listen must name a configured channel")
    if args.stereo and any(channel.mode.upper() != "WFM" for channel in channels):
        parser.error("--stereo currently requires WFM-only channels")
    receiver = MultiModeRadioReceiver(stereo_wfm=args.stereo)
    for channel in channels:
        try:
            receiver.add_channel(channel)
        except ValueError as exc:
            parser.error(str(exc))
        bandwidth = receiver.channels[-1].bandwidth_hz
        if abs(channel.frequency_hz - center) + bandwidth / 2 >= 1_200_000:
            parser.error(f"channel {channel.name} is outside 2.4 MSPS RF capture span")
    return receiver, center, listen


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    receiver, center, listen = configuration(args, parser)
    print(json.dumps({
        "center_hz": center,
        "sample_rate_hz": 2_400_000,
        "channels": [vars(channel) for channel in receiver.channels],
        "listen": None if args.no_audio else listen,
        "device_index": args.device_index,
        "stereo": args.stereo,
        "gain_db": None if args.tuner_agc else args.gain,
        "dry_run": args.dry_run,
        "rf_warmup_seconds": args.rf_warmup_seconds,
        "audio_prebuffer_ms": args.audio_prebuffer_ms,
    }, indent=2), flush=True)
    if args.dry_run:
        return 0

    def create_session():
        source = RtlSdrSource(device_index=args.device_index, acquisition_mode="async")
        service = NativeRadioService(
            source, receiver, center_frequency_hz=center,
            gain_db=None if args.tuner_agc else args.gain,
            rf_warmup_seconds=args.rf_warmup_seconds,
        )
        if args.no_audio:
            return service
        output = SounddevicePcmOutputAdapter(
            volume=args.volume, prime_ms=args.audio_prime_ms, latency="high",
            channels=2 if args.stereo else 1
        )
        playback = PcmPlaybackWorker(output, queue_blocks=args.pcm_queue,
                                     prebuffer_ms=args.audio_prebuffer_ms,
                                     channels=2 if args.stereo else 1)
        session = RadioAudioSession(service, playback)
        session.select_channel(listen)
        return session

    recovery = RecoveringRadioSession(
        create_session, max_retries=args.reconnect_retries,
        retry_delay_seconds=args.reconnect_delay,
    )
    started = time.monotonic()
    monitor = DspPerformanceMonitor(warmup_seconds=args.warmup_seconds)
    next_report = started + args.report_seconds
    exit_code = 0
    try:
        recovery.start()
        while time.monotonic() - started < args.seconds:
            previous = recovery.session
            previous_service = previous.radio if isinstance(previous, RadioAudioSession) else previous
            samples_before = previous_service.status.processed_iq_samples
            recovery.process_once()
            current = recovery.session
            if current is not previous:
                print(json.dumps({"recovery": asdict(recovery.status)}), flush=True)
                monitor = DspPerformanceMonitor(warmup_seconds=args.warmup_seconds)
                next_report = time.monotonic() + args.report_seconds
                continue
            session = current if isinstance(current, RadioAudioSession) else None
            service = session.radio if session is not None else current
            source = service.source
            if session is not None and session.playback.status.last_error:
                raise RuntimeError(f"audio playback failed: {session.playback.status.last_error}")
            processed_samples = service.status.processed_iq_samples - samples_before
            if processed_samples:
                monitor.record(samples=processed_samples, dsp_seconds=service.last_dsp_seconds)
            now = time.monotonic()
            if now >= next_report:
                elapsed = max(now - started, 1e-9)
                print(json.dumps({
                    "elapsed_s": round(elapsed, 2),
                    "iq_blocks": service.status.processed_blocks,
                    "iq_samples": service.status.processed_iq_samples,
                    "processing_msps": round(service.status.processed_iq_samples / elapsed / 1e6, 3),
                    "discontinuities": service.status.discontinuities,
                    "source": source.get_acquisition_stats(),
                    "dsp": asdict(monitor.snapshot()),
                    "rf_channels": {name: asdict(value) for name, value in receiver.telemetry.items()},
                    "rf_telemetry_note": "spectral peak-to-median contrast; not calibrated RF SNR",
                    "recovery": asdict(recovery.status),
                    "tuner": {
                        "requested_center_hz": center,
                        "reported_center_hz": source.get_center_frequency(),
                        "reported_sample_rate_hz": source.get_sample_rate(),
                        "pll_lock_status": "not_exposed_by_librtlsdr",
                    },
                    "audio": vars(session.playback.status) if session else None,
                }), flush=True)
                next_report = now + args.report_seconds
    except KeyboardInterrupt:
        print("Interrupted; stopping receiver.", flush=True)
    except Exception as exc:
        print(f"Receiver error: {exc}", flush=True)
        exit_code = 1
    finally:
        recovery.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
