# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Short-lived browser approval sessions for service-manager clients."""

from __future__ import annotations

from dataclasses import dataclass
import secrets
import time

from services.common.service_manager_pairing import ServiceManagerPairing


@dataclass
class BrowserPairingSession:
    session_id: str
    client_name: str
    expires_at: float
    approved: bool = False
    consumed: bool = False


class ServiceManagerBrowserPairing:
    """Create browser-approved client credentials without exposing the admin token."""

    def __init__(
        self,
        pairing: ServiceManagerPairing,
        ttl_seconds: float = 300.0,
    ) -> None:
        self._pairing = pairing
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, BrowserPairingSession] = {}

    def begin(self, client_name: str) -> BrowserPairingSession:
        name = client_name.strip()
        if not name:
            raise ValueError("client_name is required")
        session = BrowserPairingSession(
            session_id=secrets.token_urlsafe(24),
            client_name=name,
            expires_at=time.time() + self._ttl_seconds,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> BrowserPairingSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() > session.expires_at:
            self._sessions.pop(session_id, None)
            return None
        return session

    def approve(self, session_id: str) -> bool:
        session = self.get(session_id)
        if session is None or session.consumed:
            return False
        session.approved = True
        return True

    def complete(self, session_id: str) -> tuple[str, str] | None:
        session = self.get(session_id)
        if session is None or not session.approved or session.consumed:
            return None
        session.consumed = True
        return self._pairing.issue_client(session.client_name)
