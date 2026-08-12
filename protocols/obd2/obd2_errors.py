# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

class Obd2Error(RuntimeError):
    """Base exception for OBD-II adapter and protocol failures."""


class Obd2ConnectionError(Obd2Error):
    """The adapter connection could not be established or was lost."""


class Obd2CommandError(Obd2Error):
    """The adapter or vehicle rejected or could not complete a request."""


class Obd2ProtocolError(Obd2Error):
    """A vehicle or adapter response was malformed or inconsistent."""
