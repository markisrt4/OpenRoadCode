"""Shared touch-sized navigation bar and docked drawers beside native viewers."""
import tkinter as tk

from ui import UiWidget
from ui.navigation.navigation_experience_if import (
    NavigationExperience, NavigationExperienceRequestHandlerIf, NavigationPlacesDrawerState,
)
from ui.navigation.poi_models import PoiCategory, TransitMode
from ui.navigation.waze_gesture_if import WazeGesture


class NavigationExperienceControls(tk.Frame, UiWidget):
    def __init__(self, parent, *, drawer_parent, drawer_row, drawer_column,
                 handler: NavigationExperienceRequestHandlerIf, theme, on_open=lambda: None,
                 on_close=lambda: None):
        self._ui = ui = theme.ui
        super().__init__(parent, bg=ui.surface_alt)
        self._handler = handler
        self._on_open = on_open
        self._on_close = on_close
        self._drawer_parent = drawer_parent
        self._drawer_row, self._drawer_column = drawer_row, drawer_column
        self._drawer_kind = None
        self._last_state = None
        self._places_state = NavigationPlacesDrawerState()
        self._poll_job = None
        self._surface_loading = False
        toolbar = tk.Frame(self, bg=ui.surface_alt)
        toolbar.pack(fill=tk.X)
        for text, key in (('⌂ HOME', 'home'), ('▣ WORK', 'work')):
            self._button(toolbar, text, lambda key=key: handler.request_saved_destination(key)).pack(
                side=tk.LEFT, padx=(0, 4), pady=3)
        self.places_button = self._button(toolbar, 'PLACES ▾', handler.request_places)
        self.places_button.pack(side=tk.LEFT, padx=2, pady=3)
        right = tk.Frame(toolbar, bg=ui.surface_alt)
        right.pack(side=tk.RIGHT, padx=4)
        self.views_button = self._button(right, '▱ VIEWS', lambda: self.toggle_drawer('views'))
        self.views_button.pack(fill=tk.X, pady=3)
        self.gestures_button = self._button(right, 'WAZE CONTROLS ▾', lambda: self.toggle_drawer('gestures'))
        self._loading_label = tk.Label(self, text='Loading Waze…', bg=ui.surface_alt,
            fg=ui.accent_primary, font=('Sans', 12, 'bold'), pady=6)
        self._drawer = tk.Frame(drawer_parent, bg=ui.surface_alt,
                                highlightthickness=1, highlightbackground=ui.border)
        self._drawer.grid_propagate(False)
        self._drawer.pack_propagate(False)
        header = tk.Frame(self._drawer, bg=ui.surface_alt)
        header.pack(fill=tk.X)
        self._title = tk.Label(header, bg=ui.surface_alt, fg=ui.text, font=('Sans', 13, 'bold'))
        self._button(header, '×', self.close_drawer).pack(side=tk.RIGHT, padx=4)
        self._title.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
        self._canvas = tk.Canvas(self._drawer, bg=ui.surface_alt, highlightthickness=0)
        scroll = tk.Scrollbar(self._drawer, orient=tk.VERTICAL, command=self._canvas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.configure(yscrollcommand=scroll.set)
        self._content = tk.Frame(self._canvas, bg=ui.surface_alt)
        window = self._canvas.create_window(0, 0, window=self._content, anchor='nw')
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfigure(window, width=e.width))
        self._content.bind('<Configure>', lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._views = tk.Frame(self._content, bg=ui.surface_alt)
        self._cards = {}
        self._previews = {}
        for experience, title, detail in (
            (NavigationExperience.ROAD, '⌖  Road map', 'ORC maps & places'),
            (NavigationExperience.WAZE, '➤  Waze', 'Native navigation'),
            (NavigationExperience.TERRAIN, '△  3D terrain', 'Explore with Cesium'),
        ):
            card = self._button(self._views, title + '\n' + detail,
                                lambda value=experience: self._select(value))
            card.configure(anchor='w', justify=tk.LEFT, pady=12, highlightthickness=2,
                           highlightbackground=ui.border, wraplength=220)
            self._previews[experience] = self._preview(experience)
            card.configure(image=self._previews[experience], compound=tk.LEFT)
            card.pack(fill=tk.X, padx=8, pady=5)
            card.bind('<Configure>', lambda e: e.widget.configure(wraplength=max(90, e.width - 100)))
            self._cards[experience] = card
        self._button(self._views, 'CLOSE WAZE', self._close_waze).pack(fill=tk.X, padx=8, pady=6)
        self.overlay_frame = tk.Frame(self._views, bg=ui.surface_alt)
        self.overlay_frame.pack(fill=tk.X, padx=8, pady=6)
        self._places = tk.Frame(self._content, bg=ui.surface_alt)
        categories = tk.Frame(self._places, bg=ui.surface_alt)
        categories.pack(fill=tk.X, padx=8)
        categories.columnconfigure((0, 1), weight=1)
        for index, (label, category) in enumerate((('Food', PoiCategory.FOOD), ('Fuel', PoiCategory.FUEL),
                                                  ('Groceries', PoiCategory.GROCERY), ('Transit', PoiCategory.TRANSIT))):
            self._button(categories, label, lambda value=category: handler.request_search_places(value)).grid(
                row=index // 2, column=index % 2, sticky='ew', padx=2, pady=3)
        transit = tk.Menubutton(self._places, text='Transit filters ▾', bg=ui.control_background,
                                fg=ui.text, font=('Sans', 10, 'bold'), pady=8)
        menu = tk.Menu(transit, tearoff=False, bg=ui.control_background, fg=ui.text)
        for title, mode in (('All transit', TransitMode.ALL), ('Bus', TransitMode.BUS),
                            ('Rail', TransitMode.RAIL), ('Tram / Subway', TransitMode.TRAM_SUBWAY)):
            menu.add_command(label=title, command=lambda value=mode: handler.request_search_places(PoiCategory.TRANSIT, value))
        transit.configure(menu=menu)
        transit.pack(fill=tk.X, padx=10, pady=3)
        self._button(self._places, 'CLEAR RESULTS', handler.request_clear_places).pack(fill=tk.X, padx=10, pady=3)
        self._status = tk.Label(self._places, bg=ui.surface_alt, fg=ui.text_muted,
                                wraplength=220, justify=tk.LEFT, anchor='w')
        self._status.pack(fill=tk.X, padx=12, pady=8)
        self._results = tk.Frame(self._places, bg=ui.surface_alt)
        self._results.pack(fill=tk.X)
        self._gestures = tk.Frame(self._content, bg=ui.surface_alt)
        tk.Label(self._gestures, text='Move the view', bg=ui.surface_alt, fg=ui.text,
                 font=('Sans', 12, 'bold')).pack(pady=8)
        arrows = tk.Frame(self._gestures, bg=ui.surface_alt)
        arrows.pack(fill=tk.X, padx=10)
        arrows.columnconfigure((0, 1, 2), weight=1)
        self._gesture_buttons = {}
        for text, action, row, col in (
            ('↑', WazeGesture.PAN_UP, 0, 1), ('←', WazeGesture.PAN_LEFT, 1, 0),
            ('→', WazeGesture.PAN_RIGHT, 1, 2), ('↓', WazeGesture.PAN_DOWN, 2, 1),
        ):
            button = self._button(arrows, text, lambda value=action: handler.request_waze_gesture(value))
            button.configure(font=('Sans', 18, 'bold'), pady=8)
            button.grid(row=row, column=col, sticky='ew', padx=2, pady=2)
            self._gesture_buttons[action] = button
        zoom = tk.Frame(self._gestures, bg=ui.surface_alt)
        zoom.pack(fill=tk.X, padx=10, pady=10)
        zoom.columnconfigure((0, 1), weight=1)
        for column, (text, action) in enumerate((('ZOOM +', WazeGesture.ZOOM_IN), ('ZOOM −', WazeGesture.ZOOM_OUT))):
            button = self._button(zoom, text, lambda value=action: handler.request_waze_gesture(value))
            button.grid(row=0, column=column, sticky='ew', padx=2)
            self._gesture_buttons[action] = button
        self._gesture_status = tk.Label(self._gestures, bg=ui.surface_alt, fg=ui.text_muted,
                                        wraplength=210, justify=tk.LEFT)
        self._gesture_status.pack(fill=tk.X, padx=12, pady=8)
        tk.Label(self._gestures, text='Use with Waze’s map visible.\nWaze may resume automatic following.',
                 bg=ui.surface_alt, fg=ui.text_muted, wraplength=210, justify=tk.LEFT).pack(padx=12, pady=8)
        self.set_places_state(self._places_state)
        self.bind('<Destroy>', self._destroyed, add='+')
        self._poll()

    def _button(self, parent, text, command):
        ui = self._ui
        return tk.Button(parent, text=text, command=command, bg=ui.control_background, fg=ui.control_text,
            activebackground=ui.control_active, activeforeground=ui.text, relief=tk.FLAT,
            bd=0, highlightthickness=0, font=('Sans', 10, 'bold'), padx=10, pady=9, cursor='hand2')

    def _preview(self, experience):
        """Small schematic thumbnails, not live map captures or downloaded tiles."""
        image = tk.PhotoImage(master=self, width=64, height=48)
        if experience is NavigationExperience.TERRAIN:
            image.put('#24485b', to=(0, 0, 64, 48))
            for y in range(12, 48):
                left, right = max(0, 23 - y // 2), min(64, 32 + y)
                image.put('#6b8870' if y < 30 else '#355d48', to=(left, y, right, y + 1))
            return image
        dark = experience is NavigationExperience.ROAD
        image.put('#102933' if dark else '#dde6d5', to=(0, 0, 64, 48))
        for x in (10, 29, 49):
            image.put('#3c5962' if dark else '#ffffff', to=(x, 0, x + 2, 48))
        for y in (9, 23, 37):
            image.put('#3c5962' if dark else '#ffffff', to=(0, y, 64, y + 2))
        for x in range(5, 58):
            y = 39 - x // 2
            image.put('#00c4f3' if dark else '#9561d5', to=(x, y, x + 2, y + 3))
        return image

    def _poll(self):
        state = self._handler.state
        if state != self._last_state:
            self._last_state = state
            for experience, card in self._cards.items():
                available = (state.waze_available if experience is NavigationExperience.WAZE else
                             state.terrain_available if experience is NavigationExperience.TERRAIN else True)
                selected = state.selected is experience
                title, detail = {
                    NavigationExperience.ROAD: ('⌖  Road map', 'ORC maps & places'),
                    NavigationExperience.WAZE: ('➤  Waze', 'Running · Resume navigation' if state.waze_running else 'Native navigation'),
                    NavigationExperience.TERRAIN: ('△  3D terrain', 'Explore with Cesium'),
                }[experience]
                if not available:
                    detail = 'Not available on this device'
                card.configure(text=('✓  ' if selected else '') + title + '\n' + detail,
                    highlightbackground=self._ui.accent_primary if selected else self._ui.border,
                    bg=self._ui.control_active if selected else self._ui.control_background,
                    state=tk.NORMAL if available and not state.busy else tk.DISABLED)
            self.views_button.configure(text='▱ VIEWS · ' + {
                NavigationExperience.ROAD: 'MAP', NavigationExperience.WAZE: 'WAZE',
                NavigationExperience.TERRAIN: 'TERRAIN'}[state.selected])
            self._render_loading()
            if state.waze_gestures_supported and state.selected is NavigationExperience.WAZE:
                self.gestures_button.pack(fill=tk.X, pady=(0, 3))
            else:
                self.gestures_button.pack_forget()
                if self._drawer_kind == 'gestures':
                    self.close_drawer()
            self.gestures_button.configure(state=tk.NORMAL if state.waze_gestures_available and not state.busy else tk.DISABLED)
            for button in self._gesture_buttons.values():
                button.configure(state=tk.NORMAL if state.waze_gestures_available and not state.waze_gesture_busy
                                 and not state.busy else tk.DISABLED)
            self._gesture_status.configure(text=state.waze_gesture_status)
        self._poll_job = self.after(500, self._poll)

    def set_surface_loading(self, loading: bool):
        """Present native viewer attachment separately from the app launch worker."""
        self._surface_loading = loading
        self._render_loading()

    def _render_loading(self):
        if self._surface_loading or (self._last_state is not None and self._last_state.waze_loading):
            self._loading_label.pack(fill=tk.X)
        else:
            self._loading_label.pack_forget()

    def toggle_drawer(self, kind):
        if self._drawer_kind == kind:
            self.close_drawer()
            return
        self.show_drawer(kind)

    def show_drawer(self, kind):
        if self._drawer_kind is not None and self._drawer_kind != kind:
            self._on_close()
        self._on_open()
        self._drawer_kind = kind
        self._views.pack_forget()
        self._places.pack_forget()
        self._gestures.pack_forget()
        {'views': self._views, 'places': self._places, 'gestures': self._gestures}[kind].pack(fill=tk.BOTH, expand=True)
        self._title.configure(text={'views': 'Navigation views', 'places': 'Places nearby', 'gestures': 'Waze controls'}[kind])
        width = max(230, min(310, int(self._drawer_parent.winfo_width() * .42)))
        self._drawer.configure(width=width)
        self._drawer_parent.grid_columnconfigure(self._drawer_column, minsize=width, weight=0)
        self._drawer.grid(row=self._drawer_row, column=self._drawer_column, sticky='nsew')
        self._drawer_parent.update_idletasks()
        # Nested native hosts can leave grid's first allocation at its requested
        # 1px height. Reassert the content track after mapping the new sibling.
        self._drawer_parent.grid_columnconfigure(self._drawer_column - 1, weight=1)
        self._drawer.lift()
        self._canvas.yview_moveto(0)

    def close_drawer(self):
        self._on_close()
        self._drawer_kind = None
        self._drawer.grid_remove()
        self._drawer_parent.grid_columnconfigure(self._drawer_column, minsize=0, weight=0)
        self._drawer_parent.update_idletasks()
        self._drawer_parent.grid_columnconfigure(self._drawer_column - 1, weight=1)

    def set_theme(self, theme):
        self._ui = ui = theme.ui

        def repaint(widget):
            if isinstance(widget, (tk.Frame, tk.Canvas, tk.Label)):
                widget.configure(bg=ui.surface_alt)
                if isinstance(widget, tk.Label):
                    widget.configure(fg=ui.text)
            elif isinstance(widget, (tk.Button, tk.Menubutton, tk.Menu)):
                widget.configure(bg=ui.control_background, fg=ui.control_text,
                                 activebackground=ui.control_active)
            for child in widget.winfo_children():
                repaint(child)

        repaint(self)
        repaint(self._drawer)
        self._drawer.configure(highlightbackground=ui.border)
        self._last_state = None
        self.after_cancel(self._poll_job)
        self._poll()

    def _select(self, experience):
        self.close_drawer()
        self._handler.request_experience(experience)

    def _close_waze(self):
        self.close_drawer()
        self._handler.request_close_waze()

    def set_places_state(self, state: NavigationPlacesDrawerState):
        self._places_state = state
        self._status.configure(text=state.status)
        for child in self._results.winfo_children():
            child.destroy()
        for place in state.places:
            text = place.name + ('\n' + place.address if place.address else '')
            button = self._button(self._results, text, lambda value=place: self._handler.request_select_place(value))
            button.configure(wraplength=220, anchor='w', justify=tk.LEFT)
            button.pack(fill=tk.X, padx=10, pady=3)

    def _destroyed(self, event):
        if event.widget is self:
            if self._poll_job is not None:
                self.after_cancel(self._poll_job)
                self._poll_job = None
            try:
                self._drawer.destroy()
            finally:
                # Tcl widget destruction does not drop Python PhotoImage objects.
                # Release them on this thread even if callbacks retain the frame.
                self._previews.clear()
