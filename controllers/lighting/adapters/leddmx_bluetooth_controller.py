"""Backward-compatible import for the transport-injected LEDDMX controller."""

from controllers.lighting.adapters.leddmx_controller import LedDmxController

LedDmxBluetoothController = LedDmxController

__all__ = ["LedDmxBluetoothController"]
