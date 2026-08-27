# OpenRoadCode Navigation Command Service IDD

## Interface

The navigation command service is a ZeroMQ REQ/REP interface. The server endpoint is defined by `services.navigation.zeromq_navigation_command_server.DEFAULT_NAVIGATION_COMMAND_ENDPOINT` and may be overridden by runtime configuration.

Each request is one JSON object. Each request receives exactly one JSON response.

## Commands

Versioning is command-semantic rather than envelope-version based in the current interface. The supported command names are:

- `navigation.calibrate_stationary`
- `navigation.reset_heading`
- `navigation.route.calculate`

## Request envelope

```json
{
  "command": "navigation.route.calculate",
  "arguments": {}
}
```

`command` is required. `arguments` is an object and may be empty.

## Response envelope

Successful commands return:

```json
{
  "ok": true,
  "message": "Route calculated",
  "data": {}
}
```

Rejected commands return:

```json
{
  "ok": false,
  "message": "Human-readable failure reason",
  "data": null
}
```

`data` is command-specific and may be omitted or null when the command has no result payload.

## Stationary calibration

Command: `navigation.calibrate_stationary`

Arguments:

| Field | JSON type | Default | Meaning |
| --- | --- | --- | --- |
| `sample_count` | integer | 100 | Number of stationary samples to collect |
| `sample_interval_s` | number | 0.01 | Delay in seconds between samples |

Successful response message: `Stationary calibration complete`.

## Heading reset

Command: `navigation.reset_heading`

Arguments:

| Field | JSON type | Default | Meaning |
| --- | --- | --- | --- |
| `heading_deg` | number | 0.0 | Relative heading to establish, in degrees |

Successful response message: `Heading reset complete`.

## Route calculation

Command: `navigation.route.calculate`

Request example:

```json
{
  "command": "navigation.route.calculate",
  "arguments": {
    "origin": {"latitude": 42.8028, "longitude": -83.0127},
    "destination": {"latitude": 42.3314, "longitude": -83.0458},
    "travel_mode": "AUTO"
  }
}
```

Coordinates in this command interface are decimal degrees. Supported travel-mode names correspond to `TravelMode`: `AUTO`, `BICYCLE`, `PEDESTRIAN`, and `MOTORCYCLE`.

Successful route data has this shape:

```json
{
  "distance_miles": 35.2,
  "duration_seconds": 2700.0,
  "shape": [
    {"latitude": 42.8028, "longitude": -83.0127}
  ],
  "maneuvers": [
    {
      "instruction": "Head south",
      "verbal_instruction": "Head south",
      "distance_miles": 0.4,
      "duration_seconds": 50.0,
      "begin_shape_index": 0,
      "end_shape_index": 4
    }
  ]
}
```

The command contract currently preserves the route-planning domain model's explicitly named mile/second units. This differs intentionally from normalized PUB/SUB telemetry contracts, which use SI units on the wire.

## Error behavior

Unknown commands return `ok=false`. Route calculation also returns `ok=false` when route planning is unavailable, origin/destination objects are missing or malformed, or the travel mode is unsupported. Transport clients may separately raise an error on timeout or malformed response data.

## Ownership

`NavigationCommandService` owns command semantics independently of transport. The ZeroMQ server owns REQ/REP transport only. UI request handlers and `NavigationCommandClient` are clients of this service and must not duplicate command execution policy.

## Versioning

Breaking changes to an existing command's request or response semantics require coordinated client/server updates. If independent compatibility becomes necessary, add an explicit protocol version before introducing incompatible deployed endpoints.
