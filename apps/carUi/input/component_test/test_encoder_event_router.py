from __future__ import annotations

import unittest
from collections.abc import Callable

from apps.carUi.input import EncoderEventRouter, PanelEncoderCallbacks


class FakeRoot:
    def __init__(self) -> None:
        self.callbacks: dict[str, Callable[[], None]] = {}
        self._next_id = 0

    def after(self, _delay_ms: int, callback: Callable[[], None]) -> str:
        self._next_id += 1
        after_id = f"after-{self._next_id}"
        self.callbacks[after_id] = callback
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self.callbacks.pop(after_id, None)

    def run_next(self) -> None:
        after_id = next(iter(self.callbacks))
        callback = self.callbacks.pop(after_id)
        callback()


class FakeEncoder:
    def __init__(self, *, start_error: Exception | None = None) -> None:
        self.is_running = False
        self.start_error = start_error
        self.poll_count = 0
        self.rotated: Callable[[int], None] | None = None
        self.button_pressed: Callable[[], None] | None = None
        self.button_released: Callable[[], None] | None = None

    def start(
        self,
        rotated: Callable[[int], None],
        button_pressed: Callable[[], None] | None = None,
        button_released: Callable[[], None] | None = None,
    ) -> None:
        if self.start_error is not None:
            raise self.start_error

        self.is_running = True
        self.rotated = rotated
        self.button_pressed = button_pressed
        self.button_released = button_released

    def stop(self) -> None:
        self.is_running = False

    def poll(self) -> None:
        self.poll_count += 1


class EncoderEventRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = FakeRoot()
        self.encoders = [FakeEncoder(), FakeEncoder(), FakeEncoder()]
        self.volume_events: list[str] = []
        self.volume_button_events: list[str] = []
        self.router = EncoderEventRouter(
            root=self.root,
            encoders=self.encoders,
            volume_encoder_index=0,
            volume_up=lambda: self.volume_events.append("up"),
            volume_down=lambda: self.volume_events.append("down"),
            volume_button_pressed=(
                lambda: self.volume_button_events.append("pressed")
            ),
        )

    def tearDown(self) -> None:
        self.router.stop()

    def test_volume_encoder_is_global_and_honors_step_count(self) -> None:
        panel_events: list[tuple[int, int]] = []
        self.router.set_panel_callbacks(
            PanelEncoderCallbacks(rotated=lambda *event: panel_events.append(event))
        )
        self.router.start()

        self.encoders[0].rotated(2)  # type: ignore[misc]
        self.encoders[0].rotated(-1)  # type: ignore[misc]
        self.root.run_next()

        self.assertEqual(["up", "up", "down"], self.volume_events)
        self.assertEqual([], panel_events)

    def test_volume_button_is_routed_to_global_callback(self) -> None:
        panel_pressed: list[int] = []
        self.router.set_panel_callbacks(
            PanelEncoderCallbacks(button_pressed=panel_pressed.append)
        )
        self.router.start()

        self.encoders[0].button_pressed()  # type: ignore[misc]
        self.root.run_next()

        self.assertEqual(["pressed"], self.volume_button_events)
        self.assertEqual([], panel_pressed)

    def test_context_encoders_are_forwarded_to_active_panel(self) -> None:
        rotations: list[tuple[int, int]] = []
        pressed: list[int] = []
        released: list[int] = []
        self.router.set_panel_callbacks(
            PanelEncoderCallbacks(
                rotated=lambda *event: rotations.append(event),
                button_pressed=pressed.append,
                button_released=released.append,
            )
        )
        self.router.start()

        self.encoders[1].rotated(-2)  # type: ignore[misc]
        self.encoders[2].button_pressed()  # type: ignore[misc]
        self.encoders[2].button_released()  # type: ignore[misc]
        self.root.run_next()

        self.assertEqual([(0, -2)], rotations)
        self.assertEqual([1], pressed)
        self.assertEqual([1], released)

    def test_queued_event_does_not_leak_into_next_panel(self) -> None:
        first_panel: list[tuple[int, int]] = []
        second_panel: list[tuple[int, int]] = []
        self.router.set_panel_callbacks(
            PanelEncoderCallbacks(rotated=lambda *event: first_panel.append(event))
        )
        self.router.start()

        self.encoders[1].rotated(1)  # type: ignore[misc]
        self.router.set_panel_callbacks(
            PanelEncoderCallbacks(rotated=lambda *event: second_panel.append(event))
        )
        self.root.run_next()

        self.assertEqual([], first_panel)
        self.assertEqual([], second_panel)

    def test_volume_index_must_be_configured(self) -> None:
        with self.assertRaisesRegex(ValueError, "volume_encoder_index"):
            EncoderEventRouter(
                root=self.root,
                encoders=[FakeEncoder()],
                volume_encoder_index=1,
                volume_up=lambda: None,
                volume_down=lambda: None,
            )

    def test_unavailable_encoder_does_not_prevent_others_starting(self) -> None:
        encoders = [
            FakeEncoder(),
            FakeEncoder(start_error=ValueError("No I2C device at address: 0x38")),
            FakeEncoder(),
        ]
        router = EncoderEventRouter(
            root=self.root,
            encoders=encoders,
            volume_encoder_index=0,
            volume_up=lambda: None,
            volume_down=lambda: None,
        )

        try:
            router.start()
            self.root.run_next()

            self.assertTrue(router.is_running)
            self.assertTrue(encoders[0].is_running)
            self.assertFalse(encoders[1].is_running)
            self.assertTrue(encoders[2].is_running)
            self.assertEqual(1, encoders[0].poll_count)
            self.assertEqual(0, encoders[1].poll_count)
            self.assertEqual(1, encoders[2].poll_count)
        finally:
            router.stop()


if __name__ == "__main__":
    unittest.main()
