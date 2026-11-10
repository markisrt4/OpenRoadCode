# SPDX-License-Identifier: MIT

"""Optional route capability; advertise only when implemented."""

from abc import ABC, abstractmethod


class RouteVoiceGuidanceRequestHandlerIf(ABC):
    """Control spoken guidance mute state."""

    @abstractmethod
    def request_voice_guidance_muted(self, muted: bool) -> None:
        """Request spoken route guidance mute state.

        @param muted True to mute spoken route guidance.
        """
        ...
