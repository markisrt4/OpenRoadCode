# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Quiet, private diagnostics for device and background operations."""

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from typing import Concatenate, ParamSpec, Protocol, TypeVar

from common.logging.structured import current_operation, event, operation


class ComponentLog:
    """Record fixed stages and transitions without storing external payloads."""

    def __init__(self, component: str, prefix: str) -> None:
        self._logger = logging.getLogger(component)
        self._prefix = prefix
        self._lock = Lock()
        self._failures: dict[str, tuple[str, str | None]] = {}
        self._states: dict[str, object] = {}

    def emit(
        self, level: int, suffix: str, operation_id: str | None = None, **fields: object
    ) -> None:
        if operation_id is not None:
            fields["operation_id"] = operation_id
        event(
            self._logger,
            level,
            f"{self._prefix}.{suffix}",
            f"{self._prefix.capitalize()} {suffix.replace('_', ' ')}",
            **fields,
        )

    def failed(
        self, stage: str, error: BaseException | None = None,
        operation_id: str | None = None, *, reason: str = "exception",
    ) -> None:
        failure = (reason, type(error).__name__ if error is not None else None)
        with self._lock:
            previous = self._failures.get(stage)
            self._failures[stage] = failure
        if previous != failure:
            fields = {"stage": stage, "reason": reason}
            if failure[1] is not None:
                fields["exception_type"] = failure[1]
            self.emit(logging.WARNING, "failed", operation_id, **fields)

    def succeeded(self, stage: str, operation_id: str | None = None) -> None:
        with self._lock:
            recovered = self._failures.pop(stage, None) is not None
        if recovered:
            self.emit(logging.INFO, "recovered", operation_id, stage=stage)
        self.emit(logging.DEBUG, "completed", operation_id, stage=stage)

    def changed(self, stage: str, value: object, operation_id: str | None = None) -> None:
        with self._lock:
            if stage in self._states and self._states[stage] == value:
                return
            self._states[stage] = value
        self.emit(logging.INFO, "state_changed", operation_id, stage=stage, state=value)

    @contextmanager
    def action(self, stage: str, operation_id: str | None = None) -> Iterator[str]:
        with operation(operation_id or current_operation()) as identifier:
            self.emit(logging.DEBUG, "requested", stage=stage)
            try:
                yield identifier
            except Exception as error:
                self.failed(stage, error)
                raise
            else:
                self.succeeded(stage)


class _DiagnosticOwner(Protocol):
    @property
    def _diagnostics(self) -> ComponentLog: ...


_P = ParamSpec("_P")
_R = TypeVar("_R")
_Owner = TypeVar("_Owner", bound=_DiagnosticOwner)


def diagnostic_action(
    stage: str, *, false_is_failure: bool = False
) -> Callable[[Callable[Concatenate[_Owner, _P], _R]], Callable[Concatenate[_Owner, _P], _R]]:
    """Instrument a method using its instance's private diagnostic recorder."""

    def decorate(
        function: Callable[Concatenate[_Owner, _P], _R],
    ) -> Callable[Concatenate[_Owner, _P], _R]:
        @wraps(function)
        def wrapped(self: _Owner, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
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
