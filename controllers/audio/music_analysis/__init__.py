# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral music analysis API."""

from .music_analysis_fanout import MusicAnalysisConsumer, MusicAnalysisFanout
from .music_analysis_pipeline import MusicAnalysisCallback, MusicAnalysisPipeline
from .music_analysis_types import MusicAnalysisState, PercussionActivity
from .music_analyzer import MusicAnalyzer
from .music_analyzer_if import MusicAnalyzerIf

__all__ = [
    "MusicAnalysisCallback",
    "MusicAnalysisConsumer",
    "MusicAnalysisFanout",
    "MusicAnalysisPipeline",
    "MusicAnalysisState",
    "MusicAnalyzer",
    "MusicAnalyzerIf",
    "PercussionActivity",
]
