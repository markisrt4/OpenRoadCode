# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level radio chooser and SDR++ presentation handoff for orcUi."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.radio_application_service import RadioApplicationServiceIf
from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from controllers.radio.streaming_radio_controller import StreamingRadioController
from controllers.radio.streaming_radio_directory_if import StreamingRadioDirectoryIf
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from frontends.tk.radio.persistent_streaming_radio_panel import PersistentStreamingRadioPanel
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL
from .radio_source_icon import draw_source_icon


class LaunchAwareRadioPanel(RadioPanel):
    """Radio panel that can present SDR++ startup state inside its X11 host."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        embedder: X11WindowEmbedder,
        theme: ThemeBundle,
        rf_active: Callable[[], bool] | None = None,
        release_rf: Callable[[], None] | None = None,
        adsb_control: OrcUiAdsbControl | None = None,
        on_location_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            embedder=embedder,
            theme=theme,
            rf_active=rf_active,
            release_rf=release_rf,
            adsb_control=adsb_control,
        )
        self._launch_status = tk.Label(
            self._host,
            text="Loading SDR++…",
            bg=theme.ui.background,
            fg=theme.ui.text,
            font=("Sans", 20, "bold"),
            padx=24,
            pady=18,
        )
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Repaint radio chrome and any visible SDR++ launch status."""
        super().set_theme_bundle(theme)
        self._launch_status.configure(bg=theme.ui.background, fg=theme.ui.text)

    def show_loading(self, text: str = "Loading SDR++…") -> None:
        self._launch_status.configure(text=text, fg=self._theme.ui.text)
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")
        self._launch_status.lift()

    def hide_loading(self) -> None:
        self._launch_status.place_forget()


