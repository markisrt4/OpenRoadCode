# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Display-unit and local-time policy for immutable weather overlay state."""

from datetime import datetime, timedelta


def weather_value(value, kind, imperial):
    if value is None:
        return "—"
    if kind == "temperature":
        celsius = value - 273.15
        return f"{celsius * 9 / 5 + 32:.0f}°F" if imperial else f"{celsius:.0f}°C"
    if kind == "wind":
        return f"{value * 2.236936:.0f} mph" if imperial else f"{value * 3.6:.0f} km/h"
    return f'{value / 0.0254:.2f}"' if imperial else f"{value * 1000:.1f} mm"


def city_time_label(state):
    anchor = state.anchor or datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    target = anchor + timedelta(hours=state.hours * (-1 if state.period == "past" else 1))

    def stamp(value):
        return value.astimezone().strftime("%a %I:%M %p %Z").replace(" 0", " ")

    if state.kind == "precipitation":
        start, end = (target, anchor) if state.period == "past" else (anchor, target)
        return f"{state.hours}h total · {stamp(start)} → {stamp(end)}"
    return f"{state.hours}h {'ago' if state.period == 'past' else 'ahead'} · {stamp(target)}"


def route_weather_label(point, layers, imperial):
    values = []
    if "temperature" in layers:
        values.append(weather_value(point.temperature_k, "temperature", imperial))
    if "rain" in layers:
        values.append("Precip —" if point.rain_probability is None else f"Precip {point.rain_probability * 100:.0f}%")
    if "wind" in layers:
        values.append("Wind " + weather_value(point.wind_speed_m_s, "wind", imperial))
    return " · ".join(values)


def model_legend(state, imperial):
    return tuple((weather_value(stop.value_si, state.kind, imperial), stop.rgb) for stop in state.legend)


def model_status(state):
    status = state.status
    if state.valid_at is not None and status == "Weather forecast":
        status += " · valid " + state.valid_at.astimezone().strftime('%I:%M %p').lstrip('0')
    return status + (" · Loading tiles…" if state.loading else "")
