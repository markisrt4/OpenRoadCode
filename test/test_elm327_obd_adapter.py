import unittest
from unittest.mock import patch

from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from hardware_io.automotive.elm327 import (
    Elm327CommandError,
    Elm327ConnectionError,
    Elm327Device,
    Elm327Response,
)
from protocols.obd2 import (
    Obd2CommandError,
    Obd2ProtocolError,
    Obd2Request,
    Obd2Response,
)


class FakeElm327Device:
    def __init__(self, response: Elm327Response) -> None:
        self.response = response
        self.is_connected = True
        self.commands: list[str] = []

    def connect(self) -> None:
        self.is_connected = True

    def disconnect(self) -> None:
        self.is_connected = False

    def send_command(self, command: str) -> Elm327Response:
        self.commands.append(command)
        return self.response


class Elm327ObdAdapterTests(unittest.TestCase):
    def test_parses_captured_rpm_response(self) -> None:
        device = FakeElm327Device(
            Elm327Response(
                command="010C",
                raw="SEARCHING...\r7E804410C09D2\r\r>",
                lines=("SEARCHING...", "7E804410C09D2"),
            )
        )
        adapter = Elm327ObdAdapter(device)  # type: ignore[arg-type]

        responses = adapter.request(Obd2Request(mode=0x01, pid=0x0C))

        self.assertEqual(device.commands, ["010C"])
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].ecu_id, 0x7E8)
        self.assertEqual(responses[0].mode, 0x41)
        self.assertEqual(responses[0].pid, 0x0C)
        self.assertEqual(responses[0].data, bytes.fromhex("09D2"))

    def test_parses_captured_supported_pid_response(self) -> None:
        response = Elm327Response(
            command="0100",
            raw="SEARCHING...\r7E8064100BE3EA813\r\r>",
            lines=("SEARCHING...", "7E8064100BE3EA813"),
        )

        parsed = Elm327ObdAdapter._parse_response(
            Obd2Request(mode=0x01, pid=0x00), response
        )

        self.assertEqual(parsed[0].data, bytes.fromhex("BE3EA813"))

    def test_preserves_responses_from_multiple_ecus(self) -> None:
        response = Elm327Response(
            command="010C",
            raw="7E804410C09D2\r7E904410C0A00\r>",
            lines=("7E804410C09D2", "7E904410C0A00"),
        )

        parsed = Elm327ObdAdapter._parse_response(
            Obd2Request(mode=0x01, pid=0x0C), response
        )

        self.assertEqual([item.ecu_id for item in parsed], [0x7E8, 0x7E9])

    def test_no_data_returns_empty_tuple(self) -> None:
        response = Elm327Response(
            command="010C", raw="NO DATA\r>", lines=("NO DATA",)
        )

        parsed = Elm327ObdAdapter._parse_response(
            Obd2Request(mode=0x01, pid=0x0C), response
        )

        self.assertEqual(parsed, ())

    def test_adapter_error_raises_command_error(self) -> None:
        response = Elm327Response(command="010C", raw="?\r>", lines=("?",))

        with self.assertRaises(Obd2CommandError):
            Elm327ObdAdapter._parse_response(
                Obd2Request(mode=0x01, pid=0x0C), response
            )

    def test_rejects_incorrect_declared_length(self) -> None:
        response = Elm327Response(
            command="010C", raw="7E806410C09D2\r>", lines=("7E806410C09D2",)
        )

        with self.assertRaises(Obd2ProtocolError):
            Elm327ObdAdapter._parse_response(
                Obd2Request(mode=0x01, pid=0x0C), response
            )


class Elm327DeviceTests(unittest.TestCase):
    def test_initialization_failure_is_reported_as_connection_error(self) -> None:
        class FakeSerial:
            is_open = True

            def close(self) -> None:
                self.is_open = False

        device = Elm327Device()
        with (
            patch(
                "hardware_io.automotive.elm327.elm327_device.serial.Serial",
                return_value=FakeSerial(),
            ),
            patch.object(
                device,
                "_initialize",
                side_effect=Elm327CommandError("ELM327 command failed: ATZ"),
            ),
        ):
            with self.assertRaises(Elm327ConnectionError):
                device.connect()

        self.assertFalse(device.is_connected)

class FakeObd2Adapter:
    def __init__(self) -> None:
        self.is_connected = True
        self.requests: list[int | None] = []

    def connect(self) -> None:
        self.is_connected = True

    def disconnect(self) -> None:
        pass

    def request(self, request: Obd2Request) -> tuple[Obd2Response, ...]:
        self.requests.append(request.pid)
        if request.pid == 0x0C:
            return (
                Obd2Response(
                    mode=0x41,
                    pid=0x0C,
                    data=bytes.fromhex("09D2"),
                    ecu_id=0x7E8,
                ),
            )
        return ()


class Obd2ManagerTests(unittest.TestCase):
    def test_decodes_first_ecu_response_and_handles_no_data(self) -> None:
        manager = Obd2Manager(FakeObd2Adapter())

        state = manager.read_state()

        self.assertEqual(state.rpm, 628.5)
        self.assertIsNone(state.speed_mph)

    def test_supported_pid_discovery_skips_unsupported_requests(self) -> None:
        class SupportedPidAdapter(FakeObd2Adapter):
            def request(
                self, request: Obd2Request
            ) -> tuple[Obd2Response, ...]:
                self.requests.append(request.pid)
                if request.pid == 0x00:
                    return (
                        Obd2Response(
                            mode=0x41,
                            pid=0x00,
                            data=bytes.fromhex("00100000"),
                            ecu_id=0x7E8,
                        ),
                    )
                if request.pid == 0x0C:
                    return (
                        Obd2Response(
                            mode=0x41,
                            pid=0x0C,
                            data=bytes.fromhex("09D2"),
                            ecu_id=0x7E8,
                        ),
                    )
                return ()

        adapter = SupportedPidAdapter()
        manager = Obd2Manager(adapter)

        manager.connect()
        state = manager.read_state()

        self.assertEqual(state.rpm, 628.5)
        self.assertEqual(adapter.requests, [0x00, 0x0C])

    def test_slow_values_are_cached_between_fast_polls(self) -> None:
        class PollingAdapter(FakeObd2Adapter):
            def request(
                self, request: Obd2Request
            ) -> tuple[Obd2Response, ...]:
                self.requests.append(request.pid)
                if request.pid == 0x05:
                    return (
                        Obd2Response(
                            mode=0x41,
                            pid=0x05,
                            data=bytes([120]),
                            ecu_id=0x7E8,
                        ),
                    )
                return super().request(request)

        adapter = PollingAdapter()
        manager = Obd2Manager(
            adapter,
            slow_poll_interval_seconds=60.0,
        )

        first = manager.read_state()
        second = manager.read_state()

        self.assertEqual(first.coolant_temp_f, 176.0)
        self.assertEqual(second.coolant_temp_f, 176.0)
        self.assertEqual(adapter.requests.count(0x05), 1)


if __name__ == "__main__":
    unittest.main()
