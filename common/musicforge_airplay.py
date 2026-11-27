"""Resolve the MusicForge charts endpoint from per-user configuration."""

import os
from urllib.parse import urlsplit

from common.xdg_paths import openroadcode_config_dir

DEFAULT_AIRPLAY_URL = "http://127.0.0.1:8000"


def validate_airplay_url(value: str) -> str:
    """Accept an HTTP base URL without embedded credentials or query parameters."""
    value = value.strip().rstrip("/")
    endpoint = urlsplit(value)
    if (
        endpoint.scheme not in {"http", "https"}
        or not endpoint.hostname
        or endpoint.username is not None
        or endpoint.query
        or endpoint.fragment
        or any(character.isspace() for character in value)
    ):
        raise ValueError("Enter an HTTP or HTTPS API base URL without credentials.")
    # Accessing port checks its syntax and range.
    if endpoint.port == 0:
        raise ValueError("The API port must be greater than zero.")
    return value


def musicforge_airplay_url() -> str:
    override = os.environ.get("MUSICFORGE_AIRPLAY_URL")
    if override:
        return override
    try:
        return validate_airplay_url(
            openroadcode_config_dir("musicforge-airplay-url").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return DEFAULT_AIRPLAY_URL
