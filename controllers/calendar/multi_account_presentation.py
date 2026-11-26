# SPDX-License-Identifier: MIT
"""Account-aware presentation adapters for the shared calendar dashboard."""

from datetime import date, tzinfo
from pathlib import Path

from ui.calendar.calendar_models import CalendarHealthView, CalendarSelectionView
from ui.calendar.calendar_presentation_if import CalendarSelectionIf

from .calendar_accounts import load_accounts
from .calendar_coverage import covered_calendar_days
from .calendar_event_cache import CalendarEventCache
from .calendar_presentation import CalendarSelectionPresentation, calendar_health_view
from .calendar_provider_factory import CalendarAccountPaths


class MultiAccountPresentation(CalendarSelectionIf):
    """Combine enabled accounts while keeping collection identities distinct."""

    def __init__(self, accounts_file: Path, metadata_root: Path) -> None:
        self._accounts_file = accounts_file
        self._metadata_root = metadata_root

    def _paths(self) -> tuple[CalendarAccountPaths, ...]:
        return tuple(
            CalendarAccountPaths(self._metadata_root, account)
            for account in load_accounts(self._accounts_file)
            if account.enabled
        )

    def coverage(
        self, cache: CalendarEventCache, zone: tzinfo, day: date, days: int
    ) -> frozenset[date]:
        windows = [
            covered_calendar_days(
                cache, paths.account.account_id, paths.selection, paths.catalog, zone, day, days
            )
            for paths in self._paths()
        ]
        return frozenset.intersection(*windows) if windows else frozenset()

    def health(self, *, offline: bool = False) -> CalendarHealthView:
        views = [calendar_health_view(paths.health, offline=offline) for paths in self._paths()]
        if not views:
            return CalendarHealthView(offline=offline)
        ages = [view.last_data_refresh_age_seconds for view in views]
        status = (
            "failed"
            if any(view.status == "failed" for view in views)
            else views[0].status
            if all(view.status == views[0].status for view in views)
            else "partial"
        )
        return CalendarHealthView(
            status=status,
            stale=any(view.stale for view in views) or any(age is None for age in ages),
            last_data_refresh_age_seconds=(
                max(age for age in ages if age is not None)
                if all(age is not None for age in ages)
                else None
            ),
            offline=offline,
            syncing=any(view.syncing for view in views),
        )

    def list_calendars(self) -> tuple[CalendarSelectionView, ...]:
        return tuple(
            CalendarSelectionView(
                f"{paths.account.account_id}:{view.calendar_id}",
                f"{paths.account.account_id}: {view.name}",
                view.enabled,
            )
            for paths in self._paths()
            for view in CalendarSelectionPresentation(
                paths.selection, paths.catalog
            ).list_calendars()
        )

    def apply_selection(self, enabled: dict[str, bool]) -> None:
        for paths in self._paths():
            prefix = f"{paths.account.account_id}:"
            changes = {
                key.removeprefix(prefix): value
                for key, value in enabled.items()
                if key.startswith(prefix)
            }
            if changes:
                CalendarSelectionPresentation(paths.selection, paths.catalog).apply_selection(
                    changes
                )
