# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""HOME presentation cleanup does not stop a capture retained by another view."""
from unittest.mock import Mock
from frontends.tk.media.home_media_visualizer import HomeMediaVisualizer


def test_retiring_home_preview_cancels_poll_and_releases_only_its_lease():
    card = object.__new__(HomeMediaVisualizer)
    card._poll_job = 'poll'
    card.after_cancel = Mock()
    card._preview = Mock()
    card._controller = Mock()
    card._owner = 'home'
    card._attached = True
    card._last_frame = Mock()
    preview = card._preview
    card._retire_preview()
    card.after_cancel.assert_called_once_with('poll')
    preview.close.assert_called_once()
    preview.destroy.assert_called_once()
    card._controller.detach_view.assert_called_once_with('home')
    card._controller.stop.assert_not_called()
    card._retire_preview()
    card._controller.detach_view.assert_called_once()


def test_failed_preview_construction_can_release_attached_lease():
    card = object.__new__(HomeMediaVisualizer)
    card._poll_job = None
    card._preview = None
    card._attached = True
    card._owner = 'home'
    card._controller = Mock()
    card._last_frame = None
    card._retire_preview()
    card._controller.detach_view.assert_called_once_with('home')
    assert not card._attached


def test_composition_can_close_home_card_before_root_destruction():
    card = object.__new__(HomeMediaVisualizer)
    card._closed = False
    card._retire_preview = Mock()
    card.close()
    card.close()
    card._retire_preview.assert_called_once()
    assert card._closed
