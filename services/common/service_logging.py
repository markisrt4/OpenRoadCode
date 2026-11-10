# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Observe restricted supervisor state without logging raw status output."""

from functools import wraps
import logging
from threading import Lock

from common.logging.lifecycle import failure_fields, logged_action
from common.logging.structured import current_operation, event, operation


def supervisor_command(component: str, action: str, service: str | None, runner):
    logger = logging.getLogger(component)
    mutating = action in {"start", "stop", "restart", "up", "down"}
    action = (
        action
        if action in {"start", "stop", "restart", "up", "down", "is-active", "show", "status"}
        else "unsupported"
    )
    level = logging.INFO if mutating else logging.DEBUG
    with operation(current_operation()):
        event(
            logger,
            level,
            "supervisor.command_requested",
            "Supervisor command requested",
            action=action,
            service=service,
        )
        try:
            result = runner()
        except Exception as error:
            event(
                logger,
                logging.ERROR if mutating else logging.DEBUG,
                "supervisor.command_failed",
                "Supervisor command failed",
                action=action,
                service=service,
                **failure_fields(error),
            )
            raise
        event(
            logger,
            level,
            "supervisor.command_completed",
            "Supervisor command completed",
            action=action,
            service=service,
            returncode=result.returncode if type(result.returncode) is int else None,
        )
        return result


def service_action(component: str, action: str):
    def context(manager, *args, **kwargs):
        name = args[0] if args else kwargs.get("name")
        return {"service": name if name in manager.SERVICES else None}

    return logged_action(component, "service.action", action, context=context)


class ServiceStatusLog:
    def __init__(self) -> None:
        self.lock = Lock()
        self.states = {}
        self.failed = set()


def observed_status(component: str):
    logger = logging.getLogger(component)

    def decorate(function):
        @wraps(function)
        def wrapped(manager, name):
            # Reject unsupported identifiers before emitting any user-controlled fields.
            if name not in manager.SERVICES:
                return function(manager, name)
            tracking = manager._status_log
            try:
                result = function(manager, name)
            except Exception as error:
                with tracking.lock:
                    if name not in tracking.failed:
                        event(
                            logger,
                            logging.WARNING,
                            "service.status_failed",
                            "Service status query failed",
                            service=name,
                            **failure_fields(error),
                        )
                    tracking.failed.add(name)
                raise
            state = result.state if result.state in {"running", "stopped", "unknown"} else "unknown"
            profile = (
                result.profile
                if result.profile in {"local", "remote", "simulated", "custom"}
                else None
            )
            input_state = getattr(result, "input_state", None)
            input_state = (
                input_state if input_state in {"waiting", "connected", "stopped"} else None
            )
            supervisor_failed = component == "runtime.services.systemd" and "failed" in {
                part.strip() for part in result.detail.split("/")
            }
            snapshot = (state, profile, input_state, supervisor_failed)
            with tracking.lock:
                if name in tracking.failed:
                    event(
                        logger,
                        logging.INFO,
                        "service.status_recovered",
                        "Service status query recovered",
                        service=name,
                    )
                    tracking.failed.discard(name)
                previous = tracking.states.get(name)
                if previous != snapshot:
                    event(
                        logger,
                        logging.WARNING
                        if state == "unknown" or input_state == "waiting" or supervisor_failed
                        else logging.INFO,
                        "service.status_observed" if previous is None else "service.status_changed",
                        "Service supervisor state observed",
                        service=name,
                        state=state,
                        profile=profile,
                        input_state=input_state,
                        supervisor_failed=supervisor_failed,
                    )
                    tracking.states[name] = snapshot
            return result

        return wrapped

    return decorate
