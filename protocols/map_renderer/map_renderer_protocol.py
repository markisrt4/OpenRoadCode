"""Protocol definitions for the native map renderer."""

from enum import StrEnum


class MapRendererCommand(StrEnum):
    """Commands supported by the native map renderer."""

    SET_CENTER = "set_center"
    SET_CAMERA = "set_camera"
