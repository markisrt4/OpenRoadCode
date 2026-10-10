# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import unittest
from unittest.mock import Mock

from frontends.tui.destination_setup import run_destination_setup
from ui.navigation.destination_setup_request_handler_if import (
    DestinationSetupRequestHandlerIf, SavedDestination,
)
from ui.navigation.destination_setup_ui_if import DestinationSetupUiIf
from ui.navigation.map_ui_if import GeoPoint


def setup_flow(choices, texts, *, confirmed=True):
    handler = Mock(spec=DestinationSetupRequestHandlerIf)
    handler.current.return_value = None
    handler.search.return_value = ()
    dialog = Mock(spec=DestinationSetupUiIf)
    dialog.choose.side_effect = choices
    dialog.text.side_effect = texts
    dialog.confirm.return_value = confirmed
    return handler, dialog


class DestinationSetupPresentationTest(unittest.TestCase):
    def test_cancelled_drafts_never_save(self):
        for choices, texts in [([None], []), (["home", "done"], [None]),
                (["home", None, "done"], ["123 Main St"]),
                (["home", "manual", "done"], ["123 Main St", None]),
                (["home", "manual", "done"], ["123 Main St", "42.8", None])]:
            with self.subTest(choices=choices, texts=texts):
                handler, dialog = setup_flow(choices, texts)
                run_destination_setup(handler, dialog)
                handler.save.assert_not_called()

    def test_manual_coordinates_use_si_and_require_confirmation(self):
        handler, dialog = setup_flow(["work", "manual", "done"], ["456 Main St", "42.8", "-83"])
        run_destination_setup(handler, dialog)
        destination = handler.save.call_args.args[0]
        self.assertEqual(destination.key, "work")
        self.assertEqual(destination.position, GeoPoint(math.radians(42.8), math.radians(-83)))
        dialog.confirm.assert_called_once()

    def test_declined_confirmation_never_saves(self):
        handler, dialog = setup_flow(["home", "manual", "done"], ["123 Main St", "42", "-83"], confirmed=False)
        run_destination_setup(handler, dialog)
        handler.save.assert_not_called()

    def test_candidate_selection_saves_confirmed_match(self):
        handler, dialog = setup_flow(["home", "1", "done"], ["Main St"])
        candidates = (SavedDestination("home", "Home", "One", GeoPoint(0.5, -1)),
                      SavedDestination("home", "Home", "Two", GeoPoint(0.6, -1)))
        handler.search.return_value = candidates
        run_destination_setup(handler, dialog)
        handler.save.assert_called_once_with(candidates[1])

    def test_invalid_coordinates_report_error_without_saving(self):
        for latitude in ("91", "nan", "invalid"):
            with self.subTest(latitude=latitude):
                handler, dialog = setup_flow(["home", "manual", "done"], ["123 Main St", latitude, "-83"])
                run_destination_setup(handler, dialog)
                handler.save.assert_not_called()
                dialog.notify.assert_called_once()

    def test_search_failure_allows_manual_coordinates(self):
        handler, dialog = setup_flow(["home", "manual", "done"], ["123 Main St", "42", "-83"])
        handler.search.side_effect = RuntimeError("Database unavailable")
        run_destination_setup(handler, dialog)
        handler.save.assert_called_once()

    def test_failed_save_reports_error_and_returns_to_menu(self):
        handler, dialog = setup_flow(["home", "manual", "done"], ["123 Main St", "42", "-83"])
        handler.save.side_effect = OSError("disk unavailable")
        run_destination_setup(handler, dialog)
        dialog.notify.assert_called_once_with("Destination not saved", "disk unavailable")
