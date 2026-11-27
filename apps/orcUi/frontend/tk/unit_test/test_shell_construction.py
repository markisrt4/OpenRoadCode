"""Shell presentation helpers retain the established volume readout."""

import pytest

from apps.orcUi.frontend.tk.shell_construction import format_volume


@pytest.mark.parametrize(
    "percent,muted,expected",
    [(None, False, "🔊 --"), (30.0, False, "🔊 30%"), (0.0, True, "🔇 0%")],
)
def test_volume_readout_handles_unknown_and_muted(percent, muted, expected):
    assert format_volume(percent, muted) == expected
