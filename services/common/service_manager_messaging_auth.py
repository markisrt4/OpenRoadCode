# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authorization boundary for sensitive messaging operations.

Service-manager pairing grants ordinary runtime control, not SMS access.
Messaging must be explicitly enabled and must require a bearer credential,
including for requests originating on localhost.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable

from services.common.service_manager_auth import authorized


def messaging_authorized(
    authorization_header: str | None,
    *,
    enabled: bool,
    messaging_token: str | None,
    paired_token_authorized: Callable[[str], bool] | None = None,
    paired_client_granted: Callable[[str], bool] | None = None,
) -> bool:
    """Authorize messaging without inheriting service-manager localhost bypass.

    A dedicated messaging token may be used for an explicitly configured
    deployment. Alternatively, a paired client must also have an explicit
    messaging grant, checked by the caller. Pairing alone is insufficient.
    """
    if not enabled or not authorization_header:
        return False
    scheme, separator, supplied = authorization_header.partition(" ")
    if not separator or scheme != "Bearer" or not supplied or supplied != supplied.strip():
        return False
    if messaging_token and authorized(authorization_header, messaging_token):
        return True
    if paired_token_authorized is None or paired_client_granted is None:
        return False
    return bool(paired_token_authorized(supplied) and paired_client_granted(supplied))
