# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend receiver contract for camera and perception state."""

from abc import ABC, abstractmethod

from ui.vision.vision_request_handler_if import VisionRequestHandlerIf
from ui.vision.vision_ui_state import VisionUiState


class VisionUiIf(ABC):
    """Receive complete vision snapshots and semantic request handlers."""

    @abstractmethod
    def set_vision_state(self, state: VisionUiState) -> None:
        """Present one complete camera and perception snapshot.

        @param state Latest immutable vision UI state.
        """
        ...

    @abstractmethod
    def set_vision_request_handler(
        self, handler: VisionRequestHandlerIf | None
    ) -> None:
        """Connect or disconnect semantic vision requests.

        @param handler Request receiver, or None to disconnect controls.
        """
        ...
