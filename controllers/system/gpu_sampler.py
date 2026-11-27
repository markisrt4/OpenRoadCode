# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only GPU busy sampling; unavailable is never represented as idle."""

from pathlib import Path


class GpuSampler:
    """Qualcomm KGSL interval counter, as exposed to unprivileged Termux."""

    def __init__(self, path: Path = Path("/sys/class/kgsl/kgsl-3d0/gpubusy")):
        self._path = path

    def sample(self) -> tuple[float | None, str]:
        try:
            values = self._path.read_text(encoding="ascii").split()
            if len(values) < 2:
                return None, "invalid KGSL counter"
            busy, total = int(values[0]), int(values[1])
            if total <= 0:
                return None, "GPU counter idle or unavailable"
            if busy < 0 or busy > total:
                return None, "invalid KGSL busy/total values"
            return round(100.0 * busy / total, 2), "Qualcomm KGSL gpubusy"
        except (OSError, ValueError, UnicodeError):
            return None, "GPU utilization counter unavailable"
