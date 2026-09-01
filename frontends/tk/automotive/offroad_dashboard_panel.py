# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk dashboard panel for off-road navigation data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import math
import tkinter as tk

from ui.navigation import (
    GroundTrackUiIf,
    HeadingReference,
    NavigationRequestHandlerIf,
    OrientationUiIf,
    PositionFix,
    PositionUiIf,
    SatelliteInfo,
    TranslationUiIf,
)
from ui.system import StatusMessage, StatusSeverity, StatusUiIf, StatusValue


# Keep the original off-road composition, but use the same visual language as
# ORCui: near-black/navy surfaces, slate borders, blue primary accents, green
# success, yellow caution, and orange-red danger.
BACKGROUND = "#05090d"
PANEL = "#0b1117"
GRID = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
BLUE = "#168bd1"
GREEN = "#84ce1f"
AMBER = "#d6ad22"
RED = "#f15a16"
SKY = "#18344b"
GROUND = "#493825"


@dataclass(slots=True)
class _Vector:
    x: float | None = None
    y: float | None = None
    z: float | None = None


@dataclass(slots=True)
class _GpsDisplayState:
    altitude_m: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    satellites_used: int | None = None


@dataclass(slots=True)
class _DashboardState:
    heading_deg: float = 0.0
    heading_reference: HeadingReference = HeadingReference.RELATIVE
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    linear_acceleration_mps2: _Vector = field(default_factory=_Vector)
    gps: _GpsDisplayState = field(default_factory=_GpsDisplayState)


def _normalize_heading(heading_deg: float) -> float:
    return heading_deg % 360.0


