"""Hardware-free NOAA RF service composition tests."""

from __future__ import annotations

from controllers.weather.noaa_rf_weather_service import NoaaRfWeatherService
from controllers.weather.weather_state import WeatherLocation


class OnlineProvider:
    @property
    def provider_id(self):
        return "online"

    def refresh(self, location):
        raise OSError("offline")


class FakeSubscriber:
    def __init__(self, adapter):
        self.adapter = adapter
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1


def event(area=None):
    return {
        "event": "noaa_forecast_completed",
        "forecast_area": area,
        "forecast_areas": [area] if area else [],
        "source_frequency_hz": 162550000,
        "forecast_cycle": 0,
        "forecast_revision": 1,
        "completed_forecast": {
            "forecast": {"period": "tonight", "conditions": "mostly cloudy"}
        },
    }


def make_service():
    return NoaaRfWeatherService(
        OnlineProvider(),
        area_matches=lambda area, _location: area == "Macomb County",
        clock=lambda: 100.0,
        subscriber_factory=FakeSubscriber,
    )


def test_preview_preserves_unknown_area_without_claiming_locality():
    service = make_service()
    assert service.preview() is None
    service.store.ingest(event())
    preview = service.preview()
    assert preview is not None
    assert preview.period == "tonight"
    assert preview.area is None
    assert not preview.geographically_scoped
    assert preview.frequency_hz == 162550000


def test_service_owns_subscriber_lifecycle():
    service = make_service()
    service.start()
    service.stop()
    assert service.subscriber.starts == 1
    assert service.subscriber.stops == 1


def test_controller_created_by_service_uses_verified_rf_offline():
    service = make_service()
    service.store.ingest(event("Macomb County"))
    controller = service.make_controller(
        fallback_location=WeatherLocation(42.8, -83.0, "Romeo", "test"),
        network_allowed=lambda: False,
    )
    assert controller.refresh().source.provider_id == "noaa_rf"
