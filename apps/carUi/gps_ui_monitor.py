from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional


class GPSUIMonitor:
    def __init__(
        self,
        root: tk.Misc,
        get_gps_device: Callable[[], object | None],
        set_location_text: Callable[[str], None],
    ) -> None:
        self.root = root
        self.get_gps_device = get_gps_device
        self.set_location_text = set_location_text
        self._after_id: Optional[str] = None

    def start(self, interval_ms: int = 1000) -> None:
        self.stop()
        self._poll(interval_ms)

    def stop(self) -> None:
        if self._after_id is None:
            return

        try:
            self.root.after_cancel(self._after_id)
        except Exception:
            pass

        self._after_id = None

    def _poll(self, interval_ms: int) -> None:
        gps_device = self.get_gps_device()

        if gps_device is None:
            self.set_location_text("🌎 lat.--, lon.--")
        else:
            try:
                pos = gps_device.position()
                if pos.get("fix") and pos.get("lat") is not None and pos.get("lon") is not None:
                    self.set_location_text(
                        f"🌎 lat.{float(pos['lat']):.4f}, lon.{float(pos['lon']):.4f}"
                    )
                else:
                    self.set_location_text("🌎 GPS searching...")
            except Exception:
                self.set_location_text("🌎 GPS error")

        self._after_id = self.root.after(
            interval_ms,
            lambda: self._poll(interval_ms),
        )
