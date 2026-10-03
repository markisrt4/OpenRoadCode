# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""The city subscription must transport replies independently of POI topics."""

import json
from time import monotonic, sleep

import zmq

from messaging.zeromq.subscriber import ZeroMqSubscriber
from protocols.map_renderer.map_weather_city_source import MapWeatherCitySource, RawWeatherCity


def test_city_subscription_receives_named_locations_and_preserves_request_id():
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    port = publisher.bind_to_random_port('tcp://127.0.0.1')
    source = MapWeatherCitySource(subscriber=ZeroMqSubscriber(f'tcp://127.0.0.1:{port}'))
    try:
        payload = {'request_id': 42, 'cities': [{'name': 'Detroit', 'latitude': 42.33, 'longitude': -83.05}]}
        deadline = monotonic() + 3
        reply = None
        while monotonic() < deadline and reply is None:
            publisher.send_multipart([b'map.poi.search_result', json.dumps(payload).encode()])
            publisher.send_multipart([b'map.weather.cities', json.dumps(payload).encode()])
            sleep(.03)  # Retry across PUB/SUB subscription startup, rather than assuming socket readiness.
            reply = source.poll()
        assert reply == (42, (RawWeatherCity('Detroit', 42.33, -83.05),))
    finally:
        source.close()
        publisher.close(linger=0)
        context.term()
