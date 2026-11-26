# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Conservative iCalendar VEVENT normalization for the read-only CalDAV path."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .calendar_models import CalendarEvent


class UnsupportedCalendarEventError(ValueError):
    """Event needs features not yet implemented."""

    def __init__(self, message: str, reason: str = "unsupported_event") -> None:
        super().__init__(message)
        self.reason = reason


def _unfold(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _unescape(value: str) -> str:
    return (
        value.replace("\\N", "\n")
        .replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _properties(lines: list[str]) -> dict[str, list[tuple[dict[str, str], str]]]:
    result: dict[str, list[tuple[dict[str, str], str]]] = {}
    for line in lines:
        head, separator, value = line.partition(":")
        if not separator:
            continue
        parts = head.split(";")
        params = {}
        for part in parts[1:]:
            key, equals, param_value = part.partition("=")
            if equals:
                params[key.upper()] = param_value.strip('"')
        result.setdefault(parts[0].upper(), []).append((params, value))
    return result


def _date_value(params: dict[str, str], value: str) -> tuple[datetime, bool]:
    if params.get("VALUE") == "DATE" or (len(value) == 8 and value.isdigit()):
        day = date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")
        return datetime.combine(day, datetime.min.time(), timezone.utc), True
    if value.endswith("Z"):
        return datetime.fromisoformat(value).astimezone(timezone.utc), False
    zone = params.get("TZID")
    if not zone:
        raise UnsupportedCalendarEventError(
            "Floating event time needs an explicit timezone", "floating_time"
        )
    try:
        tz = ZoneInfo(zone)
    except (KeyError, ValueError) as error:
        raise UnsupportedCalendarEventError(
            "Unsupported timezone identifier", "unsupported_timezone"
        ) from error
    return datetime.fromisoformat(value).replace(tzinfo=tz), False


def parse_icalendar_events(
    raw: str,
    account_id: str,
    calendar_id: str,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> list[CalendarEvent]:
    """Parse standalone VEVENTs and bounded recurrence masters.

    DATE values are represented as UTC midnights to satisfy the existing aware
    event model. All-day UI rendering must use the all_day flag, not local conversion.
    """
    result: list[CalendarEvent] = []
    overrides: dict[tuple[str, str], CalendarEvent | None] = {}
    inside = False
    event_lines: list[str] = []
    for line in _unfold(raw):
        if line == "BEGIN:VEVENT":
            if inside:
                raise ValueError("Nested VEVENT")
            inside = True
            event_lines = []
        elif line == "END:VEVENT":
            if not inside:
                raise ValueError("Unexpected END:VEVENT")
            inside = False
            fields = _properties(event_lines)
            recurring = any(key in fields for key in ("RRULE", "RDATE", "EXDATE"))
            if recurring and (window_start is None or window_end is None):
                raise UnsupportedCalendarEventError(
                    "Recurring events require recurrence expansion", "unsupported_recurrence"
                )
            recurrence = fields.get("RECURRENCE-ID")
            recurrence_id = None
            if recurrence:
                params, value = recurrence[0]
                if "RANGE" in params:
                    raise UnsupportedCalendarEventError(
                        "Range overrides are unsupported", "unsupported_override"
                    )
                recurrence_id = _date_value(params, value)[0].astimezone(timezone.utc).isoformat()
            if fields.get("STATUS", [({}, "")])[0][1] == "CANCELLED":
                if recurrence_id is not None:
                    overrides[(fields["UID"][0][1], recurrence_id)] = None
                continue
            try:
                uid = fields["UID"][0][1]
                start_params, start_raw = fields["DTSTART"][0]
            except (KeyError, IndexError) as error:
                raise ValueError("VEVENT missing UID or DTSTART") from error
            starts_at, all_day = _date_value(start_params, start_raw)
            if "DTEND" in fields:
                ends_at, end_all_day = _date_value(*fields["DTEND"][0])
                if all_day != end_all_day:
                    raise ValueError("VEVENT DTSTART/DTEND types differ")
            elif all_day:
                ends_at = starts_at + timedelta(days=1)
            else:
                raise UnsupportedCalendarEventError(
                    "Timed events without DTEND are not supported yet", "missing_end"
                )
            title = _unescape(fields.get("SUMMARY", [({}, "")])[0][1])
            location = fields.get("LOCATION")
            event = CalendarEvent(
                account_id=account_id,
                calendar_id=calendar_id,
                event_id=uid,
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
                all_day=all_day,
                location=_unescape(location[0][1]) if location else None,
                recurrence_id=recurrence_id,
            )
            if recurrence_id is not None:
                if recurring:
                    raise UnsupportedCalendarEventError(
                        "Recurring override is unsupported", "unsupported_override"
                    )
                overrides[(uid, recurrence_id)] = event
            elif recurring:
                result.extend(_expand(event, fields, window_start, window_end))
            else:
                result.append(event)
        elif inside:
            event_lines.append(line)
    if inside:
        raise ValueError("Unclosed VEVENT")
    result = [event for event in result if (event.event_id, event.recurrence_id) not in overrides]
    result.extend(
        event
        for event in overrides.values()
        if event is not None
        and (window_start is None or event.ends_at > window_start)
        and (window_end is None or event.starts_at < window_end)
    )
    return sorted(result, key=lambda event: (event.starts_at, event.event_id))


def _expand(
    event: CalendarEvent,
    fields: dict[str, list[tuple[dict[str, str], str]]],
    start: datetime,
    end: datetime,
) -> list[CalendarEvent]:
    """Expand a recurrence set within a finite overlap window."""
    from dateutil.rrule import rruleset, rrulestr
    from dateutil.tz import datetime_exists

    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("Invalid recurrence window")
    rules = rruleset()
    rules.rdate(event.starts_at)
    for _, value in fields.get("RRULE", []):
        if not value.startswith("FREQ=") and "FREQ=" not in value:
            raise ValueError("Missing recurrence frequency")
        if event.all_day:
            parts = value.split(";")
            value = ";".join(
                part + "T000000Z" if part.startswith("UNTIL=") and len(part) == 14 else part
                for part in parts
            )
        rules.rrule(rrulestr(value, dtstart=event.starts_at))
    for name, add in (("RDATE", rules.rdate), ("EXDATE", rules.exdate)):
        for params, values in fields.get(name, []):
            for value in values.split(","):
                timestamp, all_day = _date_value(params, value)
                if all_day != event.all_day:
                    raise ValueError("Recurrence date type differs from DTSTART")
                add(timestamp)
    duration = event.ends_at - event.starts_at
    result = []
    for occurrence in rules.xafter(start - duration, inc=True):
        if occurrence >= end:
            break
        if not datetime_exists(occurrence):
            continue
        if occurrence + duration <= start:
            continue
        if len(result) >= 10000:
            raise UnsupportedCalendarEventError("Too many occurrences", "recurrence_limit")
        result.append(
            replace(
                event,
                starts_at=occurrence,
                ends_at=occurrence + duration,
                recurrence_id=occurrence.astimezone(timezone.utc).isoformat(),
            )
        )
    return result
