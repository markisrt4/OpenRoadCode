from controllers.automotive.vehicle_state import VehicleState
from messaging.publisher_if import PublisherIf
from .topics import VEHICLE_STATE_TOPIC
from .vehicle_state_codec import encode_vehicle_state

class VehicleStatePublisher:
    def __init__(self, publisher: PublisherIf, *, source: str = "obd2") -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, state: VehicleState) -> None:
        self._publisher.publish(VEHICLE_STATE_TOPIC, encode_vehicle_state(state, source=self._source))
