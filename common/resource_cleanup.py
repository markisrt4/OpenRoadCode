# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Exception-safe ownership for partially assembled resource graphs."""

from collections.abc import Callable


class ResourceCleanup:
    """Close acquired resources once, in reverse order, without skipping failures.

    A successful factory releases callbacks when it transfers ownership. Failed
    construction preserves the original exception and attaches cleanup failures
    as notes. Explicit close reports all failures after attempting every callback.
    """

    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []

    def callback(self, close: Callable[[], None]) -> None:
        self._callbacks.append(close)

    def release(self) -> None:
        """Transfer ownership without closing successfully assembled resources."""
        self._callbacks.clear()

    def _close(self) -> list[BaseException]:
        callbacks, self._callbacks = self._callbacks, []
        failures = []
        for close in reversed(callbacks):
            try:
                close()
            except BaseException as error:
                failures.append(error)
        return failures

    def close(self) -> None:
        failures = self._close()
        if len(failures) == 1:
            raise failures[0]
        if failures:
            raise BaseExceptionGroup("Resource cleanup failed", failures)

    def __enter__(self) -> "ResourceCleanup":
        return self

    def __exit__(self, _type, error, _traceback) -> bool:
        failures = self._close()
        if error is not None:
            for failure in failures:
                error.add_note(f"Cleanup also failed: {type(failure).__name__}: {failure}")
        elif len(failures) == 1:
            raise failures[0]
        elif failures:
            raise BaseExceptionGroup("Resource cleanup failed", failures)
        return False


def close_resources(*callbacks: Callable[[], None]) -> None:
    """Attempt every callback in the supplied order, then report failures."""
    with ResourceCleanup() as cleanup:
        for close in reversed(callbacks):
            cleanup.callback(close)
