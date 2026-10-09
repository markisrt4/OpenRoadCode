# SPDX-License-Identifier: MIT
"""Fault injection for resource ownership and rollback."""

import pytest

from common.resource_cleanup import ResourceCleanup, close_resources


def test_rollback_preserves_startup_error_and_attempts_every_resource():
    events = []
    startup = RuntimeError("startup")

    def broken_close():
        events.append("broken")
        raise ValueError("close")

    with pytest.raises(RuntimeError) as caught:
        with ResourceCleanup() as cleanup:
            cleanup.callback(lambda: events.append("first"))
            cleanup.callback(broken_close)
            cleanup.callback(lambda: events.append("last"))
            raise startup
    assert caught.value is startup
    assert events == ["last", "broken", "first"]
    assert "ValueError: close" in startup.__notes__[0]
    cleanup.close()
    assert len(events) == 3


def test_success_transfers_ownership_without_closing():
    events = []
    with ResourceCleanup() as cleanup:
        cleanup.callback(lambda: events.append("closed"))
        cleanup.release()
    assert events == []


def test_shutdown_reports_multiple_failures_after_all_attempts():
    events = []

    def fail(name):
        events.append(name)
        raise RuntimeError(name)

    with pytest.raises(ExceptionGroup) as caught:
        close_resources(lambda: fail("one"), lambda: fail("two"),
                        lambda: events.append("three"))
    assert events == ["one", "two", "three"]
    assert [str(error) for error in caught.value.exceptions] == ["one", "two"]
