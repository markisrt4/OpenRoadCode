# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live preview for a V4L2 camera.

Run from the repository root, for example:

    python -m hardware_io.camera.component_test.camera_preview

Press q or Escape to exit.
"""

from __future__ import annotations

import argparse
import time

from hardware_io.camera import V4L2Camera


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview an OpenRoadCode V4L2 camera")
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--format", default="MJPG", dest="pixel_format")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    camera = V4L2Camera(
        args.device,
        width=args.width,
        height=args.height,
        fps=args.fps,
        pixel_format=args.pixel_format,
    )

    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise SystemExit("Install OpenCV first: sudo apt install python3-opencv") from exc

    title = "OpenRoadCode Camera Preview"
    frames = 0
    started = time.monotonic()

    try:
        with camera:
            print(
                f"[camera] {args.device} {args.width}x{args.height} "
                f"@ {args.fps:g} fps {args.pixel_format}"
            )
            print("[camera] press q or Escape to exit")

            while True:
                frame = camera.read()
                frames += 1

                elapsed = max(time.monotonic() - started, 1e-6)
                measured_fps = frames / elapsed
                cv2.putText(
                    frame.image,
                    f"OpenRoadCode  LIVE  {measured_fps:4.1f} fps",
                    (24, 44),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(title, frame.image)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
    finally:
        camera.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
