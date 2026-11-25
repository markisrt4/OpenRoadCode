# SPDX-License-Identifier: MIT
"""Keep Tk interpreter finalization on the frontend test thread."""

import gc
import threading

import pytest


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """Collect destroyed widget cycles after fixture and unittest cleanup.

    Tk widgets can retain Python reference cycles after root.destroy().
    Collect them before subsequent runtime tests start background workers,
    which must never finalize a Tcl interpreter owned by the test thread.
    """
    try:
        return (yield)
    finally:
        assert threading.current_thread() is threading.main_thread()
        gc.collect()
