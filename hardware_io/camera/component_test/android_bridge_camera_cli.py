# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Check the bridge listener/backend, optionally decoding a few live frames."""

import argparse
import sys

from hardware_io.camera.android_bridge_camera import AndroidBridgeCamera


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge-url', default='http://127.0.0.1:8767')
    parser.add_argument('--check-only', action='store_true',
                        help='Check status and decoder support without connecting to /video')
    parser.add_argument('--frames', type=int, default=5,
                        help='Decoded frame count; close Vision/ffplay first (one bridge video client)')
    args = parser.parse_args()
    if args.frames <= 0:
        parser.error('--frames must be positive')
    camera = AndroidBridgeCamera(args.bridge_url)
    try:
        camera.check_status()
        print('Bridge camera: streaming H.264/MPEG-TS')
        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError('OpenCV is unavailable in this Python environment') from exc
        registry = getattr(cv2, 'videoio_registry', None)
        if (registry is None or not hasattr(registry, 'hasBackend')
                or not registry.hasBackend(cv2.CAP_FFMPEG)
                or not hasattr(cv2, 'CAP_PROP_OPEN_TIMEOUT_MSEC')
                or not hasattr(cv2, 'CAP_PROP_READ_TIMEOUT_MSEC')):
            raise RuntimeError('OpenCV needs an FFmpeg backend with stream timeout support')
        print(f'OpenCV {cv2.__version__}: FFmpeg decoder available')
        if args.check_only:
            return 0
        camera.open()
        for _ in range(args.frames):
            frame = camera.read()
            height, width = frame.image.shape[:2]
            print(f'Frame {frame.sequence}: {width}x{height} BGR')
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f'Camera check failed: {exc}', file=sys.stderr)
        return 1
    finally:
        camera.close()


if __name__ == '__main__':
    raise SystemExit(main())
