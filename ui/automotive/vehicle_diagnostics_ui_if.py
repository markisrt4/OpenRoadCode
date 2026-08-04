"""! @brief UI contract and values for vehicle diagnostics."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from ui.automotive.diagnostics_request_handler_if import (
    DiagnosticsRequestHandlerIf,
)
from ui.ui_if import UiIf


class DiagnosticSeverity(Enum):
    """! @brief Driver-facing severity of a diagnostic condition."""

    INFORMATION = auto()
    WARNING = auto()
    CRITICAL = auto()


class DiagnosticStatus(Enum):
    """! @brief ECU-reported state of a diagnostic trouble code."""

    PENDING = auto()
    CONFIRMED = auto()
    PERMANENT = auto()


@dataclass(frozen=True, slots=True)
class DiagnosticTroubleCode:
    """! @brief Describe one vehicle diagnostic trouble code.

    @param code Standard or manufacturer-specific trouble-code identifier.
    @param status ECU-reported status of the code.
    @param severity Driver-facing severity of the condition.
    @param description Human-readable description, or None when unavailable.
    """

    code: str
    status: DiagnosticStatus
    severity: DiagnosticSeverity
    description: str | None = None


class VehicleDiagnosticsUiIf(UiIf, ABC):
    """! @brief Display diagnostics and connect diagnostic request handling."""

    @abstractmethod
    def set_malfunction_indicator(self, active: bool | None) -> None:
        """! @brief Set the malfunction-indicator-lamp state.

        @param active Active state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_trouble_codes(
        self,
        trouble_codes: Sequence[DiagnosticTroubleCode],
    ) -> None:
        """! @brief Replace the complete displayed trouble-code collection.

        @param trouble_codes Current diagnostic trouble codes.
        """
        ...

    @abstractmethod
    def set_emissions_readiness(self, ready: bool | None) -> None:
        """! @brief Set whether all supported emissions monitors are ready.

        @param ready Readiness state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_diagnostics_request_handler(
        self,
        handler: DiagnosticsRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the diagnostics request handler.

        @param handler Request handler, or None to disconnect it.
        """
        ...
