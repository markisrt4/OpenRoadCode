# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication tests for the Linux service-manager HTTP control plane."""

import unittest

from services.linux.systemd_service_manager_http import _authorized


class SystemdServiceManagerHttpTest(unittest.TestCase):
    def test_no_token_allows_local_mode_requests(self) -> None:
        self.assertTrue(_authorized(None, None))

    def test_configured_token_requires_bearer_header(self) -> None:
        self.assertFalse(_authorized(None, "secret"))
        self.assertFalse(_authorized("secret", "secret"))

    def test_configured_token_accepts_exact_bearer_value(self) -> None:
        self.assertTrue(_authorized("Bearer secret", "secret"))

    def test_configured_token_rejects_wrong_bearer_value(self) -> None:
        self.assertFalse(_authorized("Bearer wrong", "secret"))


if __name__ == "__main__":
    unittest.main()
