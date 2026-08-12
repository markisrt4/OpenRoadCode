# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for frontend and screen contract boundaries."""

import unittest

from ui import ScreenId, ScreenNavigatorIf, ScreenUiIf, ScreenUiStub, UiIf
from ui.lighting import (
    LightingRequestHandlerIf,
    LightingRequestHandlerStub,
    LightingUiIf,
    LightingUiStub,
)
from ui.navigation import (
    GroundTrackUiIf,
    NavigationRequestHandlerIf,
    NavigationRequestHandlerStub,
)
from ui.radio import (
    RadioApplicationRequestHandlerIf,
    RadioApplicationRequestHandlerStub,
    RadioRefreshRequestHandlerIf,
    RadioRefreshRequestHandlerStub,
)
from ui.system import (
    StatusMessage,
    StatusUiIf,
    StatusUiStub,
    SystemDiagnosticsUiIf,
    SystemDiagnosticsUiStub,
    TopBarUiIf,
    TopBarUiStub,
)
from ui.ui_stub import UiStub


class UiContractTests(unittest.TestCase):
    def test_frontend_stub_implements_frontend_lifecycle(self) -> None:
        frontend = UiStub()

        self.assertIsInstance(frontend, UiIf)
        self.assertTrue(frontend.initialize())
        frontend.run()
        frontend.shutdown()

    def test_domain_ui_contract_has_no_frontend_lifecycle(self) -> None:
        self.assertNotIn(UiIf, StatusUiIf.__mro__)
        self.assertNotIsInstance(StatusUiStub(), UiIf)

    def test_status_contract_accepts_concise_and_structured_values(self) -> None:
        status_ui = StatusUiStub()

        status_ui.set_status("Ready")
        status_ui.set_status(StatusMessage("Connected"))
        status_ui.set_status(None)

    def test_screen_identifier_is_normalized(self) -> None:
        self.assertEqual(ScreenId(" diagnostics ").value, "diagnostics")

    def test_screen_identifier_rejects_empty_values(self) -> None:
        with self.assertRaises(ValueError):
            ScreenId("   ")

    def test_screen_contract_exposes_lifecycle_and_actions(self) -> None:
        self.assertTrue(
            {"screen_id", "show", "hide", "handle_ui_action"}
            <= ScreenUiIf.__abstractmethods__
        )
        self.assertIsInstance(ScreenUiStub(), ScreenUiIf)

    def test_navigator_contract_exposes_navigation_state(self) -> None:
        self.assertTrue(
            {"active_screen_id", "show_screen", "go_back", "go_home"}
            <= ScreenNavigatorIf.__abstractmethods__
        )

    def test_top_bar_contract_exposes_shell_and_status_behavior(self) -> None:
        self.assertTrue(
            {
                "set_title",
                "set_back_action",
                "show_back_button",
                "hide_back_button",
                "invoke_back_action",
                "set_frequency_text",
                "set_location_text",
            }
            <= TopBarUiIf.__abstractmethods__
        )

    def test_ground_track_contract_keeps_course_separate_from_heading(self) -> None:
        self.assertEqual(
            GroundTrackUiIf.__abstractmethods__,
            {"set_ground_speed", "set_course_over_ground"},
        )

    def test_navigation_requests_cover_user_control_actions(self) -> None:
        self.assertEqual(
            NavigationRequestHandlerIf.__abstractmethods__,
            {"request_stationary_calibration", "request_heading_reset"},
        )

    def test_remaining_domain_contracts_export_concrete_stubs(self) -> None:
        self.assertIsInstance(LightingUiStub(), LightingUiIf)
        self.assertIsInstance(
            LightingRequestHandlerStub(),
            LightingRequestHandlerIf,
        )
        self.assertIsInstance(
            NavigationRequestHandlerStub(),
            NavigationRequestHandlerIf,
        )
        self.assertIsInstance(
            RadioApplicationRequestHandlerStub(),
            RadioApplicationRequestHandlerIf,
        )
        self.assertIsInstance(
            RadioRefreshRequestHandlerStub(),
            RadioRefreshRequestHandlerIf,
        )
        self.assertIsInstance(SystemDiagnosticsUiStub(), SystemDiagnosticsUiIf)
        self.assertIsInstance(TopBarUiStub(), TopBarUiIf)


if __name__ == "__main__":
    unittest.main()
