# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from __future__ import annotations
from abc import ABC,abstractmethod
from dataclasses import dataclass
from datetime import datetime
@dataclass(frozen=True,slots=True)
class WeatherAlertUiEvent:
    identifier:str; correlation_id:str; operation:str; clear_reason:str|None
    event:str; headline:str; description:str; instruction:str|None
    severity:str; urgency:str; certainty:str
    effective_at:datetime; onset_at:datetime|None; expires_at:datetime|None; sender:str
class WeatherAlertUiIf(ABC):
    @abstractmethod
    def present_weather_alert(self,alert:WeatherAlertUiEvent)->None:...
