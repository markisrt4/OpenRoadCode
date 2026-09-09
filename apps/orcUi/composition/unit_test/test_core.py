# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for shell/map/state-ingress composition."""

import unittest
from unittest.mock import Mock, patch

from apps.orcUi.composition.core import CoreComposition, create_core_composition


class CoreCompositionTest(unittest.TestCase):
    def test_lifecycle_starts_ingress_and_closes_ingress_before_map(self) -> None:
        app = Mock()
        map_runtime = Mock()
        ingress = Mock()
        core = CoreComposition(app=app, map_runtime=map_runtime, state_ingress=ingress)

        core.start()
        core.close()

        ingress.start.assert_called_once_with()
        ingress.close.assert_called_once_with()
        map_runtime.stop.assert_called_once_with()

    @patch("apps.orcUi.composition.core.StateIngressRuntime")
    @patch("apps.orcUi.composition.core.OrcUiApp")
    @patch("apps.orcUi.composition.core.MapRuntime")
    def test_factory_injects_map_runtime_and_ui_state_sinks(
        self,
        map_runtime_type: Mock,
        app_type: Mock,
        ingress_type: Mock,
    ) -> None:
        map_runtime = map_runtime_type.return_value
        app = app_type.return_value

        core = create_core_composition()

        app_type.assert_called_once_with(map_runtime=map_runtime)
        ingress_type.assert_called_once_with(
            schedule_ui=app.schedule_ui_callback,
            apply_vehicle_state=app.apply_vehicle_state,
            apply_position_state=app.apply_position_state,
            apply_attitude_state=app.apply_attitude_state,
        )
        self.assertIs(core.app, app)
        self.assertIs(core.map_runtime, map_runtime)
        self.assertIs(core.state_ingress, ingress_type.return_value)


if __name__ == "__main__":
    unittest.main()
