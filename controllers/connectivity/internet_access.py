# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""A bounded internet reachability check; it does not measure signal strength."""
import urllib.request


def internet_reachable() -> bool:
    try:
        request = urllib.request.Request(
            'https://connectivitycheck.gstatic.com/generate_204', method='HEAD',
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 204
    except (OSError, ValueError):
        return False
