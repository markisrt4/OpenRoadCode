# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Short-lived browser approval sessions for service-manager clients."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import secrets
import time

from services.common.service_manager_pairing import ServiceManagerPairing


class BrowserPairingConsumedError(RuntimeError):
    """Raised when credentials have already been issued for a browser session."""


@dataclass
class BrowserPairingSession:
    session_id: str
    client_name: str
    expires_at: float
    poll_token_hash: str
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

    def begin(self, client_name: str) -> tuple[BrowserPairingSession, str]:
        self._prune_expired()
        name = client_name.strip()
        if not name:
            raise ValueError("client_name is required")
        poll_token = secrets.token_urlsafe(32)
        session = BrowserPairingSession(
            session_id=secrets.token_urlsafe(24),
            client_name=name,
            expires_at=time.time() + self._ttl_seconds,
            poll_token_hash=hashlib.sha256(poll_token.encode("utf-8")).hexdigest(),
        )
        self._sessions[session.session_id] = session
        return session, poll_token

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

    def complete(self, session_id: str, poll_token: str) -> tuple[str, str] | None:
        session = self.get(session_id)
        if session is None or not self.poll_authorized(session, poll_token):
            raise PermissionError("invalid browser pairing poll token")
        if session.consumed:
            raise BrowserPairingConsumedError("browser pairing session already consumed")
        if not session.approved:
            return None
        session.consumed = True
        return self._pairing.issue_client(session.client_name)

    def _prune_expired(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now > session.expires_at
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

    @staticmethod
    def poll_authorized(session: BrowserPairingSession, poll_token: str) -> bool:
        supplied_hash = hashlib.sha256(poll_token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(supplied_hash, session.poll_token_hash)
