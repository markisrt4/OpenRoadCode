# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own asynchronous scan work and deliver immutable state through a UI dispatcher."""
import threading
from dataclasses import replace
from datetime import datetime, timezone
from ui.automotive.diagnostics_scan_if import DiagnosticFaultCard, DiagnosticsScanState

_FAULT_GUIDANCE = {
    "P0300": (
        "Engine misfire", "The engine computer detected uneven firing in multiple cylinders.",
        "If the engine shakes badly or the Check Engine light flashes, stop safely and seek service. "
        "Otherwise, arrange diagnosis soon; a code alone does not identify the cause.",
    ),
    "P0171": (
        "Lean fuel mixture", "The engine reports too much air or too little fuel on one side of the engine.",
        "Arrange a check for intake leaks, fuel delivery and sensor readings before replacing parts.",
    ),
    "P0420": (
        "Reduced exhaust cleaning", "The vehicle reports that its catalytic converter is not cleaning exhaust as effectively as expected.",
        "Arrange diagnosis and check related faults first. This result alone does not prove the converter needs replacement.",
    ),
    "P0455": (
        "Fuel-vapor system leak", "The system that contains fuel vapors reports a large leak, which can include a loose fuel cap.",
        "When safely parked, check that the fuel cap is fitted correctly. If the fault persists, arrange leak testing.",
    ),
}
_REPORTING = {"stored": "Confirmed fault", "pending": "Possible problem · not yet confirmed",
              "permanent": "Retained emissions record"}


def _fault_card(item):
    title, explanation, recommendation = _FAULT_GUIDANCE.get(item["code"], (
        "Vehicle-reported fault", "The vehicle reported a fault that needs vehicle-specific interpretation.",
        "Have the code checked against service information for your vehicle. Do not replace parts based on the code alone.",
    ))
    status = item.get("status", "unknown")
    if status == "pending":
        explanation += " This is a pending report; it has not yet become a confirmed fault."
    elif status == "permanent":
        explanation += " This retained record can remain after a repair; it does not by itself prove the problem is still active."
        recommendation = ("Review any confirmed or pending faults and the vehicle's repair history. "
                          "The vehicle computer removes a permanent record after its required checks pass.")
    return DiagnosticFaultCard(title, _REPORTING.get(status, "Reporting status unavailable"),
                               explanation, recommendation, item["code"], item.get("ecu_id"))

def present_diagnostics(data, *, completed_at=None):
    codes = data.get("trouble_codes", [])
    complete = set(data.get("completed_services", [])) == {"monitor", "stored", "pending", "permanent"}
    mil = data.get("mil_on")
    ready = data.get("emissions_ready")
    known = mil is not None and ready is not None and bool(data.get("responding_ecus"))
    faulted = bool(codes) or mil is True or bool(data.get("stored_dtc_count"))
    coverage_complete = complete and known
    status = ("faulted" if faulted else "unavailable" if not coverage_complete else
              "not_ready" if ready is False else "healthy")
    summary = ("Faults found" if faulted else "No emissions faults reported" if status == "healthy" else
               "Emissions checks not ready" if status == "not_ready" else "Scan incomplete")
    coverage_message = (
        "All requested emissions checks responded. Other vehicle systems are outside this scan."
        if coverage_complete else
        "Scan incomplete: some diagnostic information is unavailable. Other faults may be present."
    )
    next_action = (
        "Review the reported conditions below. A fault code alone does not identify a failed part."
        if faulted else
        "Unfinished emissions checks do not necessarily mean a fault. Checks may reset after battery work or repairs. "
        "Follow vehicle-specific guidance; readiness cannot be guaranteed by driving a fixed distance."
        if status == "not_ready" else
        "Check the vehicle connection and try again. Missing responses are not evidence that the vehicle is fault-free."
        if status == "unavailable" else
        "No faults were reported by the emissions checks in this scan. Have unusual symptoms or other warning lights checked."
    )
    faults = tuple(_fault_card(item) for item in codes)
    if faulted and not faults:
        faults = (DiagnosticFaultCard(
            "Check Engine light is on" if mil else "Stored faults reported", "Fault information incomplete",
            "The vehicle reports a diagnostic warning, but this scan did not retrieve its fault descriptions.",
            "Try another scan and arrange vehicle-specific diagnosis if the warning remains.",
        ),)
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
                       _fault_card(item).title + ". " + _fault_card(item).explanation)
    ecus = data.get("responding_ecus", [])
    details.append("ECU source: " + (", ".join(f"0x{ecu:X}" for ecu in ecus) or "unknown / no identified ECU"))
    details.append("Services responding: " + (", ".join(data.get("completed_services", [])) or "none"))
    details.append("Read-only generic OBD-II scan; other vehicle systems may have faults. Codes alone do not identify a failed part.")
    return DiagnosticsScanState(
        status=status, summary=summary, details="\n".join(details), faults=faults,
        mil_on=mil, emissions_ready=ready, coverage_complete=coverage_complete,
        coverage_message=coverage_message, next_action=next_action,
        completed_at=completed_at or datetime.now(timezone.utc),
        scan_available=True, connection_message="Vehicle connected — ready to scan.",
    )

