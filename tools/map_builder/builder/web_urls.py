# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Validation for website links supplied by map data."""
from urllib.parse import urlsplit


def valid_website(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            return None
        parsed.port  # Reject malformed port numbers.
    except ValueError:
        return None
    return value