class RadioEntryPanel(tk.Frame):
    """Offer RF or streaming radio and host the active radio presentation."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        radio_application: RadioApplicationServiceIf,
        streaming_radio: StreamingRadioController,
        directory: StreamingRadioDirectoryIf,
        favorites: StreamingRadioFavorites,
        theme: ThemeBundle,
        embedder: X11WindowEmbedder | None = None,
        adsb_control: OrcUiAdsbControl | None = None,
        on_location_changed: Callable[[str], None] | None = None,
    ) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._embedder = embedder or X11WindowEmbedder()
        self._adsb_control = adsb_control or OrcUiAdsbControl()
        self._radio_application = radio_application
        self._streaming_radio = streaming_radio
        self._directory = directory
        self._favorites = favorites
        self._radio_panel: LaunchAwareRadioPanel | None = None
        self._streaming_page: PersistentStreamingRadioPanel | None = None
        self._launching = False
        self._on_location_changed = on_location_changed

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._chooser = tk.Frame(self, bg=ui.background)
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._chooser.grid_columnconfigure(0, weight=1, uniform="radio-source")
        self._chooser.grid_columnconfigure(1, weight=1, uniform="radio-source")
        self._chooser.grid_rowconfigure(0, weight=1)
        self._build_choice_buttons()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply a live ORC theme without restarting radio playback."""
        self._theme = theme
        self.configure(bg=theme.ui.background)
        self._chooser.configure(bg=theme.ui.background)
        for child in self._chooser.winfo_children():
            child.destroy()
        self._build_choice_buttons()
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.set_theme_bundle(theme)
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.set_theme_bundle(theme)

    def open_streaming_radio(self) -> None:
        """Present the streaming-radio browser directly."""
        self._show_streaming_radio()
        self._set_location("STREAMING")

    def open_rf_radio(self) -> None:
        """Launch and present the RF radio directly."""
        self._launch_rf_radio()
        self._set_location("RF")

    def open_adsb(self) -> None:
        """Present the ADS-B aircraft dashboard without starting SDR++ first."""
        self._chooser.grid_remove()
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.grid_remove()
        if self._radio_panel is None or not self._radio_panel.winfo_exists():
            self._radio_panel = LaunchAwareRadioPanel(
                self,
                embedder=self._embedder,
                theme=self._theme,
                rf_active=lambda: self._radio_application.presented,
                release_rf=self._radio_application.relinquish_for_adsb,
                adsb_control=self._adsb_control,
            )
            self._radio_panel.grid(row=0, column=0, sticky="nsew")
            self._radio_panel.hide_loading()
        self._radio_panel.show_adsb()
        self._set_location("AIRCRAFT")

    def _build_choice_buttons(self) -> None:
        ui = self._theme.ui
        rf_card, self._rf_button = self._build_source_card(
            parent=self._chooser,
            title="RF RADIO",
            eyebrow="SOFTWARE DEFINED RADIO",
            description="Tune live RF with SDR++ spectrum and waterfall controls.",
            features="FM  •  WEATHER  •  AIRBAND  •  HAM",
            action_text="OPEN RF RADIO  ›",
            accent=ui.accent_success,
            icon_kind="rf",
            command=self.open_rf_radio,
        )
        rf_card.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=(18, 12))

        streaming_card, self._streaming_button = self._build_source_card(
            parent=self._chooser,
            title="STREAMING RADIO",
            eyebrow="INTERNET AUDIO",
            description="Browse local and regional streams with artwork, favorites and playback.",
            features="LOCAL  •  REGIONAL  •  FAVORITES",
            action_text="BROWSE STATIONS  ›",
            accent=ui.accent_primary,
            icon_kind="stream",
            command=self.open_streaming_radio,
        )
        streaming_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 12),
            pady=(18, 12),
        )
        self._status = tk.Label(
            self._chooser,
            text="Choose a radio source",
            bg=ui.background,
            fg=ui.text_muted,
            font=("Sans", FONT_BODY),
        )
        self._status.grid(row=1, column=0, columnspan=2, pady=(0, 10))

    def _build_source_card(
        self,
        *,
        parent: tk.Misc,
        title: str,
        eyebrow: str,
        description: str,
        features: str,
        action_text: str,
        accent: str,
        icon_kind: str,
        command: Callable[[], None],
    ) -> tuple[tk.Frame, tk.Button]:
        ui = self._theme.ui
        card = tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        accent_bar = tk.Frame(card, bg=accent, height=6)
        accent_bar.grid(row=0, column=0, sticky="ew")
        accent_bar.grid_propagate(False)

        heading = tk.Frame(card, bg=ui.surface)
        heading.grid(row=1, column=0, sticky="ew", padx=14, pady=(18, 10))
        heading.grid_columnconfigure(1, weight=1)
        icon = tk.Canvas(
            heading,
            width=64,
            height=64,
            bg=ui.surface,
            highlightthickness=0,
            bd=0,
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        draw_source_icon(icon, icon_kind=icon_kind, accent=accent, theme=self._theme)
        tk.Label(
            heading,
            text=eyebrow,
            bg=ui.surface,
            fg=accent,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(8, 2))
        tk.Label(
            heading,
            text=title,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 21, "bold"),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw")

        body = tk.Frame(card, bg=ui.surface)
        body.grid(row=2, column=0, sticky="nsew", padx=26, pady=(8, 14))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        tk.Label(
            body,
            text=description,
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_BODY + 3),
            justify=tk.LEFT,
            anchor="nw",
            wraplength=390,
        ).grid(row=0, column=0, sticky="new")
        tk.Label(
            body,
            text=features,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(14, 8))
        button = tk.Button(
            body,
            text=action_text,
            command=command,
            bg=ui.control_background,
            fg=accent,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            padx=16,
            pady=10,
            cursor="hand2",
        )
        button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        for widget in self._walk_widgets(card):
            if widget is button:
                continue
            widget.bind("<Button-1>", lambda _event, callback=command: callback())
            try:
                widget.configure(cursor="hand2")
            except tk.TclError:
                pass
        return card, button

    @staticmethod
    def _walk_widgets(root: tk.Misc) -> tuple[tk.Misc, ...]:
        widgets: list[tk.Misc] = [root]
        for child in root.winfo_children():
            widgets.extend(RadioEntryPanel._walk_widgets(child))
        return tuple(widgets)

    def _show_streaming_radio(self) -> None:
        self._chooser.grid_remove()
        if self._streaming_page is None or not self._streaming_page.winfo_exists():
            self._streaming_page = PersistentStreamingRadioPanel(
                self,
                directory=self._directory,
                controller=self._streaming_radio,
                favorites=self._favorites,
                theme=self._theme,
                on_back=self._show_chooser,
            )
        self._streaming_page.grid(row=0, column=0, sticky="nsew")

    def _show_chooser(self) -> None:
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.grid_remove()
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._set_location("RADIO")

    def _set_location(self, leaf: str) -> None:
        handler = self._on_location_changed
        if handler is not None:
            handler(leaf)

    def _launch_rf_radio(self) -> None:
        if self._launching:
            return
        self._launching = True
        self._chooser.grid_remove()
        self._radio_panel = LaunchAwareRadioPanel(
            self,
            embedder=self._embedder,
            theme=self._theme,
            rf_active=lambda: self._radio_application.presented,
            release_rf=self._radio_application.relinquish_for_adsb,
        )
        self._radio_panel.grid(row=0, column=0, sticky="nsew")
        self._radio_panel.show_loading("Loading SDR++…")
        self.update_idletasks()
        threading.Thread(
            target=self._present_rf_worker,
            name="orcui-sdrpp-present",
            daemon=True,
        ).start()

    def _present_rf_worker(self) -> None:
        presentation_error: list[Exception] = []

        def present() -> None:
            try:
                self._radio_application.present()
            except Exception as error:
                presentation_error.append(error)

        presentation_thread = threading.Thread(
            target=present,
            name="orcui-sdrpp-present-request",
            daemon=True,
        )
        presentation_thread.start()

        process_id: int | None = None
        while presentation_thread.is_alive() and not presentation_error:
            try:
                process_id = self._radio_application.window_process_id(
                    timeout_seconds=0.25,
                )
                break
            except RuntimeError:
                continue

        if process_id is not None:
            try:
                # Hide the temporary standalone SDR++ top-level as soon as it
                # exists.  Do not embed yet: presentation startup must still
                # complete before the X11 window is reparented into the host.
                self._embedder.hide(process_id, window_name="SDR++")
            except RuntimeError:
                # Visual suppression is best-effort.  The final embedder still
                # performs its normal discovery/retry sequence after startup.
                pass

        presentation_thread.join()
        if presentation_error:
            self.after(0, lambda exc=presentation_error[0]: self._show_launch_error(exc))
            return

        if self._radio_application.fullscreen:
            self.after(0, self._finish_fullscreen_rf_launch)
            return

        if process_id is None:
            try:
                process_id = self._radio_application.window_process_id(
                    timeout_seconds=2.0,
                )
            except Exception as error:
                self.after(0, lambda exc=error: self._show_launch_error(exc))
                return

        self.after(0, lambda pid=process_id: self._attach_rf_radio(pid))

    def _finish_fullscreen_rf_launch(self) -> None:
        self._launching = False
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.hide_loading()

    def _attach_rf_radio(self, process_id: int) -> None:
        panel = self._radio_panel
        if panel is None or not panel.winfo_exists():
            return
        try:
            panel.attach_sdrpp(process_id)
            panel.hide_loading()
        except Exception as error:
            self._show_launch_error(error)
            return
        self._launching = False

    def _show_launch_error(self, error: Exception) -> None:
        if not self.winfo_exists():
            return
        self._launching = False
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.destroy()
        self._radio_panel = None
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._rf_button.configure(state=tk.NORMAL)
        self._streaming_button.configure(state=tk.NORMAL)
        self._status.configure(
            text=f"SDR++: {type(error).__name__}: {error}",
            fg=self._theme.ui.accent_danger,
        )
        print(f"WARNING: SDR++ launch/embed: {type(error).__name__}: {error}")

    def detach_sdrpp(self, parent_window_id: int) -> None:
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.detach_sdrpp(parent_window_id)
