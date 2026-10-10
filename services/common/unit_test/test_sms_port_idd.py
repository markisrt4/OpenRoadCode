# SPDX-License-Identifier: MIT
"""Keep the SMS gateway port distinct from Android host actions."""

from pathlib import Path
import unittest


class SmsPortIddTest(unittest.TestCase):
    def test_sms_port_registered_and_separate(self):
        root = Path(__file__).resolve().parents[3]
        idd = (root / "docs" / "ethernet_idd.md").read_text()
        android_actions = next(line for line in idd.splitlines() if line.startswith("| 8772 |"))
        sms_gateway = next(line for line in idd.splitlines() if line.startswith("| 8773 |"))
        self.assertIn("host actions", android_actions.lower())
        self.assertIn("sms gateway", sms_gateway.lower())
        proxy = (root / "services" / "common" / "service_manager_sms_proxy.py").read_text()
        self.assertIn('HTTPConnection("127.0.0.1", 8773', proxy)


if __name__ == "__main__":
    unittest.main()
