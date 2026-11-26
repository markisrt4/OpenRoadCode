# SPDX-License-Identifier: MIT
"""Install the pinned Vision model for offline inference."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from urllib.request import urlopen

from controllers.computer_vision.model_readiness import vision_model_path

MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
MODEL_SHA256 = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
MODEL_SIZE = 5_613_764


def main() -> int:
    """Verify the local asset or atomically install a verified download."""
    target = vision_model_path()
    try:
        if target.is_file() and target.stat().st_size == MODEL_SIZE:
            if hashlib.sha256(target.read_bytes()).hexdigest() == MODEL_SHA256:
                print(f"[+] Vision model already verified: {target}")
                return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        print("[*] Downloading pinned YOLO model weights...")
        with urlopen(MODEL_URL, timeout=60) as response:
            weights = response.read(MODEL_SIZE + 1)
        if len(weights) != MODEL_SIZE or hashlib.sha256(weights).hexdigest() != MODEL_SHA256:
            raise ValueError("downloaded weights failed verification")
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            try:
                temporary.write(weights)
                temporary.close()
                Path(temporary.name).replace(target)
            finally:
                Path(temporary.name).unlink(missing_ok=True)
    except (OSError, ValueError, HTTPException) as exc:
        print(f"[!] Unable to install Vision model at {target}: {exc}", file=sys.stderr)
        return 1
    print(f"[+] Vision model ready for offline use: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
