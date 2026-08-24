# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the automotive public-contract telemetry demonstration."""

from pathlib import Path

from apps.demos.automotive.automotive_bus_presenter import AutomotiveBusPresenter
from apps.demos.automotive.automotive_demo_ui import AutomotiveDemoUi
from config.service_runtime_config import ServiceRuntimeConfigParser
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from ui.automotive import VehicleConnectionState

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[3] / "config" / "runtime.toml"


def main() -> int:
    """Consume the public vehicle-state topic and render it in the demo UI."""
    config = ServiceRuntimeConfigParser(DEFAULT_RUNTIME_CONFIG).load()
    ui = AutomotiveDemoUi()
    presenter = AutomotiveBusPresenter(ui)
    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(config.messaging.subscriber_endpoint),
        error_handler=presenter.set_error,
    )
    dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, presenter.set_vehicle_message)

    if not ui.initialize():
        dispatcher.close()
        return 1

    ui.set_connection_state(VehicleConnectionState.CONNECTING)
    dispatcher.start()
    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        dispatcher.close()
        ui.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
