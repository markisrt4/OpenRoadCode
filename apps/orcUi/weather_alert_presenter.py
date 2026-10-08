# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from datetime import datetime
from messaging.contracts.weather import WeatherAlertData
from ui.weather import WeatherAlertUiEvent
WeatherAlertPresentationState=WeatherAlertUiEvent
class WeatherAlertPresenter:
    @staticmethod
    def present(data:WeatherAlertData)->WeatherAlertUiEvent:
        return WeatherAlertUiEvent(identifier=data.identifier,correlation_id=data.correlation_id,operation=data.operation,clear_reason=data.clear_reason,event=data.event,headline=data.headline,description=data.description,instruction=data.instruction,severity=data.severity,urgency=data.urgency,certainty=data.certainty,effective_at=datetime.fromisoformat(data.effective_at),onset_at=None if data.onset_at is None else datetime.fromisoformat(data.onset_at),expires_at=None if data.expires_at is None else datetime.fromisoformat(data.expires_at),sender=data.sender)
