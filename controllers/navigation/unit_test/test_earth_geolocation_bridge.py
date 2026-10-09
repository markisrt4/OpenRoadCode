"""Earth-origin permission is required before delivering ORC positions."""

import unittest
from unittest.mock import Mock

from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge


class EarthGeolocationBridgeTest(unittest.TestCase):
    def test_grants_only_earth_location_before_installing_bridge(self):
        client = Mock()
        client.version.return_value = {"webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/browser/test"}
        client.evaluate_earth.return_value = True
        bridge = EarthGeolocationBridge(client)
        self.assertTrue(bridge.install())
        self.assertTrue(bridge.install())
        client.command.assert_called_once()
        target, method, params = client.command.call_args.args
        self.assertEqual(target.web_socket_debugger_url, client.version.return_value["webSocketDebuggerUrl"])
        self.assertEqual(method, "Browser.grantPermissions")
        self.assertEqual(params, {"origin": "https://earth.google.com", "permissions": ["geolocation"]})

    def test_permission_failure_is_retried_and_does_not_claim_ready(self):
        client = Mock()
        client.version.return_value = {"webSocketDebuggerUrl": "ws://127.0.0.1:9224/browser"}
        client.command.side_effect = [RuntimeError("not ready"), {}]
        client.evaluate_earth.return_value = True
        bridge = EarthGeolocationBridge(client)
        self.assertFalse(bridge.install())
        client.evaluate_earth.assert_not_called()
        self.assertTrue(bridge.install())
        self.assertEqual(client.command.call_count, 2)

    def test_new_browser_session_gets_fresh_permission(self):
        client = Mock()
        client.version.side_effect = [
            {"webSocketDebuggerUrl": "ws://localhost/browser/first"},
            {"webSocketDebuggerUrl": "ws://localhost/browser/second"}]
        client.evaluate_earth.return_value = True
        bridge = EarthGeolocationBridge(client)
        self.assertTrue(bridge.install())
        self.assertTrue(bridge.install())
        self.assertEqual(client.command.call_count, 2)
