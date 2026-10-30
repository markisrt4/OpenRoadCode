# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility re-export of libMusicForge's FFT implementation.

All signal-processing logic now lives in the reusable musicforge package.
"""
from musicforge.analysis import MusicAnalyzer

__all__ = ["MusicAnalyzer"]
