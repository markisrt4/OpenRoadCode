# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Merged media lifecycle owns both the visualizer runtime and online subscription."""
from unittest.mock import Mock

import pytest

from apps.orcUi.composition.media import MediaComposition


@pytest.mark.parametrize('hide_fails', [False, True])
def test_close_unsubscribes_and_releases_visualizer_runtime_even_if_hide_fails(hide_fails):
    calls = Mock()
    visualizer, runtime, video = Mock(), Mock(), Mock()
    unsubscribe = Mock()
    calls.attach_mock(unsubscribe, 'unsubscribe')
    calls.attach_mock(visualizer, 'visualizer')
    calls.attach_mock(runtime, 'runtime')
    calls.attach_mock(video, 'video')
    composition = MediaComposition(video, Mock(), visualizer, runtime, unsubscribe)
    if hide_fails:
        visualizer.hide.side_effect = RuntimeError('window unavailable')
        with pytest.raises(RuntimeError, match='window unavailable'):
            composition.close()
    else:
        composition.close()
    assert [call[0] for call in calls.mock_calls] == [
        'unsubscribe', 'visualizer.hide', 'runtime.close', 'video.stop_video',
    ]
