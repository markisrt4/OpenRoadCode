# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility export for shared Spotify application composition."""

from apps.common.spotify_controller_factory import create_spotify_controller

__all__ = ["create_spotify_controller"]
