"""Airframe-neutral coalition SA data, extracted once from the game state.

The DTC cartridges are type-scoped (one per airframe), so everything here is the
*shared* coalition picture from the blue point of view: enemy threat rings, the front
line trace, and friendly orbit tracks (CAP + tankers). Each airframe builder
(``cartridge.py``) turns this into the partition layout that airframe expects, applying
the per-airframe unit quirks (e.g. F-16 threat radius in metres, F-18 MEZ in NM).

Positions are DCS world coordinates in metres (``x`` north, ``y`` east) -- the same
projection pydcs uses, so no conversion is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.ato.flightplans.patrolling import PatrollingFlightPlan
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game

# F-16 THREAT_PTS only spans steerpoints 56-70, and the F-18 MEZ list is similarly
# finite. Rank by threat range and keep the most dangerous handful.
MAX_THREAT_RINGS = 15
# Default racetrack width when we only know the centreline (metres ~= 5 NM).
DEFAULT_TRACK_WIDTH_M = 9260.0


@dataclass(frozen=True)
class ThreatRing:
    """An enemy threat circle: centre + lethal radius."""

    x: float
    y: float
    radius_m: float
    name: str


@dataclass(frozen=True)
class OrbitTrack:
    """A friendly racetrack (CAP or tanker), as a centreline + width."""

    x: float  # centre
    y: float
    course_deg: int
    length_m: int
    width_m: float
    name: str


@dataclass(frozen=True)
class Polyline:
    """An ordered list of world-coordinate (x, y) points."""

    points: list[tuple[float, float]]
    name: str


@dataclass
class SaData:
    threats: list[ThreatRing] = field(default_factory=list)
    orbits: list[OrbitTrack] = field(default_factory=list)
    front_lines: list[Polyline] = field(default_factory=list)


def _collect_threats(game: Game) -> list[ThreatRing]:
    rings: list[ThreatRing] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if tgo.is_friendly(Player.BLUE):
                continue
            threat_range = tgo.max_threat_range().meters
            if threat_range <= 0:
                continue
            rings.append(
                ThreatRing(
                    x=tgo.position.x,
                    y=tgo.position.y,
                    radius_m=threat_range,
                    name=tgo.name,
                )
            )
    # Keep the most dangerous rings; the airframe partitions are capacity-limited.
    rings.sort(key=lambda r: r.radius_m, reverse=True)
    return rings[:MAX_THREAT_RINGS]


def _collect_orbits(game: Game) -> list[OrbitTrack]:
    orbits: list[OrbitTrack] = []
    for package in game.blue.ato.packages:
        for flight in package.flights:
            if flight.client_count <= 0:
                # Only player-relevant orbits are worth cluttering the SA page with.
                continue
            flight_plan = flight.flight_plan
            if not isinstance(flight_plan, PatrollingFlightPlan):
                continue
            start = flight_plan.layout.patrol_start.position
            end = flight_plan.layout.patrol_end.position
            center = (start + end) / 2
            orbits.append(
                OrbitTrack(
                    x=center.x,
                    y=center.y,
                    course_deg=int(start.heading_between_point(end)),
                    length_m=int(start.distance_to_point(end)),
                    width_m=DEFAULT_TRACK_WIDTH_M,
                    name=str(flight),
                )
            )
    return orbits


def _collect_front_lines(game: Game) -> list[Polyline]:
    # Imported lazily: frontlineconflictdescription pulls in mission-generation deps.
    from game.missiongenerator.frontlineconflictdescription import (
        FrontLineConflictDescription,
    )

    lines: list[Polyline] = []
    for front_line in game.theater.conflicts():
        bounds = FrontLineConflictDescription.frontline_bounds(front_line, game.theater)
        lines.append(
            Polyline(
                points=[
                    (bounds.left_position.x, bounds.left_position.y),
                    (bounds.right_position.x, bounds.right_position.y),
                ],
                name=front_line.name,
            )
        )
    return lines


def collect_sa_data(game: Game) -> SaData:
    """Build the blue-coalition SA picture shared by all DTC cartridges."""
    return SaData(
        threats=_collect_threats(game),
        orbits=_collect_orbits(game),
        front_lines=_collect_front_lines(game),
    )