class DiagnosticsScanController:
    def __init__(self, scan, dispatcher, *, availability=None):
        self._scan = scan
        self._dispatcher = dispatcher
        self._state = DiagnosticsScanState()
        self._observers = []
        self._closed = False
        self._busy = False
        self._generation = 0
        self._availability = availability
        self._available = False
        self._connection_timer = None
        self._monitoring = False

    def start(self):
        """Monitor the service connection without blocking the UI or adapter owner."""
        if self._closed or self._monitoring or self._availability is None:
            return
        self._monitoring = True
        self._poll_connection()

    def _poll_connection(self):
        self._connection_timer = None
        if self._closed:
            return
        if self._busy:
            self._schedule_connection_check()
            return
        generation = self._generation
        def check():
            try:
                available = self._availability() is True
            except Exception:
                available = False
            self._dispatcher.dispatch_ui(lambda: self._connection_checked(generation, available))
        threading.Thread(target=check, name="diagnostics-connection", daemon=True).start()

    def _connection_checked(self, generation, available):
        if self._closed:
            return
        if generation == self._generation and not self._busy:
            self.set_connection_available(available)
        self._schedule_connection_check()

    def _schedule_connection_check(self):
        if not self._closed:
            self._connection_timer = self._dispatcher.schedule_ui_callback(1500, self._poll_connection)

    def set_connection_available(self, available: bool):
        """Apply an observed connection state on the UI-dispatch thread."""
        if self._closed:
            return
        self._available = available
        self._publish(replace(self._state, scan_available=available,
            connection_message="Vehicle connected — ready to scan." if available else
            "Vehicle diagnostics unavailable. Connect the automotive source to scan."))

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
        if self._closed or self._busy or not self._available:
            return
        self._busy = True
        self._generation += 1
        generation = self._generation
        self._publish(DiagnosticsScanState(
            scanning=True, status="scanning", summary="Scanning vehicle diagnostics…",
            coverage_message="Reading available emissions checks. Live telemetry continues.",
            next_action="Please wait for the scan to finish.",
            scan_available=True, connection_message="Vehicle connected — scan in progress.",
        ))
        threading.Thread(target=self._work, args=(generation,), daemon=True,
                         name="diagnostics-ui-worker").start()

    def _work(self, generation):
        try:
            state = present_diagnostics(self._scan())
        except Exception as exc:
            state = DiagnosticsScanState(
                summary="Diagnostics unavailable", details=f"{type(exc).__name__}: {exc}",
                coverage_message="The scan could not finish. No fault-free result is available.",
                next_action="Check that the automotive service and vehicle connection are running, then try again.",
            )
        self._dispatcher.dispatch_ui(lambda: self._complete(generation, state))

    def _complete(self, generation, state):
        if self._closed or generation != self._generation:
            return
        self._busy = False
        if state.completed_at is None:
            self._available = False
        self._publish(replace(state, scan_available=self._available,
            connection_message="Vehicle connected — ready to scan." if self._available else
            "Vehicle diagnostics unavailable. Check the connection and try again."))

    def close(self):
        self._closed = True
        if self._connection_timer is not None:
            self._dispatcher.cancel_ui_callback(self._connection_timer)
            self._connection_timer = None
        self._generation += 1
        self._observers.clear()
