"""Translate navigation-service results into renderer-neutral route state."""

import math

from controllers.route_planning.route_planning_types import RouteResult
from messaging.contracts.route_guidance import RouteGuidanceStateMessage
from ui.navigation import GeoPoint, RouteGeometry, RouteOverlayState


class RouteOverlayController:
    """Merge route geometry and guidance without exposing either to a widget."""

    def __init__(self, update, *, point_limit=4096):
        self._update = update
        self._point_limit = point_limit
        self._route = None
        self._guidance = None

    def update_route(self, route: RouteResult | None):
        if route is not None and not isinstance(route, RouteResult):
            raise TypeError("Route overlay requires a RouteResult")
        self._route = route
        # Guidance indices describe the prior route until the service publishes
        # a correlated update for this replacement.
        self._guidance = None
        self._publish()

    def update_guidance(self, message: RouteGuidanceStateMessage):
        if not isinstance(message, RouteGuidanceStateMessage):
            raise TypeError("Route overlay guidance requires RouteGuidanceStateMessage")
        self._guidance = message
        self._publish()

    @staticmethod
    def _point(point):
        return GeoPoint(math.radians(point.latitude), math.radians(point.longitude))

    def _publish(self):
        route = self._route
        if route is None or len(route.shape) < 2:
            self._update(RouteOverlayState())
            return
        shape = route.shape
        step = max(1, math.ceil((len(shape) - 1) / (self._point_limit - 1)))
        selected = list(shape[::step])
        if selected[-1] is not shape[-1]:
            selected.append(shape[-1])
        guidance = self._guidance.data if self._guidance is not None else None
        maneuver = None
        instruction = None
        if guidance is not None and guidance.current_maneuver_index is not None:
            index = guidance.current_maneuver_index
            if 0 <= index < len(route.maneuvers):
                shape_index = route.maneuvers[index].end_shape_index
                if 0 <= shape_index < len(shape):
                    maneuver = self._point(shape[shape_index])
            instruction = guidance.instruction
        self._update(RouteOverlayState(
            RouteGeometry(tuple(self._point(point) for point in selected)),
            destination=self._point(shape[-1]), maneuver=maneuver,
            instruction=instruction,
            off_route=bool(guidance and guidance.off_route),
            route_complete=bool(guidance and guidance.route_complete),
        ))
