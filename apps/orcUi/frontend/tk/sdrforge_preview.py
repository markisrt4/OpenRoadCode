# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-free SDRForge screen preview: python -m apps.orcUi.frontend.tk.sdrforge_preview."""
from __future__ import annotations

import math
import tkinter as tk

from apps.orcUi.frontend.tk.sdrforge_receiver_view import SdrForgeReceiverView
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode


def main() -> None:
    root = tk.Tk()
    root.title("OpenRoadCode | SDRForge preview")
    root.geometry("1280x720")
    view = SdrForgeReceiverView(root, theme=theme_bundle(ThemeMode.DARK))
    view.pack(fill=tk.BOTH, expand=True)
    view.set_station(frequency_hz=104_300_000, name="WOMC",
                     radio_text="Station information appears here", stereo=True)
    view.set_presets((("WOMC", 104_300_000), ("WELR", 94_700_000),
                      ("WDZH", 98_700_000), ("WDET", 101_100_000)),
                     on_tune=lambda hz: view.set_station(frequency_hz=hz))
    frame = 0

    def refresh() -> None:
        nonlocal frame
        frame += 1
        values = [
            0.08 + 0.04 * math.sin(i * 0.27 + frame * 0.05)
            + 0.8 * math.exp(-((i - 128) / 13) ** 2)
            + 0.28 * math.exp(-((i - 58) / 4) ** 2)
            for i in range(256)
        ]
        view.set_spectrum(values)
        root.after(120, refresh)

    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
