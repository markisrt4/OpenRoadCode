# Rigctl Protocol

A small, dependency-free Python client for controlling a Hamlib-style `rigctl`
TCP server, including the SDR++ `\start` and `\stop` extensions used by 
applications.

This directory belongs in the protocol layer. It knows how to format and send
rigctl commands, but it does not decide what a higher-level application action means.

## Contents

```text
rigctl_protocol/
├── __init__.py
├── rigctl_client.py
├── README.md
└── component_test/
    ├── __init__.py
    ├── rigctl_cli.py
    └── test_rigctl_component.py
└── emulator/
    ├── __init__.py 
    └── example_rigctl_server.py
└── emulator/
```

- `rigctl_client.py`: reusable TCP client.
- `rigctl_cli.py`: one-shot and interactive command-line test client.
- `component_test/test_rigctl_component`: end-to-end tests using a real localhost TCP connection.
- `emulator/example_rigctl_server.py`: stateful local server for development.

## Requirements

Python 3.10 or newer is recommended. No third-party libraries are required.
Everything uses the Python standard library.

## Supported Client Operations

| Client method | Wire command | Purpose |
|---|---|---|
| `set_frequency(hz)` | `F <hz>` | Set frequency in hertz |
| `get_frequency()` | `f` | Read frequency |
| `set_mode(mode, bandwidth)` | `M <mode> <bandwidth>` | Set mode and bandwidth |
| `start()` | `\start` | Start receiver playback |
| `stop()` | `\stop` | Stop receiver playback |
| `get_signal_strength()` | `l STRENGTH` | Read signal strength |
| `get_snr()` | `l SNR` | Read SNR |
| `get_rds()` | `l RDS` | Read RDS text |
| `send(command)` | raw | Send any command |

`NFM` is preserved as `NFM` for SDRForge. Unknown mode names are
uppercased and passed through unchanged.

## Basic Library Use

```python
from protocols.rigctl import RigctlClient

client = RigctlClient(host="127.0.0.1", port=4532)

client.start()
client.set_frequency(101_100_000)
client.set_mode("WFM", 200_000)

print(client.get_frequency())
print(client.get_signal_strength())
print(client.get_rds())
```

The client opens a new TCP connection for each command. This keeps it stateless
and matches the simple request/response behavior expected by this package.

## Run the Example Server

From the package directory:

```bash
python3 example_rigctl_server.py --verbose
```

The default endpoint is `127.0.0.1:4532`. Use a different port when SDRForge is
already using 4532:

```bash
python3 example_rigctl_server.py --port 14532 --verbose
```

The example server supports the commands used by `RigctlClient`, plus `m` to
read the current mode and bandwidth. It is a development fixture, not a full
Hamlib implementation and, tragically, does not actually demodulate radio.

## Use the CLI

Run one command:

```bash
python3 rigctl_cli.py --port 14532 set-frequency 101100000
python3 rigctl_cli.py --port 14532 get-frequency
python3 rigctl_cli.py --port 14532 set-mode NFM 12500
python3 rigctl_cli.py --port 14532 strength
python3 rigctl_cli.py --port 14532 raw m
```

Open an interactive raw-command prompt:

```bash
python3 rigctl_cli.py --port 14532 interactive
```

Example session:

```text
rigctl> F 101100000
RPRT 0
rigctl> f
101100000
rigctl> M NFM 12500
RPRT 0
rigctl> quit
```

## Run the Component Tests

From the package directory:

```bash
python3 -m unittest discover -s component_test -v
```

Or run the component-test file directly:

```bash
python3 component_test/test_rigctl_component.py
```

The tests start the example server on an automatically assigned localhost port,
exercise the real client over TCP, and shut the server down afterward. They do
not require SDR++ and do not occupy port 4532.

## Testing Against SDRForge

1. Start the SDRForge service with its rigctl endpoint enabled.
2. Confirm its host and TCP port, commonly `127.0.0.1:4532`.
3. Run CLI checks such as:

```bash
python3 rigctl_cli.py get-frequency
python3 rigctl_cli.py set-frequency 162550000
python3 rigctl_cli.py set-mode NFM 12500
python3 rigctl_cli.py start
```

Be aware that commands and returned level formats can vary between rigctl server
implementations. The `\start`, `\stop`, and `l RDS` commands are historical SDR++-originated
extensions rather than portable Hamlib operations.

## Error Behavior

- Socket and connection failures are allowed to propagate as `OSError` from the
  library so callers can distinguish timeout, refused connection, and network
  failures.
- A read timeout after a successful send returns an empty string because some
  servers do not reply to every command.
- Invalid local arguments raise `ValueError` before opening a socket.
- The example server returns `RPRT 0` for success, `RPRT -1` for invalid values,
  and `RPRT -4` for unsupported commands.
