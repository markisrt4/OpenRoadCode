# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Quiet, private diagnostics for device and background operations."""

from contextlib import contextmanager
from functools import wraps
import logging
from threading import Lock

from common.logging.structured import current_operation, event, operation


class ComponentLog:
    """Record fixed stages and transitions without storing external payloads."""

    def __init__(self, component: str, prefix: str):
        self._logger = logging.getLogger(component)
        self._prefix = prefix
        self._lock = Lock()
        self._failures = {}
        self._states = {}

    def emit(self, level, suffix, operation_id=None, **fields):
        if operation_id is not None:
            fields["operation_id"] = operation_id
        event(self._logger, level, f"{self._prefix}.{suffix}",
              f"{self._prefix.capitalize()} {suffix.replace('_', ' ')}", **fields)

    def failed(self, stage, error=None, operation_id=None, *, reason="exception"):
        failure = (reason, type(error).__name__ if error is not None else None)
        with self._lock:
            previous = self._failures.get(stage)
            self._failures[stage] = failure
        if previous != failure:
            fields = {"stage": stage, "reason": reason}
            if failure[1] is not None:
                fields["exception_type"] = failure[1]
            self.emit(logging.WARNING, "failed", operation_id, **fields)

    def succeeded(self, stage, operation_id=None):
        with self._lock:
            recovered = self._failures.pop(stage, None) is not None
        if recovered:
            self.emit(logging.INFO, "recovered", operation_id, stage=stage)
        self.emit(logging.DEBUG, "completed", operation_id, stage=stage)

    def changed(self, stage, value, operation_id=None):
        with self._lock:
            if stage in self._states and self._states[stage] == value:
                return
            self._states[stage] = value
        self.emit(logging.INFO, "state_changed", operation_id, stage=stage, state=value)

    @contextmanager
    def action(self, stage, operation_id=None):
        with operation(operation_id or current_operation()) as identifier:
            self.emit(logging.DEBUG, "requested", stage=stage)
            try:
                yield identifier
            except Exception as error:
                self.failed(stage, error)
                raise
            else:
                self.succeeded(stage)


def diagnostic_action(stage: str, *, false_is_failure: bool = False):
    """Instrument a method using its instance's private diagnostic recorder."""
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            with operation(current_operation()):
                self._diagnostics.emit(logging.DEBUG, "requested", stage=stage)
                try:
                    result = function(self, *args, **kwargs)
                except Exception as error:
                    self._diagnostics.failed(stage, error)
                    raise
                if false_is_failure and result is False:
                    self._diagnostics.failed(stage, reason="unavailable")
                else:
                    self._diagnostics.succeeded(stage)
                return result
        return wrapped
    return decorate
