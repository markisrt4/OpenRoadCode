import math
from datetime import datetime
from typing import Optional, Dict, Any

import requests
import streamlit as st
import geocoder
from streamlit_autorefresh import st_autorefresh

try:
    import gpsd
    GPSD_AVAILABLE = True
except ImportError:
    GPSD_AVAILABLE = False


REFRESH_SECONDS = 60
USE_GPSD = True
GPSD_HOST = "127.0.0.1"
GPSD_PORT = 2947

DEFAULT_LAT = 42.6709
DEFAULT_LON = -83.0330
DEFAULT_LOCATION_NAME = "Fallback Location"

st.set_page_config(
    page_title="CarSDR Weather",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }

    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 1rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }

    .stApp {
        background: #111418;
        color: #ffffff;
    }

    h1, h2, h3 {
        color: #ffffff;
        margin-top: 0.25rem;
    }

    .weather-hero {
        background: linear-gradient(135deg, #20252b, #111418);
        border: 1px solid #384653;
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 12px;
    }

    .weather-title {
        font-size: 2.0rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 4px;
    }

    .weather-subtitle {
        color: #b8c7d3;
        font-size: 1.0rem;
    }

    div[data-testid="stMetric"] {
        background: #20252b;
        border: 1px solid #384653;
        border-radius: 16px;
        padding: 12px 16px;
    }

    div[data-testid="stMetricLabel"] {
        color: #b8c7d3;
    }

    div[data-testid="stMetricValue"] {
        color: #ffffff;
    }

    table {
        border-collapse: collapse;
    }

    thead tr th {
        background-color: #26313a !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    tbody tr:nth-child(even) {
        background-color: #182027 !important;
    }

    tbody tr:nth-child(odd) {
        background-color: #111820 !important;
    }

    tbody td {
        color: #e8eef2 !important;
        border-color: #384653 !important;
    }

    .radar-card {
        background: #20252b;
        border: 1px solid #384653;
        border-radius: 16px;
        padding: 18px 22px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=REFRESH_SECONDS * 1000, key="weather_refresh")


WMO_CODES = {
    0: "☀️ Clear sky", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
    45: "🌫️ Fog", 48: "🌫️ Rime fog", 51: "🌦️ Light drizzle", 53: "🌦️ Moderate drizzle",
    55: "🌦️ Dense drizzle", 56: "🌧️ Freezing drizzle", 57: "🌧️ Dense freezing drizzle",
    61: "🌧️ Slight rain", 63: "🌧️ Moderate rain", 65: "🌧️ Heavy rain",
    66: "🌧️ Freezing rain", 67: "🌧️ Heavy freezing rain", 71: "🌨️ Slight snow",
    73: "🌨️ Moderate snow", 75: "❄️ Heavy snow", 77: "🌨️ Snow grains",
    80: "🌦️ Slight rain showers", 81: "🌦️ Moderate rain showers",
    82: "⛈️ Violent rain showers", 85: "🌨️ Slight snow showers",
    86: "🌨️ Heavy snow showers", 95: "⛈️ Thunderstorm",
    96: "⛈️ Thunderstorm w/ hail", 99: "⛈️ Severe thunderstorm w/ hail",
}


def wind_dir_from_degrees(deg: Optional[float]) -> str:
    if deg is None:
        return "N/A"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[round(deg / 45) % 8]


def c_to_f(c: Optional[float]) -> str:
    if c is None:
        return "N/A"
    return f"{(c * 9 / 5) + 32:.1f}°F"


def kmh_to_mph(kmh: Optional[float]) -> str:
    if kmh is None:
        return "N/A"
    return f"{kmh * 0.621371:.1f} mph"


@st.cache_data(ttl=45)
def get_ip_location() -> Dict[str, Any]:
    g = geocoder.ip("me")
    if g.ok and g.latlng:
        name = ", ".join(part for part in [g.city or "", g.state or "", g.country or ""] if part)
        return {"lat": g.latlng[0], "lon": g.latlng[1], "name": name or "IP location", "source": "IP geolocation"}
    raise RuntimeError("IP geolocation failed")


def get_gpsd_location() -> Dict[str, Any]:
    if not GPSD_AVAILABLE:
        raise RuntimeError("gpsd-py3 not installed")

    gpsd.connect(host=GPSD_HOST, port=GPSD_PORT)
    packet = gpsd.get_current()

    if packet.mode < 2:
        raise RuntimeError("GPS fix not available")

    if packet.lat is None or packet.lon is None:
        raise RuntimeError("GPS returned no coordinates")

    return {"lat": packet.lat, "lon": packet.lon, "name": f"{packet.lat:.5f}, {packet.lon:.5f}", "source": "GPSD"}


def get_location() -> Dict[str, Any]:
    if USE_GPSD:
        try:
            return get_gpsd_location()
        except Exception:
            pass

    try:
        return get_ip_location()
    except Exception:
        return {
            "lat": DEFAULT_LAT,
            "lon": DEFAULT_LON,
            "name": DEFAULT_LOCATION_NAME,
            "source": "Static fallback",
        }


@st.cache_data(ttl=300)
def reverse_geocode(lat: float, lon: float) -> str:
    try:
        g = geocoder.osm([lat, lon], method="reverse")
        if g.ok:
            city = g.city or g.town or g.village or ""
            state = g.state or ""
            country = g.country or ""
            return ", ".join(part for part in [city, state, country] if part) or f"{lat:.5f}, {lon:.5f}"
    except Exception:
        pass
    return f"{lat:.5f}, {lon:.5f}"


@st.cache_data(ttl=120)
def fetch_weather(lat: float, lon: float) -> Dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "current": ",".join([
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation", "rain", "showers", "snowfall", "weather_code",
            "cloud_cover", "pressure_msl", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
        ]),
        "hourly": ",".join([
            "temperature_2m", "apparent_temperature", "precipitation_probability",
            "precipitation", "weather_code", "cloud_cover", "wind_speed_10m",
        ]),
        "daily": ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "sunrise", "sunset", "precipitation_probability_max",
            "wind_speed_10m_max",
        ]),
        "forecast_days": 7,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


