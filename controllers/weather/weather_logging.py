# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Private weather diagnostics: fixed messages, transition-only failures and IDs."""

import logging
from threading import Lock

from common.logging.structured import current_operation, event, operation


class WeatherLog:
    """Keep repeated background refreshes quiet without retaining provider payloads."""

    def __init__(self, component: str):
        self._logger = logging.getLogger(component)
        self._lock = Lock()
        self._failures = {}
        self._states = {}

    def emit(self, level, name, message, operation_id=None, **fields):
        if operation_id is not None:
            fields["operation_id"] = operation_id
        event(self._logger, level, name, message, **fields)

    def requested(self):
        with operation(current_operation()) as operation_id:
            self.emit(logging.DEBUG, "weather.requested", "Weather operation requested")
        return operation_id

    def start(self, worker, operation_id):
        try:
            worker.start()
        except Exception as error:
            self.failed(error, operation_id, stage="worker")
            raise
        self.succeeded(operation_id, stage="worker")

    def failed(self, error=None, operation_id=None, *, stage="provider", reason="exception"):
        # Callers supply exceptions, never UI error text or provider responses.
        exception_type = type(error).__name__ if error is not None else None
        failure = (reason, exception_type)
        with self._lock:
            previous = self._failures.get(stage)
            self._failures[stage] = failure
        if previous != failure:
            fields = {"stage": stage, "reason": reason}
            if exception_type is not None:
                fields["exception_type"] = exception_type
            self.emit(logging.WARNING, "weather.failed", "Weather operation failed",
                      operation_id, **fields)

    def succeeded(self, operation_id=None, *, stage="provider", **fields):
        with self._lock:
            recovered = self._failures.pop(stage, None) is not None
        if recovered:
            self.emit(logging.INFO, "weather.recovered", "Weather operation recovered",
                      operation_id, stage=stage)
        self.emit(logging.DEBUG, "weather.completed", "Weather operation completed",
                  operation_id, stage=stage, **fields)

    def stale(self, operation_id=None):
        self.emit(logging.DEBUG, "weather.result_discarded", "Obsolete weather result discarded",
                  operation_id)

    def changed(self, key, value, name, message, **fields):
        with self._lock:
            if key in self._states and self._states[key] == value:
                return
            self._states[key] = value
        self.emit(logging.INFO, name, message, **fields)
