# Automotive diagnostics command service IDD

The automotive service owns the ELM327/OBD-II adapter and its low-bandwidth
request budget. Diagnostic clients therefore use a ZeroMQ JSON request/reply
endpoint rather than opening the adapter directly.

The default endpoint is `tcp://127.0.0.1:5561`, configurable through
`[services.automotive].command_endpoint`.

## Scan request

```json
{"command":"scan_diagnostics","arguments":{}}
```

The service queues four generic SAE J1979 requests into the existing OBD polling
cadence: monitor status, stored DTCs, pending DTCs, and permanent DTCs. At most
one physical request is issued per service tick.

## Successful response

```json
{
  "ok": true,
  "message": "Vehicle diagnostic scan complete",
  "data": {
    "mil_on": false,
    "stored_dtc_count": 0,
    "emissions_ready": true,
    "responding_ecus": [2024],
    "trouble_codes": []
  }
}
```

Each trouble-code entry contains `code`, `status` (`STORED`, `PENDING`, or
`PERMANENT`), and nullable `ecu_id`. Failures return `ok: false` and a message.
Clearing codes is intentionally outside this read-only contract.
