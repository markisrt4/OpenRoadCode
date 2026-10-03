# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class WeatherAlertData:
    identifier:str; correlation_id:str; operation:str; clear_reason:str|None; event:str; headline:str; description:str; instruction:str|None; severity:str; urgency:str; certainty:str; effective_at:str; onset_at:str|None; expires_at:str|None; sender:str
@dataclass(frozen=True,slots=True)
class WeatherAlertMessage:
    version:int; source:str; data:WeatherAlertData
