class Elm327Error(Exception):
    """Base exception for ELM327 communication failures."""


class Elm327ConnectionError(Elm327Error):
    """Raised when an ELM327 connection cannot be established or used."""


class Elm327CommandError(Elm327Error):
    """Raised when an ELM327 command cannot be sent or read."""

