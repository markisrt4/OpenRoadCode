# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Safe lifecycle events for operations that may contain sensitive arguments."""

from functools import wraps
import logging

from common.logging.structured import current_operation, event, operation


def failure_fields(error: Exception) -> dict:
    fields = {"exception_type": type(error).__name__}
    for attribute in ("returncode", "errno"):
        value = getattr(error, attribute, None)
        if type(value) is int:
            fields[attribute] = value
    return fields


def logged_action(component: str, prefix: str, action: str, *, context=None):
    """Log a local operation without serializing its arguments or return value."""
    logger = logging.getLogger(component)

    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            fields = context(*args, **kwargs) if context else {}
            with operation(current_operation()):
                event(
                    logger,
                    logging.INFO,
                    f"{prefix}.requested",
                    "Lifecycle action requested",
                    action=action,
                    **fields,
                )
                try:
                    result = function(*args, **kwargs)
                except Exception as error:
                    event(
                        logger,
                        logging.ERROR,
                        f"{prefix}.failed",
                        "Lifecycle action failed",
                        action=action,
                        **fields,
                        **failure_fields(error),
                    )
                    raise
                if type(result) is bool:
                    fields = dict(fields, result=result)
                event(
                    logger,
                    logging.INFO,
                    f"{prefix}.completed",
                    "Lifecycle action completed",
                    action=action,
                    **fields,
                )
                return result

        return wrapped

    return decorate
