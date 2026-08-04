"""Concrete no-op vehicle diagnostics UI implementation."""

from collections.abc import Sequence

from ui.automotive.diagnostics_request_handler_if import (
    DiagnosticsRequestHandlerIf,
)
from ui.automotive.vehicle_diagnostics_ui_if import (
    DiagnosticTroubleCode,
    VehicleDiagnosticsUiIf,
)
from ui.ui_stub import UiStub


class VehicleDiagnosticsUiStub(UiStub, VehicleDiagnosticsUiIf):
    """Ignore vehicle diagnostic updates and request-handler registration."""

    def set_malfunction_indicator(self, active: bool | None) -> None:
        pass

    def set_trouble_codes(
        self,
        trouble_codes: Sequence[DiagnosticTroubleCode],
    ) -> None:
        pass

    def set_emissions_readiness(self, ready: bool | None) -> None:
        pass

    def set_diagnostics_request_handler(
        self,
        handler: DiagnosticsRequestHandlerIf | None,
    ) -> None:
        pass