def _cardinal_direction(heading_deg: float) -> str:
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = int((_normalize_heading(heading_deg) + 22.5) // 45.0) % 8
    return directions[index]


def _tilt_severity(
    pitch_deg: float,
    roll_deg: float,
    pitch_warning_deg: float,
    roll_warning_deg: float,
) -> str:
    pitch_ratio = abs(pitch_deg) / pitch_warning_deg
    roll_ratio = abs(roll_deg) / roll_warning_deg
    ratio = max(pitch_ratio, roll_ratio)
    if ratio >= 1.0:
        return "warning"
    if ratio >= 0.75:
        return "caution"
    return "normal"


def _is_capsized(pitch_deg: float, roll_deg: float) -> bool:
    """Return whether attitude indicates the vehicle is substantially inverted."""

    return abs(roll_deg) >= 120.0 or abs(pitch_deg) >= 120.0


def _rotate_screen_point(
    point: tuple[float, float],
    center_x: float,
    center_y: float,
    angle_deg: float,
) -> tuple[float, float]:
    """Rotate a local screen point clockwise around a screen center."""

    x, y = point
    angle = math.radians(angle_deg)
    return (
        center_x + x * math.cos(angle) - y * math.sin(angle),
        center_y + x * math.sin(angle) + y * math.cos(angle),
    )


class OffroadDashboardPanel(
    tk.Frame,
    OrientationUiIf,
    TranslationUiIf,
    PositionUiIf,
    GroundTrackUiIf,
    StatusUiIf,
):
    """Display trail-oriented navigation data through narrow UI contracts."""

    def __init__(
        self,
        parent: tk.Misc,
        pitch_warning_deg: float,
        roll_warning_deg: float,
        request_handler: NavigationRequestHandlerIf | None = None,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._pitch_warning_deg = pitch_warning_deg
        self._roll_warning_deg = roll_warning_deg
        self._request_handler = request_handler
        self._state = _DashboardState()
        self._has_orientation = False
        self._position: PositionFix | None = None
        self._redraw_pending = False

        self._canvas = tk.Canvas(self, bg=BACKGROUND, highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda _event: self._draw())

        controls = tk.Frame(self, bg=PANEL)
        controls.pack(fill=tk.X)
        self._button(controls, "CALIBRATE", self._request_calibration).pack(side=tk.LEFT, padx=(10, 4), pady=7)
        self._button(controls, "ZERO HEADING", self._request_heading_reset).pack(side=tk.LEFT, padx=4, pady=7)

        self._status = tk.StringVar(value="STARTING")
        self._status_label = tk.Label(controls, textvariable=self._status, fg=GREEN, bg=PANEL, font=("TkFixedFont", 10, "bold"))
        self._status_label.pack(side=tk.RIGHT, padx=14)

    def set_navigation_request_handler(self, handler: NavigationRequestHandlerIf | None) -> None:
        self._request_handler = handler

    def set_heading(self, heading_rad: float | None, reference: HeadingReference = HeadingReference.TRUE_NORTH) -> None:
        self._has_orientation = heading_rad is not None
        self._state.heading_reference = reference
        self._state.heading_deg = math.degrees(heading_rad) if heading_rad is not None else 0.0
        self._request_draw()

    def set_pitch(self, pitch_rad: float | None) -> None:
        self._state.pitch_deg = math.degrees(pitch_rad) if pitch_rad is not None else 0.0
        self._request_draw()

    def set_roll(self, roll_rad: float | None) -> None:
        self._state.roll_deg = math.degrees(roll_rad) if roll_rad is not None else 0.0
        self._request_draw()

    def set_rate_of_climb(self, rate_mps: float | None) -> None:
        del rate_mps

    def set_accel_x(self, acceleration_x_mps2: float | None) -> None:
        self._state.linear_acceleration_mps2.x = acceleration_x_mps2
        self._request_draw()

    def set_accel_y(self, acceleration_y_mps2: float | None) -> None:
        self._state.linear_acceleration_mps2.y = acceleration_y_mps2
        self._request_draw()

    def set_accel_z(self, acceleration_z_mps2: float | None) -> None:
        self._state.linear_acceleration_mps2.z = acceleration_z_mps2

    def set_accel_total(self, acceleration_magnitude_mps2: float | None) -> None:
        del acceleration_magnitude_mps2

    def set_position(self, position_fix: PositionFix | None) -> None:
        self._position = position_fix
        self._state.gps.altitude_m = position_fix.altitude_m if position_fix is not None else None
        self._request_draw()

    def set_satellites(self, satellites: Sequence[SatelliteInfo]) -> None:
        self._state.gps.satellites_used = sum(satellite.is_used_in_fix for satellite in satellites)
        self._request_draw()

    def set_ground_speed(self, speed_mps: float | None) -> None:
        self._state.gps.speed_mps = speed_mps
        self._request_draw()

    def set_course_over_ground(self, course_rad: float | None) -> None:
        self._state.gps.course_deg = math.degrees(course_rad) if course_rad is not None else None
        self._request_draw()

    def set_status(self, status: StatusValue) -> None:
        if isinstance(status, StatusMessage):
            text = status.summary
            color = {StatusSeverity.INFORMATION: TEXT, StatusSeverity.SUCCESS: GREEN, StatusSeverity.WARNING: AMBER, StatusSeverity.ERROR: RED}[status.severity]
        else:
            text = status or ""
            color = GREEN
        self._status_label.configure(fg=color)
        self._status.set(text.upper())

    @staticmethod
    def _button(parent: tk.Widget, text: str, command: object) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg="#101820", fg=TEXT, activebackground=BLUE, activeforeground="#ffffff", relief=tk.FLAT, padx=14, font=("TkDefaultFont", 9, "bold"))

    def _draw(self) -> None:
        self._redraw_pending = False
        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        state = self._state if self._has_orientation else None
        self._draw_header(width, state)
        content_top = 88
        content_bottom = height - 142
        center_x = width / 2.0
        center_y = (content_top + content_bottom) / 2.0
        horizon_radius = min(width * 0.24, (content_bottom - content_top) * 0.48)
        pitch = state.pitch_deg if state is not None else 0.0
        roll = state.roll_deg if state is not None else 0.0
        self._draw_tilt_meter(center_x, center_y, horizon_radius, pitch, roll, state is not None)
        if state is not None and _is_capsized(state.pitch_deg, state.roll_deg):
            self._draw_capsized_banner(center_x, center_y, horizon_radius)
        side_width = max(180.0, width * 0.2)
        self._draw_pitch_card(18, content_top + 18, side_width, pitch if state is not None else None, self._pitch_warning_deg)
        self._draw_angle_card(width - side_width - 18, content_top + 18, side_width, "ROLL", roll if state is not None else None, "RIGHT" if roll >= 0 else "LEFT", self._roll_warning_deg)
        heading_card_y = content_top + 174
        if heading_card_y + 164 <= content_bottom:
            self._draw_heading_card(width - side_width - 18, heading_card_y, side_width, state)
        self._draw_bottom_cards(width, height, state)

    def _request_draw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._draw)

    def _draw_capsized_banner(self, center_x: float, center_y: float, radius: float) -> None:
        banner_y = center_y + radius * 0.55
        half_width = radius * 0.72
        self._canvas.create_rectangle(center_x-half_width,banner_y-27,center_x+half_width,banner_y+27,fill="#5b1512",outline=RED,width=3)
        self._canvas.create_text(center_x,banner_y-8,text="CAPSIZED",fill="#ffffff",font=("TkDefaultFont",18,"bold"))
        self._canvas.create_text(center_x,banner_y+13,text="Call the police? Maybe the winch crew first.",fill="#ffd6d2",font=("TkDefaultFont",8,"bold"))

    def _draw_header(self, width: int, state: _DashboardState | None) -> None:
        self._canvas.create_rectangle(0,0,width,82,fill=PANEL,outline="")
        heading=state.heading_deg if state is not None else 0.0
        reference_text=({HeadingReference.TRUE_NORTH:"TRUE",HeadingReference.MAGNETIC_NORTH:"MAG",HeadingReference.RELATIVE:"REL"}[state.heading_reference] if state is not None else "REL")
        heading_text=f"{reference_text} {heading:03.0f}°" if state is not None else "REL ---°"
        self._canvas.create_text(width/2,22,text=heading_text,fill=TEXT,font=("TkFixedFont",22,"bold"))
        pixels_per_degree=max(3.0,width/180.0)
        for offset in range(-60,61,5):
            marker_heading=_normalize_heading(heading+offset); x=width/2+offset*pixels_per_degree; major=offset%15==0
            y1=52; y2=72 if major else 64
            self._canvas.create_line(x,y1,x,y2,fill=GRID,width=2)
            if major: self._canvas.create_text(x,44,text=f"{marker_heading:.0f}",fill=MUTED,font=("TkFixedFont",9))
        self._canvas.create_polygon(width/2-7,78,width/2+7,78,width/2,66,fill=BLUE,outline="")

    def _draw_heading_card(self,x:float,y:float,width:float,state:_DashboardState|None)->None:
        height=164
        self._canvas.create_rectangle(x,y,x+width,y+height,fill=PANEL,outline=GRID,width=2)
        self._canvas.create_text(x+14,y+14,anchor=tk.NW,text="HEADING",fill=MUTED,font=("TkDefaultFont",10,"bold"))
        center_x=x+width/2; center_y=y+87; radius=min(53.0,width*0.29)
        self._canvas.create_oval(center_x-radius,center_y-radius,center_x+radius,center_y+radius,outline=GRID,width=2)
        self._canvas.create_line(center_x,center_y-radius+3,center_x,center_y+radius-3,fill="#25313b")
        self._canvas.create_line(center_x-radius+3,center_y,center_x+radius-3,center_y,fill="#25313b")
        self._canvas.create_text(center_x,center_y-radius-9,text="0",fill=BLUE,font=("TkDefaultFont",7,"bold"))
        heading=state.heading_deg if state is not None else 0.0; gps=state.gps if state is not None else None
        if gps is not None and gps.course_deg is not None:
            self._draw_direction_arrow(center_x,center_y,radius*0.86,gps.course_deg,AMBER,3)
            self._canvas.create_text(x+width-10,y+16,anchor=tk.NE,text=f"GPS {gps.course_deg:.0f}° {_cardinal_direction(gps.course_deg)}",fill=AMBER,font=("TkDefaultFont",8,"bold"))
        local_body=((-13,25),(-17,9),(-15,-21),(-8,-31),(8,-31),(15,-21),(17,9),(13,25)); local_cabin=((-10,8),(-10,-13),(10,-13),(10,8))
        def transform(points):
            transformed=[]
            for point in points: transformed.extend(_rotate_screen_point(point,center_x,center_y,heading))
            return tuple(transformed)
        self._canvas.create_polygon(*transform(local_body),fill="#101820",outline=BLUE if state is not None else MUTED,width=2,joinstyle=tk.ROUND)
        self._canvas.create_polygon(*transform(local_cabin),fill="#18344b",outline=BLUE,width=1)
        nose_x,nose_y=_rotate_screen_point((0,-31),center_x,center_y,heading)
        self._canvas.create_oval(nose_x-3,nose_y-3,nose_x+3,nose_y+3,fill=BLUE,outline="")
        reference_text=({HeadingReference.TRUE_NORTH:"TRUE",HeadingReference.MAGNETIC_NORTH:"MAG",HeadingReference.RELATIVE:"REL"}[state.heading_reference] if state is not None else "REL")
        relative_text=f"{reference_text} {heading:03.0f}°" if state is not None else "REL ---°"
        self._canvas.create_text(center_x,y+height-10,text=relative_text,fill=TEXT,font=("TkFixedFont",9,"bold"))

    def _draw_direction_arrow(self,center_x,center_y,length,direction_deg,color,width)->None:
        tip_x,tip_y=_rotate_screen_point((0,-length),center_x,center_y,direction_deg)
        self._canvas.create_line(center_x,center_y,tip_x,tip_y,fill=color,width=width,arrow=tk.LAST,arrowshape=(10,12,5))

    def _draw_pitch_card(self,x,y,width,value,warning_deg)->None:
        height=225
        self._canvas.create_rectangle(x,y,x+width,y+height,fill=PANEL,outline=GRID,width=2)
        self._canvas.create_text(x+14,y+16,anchor=tk.NW,text="PITCH",fill=MUTED,font=("TkDefaultFont",11,"bold"))
        if value is None: display="--.-°"; color=MUTED; pitch=0.0; direction="--"
        else:
            display=f"{abs(value):.1f}°"; ratio=abs(value)/warning_deg; color=RED if ratio>=1 else AMBER if ratio>=.75 else GREEN; pitch=value; direction="NOSE UP" if value>=0 else "NOSE DOWN"
        self._canvas.create_text(x+width/2,y+57,text=display,fill=color,font=("TkFixedFont",27,"bold"))
        center_x=x+width/2; center_y=y+145; half_level=width*.38
        self._canvas.create_line(center_x-half_level,center_y+25,center_x+half_level,center_y+25,fill=BLUE,width=2,dash=(5,4))
        self._canvas.create_text(center_x+half_level,center_y+36,anchor=tk.E,text="LEVEL",fill=BLUE,font=("TkDefaultFont",7,"bold"))
        scale=min(1.0,width/210.0)
        def transform(points):
            transformed=[]
            for local_x,local_y in points: transformed.extend(_rotate_screen_point((local_x*scale,local_y*scale),center_x,center_y,-pitch))
            return tuple(transformed)
        body=((-69,-5),(48,-5),(70,9),(64,22),(-66,22),(-76,10)); cabin=((-39,-6),(-24,-32),(22,-32),(42,-6)); window=((-27,-9),(-17,-26),(15,-26),(29,-9))
        self._canvas.create_polygon(*transform(body),fill="#101820",outline=TEXT,width=2,joinstyle=tk.ROUND)
        self._canvas.create_polygon(*transform(cabin),fill="#101820",outline=TEXT,width=2)
        self._canvas.create_polygon(*transform(window),fill="#18344b",outline=BLUE,width=1)
        for wheel_x in (-48,47):
            wheel_center_x,wheel_center_y=_rotate_screen_point((wheel_x*scale,22*scale),center_x,center_y,-pitch); wheel_radius=13*scale
            self._canvas.create_oval(wheel_center_x-wheel_radius,wheel_center_y-wheel_radius,wheel_center_x+wheel_radius,wheel_center_y+wheel_radius,fill="#101820",outline=MUTED,width=2)
            hub_radius=4*scale; self._canvas.create_oval(wheel_center_x-hub_radius,wheel_center_y-hub_radius,wheel_center_x+hub_radius,wheel_center_y+hub_radius,fill=BLUE,outline="")
        self._canvas.create_text(x+width-12,y+17,anchor=tk.NE,text=direction,fill=color if value is not None else MUTED,font=("TkDefaultFont",9,"bold"))

    def _draw_tilt_meter(self,center_x,center_y,radius,pitch_deg,roll_deg,has_state)->None:
        self._canvas.create_oval(center_x-radius,center_y-radius,center_x+radius,center_y+radius,fill="#0b1117",outline=GRID,width=3)
        for offset,color,line_width in ((-48,"#101820",1),(-24,"#25313b",1),(0,BLUE,3),(24,"#25313b",1),(48,"#101820",1)):
            half_width=math.sqrt(max(0.0,(radius-10)**2-offset**2)); options={"fill":color,"width":line_width}
            if offset: options["dash"]=(5,5)
            self._canvas.create_line(center_x-half_width,center_y+offset,center_x+half_width,center_y+offset,**options)
        self._canvas.create_text(center_x+radius-16,center_y-10,anchor=tk.E,text="LEVEL",fill=BLUE,font=("TkDefaultFont",8,"bold"))
        for angle in range(-60,61,15):
            marker_angle=math.radians(angle-90); inner=radius-(16 if angle%30==0 else 10)
            self._canvas.create_line(center_x+inner*math.cos(marker_angle),center_y+inner*math.sin(marker_angle),center_x+(radius-3)*math.cos(marker_angle),center_y+(radius-3)*math.sin(marker_angle),fill=MUTED,width=2)
        self._draw_front_jeep(center_x,center_y,radius,roll_deg); self._draw_pitch_scale(center_x,center_y,radius,pitch_deg)
        severity=_tilt_severity(pitch_deg,roll_deg,self._pitch_warning_deg,self._roll_warning_deg); severity_color={"normal":GREEN,"caution":AMBER,"warning":RED}[severity]
        self._canvas.create_text(center_x,center_y+radius-16,text=severity.upper() if has_state else "NO DATA",fill=severity_color,font=("TkDefaultFont",12,"bold"))

    def _draw_front_jeep(self,center_x,center_y,radius,roll_deg)->None:
        scale=radius/150.0
        def transform(points):
            transformed=[]
            for x,y in points: transformed.extend(_rotate_screen_point((x*scale,y*scale),center_x,center_y,roll_deg))
            return tuple(transformed)
        body=((-65,-5),(-55,-42),(-38,-54),(38,-54),(55,-42),(65,-5),(61,40),(-61,40)); windshield=((-34,-47),(34,-47),(43,-14),(-43,-14)); left_tire=((-73,8),(-57,8),(-55,48),(-72,48)); right_tire=((57,8),(73,8),(72,48),(55,48))
        self._canvas.create_polygon(*transform(left_tire),fill="#101820",outline=MUTED,width=2); self._canvas.create_polygon(*transform(right_tire),fill="#101820",outline=MUTED,width=2)
        self._canvas.create_polygon(*transform(body),fill="#101820",outline=TEXT,width=3,joinstyle=tk.ROUND); self._canvas.create_polygon(*transform(windshield),fill="#18344b",outline=BLUE,width=2)
        for grille_x in (-27,-18,-9,0,9,18,27): self._canvas.create_line(*transform(((grille_x,7),(grille_x,31))),fill=MUTED,width=max(1,int(2*scale)))
        for headlight_x in (-43,43):
            x,y=_rotate_screen_point((headlight_x*scale,16*scale),center_x,center_y,roll_deg); lamp_radius=max(4.0,8.0*scale)
            self._canvas.create_oval(x-lamp_radius,y-lamp_radius,x+lamp_radius,y+lamp_radius,fill=AMBER,outline=AMBER,width=2)
        self._canvas.create_line(*transform(((-68,40),(68,40))),fill=MUTED,width=max(3,int(5*scale)))

    def _draw_pitch_scale(self,center_x,center_y,radius,pitch_deg)->None:
        x=center_x-radius*.72; pixels_per_degree=radius/55.0
        for value in (-30,-20,-10,0,10,20,30):
            y=center_y-(value-pitch_deg)*pixels_per_degree
            if center_y-radius*.68<=y<=center_y+radius*.68:
                self._canvas.create_line(x-7,y,x+7,y,fill=MUTED if value else TEXT,width=2); self._canvas.create_text(x-12,y,anchor=tk.E,text=str(value),fill=MUTED,font=("TkFixedFont",8))
        self._canvas.create_polygon(x+11,center_y,x+22,center_y-6,x+22,center_y+6,fill=BLUE,outline="")

    def _draw_angle_card(self,x,y,width,title,value,direction,warning_deg)->None:
        height=150; self._canvas.create_rectangle(x,y,x+width,y+height,fill=PANEL,outline=GRID,width=2); self._canvas.create_text(x+14,y+16,anchor=tk.NW,text=title,fill=MUTED,font=("TkDefaultFont",11,"bold"))
        if value is None: display="--.-°"; color=MUTED
        else: display=f"{abs(value):.1f}°"; ratio=abs(value)/warning_deg; color=RED if ratio>=1 else AMBER if ratio>=.75 else GREEN
        self._canvas.create_text(x+width/2,y+70,text=display,fill=color,font=("TkFixedFont",30,"bold")); self._canvas.create_text(x+width/2,y+121,text=direction if value is not None else "--",fill=TEXT,font=("TkDefaultFont",10,"bold"))

    def _draw_bottom_cards(self,width,height,state)->None:
        top=height-128; margin=14; gap=8; labels=[]
        if state is None: labels.extend((("FORE / AFT","--"),("LATERAL","--"),("ALTITUDE","--"),("SPEED","--"),("GPS COURSE","--"),("SATELLITES","--")))
        else:
            linear=state.linear_acceleration_mps2; gps=state.gps
            labels.extend((("FORE / AFT",f"{linear.x:+.2f} m/s²" if linear.x is not None else "--"),("LATERAL",f"{linear.y:+.2f} m/s²" if linear.y is not None else "--"),("ALTITUDE",f"{gps.altitude_m:.1f} m" if gps.altitude_m is not None else "--"),("SPEED",f"{gps.speed_mps*2.23694:.1f} mph" if gps.speed_mps is not None else "--"),("GPS COURSE",f"{gps.course_deg:.0f}°" if gps.course_deg is not None else "--"),("SATELLITES",str(gps.satellites_used) if gps.satellites_used is not None else "--")))
        card_width=(width-2*margin-(len(labels)-1)*gap)/len(labels)
        for index,(label,value) in enumerate(labels):
            x=margin+index*(card_width+gap); self._canvas.create_rectangle(x,top,x+card_width,height-10,fill=PANEL,outline=GRID); self._canvas.create_text(x+card_width/2,top+25,text=label,fill=MUTED,font=("TkDefaultFont",9,"bold")); self._canvas.create_text(x+card_width/2,top+66,text=value,fill=TEXT,font=("TkFixedFont",14,"bold"))

    def _request_calibration(self)->None:
        if self._request_handler is not None: self._request_handler.request_stationary_calibration()

    def _request_heading_reset(self)->None:
        if self._request_handler is not None: self._request_handler.request_heading_reset()
