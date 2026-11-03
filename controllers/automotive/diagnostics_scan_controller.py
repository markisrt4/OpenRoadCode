# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own asynchronous scan work and deliver immutable state through a UI dispatcher."""
import threading
from ui.automotive.diagnostics_scan_if import DiagnosticsScanState

_EXPLANATIONS = {
    "P0300": "Random/multiple-cylinder misfire. If shaking or the MIL flashes, stop safely and seek service.",
    "P0171": "Fuel mixture too lean (bank 1). Arrange diagnosis of intake leaks and fuel delivery.",
    "P0420": "Catalyst efficiency below threshold (bank 1). Check related faults before replacing parts.",
    "P0455": "Large evaporative-emissions leak. Check the fuel cap when safely parked; arrange leak testing if persistent.",
}

def present_diagnostics(data):
    codes = data.get("trouble_codes", [])
    complete = set(data.get("completed_services", [])) == {"monitor", "stored", "pending", "permanent"}
    mil = data.get("mil_on")
    ready = data.get("emissions_ready")
    known = mil is not None and ready is not None and bool(data.get("responding_ecus"))
    faulted = bool(codes) or mil is True or bool(data.get("stored_dtc_count"))
    status = "faulted" if faulted else "healthy" if complete and known and ready else "unavailable"
    summary = ("Diagnostic faults reported" if faulted else
               "No generic emissions faults reported" if status == "healthy" else
               "Diagnostic coverage incomplete" if not complete or not known else
               "Emissions monitors not ready")
    details = [
        "MIL / Check Engine: " + ("ON" if mil is True else "OFF" if mil is False else "unknown"),
        "Readiness: " + ("ready" if ready is True else "not ready" if ready is False else "unknown"),
        "Stored count: " + str(data.get("stored_dtc_count")),
    ]
    for name in ("stored", "pending", "permanent"):
        group = [item for item in codes if item.get("status") == name]
        details.append(name.title() + ": " + (", ".join(item["code"] for item in group) or
                       ("none" if name in data.get("completed_services", []) else "unavailable")))
    for item in codes:
        ecu = item.get("ecu_id")
        source = f"0x{ecu:X}" if isinstance(ecu, int) else "unknown"
        details.append(f"{item['code']} ({item.get('status', 'unknown')}, ECU {source}): " +
                       _EXPLANATIONS.get(item["code"], "Consult vehicle-specific service information."))
    ecus = data.get("responding_ecus", [])
    details.append("ECU source: " + (", ".join(f"0x{ecu:X}" for ecu in ecus) or "unknown / no identified ECU"))
    details.append("Services responding: " + (", ".join(data.get("completed_services", [])) or "none"))
    details.append("Read-only generic OBD-II scan; other vehicle systems may have faults. Codes alone do not identify a failed part.")
    return DiagnosticsScanState(status=status, summary=summary, details="\n".join(details))

class DiagnosticsScanController:
    def __init__(self, scan, dispatcher):
        self._scan = scan
        self._dispatcher = dispatcher
        self._state = DiagnosticsScanState()
        self._observers = []
        self._closed = False
        self._busy = False
        self._generation = 0

    def observe(self, callback):
        self._observers.append(callback)
        callback(self._state)
        def remove():
            if callback in self._observers:
                self._observers.remove(callback)
        return remove

    def _publish(self, state):
        self._state = state
        for observer in tuple(self._observers):
            observer(state)

    def request_scan(self):
        if self._closed or self._busy:
            return
        self._busy = True
        self._generation += 1
        generation = self._generation
        self._publish(DiagnosticsScanState(scanning=True, summary="Scanning vehicle diagnostics…"))
        threading.Thread(target=self._work, args=(generation,), daemon=True,
                         name="diagnostics-ui-worker").start()

    def _work(self, generation):
        try:
            state = present_diagnostics(self._scan())
        except Exception as exc:
            state = DiagnosticsScanState(summary="Diagnostics unavailable", details=str(exc))
        self._dispatcher.dispatch_ui(lambda: self._complete(generation, state))

    def _complete(self, generation, state):
        if self._closed or generation != self._generation:
            return
        self._busy = False
        self._publish(state)

    def close(self):
        self._closed = True
        self._generation += 1
        self._observers.clear()
