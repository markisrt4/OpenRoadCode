from controllers.input.input_handler_if import InputHandlerIf
from controllers.input.input_mapper_if import InputMapperIf
from controllers.input.input_types import InputEvent
from ui.ui_event_handler_if import UiEventHandlerIf


class InputManager(InputHandlerIf):

    def __init__(
        self,
        mapper: InputMapperIf,
        ui_handler: UiEventHandlerIf,
    ) -> None:

        self._mapper = mapper
        self._ui_handler = ui_handler

    def handle_input_event(
        self,
        event: InputEvent,
    ) -> None:

        action = self._mapper.map_input(event)

        if action is None:
            return

        self._ui_handler.handle_ui_action(action)
