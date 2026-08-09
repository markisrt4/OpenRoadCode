"""Concrete no-op system diagnostics UI implementation."""

from ui.system.diagnostics_ui_if import SystemDiagnostics, SystemDiagnosticsUiIf


class SystemDiagnosticsUiStub(SystemDiagnosticsUiIf):
    """Ignore host diagnostics updates."""

    def set_diagnostics(self, diagnostics: SystemDiagnostics | None) -> None:
        pass
