
from .ui_if import UiIf


class AutomotiveUiIf(UiIf):

    @abstractmethod
    def set_vehicle_status(
        self,
        status: VehicleStatus
    ) -> None:
        ...