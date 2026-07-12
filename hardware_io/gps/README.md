# GPS Reader

The `GpsReader` provides a simple interface for reading GPS data from `gpsd`.

It monitors GPS position reports and returns the latest values as a `GpsData` object.

## GPS Data

The following values are reported:

- Latitude
- Longitude
- Altitude
- Speed
- Track
- GPS fix mode

The `GpsReader` only reports data received from the GPS service. Application-specific interpretation and behavior should be handled by higher-level components.

## Example

```python
from hardware_io.gps import GpsData, GpsReader


def gps_data_received(data: GpsData) -> None:
    print(
        f"lat={data.latitude} "
        f"lon={data.longitude} "
        f"speed={data.speed}"
    )


reader = GpsReader(callback=gps_data_received)
reader.start()
```

## CLI Test

A simple CLI test application is provided in the `test` directory.

Run the test from the project root:

```bash
python3 -m hardware_io.gps.test.gps_cli
```

Press `Ctrl+C` to stop the reader.

## Dependency

The GPS reader requires `gpsd` and the Python GPS bindings.

On Debian or Raspberry Pi OS:

```bash
sudo apt install gpsd gpsd-clients python3-gps
```

The `gpsd` service must be running and configured to use the connected GPS device.
