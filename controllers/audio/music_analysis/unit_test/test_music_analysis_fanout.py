# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from controllers.audio.music_analysis.music_analysis_fanout import MusicAnalysisFanout
from controllers.audio.music_analysis.music_analysis_types import MusicAnalysisState


def test_consumers_receive_same_state_in_registration_order() -> None:
    calls: list[tuple[str, MusicAnalysisState]] = []
    state = MusicAnalysisState(level=0.5, bass=0.7)
    fanout = MusicAnalysisFanout(
        (
            lambda value: calls.append(("first", value)),
            lambda value: calls.append(("second", value)),
        )
    )

    fanout(state)

    assert calls == [("first", state), ("second", state)]


def test_add_registers_consumer() -> None:
    received: list[MusicAnalysisState] = []
    fanout = MusicAnalysisFanout()
    fanout.add(received.append)
    state = MusicAnalysisState(mid=0.8)

    fanout(state)

    assert received == [state]


def test_remove_unregisters_consumer() -> None:
    received: list[MusicAnalysisState] = []
    fanout = MusicAnalysisFanout((received.append,))
    fanout.remove(received.append)

    fanout(MusicAnalysisState())

    assert received == []


def test_remove_unknown_consumer_raises() -> None:
    fanout = MusicAnalysisFanout()

    with pytest.raises(ValueError):
        fanout.remove(lambda _state: None)


def test_mutation_during_publication_applies_to_next_state() -> None:
    calls: list[str] = []
    fanout = MusicAnalysisFanout()

    def second(_state: MusicAnalysisState) -> None:
        calls.append("second")

    def first(_state: MusicAnalysisState) -> None:
        calls.append("first")
        fanout.add(second)

    fanout.add(first)
    fanout(MusicAnalysisState())
    assert calls == ["first"]

    fanout(MusicAnalysisState())
    assert calls == ["first", "first", "second"]
