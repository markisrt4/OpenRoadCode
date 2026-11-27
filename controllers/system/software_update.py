# SPDX-License-Identifier: MIT
"""Check and apply fast-forward updates for a local OpenRoadCode checkout."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from ui.ui_dispatcher_if import UiDispatcherIf

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AvailableUpdate:
    current_commit: str
    target_commit: str


class CheckoutUpdates:
    """Use the configured origin and update only a clean master checkout."""

    def __init__(self, checkout: Path) -> None:
        self._checkout = checkout

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self._checkout), *args],
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

    def _clean_master_head(self) -> str | None:
        if (
            self._git("symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout.strip()
            != "master"
        ):
            return None
        if self._git("status", "--porcelain", "--untracked-files=normal").stdout.strip():
            return None
        return self._git("rev-parse", "HEAD").stdout.strip()

    def check(self) -> AvailableUpdate | None:
        current = self._clean_master_head()
        if current is None:
            return None
        root = Path(self._git("rev-parse", "--show-toplevel").stdout.strip())
        if root.resolve() != self._checkout.resolve():
            return None
        self._git(
            "fetch",
            "--no-tags",
            "--no-recurse-submodules",
            "origin",
            "refs/heads/master:refs/remotes/origin/master",
        )
        target = self._git("rev-parse", "refs/remotes/origin/master").stdout.strip()
        if current == target:
            return None
        ancestor = self._git("merge-base", "--is-ancestor", current, target, check=False)
        if ancestor.returncode != 0:
            return None
        return AvailableUpdate(current, target)

    def apply(self, update: AvailableUpdate) -> None:
        if self._clean_master_head() != update.current_commit:
            raise RuntimeError("The master checkout changed while the update prompt was open.")
        self._git("merge", "--ff-only", "--no-autostash", update.target_commit)


class SoftwareUpdateController:
    """Coordinate online checks, user consent, and restart without blocking Tk."""

    def __init__(
        self,
        checkout: CheckoutUpdates,
        dispatcher: UiDispatcherIf,
        *,
        online: Callable[[], bool],
        offer: Callable[[str, Callable[[], None]], None],
        report_error: Callable[[str], None],
        restart: Callable[[], None],
    ) -> None:
        self._checkout = checkout
        self._dispatcher = dispatcher
        self._online = online
        self._offer = offer
        self._report_error = report_error
        self._restart = restart
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="orc-update")
        self._timer: object = None
        self._closed = False
        self._busy = False
        self._last_offer: str | None = None

    def start(self) -> None:
        self._timer = self._dispatcher.schedule_ui_callback(3000, self._poll)

    def _poll(self) -> None:
        if self._closed:
            return
        online = self._online()
        self._timer = self._dispatcher.schedule_ui_callback(
            15 * 60_000 if online else 30_000, self._poll
        )
        if online and not self._busy:
            self._busy = True
            self._executor.submit(self._checkout.check).add_done_callback(self._checked)

    def _checked(self, result: Future[AvailableUpdate | None]) -> None:
        self._dispatcher.dispatch_ui(lambda: self._show_result(result))

    def _show_result(self, result: Future[AvailableUpdate | None]) -> None:
        self._busy = False
        if self._closed:
            return
        try:
            update = result.result()
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("Could not check for ORC updates: %s", exc)
            return
        if update is not None and self._online() and update.target_commit != self._last_offer:
            self._last_offer = update.target_commit
            self._offer(update.target_commit[:8], lambda: self._accept(update))

    def _accept(self, update: AvailableUpdate) -> None:
        if self._closed or self._busy:
            return
        if not self._online():
            self._last_offer = None
            self._report_error("Go online to update OpenRoadCode.")
            return
        self._busy = True
        self._executor.submit(self._checkout.apply, update).add_done_callback(self._applied)

    def _applied(self, result: Future[None]) -> None:
        self._dispatcher.dispatch_ui(lambda: self._finish_update(result))

    def _finish_update(self, result: Future[None]) -> None:
        self._busy = False
        if self._closed:
            return
        try:
            result.result()
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            # Git diagnostics (e.g. a worktree collision) are useful at consent time.
            detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else ""
            self._report_error(detail or str(exc))
            return
        self._restart()

    def close(self) -> None:
        self._closed = True
        self._dispatcher.cancel_ui_callback(self._timer)
        self._executor.shutdown(wait=True, cancel_futures=True)
