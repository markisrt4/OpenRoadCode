# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Background NWS alert polling driven by public navigation position telemetry."""
from __future__ import annotations
from datetime import datetime,timezone
import math,threading
from uuid import uuid4
from controllers.weather import WeatherAlertClearReason,WeatherAlertEvent,WeatherAlertOperation,WeatherLocation
from messaging.contracts.navigation import POSITION_STATE_TOPIC,PositionStateMessage,decode_position_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf

class WeatherAlertRuntime:
    def __init__(self,provider,alert_publisher,subscriber:SubscriberIf,*,poll_interval_seconds:float=60.0)->None:
        if poll_interval_seconds<30.0:raise ValueError("weather alert polling interval must be at least 30 seconds")
        self._provider=provider;self._alert_publisher=alert_publisher;self._period_s=poll_interval_seconds
        self._lock=threading.Lock();self._location=None;self._active_alerts={};self._correlations={};self._stop_event=threading.Event()
        self._dispatcher=MessageDispatcher(subscriber);self._dispatcher.register(POSITION_STATE_TOPIC,decode_position_state,self._on_position_state)
    def run(self)->None:
        self._stop_event.clear();self._dispatcher.start()
        try:
            while not self._stop_event.is_set():
                with self._lock:location=self._location
                if location is not None:self.poll_once(location)
                self._stop_event.wait(self._period_s)
        finally:self.close()
    def poll_once(self,location:WeatherLocation)->int:
        alerts=self._provider.active_alerts(location);current={a.identifier:a for a in alerts};published=0
        for identifier,alert in current.items():
            correlation=self._correlations.setdefault(identifier,str(uuid4()))
            if self._active_alerts.get(identifier)!=alert:
                self._alert_publisher.publish(WeatherAlertEvent(alert,correlation,WeatherAlertOperation.ACTIVE));published+=1
        for identifier,alert in self._active_alerts.items():
            if identifier not in current:
                expires=alert.expires_at
                reason=WeatherAlertClearReason.EXPIRED if expires is not None and expires<=datetime.now(timezone.utc) else WeatherAlertClearReason.WITHDRAWN
                self._alert_publisher.publish(WeatherAlertEvent(alert,self._correlations[identifier],WeatherAlertOperation.CLEARED,reason));published+=1
                self._correlations.pop(identifier,None)
        self._active_alerts=current;return published
    def close(self)->None:self._stop_event.set();self._dispatcher.close()
    def _on_position_state(self,message:PositionStateMessage)->None:
        lat=message.data.latitude_rad;lon=message.data.longitude_rad
        if lat is None or lon is None:return
        if message.data.fix_mode is not None and message.data.fix_mode<2:return
        lat_deg=math.degrees(lat);lon_deg=math.degrees(lon)
        with self._lock:self._location=WeatherLocation(latitude=lat_deg,longitude=lon_deg,name=f"{lat_deg:.5f}, {lon_deg:.5f}",source=message.source)
