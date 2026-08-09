"""Tests for adapting lighting controllers to generic lighting UI contracts."""

import unittest

from controllers.lighting import DummyLightingController, LightingPresenter
from ui.lighting import LightingState, LightingUiIf


class RecordingLightingUi(LightingUiIf):
    def __init__(self) -> None:
        self.states: list[LightingState | None] = []

    def set_lighting_state(self, state: LightingState | None) -> None:
        self.states.append(state)

    def set_lighting_request_handler(self, handler) -> None:
        pass


class LightingPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = DummyLightingController()
        self.lighting_ui = RecordingLightingUi()
        self.presenter = LightingPresenter(
            self.backend,
            self.lighting_ui,
            dispatch=lambda callback: callback(),
        )

    def test_connect_publishes_connected_state(self) -> None:
        self.presenter.connect()

        self.assertTrue(self.lighting_ui.states[-1].connected)  # type: ignore[union-attr]

    def test_requests_update_backend_and_publish_state(self) -> None:
        self.presenter.connect()
        self.presenter.request_power(True)
        self.presenter.request_brightness(35)
        self.presenter.request_pattern(12)

        state = self.lighting_ui.states[-1]
        self.assertTrue(state.power_enabled)  # type: ignore[union-attr]
        self.assertEqual(state.brightness_percent, 35)  # type: ignore[union-attr]
        self.assertEqual(state.pattern_index, 12)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
