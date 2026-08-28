# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fan out shared music-analysis snapshots to multiple consumers."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .music_analysis_types import MusicAnalysisState

MusicAnalysisConsumer = Callable[[MusicAnalysisState], object]


class MusicAnalysisFanout:
    """Publish each analysis snapshot to an ordered set of consumers."""

    def __init__(
        self,
        consumers: Iterable[MusicAnalysisConsumer] = (),
    ) -> None:
        self._consumers = list(consumers)

    def add(self, consumer: MusicAnalysisConsumer) -> None:
        """Append a consumer to the publication order.

        @param consumer Callback invoked for each analysis snapshot.
        """
        self._consumers.append(consumer)

    def remove(self, consumer: MusicAnalysisConsumer) -> None:
        """Remove the first matching consumer.

        @param consumer Previously registered callback.
        @raises ValueError If the callback is not registered.
        """
        self._consumers.remove(consumer)

    def __call__(self, state: MusicAnalysisState) -> None:
        """Publish one snapshot to all registered consumers.

        Consumers are invoked in registration order. Return values are
        intentionally ignored so consumers such as lighting adapters may
        return command futures without coupling the analysis pipeline to them.

        @param state Shared music-analysis snapshot.
        """
        for consumer in tuple(self._consumers):
            consumer(state)
