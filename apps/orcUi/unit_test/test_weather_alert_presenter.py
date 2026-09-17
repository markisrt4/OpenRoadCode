# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone

from apps.orcUi.weather_alert_presenter import WeatherAlertPresenter
from messaging.contracts.weather import WeatherAlertData


def test_presenter_maps_wire_alert_to_typed_presentation_state() -> None:
    data = WeatherAlertData(
        alert_id="urn:example:alert:1",
        event="Severe Thunderstorm Warning",
        headline="Severe Thunderstorm Warning issued",
        description="Storms are moving through the area.",
        instruction="Move indoors.",
        severity="severe",
        urgency="immediate",
        certainty="observed",
        effective_at="2026-09-17T20:00:00+00:00",
        onset_at="2026-09-17T20:05:00+00:00",
        expires_at="2026-09-17T21:00:00+00:00",
        sender="National Weather Service",
    )

    state = WeatherAlertPresenter.present(data)

    assert state.alert_id == "urn:example:alert:1"
    assert state.event == "Severe Thunderstorm Warning"
    assert state.severity == "severe"
    assert state.urgency == "immediate"
    assert state.certainty == "observed"
    assert state.instruction == "Move indoors."
    assert state.effective_at == datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc)
    assert state.onset_at == datetime(2026, 9, 17, 20, 5, tzinfo=timezone.utc)
    assert state.expires_at == datetime(2026, 9, 17, 21, 0, tzinfo=timezone.utc)
