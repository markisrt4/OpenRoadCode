# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Generic SAE J1979 vehicle diagnostics over an OBD-II adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from protocols.obd2 import Obd2AdapterIf, Obd2Request, Obd2Response


class Obd2DiagnosticStatus(Enum):
    """Service that reported a diagnostic trouble code."""

    STORED = auto()
    PENDING = auto()
    PERMANENT = auto()


@dataclass(frozen=True, slots=True)
class Obd2DiagnosticTroubleCode:
    """One generic OBD-II DTC, retaining its reporting ECU and status."""

    code: str
    status: Obd2DiagnosticStatus
    ecu_id: int | None = None


@dataclass(frozen=True, slots=True)
class Obd2DiagnosticsSnapshot:
    """Semantic result of one generic OBD-II diagnostic scan."""

    mil_on: bool | None
    stored_dtc_count: int | None
    emissions_ready: bool | None
    responding_ecus: tuple[int, ...]
    trouble_codes: tuple[Obd2DiagnosticTroubleCode, ...]


class Obd2DiagnosticsScanSession:
    """Accumulate one diagnostic scan through single-request scheduler steps."""

    REQUESTS = (
        Obd2Request(mode=0x01, pid=0x01),
        Obd2Request(mode=0x03),
        Obd2Request(mode=0x07),
        Obd2Request(mode=0x0A),
    )

    def __init__(self) -> None:
        self._responses: list[tuple[Obd2Response, ...]] = []

    @property
    def complete(self) -> bool:
        """Return whether every diagnostic service has been sampled."""
        return len(self._responses) == len(self.REQUESTS)

    @property
    def next_request(self) -> Obd2Request | None:
        """Return the next request, or None when the scan is complete."""
        if self.complete:
            return None
        return self.REQUESTS[len(self._responses)]

    def accept(self, responses: tuple[Obd2Response, ...]) -> None:
        """Store responses for the current step and advance the session."""
        if self.complete:
            raise RuntimeError("diagnostic scan is already complete")
        self._responses.append(tuple(responses))

    def snapshot(self) -> Obd2DiagnosticsSnapshot:
        """Build the semantic result after all scheduled steps complete."""
        if not self.complete:
            raise RuntimeError("diagnostic scan is not complete")
        monitor, stored, pending, permanent = self._responses
        return Obd2DiagnosticsScanner.decode(monitor, stored, pending, permanent)


class Obd2DiagnosticsScanner:
    """Read generic emissions diagnostics without owning adapter lifecycle."""

    def __init__(self, adapter: Obd2AdapterIf) -> None:
        self._adapter = adapter

    def scan(self) -> Obd2DiagnosticsSnapshot:
        session = self.create_session()
        while (request := session.next_request) is not None:
            session.accept(self._adapter.request(request))
        return session.snapshot()

    @staticmethod
    def create_session() -> Obd2DiagnosticsScanSession:
        """Create a scan that a low-bandwidth scheduler can advance."""
        return Obd2DiagnosticsScanSession()

    @staticmethod
    def decode(
        monitor: tuple[Obd2Response, ...],
        stored: tuple[Obd2Response, ...],
        pending: tuple[Obd2Response, ...],
        permanent: tuple[Obd2Response, ...],
    ) -> Obd2DiagnosticsSnapshot:
        """Decode four generic diagnostic-service response groups."""
        valid_monitor = tuple(response for response in monitor if response.data)
        ecu_ids = tuple(sorted({
            response.ecu_id
            for responses in (monitor, stored, pending, permanent)
            for response in responses
            if response.ecu_id is not None
        }))

        mil_on = (
            None
            if not valid_monitor
            else any(bool(response.data[0] & 0x80) for response in valid_monitor)
        )
        stored_count = (
            None
            if not valid_monitor
            else max(response.data[0] & 0x7F for response in valid_monitor)
        )

        readiness = [
            Obd2DiagnosticsScanner._decode_readiness(response)
            for response in valid_monitor
            if len(response.data) >= 4
        ]
        emissions_ready = None if not readiness else all(readiness)

        trouble_codes = (
            Obd2DiagnosticsScanner._decode_dtcs(stored, Obd2DiagnosticStatus.STORED)
            + Obd2DiagnosticsScanner._decode_dtcs(pending, Obd2DiagnosticStatus.PENDING)
            + Obd2DiagnosticsScanner._decode_dtcs(
                permanent, Obd2DiagnosticStatus.PERMANENT
            )
        )
        return Obd2DiagnosticsSnapshot(
            mil_on=mil_on,
            stored_dtc_count=stored_count,
            emissions_ready=emissions_ready,
            responding_ecus=ecu_ids,
            trouble_codes=trouble_codes,
        )

    @staticmethod
    def _decode_readiness(response: Obd2Response) -> bool:
        # PID 01 bytes B-D encode supported and incomplete monitors. Continuous
        # monitors use B[6:4] for support and B[2:0] for incomplete state.
        _, byte_b, byte_c, byte_d = response.data[:4]
        continuous_supported = (byte_b >> 4) & 0x07
        continuous_incomplete = byte_b & 0x07
        if continuous_supported & continuous_incomplete:
            return False
        # For non-continuous monitors, byte C marks support and byte D marks
        # incomplete state. Bit assignments depend on spark/compression ignition,
        # but the support/incomplete pairing is identical for this aggregate.
        return (byte_c & byte_d) == 0

    @classmethod
    def _decode_dtcs(
        cls,
        responses: tuple[Obd2Response, ...],
        status: Obd2DiagnosticStatus,
    ) -> tuple[Obd2DiagnosticTroubleCode, ...]:
        decoded: list[Obd2DiagnosticTroubleCode] = []
        for response in responses:
            for offset in range(0, len(response.data) - 1, 2):
                first, second = response.data[offset], response.data[offset + 1]
                if first == 0 and second == 0:
                    continue
                decoded.append(
                    Obd2DiagnosticTroubleCode(
                        code=cls._decode_dtc_word(first, second),
                        status=status,
                        ecu_id=response.ecu_id,
                    )
                )
        return tuple(decoded)

    @staticmethod
    def _decode_dtc_word(first: int, second: int) -> str:
        families = "PCBU"
        return (
            f"{families[(first >> 6) & 0x03]}"
            f"{(first >> 4) & 0x03:X}"
            f"{first & 0x0F:X}"
            f"{(second >> 4) & 0x0F:X}"
            f"{second & 0x0F:X}"
        )
