from __future__ import annotations

from collections.abc import Callable

from controllers.video.netflix_player import DEFAULT_NETFLIX_URL, NetflixPlayer
from frontends.tk import TkScreen
from frontends.tk.media.netflix_panel import NetflixPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId


class NetflixScreen(TkScreen):
    """Present Netflix browser controls as a Car UI destination."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        player: NetflixPlayer,
        display: str,
        colors: dict[str, str],
        back_action: Callable[[], None],
    ) -> None:
        super().__init__(ScreenId("netflix"))
        self._host = host
        self._player = player
        self._display = display
        self._colors = colors
        self._back_action = back_action

    def show(self) -> None:
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Netflix")
        self._host.set_screen_back_action(self.close)
        panel = NetflixPanel(
            self._host.screen_parent,
            player=self._player,
            default_url=DEFAULT_NETFLIX_URL,
            display=self._display,
            set_status=self._host.set_screen_status,
            on_return=self.close,
            colors=self._colors,
        )
        panel.pack(fill="both", expand=True)
        self._host.set_screen_status("Opening Netflix")
        panel.update_idletasks()
        panel.open_home()

    def close(self) -> None:
        self._player.stop()
        self._back_action()