try:
    loc = get_location()
    lat = float(loc["lat"])
    lon = float(loc["lon"])
    pretty_location = reverse_geocode(lat, lon)
    weather = fetch_weather(lat, lon)

    current = weather["current"]
    hourly = weather["hourly"]
    daily = weather["daily"]

    condition = WMO_CODES.get(current.get("weather_code"), f"Code {current.get('weather_code')}")
    wind_dir = wind_dir_from_degrees(current.get("wind_direction_10m"))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.markdown(
        f"""
        <div class="weather-hero">
            <div class="weather-title">CarSDR Weather</div>
            <div class="weather-subtitle">
                📍 {pretty_location} · {lat:.5f}, {lon:.5f} · {loc["source"]} · Updated {now_str}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_current, tab_hourly, tab_extended, tab_radar = st.tabs(
        ["Current", "Next 24 Hours", "Extended Forecast", "Radar"]
    )

    with tab_current:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Temperature", c_to_f(current.get("temperature_2m")))
            st.metric("Feels Like", c_to_f(current.get("apparent_temperature")))
        with c2:
            st.metric("Condition", condition)
            st.metric("Humidity", f"{current.get('relative_humidity_2m', 'N/A')}%")
        with c3:
            st.metric("Wind", kmh_to_mph(current.get("wind_speed_10m")))
            st.metric("Wind Dir", wind_dir)
        with c4:
            st.metric("Gusts", kmh_to_mph(current.get("wind_gusts_10m")))
            st.metric("Cloud Cover", f"{current.get('cloud_cover', 'N/A')}%")

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.metric("Pressure", f"{current.get('pressure_msl', 'N/A')} hPa")
        with d2:
            st.metric("Surface Pressure", f"{current.get('surface_pressure', 'N/A')} hPa")
        with d3:
            st.metric("Precip Now", f"{current.get('precipitation', 0)} mm")
        with d4:
            st.metric("Rain Now", f"{current.get('rain', 0)} mm")

    with tab_hourly:
        hours = hourly["time"][:24]
        hour_labels = [t.split("T")[1][:5] for t in hours]

        chart_data = {
            "Time": hour_labels,
            "Temp °F": [round((c * 9 / 5) + 32, 1) for c in hourly["temperature_2m"][:24]],
            "Feels Like °F": [round((c * 9 / 5) + 32, 1) for c in hourly["apparent_temperature"][:24]],
            "Rain %": hourly["precipitation_probability"][:24],
            "Cloud %": hourly["cloud_cover"][:24],
            "Wind mph": [round(v * 0.621371, 1) for v in hourly["wind_speed_10m"][:24]],
        }

        st.line_chart(chart_data, x="Time", y=["Temp °F", "Feels Like °F"])
        st.line_chart(chart_data, x="Time", y=["Rain %", "Cloud %"])
        st.line_chart(chart_data, x="Time", y=["Wind mph"])

    with tab_extended:
        rows = []
        for i in range(len(daily["time"])):
            rows.append({
                "Date": daily["time"][i],
                "Condition": WMO_CODES.get(daily["weather_code"][i], f"Code {daily['weather_code'][i]}"),
                "High": f"{(daily['temperature_2m_max'][i] * 9 / 5) + 32:.1f}°F",
                "Low": f"{(daily['temperature_2m_min'][i] * 9 / 5) + 32:.1f}°F",
                "Rain Chance": f"{daily['precipitation_probability_max'][i]}%",
                "Max Wind": kmh_to_mph(daily["wind_speed_10m_max"][i]),
                "Sunrise": daily["sunrise"][i].split("T")[1],
                "Sunset": daily["sunset"][i].split("T")[1],
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_radar:
        radar_url = f"https://radar.weather.gov/?settings=v1_eyJhZ2VuZGEiOiJsb2NhbCJ9#/@{lat},{lon},9z"
        st.markdown(
            f"""
            <div class="radar-card">
                <h3>Local Weather Radar</h3>
                <p>Open NOAA radar centered near your current position.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button("Open NOAA Radar", radar_url)

except Exception as e:
    st.error(f"Error fetching weather data: {e}")
