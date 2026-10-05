# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concurrent navigation and UI publications retain complete bus framing."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
import time
from unittest.mock import Mock, patch

from messaging.zeromq.publisher import ZeroMqPublisher


class RecordingSocket:
    def __init__(self):
        self.pending = []
        self.messages = []

    def connect(self, endpoint):
        pass

    def send_string(self, topic, flags):
        self.pending.append(topic.encode())
        time.sleep(0.001)  # Allow the other producer between multipart frames.

    def send_json(self, payload):
        self.pending.append(json.dumps(payload).encode())
        self.messages.append(self.pending)
        self.pending = []

    def send_multipart(self, frames):
        # Simulate GIL-releasing transport work within a multipart send.
        self.pending.append(frames[0])
        time.sleep(0.001)
        self.pending.append(frames[1])
        self.messages.append(self.pending)
        self.pending = []

    def close(self, linger):
        assert not self.pending


def test_parallel_camera_and_marker_publications_keep_two_matching_frames():
    socket = RecordingSocket()
    context = Mock()
    context.socket.return_value = socket
    with patch("messaging.zeromq.publisher.zmq.Context", return_value=context):
        publisher = ZeroMqPublisher()
        barrier = Barrier(4)

        def produce(worker):
            barrier.wait(timeout=2)
            for sequence in range(20):
                publisher.publish(f"producer.{worker}", {"worker": worker, "sequence": sequence})

        try:
            with ThreadPoolExecutor(max_workers=4) as workers:
                list(workers.map(produce, range(4)))
            assert len(socket.messages) == 80
            for frames in socket.messages:
                assert len(frames) == 2
                payload = json.loads(frames[1])
                assert frames[0].decode() == f"producer.{payload['worker']}"
        finally:
            publisher.close()
