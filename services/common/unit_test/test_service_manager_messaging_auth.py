# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for SMS-specific authorization policy."""

from __future__ import annotations

import unittest

from services.common.service_manager_messaging_auth import messaging_authorized


class MessagingAuthorizationTest(unittest.TestCase):
    def test_disabled_denies_even_valid_token(self) -> None:
        self.assertFalse(messaging_authorized("Bearer sms-secret", enabled=False, messaging_token="sms-secret"))

    def test_localhost_does_not_bypass_authentication(self) -> None:
        self.assertFalse(messaging_authorized(None, enabled=True, messaging_token="sms-secret"))

    def test_rejects_missing_or_invalid_bearer(self) -> None:
        for header in ("", "Basic sms-secret", "Bearer ", "Bearer wrong", "Bearer sms-secret "):
            with self.subTest(header=header):
                self.assertFalse(messaging_authorized(header, enabled=True, messaging_token="sms-secret"))

    def test_explicit_messaging_token_is_accepted(self) -> None:
        self.assertTrue(messaging_authorized("Bearer sms-secret", enabled=True, messaging_token="sms-secret"))

    def test_service_manager_pairing_alone_is_insufficient(self) -> None:
        self.assertFalse(messaging_authorized(
            "Bearer paired", enabled=True, messaging_token=None,
            paired_token_authorized=lambda token: token == "paired",
        ))

    def test_paired_client_requires_separate_sms_grant(self) -> None:
        self.assertFalse(messaging_authorized(
            "Bearer paired", enabled=True, messaging_token=None,
            paired_token_authorized=lambda token: token == "paired",
            paired_client_granted=lambda token: False,
        ))
        self.assertTrue(messaging_authorized(
            "Bearer paired", enabled=True, messaging_token=None,
            paired_token_authorized=lambda token: token == "paired",
            paired_client_granted=lambda token: token == "paired",
        ))


if __name__ == "__main__":
    unittest.main()
