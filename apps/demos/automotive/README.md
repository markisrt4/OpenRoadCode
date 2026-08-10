# Automotive UI contract demo

This standard-library `curses` application demonstrates the automotive UI
contracts with simulated SI data arriving at different update rates.

Run it from the repository root:

```sh
python3 -m apps.demos.automotive.main
```

Keys:

- `q` or Escape: quit
- `u`: toggle metric and imperial presentation
- `c`: request that the simulated diagnostic codes be cleared

The simulator supplies only canonical SI values. Unit conversion is performed
inside the UI implementation.
