# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for top-level ORC UI composition ownership."""

import unittest
from unittest.mock import Mock, patch

from apps.orcUi.composition.application import OrcUiComposition, create_orc_ui_composition


class OrcUiCompositionTest(unittest.TestCase):
    def test_run_starts_deferred_runtime_and_closes_owned_resources(self) -> None:
        app = Mock()
        runtime = Mock()
        media = Mock()
        composition = OrcUiComposition(app=app, runtime=runtime, media=media)

        composition.run()

        app.schedule_ui_callback.assert_called_once_with(1500, runtime.start_background_apps)
        app.run.assert_called_once_with()
        media.close.assert_called_once_with()
        runtime.close.assert_called_once_with()

    def test_run_closes_resources_when_app_raises(self) -> None:
        app = Mock()
        app.run.side_effect = RuntimeError("boom")
        runtime = Mock()
        media = Mock()
        composition = OrcUiComposition(app=app, runtime=runtime, media=media)

        with self.assertRaisesRegex(RuntimeError, "boom"):
            composition.run()

        media.close.assert_called_once_with()
        runtime.close.assert_called_once_with()

    @patch("apps.orcUi.composition.application.configure_media")
    @patch("apps.orcUi.composition.application.configure_games")
    @patch("apps.orcUi.composition.application.configure_radio")
    @patch("apps.orcUi.composition.application.OrcUiApp")
    @patch("apps.orcUi.composition.application.create_orc_ui_application_runtime")
    def test_factory_composes_every_top_level_feature(
        self,
        create_runtime: Mock,
        app_type: Mock,
        configure_radio: Mock,
        configure_games: Mock,
        configure_media: Mock,
    ) -> None:
        runtime = create_runtime.return_value
        app = app_type.return_value
        media = configure_media.return_value

        composition = create_orc_ui_composition()

        self.assertIs(composition.runtime, runtime)
        self.assertIs(composition.app, app)
        self.assertIs(composition.media, media)
        configure_radio.assert_called_once_with(app, runtime)
        configure_games.assert_called_once_with(app)
        configure_media.assert_called_once_with(app, runtime)

    @patch("apps.orcUi.composition.application.configure_radio")
    @patch("apps.orcUi.composition.application.OrcUiApp")
    @patch("apps.orcUi.composition.application.create_orc_ui_application_runtime")
    def test_factory_closes_runtime_when_composition_fails(
        self,
        create_runtime: Mock,
        app_type: Mock,
        configure_radio: Mock,
    ) -> None:
        runtime = create_runtime.return_value
        configure_radio.side_effect = RuntimeError("bad wiring")

        with self.assertRaisesRegex(RuntimeError, "bad wiring"):
            create_orc_ui_composition()

        runtime.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
