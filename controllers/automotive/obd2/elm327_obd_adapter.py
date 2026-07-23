from __future__ import annotations

from hardware_io.automotive.elm327 import (
    Elm327CommandError,
    Elm327ConnectionError,
    Elm327Device,
    Elm327Response,
)
from protocols.can import CanFrame, parse_compact_can_frame
from protocols.obd2 import (
    Obd2AdapterIf,
    Obd2CommandError,
    Obd2ConnectionError,
    Obd2ProtocolError,
    Obd2Request,
    Obd2Response,
)


class Elm327ObdAdapter(Obd2AdapterIf):
    """Translate OBD-II models to and from an ELM327 serial device."""

    _IGNORED_LINES = {"SEARCHING...", "SEARCHING"}
    _NO_RESPONSE_LINES = {"NO DATA", "STOPPED"}
    _ERROR_LINES = {
        "?",
        "BUS ERROR",
        "CAN ERROR",
        "ERROR",
        "UNABLE TO CONNECT",
    }

    def __init__(self, device: Elm327Device | None = None) -> None:
        self._device = device or Elm327Device()

    @property
    def is_connected(self) -> bool:
        return self._device.is_connected

    def connect(self) -> None:
        try:
            self._device.connect()
        except Elm327ConnectionError as exc:
            raise Obd2ConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        self._device.disconnect()

    def request(self, request: Obd2Request) -> tuple[Obd2Response, ...]:
        command = self._format_request(request)
        try:
            raw_response = self._device.send_command(command)
        except Elm327ConnectionError as exc:
            raise Obd2ConnectionError(str(exc)) from exc
        except Elm327CommandError as exc:
            raise Obd2CommandError(str(exc)) from exc

        return self._parse_response(request, raw_response)

    @staticmethod
    def _format_request(request: Obd2Request) -> str:
        command = f"{request.mode:02X}"
        if request.pid is not None:
            command += f"{request.pid:02X}"
        return command

    @classmethod
    def _parse_response(
        cls,
        request: Obd2Request,
        response: Elm327Response,
    ) -> tuple[Obd2Response, ...]:
        parsed: list[Obd2Response] = []

        for original_line in response.lines:
            line = "".join(original_line.upper().split())
            display_line = original_line.strip()

            if not line or line == response.command.replace(" ", "").upper():
                continue
            if display_line.upper() in cls._IGNORED_LINES:
                continue
            if display_line.upper() in cls._NO_RESPONSE_LINES:
                continue
            if display_line.upper() in cls._ERROR_LINES:
                raise Obd2CommandError(
                    f"ELM327 could not complete {response.command}: "
                    f"{display_line}"
                )
            parsed.append(cls._parse_can_frame(request, line))

        return tuple(parsed)

    @staticmethod
    def _parse_can_frame(request: Obd2Request, frame: str) -> Obd2Response:
        try:
            can_frame = parse_compact_can_frame(frame)
        except ValueError as exc:
            raise Obd2ProtocolError(
                f"Malformed ELM327 CAN frame: {frame!r}"
            ) from exc

        return Elm327ObdAdapter._parse_obd_payload(request, can_frame)

    @staticmethod
    def _parse_obd_payload(
        request: Obd2Request,
        frame: CanFrame,
    ) -> Obd2Response:
        payload = frame.data
        if not payload:
            raise Obd2ProtocolError("Empty OBD-II CAN payload")
        if payload[0] == 0x7F:
            code = payload[2] if len(payload) >= 3 else None
            suffix = f" (code 0x{code:02X})" if code is not None else ""
            raise Obd2CommandError(
                f"ECU rejected OBD-II mode 0x{request.mode:02X}{suffix}"
            )

        expected_mode = (request.mode + 0x40) & 0xFF
        if payload[0] != expected_mode:
            raise Obd2ProtocolError(
                f"Expected response mode 0x{expected_mode:02X}, "
                f"received 0x{payload[0]:02X}"
            )

        data_offset = 1
        response_pid: int | None = None
        if request.pid is not None:
            if len(payload) < 2:
                raise Obd2ProtocolError(
                    f"Response is missing PID 0x{request.pid:02X}"
                )
            response_pid = payload[1]
            if response_pid != request.pid:
                raise Obd2ProtocolError(
                    f"Expected PID 0x{request.pid:02X}, "
                    f"received 0x{response_pid:02X}"
                )
            data_offset = 2

        return Obd2Response(
            mode=payload[0],
            pid=response_pid,
            data=payload[data_offset:],
            ecu_id=frame.arbitration_id,
        )
