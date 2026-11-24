# SDR controllers

ORC consumes libSDRForge spectrum and receiver data. RF control and receiver orchestration live in [controllers/radio](../radio/README.md). Native presentation owns display controls; the shared RF service owns acquisition and DSP.

See [RF radio contracts](../../docs/rf_radio.md) and the [Ethernet IDD](../../docs/ethernet_idd.md) for interface responsibilities.
