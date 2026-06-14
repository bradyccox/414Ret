from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.theater import TheaterGroundObject
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from ..flightwaypointtype import FlightWaypointType


class TarpsFlightPlan(FormationAttackFlightPlan):
    """Tactical photo-recon overflight (F-14B TARPS).

    Routes a strike-style ingress / target overflight / egress, but carries a
    positive TOT offset so the recon bird passes over the target ~5 minutes
    behind the strikers — i.e. a post-strike BDA / discovery pass rather than an
    attack. The flight itself drops nothing; the recon value (imagery) is handled
    out-of-band and is intentionally not modeled here (fog of war stays intact).
    """

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        # Overfly the target after the strikers have hit it (post-strike BDA).
        return timedelta(minutes=5)


class Builder(FormationAttackBuilder[TarpsFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target

        if not isinstance(location, TheaterGroundObject):
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        # A photo-recon pass is a single overflight of the target area, not an
        # attack run weaving over every individual unit. Passing no per-unit
        # targets makes the builder emit one TARGET-area waypoint at the target
        # center instead of one waypoint per strike target.
        return self._build(FlightWaypointType.INGRESS_STRIKE, None)

    def build(self, dump_debug_info: bool = False) -> TarpsFlightPlan:
        return TarpsFlightPlan(self.flight, self.layout())
