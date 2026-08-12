# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PkcePair:
    """
    PKCE verifier and challenge pair.
    """

    verifier: str
    challenge: str
    challenge_method: str = "S256"


def create_pkce_pair() -> PkcePair:
    """
    Create a PKCE verifier and SHA-256 challenge.
    """
    verifier = secrets.token_urlsafe(64)[:128]

    digest = hashlib.sha256(
        verifier.encode("ascii")
    ).digest()

    challenge = (
        base64.urlsafe_b64encode(digest)
        .decode("ascii")
        .rstrip("=")
    )

    return PkcePair(
        verifier=verifier,
        challenge=challenge,
    )
