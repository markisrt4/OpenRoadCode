from __future__ import annotations

import unittest

from apps.carUi.panels.lighting_panel import LightingPanel


class _Widget:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}

    def configure(self, **options: str) -> None:
        self.options.update(options)


class _Panel:
    _controls_enabled = False
    _brightness_after_id = None
    _colors = {"disabled_control": "#333333"}

    def __init__(self) -> None:
        self.button = _Widget()
        self.combo = _Widget()
        self._control_widgets = [
            (self.button, "normal", "#123456"),
            (self.combo, "readonly", None),
        ]


class LightingPanelControlsTest(unittest.TestCase):
    def test_controls_enable_only_with_their_registered_active_state(self) -> None:
        panel = _Panel()

        LightingPanel._set_controls_enabled(panel, False, force=True)
        self.assertEqual("disabled", panel.button.options["state"])
        self.assertEqual("#333333", panel.button.options["background"])
        self.assertEqual("disabled", panel.combo.options["state"])

        LightingPanel._set_controls_enabled(panel, True)
        self.assertEqual("normal", panel.button.options["state"])
        self.assertEqual("#123456", panel.button.options["background"])
        self.assertEqual("readonly", panel.combo.options["state"])


if __name__ == "__main__":
    unittest.main()
