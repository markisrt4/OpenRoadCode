from concurrent.futures import Future

from controllers.lighting.lighting_controller_stub import (
    LightingControllerStub,
)


class UnconfiguredControllerStub(LightingControllerStub):
    """Notify consumers that lighting support is not configured."""

    def __init__(self, reason: str) -> None:
        super().__init__()
        self._reason = reason

    def _result(self) -> Future[None]:
        future: Future[None] = Future()
        future.set_exception(RuntimeError(self._reason))
        return future
