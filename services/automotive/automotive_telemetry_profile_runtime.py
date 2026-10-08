# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Apply semantic telemetry profile requests to the automotive source."""

import logging

from common.logging.structured import current_operation, event, operation

from controllers.automotive.automotive_telemetry_profile import AutomotiveTelemetryProfile
from messaging.contracts.automotive.telemetry_profile_request import (
    AutomotiveTelemetryProfileRequest,
    decode_automotive_telemetry_profile_request,
)
from messaging.contracts.automotive.topics import AUTOMOTIVE_TELEMETRY_PROFILE_REQUEST_TOPIC
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf

LOGGER = logging.getLogger("automotive.profiles")


class AutomotiveTelemetryProfileRuntime:
    def __init__(self, subscriber: SubscriberIf, source) -> None:
        self._source = source
        self._dispatcher = MessageDispatcher(subscriber, max_workers=1)
        self._dispatcher.register(
            AUTOMOTIVE_TELEMETRY_PROFILE_REQUEST_TOPIC,
            decode_automotive_telemetry_profile_request,
            self._handle_request,
        )

    def start(self) -> None:
        self._dispatcher.start()

    def close(self) -> None:
        self._dispatcher.close()

    def _handle_request(self, request: AutomotiveTelemetryProfileRequest) -> None:
        setter = getattr(self._source, "set_telemetry_profile", None)
        if callable(setter):
            with operation(current_operation()):
                try:
                    setter(request.profile)
                except Exception as exc:
                    event(
                        LOGGER,
                        logging.ERROR,
                        "profile.failed",
                        "Telemetry profile application failed",
                        profile=request.profile.value,
                        exception_type=type(exc).__name__,
                    )
                    raise
                event(
                    LOGGER,
                    logging.DEBUG,
                    "profile.applied",
                    "Telemetry profile applied",
                    profile=request.profile.value,
                )
        else:
            event(
                LOGGER,
                logging.DEBUG,
                "profile.ignored",
                "Source does not support telemetry profiles",
                profile=request.profile.value,
            )
