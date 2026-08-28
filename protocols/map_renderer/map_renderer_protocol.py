# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Protocol definitions for the native map renderer."""

from common.str_enum import StrEnum


MAP_RENDERER_COMMAND_TOPIC = "map.command"


class MapRendererCommand(StrEnum):
    """Commands supported by the native map renderer."""

    SET_CENTER = "set_center"
    SET_CAMERA = "set_camera"
    SET_ROUTE = "set_route"
    FIT_BOUNDS = "fit_bounds"
    SET_POSITION = "set_position"
