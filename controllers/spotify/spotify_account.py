# SPDX-License-Identifier: MIT

"""Account operations and token commits scoped to their requesting view."""

from collections.abc import Callable
from dataclasses import replace
import threading

from ui.media.spotify_account_if import (
    SpotifyAccountAction, SpotifyAccountRequests, SpotifyAccountState, SpotifyAccountUi,
)
from ui.ui_dispatcher_if import UiDispatcherIf

Current = Callable[[], bool]
Commit = Callable[[Callable[[], None]], bool]
Connect = Callable[[Current, Commit], None]


class SpotifyAccountController:
    def __init__(self, *, read_account: Callable[[], tuple[str, bool]],
                 save_client_id: Callable[[str], None], connect: Connect,
                 disconnect: Callable[[], None], online: Current,
                 run_work: Callable[[Callable[[], None]], None], dispatcher: UiDispatcherIf,
                 refresh_playback: Callable[[], None]) -> None:
        self._read = read_account
        self._save = save_client_id
        self._connect = connect
        self._disconnect = disconnect
        self._online = online
        self._run_work = run_work
        self._dispatcher = dispatcher
        self._refresh_playback = refresh_playback
        self._state = SpotifyAccountState(online=online())
        self._views: dict[object, tuple[int, SpotifyAccountUi]] = {}
        self._sequence = 0
        self._operation: tuple[object, int, int] | None = None
        self._closed = False
        self._lock = threading.RLock()

    def bind(self, key: object, generation: int, view: SpotifyAccountUi) -> None:
        if self._closed:
            raise RuntimeError("Spotify account controller is closed")
        with self._lock:
            self._views[key] = (generation, view)
        self._publish()
        self.refresh()

    def unbind(self, key: object) -> None:
        with self._lock:
            self._views.pop(key, None)
            if self._operation is not None and self._operation[0] is key:
                self._sequence += 1
                self._operation = None
                self._state = replace(self._state, busy=False, action=SpotifyAccountAction.NONE,
                                      message="", error=False)
        self._publish()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._sequence += 1
            self._operation = None
            views, self._views = self._views, {}
        for _, view in views.values():
            view.set_spotify_account_handler(None)

    def _publish(self) -> None:
        if self._closed:
            return
        self._state = replace(self._state, online=self._online())
        for _, view in tuple(self._views.values()):
            view.set_spotify_account_state(self._state)

    def network_changed(self) -> None:
        """Cancel sign-in when networking is disabled and refresh view state."""
        with self._lock:
            if not self._online() and self._state.action is SpotifyAccountAction.CONNECT:
                self._sequence += 1
                self._operation = None
                self._state = replace(self._state, busy=False, action=SpotifyAccountAction.NONE,
                                      message="Offline mode: Spotify sign-in unavailable", error=True)
        self._publish()

    def refresh(self) -> None:
        if self._closed or not self._views or self._state.busy:
            return
        sequence = self._sequence
        def read() -> None:
            try:
                client_id, connected = self._read()
                error = ""
            except Exception as failure:
                client_id, connected, error = "", False, f"Spotify: {failure}"
            def deliver() -> None:
                if self._closed or sequence != self._sequence or not self._views:
                    return
                self._state = replace(self._state, client_id=client_id, connected=connected,
                                      loading=False, message=error, error=bool(error))
                self._publish()
            self._dispatcher.dispatch_ui(deliver)
        self._run_work(read)

    def _active(self, key: object, generation: int) -> bool:
        binding = self._views.get(key)
        return not self._closed and binding is not None and binding[0] == generation

    def request(self, key: object, generation: int, action: SpotifyAccountAction, client_id: str = "") -> None:
        if not self._active(key, generation):
            return
        if action is SpotifyAccountAction.CONNECT:
            if self._state.busy:
                return
            if not self._online():
                self._state = replace(self._state, message="Offline mode: Spotify sign-in unavailable", error=True)
                self._publish()
                return
            if not self._state.configured:
                self._state = replace(self._state, message="Configure the Spotify Client ID first", error=True)
                self._publish()
                return
        if action is SpotifyAccountAction.CONFIGURE and not client_id.strip():
            self._state = replace(self._state, action=action, message="Spotify Client ID is required", error=True)
            self._publish()
            return
        with self._lock:
            self._sequence += 1
            operation = (key, generation, self._sequence)
            self._operation = operation
        messages = {
            SpotifyAccountAction.CONFIGURE: "Saving Spotify application…",
            SpotifyAccountAction.CONNECT: "Opening Spotify authorization…",
            SpotifyAccountAction.DISCONNECT: "Disconnecting Spotify…",
        }
        self._state = replace(self._state, busy=True, action=action, error=False, message=messages[action])
        self._publish()
        def current() -> bool:
            with self._lock:
                return (self._operation == operation and self._active(key, generation)
                        and (action is not SpotifyAccountAction.CONNECT or self._online()))
        def commit(change: Callable[[], None]) -> bool:
            with self._lock:
                if not current():
                    return False
                change()
                return True
        def work() -> None:
            if not current():
                return
            try:
                if action is SpotifyAccountAction.CONFIGURE:
                    if not commit(lambda: self._save(client_id.strip())):
                        return
                    message = "Spotify application saved. Restart ORC to activate it."
                elif action is SpotifyAccountAction.CONNECT:
                    self._connect(current, commit)
                    message = "Spotify account connected"
                else:
                    if not commit(self._disconnect):
                        return
                    message = "Spotify account disconnected"
                client, connected = self._read()
                error = False
            except Exception as failure:
                client, connected = self._state.client_id, self._state.connected
                message, error = f"Spotify: {failure}", True
            def deliver() -> None:
                if not current():
                    return
                with self._lock:
                    self._operation = None
                self._state = replace(self._state, client_id=client, connected=connected,
                                      loading=False, busy=False, action=action, message=message, error=error)
                if not error:
                    self._refresh_playback()
                self._publish()
            self._dispatcher.dispatch_ui(deliver)
        self._run_work(work)


class SpotifyAccountBinding:
    """Independent view lifetime backed by the shared account controller."""

    def __init__(self, controller: SpotifyAccountController) -> None:
        self._controller = controller
        self._key = object()
        self._generation = 0
        self._view: SpotifyAccountUi | None = None
        self._closed = False

    def activate(self, view: SpotifyAccountUi) -> None:
        if self._closed:
            raise RuntimeError("Spotify account session is closed")
        self.deactivate()
        self._view = view
        view.set_spotify_account_handler(_AccountRequests(self._controller, self._key, self._generation))
        try:
            self._controller.bind(self._key, self._generation, view)
        except BaseException:
            self.deactivate()
            raise

    def deactivate(self) -> None:
        self._generation += 1
        self._controller.unbind(self._key)
        view, self._view = self._view, None
        if view is not None:
            view.set_spotify_account_handler(None)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.deactivate()


class _AccountRequests(SpotifyAccountRequests):
    def __init__(self, controller: SpotifyAccountController, key: object, generation: int) -> None:
        self._controller, self._key, self._generation = controller, key, generation

    def request_configure(self, client_id: str) -> None:
        self._controller.request(self._key, self._generation, SpotifyAccountAction.CONFIGURE, client_id)

    def request_connect(self) -> None:
        self._controller.request(self._key, self._generation, SpotifyAccountAction.CONNECT)

    def request_disconnect(self) -> None:
        self._controller.request(self._key, self._generation, SpotifyAccountAction.DISCONNECT)
