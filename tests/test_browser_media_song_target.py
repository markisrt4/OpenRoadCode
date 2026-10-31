"""One-shot browser search target behavior without requiring an X display."""
from unittest.mock import Mock

import pytest

from frontends.tk.media.browser_media_screen import BrowserMediaScreen


def test_show_target_passes_search_to_existing_show_flow():
    screen = object.__new__(BrowserMediaScreen)
    screen._pending_target = None
    screen.show = Mock()
    screen.show_target("Ella Langley Loving Life Again")
    assert screen._pending_target == "Ella Langley Loving Life Again"
    screen.show.assert_called_once_with()


def test_show_target_rejects_empty_query():
    screen = object.__new__(BrowserMediaScreen)
    screen._pending_target = None
    screen.show = Mock()
    with pytest.raises(ValueError):
        screen.show_target("  ")
    screen.show.assert_not_called()
