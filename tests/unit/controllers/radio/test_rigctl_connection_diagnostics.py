# SPDX-License-Identifier: MIT
"""Connection diagnostics for the active rigctl transport."""
from unittest.mock import patch

import pytest

from protocols.rigctl.rigctl_client import RigctlClient


def test_success_records_connection_snapshot():
    client = RigctlClient()
    with patch("protocols.rigctl.rigctl_client.socket.create_connection") as connect:
        sock = connect.return_value.__enter__.return_value
        sock.recv.return_value = b"104300000\n"
        assert client.get_frequency() == "104300000"
    state = client.connection_diagnostics()
    assert state.state == "connected"
    assert state.requests == 1
    assert state.failures == 0
    assert state.last_success_monotonic is not None
    assert state.last_error is None


def test_failure_and_recovery_are_observable():
    client = RigctlClient()
    with patch("protocols.rigctl.rigctl_client.socket.create_connection",
               side_effect=ConnectionRefusedError("offline")):
        with pytest.raises(ConnectionRefusedError):
            client.get_frequency()
    state = client.connection_diagnostics()
    assert (state.state, state.requests, state.failures) == ("unavailable", 1, 1)
    assert "offline" in state.last_error
    with patch("protocols.rigctl.rigctl_client.socket.create_connection") as connect:
        connect.return_value.__enter__.return_value.recv.return_value = b"94700000\n"
        assert client.get_frequency() == "94700000"
    state = client.connection_diagnostics()
    assert (state.state, state.requests, state.failures) == ("connected", 2, 1)
    assert state.last_error is None
